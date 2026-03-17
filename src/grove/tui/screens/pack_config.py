"""Pack configuration screen: dynamic setup questions from selected packs."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, ClassVar, cast

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widget import Widget
from textual.widgets import Input, Markdown, RadioButton, RadioSet, Select, Switch

from grove.core.registry import discover_packs
from grove.tui.screens.base import GroveBaseScreen, _Bindings
from grove.tui.screens.components_preview import ComponentsPreviewScreen
from grove.tui.state import SetupState

# Step index for this screen (1-based); total steps match plan §7
PACK_CONFIG_STEP = 5
TOTAL_STEPS = 9


def _normalize_question(item: object, pack_id: str) -> dict[str, Any] | None:
    """Convert one raw setup_questions item to a question dict, or None if invalid.

    Args:
        item: Raw item from pack contributes setup_questions (dict or other).
        pack_id: Pack id this question belongs to.

    Returns:
        Normalized question dict or None if item is invalid.
    """
    if not isinstance(item, dict):
        return None
    qid = item.get("id")
    prompt = item.get("prompt")
    qtype = item.get("type", "text")
    if not qid or not prompt:
        return None
    opts = item.get("options")
    return {
        "pack_id": pack_id,
        "id": str(qid),
        "prompt": str(prompt),
        "type": str(qtype) if qtype in ("text", "select", "checkbox") else "text",
        "options": opts if isinstance(opts, list) else [],
        "default": item.get("default"),
    }


def _collect_setup_questions(
    selected_pack_ids: list[str],
) -> list[dict[str, Any]]:
    """Gather setup_questions from selected packs.

    Each question dict has: pack_id, id, prompt, type ("text"|"select"|"checkbox"),
    and optionally options (list[str]), default (str or bool).

    Args:
        selected_pack_ids: List of selected pack ids to collect questions from.

    Returns:
        Flat list of question dicts; empty if no packs or no questions.
    """
    try:
        all_packs = discover_packs()
    except (FileNotFoundError, ValueError):
        return []
    by_id = {p.id: p for p in all_packs}
    out: list[dict[str, Any]] = []
    for pack_id in selected_pack_ids:
        pack = by_id.get(pack_id)
        if not pack:
            continue
        raw = pack.contributes.get("setup_questions")
        if not isinstance(raw, list):
            continue
        for item in raw:
            q = _normalize_question(item, pack_id)
            if q is not None:
                out.append(q)
    return out


def _widgets_for_checkbox(
    q: dict[str, Any], qid_attr: str, current: str | bool | None
) -> list[Widget]:
    """Widgets for a checkbox question.

    Args:
        q: Question dict with prompt, default.
        qid_attr: Base id for widget ids.
        current: Current answer or None.

    Returns:
        List of Switch and Markdown widgets.
    """
    default = q.get("default", True)
    val = current if current is not None else default
    return [
        Switch(value=bool(val), id=f"{qid_attr}-switch"),
        Markdown(q["prompt"], id=f"{qid_attr}-label"),
    ]


def _widgets_for_select(
    q: dict[str, Any], qid_attr: str, current: str | bool | None
) -> list[Widget]:
    """Widgets for a select or select-without-options (text input) question.

    Args:
        q: Question dict with prompt, options, default.
        qid_attr: Base id for widget ids.
        current: Current answer or None.

    Returns:
        List of Markdown and Select or Input widgets.
    """
    prompt = q["prompt"]
    options = q.get("options") or []
    opt_tuples = [(str(o), o) for o in options]
    default = options[0] if options else None
    val = current if current is not None and current in options else default
    if opt_tuples:
        sel = Select(opt_tuples, value=val, id=f"{qid_attr}-select")
        return [Markdown(f"**{prompt}**", id=f"{qid_attr}-label"), sel]
    return [
        Markdown(f"**{prompt}**", id=f"{qid_attr}-label"),
        Input(value=str(val or ""), placeholder=prompt, id=f"{qid_attr}-input"),
    ]


def _widgets_for_text(
    q: dict[str, Any], qid_attr: str, current: str | bool | None
) -> list[Widget]:
    """Widgets for a text question.

    Args:
        q: Question dict with prompt, default.
        qid_attr: Base id for widget ids.
        current: Current answer or None.

    Returns:
        List of Markdown and Input widgets.
    """
    prompt = q["prompt"]
    default = q.get("default") or ""
    val = str(current) if current is not None else str(default)
    return [
        Markdown(f"**{prompt}**", id=f"{qid_attr}-label"),
        Input(value=val, placeholder=prompt, id=f"{qid_attr}-input"),
    ]


def _widgets_for_question(
    q: dict[str, Any],
    i: int,
    answers: dict[str, Any],
) -> list[Widget]:
    """Return the list of widgets for one setup question.

    Args:
        q: Question dict (pack_id, id, prompt, type, options, default).
        i: Question index for widget ids.
        answers: Current config_answers for prefill.

    Returns:
        List of widgets for this question.
    """
    key = f"{q['pack_id']}.{q['id']}"
    current = answers.get(key)
    qid_attr = f"pack-config-q-{i}"
    if q["type"] == "checkbox":
        return _widgets_for_checkbox(q, qid_attr, current)
    if q["type"] == "select":
        return _widgets_for_select(q, qid_attr, current)
    return _widgets_for_text(q, qid_attr, current)


def has_setup_questions(selected_pack_ids: list[str]) -> bool:
    """Return True if any selected pack has setup_questions to show.

    Use this to skip the Pack configuration screen when there are no questions.

    Args:
        selected_pack_ids: List of selected pack ids.

    Returns:
        True if any pack has setup_questions.
    """
    return len(_collect_setup_questions(selected_pack_ids)) > 0


class PackConfigScreen(GroveBaseScreen):
    """Screen 5: configure selected packs via their setup_questions."""

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
            state: Shared state (selected_pack_ids, config_answers, etc.).
        """
        super().__init__()
        self._state = state
        self._questions: list[dict[str, Any]] = []

    def compose_content(self) -> ComposeResult:
        """Build pack config: step, panel (intro + questions or message, radios).

        Yields:
            Step indicator and content container.
        """
        self._questions = _collect_setup_questions(self._state.selected_pack_ids)
        answers = self._state.config_answers

        panel_children: list = [
            Markdown(
                "Configure options for the selected packs. "
                "Change any values below, then choose **Next**.",
                id="pack-config-intro",
            ),
        ]
        if not self._questions:
            panel_children.append(
                Markdown(
                    "*No configuration questions for the selected packs.*",
                    id="pack-config-none",
                ),
            )
        else:
            for i, q in enumerate(self._questions):
                panel_children.extend(_widgets_for_question(q, i, answers))

        panel_children.append(
            RadioSet(
                RadioButton("Next", value=True, id="action-next"),
                RadioButton("Back", value=True, id="action-back"),
                id="action-radios",
            ),
        )
        content = Container(*panel_children, id="pack-config-content")
        content.border_title = "○ Pack configuration"
        with VerticalScroll():
            yield Markdown(
                f"*Step {PACK_CONFIG_STEP} of {TOTAL_STEPS}*",
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
        """Save answers and push Components preview screen."""
        self._save_from_ui()
        self.app.push_screen(ComponentsPreviewScreen(self._state))

    def _save_from_ui(self) -> None:
        """Read answers from UI into state.config_answers."""
        for i, q in enumerate(self._questions):
            key = f"{q['pack_id']}.{q['id']}"
            qid_attr = f"pack-config-q-{i}"
            qtype = q["type"]
            if qtype == "checkbox":
                sw = self.query_one(f"#{qid_attr}-switch", Switch)
                self._state.config_answers[key] = sw.value
            elif qtype == "select":
                options = q.get("options") or []
                if options:
                    sel = self.query_one(f"#{qid_attr}-select", Select)
                    self._state.config_answers[key] = sel.value
                else:
                    inp = self.query_one(f"#{qid_attr}-input", Input)
                    self._state.config_answers[key] = inp.value
            else:
                inp = self.query_one(f"#{qid_attr}-input", Input)
                self._state.config_answers[key] = inp.value
