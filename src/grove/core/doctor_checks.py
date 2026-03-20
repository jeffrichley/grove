"""Generic read-only checks used by `grove doctor`."""

import re
from pathlib import Path

from grove.core.composer import compose
from grove.core.file_ops import render_planned_file
from grove.core.manifest import load_manifest
from grove.core.markers import find_anchor_ranges
from grove.core.models import (
    CodexSkillTargetState,
    DoctorCheckSpec,
    DoctorIssue,
    ManifestState,
    PackManifest,
    PlannedFile,
    ProjectProfile,
    ToolHookTargetState,
)
from grove.core.remove_impl import RemoveContext, build_remove_context
from grove.core.sync import _sync_target_content
from grove.core.tool_hooks import plan_codex_skill_targets, plan_tool_hook_targets

_ERROR = "error"
_WARNING = "warning"
_TOOL_HOOK_START_RE = re.compile(r"<!--\s*grove:tool-hook:([^:]+):([^:]+):start\s*-->")


def build_doctor_context(
    root: Path,
    manifest: ManifestState,
    pack_roots: dict[str, Path],
    profile: ProjectProfile,
    packs: list[PackManifest],
) -> RemoveContext:
    """Reuse the remove ownership context for doctor checks.

    Args:
        root: Project root for project-relative reporting.
        manifest: Loaded manifest state.
        pack_roots: Pack root lookup for template rendering.
        profile: Current analyzed project profile.
        packs: Available packs in dependency order.

    Returns:
        Shared immutable context for doctor checks.
    """
    return build_remove_context(root, manifest, pack_roots, profile, packs)


def check_manifest_load(root: Path) -> list[DoctorIssue]:
    """Return manifest existence or parse issues that block doctor execution.

    Args:
        root: Project root whose Grove manifest should be loaded.

    Returns:
        Blocking manifest issues, or an empty list when the manifest is loadable.
    """
    manifest_path = root / ".grove" / "manifest.toml"
    if not manifest_path.exists():
        return [
            DoctorIssue(
                code="manifest-missing",
                severity=_ERROR,
                message="No Grove manifest found; run 'grove init' first.",
                path=".grove/manifest.toml",
            )
        ]
    try:
        load_manifest(manifest_path)
    except ValueError as exc:
        return [
            DoctorIssue(
                code="manifest-invalid",
                severity=_ERROR,
                message=str(exc),
                path=".grove/manifest.toml",
            )
        ]
    return []


def check_pack_coherence(
    manifest: ManifestState,
    packs: list[PackManifest],
) -> list[DoctorIssue]:
    """Return pack availability and dependency issues from the manifest.

    Args:
        manifest: Loaded manifest state.
        packs: Available packs in dependency order.

    Returns:
        Pack availability and dependency issues.
    """
    issues: list[DoctorIssue] = []
    packs_by_id = {pack.id: pack for pack in packs}
    installed_ids = {record.id for record in manifest.installed_packs}
    for record in manifest.installed_packs:
        pack = packs_by_id.get(record.id)
        if pack is None:
            issues.append(
                DoctorIssue(
                    code="pack-missing",
                    severity=_ERROR,
                    message=(
                        f"Installed pack '{record.id}' is not available in the "
                        "registry."
                    ),
                    pack_id=record.id,
                )
            )
            continue
        missing_deps = sorted(
            dep_id for dep_id in pack.depends_on if dep_id not in installed_ids
        )
        issues.extend(
            [
                DoctorIssue(
                    code="pack-dependency-missing",
                    severity=_ERROR,
                    message=(
                        f"Pack '{record.id}' is missing required dependency '{dep_id}'."
                    ),
                    pack_id=record.id,
                )
                for dep_id in missing_deps
            ]
        )
    return issues


