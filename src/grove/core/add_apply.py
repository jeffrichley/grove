"""Apply and merge: compose plan for new packs and merge into manifest."""

from pathlib import Path

from grove.analyzer import analyze
from grove.core.add_impl import merge_generated
from grove.core.composer import compose
from grove.core.file_ops import ApplyOptions, apply
from grove.core.models import InstalledPackRecord, ManifestState, PackManifest


def apply_and_merge(
    manifest: ManifestState,
    to_add: list[str],
    root: Path,
    pack_roots: dict[str, Path],
    packs: list[PackManifest],
) -> ManifestState:
    """Compose, apply, and merge new pack files into manifest.

    Args:
        manifest: Loaded manifest.
        to_add: Pack ids to add (dependency order).
        root: Project root.
        pack_roots: Map pack_id -> pack root path.
        packs: All packs in dependency order.

    Returns:
        Updated ManifestState with new installed_packs and generated_files merged.
    """
    selected = [p.id for p in manifest.installed_packs] + to_add
    install_root = root / (
        manifest.init_provenance.install_root if manifest.init_provenance else ".grove"
    )
    profile = analyze(root)
    plan = compose(profile, selected, install_root, packs)
    options = ApplyOptions(dry_run=False, collision_strategy="overwrite")
    updated = apply(plan, manifest, options, pack_roots)
    new_records = [
        InstalledPackRecord(id=p.id, version=p.version) for p in packs if p.id in to_add
    ]
    merged = merge_generated(manifest, updated)
    return manifest.model_copy(
        update={
            "installed_packs": manifest.installed_packs + new_records,
            "generated_files": merged,
        }
    )
