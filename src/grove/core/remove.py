"""Top-level remove orchestration for Grove lifecycle changes."""

from collections.abc import Mapping
from pathlib import Path

from grove.analyzer import analyze
from grove.core.manifest import load_manifest, save_manifest
from grove.core.models import RemovePlan
from grove.core.registry import get_builtin_pack_roots_and_packs
from grove.core.remove_apply import apply_remove
from grove.core.remove_impl import build_remove_context, plan_remove
from grove.exceptions import GroveManifestError, GrovePackError


def run_remove(
    root: Path,
    pack_id: str,
    *,
    dry_run: bool = False,
) -> RemovePlan:
    """Plan and optionally apply removal of one installed pack.

    Args:
        root: Project root that owns the Grove manifest.
        pack_id: Pack id to remove.
        dry_run: If True, only compute the removal plan.

    Returns:
        RemovePlan describing the computed lifecycle changes.

    Raises:
        GroveManifestError: Manifest is missing or invalid.
        GrovePackError: Removal is blocked or the target pack is invalid.
    """
    manifest_path = root / ".grove" / "manifest.toml"
    try:
        manifest = load_manifest(manifest_path)
    except (FileNotFoundError, ValueError) as exc:
        raise GroveManifestError(str(exc)) from exc

    pack_roots, packs = get_builtin_pack_roots_and_packs()
    context = build_remove_context(
        root,
        manifest,
        pack_roots,
        analyze(root),
        packs,
    )
    try:
        remove_plan = plan_remove(pack_id, context)
    except ValueError as exc:
        raise GrovePackError(str(exc)) from exc
    if dry_run:
        return remove_plan

    updated_manifest = apply_remove(context, remove_plan, dry_run=True)
    temp_manifest_path = manifest_path.with_name(f"{manifest_path.name}.tmp")
    changed_paths = [change.path for change in remove_plan.changes]
    file_snapshot = _snapshot_paths(root, changed_paths)
    save_manifest(temp_manifest_path, updated_manifest)
    try:
        apply_remove(context, remove_plan, dry_run=False)
        temp_manifest_path.replace(manifest_path)
    except (OSError, ValueError) as exc:
        _restore_snapshot(root, file_snapshot)
        if temp_manifest_path.exists():
            temp_manifest_path.unlink()
        raise GroveManifestError(str(exc)) from exc
    return remove_plan


def _snapshot_paths(root: Path, paths: list[str]) -> dict[str, str | None]:
    """Capture current on-disk content for paths that may change during remove.

    Args:
        root: Project root used to resolve project-relative paths.
        paths: Project-relative file paths that may be mutated.

    Returns:
        Mapping of project-relative paths to their current content, or None when
        the file does not yet exist.
    """
    snapshot: dict[str, str | None] = {}
    for path in sorted(set(paths)):
        target = (root / path).resolve()
        snapshot[path] = target.read_text(encoding="utf-8") if target.exists() else None
    return snapshot


def _restore_snapshot(root: Path, snapshot: Mapping[str, str | None]) -> None:
    """Restore files captured before a failed remove apply/finalize step.

    Args:
        root: Project root used to resolve project-relative paths.
        snapshot: Previously captured file content for changed paths.
    """
    for path, content in snapshot.items():
        target = (root / path).resolve()
        if content is None:
            if target.exists():
                target.unlink()
            _prune_empty_parent_dirs(target.parent, stop_at=root.resolve())
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def _prune_empty_parent_dirs(path: Path, *, stop_at: Path) -> None:
    """Remove empty parent directories up to, but not including, stop_at.

    Args:
        path: Directory path to start pruning from.
        stop_at: Directory boundary that must not be removed.
    """
    current = path.resolve()
    while current != stop_at and current.exists():
        try:
            current.rmdir()
        except OSError:
            return
        current = current.parent
