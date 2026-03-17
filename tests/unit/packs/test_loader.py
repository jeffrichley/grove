"""Unit tests for grove.packs.loader."""

from pathlib import Path

import pytest

from grove.core.models import PackManifest
from grove.packs.loader import load_pack_manifest


@pytest.mark.unit
def test_load_pack_manifest_toml(tmp_path: Path) -> None:
    """Load a valid pack.toml and get PackManifest."""
    # Arrange - valid pack.toml with all sections
    (tmp_path / "pack.toml").write_text(
        """
id = "test"
name = "Test Pack"
version = "0.1.0"
depends_on = ["base"]
compatible_with = ["python"]
activates_when = ["pyproject.toml"]

[contributes]
templates = ["GROVE.md.j2"]
setup_questions = []

[[contributes.rules]]
paths = ["**/*.py"]
"""
    )
    # Act - load_pack_manifest
    manifest = load_pack_manifest(tmp_path)
    # Assert - PackManifest with expected fields and contributes
    assert isinstance(manifest, PackManifest)
    assert manifest.id == "test"
    assert manifest.name == "Test Pack"
    assert manifest.version == "0.1.0"
    assert manifest.depends_on == ["base"]
    assert manifest.compatible_with == ["python"]
    assert manifest.contributes.get("templates") == ["GROVE.md.j2"]
    rules = manifest.contributes.get("rules")
    assert isinstance(rules, list) and len(rules) == 1
    assert rules[0].get("paths") == ["**/*.py"]


@pytest.mark.unit
def test_load_pack_manifest_missing_manifest_raises(tmp_path: Path) -> None:
    """Load from dir with no pack.toml raises FileNotFoundError."""
    # Arrange - directory with no pack.toml
    # Act - load_pack_manifest
    # Assert - FileNotFoundError
    with pytest.raises(FileNotFoundError, match="No pack manifest"):
        load_pack_manifest(tmp_path)


@pytest.mark.unit
def test_load_pack_manifest_missing_required_field_raises(tmp_path: Path) -> None:
    """Manifest without id raises ValueError."""
    # Arrange - pack.toml without id
    (tmp_path / "pack.toml").write_text('name = "X"\nversion = "0.1.0"\n')
    # Act - load_pack_manifest
    # Assert - ValueError
    with pytest.raises(ValueError, match="missing required field"):
        load_pack_manifest(tmp_path)


@pytest.mark.unit
def test_load_pack_manifest_empty_id_raises(tmp_path: Path) -> None:
    """Manifest with empty id raises ValueError."""
    # Arrange - pack.toml with empty id
    (tmp_path / "pack.toml").write_text('id = ""\nname = "X"\nversion = "0.1.0"\n')
    # Act - load_pack_manifest
    # Assert - ValueError
    with pytest.raises(ValueError, match="must be non-empty"):
        load_pack_manifest(tmp_path)
