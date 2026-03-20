"""Manage dashboard: installed packs, analysis, sync; add pack, re-run, re-setup."""

from collections.abc import Callable
from typing import ClassVar, cast

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Input, Markdown, RadioButton, RadioSet, Static

from grove.analyzer import analyze
from grove.core.add import add_pack
from grove.core.manifest import save_manifest
from grove.core.models import ProjectProfile
from grove.core.registry import get_builtin_pack_roots_and_packs
from grove.core.tool_hooks import apply_tool_hooks
from grove.exceptions import GroveError
from grove.tui.screens.base import GroveBaseScreen, _Bindings
from grove.tui.screens.welcome import WelcomeScreen
from grove.tui.state import SetupState, setup_state_from_manifest


def _analysis_summary_text(profile: ProjectProfile) -> str:
    """Build short analysis summary string from profile for display.

    Args:
        profile: ProjectProfile from analyzer.

    Returns:
        Comma-separated summary (e.g. 'python, uv, pytest').
    """
    parts: list[str] = []
    for attr in ("language", "package_manager", "test_framework"):
        val = getattr(profile, attr, None)
        if isinstance(val, str) and val:
            parts.append(val)
    tools = getattr(profile, "tools", None)
    if isinstance(tools, list) and tools:
        parts.extend(tools)
    return ", ".join(parts) if parts else "—"


