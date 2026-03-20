"""Integration tests for the slim Phase 2 base pack and minimal capability packs."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from grove.cli.app import app
from grove.core.manifest import load_manifest

runner = CliRunner()


@pytest.mark.integration
def test_phase2_base_pack_init_writes_only_core_infrastructure(tmp_path: Path) -> None:
    """Base-only init writes GROVE, INDEX, and manifest without legacy scaffolding."""
    # Arrange - a minimal project root
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1.0"\n'
    )
    # Act - initialize Grove with only the base pack
    result = runner.invoke(app, ["init", "--root", str(tmp_path), "--pack", "base"])
    # Assert - init succeeds and only the slim core files exist from base
    assert result.exit_code == 0, result.output
    grove_dir = tmp_path / ".grove"
    assert (grove_dir / "GROVE.md").exists()
    assert (grove_dir / "INDEX.md").exists()
    assert (grove_dir / "manifest.toml").exists()
    assert not (grove_dir / "plans").exists()
    assert not (grove_dir / "handoffs").exists()
    assert not (grove_dir / "decisions").exists()
    manifest = load_manifest(grove_dir / "manifest.toml")
    assert [pack.id for pack in manifest.installed_packs] == ["base"]
    assert sorted(g.path for g in manifest.generated_files) == ["GROVE.md", "INDEX.md"]


@pytest.mark.integration
def test_phase2_add_installs_each_minimal_pack(tmp_path: Path) -> None:
    """Each new slim Phase 2 pack can be added and produces its minimal artifact."""
    # Arrange - initialize with base only
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1.0"\n'
    )
    init_result = runner.invoke(
        app, ["init", "--root", str(tmp_path), "--pack", "base"]
    )
    assert init_result.exit_code == 0, init_result.output
    # Act - add the new slim capability packs one by one
    for pack_id in ("memory", "commands", "knowledge", "project-context"):
        result = runner.invoke(app, ["add", pack_id, "--root", str(tmp_path)])
        assert result.exit_code == 0, result.output
    # Assert - new files exist and packs are recorded in the manifest
    grove_dir = tmp_path / ".grove"
    assert (grove_dir / "memory" / "README.md").exists()
    assert (grove_dir / "commands" / "README.md").exists()
    assert (grove_dir / "docs" / "knowledge.md").exists()
    assert (grove_dir / "docs" / "project-context.md").exists()
    manifest = load_manifest(grove_dir / "manifest.toml")
    assert [pack.id for pack in manifest.installed_packs] == [
        "base",
        "memory",
        "commands",
        "knowledge",
        "project-context",
    ]
    generated_paths = {record.path for record in manifest.generated_files}
    assert "memory/README.md" in generated_paths
    assert "commands/README.md" in generated_paths
    assert "docs/knowledge.md" in generated_paths
    assert "docs/project-context.md" in generated_paths
    index_content = (grove_dir / "INDEX.md").read_text(encoding="utf-8")
    assert ".grove/memory/README.md" in index_content
    assert ".grove/commands/README.md" in index_content
    assert ".grove/docs/knowledge.md" in index_content
    assert ".grove/docs/project-context.md" in index_content
