"""Planning helpers for `grove remove` before any filesystem mutation."""

from dataclasses import dataclass
from pathlib import Path

from grove.core.composer import compose
from grove.core.file_ops import render_planned_file
from grove.core.models import (
    ManifestState,
    PackManifest,
    PlannedFile,
    ProjectProfile,
    RemovePathPlan,
    RemovePlan,
    ToolHookTargetState,
)
from grove.core.tool_hooks import plan_codex_skill_targets, plan_tool_hook_targets

_BASE_PACK_ID = "base"
_DELETE_ACTION = "delete"
_PRESERVE_ACTION = "preserve"
_REWRITE_ACTION = "rewrite"
_PACK_LOCAL_SKILL_SURFACE = "pack_local_skill"
_MANAGED_FILE_SURFACE = "managed_file"
_TOOL_HOOK_SURFACE = "tool_hook"
_MANAGED_BLOCK_HOOK = "managed_block"


@dataclass(frozen=True)
class RemoveContext:
    """Shared immutable inputs for one remove-planning run."""

    root: Path
    manifest: ManifestState
    pack_roots: dict[str, Path]
    profile: ProjectProfile
    packs: list[PackManifest]


@dataclass(frozen=True)
class ManagedFileCandidate:
    """Current and remaining state for one managed file classification."""

    relative_path: str
    fallback_pack_id: str
    current_file: PlannedFile | None
    remaining_file: PlannedFile | None


def build_remove_context(
    root: Path,
    manifest: ManifestState,
    pack_roots: dict[str, Path],
    profile: ProjectProfile,
    packs: list[PackManifest],
) -> RemoveContext:
    """Package common remove-planning inputs into one context object.

    Args:
        root: Project root for project-relative planning.
        manifest: Loaded Grove manifest state.
        pack_roots: Pack root lookup for template rendering.
        profile: Current analyzed project profile.
        packs: Available packs in dependency order.

    Returns:
        Frozen context reused by planning and apply helpers.
    """
    return RemoveContext(
        root=root.resolve(),
        manifest=manifest,
        pack_roots=pack_roots,
        profile=profile,
        packs=packs,
    )


def plan_remove(
    target_pack_id: str,
    context: RemoveContext,
) -> RemovePlan:
    """Build a non-mutating remove plan for one installed pack.

    Args:
        target_pack_id: Installed pack requested for removal.
        context: Shared remove-planning inputs.

    Returns:
        RemovePlan describing delete/rewrite/preserve actions.

    Raises:
        ValueError: Removal is not allowed or the target pack is unavailable.
    """
    installed_ids = [record.id for record in context.manifest.installed_packs]
    _validate_remove_target(target_pack_id, installed_ids, context.packs)
    remaining_pack_ids = [
        pack_id for pack_id in installed_ids if pack_id != target_pack_id
    ]
    install_root = _install_root(context.manifest)
    current_plan = compose(context.profile, installed_ids, install_root, context.packs)
    remaining_plan = compose(
        context.profile,
        remaining_pack_ids,
        install_root,
        context.packs,
    )
    changes = _plan_managed_file_changes(
        context,
        target_pack_id,
        current_plan.files,
        remaining_plan.files,
    )
    changes.extend(_plan_tool_hook_changes(context, installed_ids, remaining_pack_ids))
    changes.extend(
        _plan_codex_skill_changes(
            context,
            installed_ids,
            remaining_pack_ids,
            target_pack_id,
        )
    )
    return RemovePlan(
        target_pack_id=target_pack_id,
        remaining_pack_ids=remaining_pack_ids,
        changes=sorted(
            changes,
            key=lambda item: (item.action, item.path, item.surface),
        ),
    )


