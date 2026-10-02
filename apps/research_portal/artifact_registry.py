"""Opaque, owner-aware artifact metadata and exact asset resolution."""

from __future__ import annotations

import hashlib
from fnmatch import fnmatch
import json
from pathlib import Path


class ArtifactRegistryError(ValueError):
    pass


_ASSET_MEDIA_TYPES = {
    ".csv": "text/csv; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
    ".pdf": "application/pdf",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _owners(root: Path) -> list[tuple[str, str, Path]]:
    registry = json.loads((root / "PROJECT_REGISTRY.json").read_text(encoding="utf-8"))
    projects = [("PROJECT", entry["id"], (root / entry["artifact_root"]).resolve()) for entry in registry.get("projects", [])]
    platforms = [("PLATFORM", entry["id"], (root / entry["artifact_root"]).resolve()) for entry in registry.get("platforms", [])]
    return [*projects, *platforms]


def classify_artifact_path(root: Path, path: Path) -> tuple[str, str]:
    root = root.resolve()
    candidate = path.resolve()
    for _, owner_id, owner_root in _owners(root):
        try:
            relative = candidate.relative_to(owner_root)
        except ValueError:
            continue
        if not relative.parts or relative.parts[0] not in {"public", "restricted", "intermediate"}:
            raise ArtifactRegistryError(f"artifact has no valid classification: {path}")
        return owner_id, relative.parts[0]
    raise ArtifactRegistryError(f"artifact is outside registered owner roots: {path}")


def _run_label(manifest: dict, manifest_path: Path) -> str:
    for key in ("run_id", "id", "name"):
        value = manifest.get(key)
        if isinstance(value, str) and value:
            return value
    return manifest_path.parent.name


def _load_manifest(path: Path) -> dict:
    if path.is_symlink():
        raise ArtifactRegistryError(f"run manifest cannot be a symlink: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactRegistryError(f"invalid run manifest: {path}") from exc
    if not isinstance(value, dict):
        raise ArtifactRegistryError(f"run manifest must be an object: {path}")
    return value


class ArtifactRegistry:
    """Keep canonical paths private and expose only opaque, hash-bound records."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self._records: dict[str, dict] = {}
        self._discover_owned()
        self._discover_legacy()

    @staticmethod
    def _asset_records(artifact_id: str, run_root: Path) -> tuple[list[dict], dict[str, dict]]:
        public: list[dict] = []
        private: dict[str, dict] = {}
        for path in sorted(run_root.iterdir()):
            media_type = _ASSET_MEDIA_TYPES.get(path.suffix.lower())
            if not media_type or not path.is_file() or path.is_symlink():
                continue
            resolved = path.resolve()
            try:
                resolved.relative_to(run_root.resolve())
            except ValueError as exc:
                raise ArtifactRegistryError(f"asset leaves run root: {path}") from exc
            digest = _sha256(resolved)
            asset_id = "asset-" + hashlib.sha256(f"{artifact_id}\0{path.name}\0{digest}".encode()).hexdigest()[:20]
            client = {
                "asset_id": asset_id,
                "label": path.name,
                "media_type": media_type.split(";", 1)[0],
                "size_bytes": path.stat().st_size,
                "sha256": digest,
            }
            public.append(client)
            private[asset_id] = {**client, "canonical_path": resolved, "response_media_type": media_type}
        return public, private

    def _register(
        self,
        *,
        owner_kind: str,
        owner_id: str,
        classification: str,
        access_classification: str,
        manifest_path: Path,
        opaque_source: str,
    ) -> None:
        manifest = _load_manifest(manifest_path)
        run_root = manifest_path.parent.resolve()
        artifact_id = "art-" + hashlib.sha256(opaque_source.encode()).hexdigest()[:20]
        if artifact_id in self._records:
            raise ArtifactRegistryError(f"duplicate artifact id for {manifest_path}")
        assets, private_assets = self._asset_records(artifact_id, run_root)
        client = {
            "artifact_id": artifact_id,
            "owner_kind": owner_kind,
            "owner_id": owner_id,
            "classification": classification,
            "run_label": _run_label(manifest, manifest_path),
            "experiment_id": str(manifest.get("experiment_id", "")),
            "created_at": str(manifest.get("run_date", manifest.get("created_at", manifest.get("created_at_utc", "")))),
            "claim_scope": str(manifest.get("claim_scope", "")),
            "has_result": (run_root / "RESULT.json").is_file(),
            "has_report": (run_root / "REPORT_KO.md").is_file(),
            "manifest_hash": _sha256(manifest_path),
            "assets": assets,
        }
        self._records[artifact_id] = {
            "client": client,
            "canonical_path": run_root,
            "manifest_path": manifest_path.resolve(),
            "access_classification": access_classification,
            "assets": private_assets,
        }

    def _discover_owned(self) -> None:
        for owner_kind, owner_id, owner_root in _owners(self.root):
            if not owner_root.is_dir():
                continue
            for manifest_path in sorted(owner_root.glob("*/*/*/RUN_MANIFEST.json")):
                actual_owner, classification = classify_artifact_path(self.root, manifest_path)
                if actual_owner != owner_id:
                    raise ArtifactRegistryError(f"artifact owner mismatch: {manifest_path}")
                relative = manifest_path.relative_to(owner_root).as_posix()
                self._register(
                    owner_kind=owner_kind,
                    owner_id=owner_id,
                    classification=classification,
                    access_classification=classification,
                    manifest_path=manifest_path,
                    opaque_source=f"{owner_id}\0{classification}\0{relative}",
                )

    def _discover_legacy(self) -> None:
        ownership_path = self.root / "artifacts/LEGACY_OWNERSHIP.json"
        if not ownership_path.is_file():
            return
        ownership = json.loads(ownership_path.read_text(encoding="utf-8"))
        if ownership.get("immutable") is not True:
            raise ArtifactRegistryError("legacy artifact catalog must be immutable")
        owner_kinds = {owner_id: owner_kind for owner_kind, owner_id, _ in _owners(self.root)}
        for rule in ownership.get("rules", []):
            owner_id = rule["owner"]
            if owner_id not in owner_kinds:
                raise ArtifactRegistryError(f"unknown legacy artifact owner: {owner_id}")
            class_root = (self.root / "artifacts" / rule["class"]).resolve()
            if not class_root.is_dir():
                continue
            access_classification = "intermediate" if rule["class"] == "intermediate" else rule["class"].split("/")[-1]
            for experiment_root in sorted(class_root.iterdir()):
                if not experiment_root.is_dir() or not fnmatch(experiment_root.name, rule["pattern"]):
                    continue
                manifests: list[Path] = []
                for run_root in sorted(path for path in experiment_root.iterdir() if path.is_dir()):
                    candidates = [
                        path for path in (
                            run_root / "RUN_MANIFEST.json",
                            run_root / "EMBEDDED_REVIEW_MANIFEST.json",
                        ) if path.is_file()
                    ]
                    if len(candidates) > 1:
                        candidates = candidates[:1]
                    manifests.extend(candidates)
                for manifest_path in manifests:
                    self._register(
                        owner_kind=owner_kinds[owner_id],
                        owner_id=owner_id,
                        classification="legacy_immutable",
                        access_classification=access_classification,
                        manifest_path=manifest_path,
                        opaque_source=f"legacy\0{owner_id}\0{manifest_path.relative_to(self.root).as_posix()}",
                    )

    def records(self, *, include_restricted: bool = True) -> list[dict]:
        allowed = {"public"}
        if include_restricted:
            allowed.update({"restricted", "intermediate"})
        return [
            dict(record["client"])
            for _, record in sorted(self._records.items())
            if record["access_classification"] in allowed
        ]

    def detail(self, artifact_id: str, *, include_restricted: bool) -> dict:
        record = self._records.get(artifact_id)
        if record is None:
            raise ArtifactRegistryError("unknown artifact id")
        if record["access_classification"] != "public" and not include_restricted:
            raise ArtifactRegistryError("artifact requires restricted access")
        return dict(record["client"])

    def resolve_asset(self, artifact_id: str, asset_id: str, *, include_restricted: bool) -> tuple[Path, str]:
        record = self._records.get(artifact_id)
        if record is None:
            raise ArtifactRegistryError("unknown artifact id")
        if record["access_classification"] != "public" and not include_restricted:
            raise ArtifactRegistryError("artifact requires restricted access")
        asset = record["assets"].get(asset_id)
        if asset is None:
            raise ArtifactRegistryError("unknown asset id")
        path = asset["canonical_path"]
        if path.is_symlink() or not path.is_file():
            raise ArtifactRegistryError("registered asset is no longer a regular file")
        try:
            path.resolve().relative_to(record["canonical_path"])
        except ValueError as exc:
            raise ArtifactRegistryError("registered asset left its run root") from exc
        if _sha256(path) != asset["sha256"]:
            raise ArtifactRegistryError("registered asset hash changed")
        return path, asset["response_media_type"]


def build_artifact_registry(root: Path) -> list[dict]:
    """Compatibility wrapper returning restricted-local client metadata."""
    return ArtifactRegistry(root).records(include_restricted=True)
