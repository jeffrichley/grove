"""Components preview screen: list files to create and their status."""

from collections.abc import Callable
from typing import ClassVar, cast

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Markdown, RadioButton, RadioSet

from grove.analyzer import analyze
from grove.core.composer import compose
from grove.core.registry import discover_packs
from grove.tui.screens.base import GroveBaseScreen, _Bindings
from grove.tui.screens.conflicts import ConflictsScreen, has_conflicts
from grove.tui.screens.final_review import FinalReviewScreen
from grove.tui.state import SetupState

# Step index for this screen (1-based); total steps match plan §7
COMPONENTS_PREVIEW_STEP = 6
TOTAL_STEPS = 9


def _ensure_plan(state: SetupState) -> None:
    """Compute install plan and set state.install_plan if not already set.

    Args:
        state: Shared setup state; install_plan and profile may be updated.
    """
    if state.install_plan is not None:
        return
    if state.profile is None:
        state.profile = analyze(state.root)
    root = state.root.resolve()
    install_root = state.install_root
    if not install_root.is_absolute():
        install_root = (root / install_root).resolve()
    try:
        packs = discover_packs()
    except (FileNotFoundError, ValueError):
        state.install_plan = None
        return
    try:
        state.install_plan = compose(
            state.profile,
            state.selected_pack_ids,
            install_root,
            packs,
        )
    except ValueError:
        state.install_plan = None


def _plan_summary_and_rows(state: SetupState) -> tuple[str, list[tuple[str, str]]]:
    """Return summary line and list of (path_display, status) for the plan.

    Args:
        state: Shared setup state; uses install_plan.

    Returns:
        (summary_markdown, [(path_str, "new"|"exists"), ...])
    """
    plan = state.install_plan
    if plan is None or not plan.files:
        return "*No files in the install plan.*", []
    install_root = plan.install_root.resolve()
    rows: list[tuple[str, str]] = []
    for planned in plan.files:
        dst = (
            (install_root / planned.dst).resolve()
            if not planned.dst.is_absolute()
            else planned.dst.resolve()
        )
        path_display = str(planned.dst) if not planned.dst.is_absolute() else str(dst)
        status = "exists" if dst.exists() else "new"
        rows.append((path_display, status))
    new_count = sum(1 for _, s in rows if s == "new")
    exist_count = len(rows) - new_count
    summary = (
        f"**{len(rows)}** files in plan: **{new_count}** to create, "
        f"**{exist_count}** already exist."
    )
    return summary, rows


class ComponentsPreviewScreen(GroveBaseScreen):
    """Screen 6: preview components (files) to be created or updated."""

    BINDINGS: ClassVar[_Bindings] = cast(
        _Bindings,
        [
            ("enter", "next", "Next"),
            ("b", "back", "Back"),
            ("q", "quit", "Quit"),
            ("escape", "quit", "Quit"),
        ],
    )

    def __init__(self, state: SetupState) -> None:
        """Store shared setup state.

        Args:
            state: Shared state (root, profile, install_plan, etc.).
        """
        super().__init__()
        self._state = state

    def compose_content(self) -> ComposeResult:
        """Build components preview: step, panel (summary, list, radios).

        Yields:
            Step indicator and content container.
        """
        _ensure_plan(self._state)
        summary, rows = _plan_summary_and_rows(self._state)
        lines: list[str] = [summary, ""]
        for path_display, status in rows:
            lines.append(f"- `{path_display}` — **{status}**")
        list_md = "\n".join(lines) if lines else "*No files to show.*"
        content = Container(
            Markdown(list_md, id="components-preview-list"),
            RadioSet(
                RadioButton("Next", value=True, id="action-next"),
                RadioButton("Back", value=True, id="action-back"),
                id="action-radios",
            ),
            id="components-preview-content",
        )
        content.border_title = "○ Components preview"
        with VerticalScroll():
            yield Markdown(
                f"*Step {COMPONENTS_PREVIEW_STEP} of {TOTAL_STEPS}*",
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
        """Pop to previous screen."""
        self.app.pop_screen()

    def action_next(self) -> None:
        """Proceed to Conflicts (screen 7) if any, else Final review (screen 8)."""
        if has_conflicts(self._state):
            self.app.push_screen(ConflictsScreen(self._state))
        else:
            self.app.push_screen(FinalReviewScreen(self._state))
