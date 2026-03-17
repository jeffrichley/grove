"""Unit tests for SetupState."""

from pathlib import Path

import pytest

from grove.tui.state import SetupState


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
