"""Typer app and grove init command: analyzer -> composer -> file_ops -> manifest."""

import sys
from importlib.metadata import version
from importlib.resources import as_file, files
from pathlib import Path
from typing import Annotated

import typer

from grove.analyzer import analyze
from grove.core import apply, compose, save_manifest
from grove.core.add import add_pack
from grove.core.file_ops import ApplyOptions
from grove.core.manifest import MANIFEST_SCHEMA_VERSION
from grove.core.models import (
    GroveSection,
    InitProvenance,
    InstalledPackRecord,
    ManifestState,
    ProjectSection,
)
from grove.core.registry import discover_packs, get_builtin_pack_roots_and_packs
from grove.core.sync import run_sync
from grove.exceptions import (
    GroveConfigError,
    GroveError,
    GroveManifestError,
    GrovePackError,
)
from grove.tui import GroveInitApp
from grove.tui.state import setup_state_from_manifest

app = typer.Typer(help="Grove: context engineering for AI-assisted development.")


@app.callback(invoke_without_command=True)
def _callback(
    ctx: typer.Context,
) -> None:
    """Show help when no subcommand is given.

    Args:
        ctx: Typer context (used to get help and invoked subcommand).
    """
    if ctx.invoked_subcommand is not None:
        return
    typer.echo(ctx.get_help())


def _run_init_tui(root: Path) -> None:
    """Launch interactive TUI for grove init.

    If .grove/manifest.toml exists, prefill state from it (packs, install root,
    core options) so Recommended packs and Core install show previous choices.

    Args:
        root: Resolved project root directory.
    """
    manifest_path = root / ".grove" / "manifest.toml"
    state = setup_state_from_manifest(manifest_path, root)
    GroveInitApp(state).run()


def _run_init_flag_based(
    root: Path,
    pack: list[str] | None,
    dry_run: bool,
) -> None:
    """Run flag-based grove init (no TUI).

    Args:
        root: Resolved project root directory.
        pack: Pack ids to install, or None for default (base, python).
        dry_run: If True, do not write files.

    Raises:
        GrovePackError: When a pack id is not found in the registry.
    """
    builtins_ref = files("grove.packs") / "builtins"
    with as_file(builtins_ref) as builtins_path:
        builtins_dir = Path(builtins_path)
        packs = discover_packs(builtins_dir)
        pack_roots = {p.id: builtins_dir / p.id for p in packs}

    selected = pack if pack is not None and len(pack) > 0 else ["base", "python"]
    for pid in selected:
        if pid not in pack_roots:
            available = sorted(pack_roots.keys())
            raise GrovePackError(f"pack '{pid}' not found; available: {available}")

    profile = analyze(root)
    install_root = root / ".grove"
    plan = compose(profile, selected, install_root, packs)

    grove_version = version("grove")
    # Store install root as relative for portable provenance
    install_root_provenance = ".grove"
    manifest = ManifestState(
        grove=GroveSection(
            version=grove_version, schema_version=MANIFEST_SCHEMA_VERSION
        ),
        project=ProjectSection(
            root=str(root),
            analysis_summary=_analysis_summary(profile),
        ),
        packs=[
            InstalledPackRecord(id=p.id, version=p.version)
            for p in packs
            if p.id in selected
        ],
        generated_files=[],
        init_provenance=InitProvenance(
            install_root=install_root_provenance,
            core_include_adrs=True,
            core_include_handoffs=True,
            core_include_scoped_rules=True,
            core_include_memory=True,
            core_include_skills_dir=True,
        ),
    )

    options = ApplyOptions(dry_run=dry_run, collision_strategy="overwrite")
    updated = apply(plan, manifest, options, pack_roots)

    if dry_run:
        typer.echo("Dry run: would write .grove/ and manifest (no files changed).")
        return

    install_root.mkdir(parents=True, exist_ok=True)
    save_manifest(install_root / "manifest.toml", updated)
    typer.echo(f"Initialized .grove/ at {install_root}")


