"""Generic tool hook pipeline for pack-owned external integrations."""

from collections.abc import Callable
from pathlib import Path

from grove.core.models import (
    CodexSkillSpec,
    ManifestState,
    PackManifest,
    ProjectProfile,
    ToolHookSpec,
)
from grove.core.renderer import render, render_string

HookWriter = Callable[..., bool]
_MANAGED_BLOCK = "managed_block"


def apply_tool_hooks(
    root: Path,
    manifest: ManifestState,
    packs: list[PackManifest],
    profile: ProjectProfile,
    *,
    dry_run: bool = False,
) -> list[str]:
    """Render and apply pack-owned tool integrations contributed by installed packs.

    Args:
        root: Project root that owns the hook targets.
        manifest: Current manifest state used to determine selected packs.
        packs: Available pack manifests in dependency order.
        profile: Project analysis used as template variables.
        dry_run: If True, do not write files; return paths that would change.

    Returns:
        Relative project-root paths written or that would be written.

    Raises:
        ValueError: A tool integration contribution is invalid.
        KeyError: A hook write strategy is not supported.
    """
    selected = {record.id for record in manifest.installed_packs}
    hooks = collect_tool_hooks(packs, selected)
    codex_skills = collect_codex_skills(packs, selected)
    variables = _variables_from_profile(profile)
    packs_by_id = {pack.id: pack for pack in packs}
    changed: list[str] = []

    for hook in hooks:
        rendered = _render_tool_hook(hook, variables, packs_by_id)
        target = _resolve_target(root, hook.target)
        writer = _hook_writers().get(hook.hook_type)
        if writer is None:
            raise KeyError(f"Unsupported tool hook type: {hook.hook_type}")
        if writer(target, hook, rendered, dry_run=dry_run):
            changed.append(_relative_to_root(root, target))

    for skill in codex_skills:
        rendered = _render_codex_skill(skill, variables, packs_by_id)
        target = _codex_skills_root(root) / skill.path / "SKILL.md"
        if _write_codex_skill(target, rendered, dry_run=dry_run):
            changed.append(_relative_to_root(root, target))
    return changed


def collect_tool_hooks(
    packs: list[PackManifest],
    selected_pack_ids: set[str],
) -> list[ToolHookSpec]:
    """Collect tool hook contributions for the selected packs.

    Args:
        packs: Available pack manifests in dependency order.
        selected_pack_ids: Selected pack ids to include.

    Returns:
        Tool hook specs ordered deterministically by order then id.

    Raises:
        ValueError: Duplicate hook ids are present.
    """
    hooks: list[ToolHookSpec] = []
    seen_ids: set[str] = set()
    for pack in packs:
        if pack.id not in selected_pack_ids:
            continue
        for hook in _tool_hooks_from_pack(pack):
            if hook.id in seen_ids:
                raise ValueError(f"Duplicate tool hook id: {hook.id}")
            seen_ids.add(hook.id)
            hooks.append(hook)
    return sorted(hooks, key=lambda item: (item.order, item.id))


def collect_codex_skills(
    packs: list[PackManifest],
    selected_pack_ids: set[str],
) -> list[CodexSkillSpec]:
    """Collect Codex skill contributions for the selected packs.

    Args:
        packs: Available pack manifests in dependency order.
        selected_pack_ids: Selected pack ids to include.

    Returns:
        Codex skill specs ordered deterministically by order then id.

    Raises:
        ValueError: Duplicate skill ids are present.
    """
    skills: list[CodexSkillSpec] = []
    seen_ids: set[str] = set()
    for pack in packs:
        if pack.id not in selected_pack_ids:
            continue
        for skill in _codex_skills_from_pack(pack):
            if skill.id in seen_ids:
                raise ValueError(f"Duplicate Codex skill id: {skill.id}")
            seen_ids.add(skill.id)
            skills.append(skill)
    return sorted(skills, key=lambda item: (item.order, item.id))


