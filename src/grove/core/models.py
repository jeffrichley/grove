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


class InjectionProvenance(BaseModel):
    """Structured provenance for one anchored contribution."""

    pack_id: str = Field(..., description="Pack that owns the contribution.")
    injection_id: str = Field(..., description="Injection identifier within the pack.")
    anchor: str = Field(..., description="Anchor name the injection targets.")
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


class CodexSkillSpec(BaseModel):
    """One pack-owned Codex skill materialization output."""

    pack_id: str = Field(..., description="Pack that owns this Codex skill.")
    id: str = Field(..., description="Unique skill id across selected packs.")
    path: Path = Field(
        ...,
        description="Destination folder path relative to repo-local `.agents/skills`.",
    )
    source: Path | None = Field(
        default=None,
        description="Optional source template path relative to the contributing pack.",
    )
    content: str | None = Field(
        default=None,
        description="Optional inline template content for the skill body.",
    )
    order: int = Field(default=0, description="Deterministic ordering key.")


class ToolHookOutputRecord(BaseModel):
    """One materialized tool-native output owned by a selected pack."""

    pack_id: str = Field(..., description="Pack that owns this tool-native output.")
    hook_id: str = Field(..., description="Hook identifier within the owning pack.")
    tool: str = Field(..., description="External tool id (e.g. 'codex').")
    hook_type: str = Field(..., description="Write/update strategy for the output.")
    path: str = Field(..., description="Target path relative to the project root.")


class CodexSkillOutputRecord(BaseModel):
    """One materialized repo-local Codex skill owned by a selected pack."""

    pack_id: str = Field(..., description="Pack that owns this materialized skill.")
    skill_id: str = Field(..., description="Skill identifier within the owning pack.")
    path: str = Field(
        ...,
        description="Target path relative to the project root for `SKILL.md`.",
    )


class DoctorCheckSpec(BaseModel):
    """One pack-owned doctor check contribution."""

    pack_id: str = Field(..., description="Pack that owns this doctor check.")
    id: str = Field(..., description="Unique doctor check id across selected packs.")
    check_type: str = Field(
        ...,
        description="Generic doctor check kind executed by the doctor engine.",
    )
    description: str = Field(
        default="",
        description="Short human-readable summary of what this check verifies.",
    )
    target: Path | None = Field(
        default=None,
        description="Optional project-relative target path inspected by the check.",
    )
    tool: str | None = Field(
        default=None,
        description="Optional external tool id associated with the check.",
    )
    skill_path: Path | None = Field(
        default=None,
        description="Optional repo-local skill directory associated with the check.",
    )
    required_front_matter: list[str] = Field(
        default_factory=list,
        description="Required front-matter keys for semantic output validation.",
    )
    order: int = Field(default=0, description="Deterministic ordering key.")


class DoctorIssue(BaseModel):
    """One issue detected during `grove doctor`."""

    code: str = Field(..., description="Stable issue code.")
    severity: str = Field(
        ...,
        description="Issue severity (e.g. info, warning, error).",
    )
    message: str = Field(..., description="Human-readable issue summary.")
    path: str | None = Field(
        default=None,
        description="Optional project-relative path associated with the issue.",
    )
    pack_id: str | None = Field(
        default=None,
        description="Optional pack id associated with the issue.",
    )
    check_id: str | None = Field(
        default=None,
        description="Optional doctor check id that produced the issue.",
    )


class DoctorReport(BaseModel):
    """Structured report returned by the future doctor engine."""

    healthy: bool = Field(
        default=True,
        description="True when no warning/error issues were detected.",
    )
    summary: str = Field(
        default="",
        description="Short human-readable summary of the installation state.",
    )
    issues: list[DoctorIssue] = Field(
        default_factory=list,
        description="Ordered issues detected during the doctor run.",
    )


class ToolHookTargetState(BaseModel):
    """Desired tool-hook target state for a selected pack set."""

    path: str = Field(..., description="Project-root-relative tool target path.")
    hook_type: str = Field(..., description="Shared hook type for this target path.")
    tools: list[str] = Field(
        default_factory=list,
        description="Ordered tool ids aligned with the contributing hook ids.",
    )
    hook_ids: list[str] = Field(
        default_factory=list,
        description="Ordered hook ids that contribute to this target path.",
    )
    pack_ids: list[str] = Field(
        default_factory=list,
        description="Ordered pack ids that contribute hooks to this path.",
    )
    rendered_blocks: list[str] = Field(
        default_factory=list,
        description="Rendered managed blocks in deterministic hook order.",
    )


class CodexSkillTargetState(BaseModel):
    """Desired repo-local Codex skill state for a selected pack set."""

    path: str = Field(..., description="Project-root-relative `SKILL.md` path.")
    skill_id: str = Field(..., description="Owning skill contribution id.")
    pack_id: str = Field(..., description="Pack that owns the skill contribution.")
    rendered_content: str = Field(
        ...,
        description="Rendered skill file body including the trailing newline.",
    )


class RemovePathPlan(BaseModel):
    """Planned action for one path during `grove remove`."""

    path: str = Field(..., description="Project-root-relative path to classify.")
    action: str = Field(
        ...,
        description="Planned action: delete, rewrite, or preserve.",
    )
    surface: str = Field(
        ...,
        description=(
            "Ownership surface: managed_file, tool_hook, or pack_local_skill."
        ),
    )
    reason: str = Field(..., description="Human-readable reason for the action.")
    pack_ids: list[str] = Field(
        default_factory=list,
        description="Packs that currently contribute to this path.",
    )
    anchors: list[str] = Field(
        default_factory=list,
        description="Affected anchors for managed file rewrites, when known.",
    )


class RemovePlan(BaseModel):
    """Non-mutating remove plan computed before filesystem changes."""

    target_pack_id: str = Field(..., description="Pack requested for removal.")
    remaining_pack_ids: list[str] = Field(
        default_factory=list,
        description="Installed pack ids that remain after removal.",
    )
    changes: list[RemovePathPlan] = Field(
        default_factory=list,
        description="Ordered path actions that remove would apply or preserve.",
    )


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
    anchor_provenance: dict[str, list[InjectionProvenance]] = Field(
        default_factory=dict,
        description="Per-anchor provenance for composed injection content.",
    )


class InstallPlan(BaseModel):
    """Ordered list of files to generate and variables to use."""

    install_root: Path = Field(
        ..., description="Root directory for installation (e.g. .grove)."
    )
    files: list[PlannedFile] = Field(
        default_factory=list, description="Files to create or update."
    )


class AnchorSyncChange(BaseModel):
    """One changed anchor reported by sync dry-run."""

    anchor: str = Field(..., description="Anchor whose body would be rewritten.")
    provenance: list[InjectionProvenance] = Field(
        default_factory=list,
        description="Ordered provenance entries that own the desired anchor body.",
    )


class SyncFileChange(BaseModel):
    """One file that sync would update or did update."""

    path: str = Field(..., description="Path relative to the project root.")
    anchors: list[AnchorSyncChange] = Field(
        default_factory=list,
        description="Changed anchors for composed files; empty for whole-file writes.",
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
