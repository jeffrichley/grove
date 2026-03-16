"""UV detector: package_manager from [tool.uv] or uv.lock.

Detection rule (evidence-only):
- package_manager "uv": when [tool.uv] exists in pyproject.toml, or uv.lock
  is present in repo root. No inference from other lock files.
"""

from pathlib import Path

from grove.analyzer.detectors._pyproject import load_pyproject
from grove.analyzer.models import DetectedFact


def detect(repo_root: Path) -> list[DetectedFact]:
    """Return package_manager=uv when tool.uv or uv.lock is present.

    Args:
        repo_root: Path to the project root.

    Returns:
        List of DetectedFact; empty or one fact with key package_manager, value uv.
    """
    facts: list[DetectedFact] = []
    if (repo_root / "uv.lock").is_file():
        facts.append(
            DetectedFact(
                key="package_manager",
                value="uv",
                evidence="uv.lock present in repo root",
            )
        )
        return facts
    data = load_pyproject(repo_root)
    tool = data.get("tool") if data else None
    if isinstance(tool, dict) and "uv" in tool:
        facts.append(
            DetectedFact(
                key="package_manager",
                value="uv",
                evidence="[tool.uv] in pyproject.toml",
            )
        )
    return facts


class UvDetector:
    """Detector for uv package manager ([tool.uv] or uv.lock)."""

    def detect(self, repo_root: Path) -> list[DetectedFact]:
        """Return package_manager=uv when tool.uv or uv.lock is present.

        Args:
            repo_root: Path to the project root.

        Returns:
            List of DetectedFact; empty or one fact with key package_manager, value uv.
        """
        return detect(repo_root)
