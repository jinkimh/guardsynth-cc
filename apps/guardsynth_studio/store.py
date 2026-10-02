"""Independent SQLite store; immutable revisions, transactional CAS and receipts."""

from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import threading

from .common import StudioError, digest, dumps, now, uid

DEPENDENCIES = {
    "coc": (), "source": (), "binding": (), "action": (),
    "proposal": ("coc", "source", "binding"),
    "contract": ("proposal", "source", "binding"),
    "check": ("contract", "binding", "source"),
    "cnl": ("contract", "check", "binding"),
    "combined": ("coc", "cnl", "action"),
    "applicability": ("proposal", "source", "binding"),
    "context": ("coc", "action"), "derived": ("cnl",),
}
EDITABLE = set(DEPENDENCIES) - {"check", "cnl", "combined"}


class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(self.root / "studio.sqlite3", check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            PRAGMA foreign_keys=ON;
            PRAGMA journal_mode=WAL;
            PRAGMA synchronous=FULL;
            CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS objects(id TEXT PRIMARY KEY, kind TEXT NOT NULL, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS moments(id TEXT PRIMARY KEY, extraction TEXT NOT NULL,
                ordinal INTEGER NOT NULL, head INTEGER NOT NULL, UNIQUE(extraction, ordinal));
            CREATE TABLE IF NOT EXISTS revisions(moment TEXT NOT NULL REFERENCES moments(id),
                revision INTEGER NOT NULL, data TEXT NOT NULL, actor TEXT NOT NULL, created TEXT NOT NULL,
                PRIMARY KEY(moment, revision));
            CREATE TABLE IF NOT EXISTS receipts(actor TEXT NOT NULL, key TEXT NOT NULL,
                request_hash TEXT NOT NULL, response TEXT NOT NULL, PRIMARY KEY(actor,key));
            CREATE TABLE IF NOT EXISTS audit(id TEXT PRIMARY KEY, data TEXT NOT NULL);
        """)
        existing = self.db.execute("SELECT value FROM metadata WHERE key='owner'").fetchone()
        if existing and existing[0] != "guardsynth-coc/guardsynth-studio/v1":
            raise StudioError("OWNER", "Not a Studio database")
        self.db.execute("INSERT OR IGNORE INTO metadata VALUES('owner',?)", ("guardsynth-coc/guardsynth-studio/v1",))

    @contextmanager
    def transaction(self):
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                yield
                self.db.execute("COMMIT")
            except BaseException:
                self.db.execute("ROLLBACK")
                raise

    def close(self):
        self.db.close()

    def put(self, kind, value, identity=None):
        identity = identity or uid()
        self.db.execute("INSERT INTO objects VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data",
                        (identity, kind, dumps(value)))
        return identity

    def get(self, identity, kind=None):
        row = self.db.execute("SELECT * FROM objects WHERE id=?", (identity,)).fetchone()
        if not row or (kind and row["kind"] != kind):
            raise StudioError("NOT_FOUND", "Object not found", 404)
        return json.loads(row["data"])

    def objects(self, kind):
        return [{"id": r["id"], **json.loads(r["data"])} for r in
                self.db.execute("SELECT * FROM objects WHERE kind=? ORDER BY rowid", (kind,))]

    def mutate(self, actor, key, request, operation):
        if not isinstance(key, str) or not 8 <= len(key) <= 128:
            raise StudioError("IDEMPOTENCY", "Idempotency-Key required")
        hashed = digest(request)
        with self.transaction():
            previous = self.db.execute("SELECT * FROM receipts WHERE actor=? AND key=?", (actor, key)).fetchone()
            if previous:
                if previous["request_hash"] != hashed:
                    raise StudioError("IDEMPOTENCY_CONFLICT", "Key reused with different input", 409)
                return json.loads(previous["response"])
            result = operation()
            self.db.execute("INSERT INTO receipts VALUES(?,?,?,?)", (actor, key, hashed, dumps(result)))
            return result

    def create_moment(self, extraction, ordinal, frame):
        identity = uid()
        self.db.execute("INSERT INTO moments VALUES(?,?,?,0)", (identity, extraction, ordinal))
        value = {"studio_schema_version": 1, "id": identity, "extraction_id": extraction,
                 "ordinal": ordinal, "t0_us": frame["timestamp_us"], "frame": frame,
                 "revision": 0, "components": {}, "approvals": {}, "completion": None, "exposures": []}
        self.db.execute("INSERT INTO revisions VALUES(?,?,?,?,?)", (identity, 0, dumps(value), "system", now()))
        return identity

    def moment(self, identity, revision=None):
        head = self.db.execute("SELECT head FROM moments WHERE id=?", (identity,)).fetchone()
        if head is None:
            raise StudioError("NOT_FOUND", "Moment not found", 404)
        revision = head[0] if revision is None else revision
        row = self.db.execute("SELECT data FROM revisions WHERE moment=? AND revision=?", (identity, revision)).fetchone()
        if row is None:
            raise StudioError("NOT_FOUND", "Revision not found", 404)
        return json.loads(row[0])

    def require_head(self, identity, expected):
        value = self.moment(identity)
        if type(expected) is not int or value["revision"] != expected:
            raise StudioError("REVISION_CONFLICT", f"Current revision: {value['revision']}", 409)
        return value

    def save(self, value, actor):
        value = deepcopy(value)
        base = value["revision"]
        value["revision"] += 1
        changed = self.db.execute("UPDATE moments SET head=? WHERE id=? AND head=?",
                                  (value["revision"], value["id"], base)).rowcount
        if changed != 1:
            raise StudioError("REVISION_CONFLICT", "Concurrent update", 409)
        self.db.execute("INSERT INTO revisions VALUES(?,?,?,?,?)",
                        (value["id"], value["revision"], dumps(value), actor, now()))
        return value

    def install(self, value, kind, payload, extra_dependencies=()):
        components = value["components"]
        deps = set(DEPENDENCIES[kind]) | set(extra_dependencies)
        if not deps.issubset(DEPENDENCIES) or kind in deps:
            raise StudioError("DEPENDENCY", "Invalid dependency")
        refs = {d: components[d]["id"] if d in components else None for d in sorted(deps)}
        pending, ancestors = list(deps), set()
        while pending:
            parent = pending.pop()
            if parent == kind:
                raise StudioError("DEPENDENCY_CYCLE", "Dependency cycle is not allowed")
            if parent not in ancestors:
                ancestors.add(parent)
                pending.extend(components.get(parent, {}).get("dependencies", {}))
        component = {"id": uid(), "kind": kind, "payload": deepcopy(payload), "hash": digest(payload),
                     "dependencies": refs, "stale": False}
        components[kind] = component
        value["approvals"].pop(kind, None)
        changed = {kind}
        while True:
            more = {k for k, c in components.items() if k not in changed and set(c["dependencies"]) & changed}
            if not more:
                break
            for k in more:
                components[k]["stale"] = True
            changed |= more
        value["completion"] = None
        return component

    def approved(self, value, kind):
        c = value["components"].get(kind)
        a = value["approvals"].get(kind)
        return bool(c and not c["stale"] and a and a["decision"] == "APPROVE" and
                    a["component_id"] == c["id"] and a["dependency_digest"] == digest(c["dependencies"]))

    def record_approval(self, value, kind, decision, actor, note=""):
        c = value["components"].get(kind)
        if not c or c["stale"]:
            raise StudioError("STALE", "Missing or stale component", 409)
        record = {"approval_id": uid(), "moment_id": value["id"], "stage": kind,
                  "component_id": c["id"], "hash": c["hash"], "dependency_digest": digest(c["dependencies"]),
                  "decision": decision, "actor_id": actor, "server_time": now(), "note": note,
                  "exposure": deepcopy(value["exposures"])}
        value["approvals"][kind] = record
        self.db.execute("INSERT INTO audit VALUES(?,?)", (record["approval_id"], dumps(record)))
        value["completion"] = None
        if decision != "APPROVE":
            changed = {kind}
            while True:
                more = {k for k, c in value["components"].items() if k not in changed and set(c["dependencies"]) & changed}
                if not more:
                    break
                for k in more:
                    value["components"][k]["stale"] = True
                changed |= more
        return record