def _validate_remove_target(
    target_pack_id: str,
    installed_ids: list[str],
    packs: list[PackManifest],
) -> None:
    """Ensure the requested pack can be removed safely.

    Args:
        target_pack_id: Pack requested for removal.
        installed_ids: Currently installed pack ids.
        packs: Available packs in dependency order.
    """
    if target_pack_id == _BASE_PACK_ID:
        raise ValueError("Pack 'base' is required and cannot be removed.")
    if target_pack_id not in installed_ids:
        raise ValueError(f"Pack '{target_pack_id}' is not installed.")
    packs_by_id = {pack.id: pack for pack in packs}
    if target_pack_id not in packs_by_id:
        raise ValueError(f"Pack '{target_pack_id}' is not available in the registry.")
    dependents = sorted(
        pack_id
        for pack_id in installed_ids
        if (
            pack_id != target_pack_id
            and target_pack_id in packs_by_id[pack_id].depends_on
        )
    )
    if dependents:
        raise ValueError(
            f"Pack '{target_pack_id}' cannot be removed; installed dependents: "
            + ", ".join(dependents)
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


def _plan_managed_file_changes(
    context: RemoveContext,
    target_pack_id: str,
    current_files: list[PlannedFile],
    remaining_files: list[PlannedFile],
) -> list[RemovePathPlan]:
    """Classify current managed Grove outputs for remove planning.

    Args:
        context: Shared remove-planning inputs.
        target_pack_id: Pack requested for removal.
        current_files: Desired managed files for the current installed set.
        remaining_files: Desired managed files for the remaining installed set.

    Returns:
        Ordered managed-file path classifications.
    """
    install_root = _install_root(context.manifest)
    current_by_rel = {
        planned.dst.relative_to(install_root).as_posix(): planned
        for planned in current_files
    }
    remaining_by_rel = {
        planned.dst.relative_to(install_root).as_posix(): planned
        for planned in remaining_files
    }
    return [
        _classify_managed_file_change(
            context,
            target_pack_id,
            install_root,
            ManagedFileCandidate(
                relative_path=record.path,
                fallback_pack_id=record.pack_id,
                current_file=current_by_rel.get(record.path),
                remaining_file=remaining_by_rel.get(record.path),
            ),
        )
        for record in context.manifest.generated_files
    ]


def _classify_managed_file_change(
    context: RemoveContext,
    target_pack_id: str,
    install_root: Path,
    candidate: ManagedFileCandidate,
) -> RemovePathPlan:
    """Return one managed-file remove classification.

    Args:
        context: Shared remove-planning inputs.
        target_pack_id: Pack requested for removal.
        install_root: Absolute Grove install root for relative path resolution.
        candidate: Current and remaining state for one managed file path.

    Returns:
        Planned path action for the managed file candidate.
    """
    project_path = _project_relative_path(
        context.root,
        install_root,
        candidate.relative_path,
    )
    pack_ids = _current_file_pack_ids(
        candidate.current_file,
        candidate.fallback_pack_id,
    )
    target_involved = _planned_file_involves_pack(
        candidate.current_file,
        target_pack_id,
    ) or (candidate.fallback_pack_id == target_pack_id)
    if candidate.remaining_file is None:
        return _missing_remaining_file_change(project_path, pack_ids, target_involved)
    if not target_involved:
        return RemovePathPlan(
            path=project_path,
            action=_PRESERVE_ACTION,
            surface=_MANAGED_FILE_SURFACE,
            reason="Managed file is unaffected by the removed pack.",
            pack_ids=pack_ids,
        )
    if _managed_file_unchanged(
        context,
        candidate.current_file,
        candidate.remaining_file,
    ):
        return RemovePathPlan(
            path=project_path,
            action=_PRESERVE_ACTION,
            surface=_MANAGED_FILE_SURFACE,
            reason="Remaining managed output is unchanged after removing the pack.",
            pack_ids=pack_ids,
        )
    return RemovePathPlan(
        path=project_path,
        action=_REWRITE_ACTION,
        surface=_MANAGED_FILE_SURFACE,
        reason="Remaining packs still contribute this managed file.",
        pack_ids=pack_ids,
        anchors=_affected_anchors(candidate.current_file, target_pack_id),
    )


def _missing_remaining_file_change(
    project_path: str,
    pack_ids: list[str],
    target_involved: bool,
) -> RemovePathPlan:
    """Return the remove classification when no remaining file exists.

    Args:
        project_path: Project-root-relative path being classified.
        pack_ids: Packs that currently contribute to the path.
        target_involved: Whether the removed pack contributed to the path.

    Returns:
        Delete or preserve classification for the missing remaining file.
    """
    action = _DELETE_ACTION if target_involved else _PRESERVE_ACTION
    reason = (
        "Target pack owns the managed file and no remaining pack contributes it."
        if target_involved
        else "Managed file is unrelated to the removed pack."
    )
    return RemovePathPlan(
        path=project_path,
        action=action,
        surface=_MANAGED_FILE_SURFACE,
        reason=reason,
        pack_ids=pack_ids,
    )


def _managed_file_unchanged(
    context: RemoveContext,
    current_file: PlannedFile | None,
    remaining_file: PlannedFile,
) -> bool:
    """Return whether the managed file content stays identical after removal.

    Args:
        context: Shared remove-planning inputs with pack roots.
        current_file: Current desired file for the installed pack set, if any.
        remaining_file: Desired file for the remaining pack set.

    Returns:
        True when the rendered content is unchanged after removal.
    """
    current_content = (
        render_planned_file(current_file, context.pack_roots)
        if current_file is not None
        else ""
    )
    remaining_content = render_planned_file(remaining_file, context.pack_roots)
    return current_content == remaining_content


def _plan_tool_hook_changes(
    context: RemoveContext,
    installed_ids: list[str],
    remaining_pack_ids: list[str],
) -> list[RemovePathPlan]:
    """Classify tool-hook targets for remove planning.

    Args:
        context: Shared remove-planning inputs.
        installed_ids: Current installed pack ids.
        remaining_pack_ids: Pack ids that remain after removal.

    Returns:
        Planned path actions for tool-native hook targets.
    """
    current_states = {
        state.path: state
        for state in plan_tool_hook_targets(
            context.root,
            context.packs,
            context.profile,
            set(installed_ids),
        )
    }
    remaining_states = {
        state.path: state
        for state in plan_tool_hook_targets(
            context.root,
            context.packs,
            context.profile,
            set(remaining_pack_ids),
        )
    }
    changes: list[RemovePathPlan] = []

    for path, current_state in current_states.items():
        remaining_state = remaining_states.get(path)
        if remaining_state is None:
            action = (
                _REWRITE_ACTION
                if current_state.hook_type == _MANAGED_BLOCK_HOOK
                else _DELETE_ACTION
            )
            reason = (
                "Managed hook blocks must be removed while preserving "
                "non-Grove content."
                if current_state.hook_type == _MANAGED_BLOCK_HOOK
                else "No remaining pack contributes this tool-native output."
            )
            changes.append(
                RemovePathPlan(
                    path=path,
                    action=action,
                    surface=_TOOL_HOOK_SURFACE,
                    reason=reason,
                    pack_ids=list(current_state.pack_ids),
                )
            )
            continue
        if _tool_hook_state_changed(current_state, remaining_state):
            changes.append(
                RemovePathPlan(
                    path=path,
                    action=_REWRITE_ACTION,
                    surface=_TOOL_HOOK_SURFACE,
                    reason=(
                        "Remaining hook targets must be recomputed without "
                        "the removed pack."
                    ),
                    pack_ids=list(current_state.pack_ids),
                )
            )
            continue
        changes.append(
            RemovePathPlan(
                path=path,
                action=_PRESERVE_ACTION,
                surface=_TOOL_HOOK_SURFACE,
                reason="Tool-native output is unchanged after removing the pack.",
                pack_ids=list(current_state.pack_ids),
            )
        )
    return changes


def _plan_codex_skill_changes(
    context: RemoveContext,
    installed_ids: list[str],
    remaining_pack_ids: list[str],
    target_pack_id: str,
) -> list[RemovePathPlan]:
    """Classify repo-local Codex skill outputs for remove planning.

    Args:
        context: Shared remove-planning inputs.
        installed_ids: Current installed pack ids.
        remaining_pack_ids: Pack ids that remain after removal.
        target_pack_id: Pack requested for removal.

    Returns:
        Planned path actions for pack-local skill outputs.
    """
    current_states = {
        state.path: state
        for state in plan_codex_skill_targets(
            context.root,
            context.packs,
            context.profile,
            set(installed_ids),
        )
    }
    remaining_states = {
        state.path: state
        for state in plan_codex_skill_targets(
            context.root,
            context.packs,
            context.profile,
            set(remaining_pack_ids),
        )
    }
    changes: list[RemovePathPlan] = []

    for path, current_state in current_states.items():
        remaining_state = remaining_states.get(path)
        if remaining_state is None:
            action = (
                _DELETE_ACTION
                if current_state.pack_id == target_pack_id
                else _PRESERVE_ACTION
            )
            reason = (
                "Repo-local skill is exclusively owned by the removed pack."
                if current_state.pack_id == target_pack_id
                else "Repo-local skill is unrelated to the removed pack."
            )
            changes.append(
                RemovePathPlan(
                    path=path,
                    action=action,
                    surface=_PACK_LOCAL_SKILL_SURFACE,
                    reason=reason,
                    pack_ids=[current_state.pack_id],
                )
            )
            continue
        if (
            current_state.pack_id != remaining_state.pack_id
            or current_state.skill_id != remaining_state.skill_id
            or current_state.rendered_content != remaining_state.rendered_content
        ):
            changes.append(
                RemovePathPlan(
                    path=path,
                    action=_REWRITE_ACTION,
                    surface=_PACK_LOCAL_SKILL_SURFACE,
                    reason="Repo-local skill remains selected but must be rewritten.",
                    pack_ids=[current_state.pack_id],
                )
            )
            continue
        changes.append(
            RemovePathPlan(
                path=path,
                action=_PRESERVE_ACTION,
                surface=_PACK_LOCAL_SKILL_SURFACE,
                reason="Repo-local skill is unchanged after removing the pack.",
                pack_ids=[current_state.pack_id],
            )
        )
    return changes


def _planned_file_involves_pack(
    planned: PlannedFile | None,
    pack_id: str,
) -> bool:
    """Return whether a managed file is owned or composed by one pack.

    Args:
        planned: Planned managed file, if one exists for the path.
        pack_id: Pack id to test for ownership or anchor contributions.

    Returns:
        True when the pack contributes the file directly or through anchors.
    """
    if planned is None:
        return False
    if planned.pack_id == pack_id:
        return True
    return any(
        entry.pack_id == pack_id
        for provenance in planned.anchor_provenance.values()
        for entry in provenance
    )


def _current_file_pack_ids(
    planned: PlannedFile | None,
    fallback_pack_id: str,
) -> list[str]:
    """Return deterministic pack ids contributing to a managed file.

    Args:
        planned: Planned managed file, if one exists for the path.
        fallback_pack_id: Manifest pack id used when no planned file is present.

    Returns:
        Sorted pack ids contributing to the managed file.
    """
    if planned is None:
        return [fallback_pack_id] if fallback_pack_id else []
    pack_ids = {planned.pack_id}
    pack_ids.update(
        entry.pack_id
        for provenance in planned.anchor_provenance.values()
        for entry in provenance
    )
    return sorted(pack_id for pack_id in pack_ids if pack_id)


def _affected_anchors(planned: PlannedFile | None, target_pack_id: str) -> list[str]:
    """Return anchors that include contributions from the removed pack.

    Args:
        planned: Planned managed file, if one exists for the path.
        target_pack_id: Pack requested for removal.

    Returns:
        Sorted anchor names affected by the removed pack.
    """
    if planned is None:
        return []
    return sorted(
        anchor
        for anchor, provenance in planned.anchor_provenance.items()
        if any(entry.pack_id == target_pack_id for entry in provenance)
    )


def _tool_hook_state_changed(
    current: ToolHookTargetState,
    remaining: ToolHookTargetState,
) -> bool:
    """Return whether a tool-hook target requires rewrite after removal.

    Args:
        current: Current desired tool-hook state.
        remaining: Desired tool-hook state after removal.

    Returns:
        True when hook ordering, type, or content changes.
    """
    return (
        current.hook_type != remaining.hook_type
        or current.hook_ids != remaining.hook_ids
        or current.rendered_blocks != remaining.rendered_blocks
    )


def _project_relative_path(project_root: Path, install_root: Path, path: str) -> str:
    """Return one install-root-relative path as project-root-relative text.

    Args:
        project_root: Absolute project root for reporting.
        install_root: Absolute Grove install root.
        path: Path relative to the install root.

    Returns:
        Project-root-relative path string.
    """
    absolute = (install_root / path).resolve()
    return absolute.relative_to(project_root.resolve()).as_posix()
