"""Pydantic models for Grove CLI: profile, pack manifest, install plan, manifest."""

from pathlib import Path

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Pack manifest (from pack.yaml / pack.toml)
# ---------------------------------------------------------------------------


class PackManifest(BaseModel):
    """Metadata for a capability pack (from pack.yaml or pack.toml)."""

    id: str = Field(..., description="Unique pack identifier (e.g. 'base', 'python').")
    name: str = Field(..., description="Human-readable pack name.")
    version: str = Field(..., description="Pack version (e.g. '0.1.0').")
    depends_on: list[str] = Field(
        default_factory=list, description="Pack IDs this pack depends on."
    )
    compatible_with: list[str] = Field(
        default_factory=list,
        description="Compatibility tags (e.g. language, tool) for filtering.",
    )
    activates_when: list[str] = Field(
        default_factory=list,
        description="Conditions that auto-activate this pack (e.g. file patterns).",
    )
    contributes: dict[str, object] = Field(
        default_factory=dict,
        description="Templates, rules, setup_questions; structure defined per pack.",
    )
    root_dir: Path | None = Field(
        default=None,
        description="Absolute pack root on disk for template resolution.",
    )


class InjectionSpec(BaseModel):
    """One anchored snippet contribution from a pack."""

    pack_id: str = Field(..., description="Pack that owns this injection.")
    id: str = Field(..., description="Unique injection id across selected packs.")
    target: str | None = Field(
        default=None,
        description="Optional target file relative to install root (e.g. 'GROVE.md').",
    )
    anchor: str = Field(..., description="Anchor name inside the target file.")
    source: Path | None = Field(
        default=None,
        description=(
            "Optional source template path relative to the contributing pack root."
        ),
    )
    content: str | None = Field(
        default=None,
        description="Optional inline template content for the injection.",
    )
    order: int = Field(default=0, description="Deterministic ordering key.")


class ToolHookSpec(BaseModel):
    """One pack-owned tool integration output."""

    pack_id: str = Field(..., description="Pack that owns this tool hook.")
    id: str = Field(..., description="Unique hook id across selected packs.")
    tool: str = Field(..., description="External tool id (e.g. 'codex').")
    hook_type: str = Field(
        ...,
        description="Write/update strategy used to apply this hook.",
    )
    target: Path = Field(
        ...,
        description="Target path relative to the project root unless absolute.",
    )
    source: Path | None = Field(
        default=None,
        description="Optional source template path relative to the contributing pack.",
    )
    content: str | None = Field(
        default=None,
        description="Optional inline template content for the hook body.",
    )
    order: int = Field(default=0, description="Deterministic ordering key.")


# ---------------------------------------------------------------------------
# Project profile (from analyzer)
# ---------------------------------------------------------------------------


class ProjectProfile(BaseModel):
    """Result of repo analysis: language, tools, package manager, etc."""

    project_name: str = Field(
        default="", description="Project name from pyproject or directory."
    )
    project_root: Path = Field(
        default_factory=Path, description="Absolute path to project root."
    )
    language: str = Field(default="", description="Primary language (e.g. 'python').")
    package_manager: str = Field(
        default="", description="Package manager (e.g. 'uv', 'pip')."
    )
    test_framework: str = Field(
        default="", description="Test framework (e.g. 'pytest')."
    )
    tools: list[str] = Field(
        default_factory=list, description="Detected tools (ruff, mypy, etc.)."
    )
    raw: dict[str, object] = Field(
        default_factory=dict,
        description="Extra detector output for template variables.",
    )


# ---------------------------------------------------------------------------
# Install plan (from composer)
# ---------------------------------------------------------------------------


class PlannedFile(BaseModel):
    """A single file to be generated in an install plan."""

    pack_id: str = Field(
        default="",
        description="Pack that contributes this file (for resolving src to template).",
    )
    src: Path = Field(..., description="Source template path (relative to pack root).")
    dst: Path = Field(..., description="Destination path (relative to install root).")
    variables: dict[str, object] = Field(
        default_factory=dict, description="Variables for rendering."
    )
    managed: bool = Field(
        default=True,
        description="Whether this file is managed by Grove (overwrite/sync).",
    )
    rendered_content: str | None = Field(
        default=None,
        description="Pre-rendered output for composition-aware files.",
    )


class InstallPlan(BaseModel):
    """Ordered list of files to generate and variables to use."""

    install_root: Path = Field(
        ..., description="Root directory for installation (e.g. .grove)."
    )
    files: list[PlannedFile] = Field(
        default_factory=list, description="Files to create or update."
    )


# ---------------------------------------------------------------------------
# Manifest state (manifest.toml shape)
# Schema version: 1. Documented here and in manifest.py.
# ---------------------------------------------------------------------------


class GroveSection(BaseModel):
    """[grove] section of manifest.toml."""

    version: str = Field(..., description="Grove CLI version that wrote this manifest.")
    schema_version: int = Field(
        default=1, description="Manifest schema version for migrations."
    )


class ProjectSection(BaseModel):
    """[project] section of manifest.toml."""

    root: str = Field(..., description="Project root path (as string for TOML).")
    analysis_summary: str = Field(
        default="", description="Brief summary of last analysis (optional)."
    )


class InstalledPackRecord(BaseModel):
    """One installed pack entry in [packs] or equivalent."""

    id: str = Field(..., description="Pack id.")
    version: str = Field(default="", description="Pack version when installed.")


class GeneratedFileRecord(BaseModel):
    """One entry in [[generated_files]]."""

    path: str = Field(..., description="Path relative to install root.")
    pack_id: str = Field(default="", description="Pack that generated this file.")


class InitProvenance(BaseModel):
    """Optional [init] section: last init choices for re-run / TUI prefill.

    Stored in .grove/manifest.toml so we can query what was selected previously
    and pre-select Core install and Recommended packs when re-running init.
    """

    install_root: str = Field(
        default=".grove",
        description="Install root path (relative or absolute) as stored.",
    )
    core_include_adrs: bool = Field(default=True, description="ADRs included.")
    core_include_handoffs: bool = Field(default=True, description="Handoffs included.")
    core_include_scoped_rules: bool = Field(
        default=True, description="Scoped rules included."
    )
    core_include_memory: bool = Field(default=True, description="Memory included.")
    core_include_skills_dir: bool = Field(
        default=True, description="Skills directory included."
    )


class ManifestState(BaseModel):
    """In-memory shape of .grove/manifest.toml.

    Schema version 1. Sections: [grove], [project], [packs], [[generated_files]],
    and optional [init] for provenance (TUI prefill).
    """

    grove: GroveSection = Field(..., description="Grove version and schema version.")
    project: ProjectSection = Field(
        ..., description="Project root and analysis summary."
    )
    installed_packs: list[InstalledPackRecord] = Field(
        default_factory=list,
        alias="packs",
        description="Installed packs (serialized as 'packs' in TOML).",
    )
    generated_files: list[GeneratedFileRecord] = Field(
        default_factory=list,
        description="List of generated file paths and their pack.",
    )
    init_provenance: InitProvenance | None = Field(
        default=None,
        description="Optional [init] section: last init choices for TUI prefill.",
    )

    model_config = {"populate_by_name": True}
