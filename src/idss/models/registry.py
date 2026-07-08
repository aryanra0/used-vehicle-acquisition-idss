"""Simple versioned model registry: joblib artifact + JSON metadata sidecar."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import joblib

from .. import config


def _paths(name: str, models_dir: Optional[Path]) -> tuple[Path, Path]:
    base = Path(models_dir) if models_dir else config.MODELS_DIR
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{name}.joblib", base / f"{name}.meta.json"


def save_model(
    name: str,
    obj: Any,
    metadata: Optional[dict] = None,
    models_dir: Optional[Path] = None,
) -> Path:
    artifact, meta_path = _paths(name, models_dir)
    joblib.dump(obj, artifact)
    meta = dict(metadata or {})
    meta.update(
        {
            "name": name,
            "artifact": artifact.name,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    meta_path.write_text(json.dumps(meta, indent=2))
    return artifact


def load_model(name: str, models_dir: Optional[Path] = None) -> Any:
    artifact, _ = _paths(name, models_dir)
    if not artifact.exists():
        raise FileNotFoundError(
            f"Model '{name}' not found at {artifact}. Train models first (python -m idss.train)."
        )
    return joblib.load(artifact)


def load_metadata(name: str, models_dir: Optional[Path] = None) -> dict:
    _, meta_path = _paths(name, models_dir)
    if not meta_path.exists():
        return {}
    return json.loads(meta_path.read_text())


def model_exists(name: str, models_dir: Optional[Path] = None) -> bool:
    artifact, _ = _paths(name, models_dir)
    return artifact.exists()
