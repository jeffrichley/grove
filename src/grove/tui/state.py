"""Shared state for the grove init TUI flow."""

from pathlib import Path

from pydantic import BaseModel, Field

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
    manifest: ManifestState | None = Field(
        default=None,
        description="Manifest to write after apply; set before final review.",
    )

    model_config = {"arbitrary_types_allowed": True}
