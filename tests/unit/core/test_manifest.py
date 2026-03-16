"""Unit tests for grove.core.manifest load/save and round-trip."""

from pathlib import Path

import pytest

from grove.core.manifest import MANIFEST_SCHEMA_VERSION, load_manifest, save_manifest
from grove.core.models import (
    GeneratedFileRecord,
    GroveSection,
    InstalledPackRecord,
    ManifestState,
    ProjectSection,
)


@pytest.mark.unit
def test_save_and_load_round_trip(tmp_path: Path) -> None:
    """Save ManifestState to TOML and load it back; data matches."""
    path = tmp_path / "manifest.toml"
    state = ManifestState(
        grove=GroveSection(version="0.1.0", schema_version=MANIFEST_SCHEMA_VERSION),
        project=ProjectSection(root=str(tmp_path), analysis_summary="Python, uv"),
        installed_packs=[
            InstalledPackRecord(id="base", version="0.1.0"),
            InstalledPackRecord(id="python", version="0.1.0"),
        ],
        generated_files=[
            GeneratedFileRecord(path="GROVE.md", pack_id="base"),
            GeneratedFileRecord(path="rules/python.md", pack_id="python"),
        ],
    )
    save_manifest(path, state)
    assert path.exists()

    loaded = load_manifest(path)
    assert loaded.grove.version == state.grove.version
    assert loaded.grove.schema_version == state.grove.schema_version
    assert loaded.project.root == state.project.root
    assert loaded.project.analysis_summary == state.project.analysis_summary
    assert len(loaded.installed_packs) == len(state.installed_packs)
    assert loaded.installed_packs[0].id == state.installed_packs[0].id
    assert len(loaded.generated_files) == len(state.generated_files)
    assert loaded.generated_files[0].path == state.generated_files[0].path


@pytest.mark.unit
def test_load_missing_file_raises(tmp_path: Path) -> None:
    """load_manifest on non-existent path raises FileNotFoundError."""
    path = tmp_path / "nonexistent.toml"
    with pytest.raises(FileNotFoundError, match="Manifest not found"):
        load_manifest(path)


@pytest.mark.unit
def test_load_invalid_toml_missing_grove_section(tmp_path: Path) -> None:
    """load_manifest with TOML missing [grove] raises ValueError."""
    path = tmp_path / "manifest.toml"
    path.write_text('[project]\nroot = "/repo"\n')
    with pytest.raises(ValueError, match="contain \\[grove\\]"):
        load_manifest(path)


@pytest.mark.unit
def test_load_invalid_toml_missing_project_section(tmp_path: Path) -> None:
    """load_manifest with TOML missing [project] raises ValueError."""
    path = tmp_path / "manifest.toml"
    path.write_text('[grove]\nversion = "0.1.0"\nschema_version = 1\n')
    with pytest.raises(ValueError, match="contain \\[project\\]"):
        load_manifest(path)


@pytest.mark.unit
def test_save_creates_parent_dir(tmp_path: Path) -> None:
    """save_manifest creates parent directory if needed."""
    sub = tmp_path / "sub" / "dir" / "manifest.toml"
    state = ManifestState(
        grove=GroveSection(version="0.1.0", schema_version=1),
        project=ProjectSection(root="/repo", analysis_summary=""),
    )
    save_manifest(sub, state)
    assert sub.exists()
    loaded = load_manifest(sub)
    assert loaded.grove.version == "0.1.0"
