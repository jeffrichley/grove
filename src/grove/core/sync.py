"""Sync: re-render manifest.generated_files from current profile and templates."""

from pathlib import Path

from grove.analyzer import analyze
from grove.core.composer import compose
from grove.core.file_ops import render_planned_file
from grove.core.manifest import load_manifest
from grove.core.markers import MarkerRange, find_anchor_ranges, find_user_regions
from grove.core.models import (
    AnchorSyncChange,
    InjectionProvenance,
    ManifestState,
    PackManifest,
    PlannedFile,
    ProjectProfile,
    SyncFileChange,
)
from grove.core.registry import get_builtin_pack_roots_and_packs
from grove.core.tool_hooks import apply_tool_hooks
from grove.exceptions import GroveManifestError


def _rel_posix(planned: PlannedFile, install_root: Path) -> str:
    """Return destination path relative to install_root as posix string.

    Args:
        planned: Planned file with dst path.
        install_root: Install root path.

    Returns:
        Relative path as posix string.
    """
    rel = (
        planned.dst
        if not planned.dst.is_absolute()
        else planned.dst.relative_to(install_root)
    )
    return rel.as_posix()


def sync_managed(
    manifest: ManifestState,
    pack_roots: dict[str, Path],
    profile: ProjectProfile,
    packs: list[PackManifest],
    *,
    dry_run: bool = False,
) -> list[SyncFileChange]:
    """Re-render and write only paths listed in manifest.generated_files.

    Loads no packs; caller must pass packs (e.g. from discover_packs).
    Does not modify manifest. Returns list of paths written or that would be
    written (relative to install_root, posix).

    Args:
        manifest: Current manifest (installed_packs, generated_files).
        pack_roots: Map pack_id -> absolute path to pack root.
        profile: Project profile for template variables.
        packs: All available packs in dependency order.
        dry_run: If True, do not write files; return paths that would be written.

    Returns:
        File change records in manifest.generated_files that were
        (or would be) written.

    Raises:
        KeyError: A pack_id in the plan is not in pack_roots.
        ValueError: Anchor reconstruction is unsafe for an existing file.
    """
    install_root = Path(manifest.project.root) / (
        manifest.init_provenance.install_root if manifest.init_provenance else ".grove"
    )
    install_root = install_root.resolve()
    project_root = Path(manifest.project.root).resolve()
    selected = [p.id for p in manifest.installed_packs]
    plan = compose(profile, selected, install_root, packs)
    generated_set = {g.path for g in manifest.generated_files}
    written: list[SyncFileChange] = []
    for planned in plan.files:
        rel_posix = _rel_posix(planned, install_root)
        if rel_posix not in generated_set:
            continue
        dst = install_root / rel_posix
        desired_content = render_planned_file(planned, pack_roots)
        current_content = dst.read_text(encoding="utf-8") if dst.exists() else None
        next_content = _sync_target_content(current_content, desired_content)
        if current_content == next_content:
            continue
        file_change = SyncFileChange(
            path=_path_relative_to_project_root(dst, project_root),
            anchors=_describe_anchor_changes(
                current_content,
                desired_content,
                planned.anchor_provenance,
            ),
        )
        if dry_run:
            written.append(file_change)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(next_content, encoding="utf-8")
        written.append(file_change)
    return written


def run_sync(root: Path, dry_run: bool = False) -> list[SyncFileChange]:
    """Load manifest, re-render managed files; return paths written.

    Uses builtin packs and analyzer on root. Call when .grove/manifest.toml
    exists.

    Args:
        root: Project root (manifest at root/.grove/manifest.toml).
        dry_run: If True, do not write files; return paths that would be written.

    Returns:
        File change records written or that would be written.

    Raises:
        GroveManifestError: Manifest missing, invalid, or pack not in builtins.
    """
    manifest_path = root / ".grove" / "manifest.toml"
    try:
        manifest = load_manifest(manifest_path)
    except (FileNotFoundError, ValueError) as e:
        raise GroveManifestError(str(e)) from e
    pack_roots, packs = get_builtin_pack_roots_and_packs()
    profile = analyze(root)
    try:
        written = sync_managed(manifest, pack_roots, profile, packs, dry_run=dry_run)
        hook_writes = apply_tool_hooks(
            root,
            manifest,
            packs,
            profile,
            dry_run=dry_run,
        )
        combined = list(written)
        seen_paths = {change.path for change in combined}
        for path in hook_writes:
            if path in seen_paths:
                continue
            combined.append(SyncFileChange(path=path))
            seen_paths.add(path)
        return combined
    except (KeyError, ValueError) as e:
        raise GroveManifestError(str(e)) from e


