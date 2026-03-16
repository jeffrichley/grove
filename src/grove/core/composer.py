"""Composer: compute InstallPlan from profile, selected pack ids, and registry.

No file I/O; no TUI. Takes ProjectProfile, list of pack ids, install root path,
and the list of available packs (from registry); returns an InstallPlan with
PlannedFiles (src, dst, variables, managed). Template specs come from each
pack's contributes.templates (paths relative to pack root). Compatibility:
we include all selected packs; when profile does not match a pack's
compatible_with/activates_when, we include the pack anyway and do not surface
warnings in this phase (warnings may be added in a later iteration).
"""

from pathlib import Path

from grove.core.models import (
    InstallPlan,
    PackManifest,
    PlannedFile,
    ProjectProfile,
)


def compose(
    profile: ProjectProfile,
    selected_pack_ids: list[str],
    install_root: Path,
    packs: list[PackManifest],
) -> InstallPlan:
    """Build an install plan from profile, selected pack ids, and available packs.

    Args:
        profile: Result of repo analysis (project_name, language, tools, etc.).
        selected_pack_ids: Pack ids to include (e.g. ["base", "python"]).
        install_root: Root directory for installation (e.g. .grove).
        packs: All available packs in dependency order (e.g. from discover_packs()).

    Returns:
        InstallPlan with install_root and files (PlannedFile per template).

    Raises:
        ValueError: A selected pack id is not in the available packs list.
    """
    install_root = install_root.resolve()
    by_id = {p.id: p for p in packs}
    for pid in selected_pack_ids:
        if pid not in by_id:
            raise ValueError(
                f"Pack id '{pid}' is not available; "
                f"available packs: {sorted(by_id.keys())}"
            )

    variables = _variables_from_profile(profile)
    files: list[PlannedFile] = []
    for pack in packs:
        if pack.id not in selected_pack_ids:
            continue
        for template_rel in _template_paths_from_contributes(pack.contributes):
            src = Path(template_rel)
            dst = _dst_path(install_root, template_rel)
            files.append(
                PlannedFile(
                    pack_id=pack.id,
                    src=src,
                    dst=dst,
                    variables=dict(variables),
                    managed=True,
                )
            )

    return InstallPlan(install_root=install_root, files=files)


def _variables_from_profile(profile: ProjectProfile) -> dict[str, object]:
    """Build template variables from profile (and raw).

    Args:
        profile: Analyzer result with project_name, language, tools, etc.

    Returns:
        Dict suitable for template rendering (includes raw if present).
    """
    out: dict[str, object] = {
        "project_name": profile.project_name,
        "language": profile.language,
        "package_manager": profile.package_manager,
        "test_framework": profile.test_framework,
        "tools": profile.tools,
    }
    if profile.raw:
        out["raw"] = profile.raw
    return out


def _template_paths_from_contributes(contributes: dict[str, object]) -> list[str]:
    """Return list of template path strings from contributes.templates.

    Args:
        contributes: Pack contributes dict (e.g. from PackManifest.contributes).

    Returns:
        Non-empty trimmed path strings; empty list if missing or not a list.
    """
    templates = contributes.get("templates")
    if templates is None:
        return []
    if not isinstance(templates, list):
        return []
    return [
        item.strip() for item in templates if isinstance(item, str) and item.strip()
    ]


def _dst_path(install_root: Path, template_rel: str) -> Path:
    """Destination path under install_root for a template path.

    Template paths are relative to pack root (e.g. "GROVE.md.j2").
    We strip a trailing .j2 so the generated file has the final name.

    Args:
        install_root: Root directory for installation (e.g. .grove).
        template_rel: Template path relative to pack root (e.g. "rules/python.md.j2").

    Returns:
        Path under install_root for the generated file (e.g. rules/python.md).
    """
    p = template_rel.replace("\\", "/")
    if p.endswith(".j2"):
        p = p[:-3]
    return install_root / p
