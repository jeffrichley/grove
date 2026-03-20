"""Filesystem mutation helpers for `grove remove`."""

from collections.abc import Mapping
from pathlib import Path

from grove.core.composer import compose
from grove.core.file_ops import render_planned_file
from grove.core.models import (
    CodexSkillTargetState,
    GeneratedFileRecord,
    InstallPlan,
    ManifestState,
    PlannedFile,
    RemovePlan,
    ToolHookTargetState,
)
from grove.core.remove_impl import RemoveContext
from grove.core.sync import _sync_target_content
from grove.core.tool_hooks import (
    _upsert_block,
    plan_codex_skill_targets,
    plan_tool_hook_targets,
)

_DELETE_ACTION = "delete"
_PRESERVE_ACTION = "preserve"
_REWRITE_ACTION = "rewrite"
_MANAGED_FILE_SURFACE = "managed_file"
_PACK_LOCAL_SKILL_SURFACE = "pack_local_skill"
_TOOL_HOOK_SURFACE = "tool_hook"
_MANAGED_BLOCK_HOOK = "managed_block"


def apply_remove(
    context: RemoveContext,
    plan: RemovePlan,
    *,
    dry_run: bool = False,
) -> ManifestState:
    """Apply a remove plan and return the updated manifest state.

    Args:
        context: Shared remove-planning inputs.
        plan: Precomputed remove plan to apply.
        dry_run: If True, do not mutate files or manifest.

    Returns:
        Updated manifest state for the remaining installed packs.
    """
    remaining_plan = compose(
        context.profile,
        plan.remaining_pack_ids,
        _install_root(context.manifest),
        context.packs,
    )
    remaining_files = {
        _project_relative_from_install_root(
            context,
            planned.dst.relative_to(remaining_plan.install_root).as_posix(),
        ): planned
        for planned in remaining_plan.files
    }
    current_hook_states = _tool_hook_states(
        context,
        installed=True,
        remaining_pack_ids=None,
    )
    remaining_hook_states = _tool_hook_states(
        context,
        installed=False,
        remaining_pack_ids=plan.remaining_pack_ids,
    )
    remaining_skill_states = {
        state.path: state
        for state in plan_codex_skill_targets(
            context.root,
            context.packs,
            context.profile,
            set(plan.remaining_pack_ids),
        )
    }

    if not dry_run:
        for change in plan.changes:
            if change.action == _PRESERVE_ACTION:
                continue
            if change.surface == _MANAGED_FILE_SURFACE:
                _apply_managed_file_change(
                    context,
                    change.path,
                    change.action,
                    remaining_files,
                )
                continue
            if change.surface == _TOOL_HOOK_SURFACE:
                _apply_tool_hook_change(
                    context,
                    change.path,
                    change.action,
                    current_hook_states,
                    remaining_hook_states,
                )
                continue
            if change.surface == _PACK_LOCAL_SKILL_SURFACE:
                _apply_pack_local_skill_change(
                    context,
                    change.path,
                    change.action,
                    remaining_skill_states,
                )
    return _updated_manifest(context.manifest, plan.remaining_pack_ids, remaining_plan)


def _apply_managed_file_change(
    context: RemoveContext,
    path: str,
    action: str,
    remaining_files: Mapping[str, PlannedFile],
) -> None:
    """Delete or rewrite one managed Grove file.

    Args:
        context: Shared remove-planning inputs.
        path: Project-root-relative managed file path.
        action: Planned action for the file.
        remaining_files: Remaining desired managed files keyed by project path.
    """
    target = (context.root / path).resolve()
    if action == _DELETE_ACTION:
        if target.exists():
            target.unlink()
        _prune_empty_parent_dirs(target.parent, stop_at=context.root)
        return
    planned = remaining_files.get(path)
    if planned is None:
        raise ValueError(f"Missing remaining plan for managed file rewrite: {path}")
    desired = render_planned_file(planned, context.pack_roots)
    current = target.read_text(encoding="utf-8") if target.exists() else None
    next_content = _sync_target_content(current, desired)
    if current == next_content:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(next_content, encoding="utf-8")


