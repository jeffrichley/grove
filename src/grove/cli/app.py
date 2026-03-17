"""Typer app and grove init command: analyzer -> composer -> file_ops -> manifest."""

import sys
from importlib.metadata import version
from importlib.resources import as_file, files
from pathlib import Path

import typer

from grove.analyzer import analyze
from grove.core import apply, compose, save_manifest
from grove.core.file_ops import ApplyOptions
from grove.core.manifest import MANIFEST_SCHEMA_VERSION
from grove.core.models import (
    GroveSection,
    InstalledPackRecord,
    ManifestState,
    ProjectSection,
)
from grove.core.registry import discover_packs
from grove.tui import GroveInitApp, SetupState

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

    Args:
        root: Resolved project root directory.
    """
    state = SetupState(root=root, install_root=root / ".grove")
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
        Exit: When a pack id is not found in the registry (typer.Exit).
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
            typer.echo(
                f"Error: pack '{pid}' not found; available: {available}",
                err=True,
            )
            raise typer.Exit(1)

    profile = analyze(root)
    install_root = root / ".grove"
    plan = compose(profile, selected, install_root, packs)

    grove_version = version("grove")
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


@app.command()
def init(
    root: Path = typer.Option(  # noqa: B008
        Path.cwd(),  # noqa: B008
        "--root",
        "-r",
        help="Project root (default: current directory).",
    ),
    pack: list[str] | None = typer.Option(  # noqa: B008
        None,
        "--pack",
        "-p",
        help="Pack(s) to install (default: base, python).",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Do not write files; only report what would be done.",
    ),
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
        Exit: On validation error (e.g. root not a dir, unknown pack) via typer.Exit.
    """
    root = Path(root).resolve()
    if not root.is_dir():
        typer.echo(f"Error: root is not a directory: {root}", err=True)
        raise typer.Exit(1)

    if pack is None and sys.stdout.isatty():
        _run_init_tui(root)
        return

    _run_init_flag_based(root, pack, dry_run)


def main() -> None:
    """Entry point for the grove console script."""
    app()


if __name__ == "__main__":
    main()
