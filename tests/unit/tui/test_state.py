"""Unit tests for SetupState and setup_state_from_manifest."""

from pathlib import Path

import pytest

from grove.tui.state import SetupState, setup_state_from_manifest


@pytest.mark.unit
def test_setup_state_defaults() -> None:
    """SetupState has expected defaults for optional fields."""
    # Arrange - none
    # Act - construct default SetupState
    state = SetupState()
    # Assert - default root, install_root, and optional fields
    assert state.root == Path.cwd()
    assert state.install_root == Path(".grove")
    assert state.profile is None
    assert state.selected_pack_ids == []
    assert state.config_answers == {}
    assert state.install_plan is None
    assert state.manifest is None


@pytest.mark.unit
def test_setup_state_root_and_install_root() -> None:
    """SetupState accepts root and install_root."""
    # Arrange - root and install_root paths
    root = Path("/some/repo")
    install_root = root / ".grove"
    # Act - construct SetupState with paths
    state = SetupState(root=root, install_root=install_root)
    # Assert - paths stored
    assert state.root == root
    assert state.install_root == install_root


@pytest.mark.unit
def test_setup_state_round_trip_serialization() -> None:
    """SetupState can be constructed and serialized (Pydantic)."""
    # Arrange - populated SetupState
    state = SetupState(
        root=Path("/tmp/repo"),
        install_root=Path("/tmp/repo/.grove"),
        selected_pack_ids=["base", "python"],
        config_answers={"pack_manager": "uv"},
    )
    # Act - dump and validate back
    data = state.model_dump()
    restored = SetupState.model_validate(data)
    # Assert - dump contains selected fields and restored matches
    assert data["selected_pack_ids"] == ["base", "python"]
    assert data["config_answers"] == {"pack_manager": "uv"}
    assert restored.root == state.root
    assert restored.selected_pack_ids == state.selected_pack_ids


@pytest.mark.unit
def test_setup_state_from_manifest_missing_returns_defaults(tmp_path: Path) -> None:
    """When manifest path does not exist, return SetupState with default_root."""
    # Arrange - no file at path
    manifest_path = tmp_path / ".grove" / "manifest.toml"
    default_root = tmp_path
    # Act - load state from missing manifest
    state = setup_state_from_manifest(manifest_path, default_root)
    # Assert - default root and install_root
    assert state.root == default_root
    assert state.install_root == default_root / ".grove"
    assert state.selected_pack_ids == []


@pytest.mark.unit
def test_setup_state_from_manifest_valid_with_provenance(tmp_path: Path) -> None:
    """When manifest exists with [init], prefill install_root and core options."""
    # Arrange - valid manifest with init provenance
    grove_dir = tmp_path / ".grove"
    grove_dir.mkdir()
    manifest_path = grove_dir / "manifest.toml"
    root_str = tmp_path.resolve().as_posix()
    manifest_path.write_text(
        f"""[grove]
version = "0.1.0"
schema_version = 1

[project]
root = "{root_str}"

[[packs]]
id = "base"
version = "0.1.0"

[[packs]]
id = "python"
version = "0.1.0"

[init]
install_root = ".grove"
core_include_adrs = true
core_include_handoffs = true
core_include_scoped_rules = true
core_include_memory = false
core_include_skills_dir = true
"""
    )
    # Act - load state from manifest
    state = setup_state_from_manifest(manifest_path, tmp_path)
    # Assert - root, install_root, packs, and core options from provenance
    assert state.root == tmp_path.resolve()
    assert state.install_root == tmp_path.resolve() / ".grove"
    assert state.selected_pack_ids == ["base", "python"]
    assert state.core_include_memory is False
    assert state.core_include_handoffs is True


@pytest.mark.unit
def test_setup_state_from_manifest_valid_no_provenance(tmp_path: Path) -> None:
    """When manifest exists without [init], use project root and packs only."""
    # Arrange - manifest with no [init] section
    grove_dir = tmp_path / ".grove"
    grove_dir.mkdir()
    manifest_path = grove_dir / "manifest.toml"
    root_str = tmp_path.resolve().as_posix()
    manifest_path.write_text(
        f"""[grove]
version = "0.1.0"
schema_version = 1

[project]
root = "{root_str}"

[[packs]]
id = "base"
version = "0.1.0"
"""
    )
    # Act - load state from manifest
    state = setup_state_from_manifest(manifest_path, tmp_path)
    # Assert - root, install_root, and packs from manifest
    assert state.root == tmp_path.resolve()
    assert state.install_root == tmp_path / ".grove"
    assert state.selected_pack_ids == ["base"]


@pytest.mark.unit
def test_setup_state_from_manifest_load_error_returns_defaults(tmp_path: Path) -> None:
    """When manifest exists but is invalid, return SetupState with default_root."""
    # Arrange - file exists but invalid TOML (no [grove])
    grove_dir = tmp_path / ".grove"
    grove_dir.mkdir()
    manifest_path = grove_dir / "manifest.toml"
    manifest_path.write_text("invalid = true\n[project]\nroot = '/tmp'")
    default_root = tmp_path
    # Act - load state (load_manifest raises ValueError)
    state = setup_state_from_manifest(manifest_path, default_root)
    # Assert - fallback to defaults
    assert state.root == default_root
    assert state.install_root == default_root / ".grove"
    assert state.selected_pack_ids == []
