"""Add pack: load manifest, resolve deps, compose, apply, merge manifest."""

from pathlib import Path

from grove.core.add_apply import apply_and_merge
from grove.core.add_impl import packs_to_add
from grove.core.manifest import load_manifest
from grove.core.models import ManifestState, PackManifest
from grove.exceptions import GroveManifestError, GrovePackError


def add_pack(
    root: Path,
    manifest_path: Path,
    new_pack_id: str,
    pack_roots: dict[str, Path],
    packs: list[PackManifest],
) -> ManifestState:
    """Load manifest, resolve deps, compose, apply, merge manifest.

    Does not save; caller must save_manifest.

    Args:
        root: Project root.
        manifest_path: Path to .grove/manifest.toml.
        new_pack_id: Pack id to add.
        pack_roots: Map pack_id -> pack root path.
        packs: All packs in dependency order.

    Returns:
        Updated ManifestState (installed_packs and generated_files merged).

    Raises:
        GroveManifestError: Manifest path does not exist or is invalid.
        GrovePackError: Pack not found or dependency missing.
    """
    try:
        manifest = load_manifest(manifest_path)
    except (FileNotFoundError, ValueError) as e:
        raise GroveManifestError(str(e)) from e
    if new_pack_id not in pack_roots:
        raise GrovePackError(
            f"Pack '{new_pack_id}' not found; available: {sorted(pack_roots.keys())}"
        )

    to_add = packs_to_add(manifest, new_pack_id, packs)
    if not to_add:
        return manifest

    return apply_and_merge(manifest, to_add, root, pack_roots, packs)
