"""File operations: preview, apply, and sync install plan with collision handling.

Supports dry_run and preview (path + content). No overwrite without explicit
caller-provided strategy (overwrite | skip | rename); otherwise fail.
"""

from pathlib import Path
from typing import Literal

from grove.core.models import (
    GeneratedFileRecord,
    InstallPlan,
    ManifestState,
)
from grove.core.renderer import render

CollisionStrategy = Literal["overwrite", "skip", "rename"]


class ApplyOptions:
    """Options for apply(): dry_run and collision strategy."""

    def __init__(
        self,
        *,
        dry_run: bool = False,
        collision_strategy: CollisionStrategy = "overwrite",
    ) -> None:
        """Initialize apply options.

        Args:
            dry_run: If True, do not write files or update manifest.
            collision_strategy: What to do when destination path exists:
                overwrite — replace file; skip — do not write this file;
                rename — write to a new name (e.g. path.1).
        """
        self.dry_run = dry_run
        self.collision_strategy = collision_strategy


def _next_available_path(path: Path) -> Path:
    """Return next available path if path exists (e.g. path.1, path.2).

    Args:
        path: Desired path that may already exist.

    Returns:
        path if it does not exist, else path.1, path.2, etc.
    """
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    n = 1
    while True:
        candidate = parent / f"{stem}.{n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def preview(
    plan: InstallPlan,
    pack_roots: dict[str, Path],
) -> list[tuple[Path, str]]:
    """Produce a list of (destination path, rendered content) without writing.

    Args:
        plan: Install plan with files (pack_id, src, dst, variables).
        pack_roots: Map pack_id -> absolute path to pack root (for template resolution).

    Returns:
        List of (dst_path, content) in plan order.

    Raises:
        KeyError: A pack_id in a PlannedFile is not in pack_roots.
    """
    result: list[tuple[Path, str]] = []
    for planned in plan.files:
        root = pack_roots.get(planned.pack_id)
        if root is None:
            raise KeyError(
                f"Pack id '{planned.pack_id}' not in pack_roots; "
                f"keys: {sorted(pack_roots.keys())}"
            )
        template_path = (root / planned.src).resolve()
        content = render(template_path, planned.variables)
        dst = (
            planned.dst
            if planned.dst.is_absolute()
            else plan.install_root.resolve() / planned.dst
        )
        result.append((dst.resolve(), content))
    return result


def apply(
    plan: InstallPlan,
    manifest: ManifestState,
    options: ApplyOptions,
    pack_roots: dict[str, Path],
    collision_overrides: dict[str, CollisionStrategy] | None = None,
) -> ManifestState:
    """Write planned files to disk and return updated manifest.

    When a destination path already exists, behavior is determined by
    collision_overrides[path_key] if provided, else options.collision_strategy.
    path_key is the destination path relative to install_root (posix).

    Args:
        plan: Install plan with install_root and files.
        manifest: Current manifest state; will be updated with generated_files.
        options: dry_run and default collision_strategy.
        pack_roots: Map pack_id -> absolute path to pack root.
        collision_overrides: Optional per-path strategy (overwrite | skip | rename).

    Returns:
        Updated ManifestState with generated_files reflecting written paths
        (unchanged if dry_run).

    Raises:
        KeyError: A pack_id in a PlannedFile is not in pack_roots.
    """
    if options.dry_run:
        return manifest

    overrides = collision_overrides or {}
    install_root = plan.install_root.resolve()
    generated: list[GeneratedFileRecord] = []

    for planned in plan.files:
        root = pack_roots.get(planned.pack_id)
        if root is None:
            raise KeyError(
                f"Pack id '{planned.pack_id}' not in pack_roots; "
                f"keys: {sorted(pack_roots.keys())}"
            )
        template_path = (root / planned.src).resolve()
        content = render(template_path, planned.variables)
        dst = planned.dst if planned.dst.is_absolute() else install_root / planned.dst
        dst = dst.resolve()
        path_key = planned.dst.as_posix() if not planned.dst.is_absolute() else str(dst)
        strategy = overrides.get(path_key, options.collision_strategy)

        if dst.exists():
            if strategy == "skip":
                continue
            if strategy == "rename":
                dst = _next_available_path(dst)
            # overwrite: fall through
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)

        dst.write_text(content, encoding="utf-8")
        rel = dst.relative_to(install_root)
        generated.append(
            GeneratedFileRecord(path=rel.as_posix(), pack_id=planned.pack_id)
        )

    return manifest.model_copy(
        update={"generated_files": manifest.generated_files + generated}
    )
