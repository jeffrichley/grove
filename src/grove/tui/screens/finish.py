"""Finish screen: success message and suggested next commands."""

from collections.abc import Callable
from typing import ClassVar, cast

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Markdown, RadioButton, RadioSet

from grove.tui.screens.base import GroveBaseScreen, _Bindings
from grove.tui.state import SetupState

FINISH_STEP = 9
TOTAL_STEPS = 9


def _install_root_display(state: SetupState) -> str:
    """Return install root path string for display (resolved if relative).

    Args:
        state: Shared setup state; uses root and install_root.

    Returns:
        String path for display.
    """
    root = state.root.resolve()
    install_root = state.install_root
    if not install_root.is_absolute():
        install_root = (root / install_root).resolve()
    return str(install_root)


class FinishScreen(GroveBaseScreen):
    """Screen 9: success message and Done."""

    BINDINGS: ClassVar[_Bindings] = cast(
        _Bindings,
        [
            ("enter", "done", "Done"),
            ("q", "quit", "Quit"),
            ("escape", "quit", "Quit"),
        ],
    )

    def __init__(self, state: SetupState) -> None:
        """Store shared setup state.

        Args:
            state: Shared state (root, install_root, manifest, etc.).
        """
        super().__init__()
        self._state = state

    def compose_content(self) -> ComposeResult:
        """Build finish layout: step, success message, suggested commands, Done.

        Yields:
            Step indicator and content container.
        """
        install_root = _install_root_display(self._state)
        body = (
            f"**Grove initialized at** `{install_root}`\n\n"
            "Suggested next commands:\n\n"
            "- `grove doctor` — check setup\n"
            "- `grove sync` — re-render managed files after edits\n\n"
            "*To add packs or change settings later, run `grove configure`.*"
        )
        content = Container(
            Markdown(body, id="finish-message"),
            RadioSet(
                RadioButton("Done", value=True, id="action-done"),
                id="action-radios",
            ),
            id="finish-content",
        )
        content.border_title = "○ Finish"
        with VerticalScroll():
            yield Markdown(
                f"*Step {FINISH_STEP} of {TOTAL_STEPS}*",
                id="step-indicator",
                classes="step-indicator",
            )
            yield content

    def _radio_actions(self) -> dict[str, Callable[[], None]]:
        """Map radio button ids to actions.

        Returns:
            Dict mapping button id to callable.
        """
        return {"action-done": self.action_done}

    def action_done(self) -> None:
        """Exit the app."""
        self.app.exit()

    def action_quit(self) -> None:
        """Exit the app."""
        self.app.exit()