def check_managed_outputs(context: RemoveContext) -> list[DoctorIssue]:
    """Return drift, missing-file, orphan, and anchor-integrity issues.

    Args:
        context: Shared doctor context with manifest and pack roots.

    Returns:
        Issues for Grove-managed files under the install root.
    """
    issues: list[DoctorIssue] = []
    install_root = _install_root(context.manifest)
    desired_files = _desired_managed_files(context)
    tracked_paths = {record.path for record in context.manifest.generated_files}

    for record in context.manifest.generated_files:
        project_path = _project_relative_path(context.root, install_root, record.path)
        planned = desired_files.get(record.path)
        target = install_root / record.path
        if planned is None:
            issues.append(
                DoctorIssue(
                    code="managed-file-untracked-by-packs",
                    severity=_WARNING,
                    message=(
                        "Manifest tracks a managed file that is no longer produced by "
                        "the installed pack set."
                    ),
                    path=project_path,
                    pack_id=record.pack_id,
                )
            )
            continue
        if not target.exists():
            issues.append(
                DoctorIssue(
                    code="managed-file-missing",
                    severity=_ERROR,
                    message="Managed file is missing from disk.",
                    path=project_path,
                    pack_id=record.pack_id,
                )
            )
            continue
        issues.extend(
            _managed_file_state_issues(
                context,
                planned,
                target,
                project_path,
            )
        )

    issues.extend(_orphan_install_root_issues(install_root, tracked_paths))
    return issues


def check_tool_outputs(context: RemoveContext) -> list[DoctorIssue]:
    """Return issues for tool-hook targets and pack-local skill files.

    Args:
        context: Shared doctor context with current selected pack state.

    Returns:
        Tool integration issues for managed blocks and pack-local skills.
    """
    issues: list[DoctorIssue] = []
    selected_ids = {record.id for record in context.manifest.installed_packs}
    for hook_state in plan_tool_hook_targets(
        context.root,
        context.packs,
        context.profile,
        selected_ids,
    ):
        issues.extend(_tool_hook_target_issues(context.root, hook_state))
    for skill_state in plan_codex_skill_targets(
        context.root,
        context.packs,
        context.profile,
        selected_ids,
    ):
        issues.extend(_pack_local_skill_issues(context.root, skill_state))
    issues.extend(_unexpected_tool_hook_issues(context, selected_ids))
    issues.extend(_orphan_pack_local_skill_issues(context.root, selected_ids, context))
    return issues


def collect_doctor_checks(
    packs: list[PackManifest],
    selected_pack_ids: set[str],
) -> list[DoctorCheckSpec]:
    """Collect pack-owned doctor check contributions for selected packs.

    Args:
        packs: Available pack manifests in dependency order.
        selected_pack_ids: Selected pack ids to include.

    Returns:
        Doctor check specs ordered deterministically by order then id.

    Raises:
        ValueError: Duplicate doctor check ids are present.
    """
    checks = [
        check
        for pack in packs
        if pack.id in selected_pack_ids
        for check in _doctor_checks_from_pack(pack)
    ]
    _validate_doctor_check_ids(checks)
    return sorted(checks, key=lambda item: (item.order, item.id))


def collect_doctor_checks_with_issues(
    packs: list[PackManifest],
    selected_pack_ids: set[str],
) -> tuple[list[DoctorCheckSpec], list[DoctorIssue]]:
    """Collect pack-owned doctor checks and convert malformed specs to issues.

    Args:
        packs: Available pack manifests in dependency order.
        selected_pack_ids: Selected pack ids to include.

    Returns:
        Tuple of valid doctor check specs and any invalid-spec issues.
    """
    checks: list[DoctorCheckSpec] = []
    issues: list[DoctorIssue] = []
    seen_ids: set[str] = set()
    for pack in packs:
        if pack.id not in selected_pack_ids:
            continue
        raw = pack.contributes.get("doctor_checks")
        if not isinstance(raw, list):
            continue
        for item in raw:
            if not isinstance(item, dict):
                issues.append(
                    DoctorIssue(
                        code="doctor-check-invalid",
                        severity=_ERROR,
                        message=(
                            f"Pack '{pack.id}' has a doctor check entry that is not an "
                            "object."
                        ),
                        pack_id=pack.id,
                    )
                )
                continue
            try:
                spec = _doctor_check_from_item(pack.id, item)
            except (KeyError, TypeError, ValueError) as exc:
                issues.append(
                    DoctorIssue(
                        code="doctor-check-invalid",
                        severity=_ERROR,
                        message=str(exc),
                        pack_id=pack.id,
                        check_id=str(item.get("id")) if "id" in item else None,
                    )
                )
                continue
            if spec.id in seen_ids:
                issues.append(
                    DoctorIssue(
                        code="doctor-check-duplicate-id",
                        severity=_ERROR,
                        message=f"Duplicate doctor check id: {spec.id}",
                        pack_id=pack.id,
                        check_id=spec.id,
                    )
                )
                continue
            seen_ids.add(spec.id)
            checks.append(spec)
    return sorted(checks, key=lambda item: (item.order, item.id)), issues


