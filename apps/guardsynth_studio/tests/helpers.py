from copy import deepcopy
from fractions import Fraction
import hashlib
from pathlib import Path

from apps.guardsynth_studio.common import digest, uid
from apps.guardsynth_studio.store import Store
from apps.guardsynth_studio.service import Service


def fixture(root, count=10):
    store = Store(root)
    service = Service(store)
    group = store.put("lineage", {"revision": 0, "split": "train", "confirmed": True})
    video = store.put("video", {"original_sha256": "f" * 64, "asset_id": "original", "permission": True,
                               "source": "synthetic test", "license": "test", "revision": 0,
                               "lineage_group_id": group, "status": "READY", "drive_id": "test-drive"})
    frames = []
    for i in range(count):
        frame = {"frame_id": uid(), "asset_id": uid(), "ordinal": i, "timestamp_us": i * 1000000,
                 "pts": i, "time_base": "1", "dimensions": [64, 64], "pixel_sha256": digest(i)}
        frames.append(frame)
    extraction = store.put("extraction", {"video_id": video, "frames": frames, "status": "READY"})
    with store.transaction():
        ids = [store.create_moment(extraction, i, f) for i, f in enumerate(frames)]
    return store, service, ids, extraction, video, group


def edit(service, identity, kind, data):
    return service.edit(identity, service.store.moment(identity)["revision"], kind, data, "reviewer", uid())


def approve(service, identity, kind):
    m = service.store.moment(identity)
    c = m["components"][kind]
    return service.approve([{"moment_id": identity, "revision": m["revision"], "stage": kind,
                             "component_id": c["id"], "dependency_digest": digest(c["dependencies"]),
                             "decision": "APPROVE"}], "reviewer", uid())


def binding(service, identity, truth="FALSE"):
    m = service.store.moment(identity)
    return {"binding_status": "BOUND", "zone_id": "entry_zone", "zone_polygon": [[0, 0], [1, 0], [1, 1]],
            "target_id": "person", "target_point": [.5, .5], "target_name": "검토 대상", "zone_name": "진입 영역",
            "frame_id": m["frame"]["frame_id"], "evidence_refs": [m["frame"]["frame_id"]],
            "t0_us": m["t0_us"], "max_observed_timestamp_us": m["t0_us"],
            "event_predicates": {"ped": {"truth": truth, "evidence_valid": True, "prior_active": None},
                                 "road": {"truth": "FALSE", "evidence_valid": True, "prior_active": None,
                                          "contextual_target_confirmed": True}}}


def contract():
    return {"contract_version": "eblc-action-contract-v0.1", "contract_id": "studio_test", "horizon": 3,
            "claim_scope": "CONDITIONAL_ACTION_SELECTION_NOT_VEHICLE_SAFETY", "subject_id": "ego",
            "zone_id": "entry_zone", "policy": "CLEAR_REQUIRED_FOR_ENTRY", "source_refs": ["policy"],
            "obligations": [{"obligation_id": oid, "predicate_id": pred, "target_entity_id": target,
                             "rule_ref": "policy", "source_refs": ["policy"]}
                            for oid, pred, target in [("ped", "pedestrian_conflict", "person"),
                                                      ("road", "main_road_yield_required", None)]]}


def proposal():
    return {"frontend_version": "guardsynth-coc-conditioned-frontend-v0.1", "request_id": "test",
            "status": "PROPOSED", "reason_codes": [], "claim_promoted_to_scene_or_legal_authority": False,
            "claim_scope": "CONDITIONAL", "coc_parse": {"parser_version": "guardsynth-coc-conditioned-frontend-v0.1",
            "language": "ko", "epistemic_kind": "CLAIMED", "evidence_ref": "test", "text_included": False,
            "concepts": {}, "unknown_groups": []}, "proposals": [
                {"rule_id": "policy", "slice": "entry", "source_claim_refs": ["policy"], "source_record_refs": ["policy"],
                 "required_predicate_refs": ["pedestrian_conflict", "main_road_yield_required"], "applicability": "TRUE",
                 "binding_status": "BOUND", "binder_ref": "human", "verdict": "PROPOSED", "reason_codes": [],
                 "claim_boundary": "CONDITIONAL"}]}


def prepare(service, identity, real_provenance_fixture=False, truth="FALSE"):
    edit(service, identity, "coc", {"edited_text": "현재 관찰", "causal_confirmed": True, "observations": "관찰", "leakage": False})
    if real_provenance_fixture:
        # Synthetic provenance injection for export unit tests, NEVER an actual VLM acceptance test.
        with service.store.transaction():
            m = service.store.moment(identity)
            p = deepcopy(m["components"]["coc"]["payload"])
            p.update(origin="REAL", raw_output="synthetic test fixture", model_version="test-only")
            service.store.install(m, "coc", p)
            service.store.save(m, "fixture")
    approve(service, identity, "coc")
    edit(service, identity, "source", {"records": [{"id": "policy", "kind": "POLICY", "version": "1",
                                                   "locator": "section 1", "quote": "yield", "sha256": hashlib.sha256(b"yield").hexdigest(), "reviewed": True}]})
    approve(service, identity, "source")
    edit(service, identity, "binding", binding(service, identity, truth))
    approve(service, identity, "binding")
    edit(service, identity, "proposal", proposal())
    approve(service, identity, "proposal")
    edit(service, identity, "contract", contract())
    approve(service, identity, "contract")
    edit(service, identity, "action", {"labels": {"ENTER_ZONE": "APPROPRIATE" if truth == "FALSE" else "INAPPROPRIATE",
                                                "DEFER_ENTRY": "APPROPRIATE"}, "vocabulary_version": "test"})
    approve(service, identity, "action")


def video_bytes(root, count=20):
    import av
    from PIL import Image
    path = Path(root) / (uid() + ".mp4")
    with av.open(str(path), "w") as output:
        stream = output.add_stream("libx264", rate=2)
        stream.width, stream.height, stream.pix_fmt = 64, 64, "yuv420p"
        stream.codec_context.thread_count = 1
        for i in range(count):
            frame = av.VideoFrame.from_image(Image.new("RGB", (64, 64), (i * 9 % 255, 30, 40)))
            frame.pts, frame.time_base = i, Fraction(1, 2)
            for packet in stream.encode(frame):
                output.mux(packet)
        for packet in stream.encode():
            output.mux(packet)
    return path.read_bytes()
