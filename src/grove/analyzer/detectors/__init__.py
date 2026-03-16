"""Detectors for repo analysis (pyproject, uv, pytest, ruff, mypy)."""

from grove.analyzer.detectors.base import DetectorProtocol
from grove.analyzer.detectors.mypy import MypyDetector
from grove.analyzer.detectors.pyproject import PyprojectDetector
from grove.analyzer.detectors.pytest import PytestDetector
from grove.analyzer.detectors.ruff import RuffDetector
from grove.analyzer.detectors.uv import UvDetector

__all__ = [
    "DetectorProtocol",
    "MypyDetector",
    "PyprojectDetector",
    "PytestDetector",
    "RuffDetector",
    "UvDetector",
]
