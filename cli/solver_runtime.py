"""Resolve a reproducible project-local solver runtime for CLI pipelines."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import importlib
import os
from pathlib import Path
import sys


DEFAULT_Z3_PREFIX = "runtime/solvers/z3-5.0.0-x86_64-glibc-2.36"
EXPECTED_Z3_VERSION = "5.0.0"


@dataclass(frozen=True, slots=True)
class Z3Runtime:
    version: str
    module_path: str
    prefix: str
    python_site_packages: str
    source: str

    def manifest(self) -> dict[str, str]:
        return asdict(self)


def _prepend_environment_path(name: str, path: Path) -> None:
    value = str(path)
    existing = os.environ.get(name, "")
    entries = [item for item in existing.split(os.pathsep) if item]
    if value in entries:
        entries.remove(value)
    os.environ[name] = os.pathsep.join([value, *entries])


def _python_site_packages(prefix: Path) -> Path:
    candidates = sorted(
        path
        for path in (prefix / "lib").glob("python*/site-packages")
        if (path / "z3/__init__.py").is_file()
    )
    if not candidates:
        raise FileNotFoundError(
            f"project-local Z3 Python package not found below {prefix / 'lib'}"
        )
    return candidates[-1]


def _manifest_path(project_root: Path, path: Path) -> str:
    """Return a portable path without exposing a user-specific workspace root."""

    try:
        return path.relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return "EXTERNAL_GUARDSYNTH_Z3_PREFIX"


def configure_project_z3(
    project_root: Path,
    *,
    expected_version: str = EXPECTED_Z3_VERSION,
) -> Z3Runtime:
    """Select the isolated Z3 build before any EBLC module imports ``z3``.

    ``GUARDSYNTH_Z3_PREFIX`` may override the repository-relative default.
    An already imported solver from another prefix is rejected because Python
    cannot safely replace a loaded native library in the current process.
    """

    configured = os.environ.get("GUARDSYNTH_Z3_PREFIX")
    prefix = (
        Path(configured).expanduser().resolve()
        if configured
        else (project_root / DEFAULT_Z3_PREFIX).resolve()
    )
    executable = prefix / "bin/z3"
    library_dir = prefix / "lib"
    if not executable.is_file() or not (library_dir / "libz3.so").is_file():
        raise FileNotFoundError(f"incomplete project-local Z3 installation: {prefix}")

    site_packages = _python_site_packages(prefix)
    loaded = sys.modules.get("z3")
    if loaded is not None:
        loaded_version = loaded.get_version_string()
        loaded_path = Path(loaded.__file__).resolve()
        if loaded_version != expected_version or site_packages not in loaded_path.parents:
            raise RuntimeError(
                "a different Z3 runtime was imported before EBLC configuration: "
                f"version={loaded_version}, module={loaded_path}; expected "
                f"version={expected_version} below {site_packages}"
            )
    else:
        site_value = str(site_packages)
        if site_value in sys.path:
            sys.path.remove(site_value)
        sys.path.insert(0, site_value)
        _prepend_environment_path("PYTHONPATH", site_packages)
        _prepend_environment_path("LD_LIBRARY_PATH", library_dir)
        _prepend_environment_path("PATH", prefix / "bin")
        importlib.invalidate_caches()
        loaded = importlib.import_module("z3")

    version = loaded.get_version_string()
    module_path = Path(loaded.__file__).resolve()
    if version != expected_version:
        raise RuntimeError(f"Z3 version mismatch: expected {expected_version}, got {version}")
    if site_packages not in module_path.parents:
        raise RuntimeError(
            f"Z3 module was not loaded from the project-local prefix: {module_path}"
        )

    return Z3Runtime(
        version=version,
        module_path=_manifest_path(project_root, module_path),
        prefix=_manifest_path(project_root, prefix),
        python_site_packages=_manifest_path(project_root, site_packages),
        source="PROJECT_LOCAL_ISOLATED_BUILD",
    )
