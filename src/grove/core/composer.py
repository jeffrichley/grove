"""Composer: compute InstallPlan from profile, selected pack ids, and registry."""

from pathlib import Path

from grove.core.injections import RenderedInjection, assemble_injections
from grove.core.markers import find_anchor_ranges
from grove.core.models import (
    InjectionProvenance,
    InjectionSpec,
    InstallPlan,
    PackManifest,
    PlannedFile,
    ProjectProfile,
)
from grove.core.renderer import render, render_string


def compose(
    profile: ProjectProfile,
    selected_pack_ids: list[str],
    install_root: Path,
    packs: list[PackManifest],
) -> InstallPlan:
    """Build an install plan from profile, selected pack ids, and available packs.

    Args:
        profile: Project analysis result used to build template variables.
        selected_pack_ids: Pack ids selected for this install.
        install_root: Root directory where Grove files will be installed.
        packs: Available pack manifests in dependency order.

    Returns:
        Install plan with whole-file and composition-aware outputs.
    """
    install_root = install_root.resolve()
    packs_by_id = {p.id: p for p in packs}
    for pid in selected_pack_ids:
        if pid not in packs_by_id:
            raise ValueError(
                f"Pack id '{pid}' is not available; "
                f"available packs: {sorted(packs_by_id.keys())}"
            )

    variables = _variables_from_profile(profile)
    files, injections = _collect_pack_contributions(
        packs,
        selected_pack_ids,
        install_root,
        variables,
    )
    matched_injection_ids: set[str] = set()
    composed_files = [
        _compose_file(
            planned,
            install_root,
            injections,
            packs_by_id,
            matched_injection_ids,
        )
        for planned in files
    ]
    _validate_injection_matches(
        injections,
        matched_injection_ids,
        composed_files,
        install_root,
    )
    return InstallPlan(install_root=install_root, files=composed_files)


def _collect_pack_contributions(
    packs: list[PackManifest],
    selected_pack_ids: list[str],
    install_root: Path,
    variables: dict[str, object],
) -> tuple[list[PlannedFile], list[InjectionSpec]]:
    """Collect template files and injections for selected packs.

    Args:
        packs: Available pack manifests in dependency order.
        selected_pack_ids: Pack ids selected for this install.
        install_root: Root directory where Grove files will be installed.
        variables: Shared template variables from the project profile.

    Returns:
        Planned files and parsed injection specs for the selected packs.
    """
    files: list[PlannedFile] = []
    injections: list[InjectionSpec] = []
    seen_injection_ids: set[str] = set()

    for pack in packs:
        if pack.id not in selected_pack_ids:
            continue
        files.extend(_planned_files_for_pack(pack, install_root, variables))
        for injection in _injections_from_contributes(pack):
            if injection.id in seen_injection_ids:
                raise ValueError(f"Duplicate injection id: {injection.id}")
            seen_injection_ids.add(injection.id)
            injections.append(injection)
    return files, injections


def _planned_files_for_pack(
    pack: PackManifest,
    install_root: Path,
    variables: dict[str, object],
) -> list[PlannedFile]:
    """Build planned files for one pack's template contributions.

    Args:
        pack: Pack manifest to inspect.
        install_root: Root directory where Grove files will be installed.
        variables: Shared template variables from the project profile.

    Returns:
        Planned files for the pack's template contributions.
    """
    return [
        PlannedFile(
            pack_id=pack.id,
            src=Path(template_rel),
            dst=_dst_path(install_root, template_rel),
            variables=dict(variables),
            managed=True,
        )
        for template_rel in _template_paths_from_contributes(pack.contributes)
    ]


def _compose_file(
    planned: PlannedFile,
    install_root: Path,
    injections: list[InjectionSpec],
    packs_by_id: dict[str, PackManifest],
    matched_injection_ids: set[str],
) -> PlannedFile:
    """Return a planned file, precomposed when injections match its anchors.

    Args:
        planned: Candidate planned file from template contributions.
        install_root: Root directory for installed Grove files.
        injections: Injection specs available to the file.
        packs_by_id: Pack manifests keyed by pack id.
        matched_injection_ids: Injection ids matched to at least one file.

    Returns:
        Original planned file or a copy with rendered composed content.
    """
    target = planned.dst.relative_to(install_root).as_posix()
    pack = packs_by_id.get(planned.pack_id)
    if pack is None or pack.root_dir is None:
        raise ValueError(f"Pack root is unavailable for '{planned.pack_id}'")
    base_content = render((pack.root_dir / planned.src).resolve(), planned.variables)
    anchor_names = set(find_anchor_ranges(base_content))
    applicable = [
        injection
        for injection in injections
        if _injection_matches_file(injection, target, anchor_names)
    ]
    if not applicable:
        return planned

    matched_injection_ids.update(injection.id for injection in applicable)
    rendered_injections = _render_injections(
        applicable,
        planned.variables,
        packs_by_id,
    )
    return planned.model_copy(
        update={
            "rendered_content": assemble_injections(base_content, rendered_injections),
            "anchor_provenance": _build_anchor_provenance(applicable),
        }
    )


