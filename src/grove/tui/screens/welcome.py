"""Welcome screen: explain Grove, confirm repo root, detect existing .grove."""

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Input, Static

from grove.tui.state import SetupState


class WelcomeScreen(Screen[None]):
    """First screen: welcome message, repo root, existing manifest notice."""

    BINDINGS = [  # noqa: RUF012
        ("q", "quit", "Quit"),
    ]

    def __init__(self, state: SetupState) -> None:
        """Store shared setup state for the flow.

        Args:
            state: Shared state (root, install_root, etc.).
        """
        super().__init__()
        self._state = state

    def compose(self) -> ComposeResult:
        """Build welcome layout: blurb, root path, notice, buttons.

        Yields:
            VerticalScroll containing Static, Input, optional notice, and buttons.
        """
        with VerticalScroll():
            yield Static(
                "[bold]Grove[/bold] installs a minimal context-engineering setup "
                "into your repo: rules, plans, handoffs, and optional packs "
                "(e.g. Python).\n"
                "You choose what to install; Grove writes [.grove/] and a manifest.",
                id="welcome-blurb",
            )
            yield Static("Project root:", classes="label")
            root_input = Input(
                value=str(self._state.root.resolve()),
                placeholder="Path to repo root",
                id="root-input",
            )
            yield root_input
            manifest_path = self._state.root / ".grove" / "manifest.toml"
            if manifest_path.exists():
                yield Static(
                    "Existing Grove found at .grove/; re-run will update.",
                    id="existing-notice",
                    classes="notice",
                )
            yield Container(
                Button("Next", variant="primary", id="next-btn"),
                Button("Quit", id="quit-btn"),
                id="button-row",
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle Next or Quit.

        Args:
            event: Button press event (next-btn or quit-btn).
        """
        if event.button.id == "quit-btn":
            self.app.exit()
            return
        if event.button.id == "next-btn":
            root_input = self.query_one("#root-input", Input)
            try:
                self._state.root = Path(root_input.value).resolve()
            except (ValueError, OSError):
                root_input.value = str(self._state.root)
                return
            if not self._state.root.is_dir():
                root_input.value = str(self._state.root)
                return
            # Next screen will be Repository analysis; for now we just exit
            # so the flow is runnable without all screens
            self.app.exit()
