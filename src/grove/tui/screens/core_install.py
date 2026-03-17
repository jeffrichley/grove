"""Core install screen: Base Pack, install root, and base toggles."""

from collections.abc import Callable
from pathlib import Path
from typing import ClassVar

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Input, Markdown, RadioButton, RadioSet, SelectionList

from grove.tui.screens.base import GroveBaseScreen
from grove.tui.screens.recommended_packs import RecommendedPacksScreen
from grove.tui.state import SetupState

# Step index for this screen (1-based); total steps match plan §7
CORE_INSTALL_STEP = 3
TOTAL_STEPS = 9


def format_install_root_display(root: Path, install_root: Path) -> str:
    """Return install root as a string for display: relative to root when possible.

    When install_root is absolute and under root, returns the relative path
    (e.g. ".grove"). When it is not under root (e.g. different drive on Windows),
    returns the absolute path string.

    Args:
        root: Project root path.
        install_root: Install root path (may be relative or absolute).

    Returns:
        String to show in the install-root input (relative preferred).
    """
    if not install_root.is_absolute():
        return install_root.as_posix()
    try:
        return install_root.relative_to(root).as_posix()
    except ValueError:
        return str(install_root)


# SelectionList value keys for "include in base install" options
CORE_OPTION_ADRS = "adrs"
CORE_OPTION_HANDOFFS = "handoffs"
CORE_OPTION_SCOPED_RULES = "scoped_rules"
CORE_OPTION_MEMORY = "memory"
CORE_OPTION_SKILLS_DIR = "skills_dir"


class CoreInstallScreen(GroveBaseScreen):
    """Screen 3: Base Pack, install root, toggles for ADRs, handoffs, etc."""

    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("enter", "next", "Next"),
        ("b", "back", "Back"),
        ("q", "quit", "Quit"),
        ("escape", "quit", "Quit"),
    ]

    def __init__(self, state: SetupState) -> None:
        """Store shared setup state.

        Args:
            state: Shared state (root, install_root, core toggles, etc.).
        """
        super().__init__()
        self._state = state

    def compose_content(self) -> ComposeResult:
        """Build core install: step, panel (base message, root, toggles, radios).

        Yields:
            Step indicator and content container.
        """
        install_root_str = format_install_root_display(
            self._state.root, self._state.install_root
        )
        content = Container(
            Markdown(
                "**Base Pack (required)** is always installed. It adds:\n\n"
                "- GROVE.md\n"
                "- plans/\n"
                "- handoffs/\n"
                "- decisions/ (ADRs)",
                id="core-base-message",
            ),
            Markdown("**Install root:**", id="core-root-label"),
            Input(
                value=install_root_str,
                placeholder="e.g. .grove",
                id="core-install-root-input",
            ),
            Markdown("**Select optional base components:**", id="core-toggles-label"),
            SelectionList[str](
                ("ADRs (decisions)", CORE_OPTION_ADRS, self._state.core_include_adrs),
                ("Handoffs", CORE_OPTION_HANDOFFS, self._state.core_include_handoffs),
                (
                    "Scoped rules",
                    CORE_OPTION_SCOPED_RULES,
                    self._state.core_include_scoped_rules,
                ),
                (
                    "Memory / preferences",
                    CORE_OPTION_MEMORY,
                    self._state.core_include_memory,
                ),
                (
                    "Skills directory",
                    CORE_OPTION_SKILLS_DIR,
                    self._state.core_include_skills_dir,
                ),
                id="core-options-list",
            ),
            RadioSet(
                RadioButton("Next", value=True, id="action-next"),
                RadioButton("Back", value=True, id="action-back"),
                id="action-radios",
            ),
            id="core-install-content",
        )
        content.border_title = "○ Core install"
        with VerticalScroll():
            yield Markdown(
                f"*Step {CORE_INSTALL_STEP} of {TOTAL_STEPS}*",
                id="step-indicator",
                classes="step-indicator",
            )
            yield content

    def _radio_actions(self) -> dict[str, Callable[[], None]]:
        """Map radio button ids to actions.

        Returns:
            Dict mapping button id to callable.
        """
        return {
            "action-back": self.action_back,
            "action-next": self.action_next,
        }

    def action_back(self) -> None:
        """Return to Analysis screen."""
        self.app.pop_screen()

    def action_next(self) -> None:
        """Save install root and toggles, then go to Recommended packs (screen 4)."""
        self._save_from_ui()
        self.app.push_screen(RecommendedPacksScreen(self._state))

    def _save_from_ui(self) -> None:
        """Read install root and selection list from UI into state."""
        root_input = self.query_one("#core-install-root-input", Input)
        raw = root_input.value.strip() or ".grove"
        self._state.install_root = Path(raw)
        selected = set(self.query_one("#core-options-list", SelectionList).selected)
        self._state.core_include_adrs = CORE_OPTION_ADRS in selected
        self._state.core_include_handoffs = CORE_OPTION_HANDOFFS in selected
        self._state.core_include_scoped_rules = CORE_OPTION_SCOPED_RULES in selected
        self._state.core_include_memory = CORE_OPTION_MEMORY in selected
        self._state.core_include_skills_dir = CORE_OPTION_SKILLS_DIR in selected