def _render_injections(
    injections: list[InjectionSpec],
    variables: dict[str, object],
    packs_by_id: dict[str, PackManifest],
) -> list[RenderedInjection]:
    """Render injection payloads for one output file.

    Args:
        injections: Injection specs applicable to one output file.
        variables: Shared template variables from the project profile.
        packs_by_id: Pack manifests keyed by pack id.

    Returns:
        Rendered injections ready for anchor assembly.
    """
    return [
        RenderedInjection(
            id=spec.id,
            anchor=spec.anchor,
            order=spec.order,
            content=_render_injection_content(spec, variables, packs_by_id),
        )
        for spec in injections
    ]


def _build_anchor_provenance(
    injections: list[InjectionSpec],
) -> dict[str, list[InjectionProvenance]]:
    """Build ordered provenance entries for each anchor in one planned file.

    Provenance is derived from injection specs during composition so sync can
    report ownership of changed anchor bodies without scraping rendered output.

    Args:
        injections: Injection specs applicable to one output file.

    Returns:
        Provenance entries keyed by anchor name, ordered by injection order and id.
    """
    provenance: dict[str, list[InjectionProvenance]] = {}
    for spec in sorted(injections, key=lambda item: (item.order, item.id)):
        provenance.setdefault(spec.anchor, []).append(
            InjectionProvenance(
                pack_id=spec.pack_id,
                injection_id=spec.id,
                anchor=spec.anchor,
                order=spec.order,
            )
        )
    return provenance


def _validate_injection_matches(
    injections: list[InjectionSpec],
    matched_injection_ids: set[str],
    files: list[PlannedFile],
    install_root: Path,
) -> None:
    """Fail when injections do not match any selected file and anchor.

    Args:
        injections: Parsed injection specs for the selected packs.
        matched_injection_ids: Injection ids that matched at least one file.
        files: Planned files produced by compose.
        install_root: Root directory for installed Grove files.
    """
    targets = {planned.dst.relative_to(install_root).as_posix() for planned in files}
    missing_targets = sorted(
        injection.target
        for injection in injections
        if injection.target is not None and injection.target not in targets
    )
    if missing_targets:
        raise ValueError(
            "Injection target file(s) missing from install plan: "
            + ", ".join(missing_targets)
        )
    unmatched = sorted(
        injection.id
        for injection in injections
        if injection.id not in matched_injection_ids
    )
    if unmatched:
        raise ValueError(
            "Injection anchor(s) did not match any selected file: "
            + ", ".join(unmatched)
        )


def _variables_from_profile(profile: ProjectProfile) -> dict[str, object]:
    """Build template variables from profile (and raw).

    Args:
        profile: Project analysis result.

    Returns:
        Template variables derived from the profile.
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
        contributes: Pack contribution data.

    Returns:
        Normalized template path strings.
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

    Args:
        install_root: Root directory for installed Grove files.
        template_rel: Template path relative to a pack root.

    Returns:
        Destination path with any trailing `.j2` removed.
    """
    path_str = template_rel.replace("\\", "/")
    if path_str.endswith(".j2"):
        path_str = path_str[:-3]
    return install_root / path_str


def _injections_from_contributes(pack: PackManifest) -> list[InjectionSpec]:
    """Parse injection specs from pack contributes.

    Args:
        pack: Pack manifest to inspect.

    Returns:
        Parsed injection specs for the pack.
    """
    raw = pack.contributes.get("injections")
    if not isinstance(raw, list):
        return []

    specs: list[InjectionSpec] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        specs.append(
            InjectionSpec(
                pack_id=pack.id,
                id=str(item["id"]),
                target=str(item["target"]) if "target" in item else None,
                anchor=str(item["anchor"]),
                source=Path(str(item["source"])) if "source" in item else None,
                content=str(item["content"]) if "content" in item else None,
                order=int(item.get("order", 0)),
            )
        )
    return specs


def _render_injection_content(
    spec: InjectionSpec,
    variables: dict[str, object],
    packs_by_id: dict[str, PackManifest],
) -> str:
    """Render one injection payload from either source or inline content.

    Args:
        spec: Injection spec to render.
        variables: Shared template variables from the project profile.
        packs_by_id: Pack manifests keyed by pack id.

    Returns:
        Rendered injection content.

    Raises:
        ValueError: The injection payload definition is invalid.
    """
    has_source = spec.source is not None
    has_content = spec.content is not None
    if has_source == has_content:
        raise ValueError(
            f"Injection '{spec.id}' must define exactly one of 'source' or 'content'"
        )
    if spec.content is not None:
        return render_string(spec.content, variables)
    pack = packs_by_id.get(spec.pack_id)
    if pack is None or pack.root_dir is None or spec.source is None:
        raise ValueError(f"Pack root is unavailable for injection '{spec.id}'")
    return render((pack.root_dir / spec.source).resolve(), variables)


def _injection_matches_file(
    injection: InjectionSpec,
    target: str,
    anchor_names: set[str],
) -> bool:
    """Return whether an injection applies to one planned file.

    Args:
        injection: Injection spec to evaluate.
        target: File path relative to the install root.
        anchor_names: Anchors exposed by the rendered base file.

    Returns:
        True when the injection should be applied to the file.
    """
    if injection.target is not None and injection.target != target:
        return False
    return injection.anchor in anchor_names
