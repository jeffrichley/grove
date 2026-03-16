"""Base detector protocol: read-only, evidence-based contribution to profile."""

from pathlib import Path
from typing import Protocol

from grove.analyzer.models import DetectedFact


class DetectorProtocol(Protocol):
    """Protocol for a detector: accepts repo root, returns zero or more facts.

    Detectors must not mutate the repo or perform network calls.
    Facts are evidence-based only; no inference when config is missing.
    """

    def detect(self, repo_root: Path) -> list[DetectedFact]:
        """Run detection under repo_root and return facts.

        Implementations must return a list of DetectedFact (empty if no evidence).
        Do not guess; evidence-only.

        Args:
            repo_root: Path to the project root (e.g. where pyproject.toml lives).

        Returns:
            List of DetectedFact; empty if no evidence. Do not guess.
        """
        _ = repo_root  # Protocol default; implementors use repo_root
        return []