class ManageDashboardScreen(GroveBaseScreen):
    """Manage dashboard: installed packs, analysis summary, sync status; actions."""

    BINDINGS: ClassVar[_Bindings] = cast(
        _Bindings,
        [
            ("enter", "confirm", "Confirm"),
            ("q", "quit", "Quit"),
            ("escape", "quit", "Quit"),
        ],
    )

    def __init__(self, state: SetupState) -> None:
        """Store shared state (from manifest).

        Args:
            state: SetupState with root, manifest, selected_pack_ids from manifest.
        """
        super().__init__()
        self._state = state

    def compose_content(self) -> ComposeResult:
        """Build dashboard: packs and status as lists; actions as radios.

        Yields:
            VerticalScroll with bordered panel and radio actions.
        """
        manifest = self._state.manifest
        if manifest is not None:
            pack_bullets = (
                "\n".join(f"- {p.id}" for p in manifest.installed_packs) or "- —"
            )
            analysis_line = manifest.project.analysis_summary or "—"
        else:
            pack_bullets = "- —"
            analysis_line = "—"

        body = (
            "**Installed packs**\n\n"
            f"{pack_bullets}\n\n"
            "**Last analysis**\n\n"
            f"- {analysis_line}\n\n"
            "**Sync**\n\n"
            "- Run `grove sync` to re-render managed files."
        )
        content = Container(
            Markdown(body, id="manage-summary"),
            RadioSet(
                RadioButton("Add pack", value=True, id="action-add-pack"),
                RadioButton("Re-run analysis", value=True, id="action-rerun"),
                RadioButton("Full re-setup", value=True, id="action-resetup"),
                RadioButton("Quit", value=True, id="action-quit"),
                id="action-radios",
            ),
            id="manage-content",
        )
        content.border_title = "○ Grove — Manage"
        with VerticalScroll():
            yield content

    def _action_add_pack(self) -> None:
        """Open Add pack screen."""
        self.app.push_screen(AddPackScreen(self._state))

    def _action_resetup(self) -> None:
        """Open full re-setup (Welcome) screen."""
        self.app.push_screen(WelcomeScreen(self._state))

    def _radio_actions(self) -> dict[str, Callable[[], None]]:
        """Map radio button ids to actions.

        Returns:
            Dict mapping button id to callable.
        """
        return {
            "action-add-pack": self._action_add_pack,
            "action-rerun": self._rerun_analysis,
            "action-resetup": self._action_resetup,
            "action-quit": self.action_quit,
        }

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Run action only on Enter; do not run on mere selection change.

        Args:
            event: RadioSet.Changed (unused; we dispatch on Enter only).
        """
        # Base would run action on change; we run only on action_confirm (Enter)
        pass

    def action_confirm(self) -> None:
        """Run the action for the selected radio (Enter key)."""
        radios = self.query_one("#action-radios", RadioSet)
        pressed = radios.pressed_button if radios else None
        if pressed is None:
            return
        actions = self._radio_actions()
        if pressed.id in actions:
            actions[pressed.id]()

    def _rerun_analysis(self) -> None:
        """Run analyzer on root and show summary in a message."""
        try:
            profile = analyze(self._state.root)
            summary = _analysis_summary_text(profile)
            self.app.notify(f"Analysis: {summary}", title="Re-run analysis")
        except Exception as e:
            self.app.notify(str(e), title="Analysis failed", severity="error")

    def action_quit(self) -> None:
        """Exit the app."""
        self.app.exit()


class AddPackScreen(GroveBaseScreen):
    """Simple screen to enter pack id and add pack; on success refresh dashboard."""

    BINDINGS: ClassVar[_Bindings] = cast(
        _Bindings,
        [
            ("enter", "confirm", "Confirm"),
            ("escape", "cancel", "Cancel"),
        ],
    )

    def __init__(self, state: SetupState) -> None:
        """Store state for root/manifest path and refresh after add.

        Args:
            state: SetupState with root; used to resolve manifest path.
        """
        super().__init__()
        self._state = state

    def compose_content(self) -> ComposeResult:
        """Build layout: pack id input and Add / Cancel radios.

        Yields:
            Container with input and radio actions.
        """
        content = Container(
            Static("Pack id to add (e.g. python):", id="add-pack-label"),
            Input(placeholder="pack id", id="add-pack-input"),
            RadioSet(
                RadioButton("Add pack", value=True, id="add-pack-submit"),
                RadioButton("Cancel", value=True, id="add-pack-cancel"),
                id="add-pack-radios",
            ),
            id="add-pack-content",
        )
        content.border_title = "○ Add pack"
        with VerticalScroll():
            yield content

    def on_mount(self) -> None:
        """Focus the pack id input."""
        self.query_one("#add-pack-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """When user presses Enter in the pack id input, run Add pack.

        Args:
            event: Input.Submitted from the pack id input.
        """
        if getattr(event.input, "id", None) == "add-pack-input":
            self._do_add()

    def _radio_actions(self) -> dict[str, Callable[[], None]]:
        """Map radio button ids to actions.

        Returns:
            Dict mapping radio button id to callable.
        """
        return {
            "add-pack-submit": self._do_add,
            "add-pack-cancel": self.action_cancel,
        }

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Run action only on Enter; do not run on mere selection change.

        Args:
            event: RadioSet.Changed (unused; we dispatch on Enter only).
        """
        pass

    def action_confirm(self) -> None:
        """Run Add pack when focus is in input; otherwise run selected radio action."""
        focused = self.focused
        if focused is not None and getattr(focused, "id", None) == "add-pack-input":
            self._do_add()
            return
        radios = self.query_one("#add-pack-radios", RadioSet)
        pressed = radios.pressed_button if radios else None
        if pressed is None:
            return
        actions = self._radio_actions()
        if pressed.id in actions:
            actions[pressed.id]()

    def action_cancel(self) -> None:
        """Cancel and pop screen."""
        self.app.pop_screen()

    def _do_add(self) -> None:
        """Call add_pack, save manifest; on success refresh dashboard and pop."""
        pack_input = self.query_one("#add-pack-input", Input)
        pack_id = (pack_input.value or "").strip()
        if not pack_id:
            self.app.notify("Enter a pack id", severity="error")
            return
        manifest_path = self._state.root / ".grove" / "manifest.toml"
        try:
            pack_roots, packs = get_builtin_pack_roots_and_packs()
            updated = add_pack(
                self._state.root,
                manifest_path,
                pack_id,
                pack_roots,
                packs,
            )
            profile = analyze(self._state.root)
            apply_tool_hooks(self._state.root, updated, packs, profile)
            save_manifest(manifest_path, updated)
        except (GroveError, ValueError, KeyError) as e:
            self.app.notify(str(e), title="Add pack failed", severity="error")
            return
        self.app.notify(f"Added pack {pack_id}.", title="Pack installed")
        refreshed = setup_state_from_manifest(manifest_path, self._state.root)
        self.app.pop_screen()
        self.app.push_screen(ManageDashboardScreen(refreshed))
