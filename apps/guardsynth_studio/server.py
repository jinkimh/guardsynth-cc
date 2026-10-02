"""Authenticated loopback HTTP API and static Studio UI."""

from email import policy
from email.parser import BytesParser
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
from pathlib import Path
from urllib.parse import urlsplit

from apps.research_portal.security import (SessionStore, LoginRateLimiter, verify_secret, validate_auth_config,
                                           validate_loopback_request, validate_route_segment, security_headers, SecurityError)
from .common import StudioError, dumps, digest
from .media import LIMITS

STATIC = Path(__file__).parent / "static"
PREFIX = "/api/studio/v1"


def make_server(service, auth, port=0):
    hashes, roles = validate_auth_config(auth)
    sessions = SessionStore()
    limiter = LoginRateLimiter()
    upload_gate = threading.BoundedSemaphore(1)

    class Handler(BaseHTTPRequestHandler):
        server_version = "GuardSynthStudio"

        def log_message(self, *args):
            pass

        def respond(self, status, value, content_type="application/json", headers=None):
            data = value if isinstance(value, bytes) else dumps(value).encode()
            self.send_response(status)
            for k, v in security_headers(legacy_review=False).items():
                self.send_header(k, v)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            for k, v in (headers or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(data)

        def session(self, write=False):
            cookie = SimpleCookie(self.headers.get("Cookie", ""))
            sid = cookie.get("studio_session")
            if not sid:
                raise StudioError("AUTH", "Login required", 401)
            token = self.headers.get("X-CSRF-Token") if write else None
            if write and not token:
                raise StudioError("CSRF", "CSRF token required", 403)
            return sessions.require(sid.value, token)

        def read_body(self, upload=False):
            try:
                size = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                raise StudioError("LENGTH", "Invalid Content-Length", 400)
            maximum = LIMITS["upload_bytes"] + 65536 if upload else LIMITS["payload_bytes"]
            if size < 0 or size > maximum or self.headers.get("Transfer-Encoding"):
                raise StudioError("BODY_SIZE", "Request exceeds body limit", 413)
            self.connection.settimeout(120)
            data = self.rfile.read(size)
            if len(data) != size:
                raise StudioError("BODY", "Incomplete body", 400)
            return data

        def handle_request(self):
            try:
                validate_loopback_request(self.headers.get("Host", ""), self.headers.get("Origin"), self.server.server_port)
                path = urlsplit(self.path).path
                method = self.command
                if method == "GET" and path in ("/", "/manual.html", "/app.js", "/style.css"):
                    name, mime = {"/": ("index.html", "text/html; charset=utf-8"), "/manual.html": ("manual.html", "text/html; charset=utf-8"), "/app.js": ("app.js", "text/javascript"), "/style.css": ("style.css", "text/css")}[path]
                    return self.respond(200, (STATIC / name).read_bytes(), mime)
                if path == PREFIX + "/login" and method == "POST":
                    limiter.check(self.client_address[0])
                    data = json.loads(self.read_body())
                    actor = data.get("actor_id", "")
                    if actor not in hashes or not verify_secret(data.get("secret", ""), hashes[actor]):
                        limiter.failure(self.client_address[0])
                        raise StudioError("AUTH", "Invalid login", 401)
                    limiter.success(self.client_address[0])
                    session = sessions.create(actor)
                    return self.respond(200, {"actor_id": actor, "csrf_token": session.csrf_token},
                                        headers={"Set-Cookie": f"studio_session={session.session_id}; HttpOnly; SameSite=Strict; Path=/"})
                session = self.session(method != "GET")
                if not roles[session.actor_id]:
                    raise StudioError("ROLE", "Review role required", 403)
                if path == PREFIX + "/session" and method == "GET":
                    return self.respond(200, {"actor_id": session.actor_id, "csrf_token": session.csrf_token})
                if path == PREFIX + "/logout" and method == "POST":
                    sessions._sessions.pop(session.session_id, None)
                    return self.respond(200, {"logged_out": True}, headers={"Set-Cookie": "studio_session=; Max-Age=0; HttpOnly; SameSite=Strict; Path=/"})
                if not path.startswith(PREFIX + "/"):
                    raise StudioError("ROUTE", "Not found", 404)
                parts = [validate_route_segment(x) for x in path[len(PREFIX) + 1:].split("/")]
                key = self.headers.get("Idempotency-Key", "")
                if method == "POST" and parts == ["videos"]:
                    mime = self.headers.get("Content-Type", "")
                    if not mime.startswith("multipart/form-data;"):
                        raise StudioError("CONTENT_TYPE", "Multipart upload required", 415)
                    if not upload_gate.acquire(blocking=False):
                        raise StudioError("UPLOAD_BUSY", "One upload at a time", 429)
                    try:
                        message = BytesParser(policy=policy.default).parsebytes(("Content-Type: " + mime + "\r\n\r\n").encode() + self.read_body(True))
                        fields = {}
                        for part in message.iter_parts():
                            name = part.get_param("name", header="content-disposition")
                            if name in fields or name not in ("file", "metadata"):
                                raise StudioError("UPLOAD", "Unknown or duplicate form field")
                            fields[name] = part.get_payload(decode=True)
                        if len(fields["metadata"]) > 65536:
                            raise StudioError("METADATA_SIZE", "Metadata exceeds 64 KiB", 413)
                        result = service.upload(fields["file"], json.loads(fields["metadata"]), session.actor_id, key)
                    finally:
                        upload_gate.release()
                    return self.respond(201, result)
                data = json.loads(self.read_body() or b"{}") if method in ("POST", "PATCH") else {}
                with service.store.lock:
                    result = self.dispatch(method, parts, data, session.actor_id, key)
                status = 202 if method == "POST" and ("job_id" in result) else 200
                self.respond(status, result, headers={"ETag": str(result["revision"])} if "revision" in result else None)
            except StudioError as exc:
                self.respond(exc.status, exc.record())
            except SecurityError:
                self.respond(403, {"code": "SECURITY", "message": "Session, origin or route rejected"})
            except (ValueError, KeyError, TypeError, IndexError) as exc:
                self.respond(422, {"code": "INVALID_INPUT", "message": str(exc)[:300]})
            except (TimeoutError, OSError):
                self.respond(503, {"code": "IO", "message": "Storage or request unavailable"})

        def dispatch(self, method, p, data, actor, key):
            s = service.store
            if method == "GET":
                if p == ["capabilities"]:
                    return service.capabilities()
                if p == ["videos"]:
                    return {"videos": s.objects("video"), "extractions": s.objects("extraction"), "lineages": s.objects("lineage")}
                if p == ["jobs"]:
                    return {"jobs": [{k: j.get(k) for k in ("id", "kind", "status", "error", "moment_id")} for j in s.objects("job")]}
                if len(p) == 2 and p[0] in ("jobs", "exports"):
                    return s.get(p[1], "job" if p[0] == "jobs" else "export")
                if len(p) == 2 and p[0] == "moments":
                    m = service.moment(p[1])
                    for c in m["components"].values():
                        c["dependency_digest"] = digest(c["dependencies"])
                    return m
                if len(p) == 3 and p[0] == "extractions" and p[2] == "moments":
                    ms = service.moments(p[1])
                    return {"moments": [{k: m[k] for k in ("id", "ordinal", "t0_us", "revision", "completion", "eligibility")} for m in ms],
                            "review_complete": sum(m["completion"] is not None for m in ms),
                            "training_eligible": sum(m["eligibility"]["state"] != "HELD" for m in ms)}
                if len(p) == 2 and p[0] == "assets":
                    # Handled separately to stream large files.
                    return {"asset": p[1]}
            revision = data.get("revision")
            if method == "PATCH" and len(p) == 2 and p[0] == "moments":
                if self.headers.get("If-Match") != str(revision):
                    raise StudioError("IF_MATCH", "If-Match must match base revision", 409)
                return service.edit(p[1], revision, data["kind"], data["payload"], actor, key, data.get("dependencies", []))
            if method == "POST":
                if p == ["lineages", "merge"]:
                    return service.merge_lineages(data["groups"], data["reason"], actor, key)
                if len(p) == 3 and p[0] == "videos" and p[2] == "permission":
                    return service.video_permission(p[1], revision, data["permission"], actor, key)
                if len(p) == 3 and p[0] == "videos" and p[2] == "extractions":
                    return service.extraction(p[1], data.get("interval_s", 1), actor, key)
                if len(p) == 3 and p[0] == "moments" and p[2] in ("jobs", "complete"):
                    return service.enqueue(p[1], revision, data["type"], actor, key) if p[2] == "jobs" else service.complete(p[1], revision, actor, key)
                if p in (["approvals"], ["approvals", "batch"]):
                    return service.approve(data["items"], actor, key)
                if len(p) == 3 and p[0] == "jobs" and p[2] in ("cancel", "retry"):
                    return service.job_action(p[1], p[2], actor, key)
                if len(p) == 2 and p[0] == "lineages":
                    return service.lineage(p[1], revision, data["split"], data["confirmed"], actor, key)
                if p == ["exports"]:
                    return service.export(data, actor, key)
                if len(p) == 3 and p[0] == "moments" and p[2] == "exposure":
                    def operation():
                        m = s.require_head(p[1], revision)
                        s.put("exposure", {"moment_id": m["id"], "actor": actor, "panel": data["panel"],
                                           "t0_us": m["t0_us"], "extraction_id": m["extraction_id"],
                                           "constraints_visible": any(k in m["components"] for k in ("proposal", "contract", "cnl"))})
                        return m
                    return s.mutate(actor, key, ["exposure", p[1], data], operation)
            raise StudioError("ROUTE", "Not found", 404)

        def do_GET(self):
            path = urlsplit(self.path).path
            if path.startswith(PREFIX + "/assets/"):
                try:
                    validate_loopback_request(self.headers.get("Host", ""), self.headers.get("Origin"), self.server.server_port)
                    session = self.session()
                    if not roles[session.actor_id]:
                        raise StudioError("ROLE", "Review role required", 403)
                    identity = validate_route_segment(path.split("/")[-1])
                    with service.store.lock:
                        file = service.asset_path(identity)
                        asset = service.store.get(identity, "asset")
                    self.respond(200, file.read_bytes(), asset["content_type"])
                except (StudioError, SecurityError) as exc:
                    self.respond(getattr(exc, "status", 403), {"code": "ASSET", "message": "Asset unavailable"})
            else:
                self.handle_request()

        do_POST = handle_request
        do_PATCH = handle_request

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)