def _tool_hooks_from_pack(pack: PackManifest) -> list[ToolHookSpec]:
    """Parse tool hook specs from one pack manifest.

    Args:
        pack: Pack manifest to inspect.

    Returns:
        Parsed tool hook specs for the pack.
    """
    raw = pack.contributes.get("tool_hooks")
    if not isinstance(raw, list):
        return []
    hooks: list[ToolHookSpec] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        hooks.append(
            ToolHookSpec(
                pack_id=pack.id,
                id=str(item["id"]),
                tool=str(item["tool"]),
                hook_type=str(item["hook_type"]),
                target=Path(str(item["target"])),
                source=Path(str(item["source"])) if "source" in item else None,
                content=str(item["content"]) if "content" in item else None,
                order=int(item.get("order", 0)),
            )
        )
    return hooks


def _codex_skills_from_pack(pack: PackManifest) -> list[CodexSkillSpec]:
    """Parse Codex skill specs from one pack manifest.

    Args:
        pack: Pack manifest to inspect.

    Returns:
        Parsed Codex skill specs for the pack.
    """
    raw = pack.contributes.get("codex_skills")
    if not isinstance(raw, list):
        return []
    skills: list[CodexSkillSpec] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        skills.append(
            CodexSkillSpec(
                pack_id=pack.id,
                id=str(item["id"]),
                path=Path(str(item["path"])),
                source=Path(str(item["source"])) if "source" in item else None,
                content=str(item["content"]) if "content" in item else None,
                order=int(item.get("order", 0)),
            )
        )
    return skills


def _render_tool_hook(
    hook: ToolHookSpec,
    variables: dict[str, object],
    packs_by_id: dict[str, PackManifest],
) -> str:
    """Render a tool hook body from either a template or inline content.

    Args:
        hook: Tool hook spec to render.
        variables: Template variables derived from the project profile.
        packs_by_id: Pack manifests keyed by pack id.

    Returns:
        Rendered hook body text.
    """
    has_source = hook.source is not None
    has_content = hook.content is not None
    if has_source == has_content:
        raise ValueError(
            f"Tool hook '{hook.id}' must define exactly one of 'source' or 'content'"
        )
    if hook.content is not None:
        return render_string(hook.content, variables).strip()
    pack = packs_by_id.get(hook.pack_id)
    if pack is None or pack.root_dir is None or hook.source is None:
        raise ValueError(f"Pack root is unavailable for tool hook '{hook.id}'")
    return render((pack.root_dir / hook.source).resolve(), variables).strip()


def _render_codex_skill(
    skill: CodexSkillSpec,
    variables: dict[str, object],
    packs_by_id: dict[str, PackManifest],
) -> str:
    """Render one Codex skill body from either a template or inline content.

    Args:
        skill: Codex skill contribution to render.
        variables: Template variables derived from the project profile.
        packs_by_id: Pack manifests keyed by pack id.

    Returns:
        Rendered skill body text.
    """
    has_source = skill.source is not None
    has_content = skill.content is not None
    if has_source == has_content:
        raise ValueError(
            f"Codex skill '{skill.id}' must define exactly one of 'source' or 'content'"
        )
    if skill.content is not None:
        return render_string(skill.content, variables).strip()
    pack = packs_by_id.get(skill.pack_id)
    if pack is None or pack.root_dir is None or skill.source is None:
        raise ValueError(f"Pack root is unavailable for Codex skill '{skill.id}'")
    return render((pack.root_dir / skill.source).resolve(), variables).strip()


def _resolve_target(root: Path, target: Path) -> Path:
    """Resolve a tool hook target path against the project root.

    Args:
        root: Project root directory.
        target: Hook target path from the contribution spec.

    Returns:
        Absolute path to the hook target.
    """
    if target.is_absolute():
        return target.resolve()
    return (root.resolve() / target).resolve()


def _relative_to_root(root: Path, target: Path) -> str:
    """Return a target path relative to the project root when possible.

    Args:
        root: Project root directory.
        target: Absolute or project-relative target path.

    Returns:
        Path relative to the project root when possible, else the absolute path.
    """
    try:
        return target.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(target.resolve())


