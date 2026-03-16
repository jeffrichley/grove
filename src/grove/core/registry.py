"""Pack registry: discover and load packs from a directory in dependency order."""

from importlib.resources import as_file, files
from pathlib import Path

from grove.core.models import PackManifest
from grove.packs.loader import load_pack_manifest


def discover_packs(builtins_dir: Path | None = None) -> list[PackManifest]:
    """Discover packs in a directory and return manifests in dependency order.

    Scans subdirectories of builtins_dir. When builtins_dir is None, uses
    the grove.packs.builtins package resource (works from source, installed
    package, or zip). Each subdir that contains a pack manifest (pack.toml)
    is loaded. Pack names are not hard-coded; discovery is by directory
    layout. Packs are returned in dependency order (e.g. base before python
    when python depends_on base). Dependency resolution may raise ValueError
    if a pack lists a dependency not in the discovered set.

    Args:
        builtins_dir: Directory containing one subdir per pack. If None,
            uses the builtins shipped with the grove.packs package.

    Returns:
        List of PackManifest in dependency order.

    Raises:
        FileNotFoundError: builtins_dir was passed and does not exist.
    """
    if builtins_dir is not None:
        root = builtins_dir.resolve()
        if not root.is_dir():
            raise FileNotFoundError(f"Builtins directory not found: {root}")
        return _discover_packs_from_path(root)
    # Use package resource so discovery works from source, install, or zip.
    builtins_ref = files("grove.packs") / "builtins"
    with as_file(builtins_ref) as root_path:
        return _discover_packs_from_path(Path(root_path))


def _discover_packs_from_path(root: Path) -> list[PackManifest]:
    """Scan root for pack subdirs and return manifests in dependency order.

    Args:
        root: Directory containing one subdir per pack (each with pack.toml).

    Returns:
        List of PackManifest in dependency order (dependencies first).
    """
    by_id: dict[str, PackManifest] = {}
    for subdir in sorted(root.iterdir()):
        if not subdir.is_dir():
            continue
        try:
            manifest = load_pack_manifest(subdir)
        except FileNotFoundError:
            continue
        by_id[manifest.id] = manifest
    return _dependency_order(by_id)


def _dependency_order(by_id: dict[str, PackManifest]) -> list[PackManifest]:
    """Return packs in topological order by depends_on. Base required when ref'd.

    The nested visit() may raise ValueError if a pack depends on a pack not in by_id.

    Args:
        by_id: Map of pack id to PackManifest.

    Returns:
        Packs in dependency order (dependencies before dependents).
    """
    order: list[PackManifest] = []
    seen: set[str] = set()

    def visit(manifest: PackManifest) -> None:
        """Visit one pack and its dependencies in topological order.

        Args:
            manifest: Pack to visit.

        Raises:
            ValueError: If the pack depends on a pack not in by_id.
        """
        if manifest.id in seen:
            return
        for dep_id in manifest.depends_on:
            if dep_id not in by_id:
                raise ValueError(
                    f"Pack '{manifest.id}' depends on '{dep_id}', "
                    "which is not in the builtins directory"
                )
            visit(by_id[dep_id])
        seen.add(manifest.id)
        order.append(manifest)

    for manifest in by_id.values():
        visit(manifest)

    return order
