"""Unit tests for grove.core.file_ops."""

from pathlib import Path

import pytest

from grove.core.file_ops import ApplyOptions, apply, preview
from grove.core.manifest import MANIFEST_SCHEMA_VERSION
from grove.core.models import (
    GroveSection,
    InstallPlan,
    ManifestState,
    PlannedFile,
    ProjectSection,
)


def _make_plan_and_pack(tmp_path: Path) -> tuple[InstallPlan, dict[str, Path]]:
    """Create a minimal plan and pack_roots with one template."""
    pack_root = tmp_path / "pack"
    pack_root.mkdir()
    (pack_root / "greet.j2").write_text("Hello {{ project_name }}!")
    install_root = tmp_path / ".grove"
    plan = InstallPlan(
        install_root=install_root,
        files=[
            PlannedFile(
                pack_id="base",
                src=Path("greet.j2"),
                dst=install_root / "greet.txt",
                variables={"project_name": "my-app"},
            ),
        ],
    )
    pack_roots = {"base": pack_root}
    return plan, pack_roots


@pytest.mark.unit
def test_preview_returns_path_and_content(tmp_path: Path) -> None:
    """preview() returns list of (path, content) without writing."""
    plan, pack_roots = _make_plan_and_pack(tmp_path)
    items = preview(plan, pack_roots)
    assert len(items) == 1
    path, content = items[0]
    assert path == tmp_path / ".grove" / "greet.txt"
    assert content == "Hello my-app!"


@pytest.mark.unit
def test_preview_missing_pack_raises(tmp_path: Path) -> None:
    """preview() with unknown pack_id raises KeyError."""
    plan, _ = _make_plan_and_pack(tmp_path)
    with pytest.raises(KeyError, match="not in pack_roots"):
        preview(plan, {})


@pytest.mark.unit
def test_apply_dry_run_does_not_write(tmp_path: Path) -> None:
    """apply() with dry_run=True does not create files."""
    plan, pack_roots = _make_plan_and_pack(tmp_path)
    manifest = ManifestState(
        grove=GroveSection(version="0.1.0", schema_version=MANIFEST_SCHEMA_VERSION),
        project=ProjectSection(root=str(tmp_path), analysis_summary=""),
    )
    options = ApplyOptions(dry_run=True)
    result = apply(plan, manifest, options, pack_roots)
    assert (tmp_path / ".grove" / "greet.txt").exists() is False
    assert result.generated_files == []


@pytest.mark.unit
def test_apply_creates_files_and_updates_manifest(tmp_path: Path) -> None:
    """apply() creates files and returns manifest with generated_files."""
    plan, pack_roots = _make_plan_and_pack(tmp_path)
    manifest = ManifestState(
        grove=GroveSection(version="0.1.0", schema_version=MANIFEST_SCHEMA_VERSION),
        project=ProjectSection(root=str(tmp_path), analysis_summary=""),
    )
    options = ApplyOptions(dry_run=False)
    result = apply(plan, manifest, options, pack_roots)
    greet_path = tmp_path / ".grove" / "greet.txt"
    assert greet_path.exists()
    assert greet_path.read_text() == "Hello my-app!"
    assert len(result.generated_files) == 1
    assert result.generated_files[0].path == "greet.txt"
    assert result.generated_files[0].pack_id == "base"


@pytest.mark.unit
def test_apply_collision_skip_skips_existing(tmp_path: Path) -> None:
    """When path exists and strategy is skip, file is not overwritten."""
    plan, pack_roots = _make_plan_and_pack(tmp_path)
    install_root = tmp_path / ".grove"
    install_root.mkdir(parents=True)
    existing = install_root / "greet.txt"
    existing.write_text("original")
    manifest = ManifestState(
        grove=GroveSection(version="0.1.0", schema_version=MANIFEST_SCHEMA_VERSION),
        project=ProjectSection(root=str(tmp_path), analysis_summary=""),
    )
    options = ApplyOptions(dry_run=False, collision_strategy="skip")
    result = apply(plan, manifest, options, pack_roots)
    assert existing.read_text() == "original"
    assert len(result.generated_files) == 0


@pytest.mark.unit
def test_apply_collision_rename_writes_new_path(tmp_path: Path) -> None:
    """When path exists and strategy is rename, write to new path."""
    plan, pack_roots = _make_plan_and_pack(tmp_path)
    install_root = tmp_path / ".grove"
    install_root.mkdir(parents=True)
    (install_root / "greet.txt").write_text("original")
    manifest = ManifestState(
        grove=GroveSection(version="0.1.0", schema_version=MANIFEST_SCHEMA_VERSION),
        project=ProjectSection(root=str(tmp_path), analysis_summary=""),
    )
    options = ApplyOptions(dry_run=False, collision_strategy="rename")
    result = apply(plan, manifest, options, pack_roots)
    assert (install_root / "greet.txt").read_text() == "original"
    renamed = install_root / "greet.1.txt"
    assert renamed.exists()
    assert renamed.read_text() == "Hello my-app!"
    assert len(result.generated_files) == 1
    assert result.generated_files[0].path == "greet.1.txt"


@pytest.mark.unit
def test_apply_collision_overwrite_replaces(tmp_path: Path) -> None:
    """When path exists and strategy is overwrite, file is replaced."""
    plan, pack_roots = _make_plan_and_pack(tmp_path)
    install_root = tmp_path / ".grove"
    install_root.mkdir(parents=True)
    (install_root / "greet.txt").write_text("original")
    manifest = ManifestState(
        grove=GroveSection(version="0.1.0", schema_version=MANIFEST_SCHEMA_VERSION),
        project=ProjectSection(root=str(tmp_path), analysis_summary=""),
    )
    options = ApplyOptions(dry_run=False, collision_strategy="overwrite")
    result = apply(plan, manifest, options, pack_roots)
    assert (install_root / "greet.txt").read_text() == "Hello my-app!"
    assert len(result.generated_files) == 1