def _codex_skills_root(root: Path) -> Path:
    """Return the repo-local Codex skills root directory.

    Args:
        root: Project root used as the base for repo-local skill materialization.

    Returns:
        Absolute path to `.agents/skills` under the project root.
    """
    return (root.resolve() / ".agents" / "skills").resolve()


def _hook_writers() -> dict[str, HookWriter]:
    """Return hook writers keyed by hook_type.

    Returns:
        Mapping of supported hook types to their writer functions.
    """
    return {_MANAGED_BLOCK: _write_managed_block}


def _write_managed_block(
    target: Path,
    hook: ToolHookSpec,
    rendered: str,
    *,
    dry_run: bool = False,
) -> bool:
    """Create or update a managed block in a target file.

    Args:
        target: Target file to update.
        hook: Hook metadata used to build stable markers.
        rendered: Rendered body to place between markers.
        dry_run: If True, do not write the file.

    Returns:
        True when the file would change or was changed.
    """
    start = _managed_block_start(hook)
    end = _managed_block_end(hook)
    managed_block = f"{start}\n{rendered}\n{end}\n"
    current = target.read_text(encoding="utf-8") if target.exists() else ""
    updated = _upsert_block(current, start, end, managed_block)
    if updated == current:
        return False
    if dry_run:
        return True
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(updated, encoding="utf-8")
    return True


def _write_codex_skill(
    target: Path,
    rendered: str,
    *,
    dry_run: bool = False,
) -> bool:
    """Create or update one materialized Codex skill file.

    Args:
        target: Destination `SKILL.md` path under repo-local `.agents/skills`.
        rendered: Rendered skill body to write.
        dry_run: If True, do not write the file.

    Returns:
        True when the skill file would change or was changed.
    """
    current = target.read_text(encoding="utf-8") if target.exists() else None
    updated = f"{rendered}\n"
    if current == updated:
        return False
    if dry_run:
        return True
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(updated, encoding="utf-8")
    return True


def _managed_block_start(hook: ToolHookSpec) -> str:
    """Return the stable start marker for one managed tool hook block.

    Args:
        hook: Hook metadata used to build the marker.

    Returns:
        Stable start marker string for the hook block.
    """
    return f"<!-- grove:tool-hook:{hook.tool}:{hook.id}:start -->"


def _managed_block_end(hook: ToolHookSpec) -> str:
    """Return the stable end marker for one managed tool hook block.

    Args:
        hook: Hook metadata used to build the marker.

    Returns:
        Stable end marker string for the hook block.
    """
    return f"<!-- grove:tool-hook:{hook.tool}:{hook.id}:end -->"


def _upsert_block(
    current: str,
    start_marker: str,
    end_marker: str,
    block: str,
) -> str:
    """Replace an existing managed block or append a new one.

    Args:
        current: Current file content.
        start_marker: Managed block start marker.
        end_marker: Managed block end marker.
        block: Fully rendered managed block including markers.

    Returns:
        Updated file content with the managed block replaced or appended.
    """
    start_index = current.find(start_marker)
    if start_index != -1:
        end_index = current.find(end_marker, start_index)
        if end_index == -1:
            raise ValueError(f"Missing end marker for managed block: {start_marker}")
        after_end = end_index + len(end_marker)
        if after_end < len(current) and current[after_end] == "\n":
            after_end += 1
        return current[:start_index] + block + current[after_end:]

    if not current:
        return block
    separator = "\n\n" if not current.endswith("\n") else "\n"
    return f"{current}{separator}{block}"


def _variables_from_profile(profile: ProjectProfile) -> dict[str, object]:
    """Build template variables for tool hook rendering.

    Args:
        profile: Project analysis used to populate template variables.

    Returns:
        Mapping of template variables derived from the profile.
    """
    out: dict[str, object] = {
        "project_name": profile.project_name,
        "language": profile.language,
        "package_manager": profile.package_manager,
        "test_framework": profile.test_framework,
        "tools": profile.tools,
    }
    if profile.raw:
        out["raw"] = profile.raw
    return out
