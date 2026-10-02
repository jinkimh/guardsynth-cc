"""Responses wire contract tests: synthetic images and injected transport only."""

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from apps.guardsynth_studio import provider
from apps.guardsynth_studio.common import StudioError, dumps, uid
from apps.guardsynth_studio.jobs import Worker
from apps.guardsynth_studio.service import Service
from apps.guardsynth_studio.store import Store
from .helpers import fixture, prepare, proposal


def config():
    return {"mode": "OPENAI", "model": "explicit-test-model", "transmission_approved": True,
            "video_sha256_allowlist": ["f" * 64], "max_calls": 2,
            "max_output_tokens": 1024, "timeout_s": 10}


def coc():
    return {"observations": "현재 관찰", "relations": "", "assumptions": "", "unknowns": "",
            "action_rationale": "", "suggested_actions": [], "edited_text": "현재 관찰",
            "causal_confirmed": False}


def response(candidate=None):
    return {"id": "resp_test", "model": "explicit-test-model", "status": "completed",
            "output": [{"type": "message", "role": "assistant", "status": "completed",
                        "content": [{"type": "output_text", "text": dumps(candidate or coc()), "annotations": []}]}],
            "usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}}


class OpenAIProviderTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store, self.service, self.ids, self.extraction, self.video, _ = fixture(self.temp.name)
        self.addCleanup(lambda: self.store.close())
        from PIL import Image
        extraction = self.store.get(self.extraction, "extraction")
        for frame in extraction["frames"]:
            path = Path(self.temp.name) / (frame["asset_id"] + ".png")
            Image.new("RGB", (64, 64), (frame["ordinal"], 0, 0)).save(path)
            frame["file_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            self.store.put("asset", {"relative_path": path.name, "content_type": "image/png",
                                    "sha256": frame["file_sha256"]}, frame["asset_id"])
        self.store.put("extraction", extraction, self.extraction)
        self.sent = []
        self.reply = response()
        self.env = patch.dict(os.environ, {"OPENAI_API_KEY": "test-secret-never-persist"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def connect(self, settings=None):
        self.assertTrue(hasattr(provider, "OpenAIProvider"), "Responses adapter is missing")
        def transport(body, timeout):
            self.sent.append(deepcopy(body))
            if isinstance(self.reply, Exception):
                raise self.reply
            return deepcopy(self.reply)
        adapter = provider.OpenAIProvider(settings or config(), transport=transport)
        self.service = Service(self.store, adapter)

    def run_job(self, kind="COC", index=6):
        identity = self.ids[index]
        job = self.service.enqueue(identity, self.store.moment(identity)["revision"], kind, "reviewer", uid())
        Worker(self.service).run_once()
        return self.store.get(job["job_id"], "job")

    def test_missing_deployment_settings_disable_generation(self):
        for key in config():
            settings = config()
            settings.pop(key)
            try:
                adapter = provider.configured_provider(settings)
            except StudioError as exc:
                self.assertEqual(exc.status, 503)
            else:
                self.assertEqual(adapter.mode, "DISABLED")
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            self.assertEqual(provider.configured_provider(config()).mode, "DISABLED")

    def vehicle_state(self):
        return {"schema_version": 1, "dataset": "nuscenes-can-bus", "scene_id": "scene-0061",
                "video_sha256": "f" * 64, "source_sha256": "a" * 64, "clock_origin_utime": 1500000000000000,
                "transmission_approved": True,
                "samples": [{"timestamp_us": t, "vehicle_speed_kmh": speed, "brake_pressure_bar": 0,
                             "throttle_permille": 10, "steering_deg": 2}
                            for t, speed in [(0, 20), (5900000, 15), (6100000, 99)]]}

    def test_vehicle_state_is_causal_bound_and_preserved_in_draft_export(self):
        self.connect()
        self.assertTrue(hasattr(self.service, "attach_vehicle_state"), "Bounded vehicle state attachment missing")
        self.service.attach_vehicle_state(self.video, 0, self.vehicle_state(), "reviewer", uid())
        job = self.run_job()
        self.assertEqual(job["status"], "SUCCEEDED")
        data = json.loads(self.sent[0]["input"][0]["content"][0]["text"])["data"]["vehicle_state"]
        self.assertEqual(data["frames"][-1]["sample"]["vehicle_speed_kmh"], 15)
        self.assertEqual(data["frames"][-1]["age_us"], 100000)
        self.assertIsNone(data["frames"][1]["sample"])
        self.assertNotIn('99', dumps(data))
        m = self.store.moment(self.ids[6])
        self.assertEqual(m["components"]["coc"]["payload"]["vehicle_state_input"], data)
        self.assertIn("VEHICLE_STATE_DEMO_ONLY", self.service.eligibility(m)["reasons"])
        exported = self.service.export({"mode": "COC_TARGET", "purpose": "DRAFT",
                                        "moments": [{"id": m["id"], "revision": m["revision"]}]}, "reviewer", uid())
        Worker(self.service).run_once()
        exp = self.store.get(exported["export_id"], "export")
        path = next(f["relative_path"] for f in exp["files"] if f["relative_path"].endswith('samples.jsonl'))
        row = json.loads((self.store.root / path).read_text())
        self.assertEqual(row["inputs"]["vehicle_state"], data)
        self.assertFalse(row["training_eligible"])

    def test_vehicle_state_rejects_wrong_binding_labels_and_replacement(self):
        self.connect()
        self.assertTrue(hasattr(self.service, "attach_vehicle_state"), "Bounded vehicle state attachment missing")
        for change in ({"video_sha256": "b" * 64}, {"transmission_approved": False},
                       {"action_label": "BRAKE"}, {"clock_origin_utime": "unknown"}):
            with self.assertRaises(StudioError):
                self.service.attach_vehicle_state(self.video, 0, {**self.vehicle_state(), **change}, "reviewer", uid())
        invalid = self.vehicle_state()
        invalid["samples"][0]["vehicle_speed_kmh"] = float('nan')
        with self.assertRaises(StudioError):
            self.service.attach_vehicle_state(self.video, 0, invalid, "reviewer", uid())
        self.service.attach_vehicle_state(self.video, 0, self.vehicle_state(), "reviewer", uid())
        with self.assertRaises(StudioError):
            self.service.attach_vehicle_state(self.video, 1, self.vehicle_state(), "reviewer", uid())

    def test_state_prompt_revision_is_bound_to_wire_and_stales_old_jobs(self):
        self.connect()
        self.service.attach_vehicle_state(self.video, 0, self.vehicle_state(), "reviewer", uid())
        old = self.service.enqueue(self.ids[6], 0, "COC", "reviewer", uid())
        with patch.dict(provider.PROMPT_VERSIONS, {"STATE_COC": "test-state-revision"}):
            self.connect()
            Worker(self.service).run_once()
            self.assertEqual(self.store.get(old["job_id"], "job")["error"]["code"], "PROVIDER_CONFIG_CHANGED")
            self.assertFalse(self.sent)
            job = self.run_job()
            self.assertEqual(job["status"], "SUCCEEDED")
            data = json.loads(self.sent[0]["input"][0]["content"][0]["text"])["data"]
            self.assertEqual(data["version"], "test-state-revision")
            self.assertEqual(job["inputs"]["prompt_version"], data["version"])
            self.assertFalse(self.store.approved(self.store.moment(self.ids[6]), "coc"))

    def test_tampered_vehicle_state_job_never_transmits(self):
        self.connect()
        self.assertTrue(hasattr(self.service, "attach_vehicle_state"), "Bounded vehicle state attachment missing")
        self.service.attach_vehicle_state(self.video, 0, self.vehicle_state(), "reviewer", uid())
        result = self.service.enqueue(self.ids[6], 0, "COC", "reviewer", uid())
        job = self.store.get(result["job_id"], "job")
        job["inputs"]["vehicle_state"]["frames"][-1]["sample"]["timestamp_us"] = 7000000
        self.store.put("job", job, result["job_id"])
        Worker(self.service).run_once()
        self.assertFalse(self.sent)
        self.assertEqual(self.store.get(result["job_id"], "job")["error"]["code"], "PROVIDER_CAUSAL")

    def test_responses_images_stateless_schema_and_no_approval(self):
        self.connect()
        job = self.run_job()
        self.assertEqual(job["status"], "SUCCEEDED")
        wire = self.sent[0]
        self.assertEqual(wire["model"], "explicit-test-model")
        self.assertIs(wire["store"], False)
        self.assertEqual(wire["tools"], [])
        self.assertNotIn("previous_response_id", wire)
        self.assertNotIn("conversation", wire)
        images = [c for c in wire["input"][0]["content"] if c["type"] == "input_image"]
        self.assertEqual(len(images), 7)
        self.assertTrue(all(c["image_url"].startswith("data:image/png;base64,") for c in images))
        self.assertTrue(wire["text"]["format"]["strict"])
        m = self.store.moment(self.ids[6])
        self.assertFalse(self.store.approved(m, "coc"))
        self.assertEqual(m["components"]["coc"]["payload"]["origin"], "MOCK")
        self.assertEqual(self.service.eligibility(m)["state"], "HELD")
        self.assertNotIn("test-secret-never-persist", dumps(self.store.objects("job")))

    def test_future_visit_separation_and_proposal_sources(self):
        self.connect()
        self.run_job(index=9)
        prepare(self.service, self.ids[2])
        candidate = proposal()
        candidate["proposals"][0].update(target_id=None, zone_id=None, executable_parameters=None)
        self.reply = response(candidate)
        job = self.run_job("PROPOSAL", 2)
        self.assertEqual(job["status"], "SUCCEEDED")
        wire = self.sent[-1]
        text = json.loads(wire["input"][0]["content"][0]["text"])
        self.assertEqual(text["task"], "PROPOSAL")
        self.assertEqual(text["data"]["coc"], "현재 관찰")
        self.assertEqual(text["data"]["source"]["records"][0]["quote"], "yield")
        self.assertNotIn("action", text["data"])
        self.assertEqual([f["timestamp_us"] for f in text["frames"]], [0, 1000000, 2000000])
        self.assertFalse(self.store.approved(self.store.moment(self.ids[2]), "proposal"))

    def test_coc_request_separates_scene_description_from_contract_gate(self):
        self.connect()
        for index, count in [(0, 1), (6, 7)]:
            job = self.run_job(index=index)
            self.assertEqual(job["status"], "SUCCEEDED")
            wire = self.sent[-1]
            for identifier in ("pedestrian_conflict", "main_road_yield_required", "ENTER_ZONE", "DEFER_ENTRY"):
                self.assertNotIn(identifier, wire["instructions"])
            request = json.loads(wire["input"][0]["content"][0]["text"])
            self.assertEqual(request["frame_count"], count)
            self.assertEqual(request["observation_window"], "single_frame" if count == 1 else "past_to_current_sequence")
            self.assertNotIn("source", request["data"])
            self.assertEqual(job["inputs"]["prompt_version"], "studio-scene-coc-v3")
            fields = wire["text"]["format"]["schema"]["properties"]
            self.assertTrue(all(fields[k].get("description") for k in coc() if k != "causal_confirmed"))

    def test_error_states_are_durable_without_retry_or_secret_echo(self):
        self.connect({**config(), "max_calls": 20})
        cases = [(TimeoutError("test-secret-never-persist"), "PROVIDER_TIMEOUT"),
                 (StudioError("PROVIDER_AUTH", "test-secret-never-persist"), "PROVIDER_AUTH"),
                 (StudioError("PROVIDER_RATE_LIMIT", "test-secret-never-persist"), "PROVIDER_RATE_LIMIT"),
                 ({**response(), "status": "incomplete"}, "PROVIDER_INCOMPLETE"),
                 ({**response(), "output": [{"type": "message", "content": [{"type": "refusal", "refusal": "no"}]}]}, "PROVIDER_REFUSAL"),
                 ({**response(), "output": [{"type": "message", "content": [{"type": "output_text", "text": "{"}]}]}, "PROVIDER_JSON"),
                 (response({"observations": "missing fields"}), "PROVIDER_SCHEMA"),
                 (response({**coc(), "causal_confirmed": True}), "PROVIDER_SCHEMA"),
                 (response({**coc(), "unknowns": "test-secret-never-persist"}), "PROVIDER_SECRET_ECHO")]
        for reply, code in cases:
            with self.subTest(code=code):
                self.reply = reply
                before = len(self.sent)
                job = self.run_job()
                self.assertIn(job["status"], ("FAILED", "TIMED_OUT"))
                self.assertEqual(job["error"]["code"], code)
                self.assertEqual(len(self.sent), before + 1)
                self.assertNotIn("test-secret-never-persist", dumps(job))
                self.assertFalse(self.store.moment(self.ids[6])["components"])

    def test_budget_survives_restart_and_config_change_stales_job(self):
        self.connect({**config(), "max_calls": 1})
        self.assertEqual(self.run_job()["status"], "SUCCEEDED")
        self.store.close()
        self.store = Store(self.temp.name)
        self.connect({**config(), "max_calls": 1})
        job = self.run_job(index=7)
        self.assertEqual(job["error"]["code"], "PROVIDER_BUDGET")
        self.assertEqual(len(self.sent), 1)
        j = self.service.enqueue(self.ids[8], 0, "COC", "reviewer", uid())
        self.connect({**config(), "model": "another-explicit-model"})
        Worker(self.service).run_once()
        self.assertEqual(self.store.get(j["job_id"], "job")["error"]["code"], "PROVIDER_CONFIG_CHANGED")
        self.assertEqual(len(self.sent), 1)

    def test_unapproved_video_future_manifest_and_stale_job_never_transmit(self):
        self.connect()
        v = self.store.get(self.video, "video")
        v["permission"] = False
        self.store.put("video", v, self.video)
        with self.assertRaises(StudioError):
            self.run_job()
        self.assertFalse(self.sent)
        v["permission"] = True
        self.store.put("video", v, self.video)
        j = self.service.enqueue(self.ids[6], 0, "COC", "reviewer", uid())
        saved = self.store.get(j["job_id"], "job")
        saved["inputs"]["frames"][-1]["timestamp_us"] = 99999999
        self.store.put("job", saved, j["job_id"])
        Worker(self.service).run_once()
        self.assertFalse(self.sent)

    def test_http_boundary_redacts_errors_and_does_not_retry(self):
        from apps.guardsynth_studio import task
        self.assertTrue(hasattr(task, "responses_http"), "Bounded HTTP task is missing")
        from unittest.mock import MagicMock
        for status, code in [(401, "PROVIDER_AUTH"), (403, "PROVIDER_AUTH"),
                             (429, "PROVIDER_RATE_LIMIT"), (500, "PROVIDER_HTTP"), (302, "PROVIDER_HTTP")]:
            conn = MagicMock()
            conn.getresponse.return_value.status = status
            conn.getresponse.return_value.read.return_value = b'test-secret-never-persist'
            with patch("http.client.HTTPSConnection", return_value=conn):
                result = task.responses_http({"body": {}, "timeout_s": 10})
            self.assertEqual(result, {"error_code": code})
            self.assertEqual(conn.request.call_count, 1)
            self.assertEqual(conn.request.call_args.args[:2], ("POST", "/v1/responses"))
            self.assertTrue(conn.close.called)
        conn = MagicMock()
        conn.getresponse.return_value.status = 200
        for raw, code in [(b'{', "PROVIDER_JSON"), (b'x' * 65537, "PROVIDER_RESPONSE_SIZE"),
                          (b'{"echo":"test-secret-never-persist"}', "PROVIDER_SECRET_ECHO")]:
            conn.getresponse.return_value.read.return_value = raw
            with patch("http.client.HTTPSConnection", return_value=conn):
                self.assertEqual(task.responses_http({"body": {}, "timeout_s": 10}), {"error_code": code})

    def test_cli_rejects_reserved_ports_and_default_uses_free_port(self):
        from apps.guardsynth_studio import run
        self.assertTrue(hasattr(run, "valid_port"), "Studio ephemeral port validation missing")
        self.assertTrue(run.valid_port(0))
        self.assertFalse(run.valid_port(8766))
        self.assertFalse(run.valid_port(8877))

    def test_stale_and_cancelled_responses_never_overwrite_review(self):
        from .helpers import edit
        self.connect()
        def delayed(body, timeout):
            edit(self.service, self.ids[6], "coc", {"edited_text": "human correction", "causal_confirmed": False})
            return response()
        self.service.provider.transport = delayed
        job = self.run_job()
        self.assertEqual(job["status"], "STALE_RESULT")
        self.assertEqual(self.store.moment(self.ids[6])["components"]["coc"]["payload"]["edited_text"], "human correction")
        pending = self.service.enqueue(self.ids[7], 0, "COC", "reviewer", uid())
        def cancelled(body, timeout):
            self.service.job_action(pending["job_id"], "cancel", "reviewer", uid())
            return response()
        self.service.provider.transport = cancelled
        Worker(self.service).run_once()
        self.assertEqual(self.store.get(pending["job_id"], "job")["status"], "CANCELLED")
        self.assertFalse(self.store.moment(self.ids[7])["components"])

    def test_secret_in_input_and_changed_permission_before_send_are_blocked(self):
        self.connect()
        prepare(self.service, self.ids[6])
        from .helpers import edit, approve
        edit(self.service, self.ids[6], "coc", {"edited_text": "test-secret-never-persist", "causal_confirmed": True})
        approve(self.service, self.ids[6], "coc")
        job = self.run_job("PROPOSAL")
        self.assertEqual(job["error"]["code"], "PROVIDER_SECRET_INPUT")
        self.assertFalse(self.sent)
        original = self.service.asset_path
        def revoke(asset):
            v = self.store.get(self.video, "video")
            v.update(permission=False, revision=v["revision"] + 1)
            self.store.put("video", v, self.video)
            return original(asset)
        with patch.object(self.service, "asset_path", side_effect=revoke):
            job = self.run_job(index=7)
        self.assertEqual(job["error"]["code"], "PROVIDER_TRANSMISSION_APPROVAL")
        self.assertFalse(self.sent)

    def test_config_cannot_expose_key_as_model(self):
        adapter = provider.configured_provider({**config(), "model": "test-secret-never-persist"})
        self.assertEqual(adapter.mode, "DISABLED")

    def test_encoded_secret_echo_cannot_reach_database_or_export(self):
        self.connect()
        reply = response({**coc(), "unknowns": "test-secret-never-persist"})
        reply["output"][0]["content"][0]["text"] = reply["output"][0]["content"][0]["text"].replace("test-secret", "\\u0074est-secret")
        self.reply = reply
        job = self.run_job()
        self.assertEqual(job["status"], "FAILED")
        self.assertEqual(job["error"]["code"], "PROVIDER_SECRET_ECHO")
        records = list(self.store.db.execute("SELECT data FROM objects"))
        self.assertFalse(any("test-secret-never-persist" in r[0] for r in records))
        export = self.service.export({"mode": "COC_TARGET", "purpose": "DRAFT",
                                      "moments": [{"id": self.ids[6], "revision": 0}]}, "reviewer", uid())
        Worker(self.service).run_once()
        result = self.store.get(export["export_id"], "export")
        for file in result["files"]:
            self.assertNotIn("test-secret-never-persist", (self.store.root / file["relative_path"]).read_text())

    def test_manual_retry_preserves_prior_failure_evidence(self):
        self.connect()
        self.reply = StudioError("PROVIDER_RATE_LIMIT", "untrusted error")
        job = self.run_job()
        self.assertEqual(job["error"]["code"], "PROVIDER_RATE_LIMIT")
        self.service.job_action(self.store.objects("job")[0]["id"], "retry", "reviewer", uid())
        self.reply = response()
        Worker(self.service).run_once()
        history = self.store.objects("provider_error")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["error"]["code"], "PROVIDER_RATE_LIMIT")
        self.assertNotIn("untrusted error", dumps(history))
