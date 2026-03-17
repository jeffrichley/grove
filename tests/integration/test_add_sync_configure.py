"""Integration tests: grove add and grove sync CLI (Phase 1 of plan 003)."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from grove.cli.app import app
from grove.core.manifest import load_manifest

runner = CliRunner()


def _init_grove(root: Path, pack: list[str] | None = None) -> None:
    """Run grove init with optional --pack; assert success."""
    args = ["init", "--root", str(root)]
    if pack:
        for p in pack:
            args.extend(["--pack", p])
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output


@pytest.mark.integration
def test_sync_without_manifest_exits_nonzero(tmp_path: Path) -> None:
    """Sync with no .grove/manifest.toml exits non-zero and tells user to run init."""
    # Arrange - project root with no .grove
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1.0"\n'
    )
    # Act - grove sync without manifest
    result = runner.invoke(app, ["sync", "--root", str(tmp_path)])
    # Assert - non-zero exit and message mentions manifest or init
    assert result.exit_code != 0
    assert "manifest" in result.output.lower() or "init" in result.output.lower()


@pytest.mark.integration
def test_add_without_manifest_exits_nonzero(tmp_path: Path) -> None:
    """Add with no .grove/manifest.toml exits non-zero and tells user to run init."""
    # Arrange - project root with no .grove
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1.0"\n'
    )
    # Act - grove add without manifest
    result = runner.invoke(app, ["add", "python", "--root", str(tmp_path)])
    # Assert - non-zero exit and message mentions manifest or init
    assert result.exit_code != 0
    assert "manifest" in result.output.lower() or "init" in result.output.lower()


@pytest.mark.integration
def test_add_unknown_pack_exits_nonzero(tmp_path: Path) -> None:
    """Add with unknown pack id exits non-zero and reports pack not found."""
    # Arrange - project with grove init already run
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1.0"\n'
    )
    _init_grove(tmp_path, pack=["base", "python"])
    # Act - grove add with nonexistent pack id
    result = runner.invoke(app, ["add", "nonexistent-pack", "--root", str(tmp_path)])
    # Assert - non-zero exit and error mentions not found or pack name
    assert result.exit_code != 0
    assert "not found" in result.output or "nonexistent" in result.output


@pytest.mark.integration
def test_add_after_init_updates_manifest_and_files(tmp_path: Path) -> None:
    """Init with base only, then add python; manifest has both packs and new files."""
    # Arrange - project with init using base pack only
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1.0"\n'
    )
    _init_grove(tmp_path, pack=["base"])
    manifest_path = tmp_path / ".grove" / "manifest.toml"
    state_before = load_manifest(manifest_path)
    assert len(state_before.installed_packs) == 1
    assert state_before.installed_packs[0].id == "base"
    # Act - grove add python
    result = runner.invoke(app, ["add", "python", "--root", str(tmp_path)])
    # Assert - success, manifest lists base and python, new files present
    assert result.exit_code == 0, result.output
    assert "Added pack python" in result.output
    state_after = load_manifest(manifest_path)
    pack_ids = [p.id for p in state_after.installed_packs]
    assert "base" in pack_ids
    assert "python" in pack_ids
    assert len(state_after.generated_files) >= len(state_before.generated_files)
    grove_dir = tmp_path / ".grove"
    assert (grove_dir / "GROVE.md").exists()
    assert (grove_dir / "rules" / "python.md").exists() or any(
        "python" in g.path for g in state_after.generated_files
    )


@pytest.mark.integration
def test_sync_after_init_exits_zero_and_reports(tmp_path: Path) -> None:
    """Init then sync exits 0; sync reports updated or no change."""
    # Arrange - project with grove init (base + python)
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1.0"\n'
    )
    _init_grove(tmp_path, pack=["base", "python"])
    # Act - grove sync
    result = runner.invoke(app, ["sync", "--root", str(tmp_path)])
    # Assert - exit 0 and output reports Updated or No managed files to update
    assert result.exit_code == 0, result.output
    assert "Updated:" in result.output or "No managed files to update." in result.output


@pytest.mark.integration
def test_sync_dry_run_does_not_modify_files(tmp_path: Path) -> None:
    """Sync --dry-run exits 0 and reports would-write without changing disk."""
    # Arrange - project with grove init and GROVE.md content captured
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1.0"\n'
    )
    _init_grove(tmp_path, pack=["base", "python"])
    grove_md = tmp_path / ".grove" / "GROVE.md"
    content_before = grove_md.read_text()
    # Act - grove sync --dry-run
    result = runner.invoke(app, ["sync", "--root", str(tmp_path), "--dry-run"])
    # Assert - exit 0, dry-run message, file content unchanged
    assert result.exit_code == 0, result.output
    assert "Dry run" in result.output or "would write" in result.output.lower()
    assert grove_md.read_text() == content_before


@pytest.mark.integration
def test_sync_reverts_modified_managed_file(tmp_path: Path) -> None:
    """Sync re-renders managed files; modified GROVE.md is overwritten."""
    # Arrange - init then overwrite a managed file
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1.0"\n'
    )
    _init_grove(tmp_path, pack=["base", "python"])
    grove_md = tmp_path / ".grove" / "GROVE.md"
    grove_md.write_text("corrupted content")
    # Act - grove sync
    result = runner.invoke(app, ["sync", "--root", str(tmp_path)])
    # Assert - exit 0, GROVE.md re-rendered (contains Grove / template content)
    assert result.exit_code == 0, result.output
    content = grove_md.read_text()
    assert "corrupted content" not in content
    assert "GROVE" in content or "Grove" in content


@pytest.mark.integration
def test_configure_with_manifest_requires_tty(tmp_path: Path) -> None:
    """Configure with manifest but no TTY exits non-zero and mentions interactive."""
    # Arrange - project with grove init (manifest present)
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1.0"\n'
    )
    _init_grove(tmp_path, pack=["base", "python"])
    # Act - grove configure (headless: no TTY, so CLI exits with message)
    result = runner.invoke(app, ["configure", "--root", str(tmp_path)])
    # Assert - exit non-zero and message tells user to run in terminal
    assert result.exit_code != 0, result.output
    assert "interactive" in result.output.lower() or "terminal" in result.output.lower()