def _doctor_checks_from_pack(pack: PackManifest) -> list[DoctorCheckSpec]:
    """Return typed doctor checks contributed by one pack.

    Args:
        pack: Pack manifest to inspect.

    Returns:
        Typed doctor check specs for the pack.
    """
    raw = pack.contributes.get("doctor_checks")
    if not isinstance(raw, list):
        return []
    return [
        _doctor_check_from_item(pack.id, item) for item in raw if isinstance(item, dict)
    ]


def _doctor_check_from_item(
    pack_id: str,
    item: dict[str, object],
) -> DoctorCheckSpec:
    """Return one typed doctor check spec from raw pack data.

    Args:
        pack_id: Owning pack identifier.
        item: Raw doctor check contribution item.

    Returns:
        Typed doctor check spec.
    """
    if "id" not in item:
        raise ValueError(
            f"Pack '{pack_id}' doctor check is missing required field 'id'."
        )
    if "check_type" not in item:
        raise ValueError(
            f"Pack '{pack_id}' doctor check '{item['id']}' is missing required "
            "field 'check_type'."
        )
    required_front_matter = item.get("required_front_matter", [])
    if not isinstance(required_front_matter, list):
        required_front_matter = []
    order = item.get("order", 0)
    return DoctorCheckSpec(
        pack_id=pack_id,
        id=str(item["id"]),
        check_type=str(item["check_type"]),
        description=str(item.get("description", "")),
        target=Path(str(item["target"])) if "target" in item else None,
        tool=str(item["tool"]) if "tool" in item else None,
        skill_path=Path(str(item["skill_path"])) if "skill_path" in item else None,
        required_front_matter=[str(value) for value in required_front_matter],
        order=int(order) if isinstance(order, int | str) else 0,
    )


def _validate_doctor_check_ids(checks: list[DoctorCheckSpec]) -> None:
    """Ensure collected doctor checks have unique ids.

    Args:
        checks: Collected doctor check specs.

    Raises:
        ValueError: Duplicate doctor check ids are present.
    """
    seen_ids: set[str] = set()
    for check in checks:
        if check.id in seen_ids:
            raise ValueError(f"Duplicate doctor check id: {check.id}")
        seen_ids.add(check.id)


def check_pack_doctor_specs(context: RemoveContext) -> list[DoctorIssue]:
    """Run pack-owned doctor checks for the selected pack set.

    Args:
        context: Shared doctor context with selected packs and project root.

    Returns:
        Issues reported by pack-owned doctor checks.
    """
    selected_ids = {record.id for record in context.manifest.installed_packs}
    checks, issues = collect_doctor_checks_with_issues(context.packs, selected_ids)
    for spec in checks:
        try:
            issues.extend(_run_doctor_check(context.root, spec))
        except ValueError as exc:
            issues.append(
                DoctorIssue(
                    code="doctor-check-unsupported",
                    severity=_ERROR,
                    message=str(exc),
                    pack_id=spec.pack_id,
                    check_id=spec.id,
                )
            )
    return issues


def _desired_managed_files(context: RemoveContext) -> dict[str, PlannedFile]:
    """Return desired managed files keyed by install-root-relative path.

    Args:
        context: Shared doctor context.

    Returns:
        Desired managed files for the installed pack set.
    """
    install_root = _install_root(context.manifest)
    selected_ids = [record.id for record in context.manifest.installed_packs]
    plan = compose(context.profile, selected_ids, install_root, context.packs)
    return {
        planned.dst.relative_to(install_root).as_posix(): planned
        for planned in plan.files
    }


def _managed_file_state_issues(
    context: RemoveContext,
    planned: PlannedFile,
    target: Path,
    project_path: str,
) -> list[DoctorIssue]:
    """Return anchor and drift issues for one managed file on disk.

    Args:
        context: Shared doctor context with pack roots.
        planned: Desired managed file state.
        target: Absolute target path on disk.
        project_path: Project-root-relative path for reporting.

    Returns:
        Issues for one managed file.
    """
    current = target.read_text(encoding="utf-8")
    desired = render_planned_file(planned, context.pack_roots)
    issues: list[DoctorIssue] = []
    try:
        find_anchor_ranges(current)
    except ValueError as exc:
        issues.append(
            DoctorIssue(
                code="managed-file-anchor-invalid",
                severity=_ERROR,
                message=str(exc),
                path=project_path,
                pack_id=planned.pack_id,
            )
        )
        return issues
    try:
        next_content = _sync_target_content(current, desired)
    except ValueError as exc:
        issues.append(
            DoctorIssue(
                code="managed-file-anchor-unsafe",
                severity=_ERROR,
                message=str(exc),
                path=project_path,
                pack_id=planned.pack_id,
            )
        )
        return issues
    if current != next_content:
        issues.append(
            DoctorIssue(
                code="managed-file-drift",
                severity=_WARNING,
                message="Managed file has drifted from the current desired state.",
                path=project_path,
                pack_id=planned.pack_id,
            )
        )
    return issues