def _sync_target_content(current: str | None, desired: str) -> str:
    """Return the content that sync should leave on disk for one file.

    Args:
        current: Existing file content, if the file is present.
        desired: Newly composed desired file content.

    Returns:
        Content to write for this file.

    Raises:
        ValueError: Existing content lacks anchors required for safe reconstruction.
    """
    if current is None:
        return desired
    desired_with_users = _preserve_user_regions(current, desired)
    desired_anchors = find_anchor_ranges(desired_with_users)
    if not desired_anchors:
        return desired_with_users
    return _replace_anchor_bodies(current, desired_with_users, desired_anchors)


def _preserve_user_regions(current: str, desired: str) -> str:
    """Preserve user-region bodies from current content in desired content.

    Args:
        current: Existing file content on disk.
        desired: Newly composed desired file content.

    Returns:
        Desired content with current user-region bodies preserved where possible.
    """
    current_users = find_user_regions(current)
    desired_users = find_user_regions(desired)
    output = desired
    for region_id, desired_range in sorted(
        desired_users.items(),
        key=lambda item: item[1].start,
        reverse=True,
    ):
        current_range = current_users.get(region_id)
        if current_range is None:
            continue
        output = (
            output[: _body_start(desired_range)]
            + _body(current, current_range)
            + output[_body_end(desired_range) :]
        )
    return output


def _replace_anchor_bodies(
    current: str,
    desired: str,
    desired_anchors: dict[str, MarkerRange],
) -> str:
    """Replace anchor bodies in an existing file while preserving outer content.

    Args:
        current: Existing file content on disk.
        desired: Newly composed desired file content.
        desired_anchors: Desired anchor ranges keyed by name.

    Returns:
        Existing file content with anchor bodies replaced from desired.

    Raises:
        ValueError: Existing content lacks anchors required for safe reconstruction.
    """
    current_anchors = find_anchor_ranges(current)
    missing = sorted(
        anchor_name
        for anchor_name in desired_anchors
        if anchor_name not in current_anchors
    )
    if missing:
        raise ValueError(
            "Anchor reconstruction is unsafe; missing anchor(s): " + ", ".join(missing)
        )

    output = current
    for anchor_name, current_range in sorted(
        current_anchors.items(),
        key=lambda item: item[1].start,
        reverse=True,
    ):
        desired_range = desired_anchors.get(anchor_name)
        if desired_range is None:
            continue
        output = (
            output[: _body_start(current_range)]
            + _body(desired, desired_range)
            + output[_body_end(current_range) :]
        )
    return output


def _describe_anchor_changes(
    current: str | None,
    desired: str,
    anchor_provenance: dict[str, list[InjectionProvenance]],
) -> list[AnchorSyncChange]:
    """Return changed anchor bodies plus their provenance.

    The sync rewrite boundary is the full body of each `grove:anchor:*` region.
    Provenance therefore comes from composition metadata rather than on-disk
    markers, because rendered files intentionally do not include per-injection
    wrapper blocks.

    Args:
        current: Existing file content on disk, if any.
        desired: Newly composed desired file content.
        anchor_provenance: Provenance entries keyed by anchor name for the file.

    Returns:
        Ordered changed anchor descriptors for dry-run reporting.
    """
    desired_anchors = find_anchor_ranges(desired)
    if not desired_anchors:
        return []
    current_anchors = find_anchor_ranges(current) if current is not None else {}
    changes: list[AnchorSyncChange] = []
    for anchor_name, desired_range in sorted(
        desired_anchors.items(),
        key=lambda item: item[1].start,
    ):
        current_range = current_anchors.get(anchor_name)
        desired_body = _body(desired, desired_range)
        current_body = (
            "" if current_range is None else _body(current or "", current_range)
        )
        if current_range is not None and current_body == desired_body:
            continue
        changes.append(
            AnchorSyncChange(
                anchor=anchor_name,
                provenance=list(anchor_provenance.get(anchor_name, [])),
            )
        )
    return changes


def _path_relative_to_project_root(path: Path, project_root: Path) -> str:
    """Return a path relative to the project root when possible.

    Args:
        path: Absolute path to report.
        project_root: Absolute project root used as the reporting base.

    Returns:
        Project-root-relative path when nested under the root, else absolute path.
    """
    resolved = path.resolve()
    try:
        return resolved.relative_to(project_root).as_posix()
    except ValueError:
        return str(resolved)


def _body(content: str, marker_range: MarkerRange) -> str:
    """Return the content inside a marker pair.

    Args:
        content: File content to slice.
        marker_range: Marker range describing the pair.

    Returns:
        Content between the start and end markers.
    """
    return content[_body_start(marker_range) : _body_end(marker_range)]


def _body_start(marker_range: MarkerRange) -> int:
    """Return the body start offset for an anchor or user range.

    Args:
        marker_range: Marker range to inspect.

    Returns:
        Absolute string offset immediately after the start marker.
    """
    return marker_range.start + len(marker_range.start_token)


def _body_end(marker_range: MarkerRange) -> int:
    """Return the body end offset for an anchor or user range.

    Args:
        marker_range: Marker range to inspect.

    Returns:
        Absolute string offset immediately before the end marker.
    """
    return marker_range.end - len(marker_range.end_token)
