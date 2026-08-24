"""A tiny versioned model registry — save/load the winning anomaly model.

Each `save` writes a new `vN/` directory under the registry root containing the
pickled artifact (model + feature pipeline + standardizer + threshold) plus
`metrics.json` and `meta.json`. Versions auto-increment, so promoting a new
model never overwrites an old one and any version can be reloaded for serving.
"""
from __future__ import annotations

import json
import pickle
import time
from pathlib import Path

DEFAULT_ROOT = "artifacts/anomaly/registry"


def _versions(root: Path) -> list[int]:
    return sorted(
        int(p.name[1:]) for p in root.glob("v*")
        if p.is_dir() and p.name[1:].isdigit()
    )


def save_model(
    artifact: dict, metrics: dict, meta: dict, root: str = DEFAULT_ROOT
) -> int:
    """Persist a new model version. `artifact` must be picklable. Returns the version."""
    base = Path(root)
    base.mkdir(parents=True, exist_ok=True)
    versions = _versions(base)
    version = (versions[-1] + 1) if versions else 1
    vdir = base / f"v{version}"
    vdir.mkdir()

    with (vdir / "model.pkl").open("wb") as f:
        pickle.dump(artifact, f)
    (vdir / "metrics.json").write_text(json.dumps(metrics, indent=2))
    (vdir / "meta.json").write_text(
        json.dumps({**meta, "version": version, "created": time.time()}, indent=2)
    )
    return version


def latest_version(root: str = DEFAULT_ROOT) -> int | None:
    versions = _versions(Path(root))
    return versions[-1] if versions else None


def load_model(root: str = DEFAULT_ROOT, version: int | None = None) -> dict:
    """Load a version's artifact + metrics + meta. Defaults to the latest."""
    base = Path(root)
    if version is None:
        version = latest_version(root)
    if version is None:
        raise FileNotFoundError(f"no models in registry at {root}")
    vdir = base / f"v{version}"
    with (vdir / "model.pkl").open("rb") as f:
        artifact = pickle.load(f)
    return {
        "artifact": artifact,
        "metrics": json.loads((vdir / "metrics.json").read_text()),
        "meta": json.loads((vdir / "meta.json").read_text()),
        "version": version,
    }
