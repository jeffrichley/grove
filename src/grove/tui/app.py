"""Textual app for grove init: holds state and drives screen flow."""

from pathlib import Path
from typing import ClassVar, cast

from textual.app import App, ComposeResult
from textual.binding import Binding

from grove.tui.screens.welcome import WelcomeScreen
from grove.tui.state import SetupState

_Bindings = list[Binding | tuple[str, str] | tuple[str, str, str]]


class GroveInitApp(App[None]):
    """TUI for interactive grove init: welcome -> analysis -> ... -> finish."""

    TITLE = "▸ Grove init"
    CSS_PATH = str(Path(__file__).parent / "grove_init.tcss")
    BINDINGS: ClassVar[_Bindings] = cast(
        _Bindings,
        [
            ("q", "quit", "Quit"),
            ("escape", "quit", "Quit"),
        ],
    )

    # Total steps in the flow (for step indicator)
    TOTAL_STEPS = 9

    def __init__(self, state: SetupState | None = None) -> None:
        """Initialize app with optional setup state.

        Args:
            state: Shared state for the init flow; defaults to new SetupState.
        """
        super().__init__()
        self.setup_state = state if state is not None else SetupState()

    def compose(self) -> ComposeResult:
        """Compose app: no widgets; the pushed screen provides all content.

        Yields:
            Nothing; the pushed screen provides content.
        """
        yield from ()  # app has no widgets; pushed screen provides content

    def on_mount(self) -> None:
        """Push the first screen (Welcome)."""
        self.push_screen(WelcomeScreen(self.setup_state))