def _analysis_summary(profile: object) -> str:
    """Build a short analysis summary string from profile for manifest.

    Args:
        profile: ProjectProfile or object with language, package_manager,
            test_framework, tools attributes.

    Returns:
        Comma-separated summary string (e.g. 'python, uv, pytest').
    """
    parts: list[str] = []
    for attr in ("language", "package_manager", "test_framework"):
        val = getattr(profile, attr, None)
        if isinstance(val, str) and val:
            parts.append(val)
    tools = getattr(profile, "tools", None)
    if isinstance(tools, list) and tools:
        parts.extend(tools)
    return ", ".join(parts) if parts else ""


def _resolve_root(root: Path | None) -> Path:
    """Resolve and validate project root; raise if not a directory.

    Args:
        root: Project root or None for cwd.

    Returns:
        Resolved absolute Path to project root.

    Raises:
        GroveConfigError: When path is not a directory.
    """
    if root is None:
        root = Path.cwd()
    root = Path(root).resolve()
    if not root.is_dir():
        raise GroveConfigError(f"root is not a directory: {root}")
    return root


@app.command()
def init(
    root: Annotated[
        Path | None,
        typer.Option("--root", "-r", help="Project root (default: current directory)."),
    ] = None,
    pack: Annotated[
        list[str] | None,
        typer.Option(
            "--pack",
            "-p",
            help="Pack(s) to install (default: base, python).",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Do not write files; only report what would be done.",
        ),
    ] = False,
) -> None:
    """Initialize .grove/ with Base Pack and optional capability packs.

    Runs analyzer on --root, composes an install plan from selected packs,
    renders templates, and writes .grove/ and manifest.toml. Use --dry-run
    to preview without writing.

    Args:
        root: Project root directory (default: current directory).
        pack: Pack ids to install (default: base, python).
        dry_run: If True, do not write files.

    Raises:
        typer.Exit: On validation error (e.g. root not a dir, unknown pack).
    """
    try:
        root = _resolve_root(root)
    except GroveError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e

    if pack is None and sys.stdout.isatty():
        _run_init_tui(root)
        return

    try:
        _run_init_flag_based(root, pack, dry_run)
    except GroveError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
def sync(
    root: Annotated[
        Path | None,
        typer.Option("--root", "-r", help="Project root (default: current directory)."),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Do not write files; only report what would be written.",
        ),
    ] = False,
) -> None:
    """Re-render managed files from current templates and profile.

    Requires an existing Grove manifest (.grove/manifest.toml). Writes only
    paths listed in the manifest; does not add or remove files from the manifest.

    Args:
        root: Project root directory (default: current directory).
        dry_run: If True, do not write files; report what would be written.

    Raises:
        typer.Exit: When manifest is missing or invalid.
    """
    try:
        root = _resolve_root(root)
        manifest_path = root / ".grove" / "manifest.toml"
        if not manifest_path.exists():
            raise GroveManifestError("No Grove manifest; run 'grove init' first.")
        written = run_sync(root, dry_run=dry_run)
    except GroveError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e

    if dry_run:
        typer.echo("Dry run: would write:")
        for p in written:
            typer.echo(f"  {p}")
    elif written:
        typer.echo("Updated:")
        for p in written:
            typer.echo(f"  {p}")
    else:
        typer.echo("No managed files to update.")


@app.command()
def add(
    pack: Annotated[str, typer.Argument(help="Pack id to add (e.g. 'python').")],
    root: Annotated[
        Path | None,
        typer.Option("--root", "-r", help="Project root (default: current directory)."),
    ] = None,
) -> None:
    """Add a pack to an existing Grove installation.

    Requires an existing manifest (.grove/manifest.toml). Resolves
    dependencies and updates the manifest and generated files.

    Args:
        pack: Pack id to install.
        root: Project root directory (default: current directory).

    Raises:
        typer.Exit: When manifest is missing or pack not found.
    """
    try:
        root = _resolve_root(root)
        manifest_path = root / ".grove" / "manifest.toml"
        if not manifest_path.exists():
            raise GroveManifestError("No Grove manifest; run 'grove init' first.")
        pack_roots, packs = get_builtin_pack_roots_and_packs()
        updated = add_pack(root, manifest_path, pack, pack_roots, packs)
    except GroveError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e

    save_manifest(manifest_path, updated)
    typer.echo(f"Added pack {pack}.")


def main() -> None:
    """Entry point for the grove console script."""
    app()


if __name__ == "__main__":
    main()
