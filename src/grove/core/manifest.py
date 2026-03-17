"""Load and save .grove/manifest.toml with versioned schema."""

import tomllib
from pathlib import Path

import tomli_w

from grove.core.models import (
    GeneratedFileRecord,
    GroveSection,
    InitProvenance,
    InstalledPackRecord,
    ManifestState,
    ProjectSection,
)

# Schema version for manifest.toml; bump when breaking compatibility.
MANIFEST_SCHEMA_VERSION = 1


def _parse_grove_section(data: dict[str, object]) -> GroveSection:
    """Extract and validate [grove] section.

    Args:
        data: Raw TOML data (dict from tomllib.load).

    Returns:
        Validated GroveSection.

    Raises:
        ValueError: If [grove] missing or schema version unsupported.
    """
    grove_data = data.get("grove")
    if not grove_data or not isinstance(grove_data, dict):
        raise ValueError(
            "Manifest must contain [grove] section with version and schema_version"
        )
    schema_version = grove_data.get("schema_version", 1)
    if schema_version != MANIFEST_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported manifest schema version {schema_version}; "
            f"expected {MANIFEST_SCHEMA_VERSION}"
        )
    return GroveSection(
        version=str(grove_data.get("version", "")),
        schema_version=int(grove_data.get("schema_version", 1)),
    )


def _parse_project_section(data: dict[str, object]) -> ProjectSection:
    """Extract and validate [project] section.

    Args:
        data: Raw TOML data (dict from tomllib.load).

    Returns:
        Validated ProjectSection.

    Raises:
        ValueError: If [project] section missing or invalid.
    """
    project_data = data.get("project")
    if not project_data or not isinstance(project_data, dict):
        raise ValueError("Manifest must contain [project] section with root")
    return ProjectSection(
        root=str(project_data.get("root", "")),
        analysis_summary=str(project_data.get("analysis_summary", "")),
    )


def _parse_packs(data: dict[str, object]) -> list[InstalledPackRecord]:
    """Extract [packs] list.

    Args:
        data: Raw TOML data (dict from tomllib.load).

    Returns:
        List of InstalledPackRecord; empty if missing or not a list.
    """
    packs_data = data.get("packs", [])
    if not isinstance(packs_data, list):
        packs_data = []
    return [
        InstalledPackRecord(id=item.get("id", ""), version=str(item.get("version", "")))
        for item in packs_data
        if isinstance(item, dict) and item.get("id")
    ]


def _parse_init_section(data: dict[str, object]) -> InitProvenance | None:
    """Extract optional [init] section for provenance (TUI prefill).

    Args:
        data: Raw TOML data.

    Returns:
        InitProvenance if [init] present and valid, else None.
    """
    init_data = data.get("init")
    if not init_data or not isinstance(init_data, dict):
        return None
    return InitProvenance(
        install_root=str(init_data.get("install_root", ".grove")),
        core_include_adrs=bool(init_data.get("core_include_adrs", True)),
        core_include_handoffs=bool(init_data.get("core_include_handoffs", True)),
        core_include_scoped_rules=bool(
            init_data.get("core_include_scoped_rules", True)
        ),
        core_include_memory=bool(init_data.get("core_include_memory", True)),
        core_include_skills_dir=bool(init_data.get("core_include_skills_dir", True)),
    )


def _parse_generated_files(data: dict[str, object]) -> list[GeneratedFileRecord]:
    """Extract [[generated_files]] list.

    Args:
        data: Raw TOML data (dict from tomllib.load).

    Returns:
        List of GeneratedFileRecord; empty if missing or not a list.
    """
    generated_data = data.get("generated_files", [])
    if not isinstance(generated_data, list):
        generated_data = []
    return [
        GeneratedFileRecord(
            path=str(item.get("path", "")),
            pack_id=str(item.get("pack_id", "")),
        )
        for item in generated_data
        if isinstance(item, dict) and item.get("path")
    ]


def load_manifest(path: Path) -> ManifestState:
    """Load manifest from a TOML file.

    Args:
        path: Path to manifest.toml.

    Returns:
        Validated ManifestState.

    Raises:
        FileNotFoundError: If path does not exist.
        ValueError: If content is invalid or schema version is unsupported.
    """
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found: {path}")

    with path.open("rb") as f:
        data = tomllib.load(f)

    if not isinstance(data, dict):
        raise ValueError("Manifest file must be a TOML table")

    grove = _parse_grove_section(data)
    project = _parse_project_section(data)
    installed_packs = _parse_packs(data)
    generated_files = _parse_generated_files(data)
    init_provenance = _parse_init_section(data)

    return ManifestState(
        grove=grove,
        project=project,
        packs=installed_packs,
        generated_files=generated_files,
        init_provenance=init_provenance,
    )


def save_manifest(path: Path, state: ManifestState) -> None:
    """Write ManifestState to a TOML file.

    Args:
        path: Path to manifest.toml (parent directory must exist).
        state: Validated ManifestState to serialize.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    # Build dict for TOML: [grove], [project], [packs], [[generated_files]], [init]
    data: dict[str, object] = {
        "grove": {
            "version": state.grove.version,
            "schema_version": state.grove.schema_version,
        },
        "project": {
            "root": state.project.root,
            "analysis_summary": state.project.analysis_summary,
        },
        "packs": [{"id": p.id, "version": p.version} for p in state.installed_packs],
        "generated_files": [
            {"path": g.path, "pack_id": g.pack_id} for g in state.generated_files
        ],
    }
    if state.init_provenance is not None:
        prov = state.init_provenance
        data["init"] = {
            "install_root": prov.install_root,
            "core_include_adrs": prov.core_include_adrs,
            "core_include_handoffs": prov.core_include_handoffs,
            "core_include_scoped_rules": prov.core_include_scoped_rules,
            "core_include_memory": prov.core_include_memory,
            "core_include_skills_dir": prov.core_include_skills_dir,
        }

    with path.open("wb") as f:
        tomli_w.dump(data, f)
