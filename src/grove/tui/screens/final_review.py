"""Final review screen: summary and apply installation."""

from collections.abc import Callable
from importlib.metadata import version
from importlib.resources import as_file, files
from pathlib import Path
from typing import ClassVar, cast

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Markdown, RadioButton, RadioSet

from grove.core.file_ops import ApplyOptions, CollisionStrategy, apply
from grove.core.manifest import MANIFEST_SCHEMA_VERSION, save_manifest
from grove.core.models import (
    GroveSection,
    InitProvenance,
    InstalledPackRecord,
    ManifestState,
    ProjectSection,
)
from grove.core.registry import discover_packs
from grove.tui.screens.base import GroveBaseScreen, _Bindings
from grove.tui.screens.finish import FinishScreen
from grove.tui.state import SetupState

FINAL_REVIEW_STEP = 8
TOTAL_STEPS = 9


def _analysis_summary(profile: object) -> str:
    """Build a short analysis summary string from profile for manifest.

    Args:
        profile: Analysis profile with language, package_manager, test_framework, tools.

    Returns:
        Comma-separated summary string, or empty if no attributes.
    """
    parts: list[str] = []
    for attr in ("language", "package_manager", "test_framework"):
        val = getattr(profile, attr, None)
        if isinstance(val, str) and val:
            parts.append(val)
    tools = getattr(profile, "tools", None)
    if isinstance(tools, list) and tools:
        parts.extend(tools)
    return ", ".join(parts) if parts else ""


def _resolved_install_root(state: SetupState) -> Path:
    """Return install_root as an absolute path.

    Args:
        state: Shared setup state; uses root and install_root.

    Returns:
        Resolved absolute Path for install root.
    """
    root = state.root.resolve()
    install_root = state.install_root
    if not install_root.is_absolute():
        install_root = (root / install_root).resolve()
    return install_root


def _discover_builtin_packs() -> tuple[dict[str, Path], list]:
    """Discover builtin packs and return (pack_roots, packs list).

    Returns:
        (pack_roots map, list of pack objects).
    """
    builtins_ref = files("grove.packs") / "builtins"
    with as_file(builtins_ref) as builtins_path:
        builtins_dir = Path(builtins_path)
        packs = discover_packs(builtins_dir)
    pack_roots = {p.id: builtins_dir / p.id for p in packs}
    return pack_roots, packs


def _build_manifest(state: SetupState, packs: list) -> ManifestState:
    """Build ManifestState for apply from state and discovered packs.

    Args:
        state: Shared setup state; uses profile, selected_pack_ids, core toggles.
        packs: Discovered pack objects (from builtins).

    Returns:
        ManifestState for the apply step.
    """
    root = state.root.resolve()
    grove_version = version("grove")
    install_root_provenance = (
        state.install_root.as_posix()
        if not state.install_root.is_absolute()
        else ".grove"
    )
    return ManifestState(
        grove=GroveSection(
            version=grove_version,
            schema_version=MANIFEST_SCHEMA_VERSION,
        ),
        project=ProjectSection(
            root=str(root),
            analysis_summary=_analysis_summary(state.profile),
        ),
        packs=[
            InstalledPackRecord(id=p.id, version=p.version)
            for p in packs
            if p.id in state.selected_pack_ids
        ],
        generated_files=[],
        init_provenance=InitProvenance(
            install_root=install_root_provenance,
            core_include_adrs=state.core_include_adrs,
            core_include_handoffs=state.core_include_handoffs,
            core_include_scoped_rules=state.core_include_scoped_rules,
            core_include_memory=state.core_include_memory,
            core_include_skills_dir=state.core_include_skills_dir,
        ),
    )


class FinalReviewScreen(GroveBaseScreen):
    """Screen 8: final summary and Apply installation."""

    BINDINGS: ClassVar[_Bindings] = cast(
        _Bindings,
        [
            ("enter", "apply", "Apply installation"),
            ("b", "back", "Back"),
            ("q", "quit", "Quit"),
            ("escape", "quit", "Quit"),
        ],
    )

    def __init__(self, state: SetupState) -> None:
        """Store shared setup state.

        Args:
            state: Shared state (root, install_plan, selected_pack_ids, etc.).
        """
        super().__init__()
        self._state = state

    def compose_content(self) -> ComposeResult:
        """Build final review layout: step, summary panel, Apply/Back/Quit.

        Yields:
            Step indicator and content container.
        """
        state = self._state
        root = state.root.resolve()
        install_root = state.install_root
        if not install_root.is_absolute():
            install_root = (root / install_root).resolve()
        packs_str = (
            ", ".join(state.selected_pack_ids) if state.selected_pack_ids else "—"
        )
        file_count = len(state.install_plan.files) if state.install_plan else 0
        summary = (
            f"**Root:** `{root}`\n\n"
            f"**Install root:** `{install_root}`\n\n"
            f"**Packs:** {packs_str}\n\n"
            f"**Files in plan:** {file_count}"
        )
        content = Container(
            Markdown(summary, id="final-review-summary"),
            RadioSet(
                RadioButton("Apply installation", value=True, id="action-apply"),
                RadioButton("Back", value=True, id="action-back"),
                RadioButton("Quit", value=True, id="action-quit"),
                id="action-radios",
            ),
            id="final-review-content",
        )
        content.border_title = "○ Final review"
        with VerticalScroll():
            yield Markdown(
                f"*Step {FINAL_REVIEW_STEP} of {TOTAL_STEPS}*",
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
            "action-apply": self.action_apply,
            "action-quit": self.action_quit,
        }

    def action_back(self) -> None:
        """Pop to previous screen."""
        self.app.pop_screen()

    def action_apply(self) -> None:
        """Run install (apply plan, save manifest) then show Finish screen."""
        state = self._state
        plan = state.install_plan
        if plan is None or state.profile is None:
            self.app.exit()
            return
        install_root = _resolved_install_root(state)
        pack_roots, packs = _discover_builtin_packs()
        manifest = _build_manifest(state, packs)
        options = ApplyOptions(dry_run=False, collision_strategy="skip")
        overrides = {
            k: cast(CollisionStrategy, v)
            for k, v in state.conflict_choices.items()
            if v in ("overwrite", "skip", "rename")
        }
        updated = apply(
            plan,
            manifest,
            options,
            pack_roots,
            collision_overrides=overrides or None,
        )
        install_root.mkdir(parents=True, exist_ok=True)
        save_manifest(install_root / "manifest.toml", updated)
        state.manifest = updated
        self.app.push_screen(FinishScreen(state))

    def action_quit(self) -> None:
        """Exit the app."""
        self.app.exit()