def _apply_tool_hook_change(
    context: RemoveContext,
    path: str,
    action: str,
    current_states: dict[str, ToolHookTargetState],
    remaining_states: dict[str, ToolHookTargetState],
) -> None:
    """Rewrite or remove one tool-hook target file.

    Args:
        context: Shared remove-planning inputs.
        path: Project-root-relative tool-hook target path.
        action: Planned action for the target.
        current_states: Current tool-hook target states keyed by path.
        remaining_states: Remaining tool-hook target states keyed by path.
    """
    target = (context.root / path).resolve()
    current_state = current_states.get(path)
    if current_state is None:
        raise ValueError(f"Missing current tool-hook state for: {path}")
    if action == _DELETE_ACTION:
        if target.exists():
            target.unlink()
        _prune_empty_parent_dirs(target.parent, stop_at=context.root)
        return
    remaining_state = remaining_states.get(path)
    if remaining_state is None:
        _remove_tool_hook_blocks(target, current_state, stop_at=context.root)
        return
    _write_tool_hook_blocks(target, remaining_state)


def _apply_pack_local_skill_change(
    context: RemoveContext,
    path: str,
    action: str,
    remaining_states: Mapping[str, CodexSkillTargetState],
) -> None:
    """Delete or rewrite one pack-local skill file.

    Args:
        context: Shared remove-planning inputs.
        path: Project-root-relative pack-local skill path.
        action: Planned action for the skill file.
        remaining_states: Remaining pack-local skill states keyed by path.
    """
    target = (context.root / path).resolve()
    if action == _DELETE_ACTION:
        if target.exists():
            target.unlink()
        _prune_empty_parent_dirs(target.parent, stop_at=context.root)
        return
    state = remaining_states.get(path)
    if state is None:
        raise ValueError(f"Missing remaining pack-local skill state for: {path}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(state.rendered_content, encoding="utf-8")


def _tool_hook_states(
    context: RemoveContext,
    *,
    installed: bool,
    remaining_pack_ids: list[str] | None,
) -> dict[str, ToolHookTargetState]:
    """Return tool-hook target state keyed by path.

    Args:
        context: Shared remove-planning inputs.
        installed: When True, use currently installed packs from the manifest.
        remaining_pack_ids: Remaining pack ids used when installed is False.

    Returns:
        Tool-hook target states keyed by project-root-relative path.
    """
    selected_ids = (
        {record.id for record in context.manifest.installed_packs}
        if installed
        else set(remaining_pack_ids or [])
    )
    return {
        state.path: state
        for state in plan_tool_hook_targets(
            context.root,
            context.packs,
            context.profile,
            selected_ids,
        )
    }


def _write_tool_hook_blocks(target: Path, state: ToolHookTargetState) -> None:
    """Upsert all desired managed blocks for one tool-hook target.

    Args:
        target: Absolute file path to update.
        state: Desired tool-hook target state for the file.
    """
    current = target.read_text(encoding="utf-8") if target.exists() else ""
    updated = current
    for tool, hook_id, rendered in zip(
        state.tools,
        state.hook_ids,
        state.rendered_blocks,
        strict=True,
    ):
        start = _managed_block_start_for_target(tool, hook_id)
        end = _managed_block_end_for_target(tool, hook_id)
        block = f"{start}\n{rendered}\n{end}\n"
        updated = _upsert_block(updated, start, end, block)
    if updated == current:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(updated, encoding="utf-8")


def _remove_tool_hook_blocks(
    target: Path,
    state: ToolHookTargetState,
    *,
    stop_at: Path,
) -> None:
    """Remove managed hook blocks and delete the file when nothing remains.

    Args:
        target: Absolute file path to update.
        state: Current tool-hook target state whose blocks should be removed.
        stop_at: Directory boundary for empty-directory pruning.
    """
    current = target.read_text(encoding="utf-8") if target.exists() else ""
    updated = current
    for tool, hook_id in zip(state.tools, state.hook_ids, strict=True):
        updated = _remove_managed_block(
            updated,
            _managed_block_start_for_target(tool, hook_id),
            _managed_block_end_for_target(tool, hook_id),
        )
    if updated == current:
        return
    if updated.strip():
        target.write_text(updated, encoding="utf-8")
        return
    if target.exists():
        target.unlink()
    _prune_empty_parent_dirs(target.parent, stop_at=stop_at)


def _remove_managed_block(
    current: str,
    start_marker: str,
    end_marker: str,
) -> str:
    """Remove one managed block from current content when present.

    Args:
        current: Current file content.
        start_marker: Managed block start marker.
        end_marker: Managed block end marker.

    Returns:
        Updated file content with the block removed when present.
    """
    start_index = current.find(start_marker)
    if start_index == -1:
        return current
    end_index = current.find(end_marker, start_index)
    if end_index == -1:
        raise ValueError(f"Missing end marker for managed block: {start_marker}")
    after_end = end_index + len(end_marker)
    if after_end < len(current) and current[after_end] == "\n":
        after_end += 1
    updated = current[:start_index] + current[after_end:]
    return updated.strip("\n") + ("\n" if updated.strip() else "")


def _managed_block_start_for_target(tool: str, hook_id: str) -> str:
    """Return the stable start marker for one remove target block.

    Args:
        tool: External tool id for the hook.
        hook_id: Hook identifier within the tool.

    Returns:
        Stable start marker string.
    """
    return f"<!-- grove:tool-hook:{tool}:{hook_id}:start -->"


def _managed_block_end_for_target(tool: str, hook_id: str) -> str:
    """Return the stable end marker for one remove target block.

    Args:
        tool: External tool id for the hook.
        hook_id: Hook identifier within the tool.

    Returns:
        Stable end marker string.
    """
    return f"<!-- grove:tool-hook:{tool}:{hook_id}:end -->"


def _updated_manifest(
    manifest: ManifestState,
    remaining_pack_ids: list[str],
    remaining_plan: InstallPlan,
) -> ManifestState:
    """Return the manifest state after a successful remove.

    Args:
        manifest: Current manifest state before removal.
        remaining_pack_ids: Pack ids that remain installed.
        remaining_plan: Desired managed install plan for the remaining packs.

    Returns:
        Updated manifest with remaining packs and generated files only.
    """
    install_root = _install_root(manifest)
    remaining_generated = [
        GeneratedFileRecord(
            path=planned.dst.relative_to(install_root).as_posix(),
            pack_id=planned.pack_id,
        )
        for planned in remaining_plan.files
    ]
    return manifest.model_copy(
        update={
            "installed_packs": [
                record
                for record in manifest.installed_packs
                if record.id in remaining_pack_ids
            ],
            "generated_files": remaining_generated,
        }
    )


def _install_root(manifest: ManifestState) -> Path:
    """Return the resolved Grove install root for one manifest.

    Args:
        manifest: Loaded manifest whose init provenance defines install_root.

    Returns:
        Absolute Grove install root for the manifest.
    """
    install_rel = (
        manifest.init_provenance.install_root if manifest.init_provenance else ".grove"
    )
    return (Path(manifest.project.root).resolve() / install_rel).resolve()


def _project_relative_from_install_root(context: RemoveContext, path: str) -> str:
    """Return one install-root-relative path as project-root-relative text.

    Args:
        context: Shared remove-planning inputs with project root.
        path: Path relative to the Grove install root.

    Returns:
        Project-root-relative path string.
    """
    return (
        (_install_root(context.manifest) / path)
        .resolve()
        .relative_to(context.root)
        .as_posix()
    )


def _prune_empty_parent_dirs(path: Path, *, stop_at: Path) -> None:
    """Remove empty parent directories up to, but not including, stop_at.

    Args:
        path: Directory path to start pruning from.
        stop_at: Directory boundary that must not be removed.
    """
    current = path.resolve()
    boundary = stop_at.resolve()
    while current != boundary and current.exists():
        try:
            current.rmdir()
        except OSError:
            return
        current = current.parent
