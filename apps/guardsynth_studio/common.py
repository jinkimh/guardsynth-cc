"""Small serialization and HTTP error primitives."""

import hashlib
import json
import uuid
from datetime import datetime, timezone


def dumps(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(dumps(value).encode()).hexdigest()


def uid():
    return uuid.uuid4().hex


def now():
    return datetime.now(timezone.utc).isoformat()


class StudioError(ValueError):
    def __init__(self, code, message, status=422):
        super().__init__(message)
        self.code, self.status = code, status

    def record(self):
        return {"code": self.code, "message": str(self), "field_errors": [], "retryable": self.status in (409, 503)}
