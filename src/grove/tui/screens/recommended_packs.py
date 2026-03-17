"""Recommended packs screen: choose optional packs to install."""

from collections.abc import Callable
from typing import Any, ClassVar

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widget import Widget
from textual.widgets import Markdown, RadioButton, RadioSet, SelectionList

from grove.core.registry import discover_packs
from grove.tui.screens.base import GroveBaseScreen
from grove.tui.screens.components_preview import ComponentsPreviewScreen
from grove.tui.screens.pack_config import PackConfigScreen, has_setup_questions
from grove.tui.state import SetupState

# Step index for this screen (1-based); total steps match plan §7
RECOMMENDED_PACKS_STEP = 4
TOTAL_STEPS = 9

# Base pack is always installed; not shown as an optional choice
BASE_PACK_ID = "base"


def _required_label(required: list[Any]) -> str:
    """Return markdown string for the required (base) pack message.

    Args:
        required: List of required (base) pack objects; may be empty.

    Returns:
        Markdown string for the required pack line.
    """
    if required:
        return (
            f"**{required[0].name}** ({required[0].id}) — required, always installed."
        )
    return "**Base pack** (required) — always installed."


def _optional_selections(
    optional: list[Any],
    selected_ids: set[str],
    default_optional_selected: bool,
) -> list[tuple[str, str, bool]]:
    """Return (label, id, initial_checked) tuples for optional packs.

    Args:
        optional: List of optional pack objects.
        selected_ids: Currently selected pack ids.
        default_optional_selected: If True, all optional start selected.

    Returns:
        List of (label, id, initial_checked) for SelectionList.
    """
    return [
        (
            f"{p.name} ({p.id})",
            p.id,
            (p.id in selected_ids) if not default_optional_selected else True,
        )
        for p in optional
    ]


def _optional_packs_widget(
    optional_selections: list[tuple[str, str, bool]],
) -> list[Widget]:
    """SelectionList for optional packs, or message + empty list when none.

    Args:
        optional_selections: (label, id, initial_checked) tuples.

    Returns:
        List containing SelectionList, or message + empty SelectionList.
    """
    if optional_selections:
        return [SelectionList[str](*optional_selections, id="packs-optional-list")]
    return [
        Markdown("*No optional packs available.*", id="packs-none"),
        SelectionList[str](id="packs-optional-list"),
    ]


class RecommendedPacksScreen(GroveBaseScreen):
    """Screen 4: show required base pack, optional packs; select which to install."""

    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("enter", "next", "Next"),
        ("b", "back", "Back"),
        ("q", "quit", "Quit"),
        ("escape", "quit", "Quit"),
    ]

    def __init__(self, state: SetupState) -> None:
        """Store shared setup state.

        Args:
            state: Shared state (root, profile, selected_pack_ids, etc.).
        """
        super().__init__()
        self._state = state

    def compose_content(self) -> ComposeResult:
        """Build recommended packs: step, panel (required, list, radios).

        Yields:
            Step indicator and content container.
        """
        try:
            all_packs = discover_packs()
        except (FileNotFoundError, ValueError):
            all_packs = []
        required = [p for p in all_packs if p.id == BASE_PACK_ID]
        optional = [p for p in all_packs if p.id != BASE_PACK_ID]
        selected_ids = set(self._state.selected_pack_ids)
        default_optional_selected = not selected_ids or selected_ids <= {BASE_PACK_ID}
        optional_selections = _optional_selections(
            optional, selected_ids, default_optional_selected
        )
        content = Container(
            Markdown(_required_label(required), id="packs-required-message"),
            Markdown("**Optional packs:**", id="packs-optional-label"),
            *_optional_packs_widget(optional_selections),
            RadioSet(
                RadioButton("Next", value=True, id="action-next"),
                RadioButton("Back", value=True, id="action-back"),
                id="action-radios",
            ),
            id="recommended-packs-content",
        )
        content.border_title = "○ Recommended packs"
        with VerticalScroll():
            yield Markdown(
                f"*Step {RECOMMENDED_PACKS_STEP} of {TOTAL_STEPS}*",
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
        """Return to Core install screen."""
        self.app.pop_screen()

    def action_next(self) -> None:
        """Save selected pack ids; go to Pack config if any, else skip to next."""
        self._save_from_ui()
        if has_setup_questions(self._state.selected_pack_ids):
            self.app.push_screen(PackConfigScreen(self._state))
        else:
            self.app.push_screen(ComponentsPreviewScreen(self._state))

    def _save_from_ui(self) -> None:
        """Read optional pack selection from UI into state."""
        selected: list[str] = [BASE_PACK_ID]  # base always included
        optional_list = self.query_one("#packs-optional-list", SelectionList)
        selected.extend(optional_list.selected)
        self._state.selected_pack_ids = selected
