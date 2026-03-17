"""Welcome screen: explain Grove, confirm repo root, detect existing .grove."""

from pathlib import Path
from typing import ClassVar

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Input, Markdown, RadioButton, RadioSet

from grove.tui.screens.analysis import AnalysisScreen
from grove.tui.screens.base import GroveBaseScreen
from grove.tui.state import SetupState

# Step index for this screen (1-based); total steps match plan §7
WELCOME_STEP = 1
TOTAL_STEPS = 9

WELCOME_MARKDOWN = """\
**Grove** installs a minimal context-engineering setup into your repo: \
rules, plans, handoffs, and optional packs (e.g. Python).

You choose what to install; Grove writes `.grove/` and a manifest.

> *Agents do not hold knowledge — the grove does.*
"""


class WelcomeScreen(GroveBaseScreen):
    """First screen: welcome message, repo root, existing manifest notice."""

    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("enter", "next", "Next"),
        ("q", "quit", "Quit"),
        ("escape", "quit", "Quit"),
    ]

    def __init__(self, state: SetupState) -> None:
        """Store shared setup state for the flow.

        Args:
            state: Shared state (root, install_root, etc.).
        """
        super().__init__()
        self._state = state

    def compose_content(self) -> ComposeResult:
        """Build welcome layout: step indicator, panel (markdown, root, notice, radios).

        Yields:
            VerticalScroll with step indicator and bordered content panel.
        """
        manifest_path = self._state.root / ".grove" / "manifest.toml"
        panel_children: list = [
            Markdown(WELCOME_MARKDOWN, id="welcome-markdown"),
            Markdown("**Project root:**", id="root-label"),
            Input(
                value=str(self._state.root.resolve()),
                placeholder="Path to repo root",
                id="root-input",
            ),
        ]
        if manifest_path.exists():
            panel_children.append(
                Markdown(
                    "*Existing Grove found at .grove/; re-run will update.*",
                    id="existing-notice",
                    classes="notice",
                )
            )
        panel_children.append(
            RadioSet(
                RadioButton("Continue", value=True, id="action-continue"),
                RadioButton("Quit", value=False, id="action-quit"),
                id="action-radios",
            )
        )
        content = Container(*panel_children, id="welcome-content")
        content.border_title = "○ Welcome"
        with VerticalScroll():
            yield Markdown(
                f"*Step {WELCOME_STEP} of {TOTAL_STEPS}*",
                id="step-indicator",
                classes="step-indicator",
            )
            yield content

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Handle radio choice: Continue or Quit.

        Args:
            event: RadioSet.Changed with the pressed button.
        """
        radios = event.control
        pressed = radios.pressed_button if radios else None
        if pressed is not None and pressed.id == "action-quit":
            self.app.exit()
            return
        if pressed is not None and pressed.id == "action-continue":
            self.action_next()

    def action_next(self) -> None:
        """Handle Next (Enter key or Continue selection)."""
        root_input = self.query_one("#root-input", Input)
        try:
            self._state.root = Path(root_input.value).resolve()
        except (ValueError, OSError):
            root_input.value = str(self._state.root)
            return
        if not self._state.root.is_dir():
            root_input.value = str(self._state.root)
            return
        self.app.push_screen(AnalysisScreen(self._state))
