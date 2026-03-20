"""Integration tests for the `grove doctor` CLI command."""

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
        '[project]\nname = "fixture"\nversion = "0.1.0"\n',
        encoding="utf-8",
    )


@pytest.mark.integration
def test_doctor_reports_healthy_repo(tmp_path: Path) -> None:
    """Doctor exits cleanly when the Grove install is healthy."""
    # Arrange - initialize a healthy base plus python install
    _write_project(tmp_path)
    init_result = runner.invoke(
        app,
        ["init", "--root", str(tmp_path), "--pack", "base", "--pack", "python"],
    )
    assert init_result.exit_code == 0, init_result.output
    # Act - run doctor against the healthy install
    result = runner.invoke(app, ["doctor", "--root", str(tmp_path)])
    # Assert - doctor reports no issues and exits zero
    assert result.exit_code == 0, result.output
    assert "No issues found." in result.output


@pytest.mark.integration
def test_doctor_reports_broken_repo_findings(tmp_path: Path) -> None:
    """Doctor reports drift, missing hooks, and missing skills in a broken repo."""
    # Arrange - initialize base, python, and codex, then break several outputs
    _write_project(tmp_path)
    init_result = runner.invoke(
        app,
        [
            "init",
            "--root",
            str(tmp_path),
            "--pack",
            "base",
            "--pack",
            "python",
            "--pack",
            "codex",
        ],
    )
    assert init_result.exit_code == 0, init_result.output
    grove_md = tmp_path / ".grove" / "GROVE.md"
    grove_md.write_text(
        re.sub(
            _GUIDANCE_ANCHOR_RE,
            r"\1stale guidance body\2",
            grove_md.read_text(encoding="utf-8"),
            count=1,
            flags=re.S,
        ),
        encoding="utf-8",
    )
    (tmp_path / "AGENTS.md").unlink()
    (tmp_path / ".agents" / "skills" / "planning-execution" / "SKILL.md").unlink()
    # Act - run doctor against the broken install
    result = runner.invoke(app, ["doctor", "--root", str(tmp_path)])
    # Assert - doctor exits non-zero and reports categorized findings
    assert result.exit_code != 0
    assert "managed-file-drift" in result.output
    assert "tool-hook-target-missing" in result.output
    assert "pack-local-skill-missing" in result.output


@pytest.mark.integration
def test_doctor_reports_codex_skill_front_matter_failures(tmp_path: Path) -> None:
    """Doctor reports missing and malformed Codex skill front matter."""
    # Arrange - init codex, then break front matter in both skill files
    _write_project(tmp_path)
    init_result = runner.invoke(
        app,
        ["init", "--root", str(tmp_path), "--pack", "base", "--pack", "codex"],
    )
    assert init_result.exit_code == 0, init_result.output
    planning_skill = tmp_path / ".agents" / "skills" / "planning-execution" / "SKILL.md"
    memory_skill = tmp_path / ".agents" / "skills" / "memory-writeback" / "SKILL.md"
    planning_skill.write_text("# Planning Execution\n", encoding="utf-8")
    memory_skill.write_text(
        "---\nname Memory Writeback\n---\n\n# Memory Writeback\n",
        encoding="utf-8",
    )
    # Act - run doctor against the invalid Codex skills
    result = runner.invoke(app, ["doctor", "--root", str(tmp_path)])
    # Assert - doctor exits non-zero and reports both front-matter failure types
    assert result.exit_code != 0
    assert "skill-front-matter-missing" in result.output
    assert "skill-front-matter-malformed" in result.output
