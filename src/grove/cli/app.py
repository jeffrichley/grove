"""Typer app and grove init command: analyzer -> composer -> file_ops -> manifest."""

import sys
from importlib.metadata import version
from importlib.resources import as_file, files
from pathlib import Path
from typing import Annotated, Never

import typer

from grove.analyzer import analyze
from grove.core import apply, compose, preview, save_manifest
from grove.core.add import add_pack
from grove.core.file_ops import ApplyOptions
from grove.core.manifest import MANIFEST_SCHEMA_VERSION
from grove.core.models import (
    GroveSection,
    InitProvenance,
    InstalledPackRecord,
    InstallPlan,
    ManifestState,
    ProjectSection,
)
from grove.core.registry import discover_packs, get_builtin_pack_roots_and_packs
from grove.core.sync import run_sync
from grove.core.tool_hooks import apply_tool_hooks
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


def _exit_with_error(message: str) -> Never:
    """Print a CLI error and exit non-zero.

    Args:
        message: User-facing error text. It should already be actionable.

    Raises:
        typer.Exit: Always exits with status code 1 after printing the message.
    """
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(1)


def _run_init_tui(root: Path) -> None:
    """Launch interactive TUI for grove init (first-time wizard).

    If .grove/manifest.toml exists, prefill state from it (packs, install root,
    core options) so Recommended packs and Core install show previous choices.

    Args:
        root: Resolved project root directory.
    """
    manifest_path = root / ".grove" / "manifest.toml"
    state = setup_state_from_manifest(manifest_path, root)
    GroveInitApp(state, mode="init").run()


def _run_manage_tui(root: Path) -> None:
    """Launch manage TUI: dashboard with installed packs, sync status, actions.

    Requires .grove/manifest.toml to exist (caller must check).

    Args:
        root: Resolved project root directory.
    """
    manifest_path = root / ".grove" / "manifest.toml"
    state = setup_state_from_manifest(manifest_path, root)
    GroveInitApp(state, mode="manage").run()


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
        _echo_dry_run_preview(plan, pack_roots, root)
        return

    install_root.mkdir(parents=True, exist_ok=True)
    apply_tool_hooks(root, updated, packs, profile)
    save_manifest(install_root / "manifest.toml", updated)
    typer.echo(f"Initialized .grove/ at {install_root}")


def _echo_dry_run_preview(
    plan: InstallPlan,
    pack_roots: dict[str, Path],
    root: Path,
) -> None:
    """Print a file-by-file dry-run preview for init.

    Args:
        plan: Install plan to preview.
        pack_roots: Pack roots used for template rendering.
        root: Project root used to relativize output paths.
    """
    typer.echo("Dry run: would write:")
    for path, content in preview(plan, pack_roots):
        rel_path = path.relative_to(root).as_posix()
        typer.echo(f"--- {rel_path} ---")
        typer.echo(content.rstrip())
    typer.echo("--- .grove/manifest.toml ---")
    typer.echo("[manifest preview omitted]")


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
    """Initialize Grove in a project.

    In a TTY with no `--pack` flags, this launches the interactive init flow.
    Otherwise it runs the non-interactive install path and writes `.grove/`
    plus `.grove/manifest.toml`. Use `--dry-run` to preview without writing.

    Args:
        root: Project root directory (default: current directory).
        pack: Pack ids to install for non-interactive init.
        dry_run: If True, report writes without changing files.
    """
    try:
        root = _resolve_root(root)
    except (GroveError, ValueError, KeyError) as e:
        _exit_with_error(str(e))

    if pack is None and sys.stdout.isatty():
        manifest_path = root / ".grove" / "manifest.toml"
        if manifest_path.exists():
            _run_manage_tui(root)
        else:
            _run_init_tui(root)
        return

    try:
        _run_init_flag_based(root, pack, dry_run)
    except (GroveError, ValueError, KeyError) as e:
        _exit_with_error(str(e))


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
    """Re-render managed files from the current templates and profile.

    This command requires an existing `.grove/manifest.toml` and only rewrites
    paths tracked in that manifest. Use `--dry-run` to report pending changes
    without writing them.

    Args:
        root: Project root directory (default: current directory).
        dry_run: If True, report writes without changing files.
    """
    try:
        root = _resolve_root(root)
        manifest_path = root / ".grove" / "manifest.toml"
        if not manifest_path.exists():
            raise GroveManifestError("No Grove manifest; run 'grove init' first.")
        written = run_sync(root, dry_run=dry_run)
    except GroveError as e:
        _exit_with_error(str(e))

    if dry_run:
        typer.echo("Dry run: would write:")
        for change in written:
            typer.echo(f"  {change.path}")
            for anchor_change in change.anchors:
                typer.echo(f"    anchor: {anchor_change.anchor}")
                for provenance in anchor_change.provenance:
                    typer.echo(
                        f"      from {provenance.pack_id}:{provenance.injection_id}"
                    )
    elif written:
        typer.echo("Updated:")
        for change in written:
            typer.echo(f"  {change.path}")
    else:
        typer.echo("No files to update.")


