"""Conflicts screen: choose action per conflicting path (overwrite / keep / rename)."""

from collections.abc import Callable
from typing import ClassVar, cast

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Markdown, RadioButton, RadioSet, Select, Static

from grove.tui.screens.base import GroveBaseScreen, _Bindings
from grove.tui.screens.final_review import FinalReviewScreen
from grove.tui.state import SetupState

CONFLICTS_STEP = 7
TOTAL_STEPS = 9

CONFLICT_ACTIONS = [
    ("Overwrite", "overwrite"),
    ("Keep existing", "skip"),
    ("Rename", "rename"),
]


def get_conflicting_paths(state: SetupState) -> list[tuple[str, str]]:
    """Return list of (path_key, path_display) for plan files that already exist.

    path_key is used as key in state.conflict_choices; path_display is shown in UI.

    Args:
        state: Shared setup state; uses install_plan.

    Returns:
        List of (path_key, path_display) for existing destinations.
    """
    plan = state.install_plan
    if plan is None or not plan.files:
        return []
    install_root = plan.install_root.resolve()
    out: list[tuple[str, str]] = []
    for planned in plan.files:
        dst = (
            (install_root / planned.dst).resolve()
            if not planned.dst.is_absolute()
            else planned.dst.resolve()
        )
        if not dst.exists():
            continue
        path_key = planned.dst.as_posix() if not planned.dst.is_absolute() else str(dst)
        path_display = path_key if not planned.dst.is_absolute() else str(dst)
        out.append((path_key, path_display))
    return out


def has_conflicts(state: SetupState) -> bool:
    """Return True if the install plan has any destination paths that already exist.

    Args:
        state: Shared setup state; uses install_plan.

    Returns:
        True if any plan destination path exists on disk.
    """
    return len(get_conflicting_paths(state)) > 0


class ConflictsScreen(GroveBaseScreen):
    """Screen 7: resolve conflicts (overwrite / keep existing / rename) per path."""

    BINDINGS: ClassVar[_Bindings] = cast(
        _Bindings,
        [
            ("enter", "apply_choices", "Apply choices"),
            ("b", "back", "Back"),
            ("q", "quit", "Quit"),
            ("escape", "quit", "Quit"),
        ],
    )

    def __init__(self, state: SetupState) -> None:
        """Store shared setup state.

        Args:
            state: Shared state (root, install_plan, conflict_choices, etc.).
        """
        super().__init__()
        self._state = state
        self._path_keys: list[str] = []

    def compose_content(self) -> ComposeResult:
        """Build conflicts: step, panel (path + Select per row), Apply/Back.

        Yields:
            Step indicator and content container.
        """
        conflicts = get_conflicting_paths(self._state)
        self._path_keys = [path_key for path_key, _ in conflicts]
        choices = self._state.conflict_choices

        panel_children: list = [
            Markdown(
                "Paths exist. Choose an action for each, then **Apply choices**.",
                id="conflicts-intro",
            ),
        ]
        for i, (path_key, path_display) in enumerate(conflicts):
            current = choices.get(path_key, "skip")
            sel_id = f"conflict-select-{i}"
            opt_tuples = [(label, value) for label, value in CONFLICT_ACTIONS]
            panel_children.append(Static(f"`{path_display}`", id=f"conflict-path-{i}"))
            panel_children.append(
                Select(
                    opt_tuples,
                    value=current
                    if current in ("overwrite", "skip", "rename")
                    else "skip",
                    id=sel_id,
                )
            )
        panel_children.append(
            RadioSet(
                RadioButton("Apply choices", value=True, id="action-apply"),
                RadioButton("Back", value=True, id="action-back"),
                id="action-radios",
            ),
        )
        content = Container(*panel_children, id="conflicts-content")
        content.border_title = "○ Conflicts"
        with VerticalScroll():
            yield Markdown(
                f"*Step {CONFLICTS_STEP} of {TOTAL_STEPS}*",
                id="step-indicator",
                classes="step-indicator",
            )
            yield content

    def _save_choices(self) -> None:
        """Read Select values and write to state.conflict_choices."""
        for i, path_key in enumerate(self._path_keys):
            sel = self.query_one(f"#conflict-select-{i}", Select)
            val = sel.value
            self._state.conflict_choices[path_key] = (
                val if isinstance(val, str) else "skip"
            )

    def _radio_actions(self) -> dict[str, Callable[[], None]]:
        """Map radio button ids to actions.

        Returns:
            Dict mapping button id to callable.
        """
        return {
            "action-back": self.action_back,
            "action-apply": self.action_apply_choices,
        }

    def action_back(self) -> None:
        """Pop to previous screen."""
        self.app.pop_screen()

    def action_apply_choices(self) -> None:
        """Save choices and push Final review screen."""
        self._save_choices()
        self.app.push_screen(FinalReviewScreen(self._state))
