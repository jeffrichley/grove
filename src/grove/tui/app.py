"""Textual app for grove init: holds state and drives screen flow."""

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header

from grove.tui.screens.welcome import WelcomeScreen
from grove.tui.state import SetupState


class GroveInitApp(App[None]):
    """TUI for interactive grove init: welcome -> analysis -> ... -> finish."""

    TITLE = "Grove init"
    BINDINGS = [  # noqa: RUF012
        ("q", "quit", "Quit"),
    ]

    def __init__(self, state: SetupState | None = None) -> None:
        """Initialize app with optional setup state.

        Args:
            state: Shared state for the init flow; defaults to new SetupState.
        """
        super().__init__()
        self.setup_state = state if state is not None else SetupState()

    def compose(self) -> ComposeResult:
        """Compose app layout: header and footer (first screen pushed in on_mount).

        Yields:
            Header and Footer widgets.
        """
        yield Header(show_clock=False)
        yield Footer()

    def on_mount(self) -> None:
        """Push the first screen (Welcome)."""
        self.push_screen(WelcomeScreen(self.setup_state))
