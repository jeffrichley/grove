"""Shared state for the grove init TUI flow."""

from pathlib import Path

from pydantic import BaseModel, Field

from grove.core.manifest import load_manifest
from grove.core.models import InstallPlan, ManifestState, ProjectProfile


class SetupState(BaseModel):
    """State shared across TUI screens during grove init.

    Populated progressively: root first, then profile, selected packs,
    config answers, then install_plan and manifest before apply.
    """

    root: Path = Field(
        default_factory=Path.cwd,
        description="Project root directory (repo root).",
    )
    install_root: Path = Field(
        default_factory=lambda: Path(".grove"),
        description="Install root relative to root (e.g. .grove).",
    )
    core_include_adrs: bool = Field(
        default=True,
        description="Include ADRs (decisions) in base install.",
    )
    core_include_handoffs: bool = Field(
        default=True,
        description="Include handoffs in base install.",
    )
    core_include_scoped_rules: bool = Field(
        default=True,
        description="Include scoped rules in base install.",
    )
    core_include_memory: bool = Field(
        default=True,
        description="Include memory/preferences in base install.",
    )
    core_include_skills_dir: bool = Field(
        default=True,
        description="Include skills directory in base install.",
    )
    profile: ProjectProfile | None = Field(
        default=None,
        description="Result of repo analysis; set after analysis screen.",
    )
    selected_pack_ids: list[str] = Field(
        default_factory=list,
        description="Pack ids to install (e.g. base, python).",
    )
    config_answers: dict[str, object] = Field(
        default_factory=dict,
        description="Answers to pack setup_questions (id -> value).",
    )
    install_plan: InstallPlan | None = Field(
        default=None,
        description="Computed install plan; set before preview.",
    )
    conflict_choices: dict[str, str] = Field(
        default_factory=dict,
        description="Per-path conflict resolution: overwrite | skip | rename.",
    )
    manifest: ManifestState | None = Field(
        default=None,
        description="Manifest to write after apply; set before final review.",
    )

    model_config = {"arbitrary_types_allowed": True}


def setup_state_from_manifest(
    manifest_path: Path,
    default_root: Path,
) -> SetupState:
    """Build SetupState from .grove/manifest.toml when re-running init.

    Prefills install_root, selected_pack_ids (from installed packs), and
    core options from [init] provenance so Core install and Recommended
    packs screens show previous choices.

    Args:
        manifest_path: Path to .grove/manifest.toml.
        default_root: Root to use if manifest cannot be loaded.

    Returns:
        SetupState with root, install_root, selected_pack_ids, and core_*
        from manifest when present; otherwise defaults for default_root.
    """
    if not manifest_path.exists():
        return SetupState(
            root=default_root,
            install_root=default_root / ".grove",
        )
    try:
        manifest = load_manifest(manifest_path)
    except (ValueError, OSError):
        return SetupState(
            root=default_root,
            install_root=default_root / ".grove",
        )
    root = Path(manifest.project.root).resolve()
    prov = manifest.init_provenance
    if prov is not None:
        install_root_raw = Path(prov.install_root)
        install_root = (
            (root / install_root_raw).resolve()
            if not install_root_raw.is_absolute()
            else install_root_raw
        )
        return SetupState(
            root=root,
            install_root=install_root,
            selected_pack_ids=[p.id for p in manifest.installed_packs],
            core_include_adrs=prov.core_include_adrs,
            core_include_handoffs=prov.core_include_handoffs,
            core_include_scoped_rules=prov.core_include_scoped_rules,
            core_include_memory=prov.core_include_memory,
            core_include_skills_dir=prov.core_include_skills_dir,
            manifest=manifest,
        )
    return SetupState(
        root=root,
        install_root=root / ".grove",
        selected_pack_ids=[p.id for p in manifest.installed_packs],
        manifest=manifest,
    )
