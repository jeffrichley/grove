"""Integration tests for Codex skill materialization."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from grove.cli.app import app

runner = CliRunner()


def _write_project(root: Path) -> None:
    """Create the minimal project files needed for Grove init."""
    (root / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1.0"\n'
    )


@pytest.mark.integration
def test_codex_skills_materialize_under_repo_local_agents_dir(tmp_path: Path) -> None:
    """Init with the Codex pack writes SKILL.md files under .agents/skills."""
    # Arrange - init a minimal project and use repo-local Codex skill output
    _write_project(tmp_path)
    # Act - init with the Codex integration pack
    result = runner.invoke(
        app,
        ["init", "--root", str(tmp_path), "--pack", "base", "--pack", "codex"],
    )
    # Assert - expected skill files are materialized under .agents/skills
    assert result.exit_code == 0, result.output
    planning_skill = tmp_path / ".agents" / "skills" / "planning-execution" / "SKILL.md"
    memory_skill = tmp_path / ".agents" / "skills" / "memory-writeback" / "SKILL.md"
    assert planning_skill.exists()
    assert memory_skill.exists()
    assert planning_skill.read_text(encoding="utf-8").startswith("---\nname:")
    assert memory_skill.read_text(encoding="utf-8").startswith("---\nname:")
    assert "Planning Execution" in planning_skill.read_text(encoding="utf-8")
    assert "Memory Writeback" in memory_skill.read_text(encoding="utf-8")


@pytest.mark.integration
def test_sync_restores_repo_local_codex_skills(tmp_path: Path) -> None:
    """Sync recreates missing and stale Codex skills under .agents/skills."""
    # Arrange - init Grove with Codex, then remove one skill and corrupt another
    _write_project(tmp_path)
    init_result = runner.invoke(
        app,
        ["init", "--root", str(tmp_path), "--pack", "base", "--pack", "codex"],
    )
    assert init_result.exit_code == 0, init_result.output
    planning_skill = tmp_path / ".agents" / "skills" / "planning-execution" / "SKILL.md"
    memory_skill = tmp_path / ".agents" / "skills" / "memory-writeback" / "SKILL.md"
    planning_skill.unlink()
    memory_skill.write_text("stale memory skill\n", encoding="utf-8")

    # Act - run sync to restore the repo-local Codex skill outputs
    sync_result = runner.invoke(app, ["sync", "--root", str(tmp_path)])

    # Assert - sync recreates the missing skill and refreshes the stale one
    assert sync_result.exit_code == 0, sync_result.output
    assert ".agents/skills/planning-execution/SKILL.md" in sync_result.output
    assert ".agents/skills/memory-writeback/SKILL.md" in sync_result.output
    assert planning_skill.exists()
    assert planning_skill.read_text(encoding="utf-8").startswith("---\nname:")
    assert "Planning Execution" in planning_skill.read_text(encoding="utf-8")
    assert "stale memory skill" not in memory_skill.read_text(encoding="utf-8")
    assert memory_skill.read_text(encoding="utf-8").startswith("---\nname:")
    assert "Memory Writeback" in memory_skill.read_text(encoding="utf-8")
