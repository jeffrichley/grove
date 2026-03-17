"""Pyproject detector: project name and language from pyproject.toml.

Detection rule (evidence-only):
- project_name: [project].name when present (string).
- language "python": when [project] exists and either requires-python is set
  or [build-system].build-backend is present (Python project). No inference
  from directory name or other heuristics.
"""

import tomllib
from pathlib import Path

from grove.analyzer.models import DetectedFact


def _facts_from_project(project: object) -> list[DetectedFact]:
    """Extract project_name and language facts from [project] section.

    Args:
        project: [project] section from pyproject.toml (dict or other).

    Returns:
        List of DetectedFact for project_name and/or language when present.
    """
    facts: list[DetectedFact] = []
    if not isinstance(project, dict):
        return facts
    name = project.get("name")
    if name is not None and isinstance(name, str) and name.strip():
        facts.append(
            DetectedFact(
                key="project_name",
                value=name.strip(),
                evidence="[project].name in pyproject.toml",
            )
        )
    if project.get("requires-python") is not None:
        facts.append(
            DetectedFact(
                key="language",
                value="python",
                evidence="[project].requires-python in pyproject.toml",
            )
        )
    return facts


def _language_from_build_system(
    data: dict[str, object], already_have_language: bool
) -> list[DetectedFact]:
    """One language fact from [build-system] if not already set.

    Args:
        data: Full pyproject.toml data dict.
        already_have_language: If True, returns [].

    Returns:
        List with one language=python fact, or [].
    """
    if already_have_language:
        return []
    build = data.get("build-system")
    if not isinstance(build, dict) or not build.get("build-backend"):
        return []
    return [
        DetectedFact(
            key="language",
            value="python",
            evidence="[build-system].build-backend in pyproject.toml",
        )
    ]


def detect(repo_root: Path) -> list[DetectedFact]:
    """Return project_name and/or language from pyproject.toml if present.

    Args:
        repo_root: Path to the project root.

    Returns:
        List of DetectedFact for project_name and/or language when present.
    """
    path = repo_root / "pyproject.toml"
    if not path.is_file():
        return []
    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except (OSError, ValueError):
        return []
    if not isinstance(data, dict):
        return []

    facts = _facts_from_project(data.get("project"))
    facts.extend(
        _language_from_build_system(data, any(f.key == "language" for f in facts))
    )
    return facts


class PyprojectDetector:
    """Detector for [project] and [build-system] in pyproject.toml."""

    def detect(self, repo_root: Path) -> list[DetectedFact]:
        """Return project_name and/or language from pyproject.toml if present.

        Args:
            repo_root: Path to the project root.

        Returns:
            List of DetectedFact for project_name and/or language when present.
        """
        return detect(repo_root)
