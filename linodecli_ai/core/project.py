"""Project manifest helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import yaml

DEFAULT_MANIFEST = "ai.linode.yml"


class ProjectManifestError(RuntimeError):
    """Raised for manifest issues."""


def load_manifest(path: str | None = None) -> Dict:
    manifest_path = Path(path or DEFAULT_MANIFEST)
    if not manifest_path.exists():
        raise ProjectManifestError(f"Project manifest not found: {manifest_path}")
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ProjectManifestError("Project manifest must be a YAML mapping")
    return data
