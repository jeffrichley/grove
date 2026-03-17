"""Textual app for grove init and manage: holds state and drives screen flow."""

from pathlib import Path
from typing import ClassVar, Literal, cast

from textual.app import App, ComposeResult
from textual.binding import Binding

from grove.tui.screens.manage_dashboard import ManageDashboardScreen
from grove.tui.screens.welcome import WelcomeScreen
from grove.tui.state import SetupState

_Bindings = list[Binding | tuple[str, str] | tuple[str, str, str]]


class GroveInitApp(App[None]):
    """TUI for grove init (welcome -> ... -> finish) or manage (dashboard)."""

    TITLE = "▸ Grove init"
    CSS_PATH = str(Path(__file__).parent / "grove_init.tcss")
    BINDINGS: ClassVar[_Bindings] = cast(
        _Bindings,
        [
            ("q", "quit", "Quit"),
            ("escape", "quit", "Quit"),
        ],
    )

    # Total steps in the init flow (for step indicator)
    TOTAL_STEPS = 9

    def __init__(
        self,
        state: SetupState | None = None,
        mode: Literal["init", "manage"] = "init",
    ) -> None:
        """Initialize app with optional setup state and mode.

        Args:
            state: Shared state for the flow; defaults to new SetupState.
            mode: 'init' for first-time wizard; 'manage' for dashboard when
                manifest exists.
        """
        super().__init__()
        self.setup_state = state if state is not None else SetupState()
        self._mode = mode
        if mode == "manage":
            self.TITLE = "▸ Grove manage"

    def compose(self) -> ComposeResult:
        """Compose app: no widgets; the pushed screen provides all content.

        Yields:
            Nothing; the pushed screen provides content.
        """
        yield from ()  # app has no widgets; pushed screen provides content

    def on_mount(self) -> None:
        """Push the first screen: Welcome (init) or ManageDashboard (manage)."""
        if self._mode == "manage":
            self.push_screen(ManageDashboardScreen(self.setup_state))
        else:
            self.push_screen(WelcomeScreen(self.setup_state))
