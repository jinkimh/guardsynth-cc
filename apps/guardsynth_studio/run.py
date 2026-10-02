"""Run the independent loopback Studio; provider requires explicit deployment settings."""

import argparse
import fcntl
import getpass
import json
import os
import re

from . import ROOT
from .common import dumps
from .store import Store
from .service import Service
from .jobs import Worker
from .provider import configured_provider
from .server import make_server
from apps.research_portal.security import hash_secret

ARTIFACT_ROOT = ROOT / "artifacts/projects/guardsynth-coc/restricted/guardsynth-studio-001"


def valid_port(port):
    return port == 0 or (1024 <= port <= 65535 and port not in (8766, 8877))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--port", type=int, default=0, help="0 selects an unused loopback port")
    parser.add_argument("--init-auth", action="store_true")
    parser.add_argument("--actor", default="studio-reviewer")
    parser.add_argument("--provider-config", type=str, help="Explicit non-secret JSON deployment config; see README")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.run_id) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.actor):
        parser.error("run-id and actor must be lowercase kebab-case")
    if not valid_port(args.port):
        parser.error("Choose port 0 or an unused unprivileged port; 8766 and 8877 are reserved")
    os.umask(0o077)
    root = ARTIFACT_ROOT / args.run_id
    root.mkdir(parents=True, exist_ok=True)
    if root.resolve().parent != ARTIFACT_ROOT.resolve():
        parser.error("Studio run must remain under its artifact namespace")
    auth_path = root / "auth.json"
    if args.init_auth:
        secret = getpass.getpass("Studio password (12+ characters; not printed): ")
        confirmation = getpass.getpass("Repeat password: ")
        if secret != confirmation:
            parser.error("Passwords differ")
        with auth_path.open("x") as handle:
            handle.write(dumps({"users": [{"actor_id": args.actor, "secret_hash": hash_secret(secret), "roles": ["REVIEWER"]}]}))
        print("Authentication initialized; no server started.")
        return
    if not auth_path.is_file():
        parser.error("Initialize separate Studio authentication with --init-auth first")
    lock = (root / "server.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    store = Store(root)
    config = {"mode": "DISABLED", "model": None}
    if args.provider_config:
        from pathlib import Path
        config = json.loads(Path(args.provider_config).read_text())
    service = Service(store, configured_provider(config))
    server = make_server(service, json.loads(auth_path.read_text()), args.port)
    worker = Worker(service)
    worker.start()
    print(f"GuardSynth Studio: http://127.0.0.1:{server.server_port}/ (VLM {service.provider.mode})", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        worker.stop()
        if not worker.thread or not worker.thread.is_alive():
            store.close()


if __name__ == "__main__":
    main()
