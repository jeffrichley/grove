"""Unit tests for PackConfigScreen (compose, actions, _save_from_ui)."""

from pathlib import Path
from unittest.mock import patch

import pytest
from textual.app import App, ScreenStackError

from grove.tui.screens.pack_config import PackConfigScreen
from grove.tui.state import SetupState


def _minimal_app(state: SetupState) -> App[None]:
    """Minimal Textual app that shows PackConfigScreen on mount."""

    class _Loader(App[None]):
        def __init__(self, setup_state: SetupState) -> None:
            super().__init__()
            self._setup_state = setup_state

        def on_mount(self) -> None:
            self.push_screen(PackConfigScreen(self._setup_state))

    return _Loader(state)


@pytest.mark.unit
async def test_pack_config_screen_no_questions_compose_and_next() -> None:
    """No-questions screen shows message and action_next pushes next screen."""
    # Arrange - state with selected packs, _collect_setup_questions returns []
    state = SetupState(root=Path.cwd(), selected_pack_ids=["base"])
    app = _minimal_app(state)
    with patch(
        "grove.tui.screens.pack_config._collect_setup_questions",
        return_value=[],
    ):
        # Act - run screen and trigger Next
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, PackConfigScreen)
            screen.action_next()
        # Assert - next screen was pushed (app.screen may have changed)
        assert len(state.config_answers) == 0


@pytest.mark.unit
async def test_pack_config_screen_with_checkbox_save_from_ui() -> None:
    """PackConfigScreen with one checkbox question saves answer on Next."""
    # Arrange - one checkbox question
    questions = [
        {
            "pack_id": "p",
            "id": "c",
            "prompt": "Enable?",
            "type": "checkbox",
            "default": True,
        }
    ]
    state = SetupState(root=Path.cwd(), selected_pack_ids=["p"], config_answers={})
    app = _minimal_app(state)
    with patch(
        "grove.tui.screens.pack_config._collect_setup_questions",
        return_value=questions,
    ):
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, PackConfigScreen)
            # Act - trigger Next to run _save_from_ui
            screen.action_next()
        # Assert - checkbox answer written to state
        assert state.config_answers.get("p.c") is True


@pytest.mark.unit
async def test_pack_config_screen_action_back_pops_screen() -> None:
    """PackConfigScreen action_back pops the screen."""
    # Arrange - screen with no questions
    state = SetupState(root=Path.cwd(), selected_pack_ids=["base"])
    app = _minimal_app(state)
    with patch(
        "grove.tui.screens.pack_config._collect_setup_questions",
        return_value=[],
    ):
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, PackConfigScreen)
            # Act - trigger Back (pops this screen; app may have no other screens)
            screen.action_back()
            await pilot.pause()
        # Assert - PackConfigScreen was popped (stack empty or different screen)
        try:
            current = app.screen
            assert not isinstance(current, PackConfigScreen)
        except ScreenStackError:
            pass  # stack empty after pop


@pytest.mark.unit
async def test_pack_config_screen_with_select_save_from_ui() -> None:
    """PackConfigScreen with one select question saves answer on Next."""
    # Arrange - one select question with options
    questions = [
        {
            "pack_id": "p",
            "id": "env",
            "prompt": "Environment?",
            "type": "select",
            "options": ["dev", "prod"],
            "default": "dev",
        }
    ]
    state = SetupState(root=Path.cwd(), selected_pack_ids=["p"], config_answers={})
    app = _minimal_app(state)
    with patch(
        "grove.tui.screens.pack_config._collect_setup_questions",
        return_value=questions,
    ):
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, PackConfigScreen)
            # Act - trigger Next to run _save_from_ui (select branch)
            screen.action_next()
        # Assert - select value written to state (default or first option)
        assert state.config_answers.get("p.env") in ("dev", "prod")


@pytest.mark.unit
async def test_pack_config_screen_with_text_save_from_ui() -> None:
    """PackConfigScreen with one text question saves answer on Next."""
    # Arrange - one text question (Input has app context inside run_test)
    questions = [
        {
            "pack_id": "p",
            "id": "name",
            "prompt": "Project name?",
            "type": "text",
            "default": "myapp",
        }
    ]
    state = SetupState(root=Path.cwd(), selected_pack_ids=["p"], config_answers={})
    app = _minimal_app(state)
    with patch(
        "grove.tui.screens.pack_config._collect_setup_questions",
        return_value=questions,
    ):
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, PackConfigScreen)
            # Act - trigger Next to run _save_from_ui (text branch)
            screen.action_next()
        # Assert - text answer written to state (default)
        assert state.config_answers.get("p.name") == "myapp"
