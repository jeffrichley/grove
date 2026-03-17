"""Mypy detector: tool from [tool.mypy] or mypy.ini.

Detection rule (evidence-only):
- tools includes "mypy": when [tool.mypy] exists in pyproject.toml, or
  mypy.ini exists in repo root. No inference from other config.
"""

from pathlib import Path

from grove.analyzer.detectors._pyproject import load_pyproject
from grove.analyzer.models import DetectedFact


def detect(repo_root: Path) -> list[DetectedFact]:
    """Return tool=mypy when [tool.mypy] or mypy.ini is present.

    Args:
        repo_root: Path to the project root.

    Returns:
        List of DetectedFact; empty or one fact with key "tools", value ["mypy"].
    """
    if (repo_root / "mypy.ini").is_file():
        return [
            DetectedFact(
                key="tools",
                value=["mypy"],
                evidence="mypy.ini present in repo root",
            )
        ]
    data = load_pyproject(repo_root)
    tool = data.get("tool") if data else None
    if isinstance(tool, dict) and "mypy" in tool:
        return [
            DetectedFact(
                key="tools",
                value=["mypy"],
                evidence="[tool.mypy] in pyproject.toml",
            )
        ]
    return []


class MypyDetector:
    """Detector for mypy ([tool.mypy] or mypy.ini)."""

    def detect(self, repo_root: Path) -> list[DetectedFact]:
        """Return tool=mypy when [tool.mypy] or mypy.ini is present.

        Args:
            repo_root: Path to the project root.

        Returns:
            List of DetectedFact; empty or one fact with key "tools", value ["mypy"].
        """
        return detect(repo_root)
