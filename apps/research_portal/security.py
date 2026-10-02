"""Loopback portal authentication and HTTP boundary primitives."""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
import time
from dataclasses import dataclass
from urllib.parse import unquote, urlsplit


class SecurityError(ValueError):
    pass


OUTER_CSP = (
    "default-src 'self'; connect-src 'self'; img-src 'self' data: blob:; "
    "style-src 'self'; script-src 'self'; frame-src 'self'; object-src 'none'; "
    "base-uri 'none'; form-action 'self'; frame-ancestors 'self'"
)
LEGACY_REVIEW_CSP = (
    "default-src 'none'; img-src data: blob:; style-src 'unsafe-inline'; "
    "script-src 'unsafe-inline'; connect-src 'none'; object-src 'none'; "
    "base-uri 'none'; form-action 'none'; frame-ancestors 'self'"
)
GLOBAL_ROLES = {"RESEARCH_LEAD", "REVIEWER"}


def validate_auth_config(value: object) -> tuple[dict[str, str], dict[str, set[str]]]:
    if not isinstance(value, dict) or set(value) != {"users"} or not isinstance(value["users"], list):
        raise SecurityError("auth config must contain only a users list")
    if not 1 <= len(value["users"]) <= 100:
        raise SecurityError("auth config user count is invalid")
    hashes: dict[str, str] = {}
    roles: dict[str, set[str]] = {}
    for user in value["users"]:
        if not isinstance(user, dict) or set(user) != {"actor_id", "secret_hash", "roles"}:
            raise SecurityError("auth user fields do not match the contract")
        actor_id = user["actor_id"]
        encoded = user["secret_hash"]
        raw_roles = user["roles"]
        if not isinstance(actor_id, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", actor_id):
            raise SecurityError("auth actor_id must be opaque kebab-case")
        if actor_id in hashes:
            raise SecurityError("duplicate auth actor_id")
        if not isinstance(encoded, str) or not re.fullmatch(r"scrypt\$16384\$8\$1\$[^$]+\$[^$]+", encoded):
            raise SecurityError("auth secret_hash is not an approved scrypt encoding")
        if not isinstance(raw_roles, list) or not set(raw_roles).issubset(GLOBAL_ROLES):
            raise SecurityError("auth user has an unsupported global role")
        hashes[actor_id] = encoded
        roles[actor_id] = set(raw_roles)
    return hashes, roles


def hash_secret(secret: str) -> str:
    if not isinstance(secret, str) or len(secret) < 12:
        raise SecurityError("secret must contain at least 12 characters")
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(secret.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return "scrypt$16384$8$1$" + base64.urlsafe_b64encode(salt).decode() + "$" + base64.urlsafe_b64encode(digest).decode()


def verify_secret(secret: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt_text, digest_text = encoded.split("$")
        if algorithm != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(salt_text.encode())
        expected = base64.urlsafe_b64decode(digest_text.encode())
        actual = hashlib.scrypt(secret.encode(), salt=salt, n=int(n), r=int(r), p=int(p), dklen=len(expected))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def validate_loopback_request(host: str, origin: str | None, port: int) -> None:
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    if host not in allowed_hosts:
        raise SecurityError("request host is not loopback")
    if origin:
        parsed = urlsplit(origin)
        if parsed.scheme not in {"http", "https"} or parsed.netloc not in allowed_hosts:
            raise SecurityError("request origin is not loopback")


def validate_route_segment(raw: str) -> str:
    value = raw
    for _ in range(2):
        decoded = unquote(value)
        if decoded == value:
            break
        value = decoded
    if not value or value in {".", ".."} or "\x00" in value or "/" in value or "\\" in value:
        raise SecurityError("unsafe route segment")
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,127}", value):
        raise SecurityError("invalid route segment")
    return value


def security_headers(*, legacy_review: bool) -> dict[str, str]:
    return {
        "Content-Security-Policy": LEGACY_REVIEW_CSP if legacy_review else OUTER_CSP,
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "Cache-Control": "no-store",
        "X-Frame-Options": "SAMEORIGIN",
    }


@dataclass(frozen=True)
class Session:
    session_id: str
    actor_id: str
    csrf_token: str
    created_at: float
    last_seen_at: float


class SessionStore:
    def __init__(self, *, idle_timeout: int = 1800, absolute_timeout: int = 28800):
        self.idle_timeout = idle_timeout
        self.absolute_timeout = absolute_timeout
        self._sessions: dict[str, Session] = {}

    def create(self, actor_id: str, now: float | None = None) -> Session:
        timestamp = time.time() if now is None else now
        session = Session(secrets.token_urlsafe(32), actor_id, secrets.token_urlsafe(32), timestamp, timestamp)
        self._sessions[session.session_id] = session
        return session

    def require(self, session_id: str, csrf_token: str | None = None, now: float | None = None) -> Session:
        timestamp = time.time() if now is None else now
        session = self._sessions.get(session_id)
        if session is None or timestamp - session.last_seen_at > self.idle_timeout or timestamp - session.created_at > self.absolute_timeout:
            self._sessions.pop(session_id, None)
            raise SecurityError("session is not valid")
        if csrf_token is not None and not hmac.compare_digest(csrf_token, session.csrf_token):
            raise SecurityError("csrf token is not valid")
        refreshed = Session(session.session_id, session.actor_id, session.csrf_token, session.created_at, timestamp)
        self._sessions[session_id] = refreshed
        return refreshed


class LoginRateLimiter:
    def __init__(self, *, max_attempts: int = 5, window_seconds: int = 300):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, list[float]] = {}

    def check(self, key: str, now: float | None = None) -> None:
        timestamp = time.time() if now is None else now
        recent = [item for item in self._attempts.get(key, []) if timestamp - item < self.window_seconds]
        self._attempts[key] = recent
        if len(recent) >= self.max_attempts:
            raise SecurityError("login temporarily unavailable")

    def failure(self, key: str, now: float | None = None) -> None:
        timestamp = time.time() if now is None else now
        self._attempts.setdefault(key, []).append(timestamp)

    def success(self, key: str) -> None:
        self._attempts.pop(key, None)
