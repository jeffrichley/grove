"""Integration tests: grove add and grove sync CLI (Phase 1 of plan 003)."""

import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from grove.cli.app import app
from grove.core.manifest import load_manifest

runner = CliRunner()
_USER_NOTES_PLACEHOLDER = (
    "<!-- Add project-specific notes here. Grove sync must preserve this region. -->"
)
_GUIDANCE_ANCHOR_RE = (
    r"(<!-- grove:anchor:guidance:start -->).*?"
    r"(<!-- grove:anchor:guidance:end -->)"
)


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
    # Assert - exit 0 and output reports Updated or No files to update
    assert result.exit_code == 0, result.output
    assert "Updated:" in result.output or "No files to update." in result.output


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
    """Sync restores anchor bodies while preserving user regions."""
    # Arrange - init then modify generated and user-owned content
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1.0"\n'
    )
    _init_grove(tmp_path, pack=["base", "python"])
    grove_md = tmp_path / ".grove" / "GROVE.md"
    original = grove_md.read_text()
    corrupted = original.replace("### Python Workflow", "### Corrupted Workflow")
    corrupted = corrupted.replace(
        _USER_NOTES_PLACEHOLDER,
        "User note that must stay",
    )
    grove_md.write_text(corrupted)
    # Act - grove sync
    result = runner.invoke(app, ["sync", "--root", str(tmp_path)])
    # Assert - exit 0, anchor body restored, user region preserved
    assert result.exit_code == 0, result.output
    content = grove_md.read_text()
    assert "### Corrupted Workflow" not in content
    assert "### Python Workflow" in content
    assert "User note that must stay" in content


@pytest.mark.integration
def test_sync_rebuilds_anchor_body_when_anchor_skeleton_exists(tmp_path: Path) -> None:
    """Sync reconstructs anchor bodies when stale generated content is removed."""
    # Arrange - init then replace the guidance anchor body with stale content
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1.0"\n'
    )
    _init_grove(tmp_path, pack=["base", "python"])
    grove_md = tmp_path / ".grove" / "GROVE.md"
    corrupted = re.sub(
        _GUIDANCE_ANCHOR_RE,
        r"\1Broken guidance body\2",
        grove_md.read_text(),
        count=1,
        flags=re.S,
    )
    grove_md.write_text(corrupted)
    # Act - grove sync
    result = runner.invoke(app, ["sync", "--root", str(tmp_path)])
    # Assert - sync succeeds and reconstructs the anchor body
    assert result.exit_code == 0, result.output
    content = grove_md.read_text()
    assert "Broken guidance body" not in content
    assert "### Python Workflow" in content


@pytest.mark.integration
def test_sync_fails_when_anchor_reconstruction_is_unsafe(tmp_path: Path) -> None:
    """Sync fails clearly when a file loses required anchors."""
    # Arrange - init then replace the file with content that has no safe skeleton
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1.0"\n'
    )
    _init_grove(tmp_path, pack=["base", "python"])
    grove_md = tmp_path / ".grove" / "GROVE.md"
    grove_md.write_text("fully corrupted content")
    # Act - grove sync
    result = runner.invoke(app, ["sync", "--root", str(tmp_path)])
    # Assert - sync reports unsafe reconstruction instead of overwriting blindly
    assert result.exit_code != 0
    assert "unsafe" in result.output.lower()
    assert "anchor" in result.output.lower()


@pytest.mark.integration
def test_sync_is_idempotent_after_restoring_anchor_content(tmp_path: Path) -> None:
    """A second sync after restoration yields no further changes."""
    # Arrange - init, corrupt one anchor body, then run sync once
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1.0"\n'
    )
    _init_grove(tmp_path, pack=["base", "python"])
    grove_md = tmp_path / ".grove" / "GROVE.md"
    grove_md.write_text(
        re.sub(
            _GUIDANCE_ANCHOR_RE,
            r"\1Temporary guidance\2",
            grove_md.read_text(),
            count=1,
            flags=re.S,
        )
    )
    first = runner.invoke(app, ["sync", "--root", str(tmp_path)])
    assert first.exit_code == 0, first.output
    restored = grove_md.read_text()
    # Act - sync a second time without intervening edits
    second = runner.invoke(app, ["sync", "--root", str(tmp_path)])
    # Assert - second sync reports no work and leaves file unchanged
    assert second.exit_code == 0, second.output
    assert "No files to update." in second.output
    assert grove_md.read_text() == restored


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
