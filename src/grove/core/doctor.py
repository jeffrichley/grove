"""Top-level read-only diagnostics for `grove doctor`."""

from pathlib import Path

from grove.analyzer import analyze
from grove.core.doctor_checks import (
    build_doctor_context,
    check_managed_outputs,
    check_manifest_load,
    check_pack_coherence,
    check_pack_doctor_specs,
    check_tool_outputs,
)
from grove.core.manifest import load_manifest
from grove.core.models import DoctorIssue, DoctorReport
from grove.core.registry import get_builtin_pack_roots_and_packs


def run_doctor(root: Path) -> DoctorReport:
    """Run generic read-only diagnostics for one Grove installation.

    Args:
        root: Project root that owns `.grove/manifest.toml`.

    Returns:
        Structured doctor report covering generic installation health.
    """
    manifest_issues = check_manifest_load(root)
    if manifest_issues:
        return _build_report(manifest_issues)

    manifest = load_manifest(root / ".grove" / "manifest.toml")
    pack_roots, packs = get_builtin_pack_roots_and_packs()
    context = build_doctor_context(
        root,
        manifest,
        pack_roots,
        analyze(root),
        packs,
    )
    issues: list[DoctorIssue] = []
    issues.extend(check_pack_coherence(manifest, packs))
    issues.extend(check_managed_outputs(context))
    issues.extend(check_tool_outputs(context))
    issues.extend(check_pack_doctor_specs(context))
    return _build_report(issues)


def _build_report(issues: list[DoctorIssue]) -> DoctorReport:
    """Return a normalized doctor report from collected issues.

    Args:
        issues: Collected doctor issues in any order.

    Returns:
        Normalized doctor report with health and summary fields populated.
    """
    ordered = sorted(
        issues,
        key=lambda item: (item.severity, item.path or "", item.code),
    )
    error_count = sum(1 for issue in ordered if issue.severity == "error")
    warning_count = sum(1 for issue in ordered if issue.severity == "warning")
    if not ordered:
        return DoctorReport(healthy=True, summary="No issues found.", issues=[])
    summary = f"{error_count} error(s), {warning_count} warning(s)."
    return DoctorReport(
        healthy=False,
        summary=summary,
        issues=ordered,
    )
