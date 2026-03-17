"""Repository analysis screen: show detector results and allow re-run."""

from typing import ClassVar, cast

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Markdown, RadioButton, RadioSet

from grove.analyzer import analyze
from grove.core.models import ProjectProfile
from grove.tui.screens.base import GroveBaseScreen, _Bindings
from grove.tui.screens.core_install import CoreInstallScreen
from grove.tui.state import SetupState

# Step index for this screen (1-based); total steps match plan §7
ANALYSIS_STEP = 2
TOTAL_STEPS = 9


def _format_profile_markdown(profile: ProjectProfile) -> str:
    """Format ProjectProfile as markdown for display.

    Args:
        profile: Analyzer result to format.

    Returns:
        Markdown string with labeled fields.
    """
    name = profile.project_name or "—"
    lang = profile.language or "—"
    pkg = profile.package_manager or "—"
    test = profile.test_framework or "—"
    tools = profile.tools if profile.tools else ["—"]
    tools_str = ", ".join(tools)
    # Use Markdown soft line breaks (two spaces before newline) for single-line spacing
    return f"""\
**Repository analysis**

**Project name:** {name}
**Language:** {lang}
**Package manager:** {pkg}
**Test framework:** {test}
**Tools:** {tools_str}
"""


class AnalysisScreen(GroveBaseScreen):
    """Screen 2: show repository analysis (profile); Next, Back, Re-run."""

    BINDINGS: ClassVar[_Bindings] = cast(
        _Bindings,
        [
            ("enter", "next", "Next"),
            ("b", "back", "Back"),
            ("r", "rerun", "Re-run analysis"),
            ("q", "quit", "Quit"),
            ("escape", "quit", "Quit"),
        ],
    )

    def __init__(self, state: SetupState) -> None:
        """Store shared setup state.

        Args:
            state: Shared state (root, profile, etc.).
        """
        super().__init__()
        self._state = state

    def compose_content(self) -> ComposeResult:
        """Build analysis layout: step indicator, panel (profile display, radios).

        Yields:
            VerticalScroll with step indicator and bordered analysis panel.
        """
        # Profile content (heading + fields) filled in on_mount / after re-run
        profile_block = Markdown(
            "**Repository analysis**\n\nAnalyzing…", id="profile-display"
        )
        content = Container(
            profile_block,
            RadioSet(
                RadioButton("Next", value=True, id="action-next"),
                RadioButton("Back", value=True, id="action-back"),
                RadioButton("Re-run analysis", value=True, id="action-rerun"),
                id="action-radios",
            ),
            id="analysis-content",
        )
        content.border_title = "○ Analysis"
        with VerticalScroll():
            yield Markdown(
                f"*Step {ANALYSIS_STEP} of {TOTAL_STEPS}*",
                id="step-indicator",
                classes="step-indicator",
            )
            yield content

    def on_mount(self) -> None:
        """Run/refresh profile display on mount."""
        self._ensure_profile()
        self._refresh_display()

    def _ensure_profile(self) -> None:
        """Run analyzer if profile not yet set."""
        if self._state.profile is None:
            self._state.profile = analyze(self._state.root)

    def _refresh_display(self) -> None:
        """Update profile display widget from state."""
        if self._state.profile is None:
            return
        display = self.query_one("#profile-display", Markdown)
        display.update(_format_profile_markdown(self._state.profile))

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Route radio choice to Back, Next, or Re-run action.

        Args:
            event: RadioSet.Changed with the pressed button.
        """
        radios = event.control
        pressed = radios.pressed_button if radios else None
        if pressed is None:
            return
        pid = pressed.id
        if pid == "action-back":
            self.action_back()
        elif pid == "action-next":
            self.action_next()
        elif pid == "action-rerun":
            self.action_rerun()

    def action_back(self) -> None:
        """Return to Welcome screen."""
        self.app.pop_screen()

    def action_next(self) -> None:
        """Go to Core install screen (screen 3)."""
        self.app.push_screen(CoreInstallScreen(self._state))

    def action_rerun(self) -> None:
        """Re-run analyzer and refresh profile display."""
        self._state.profile = analyze(self._state.root)
        self._refresh_display()
