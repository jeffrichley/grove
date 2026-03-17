"""Sync: re-render manifest.generated_files from current profile and templates."""

from pathlib import Path

from grove.analyzer import analyze
from grove.core.composer import compose
from grove.core.manifest import load_manifest
from grove.core.models import (
    ManifestState,
    PackManifest,
    PlannedFile,
    ProjectProfile,
)
from grove.core.registry import get_builtin_pack_roots_and_packs
from grove.core.renderer import render
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


def _write_planned(
    planned: PlannedFile,
    install_root: Path,
    pack_roots: dict[str, Path],
) -> None:
    """Render and write one planned file.

    Args:
        planned: File to render and write.
        install_root: Install root path.
        pack_roots: Map pack_id -> pack root path.

    Raises:
        KeyError: If planned.pack_id is not in pack_roots.
    """
    root = pack_roots.get(planned.pack_id)
    if root is None:
        raise KeyError(
            f"Pack id '{planned.pack_id}' not in pack_roots; "
            f"keys: {sorted(pack_roots.keys())}"
        )
    template_path = (root / planned.src).resolve()
    content = render(template_path, planned.variables)
    rel = (
        planned.dst
        if not planned.dst.is_absolute()
        else planned.dst.relative_to(install_root)
    )
    dst = install_root / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(content, encoding="utf-8")


def sync_managed(
    manifest: ManifestState,
    pack_roots: dict[str, Path],
    profile: ProjectProfile,
    packs: list[PackManifest],
    *,
    dry_run: bool = False,
) -> list[str]:
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
        List of paths (relative, posix) in manifest.generated_files that were
        (or would be) written.

    Raises:
        KeyError: A pack_id in the plan is not in pack_roots.
    """
    install_root = Path(manifest.project.root) / (
        manifest.init_provenance.install_root if manifest.init_provenance else ".grove"
    )
    install_root = install_root.resolve()
    selected = [p.id for p in manifest.installed_packs]
    plan = compose(profile, selected, install_root, packs)
    generated_set = {g.path for g in manifest.generated_files}
    written: list[str] = []
    for planned in plan.files:
        rel_posix = _rel_posix(planned, install_root)
        if rel_posix not in generated_set:
            continue
        if dry_run:
            written.append(rel_posix)
            continue
        try:
            _write_planned(planned, install_root, pack_roots)
        except KeyError:
            raise
        written.append(rel_posix)
    return written


def run_sync(root: Path, dry_run: bool = False) -> list[str]:
    """Load manifest, re-render managed files; return paths written.

    Uses builtin packs and analyzer on root. Call when .grove/manifest.toml
    exists.

    Args:
        root: Project root (manifest at root/.grove/manifest.toml).
        dry_run: If True, do not write files; return paths that would be written.

    Returns:
        List of paths (relative, posix) written or that would be written.

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
        return sync_managed(manifest, pack_roots, profile, packs, dry_run=dry_run)
    except KeyError as e:
        raise GroveManifestError(str(e)) from e
