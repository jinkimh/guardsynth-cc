import json
from functools import partial
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import unittest

from apps.research_portal.artifact_registry import ArtifactRegistry
from apps.research_portal.review_backend import ReviewBackend
from apps.research_portal.review_store import ReviewStore
from apps.research_portal.run import ROOT, _LiveTrackingHandler, build_portal
from apps.research_portal.security import LoginRateLimiter, SessionStore, hash_secret


class PortalHttpIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        base = Path(cls.directory.name)
        cls.output = base / "portal"
        build_portal(cls.output)
        cls.store = ReviewStore.create(
            base / "round.sqlite3",
            owner_project_id="guardsynth-coc",
            classification="RESTRICTED",
        )
        portal_data = json.loads((cls.output / "PORTAL_DATA.json").read_text(encoding="utf-8"))
        secret = "http-fixture-secret-01"
        handler = partial(
            _LiveTrackingHandler,
            directory=str(cls.output),
            portal_data=portal_data,
            review_backend=ReviewBackend(cls.store, lead_actor_ids={"research-lead"}),
            auth_records={"research-lead": hash_secret(secret)},
            auth_roles={"research-lead": {"RESEARCH_LEAD"}},
            sessions=SessionStore(),
            login_limiter=LoginRateLimiter(),
            artifact_service=ArtifactRegistry(ROOT),
        )
        cls.secret = secret
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.store.close()
        cls.directory.cleanup()

    def request(self, method, path, *, body=None, headers=None):
        connection = HTTPConnection("127.0.0.1", self.server.server_port, timeout=10)
        encoded = json.dumps(body).encode() if body is not None else None
        request_headers = dict(headers or {})
        if encoded is not None:
            request_headers["Content-Type"] = "application/json"
        connection.request(method, path, body=encoded, headers=request_headers)
        response = connection.getresponse()
        raw = response.read()
        result = response.status, dict(response.getheaders()), raw
        connection.close()
        return result

    def test_login_csrf_round_authorization_csp_and_artifact_classification(self):
        status, headers, raw = self.request("GET", "/api/artifacts")
        self.assertEqual(status, 200)
        self.assertIn("object-src 'none'", headers["Content-Security-Policy"])
        public = json.loads(raw)["artifacts"]
        self.assertTrue(public)
        self.assertFalse(any(item["classification"] in {"restricted", "intermediate"} for item in public))

        status, headers, raw = self.request("POST", "/api/login", body={
            "actor_id": "research-lead",
            "secret": self.secret,
        })
        self.assertEqual(status, 200)
        login = json.loads(raw)
        self.assertEqual(login["roles"], ["RESEARCH_LEAD"])
        self.assertIn("HttpOnly", headers["Set-Cookie"])
        self.assertIn("SameSite=Strict", headers["Set-Cookie"])
        cookie = headers["Set-Cookie"].split(";", 1)[0]

        round_body = {
            "review_round_id": "http-round-001",
            "review_type": "PAPER_INTERNAL_CLAIM_REVIEW",
            "purpose": "HTTP boundary integration fixture",
        }
        status, _, _ = self.request(
            "POST", "/api/rounds", body=round_body, headers={"Cookie": cookie}
        )
        self.assertEqual(status, 403)
        status, _, raw = self.request(
            "POST",
            "/api/rounds",
            body=round_body,
            headers={"Cookie": cookie, "X-CSRF-Token": login["csrf_token"]},
        )
        self.assertEqual(status, 201)
        self.assertEqual(json.loads(raw)["state"], "DRAFT")

        status, _, raw = self.request("GET", "/api/rounds", headers={"Cookie": cookie})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw)["rounds"][0]["capability"], "LEAD")

        status, _, raw = self.request("GET", "/api/artifacts", headers={"Cookie": cookie})
        self.assertEqual(status, 200)
        authenticated = json.loads(raw)["artifacts"]
        self.assertTrue(any(item["classification"] != "public" for item in authenticated))

        status, _, _ = self.request("GET", "/", headers={"Host": "research.example"})
        self.assertEqual(status, 421)


if __name__ == "__main__":
    unittest.main()
