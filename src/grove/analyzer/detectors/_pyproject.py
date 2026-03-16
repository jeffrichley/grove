"""Shared helper: load pyproject.toml as a dict for tool detectors."""

import tomllib
from pathlib import Path


def load_pyproject(repo_root: Path) -> dict[str, object] | None:
    """Load pyproject.toml from repo_root. Returns None if missing or invalid.

    Args:
        repo_root: Path to the project root.

    Returns:
        Parsed TOML as a dict, or None if file missing or invalid.
    """
    path = repo_root / "pyproject.toml"
    if not path.is_file():
        return None
    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None
