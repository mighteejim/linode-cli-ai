"""Environment file helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Tuple


class EnvError(RuntimeError):
    """Base env module error."""


class MissingEnvVarsError(EnvError):
    """Raised when required env vars are missing."""

    def __init__(self, missing: Iterable[str]) -> None:
        names = sorted(set(missing))
        super().__init__(f"Missing environment variables: {', '.join(names)}")
        self.names = names


@dataclass(frozen=True)
class EnvRequirement:
    name: str
    description: str = ""


def load_env_file(path: str) -> Dict[str, str]:
    """Parse KEY=VALUE pairs from a dotenv-style file."""
    env_path = Path(path).expanduser()
    if not env_path.exists():
        raise EnvError(f"Env file not found: {env_path}")

    data: Dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, value = _split_env_line(line)
        data[key] = value
    return data


def ensure_required(env: Dict[str, str], requirements: Iterable[EnvRequirement]) -> None:
    """Raise if any required env var is missing."""
    missing = [req.name for req in requirements if req.name not in env]
    if missing:
        raise MissingEnvVarsError(missing)


def _split_env_line(line: str) -> Tuple[str, str]:
    if "=" not in line:
        raise EnvError(f"Invalid env line: {line}")
    key, value = line.split("=", 1)
    key = key.strip()
    value = value.strip()
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        value = value[1:-1]
    return key, value
