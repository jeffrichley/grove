"""Analyzer engine: run detectors and merge results into a single ProjectProfile."""

from pathlib import Path

from grove.analyzer.detectors import (
    MypyDetector,
    PyprojectDetector,
    PytestDetector,
    RuffDetector,
    UvDetector,
)
from grove.analyzer.detectors.base import DetectorProtocol
from grove.analyzer.models import DetectedFact
from grove.core.models import ProjectProfile


def analyze(repo_root: Path) -> ProjectProfile:
    """Run all detectors on repo_root and return a single ProjectProfile.

    No mutation of the repo; no network calls. Optional fields are set only
    when detectors produce evidence (evidence-only, non-brittle).

    Args:
        repo_root: Path to the project root (e.g. where pyproject.toml lives).

    Returns:
        A single ProjectProfile merging all detector facts.
    """
    repo_root = repo_root.resolve()
    detectors: list[DetectorProtocol] = [
        PyprojectDetector(),
        UvDetector(),
        PytestDetector(),
        RuffDetector(),
        MypyDetector(),
    ]
    facts: list[DetectedFact] = []
    for det in detectors:
        facts.extend(det.detect(repo_root))

    return _facts_to_profile(repo_root, facts)


_STR_KEYS: list[tuple[str, str]] = [
    ("project_name", "project_name_evidence"),
    ("language", "language_evidence"),
    ("package_manager", "package_manager_evidence"),
    ("test_framework", "test_framework_evidence"),
]


def _apply_str_fact(
    f: DetectedFact,
    state: dict[str, object],
    raw: dict[str, object],
) -> bool:
    """Apply a string-typed fact; return True if applied.

    Args:
        f: The detected fact to apply.
        state: Mutable state dict (project_name, language, etc.).
        raw: Mutable raw dict for evidence.

    Returns:
        True if the fact was a string key and was applied, False otherwise.
    """
    for key, ev_key in _STR_KEYS:
        if f.key == key and isinstance(f.value, str) and f.value:
            state[key] = f.value
            if f.evidence:
                raw[ev_key] = f.evidence
            return True
    return False


def _apply_tools_fact(
    f: DetectedFact,
    state: dict[str, object],
    tools_evidence: list[str],
) -> None:
    """Apply a tools list fact. Mutates state and tools_evidence.

    Args:
        f: The detected fact (key must be "tools", value a list).
        state: Mutable state dict; state["tools"] is extended.
        tools_evidence: List to append evidence string to.
    """
    if f.key != "tools" or not isinstance(f.value, list):
        return
    tools = state["tools"]
    assert isinstance(tools, list)
    for t in f.value:
        if isinstance(t, str) and t and t not in tools:
            tools.append(t)
    if f.evidence:
        tools_evidence.append(f.evidence)


def _apply_fact(
    f: DetectedFact,
    state: dict[str, object],
    raw: dict[str, object],
    tools_evidence: list[str],
) -> None:
    """Apply one fact to state dict and raw. Mutates state, raw, tools_evidence.

    Args:
        f: The detected fact.
        state: Mutable state dict.
        raw: Mutable raw dict for evidence.
        tools_evidence: List to append tools evidence to.
    """
    if _apply_str_fact(f, state, raw):
        return
    _apply_tools_fact(f, state, tools_evidence)


def _facts_to_profile(repo_root: Path, facts: list[DetectedFact]) -> ProjectProfile:
    """Merge detected facts into one ProjectProfile.

    Args:
        repo_root: Resolved project root path.
        facts: All detected facts from detectors.

    Returns:
        A single ProjectProfile with merged fields and raw evidence.
    """
    state: dict[str, object] = {
        "project_name": "",
        "language": "",
        "package_manager": "",
        "test_framework": "",
        "tools": [],
    }
    raw: dict[str, object] = {}
    tools_evidence: list[str] = []
    for f in facts:
        _apply_fact(f, state, raw, tools_evidence)
    if tools_evidence:
        raw["tools_evidence"] = tools_evidence
    raw_tools = state["tools"]
    tools_list: list[str] = (
        [x for x in raw_tools if isinstance(x, str)]
        if isinstance(raw_tools, list)
        else []
    )
    return ProjectProfile(
        project_name=str(state["project_name"]),
        project_root=repo_root,
        language=str(state["language"]),
        package_manager=str(state["package_manager"]),
        test_framework=str(state["test_framework"]),
        tools=tools_list,
        raw=raw,
    )
