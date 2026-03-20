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
    # Arrange - plan and pack roots with one template
    plan, pack_roots = _make_plan_and_pack(tmp_path)
    # Act - call preview
    items = preview(plan, pack_roots)
    # Assert - single item with expected path and rendered content
    assert len(items) == 1
    path, content = items[0]
    assert path == tmp_path / ".grove" / "greet.txt"
    assert content == "Hello my-app!"


@pytest.mark.unit
def test_preview_missing_pack_raises(tmp_path: Path) -> None:
    """preview() with unknown pack_id raises KeyError."""
    # Arrange - plan referencing a pack, empty pack_roots
    plan, _ = _make_plan_and_pack(tmp_path)
    # Act - call preview with empty pack_roots
    # Assert - KeyError for missing pack
    with pytest.raises(KeyError, match="not in pack_roots"):
        preview(plan, {})


@pytest.mark.unit
def test_apply_dry_run_does_not_write(tmp_path: Path) -> None:
    """apply() with dry_run=True does not create files."""
    # Arrange - plan, manifest, dry_run options
    plan, pack_roots = _make_plan_and_pack(tmp_path)
    manifest = ManifestState(
        grove=GroveSection(version="0.1.0", schema_version=MANIFEST_SCHEMA_VERSION),
        project=ProjectSection(root=str(tmp_path), analysis_summary=""),
    )
    options = ApplyOptions(dry_run=True)
    # Act - apply with dry_run
    result = apply(plan, manifest, options, pack_roots)
    # Assert - no file created and no generated_files
    assert (tmp_path / ".grove" / "greet.txt").exists() is False
    assert result.generated_files == []


@pytest.mark.unit
def test_apply_creates_files_and_updates_manifest(tmp_path: Path) -> None:
    """apply() creates files and returns manifest with generated_files."""
    # Arrange - plan, manifest, apply options
    plan, pack_roots = _make_plan_and_pack(tmp_path)
    manifest = ManifestState(
        grove=GroveSection(version="0.1.0", schema_version=MANIFEST_SCHEMA_VERSION),
        project=ProjectSection(root=str(tmp_path), analysis_summary=""),
    )
    options = ApplyOptions(dry_run=False)
    # Act - apply
    result = apply(plan, manifest, options, pack_roots)
    # Assert - file created with content and result lists generated file
    greet_path = tmp_path / ".grove" / "greet.txt"
    assert greet_path.exists()
    assert greet_path.read_text() == "Hello my-app!"
    assert len(result.generated_files) == 1
    assert result.generated_files[0].path == "greet.txt"
    assert result.generated_files[0].pack_id == "base"


@pytest.mark.unit
def test_apply_collision_skip_skips_existing(tmp_path: Path) -> None:
    """When path exists and strategy is skip, file is not overwritten."""
    # Arrange - plan, existing file at target, skip strategy
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
    # Act - apply with skip
    result = apply(plan, manifest, options, pack_roots)
    # Assert - existing content unchanged and no generated files
    assert existing.read_text() == "original"
    assert len(result.generated_files) == 0


@pytest.mark.unit
def test_apply_collision_rename_writes_new_path(tmp_path: Path) -> None:
    """When path exists and strategy is rename, write to new path."""
    # Arrange - plan, existing file at target, rename strategy
    plan, pack_roots = _make_plan_and_pack(tmp_path)
    install_root = tmp_path / ".grove"
    install_root.mkdir(parents=True)
    (install_root / "greet.txt").write_text("original")
    manifest = ManifestState(
        grove=GroveSection(version="0.1.0", schema_version=MANIFEST_SCHEMA_VERSION),
        project=ProjectSection(root=str(tmp_path), analysis_summary=""),
    )
    options = ApplyOptions(dry_run=False, collision_strategy="rename")
    # Act - apply with rename
    result = apply(plan, manifest, options, pack_roots)
    # Assert - original unchanged, new file with content, result points to new path
    assert (install_root / "greet.txt").read_text() == "original"
    renamed = install_root / "greet.1.txt"
    assert renamed.exists()
    assert renamed.read_text() == "Hello my-app!"
    assert len(result.generated_files) == 1
    assert result.generated_files[0].path == "greet.1.txt"


@pytest.mark.unit
def test_apply_collision_overwrite_replaces(tmp_path: Path) -> None:
    """When path exists and strategy is overwrite, file is replaced."""
    # Arrange - plan, existing file at target, overwrite strategy
    plan, pack_roots = _make_plan_and_pack(tmp_path)
    install_root = tmp_path / ".grove"
    install_root.mkdir(parents=True)
    (install_root / "greet.txt").write_text("original")
    manifest = ManifestState(
        grove=GroveSection(version="0.1.0", schema_version=MANIFEST_SCHEMA_VERSION),
        project=ProjectSection(root=str(tmp_path), analysis_summary=""),
    )
    options = ApplyOptions(dry_run=False, collision_strategy="overwrite")
    # Act - apply with overwrite
    result = apply(plan, manifest, options, pack_roots)
    # Assert - file content replaced and one generated file recorded
    assert (install_root / "greet.txt").read_text() == "Hello my-app!"
    assert len(result.generated_files) == 1


@pytest.mark.unit
def test_preview_uses_pre_rendered_content_when_present(tmp_path: Path) -> None:
    """Composition-aware planned files bypass template rendering."""
    # Arrange - a plan with pre-rendered content and no template dependency
    install_root = tmp_path / ".grove"
    plan = InstallPlan(
        install_root=install_root,
        files=[
            PlannedFile(
                pack_id="base",
                src=Path("unused.j2"),
                dst=install_root / "GROVE.md",
                variables={},
                rendered_content="pre-rendered",
            )
        ],
    )
    # Act - preview the plan
    items = preview(plan, {})
    # Assert - preview returns the pre-rendered content unchanged
    assert items == [(install_root / "GROVE.md", "pre-rendered")]
