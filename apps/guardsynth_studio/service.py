"""Transactional Studio workflows. Request payloads cannot assign verification state."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

from . import ROOT
from .common import StudioError, digest, dumps, now, uid
from .media import LIMITS
from .provider import DisabledProvider, OpenAIProvider, PROMPT_VERSIONS
from .store import EDITABLE, DEPENDENCIES


def payload(moment, kind):
    return moment["components"].get(kind, {}).get("payload", {})


class Service:
    def __init__(self, store, provider=None):
        self.store = store
        self.provider = provider or DisabledProvider()
        if isinstance(self.provider, OpenAIProvider):
            self.provider.service = self
        self._video_ids = {}
        self._frames = {}

    def capabilities(self):
        return {"studio_schema_version": 1, "provider_mode": self.provider.mode, "model": self.provider.model,
                "profiles": ["studio-entry-v0.1"], "limits": LIMITS, "classification": "RESTRICTED"}

    def asset_path(self, asset_id):
        asset = self.store.get(asset_id, "asset")
        unresolved = self.store.root / asset["relative_path"]
        path = unresolved.resolve()
        if not path.is_relative_to(self.store.root) or unresolved.is_symlink() or not path.is_file():
            raise StudioError("ASSET", "Asset unavailable", 404)
        if asset.get("export_id"):
            exp = self.store.get(asset["export_id"], "export")
            if exp["status"] != "READY" or not self.snapshot_valid(exp):
                raise StudioError("REVOKED", "Export is not available", 409)
        return path

    def free_space(self):
        if shutil.disk_usage(self.store.root).free < LIMITS["free_bytes"]:
            raise StudioError("DISK_FULL", "At least 2 GiB free space required", 507)

    def upload(self, data, metadata, actor, key):
        if not 0 < len(data) <= LIMITS["upload_bytes"]:
            raise StudioError("UPLOAD_SIZE", "Upload size exceeds limit", 413)
        if not all(isinstance(metadata.get(k), str) and metadata[k].strip() for k in ("name", "source", "license")) or metadata.get("permission") is not True:
            raise StudioError("PERMISSION", "Source, license and permission required")
        hashed = hashlib.sha256(data).hexdigest()
        def operation():
            self.free_space()
            parent = self.store.get(metadata["parent_video_id"], "video") if metadata.get("parent_video_id") else None
            matches = [v for v in self.store.objects("video") if v["original_sha256"] == hashed or
                       (metadata.get("drive_id") and v.get("drive_id") == metadata["drive_id"])]
            groups = {v["lineage_group_id"] for v in matches}
            if parent:
                groups.add(parent["lineage_group_id"])
                interval = metadata.get("parent_interval_us")
                if not isinstance(interval, list) or len(interval) != 2 or not all(type(x) is int for x in interval) or not 0 <= interval[0] < interval[1]:
                    raise StudioError("LINEAGE", "Parent source interval required")
            if len(groups) > 1:
                raise StudioError("LINEAGE_CONFLICT", "Merge lineage groups explicitly first", 409)
            group_id = next(iter(groups), uid())
            if not groups:
                self.store.put("lineage", {"revision": 0, "split": None, "confirmed": False}, group_id)
            asset_id, video_id = uid(), uid()
            relative = f"uploads/{asset_id}.mp4"
            path = self.store.root / relative
            path.parent.mkdir(exist_ok=True)
            with path.open("xb") as handle:
                handle.write(data)
                handle.flush()
                import os
                os.fsync(handle.fileno())
            self.store.put("asset", {"relative_path": relative, "content_type": "video/mp4", "sha256": hashed}, asset_id)
            video = {k: metadata.get(k) for k in ("name", "source", "license", "drive_id", "parent_video_id", "parent_interval_us")}
            video.update({"original_sha256": hashed, "asset_id": asset_id, "permission": True,
                          "classification": "RESTRICTED", "lineage_group_id": group_id, "revision": 0,
                          "uploaded_by": actor, "created": now(), "status": "PROBE_PENDING"})
            self.store.put("video", video, video_id)
            job_id = self.new_job("PROBE", {"video_id": video_id}, actor)
            return {"video_id": video_id, "job_id": job_id}
        return self.store.mutate(actor, key, {"op": "upload", "sha": hashed, "metadata": metadata}, operation)

    def new_job(self, kind, inputs, actor, moment=None):
        if sum(j["status"] == "QUEUED" for j in self.store.objects("job")) >= LIMITS["queue"]:
            raise StudioError("QUEUE_FULL", "Queue is full", 429)
        value = {"kind": kind, "inputs": deepcopy(inputs), "input_digest": digest(inputs), "actor": actor,
                 "moment_id": moment["id"] if moment else None, "base_revision": moment["revision"] if moment else None,
                 "status": "QUEUED", "generation": 0, "attempt": 0, "result": None, "error": None,
                 "provider_mode": self.provider.mode if kind in ("COC", "PROPOSAL") else None, "created": now()}
        if kind in ("COC", "PROPOSAL") and isinstance(self.provider, OpenAIProvider):
            value["provider_binding"] = self.provider.authorize(moment)
        return self.store.put("job", value)

    def extraction(self, video_id, interval, actor, key):
        def operation():
            video = self.store.get(video_id, "video")
            if video["status"] != "READY":
                raise StudioError("VIDEO_NOT_READY", "Video probe has not succeeded")
            identity = uid()
            self.store.put("extraction", {"video_id": video_id, "status": "QUEUED", "interval_s": interval}, identity)
            job = self.new_job("EXTRACT", {"extraction_id": identity, "video_id": video_id, "interval_s": interval}, actor)
            return {"extraction_id": identity, "job_id": job}
        return self.store.mutate(actor, key, ["extract", video_id, interval], operation)

    def moments(self, extraction_id):
        rows = self.store.db.execute("SELECT id FROM moments WHERE extraction=? ORDER BY ordinal", (extraction_id,))
        result = []
        for row in rows:
            m = self.store.moment(row[0])
            summary = {k: m[k] for k in ("id", "ordinal", "t0_us", "revision", "completion")}
            summary["eligibility"] = self.eligibility(m)
            result.append(summary)
        return result

    def video_id(self, extraction_id):
        if extraction_id not in self._video_ids:
            self._video_ids[extraction_id] = self.store.get(extraction_id, "extraction")["video_id"]
        return self._video_ids[extraction_id]

    def causal_frames(self, moment):
        identity = moment["extraction_id"]
        if identity not in self._frames:
            self._frames[identity] = self.store.get(identity, "extraction")["frames"]
        frames = self._frames[identity][max(0, moment["ordinal"] - 6):moment["ordinal"] + 1]
        if not frames or any(f["timestamp_us"] > moment["t0_us"] for f in frames):
            raise StudioError("FUTURE", "Invalid causal frame manifest")
        return deepcopy(frames)

    def moment(self, identity):
        value = self.store.moment(identity)
        self.refresh_tool_versions(value)
        value["frames"] = self.causal_frames(value)
        value["eligibility"] = self.eligibility(value)
        return value

    def attach_vehicle_state(self, identity, revision, data, actor, key):
        """Operator-only example import before annotation; immutable after attachment."""
        from .vehicle_state import validate
        validate(data, self.store.get(identity, "video"))
        def operation():
            video = self.store.get(identity, "video")
            if video["revision"] != revision or video.get("vehicle_state_id"):
                raise StudioError("REVISION_CONFLICT", "Vehicle state is immutable; import a new example", 409)
            extractions = {e["id"] for e in self.store.objects("extraction") if e["video_id"] == identity}
            for row in self.store.db.execute("SELECT id, extraction FROM moments"):
                if row["extraction"] in extractions and self.store.moment(row["id"])["components"]:
                    raise StudioError("REVISION_CONFLICT", "Attach state before annotation", 409)
            validate(data, video)
            video.update(vehicle_state_id=self.store.put("vehicle_state", deepcopy(data)),
                         vehicle_state_digest=digest(data), revision=revision + 1, vehicle_state_actor=actor)
            self.store.put("video", video, identity)
            return {"video_id": identity, "revision": video["revision"]}
        return self.store.mutate(actor, key, ["vehicle_state", identity, revision, data], operation)

    def causal_vehicle_state(self, moment):
        from .vehicle_state import validate, causal_projection
        video = self.store.get(self.video_id(moment["extraction_id"]), "video")
        if not video.get("vehicle_state_id"):
            return None
        value = self.store.get(video["vehicle_state_id"], "vehicle_state")
        validate(value, video)
        if digest(value) != video["vehicle_state_digest"]:
            raise StudioError("VEHICLE_STATE_INTEGRITY", "Vehicle state changed")
        return causal_projection(value, self.causal_frames(moment))

    def validate_edit(self, moment, kind, data):
        if not isinstance(data, dict):
            raise StudioError("PAYLOAD", "Object required")
        def reject_secrets(value):
            if isinstance(value, dict):
                if any(k.lower() in ("secret", "password", "api_key", "authorization", "secret_hash") for k in value):
                    raise StudioError("SECRET", "Credentials cannot be stored in review/export payloads")
                for child in value.values(): reject_secrets(child)
            elif isinstance(value, list):
                for child in value: reject_secrets(child)
        reject_secrets(data)
        if kind == "coc":
            allowed = {"observations", "relations", "assumptions", "unknowns", "action_rationale", "suggested_actions",
                       "edited_text", "causal_confirmed", "leakage", "context_text"}
            if set(data) - allowed:
                raise StudioError("PROVENANCE", "Generated provenance cannot be edited")
            if any(not isinstance(data[k], str) for k in ("observations", "relations", "assumptions", "unknowns", "action_rationale", "edited_text", "context_text") if k in data):
                raise StudioError("COC_SCHEMA", "CoC fields must be text")
            if any(type(data[k]) is not bool for k in ("causal_confirmed", "leakage") if k in data):
                raise StudioError("COC_SCHEMA", "CoC review flags must be boolean")
            original = payload(moment, "coc")
            data = {**original, **data}
            data.setdefault("origin", "HUMAN")
        if kind in ("binding", "coc"):
            if data.get("max_observed_timestamp_us", moment["t0_us"]) > moment["t0_us"]:
                raise StudioError("FUTURE", "Future evidence is not allowed")
        if kind == "binding":
            data["t0_us"] = moment["t0_us"]
            frame_ids = {f["frame_id"] for f in self.causal_frames(moment)}
            if data.get("frame_id") not in frame_ids:
                raise StudioError("FUTURE", "Binding frame must be causal")
            for field in ("target_point", "zone_polygon", "draft_zone_points"):
                if field in data:
                    points = [data[field]] if field == "target_point" else data[field]
                    if not isinstance(points, list) or (field == "zone_polygon" and len(points) < 3):
                        raise StudioError("GEOMETRY", "Polygon needs at least three points; remove field to delete")
                    for point in points:
                        if not isinstance(point, list) or len(point) != 2 or any(type(x) not in (int, float) or not 0 <= x <= 1 for x in point):
                            raise StudioError("GEOMETRY", "Normalized pixel coordinates required")
        if kind == "action":
            labels = data.get("labels")
            if not isinstance(labels, dict) or not labels or any(v not in ("APPROPRIATE", "INAPPROPRIATE", "UNKNOWN", "NOT_APPLICABLE") for v in labels.values()):
                raise StudioError("LABELS", "Four-valued action labels required")
            data["unknown_mask"] = {k: v == "UNKNOWN" for k, v in labels.items()}
        if kind == "proposal":
            from guard_synth_eblc.schema_validation import load_json, validate
            validate(data, load_json(ROOT / "projects/04-guardsynth-coc/src/guard_synth/schemas/constraint_proposal_bundle.schema.json"))
        if kind == "applicability" and data.get("status") not in ("UNREVIEWED", "APPLICABLE", "NOT_APPLICABLE", "UNRESOLVED"):
            raise StudioError("APPLICABILITY", "Invalid applicability status")
        if kind == "source":
            if not isinstance(data.get("records"), list):
                raise StudioError("SOURCE", "Source records required")
            if any(not isinstance(r, dict) or any(not isinstance(r.get(k, ""), str) for k in ("id", "version", "locator", "quote", "sha256")) for r in data["records"]):
                raise StudioError("SOURCE_SCHEMA", "Source records must contain text fields")
        return data

    def edit(self, identity, revision, kind, data, actor, key, dependencies=()):
        if kind not in EDITABLE:
            raise StudioError("READ_ONLY", "Derived verification state is server-owned")
        def operation():
            m = self.store.require_head(identity, revision)
            checked = self.validate_edit(m, kind, deepcopy(data))
            self.store.install(m, kind, checked, dependencies)
            return self.store.save(m, actor)
        return self.store.mutate(actor, key, ["edit", identity, revision, kind, data, dependencies], operation)

    def require_approvals(self, moment, kinds):
        self.refresh_tool_versions(moment)
        for kind in kinds:
            if not self.store.approved(moment, kind):
                raise StudioError("APPROVAL_REQUIRED", f"Current {kind} approval required")

    def validate_approval(self, m, kind):
        self.refresh_tool_versions(m)
        data = payload(m, kind)
        if kind == "coc" and (not data.get("edited_text") or data.get("causal_confirmed") is not True or data.get("leakage")):
            raise StudioError("CAUSAL_REVIEW", "CoC text and causal-only review required")
        if kind == "source":
            if not data.get("records"):
                raise StudioError("SOURCE", "No grounded sources")
            for r in data["records"]:
                if r.get("kind") not in ("EXTERNAL", "POLICY") or not all(r.get(k) for k in ("id", "version", "locator", "quote", "sha256")) or r.get("reviewed") is not True:
                    raise StudioError("SOURCE", "Source text/version/location and human review required")
                if r["sha256"] != hashlib.sha256(r["quote"].encode()).hexdigest():
                    raise StudioError("SOURCE_HASH", "Source excerpt hash mismatch")
                if r["kind"] == "EXTERNAL" and not all(r.get(k) for k in ("jurisdiction", "applicable_scope", "effective_period")):
                    raise StudioError("SOURCE", "External authority applicability unresolved")
        if kind == "binding":
            if data.get("binding_status") != "BOUND" or not data.get("zone_id") or not data.get("zone_polygon") or not data.get("evidence_refs"):
                raise StudioError("UNBOUND", "Zone and causal evidence binding required")
            causal_ids = {f["frame_id"] for f in self.causal_frames(m)}
            if not set(data["evidence_refs"]).issubset(causal_ids):
                raise StudioError("FUTURE", "Unbound or future frame evidence")
        if kind == "proposal":
            self.require_approvals(m, ("coc", "source", "binding"))
            if data.get("status") != "PROPOSED" or not data.get("proposals"):
                raise StudioError("UNRESOLVED", "Empty, conflicting or unsupported proposals cannot be approved")
            sources = {r["id"] for r in payload(m, "source")["records"]}
            for p in data["proposals"]:
                if p["binding_status"] != "BOUND" or p["applicability"] != "TRUE" or p["verdict"] != "PROPOSED" or not p["source_record_refs"] or not set(p["source_record_refs"]).issubset(sources):
                    raise StudioError("UNBOUND", "Proposal source/binding unresolved")
        if kind == "contract":
            self.require_approvals(m, ("proposal", "source", "binding"))
            from guard_synth.studio_contract import validate_profile
            validate_profile(data, payload(m, "binding"))
            sources = {r["id"] for r in payload(m, "source")["records"]}
            proposed_rules = {p["rule_id"] for p in payload(m, "proposal")["proposals"]}
            if not set(data["source_refs"]).issubset(sources) or any(o["rule_ref"] not in proposed_rules for o in data["obligations"]):
                raise StudioError("SOURCE", "Contract sources/rules do not match approved proposal")
            proposals = payload(m, "proposal")["proposals"]
            for obligation in data["obligations"]:
                if not any(p["rule_id"] == obligation["rule_ref"] and obligation["predicate_id"] in p["required_predicate_refs"]
                           and set(obligation["source_refs"]).issubset(p["source_record_refs"]) for p in proposals):
                    raise StudioError("PROPOSAL_MAPPING", "Contract obligation is not supported by the approved proposal")
        if kind in ("cnl", "combined"):
            self.require_approvals(m, ("contract", "binding", "source"))
            check = m["components"].get("check", {})
            if check.get("stale", True) or payload(m, "check").get("status") != "PASS":
                raise StudioError("CHECK", "Current complete SMT check required")
        if kind == "combined":
            self.require_approvals(m, ("coc", "cnl", "action"))
            labels = payload(m, "action")["labels"]
            allowed = payload(m, "cnl")["allowed_actions"]
            if any(v == "APPROPRIATE" and k not in allowed for k, v in labels.items()):
                raise StudioError("ACTION_CONFLICT", "Approved action and contract conflict")
        if kind == "applicability" and data.get("status") == "NOT_APPLICABLE":
            self.require_approvals(m, ("coc",))
            if data.get("candidate_reviewed") is not True or not data.get("reason"):
                raise StudioError("APPLICABILITY", "Explicit candidate review and reason required")
        if kind == "context" and (data.get("no_label_leakage") is not True or not data.get("text")):
            raise StudioError("LEAKAGE", "Reviewed context projection required")

    def approve(self, items, actor, key):
        if not items or len(items) > 100:
            raise StudioError("BATCH", "Approve 1–100 explicit items")
        def operation():
            seen, values = set(), []
            for item in items:
                if item["moment_id"] in seen:
                    raise StudioError("BATCH", "One stage per moment per batch")
                seen.add(item["moment_id"])
                m = self.store.require_head(item["moment_id"], item["revision"])
                c = m["components"].get(item["stage"])
                if not c or c["id"] != item["component_id"] or digest(c["dependencies"]) != item["dependency_digest"]:
                    raise StudioError("STALE", "Approval diff changed", 409)
                if item["decision"] not in ("APPROVE", "REJECT", "HOLD"):
                    raise StudioError("DECISION", "Invalid human decision")
                if item["decision"] == "APPROVE":
                    self.validate_approval(m, item["stage"])
                events = [e for e in self.store.objects("exposure") if e["actor"] == actor and e["extraction_id"] == m["extraction_id"]]
                m["exposures"] = [{"actor": actor, "max_viewed_t0_us": max((e["t0_us"] for e in events), default=m["t0_us"]),
                                   "constraints_visible": any(e["constraints_visible"] for e in events)}]
                self.store.record_approval(m, item["stage"], item["decision"], actor, item.get("note", ""))
                values.append(self.store.save(m, actor))
            return {"moments": values}
        return self.store.mutate(actor, key, ["approve", items], operation)

    def enqueue(self, identity, revision, kind, actor, key):
        if kind not in ("COC", "PROPOSAL", "CHECK", "CNL", "COMBINE"):
            raise StudioError("JOB", "Unsupported job")
        if kind in ("COC", "PROPOSAL") and self.provider.mode == "DISABLED":
            raise StudioError("PROVIDER_NOT_CONFIGURED", "Provider/model not selected; local review remains available", 503)
        def operation():
            m = self.store.require_head(identity, revision)
            required = {"COC": (), "PROPOSAL": ("coc", "source", "binding"), "CHECK": ("contract", "binding", "source"),
                        "CNL": ("contract", "binding", "source"), "COMBINE": ("coc", "cnl", "action")}[kind]
            self.require_approvals(m, required)
            if kind == "CNL" and (payload(m, "check").get("status") != "PASS" or m["components"]["check"]["stale"]):
                raise StudioError("CHECK", "Current check required")
            frames = self.causal_frames(m)
            inputs = {"frames": frames, "t0_us": m["t0_us"], "moment": m,
                      "prompt_version": PROMPT_VERSIONS.get(kind, "studio-causal-v1")}
            if kind == "COC":
                state = self.causal_vehicle_state(m)
                if state is not None:
                    inputs.update(vehicle_state=state, prompt_version=PROMPT_VERSIONS["STATE_COC"])
            return {"job_id": self.new_job(kind, inputs, actor, m)}
        return self.store.mutate(actor, key, ["job", identity, revision, kind], operation)

    def job_action(self, identity, action, actor, key):
        def operation():
            j = self.store.get(identity, "job")
            if action == "cancel":
                if j["status"] in ("QUEUED", "RUNNING"):
                    j.update(status="CANCELLED", generation=j["generation"] + 1)
                    self.store.put("job", j, identity)
                return {"job_id": identity, "status": j["status"]}
            if action != "retry" or j["status"] not in ("FAILED", "TIMED_OUT", "INTERRUPTED", "OUTCOME_UNKNOWN") or j["attempt"] >= 2:
                raise StudioError("RETRY", "Job cannot be retried")
            if j["moment_id"] and self.store.moment(j["moment_id"])["revision"] != j["base_revision"]:
                raise StudioError("STALE", "Recreate job using current revision", 409)
            j.update(status="QUEUED", generation=j["generation"] + 1, error=None)
            self.store.put("job", j, identity)
            return {"job_id": identity, "status": "QUEUED"}
        return self.store.mutate(actor, key, [action, identity], operation)

    def eligibility(self, m):
        self.refresh_tool_versions(m)
        reasons = []
        for k in ("coc", "action"):
            if not self.store.approved(m, k):
                reasons.append(k.upper() + "_UNAPPROVED")
        if payload(m, "coc").get("origin") != "REAL":
            reasons.append("REAL_PROVIDER_REQUIRED")
        if payload(m, "coc").get("leakage") or not payload(m, "coc").get("causal_confirmed"):
            reasons.append("CAUSAL_REVIEW_REQUIRED")
        video = self.store.get(self.video_id(m["extraction_id"]), "video")
        group = self.store.get(video["lineage_group_id"], "lineage")
        if video.get("vehicle_state_id"):
            reasons.append("VEHICLE_STATE_DEMO_ONLY")
        if not video["permission"]:
            reasons.append("PERMISSION_REVOKED")
        if not group["confirmed"] or not group["split"]:
            reasons.append("LINEAGE_SPLIT_UNRESOLVED")
        labels = payload(m, "action").get("labels", {})
        if any(k not in ("ENTER_ZONE", "DEFER_ENTRY") for k in labels):
            reasons.append("UNSUPPORTED_ACTION")
        if self.store.approved(m, "applicability") and payload(m, "applicability").get("status") == "NOT_APPLICABLE":
            return {"state": "BASELINE_ONLY_READY" if not reasons else "HELD", "reasons": reasons}
        for k in ("source", "binding", "proposal", "contract", "cnl", "combined"):
            if not self.store.approved(m, k):
                reasons.append(k.upper() + "_UNAPPROVED")
        check = m["components"].get("check", {})
        if check.get("stale", True) or payload(m, "check").get("status") != "PASS":
            reasons.append("CHECK_REQUIRED")
        if payload(m, "cnl").get("review_required", True):
            reasons.append("OBSERVATION_UNRESOLVED")
        return {"state": "ENHANCED_READY" if not reasons else "HELD", "reasons": reasons}

    def refresh_tool_versions(self, m):
        if not any(k in m["components"] for k in ("check", "cnl")):
            return
        from guard_synth.studio_contract import QUERY_VERSION, renderer_signature
        from guard_synth_eblc.smt_compiler import COMPILER_VERSION
        changed = set()
        checked = payload(m, "check")
        if "check" in m["components"] and (checked.get("query_version") != QUERY_VERSION or
                any(r.get("compiler_version") != COMPILER_VERSION for r in checked.get("results", []))):
            changed.add("check")
        if "cnl" in m["components"] and payload(m, "cnl").get("renderer_signature") != renderer_signature():
            changed.add("cnl")
        while changed:
            for k in changed:
                m["components"][k]["stale"] = True
            more = {k for k, c in m["components"].items() if not c["stale"] and set(c["dependencies"]) & changed}
            changed = more

    def complete(self, identity, revision, actor, key):
        def operation():
            m = self.store.require_head(identity, revision)
            e = self.eligibility(m)
            m["completion"] = {"state": e["state"] if e["state"] != "HELD" else "REVIEW_COMPLETE_HELD",
                               "reasons": e["reasons"], "actor": actor, "created": now()}
            return self.store.save(m, actor)
        return self.store.mutate(actor, key, ["complete", identity, revision], operation)

    def lineage(self, group_id, revision, split, confirmed, actor, key):
        if split not in (None, "train", "validation", "test") or type(confirmed) is not bool:
            raise StudioError("SPLIT", "Invalid lineage review")
        def operation():
            g = self.store.get(group_id, "lineage")
            if g.get("merged_into"):
                raise StudioError("LINEAGE", "Use the merged lineage group", 409)
            if g["revision"] != revision:
                raise StudioError("REVISION_CONFLICT", "Lineage changed", 409)
            if g["split"] and split and g["split"] != split:
                raise StudioError("SPLIT_OVERLAP", "Group already assigned to another split", 409)
            g.update(revision=revision + 1, split=split, confirmed=confirmed, actor=actor)
            self.store.put("lineage", g, group_id)
            return g
        return self.store.mutate(actor, key, ["lineage", group_id, revision, split, confirmed], operation)

    def snapshot_valid(self, exp):
        for v in exp["videos"]:
            current = self.store.get(v["id"], "video")
            group = self.store.get(current["lineage_group_id"], "lineage")
            if not current["permission"] or current["revision"] != v["revision"] or digest(group) != v["lineage_digest"]:
                return False
        for m in exp["moments"]:
            # A source amendment/rejection is a safety invalidation, unlike ordinary CoC edits.
            current = self.store.moment(m["id"])
            for kind in ("source",):
                if current["components"].get(kind) != m["components"].get(kind) or current["approvals"].get(kind) != m["approvals"].get(kind):
                    return False
        return True

    def merge_lineages(self, entries, reason, actor, key):
        if not isinstance(entries, list) or len(entries) < 2 or len({e["id"] for e in entries}) != len(entries) or not reason:
            raise StudioError("LINEAGE", "Distinct groups and evidence reason required")
        def operation():
            groups = [self.store.get(e["id"], "lineage") for e in entries]
            if any(g["revision"] != e["revision"] for g, e in zip(groups, entries)):
                raise StudioError("REVISION_CONFLICT", "Lineage changed", 409)
            splits = {g["split"] for g in groups if g["split"]}
            target = entries[0]["id"]
            merged = {"revision": groups[0]["revision"] + 1, "split": next(iter(splits)) if len(splits) == 1 else None,
                      "confirmed": False, "conflicting_previous_splits": sorted(splits), "reason": reason, "actor": actor}
            self.store.put("lineage", merged, target)
            ids = {e["id"] for e in entries}
            for e, g in zip(entries[1:], groups[1:]):
                self.store.put("lineage", {**g, "revision": g["revision"] + 1, "confirmed": False, "merged_into": target}, e["id"])
            for v in self.store.objects("video"):
                if v["lineage_group_id"] in ids:
                    v.update(lineage_group_id=target, revision=v["revision"] + 1)
                    self.store.put("video", v, v["id"])
            return {"lineage_group_id": target, **merged}
        return self.store.mutate(actor, key, ["merge", entries, reason], operation)

    def video_permission(self, identity, revision, permission, actor, key):
        if type(permission) is not bool:
            raise StudioError("PERMISSION", "Boolean permission required")
        def operation():
            v = self.store.get(identity, "video")
            if v["revision"] != revision:
                raise StudioError("REVISION_CONFLICT", "Video permission changed", 409)
            v.update(permission=permission, revision=revision + 1, permission_actor=actor)
            self.store.put("video", v, identity)
            return v
        return self.store.mutate(actor, key, ["permission", identity, revision, permission], operation)

    def export(self, request, actor, key):
        if request.get("mode") not in ("COC_TARGET", "ACTION_WITH_CONTEXT") or request.get("purpose") not in ("DRAFT", "DEVELOPMENT_TRAINING"):
            raise StudioError("EXPORT_MODE", "Independent evaluation requires a separate reviewed protocol")
        def operation():
            selected = request.get("moments", [])
            if not selected or len(selected) > 10000 or len({i["id"] for i in selected}) != len(selected):
                raise StudioError("EXPORT_SIZE", "Select 1–10000 unique moments")
            values, videos = [], {}
            for item in selected:
                m = self.store.require_head(item["id"], item["revision"])
                m["frames"] = self.causal_frames(m)
                m["eligibility"] = self.eligibility(m)
                if request["mode"] == "ACTION_WITH_CONTEXT" and not self.store.approved(m, "context"):
                    m["eligibility"]["state"] = "HELD"
                    m["eligibility"]["reasons"].append("CONTEXT_LABEL_LEAKAGE_REVIEW_REQUIRED")
                video_id = self.video_id(m["extraction_id"])
                video = self.store.get(video_id, "video")
                group = self.store.get(video["lineage_group_id"], "lineage")
                videos[video_id] = {"id": video_id, **video, "lineage": group, "lineage_digest": digest(group)}
                m["video_id"] = video_id
                values.append(m)
            exp = {"status": "QUEUED", "studio_schema_version": 1, "mode": request["mode"], "purpose": request["purpose"],
                   "moments": values, "videos": list(videos.values()), "created": now(), "actor": actor}
            exp["snapshot_digest"] = digest(exp)
            identity = self.store.put("export", exp)
            return {"export_id": identity, "job_id": self.new_job("EXPORT", {"export_id": identity}, actor)}
        return self.store.mutate(actor, key, ["export", request], operation)