def _run_configure(root: Path) -> None:
    """Configure entry: init TUI when no manifest, manage TUI when manifest exists.

    Args:
        root: Resolved project root directory.
    """
    manifest_path = root / ".grove" / "manifest.toml"
    if manifest_path.exists():
        _run_manage_tui(root)
    else:
        _run_init_tui(root)


@app.command()
def configure(
    root: Annotated[
        Path | None,
        typer.Option("--root", "-r", help="Project root (default: current directory)."),
    ] = None,
) -> None:
    """Open the interactive Grove setup or manage dashboard.

    With no `.grove/manifest.toml`, this launches the full init TUI. With an
    existing manifest, it launches the manage TUI for installed packs, re-run
    analysis, and full re-setup actions.

    Args:
        root: Project root directory (default: current directory).
    """
    try:
        root = _resolve_root(root)
    except GroveError as e:
        _exit_with_error(str(e))
    if not sys.stdout.isatty():
        _exit_with_error(
            "Configure is interactive; run in a terminal, or use "
            "'grove init --pack' for non-interactive init."
        )
    _run_configure(root)


@app.command()
def add(
    pack: Annotated[str, typer.Argument(help="Pack id to add (e.g. 'python').")],
    root: Annotated[
        Path | None,
        typer.Option("--root", "-r", help="Project root (default: current directory)."),
    ] = None,
) -> None:
    """Add a pack to an existing Grove installation.

    This command requires `.grove/manifest.toml`, resolves any missing
    dependencies for the requested pack, applies new generated files, and then
    updates the manifest.

    Args:
        pack: Pack id to add.
        root: Project root directory (default: current directory).
    """
    try:
        root = _resolve_root(root)
        manifest_path = root / ".grove" / "manifest.toml"
        if not manifest_path.exists():
            raise GroveManifestError("No Grove manifest; run 'grove init' first.")
        pack_roots, packs = get_builtin_pack_roots_and_packs()
        updated = add_pack(root, manifest_path, pack, pack_roots, packs)
        profile = analyze(root)
        apply_tool_hooks(root, updated, packs, profile)
    except (GroveError, ValueError, KeyError) as e:
        _exit_with_error(str(e))

    save_manifest(manifest_path, updated)
    typer.echo(f"Added pack {pack}.")


@app.command()
def manage(
    root: Annotated[
        Path | None,
        typer.Option("--root", "-r", help="Project root (default: current directory)."),
    ] = None,
) -> None:
    """Alias for `grove configure`.

    This opens the init TUI when no manifest exists and the manage dashboard
    when `.grove/manifest.toml` is already present.

    Args:
        root: Project root directory (default: current directory).
    """
    try:
        root = _resolve_root(root)
    except (GroveError, ValueError, KeyError) as e:
        _exit_with_error(str(e))
    if not sys.stdout.isatty():
        _exit_with_error(
            "Manage is interactive; run in a terminal, or use "
            "'grove add'/'grove sync' for non-interactive maintenance."
        )
    _run_configure(root)


def main() -> None:
    """Entry point for the grove console script."""
    app()


if __name__ == "__main__":
    main()
