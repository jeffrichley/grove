"""Unit tests for SetupState."""

from pathlib import Path

import pytest

from grove.tui.state import SetupState


@pytest.mark.unit
def test_setup_state_defaults() -> None:
    """SetupState has expected defaults for optional fields."""
    state = SetupState()
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
    root = Path("/some/repo")
    install_root = root / ".grove"
    state = SetupState(root=root, install_root=install_root)
    assert state.root == root
    assert state.install_root == install_root


@pytest.mark.unit
def test_setup_state_round_trip_serialization() -> None:
    """SetupState can be constructed and serialized (Pydantic)."""
    state = SetupState(
        root=Path("/tmp/repo"),
        install_root=Path("/tmp/repo/.grove"),
        selected_pack_ids=["base", "python"],
        config_answers={"pack_manager": "uv"},
    )
    data = state.model_dump()
    assert data["selected_pack_ids"] == ["base", "python"]
    assert data["config_answers"] == {"pack_manager": "uv"}
    restored = SetupState.model_validate(data)
    assert restored.root == state.root
    assert restored.selected_pack_ids == state.selected_pack_ids