def _orphan_install_root_issues(
    install_root: Path,
    tracked_paths: set[str],
) -> list[DoctorIssue]:
    """Return issues for unexpected files under the Grove install root.

    Args:
        install_root: Absolute Grove install root.
        tracked_paths: Manifest-tracked paths relative to the install root.

    Returns:
        Warning issues for untracked files under `.grove/`.
    """
    if not install_root.exists():
        return []
    expected = set(tracked_paths) | {"manifest.toml"}
    issues: list[DoctorIssue] = []
    for path in sorted(install_root.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(install_root).as_posix()
        if rel in expected:
            continue
        issues.append(
            DoctorIssue(
                code="managed-file-orphan",
                severity=_WARNING,
                message="File exists under .grove but is not tracked in the manifest.",
                path=f".grove/{rel}",
            )
        )
    return issues


def _tool_hook_target_issues(
    root: Path,
    state: ToolHookTargetState,
) -> list[DoctorIssue]:
    """Return issues for one tool-hook target file.

    Args:
        root: Project root for resolving the tool target.
        state: Desired target state for the installed pack set.

    Returns:
        Issues for missing or drifted managed blocks.
    """
    target = root / state.path
    if not target.exists():
        return [
            DoctorIssue(
                code="tool-hook-target-missing",
                severity=_ERROR,
                message="Tool integration target file is missing from disk.",
                path=state.path,
                pack_id=state.pack_ids[0] if state.pack_ids else None,
            )
        ]
    current = target.read_text(encoding="utf-8")
    issues: list[DoctorIssue] = []
    for tool, hook_id, rendered, pack_id in zip(
        state.tools,
        state.hook_ids,
        state.rendered_blocks,
        state.pack_ids,
        strict=True,
    ):
        start_marker = _managed_block_start(tool, hook_id)
        end_marker = _managed_block_end(tool, hook_id)
        start = current.find(start_marker)
        if start == -1:
            issues.append(
                DoctorIssue(
                    code="tool-hook-block-missing",
                    severity=_ERROR,
                    message="Managed tool hook block is missing from the target file.",
                    path=state.path,
                    pack_id=pack_id,
                )
            )
            continue
        end = current.find(end_marker, start)
        if end == -1:
            issues.append(
                DoctorIssue(
                    code="tool-hook-block-invalid",
                    severity=_ERROR,
                    message="Managed tool hook block is missing its end marker.",
                    path=state.path,
                    pack_id=pack_id,
                )
            )
            continue
        block_body = current[start + len(start_marker) : end].strip("\n")
        if block_body != rendered:
            issues.append(
                DoctorIssue(
                    code="tool-hook-block-drift",
                    severity=_WARNING,
                    message=(
                        "Managed tool hook block has drifted from the desired content."
                    ),
                    path=state.path,
                    pack_id=pack_id,
                )
            )
    return issues


def _unexpected_tool_hook_issues(
    context: RemoveContext,
    selected_ids: set[str],
) -> list[DoctorIssue]:
    """Return issues for stale tool-hook blocks outside the selected pack set.

    Args:
        context: Shared doctor context.
        selected_ids: Currently selected pack ids.

    Returns:
        Issues for orphaned or unexpected managed tool-hook blocks.
    """
    expected_by_path = _expected_tool_hook_blocks_by_path(context, selected_ids)
    return [
        issue
        for path in _known_tool_hook_paths(context)
        for issue in [
            _unexpected_tool_hook_issue_for_path(context, path, expected_by_path)
        ]
        if issue is not None
    ]


def _expected_tool_hook_blocks_by_path(
    context: RemoveContext,
    selected_ids: set[str],
) -> dict[str, set[tuple[str, str]]]:
    """Return expected managed tool-hook block ids keyed by target path.

    Args:
        context: Shared doctor context with packs and profile.
        selected_ids: Currently selected pack ids.

    Returns:
        Expected `(tool, hook_id)` pairs keyed by project-relative target path.
    """
    return {
        state.path: {
            (tool, hook_id)
            for tool, hook_id in zip(state.tools, state.hook_ids, strict=True)
        }
        for state in plan_tool_hook_targets(
            context.root,
            context.packs,
            context.profile,
            selected_ids,
        )
    }


def _known_tool_hook_paths(context: RemoveContext) -> list[str]:
    """Return deterministic tool-hook target paths from all known packs.

    Args:
        context: Shared doctor context with the available pack registry.

    Returns:
        Sorted project-relative tool-hook target paths.
    """
    all_pack_ids = {pack.id for pack in context.packs}
    return sorted(
        state.path
        for state in plan_tool_hook_targets(
            context.root,
            context.packs,
            context.profile,
            all_pack_ids,
        )
    )


def _unexpected_tool_hook_issue_for_path(
    context: RemoveContext,
    path: str,
    expected_by_path: dict[str, set[tuple[str, str]]],
) -> DoctorIssue | None:
    """Return one orphan/unexpected tool-hook issue for a target path.

    Args:
        context: Shared doctor context with project root information.
        path: Project-relative tool-hook target path to inspect.
        expected_by_path: Expected managed hook blocks keyed by target path.

    Returns:
        One issue when the target contains stale managed blocks, else `None`.
    """
    target = context.root / path
    if not target.exists():
        return None
    actual_blocks = _tool_hook_blocks_in_text(target.read_text(encoding="utf-8"))
    if not actual_blocks:
        return None
    expected_blocks = expected_by_path.get(path, set())
    if not actual_blocks - expected_blocks:
        return None
    return DoctorIssue(
        code=(
            "tool-hook-block-orphan"
            if not expected_blocks
            else "tool-hook-block-unexpected"
        ),
        severity=_WARNING,
        message=(
            "Managed tool hook block exists for a pack that is not currently selected."
            if not expected_blocks
            else "Target file contains managed tool hook blocks that are not expected "
            "for the current pack set."
        ),
        path=path,
    )


def _pack_local_skill_issues(
    root: Path,
    state: CodexSkillTargetState,
) -> list[DoctorIssue]:
    """Return issues for one pack-local skill file.

    Args:
        root: Project root for resolving the skill path.
        state: Desired pack-local skill state.

    Returns:
        Issues for missing or drifted skill files.
    """
    target = root / state.path
    if not target.exists():
        return [
            DoctorIssue(
                code="pack-local-skill-missing",
                severity=_ERROR,
                message="Pack-local skill file is missing from disk.",
                path=state.path,
                pack_id=state.pack_id,
            )
        ]
    current = target.read_text(encoding="utf-8")
    if current == state.rendered_content:
        return []
    return [
        DoctorIssue(
            code="pack-local-skill-drift",
            severity=_WARNING,
            message="Pack-local skill file has drifted from the desired content.",
            path=state.path,
            pack_id=state.pack_id,
        )
    ]


def _orphan_pack_local_skill_issues(
    root: Path,
    selected_ids: set[str],
    context: RemoveContext,
) -> list[DoctorIssue]:
    """Return issues for orphaned repo-local skill files.

    Args:
        root: Project root that owns `.agents/skills`.
        selected_ids: Currently selected pack ids.
        context: Shared doctor context for desired skill planning.

    Returns:
        Warning issues for orphaned skill files.
    """
    skills_root = root / ".agents" / "skills"
    if not skills_root.exists():
        return []
    expected_paths = {
        state.path
        for state in plan_codex_skill_targets(
            root,
            context.packs,
            context.profile,
            selected_ids,
        )
    }
    issues: list[DoctorIssue] = []
    for path in sorted(skills_root.rglob("SKILL.md")):
        rel = path.relative_to(root).as_posix()
        if rel in expected_paths:
            continue
        issues.append(
            DoctorIssue(
                code="pack-local-skill-orphan",
                severity=_WARNING,
                message="Pack-local skill file exists on disk but is not selected.",
                path=rel,
            )
        )
    return issues


def _run_doctor_check(root: Path, spec: DoctorCheckSpec) -> list[DoctorIssue]:
    """Execute one pack-owned doctor check.

    Args:
        root: Project root for resolving any target paths.
        spec: Pack-owned doctor check contribution to execute.

    Returns:
        Issues detected by the check.

    Raises:
        ValueError: The doctor check type is unsupported.
    """
    if spec.check_type == "skill_front_matter":
        return _skill_front_matter_issues(root, spec)
    raise ValueError(f"Unsupported doctor check type: {spec.check_type}")


def _skill_front_matter_issues(root: Path, spec: DoctorCheckSpec) -> list[DoctorIssue]:
    """Return front-matter correctness issues for one pack-local skill file.

    Args:
        root: Project root used to resolve the skill file.
        spec: Doctor check specification for one skill path.

    Returns:
        Issues for missing, malformed, or incomplete front matter.
    """
    if spec.skill_path is None:
        raise ValueError(f"Doctor check '{spec.id}' must define 'skill_path'.")
    path = (root / ".agents" / "skills" / spec.skill_path / "SKILL.md").resolve()
    project_path = path.relative_to(root.resolve()).as_posix()
    if not path.exists():
        return [
            DoctorIssue(
                code="skill-front-matter-missing-file",
                severity=_ERROR,
                message="Expected pack-local skill file is missing from disk.",
                path=project_path,
                pack_id=spec.pack_id,
                check_id=spec.id,
            )
        ]
    content = path.read_text(encoding="utf-8")
    front_matter, error = _parse_front_matter(content)
    if error == "missing":
        return [
            DoctorIssue(
                code="skill-front-matter-missing",
                severity=_ERROR,
                message="Skill file is missing required front matter.",
                path=project_path,
                pack_id=spec.pack_id,
                check_id=spec.id,
            )
        ]
    if error is not None:
        return [
            DoctorIssue(
                code="skill-front-matter-malformed",
                severity=_ERROR,
                message=error,
                path=project_path,
                pack_id=spec.pack_id,
                check_id=spec.id,
            )
        ]
    issues: list[DoctorIssue] = []
    for key in spec.required_front_matter:
        if front_matter.get(key, "").strip():
            continue
        issues.append(
            DoctorIssue(
                code="skill-front-matter-required-key-missing",
                severity=_ERROR,
                message=f"Skill front matter is missing required key '{key}'.",
                path=project_path,
                pack_id=spec.pack_id,
                check_id=spec.id,
            )
        )
    return issues


def _parse_front_matter(content: str) -> tuple[dict[str, str], str | None]:
    """Parse simple YAML-like front matter from a skill file.

    Args:
        content: Full skill file content.

    Returns:
        Parsed key/value pairs and an optional error string.
        The special error value `"missing"` indicates no front matter block.
    """
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, "missing"
    end_index = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end_index = index
            break
    if end_index is None:
        return {}, "Front matter start marker is missing a closing '---'."
    parsed: dict[str, str] = {}
    for raw_line in lines[1:end_index]:
        line = raw_line.strip()
        if not line:
            continue
        if ":" not in line:
            return {}, f"Malformed front matter line: {raw_line}"
        key, value = line.split(":", 1)
        parsed[key.strip()] = value.strip().strip("'\"")
    return parsed, None


def _tool_hook_blocks_in_text(content: str) -> set[tuple[str, str]]:
    """Return managed tool-hook block ids present in file content.

    Args:
        content: Full file content to inspect.

    Returns:
        Set of `(tool, hook_id)` tuples found in managed block start markers.
    """
    return {
        (match.group(1), match.group(2))
        for match in _TOOL_HOOK_START_RE.finditer(content)
    }


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


def _project_relative_path(project_root: Path, install_root: Path, path: str) -> str:
    """Return an install-root-relative path as project-root-relative text.

    Args:
        project_root: Absolute project root for reporting.
        install_root: Absolute Grove install root.
        path: Path relative to the install root.

    Returns:
        Project-root-relative path string.
    """
    return ((install_root / path).resolve()).relative_to(project_root).as_posix()


def _managed_block_start(tool: str, hook_id: str) -> str:
    """Return the stable start marker for one managed tool hook block.

    Args:
        tool: External tool id for the hook.
        hook_id: Hook identifier within the tool.

    Returns:
        Stable start marker string.
    """
    return f"<!-- grove:tool-hook:{tool}:{hook_id}:start -->"


def _managed_block_end(tool: str, hook_id: str) -> str:
    """Return the stable end marker for one managed tool hook block.

    Args:
        tool: External tool id for the hook.
        hook_id: Hook identifier within the tool.

    Returns:
        Stable end marker string.
    """
    return f"<!-- grove:tool-hook:{tool}:{hook_id}:end -->"
