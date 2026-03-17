"""Ruff detector: tool from [tool.ruff] or .ruff.toml.

Detection rule (evidence-only):
- tools includes "ruff": when [tool.ruff] exists in pyproject.toml, or
  .ruff.toml exists in repo root. No inference from other config.
"""

from pathlib import Path

from grove.analyzer.detectors._pyproject import load_pyproject
from grove.analyzer.models import DetectedFact


def detect(repo_root: Path) -> list[DetectedFact]:
    """Return tool=ruff when [tool.ruff] or .ruff.toml is present.

    Args:
        repo_root: Path to the project root.

    Returns:
        List of DetectedFact; empty or one fact with key "tools", value ["ruff"].
    """
    if (repo_root / ".ruff.toml").is_file():
        return [
            DetectedFact(
                key="tools",
                value=["ruff"],
                evidence=".ruff.toml present in repo root",
            )
        ]
    data = load_pyproject(repo_root)
    tool = data.get("tool") if data else None
    if isinstance(tool, dict) and "ruff" in tool:
        return [
            DetectedFact(
                key="tools",
                value=["ruff"],
                evidence="[tool.ruff] in pyproject.toml",
            )
        ]
    return []


class RuffDetector:
    """Detector for ruff ([tool.ruff] or .ruff.toml)."""

    def detect(self, repo_root: Path) -> list[DetectedFact]:
        """Return tool=ruff when [tool.ruff] or .ruff.toml is present.

        Args:
            repo_root: Path to the project root.

        Returns:
            List of DetectedFact; empty or one fact with key "tools", value ["ruff"].
        """
        return detect(repo_root)
