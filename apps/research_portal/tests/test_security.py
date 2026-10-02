import unittest

from apps.research_portal.security import (
    SecurityError,
    LoginRateLimiter,
    SessionStore,
    hash_secret,
    security_headers,
    validate_loopback_request,
    validate_auth_config,
    validate_route_segment,
    verify_secret,
)


class SecurityTest(unittest.TestCase):
    def test_scrypt_secret_round_trip_and_no_plaintext_storage(self):
        encoded = hash_secret("correct horse battery staple")

        self.assertNotIn("correct horse battery staple", encoded)
        self.assertTrue(verify_secret("correct horse battery staple", encoded))
        self.assertFalse(verify_secret("wrong", encoded))

    def test_only_loopback_host_and_origin_are_allowed(self):
        validate_loopback_request("127.0.0.1:8765", "http://localhost:8765", 8765)
        with self.assertRaises(SecurityError):
            validate_loopback_request("research.example:8765", "http://research.example:8765", 8765)

    def test_route_segments_reject_traversal_and_separators(self):
        self.assertEqual(validate_route_segment("art-a012bc"), "art-a012bc")
        for value in ("..", "%2e%2e", "a/b", "a%2fb", "a\\b", "\x00"):
            with self.assertRaises(SecurityError):
                validate_route_segment(value)

    def test_outer_headers_include_csp_and_nosniff(self):
        headers = security_headers(legacy_review=False)

        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("object-src 'none'", headers["Content-Security-Policy"])
        self.assertIn("frame-ancestors 'self'", headers["Content-Security-Policy"])

    def test_session_csrf_and_login_rate_limit_fail_closed(self):
        sessions = SessionStore(idle_timeout=10, absolute_timeout=20)
        session = sessions.create("reviewer-a", now=100)
        with self.assertRaises(SecurityError):
            sessions.require(session.session_id, "wrong-token", now=101)

        limiter = LoginRateLimiter(max_attempts=2, window_seconds=10)
        limiter.failure("loopback", now=100)
        limiter.failure("loopback", now=101)
        with self.assertRaises(SecurityError):
            limiter.check("loopback", now=102)
        limiter.check("loopback", now=112)

    def test_auth_config_allows_only_hashes_and_known_global_roles(self):
        secret_hash = hash_secret("correct horse battery staple")
        hashes, roles = validate_auth_config({
            "users": [{"actor_id": "research-lead", "secret_hash": secret_hash, "roles": ["RESEARCH_LEAD"]}]
        })
        self.assertEqual(hashes["research-lead"], secret_hash)
        self.assertEqual(roles["research-lead"], {"RESEARCH_LEAD"})
        with self.assertRaises(SecurityError):
            validate_auth_config({"users": [{"actor_id": "lead", "secret": "plaintext", "roles": []}]})


if __name__ == "__main__":
    unittest.main()
