"""Integration tests for Phase 2G sync dry-run provenance reporting."""

import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from grove.cli.app import app

runner = CliRunner()
_GUIDANCE_ANCHOR_RE = (
    r"(<!-- grove:anchor:guidance:start -->).*?"
    r"(<!-- grove:anchor:guidance:end -->)"
)


def _write_project(root: Path) -> None:
    """Create the minimal project files needed for Grove init."""
    (root / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1.0"\n'
    )


@pytest.mark.integration
def test_sync_dry_run_reports_changed_anchor_provenance(tmp_path: Path) -> None:
    """Dry-run reports changed anchor ownership without writing the file."""
    # Arrange - init Grove, then corrupt one anchor body while keeping the skeleton
    _write_project(tmp_path)
    init_result = runner.invoke(
        app,
        ["init", "--root", str(tmp_path), "--pack", "base", "--pack", "python"],
    )
    assert init_result.exit_code == 0, init_result.output

    grove_md = tmp_path / ".grove" / "GROVE.md"
    original = grove_md.read_text(encoding="utf-8")
    grove_md.write_text(
        re.sub(
            _GUIDANCE_ANCHOR_RE,
            r"\1Stale guidance body\2",
            original,
            count=1,
            flags=re.S,
        ),
        encoding="utf-8",
    )

    # Act - run sync in dry-run mode so it reports the change without writing
    result = runner.invoke(app, ["sync", "--root", str(tmp_path), "--dry-run"])

    # Assert - output names the changed anchor provenance and the file stays modified
    assert result.exit_code == 0, result.output
    assert "Dry run: would write:" in result.output
    assert ".grove/GROVE.md" in result.output
    assert "anchor: guidance" in result.output
    assert "from python:python-grove-guidance" in result.output
    assert grove_md.read_text(encoding="utf-8") != original
    assert "Stale guidance body" in grove_md.read_text(encoding="utf-8")
