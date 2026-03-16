"""Pytest detector: test_framework from config or dependencies.

Detection rule (evidence-only):
- test_framework "pytest": when [tool.pytest.ini_options] exists in
  pyproject.toml, OR pytest.ini or pyproject.toml exists in repo root,
  OR "pytest" appears in [project].dependencies or [project].optional-dependencies.
  No inference from test file names or directory layout.
"""

import tomllib
from pathlib import Path

from grove.analyzer.models import DetectedFact


def _specs_from_list(raw: object) -> list[str]:
    """Parse dependency spec strings from a list of strings.

    Args:
        raw: Value from [project].dependencies or a list (e.g. optional-deps).

    Returns:
        List of spec strings (e.g. "pytest>=7" -> "pytest>=7"); empty if not a list.
    """
    if not isinstance(raw, list):
        return []
    return [item.split("[")[0].strip() for item in raw if isinstance(item, str)]


def _specs_from_optional_deps(raw: object) -> list[str]:
    """Parse spec strings from optional-dependencies dict of lists.

    Args:
        raw: Value from [project].optional-dependencies (dict of list of str).

    Returns:
        Concatenated list of spec strings from all optional groups.
    """
    if not isinstance(raw, dict):
        return []
    out: list[str] = []
    for val in raw.values():
        out.extend(_specs_from_list(val))
    return out


def _dep_specs(project: object) -> list[str]:
    """Dependency spec strings from [project].dependencies / optional-dependencies.

    Args:
        project: [project] section from pyproject.toml (dict or other).

    Returns:
        List of dependency spec strings (e.g. "pytest", "ruff[lint]").
    """
    if not isinstance(project, dict):
        return []
    deps = _specs_from_list(project.get("dependencies"))
    opts = _specs_from_optional_deps(project.get("optional-dependencies"))
    return deps + opts


def _pytest_in_deps(project: object) -> bool:
    """Return True if pytest appears in [project] dependencies or optional-deps.

    Args:
        project: [project] section from pyproject.toml.

    Returns:
        True if any dependency spec contains "pytest".
    """
    return any("pytest" in s for s in _dep_specs(project))


def _pytest_fact(evidence: str) -> DetectedFact:
    """Build a test_framework=pytest fact with given evidence.

    Args:
        evidence: Human-readable evidence string.

    Returns:
        DetectedFact with key test_framework, value pytest.
    """
    return DetectedFact(
        key="test_framework",
        value="pytest",
        evidence=evidence,
    )


def detect(repo_root: Path) -> list[DetectedFact]:
    """Return test_framework=pytest when config or deps evidence exists.

    Args:
        repo_root: Path to the project root.

    Returns:
        List of DetectedFact; empty or one fact with key test_framework, value pytest.
    """
    result: list[DetectedFact] = []
    if (repo_root / "pytest.ini").is_file():
        result = [_pytest_fact("pytest.ini present in repo root")]
    elif (repo_root / "pyproject.toml").is_file():
        path = repo_root / "pyproject.toml"
        try:
            with path.open("rb") as f:
                data = tomllib.load(f)
        except (OSError, ValueError):
            pass
        else:
            if isinstance(data, dict):
                tool = data.get("tool")
                # TOML [tool.pytest.ini_options] → tool["pytest"]["ini_options"]
                pytest_tool = isinstance(tool, dict) and tool.get("pytest")
                if isinstance(pytest_tool, dict) and "ini_options" in pytest_tool:
                    result = [
                        _pytest_fact("[tool.pytest.ini_options] in pyproject.toml")
                    ]
                elif _pytest_in_deps(data.get("project")):
                    result = [
                        _pytest_fact(
                            "pytest in [project].dependencies or optional-deps"
                        )
                    ]
    return result


class PytestDetector:
    """Detector for pytest ([tool.pytest.ini_options], deps, or pytest.ini)."""

    def detect(self, repo_root: Path) -> list[DetectedFact]:
        """Return test_framework=pytest when config or deps evidence exists.

        Args:
            repo_root: Path to the project root.

        Returns:
            List of DetectedFact; empty or one fact (test_framework=pytest).
        """
        return detect(repo_root)
