"""Placeholder test so CI has at least one test."""

import pytest

import grove


@pytest.mark.unit
def test_placeholder() -> None:
    """Ensure grove package is importable."""
    assert grove is not None
