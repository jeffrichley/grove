"""Integration tests for the Codex AGENTS.md shim hook."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from grove.cli.app import app

runner = CliRunner()

_SHIM_START = "<!-- grove:tool-hook:codex:codex-agents-shim:start -->"
_SHIM_END = "<!-- grove:tool-hook:codex:codex-agents-shim:end -->"


def _write_project(root: Path) -> None:
    """Create the minimal project files needed for Grove init."""
    (root / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1.0"\n'
    )


@pytest.mark.integration
def test_codex_agents_shim_preserves_user_content_on_init(tmp_path: Path) -> None:
    """Init with the Codex pack appends a managed AGENTS shim and keeps user text."""
    # Arrange - existing AGENTS content plus a project Grove init target
    _write_project(tmp_path)
    agents_path = tmp_path / "AGENTS.md"
    agents_path.write_text("User-owned AGENTS intro")
    # Act - init with base + codex
    result = runner.invoke(
        app,
        ["init", "--root", str(tmp_path), "--pack", "base", "--pack", "codex"],
    )
    # Assert - user content remains and the Codex shim is appended
    assert result.exit_code == 0, result.output
    content = agents_path.read_text()
    assert "User-owned AGENTS intro" in content
    assert _SHIM_START in content
    assert _SHIM_END in content
    assert ".grove/GROVE.md" in content
    assert ".grove/INDEX.md" in content


@pytest.mark.integration
def test_codex_agents_shim_refreshes_on_sync(tmp_path: Path) -> None:
    """Sync replaces only the managed Codex shim block when it becomes stale."""
    # Arrange - init with Codex, then corrupt only the managed hook block
    _write_project(tmp_path)
    init_result = runner.invoke(
        app,
        ["init", "--root", str(tmp_path), "--pack", "base", "--pack", "codex"],
    )
    assert init_result.exit_code == 0, init_result.output
    agents_path = tmp_path / "AGENTS.md"
    corrupted = agents_path.read_text().replace(".grove/GROVE.md", ".grove/BROKEN.md")
    agents_path.write_text(corrupted)
    # Act - sync
    result = runner.invoke(app, ["sync", "--root", str(tmp_path)])
    # Assert - the managed block is restored
    assert result.exit_code == 0, result.output
    content = agents_path.read_text()
    assert ".grove/BROKEN.md" not in content
    assert ".grove/GROVE.md" in content
