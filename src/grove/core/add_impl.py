"""Internal helpers for add_pack: resolve deps, merge generated files."""

from grove.core.models import (
    GeneratedFileRecord,
    ManifestState,
    PackManifest,
)


def _need_ids(
    new_pack_id: str,
    by_id: dict[str, PackManifest],
    existing_ids: set[str],
) -> set[str]:
    """Collect new_pack_id and its deps not in existing_ids.

    Args:
        new_pack_id: Pack to add.
        by_id: Map pack id to PackManifest.
        existing_ids: Already installed pack ids.

    Returns:
        Set of pack ids to add (new_pack_id + missing deps), or empty.
    """
    if new_pack_id in existing_ids:
        return set()
    need = {new_pack_id}
    for dep_id in by_id[new_pack_id].depends_on:
        if dep_id not in existing_ids:
            need.add(dep_id)
    return need


def packs_to_add(
    manifest: ManifestState,
    new_pack_id: str,
    packs: list[PackManifest],
) -> list[str]:
    """Return pack ids to add in dependency order (deps first).

    Empty if new_pack_id is already installed.

    Args:
        manifest: Current manifest with installed_packs.
        new_pack_id: Pack to add.
        packs: All packs in dependency order.

    Returns:
        List of pack ids to add (deps first), or empty if already installed.
    """
    by_id = {p.id: p for p in packs}
    existing_ids = {p.id for p in manifest.installed_packs}
    need_ids = _need_ids(new_pack_id, by_id, existing_ids)
    return [p.id for p in packs if p.id in need_ids]


def merge_generated(
    manifest: ManifestState,
    updated: ManifestState,
) -> list[GeneratedFileRecord]:
    """Merge updated.generated_files into manifest, deduplicated by path.

    Args:
        manifest: Current manifest with generated_files.
        updated: Result of apply() with new generated_files.

    Returns:
        Merged list (manifest paths plus new paths from updated).
    """
    existing = {g.path for g in manifest.generated_files}
    out = list(manifest.generated_files)
    out.extend(g for g in updated.generated_files if g.path not in existing)
    return out
