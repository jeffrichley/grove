"""Unit tests for pack-owned doctor checks and stale tool-hook detection."""

from pathlib import Path

import pytest

from grove.core.doctor import run_doctor
from grove.core.doctor_checks import (
    collect_doctor_checks,
    collect_doctor_checks_with_issues,
)
from grove.core.manifest import MANIFEST_SCHEMA_VERSION, save_manifest
from grove.core.models import (
    GeneratedFileRecord,
    GroveSection,
    InitProvenance,
    InstalledPackRecord,
    ManifestState,
    PackManifest,
    ProjectProfile,
    ProjectSection,
)


def _make_profile(tmp_path: Path) -> ProjectProfile:
    """Build a profile fixture for doctor unit tests."""
    return ProjectProfile(
        project_name="fixture",
        project_root=tmp_path,
        language="python",
        package_manager="uv",
        test_framework="pytest",
        tools=["ruff"],
    )


def _make_manifest(tmp_path: Path, pack_ids: list[str]) -> ManifestState:
    """Build a manifest fixture for doctor pack-check tests."""
    return ManifestState(
        grove=GroveSection(version="0.1.0", schema_version=MANIFEST_SCHEMA_VERSION),
        project=ProjectSection(root=str(tmp_path), analysis_summary="python"),
        installed_packs=[
            InstalledPackRecord(id=pack_id, version="0.1.0") for pack_id in pack_ids
        ],
        generated_files=[
            GeneratedFileRecord(path="GROVE.md", pack_id="base"),
            GeneratedFileRecord(path="INDEX.md", pack_id="base"),
        ],
        init_provenance=InitProvenance(install_root=".grove"),
    )


def _make_pack(
    tmp_path: Path,
    pack_id: str,
    *,
    depends_on: list[str],
    contributes: dict[str, object],
) -> PackManifest:
    """Create a temporary pack manifest for doctor pack-check tests."""
    pack_root = tmp_path / "packs" / pack_id
    pack_root.mkdir(parents=True, exist_ok=True)
    return PackManifest(
        id=pack_id,
        name=pack_id.title(),
        version="0.1.0",
        depends_on=depends_on,
        contributes=contributes,
        root_dir=pack_root,
    )


def _write_template(path: Path, content: str) -> None:
    """Write one template fixture file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.mark.unit
def test_collect_doctor_checks_parses_pack_owned_specs(tmp_path: Path) -> None:
    """Pack-owned doctor check contributions load into typed specs."""
    # Arrange - one pack contributes a front-matter doctor check
    codex_pack = _make_pack(
        tmp_path,
        "codex",
        depends_on=["base"],
        contributes={
            "doctor_checks": [
                {
                    "id": "codex-planning-execution-front-matter",
                    "check_type": "skill_front_matter",
                    "tool": "codex",
                    "skill_path": "planning-execution",
                    "required_front_matter": ["name", "description"],
                    "order": 10,
                }
            ]
        },
    )

    # Act - collect doctor checks for the selected pack set
    checks = collect_doctor_checks([codex_pack], {"codex"})

    # Assert - the contribution becomes a typed doctor check spec
    assert len(checks) == 1
    assert checks[0].check_type == "skill_front_matter"
    assert checks[0].skill_path == Path("planning-execution")


@pytest.mark.unit
def test_collect_doctor_checks_with_issues_reports_invalid_entries(
    tmp_path: Path,
) -> None:
    """Malformed doctor checks are reported as issues instead of crashing."""
    # Arrange - one invalid check is missing its type and one valid but unsupported
    codex_pack = _make_pack(
        tmp_path,
        "codex",
        depends_on=["base"],
        contributes={
            "doctor_checks": [
                {"id": "missing-type"},
                {
                    "id": "unsupported",
                    "check_type": "not_real",
                },
            ]
        },
    )

    # Act - collect pack-owned doctor checks with resilient validation
    checks, issues = collect_doctor_checks_with_issues([codex_pack], {"codex"})

    # Assert - invalid entries become issues and valid entries still load
    assert [check.id for check in checks] == ["unsupported"]
    assert len(issues) == 1
    assert issues[0].code == "doctor-check-invalid"


@pytest.mark.unit
def test_run_doctor_reports_orphaned_tool_hook_block(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Doctor reports stale managed hook blocks left by an unselected pack."""
    # Arrange - base is installed but a stale Codex AGENTS block remains on disk
    manifest = _make_manifest(tmp_path, ["base"])
    manifest_path = tmp_path / ".grove" / "manifest.toml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    save_manifest(manifest_path, manifest)
    base_pack = _make_pack(
        tmp_path,
        "base",
        depends_on=[],
        contributes={"templates": ["GROVE.md.j2", "INDEX.md.j2"]},
    )
    codex_pack = _make_pack(
        tmp_path,
        "codex",
        depends_on=["base"],
        contributes={
            "tool_hooks": [
                {
                    "id": "codex-agents-shim",
                    "tool": "codex",
                    "hook_type": "managed_block",
                    "target": "AGENTS.md",
                    "content": "shim",
                    "order": 10,
                }
            ]
        },
    )
    _write_template(base_pack.root_dir / "GROVE.md.j2", "# Grove\n")
    _write_template(base_pack.root_dir / "INDEX.md.j2", "# Index\n")
    (tmp_path / ".grove" / "GROVE.md").write_text("# Grove\n", encoding="utf-8")
    (tmp_path / ".grove" / "INDEX.md").write_text("# Index\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text(
        "<!-- grove:tool-hook:codex:codex-agents-shim:start -->\n"
        "stale shim\n"
        "<!-- grove:tool-hook:codex:codex-agents-shim:end -->\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("grove.core.doctor.load_manifest", lambda _path: manifest)
    monkeypatch.setattr(
        "grove.core.doctor.get_builtin_pack_roots_and_packs",
        lambda: (
            {"base": base_pack.root_dir, "codex": codex_pack.root_dir},
            [base_pack, codex_pack],
        ),
    )
    monkeypatch.setattr(
        "grove.core.doctor.analyze",
        lambda _root: _make_profile(tmp_path),
    )

    # Act - run doctor against the repo with the stale managed hook block
    report = run_doctor(tmp_path)

    # Assert - doctor reports the orphaned managed hook block
    codes = {issue.code for issue in report.issues}
    assert "tool-hook-block-orphan" in codes


@pytest.mark.unit
def test_run_doctor_reports_unsupported_pack_doctor_check_as_issue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unsupported doctor check types become findings instead of tracebacks."""
    # Arrange - the selected pack contributes a check type the engine does not know
    manifest = _make_manifest(tmp_path, ["base", "codex"])
    manifest_path = tmp_path / ".grove" / "manifest.toml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    save_manifest(manifest_path, manifest)
    base_pack = _make_pack(
        tmp_path,
        "base",
        depends_on=[],
        contributes={"templates": ["GROVE.md.j2", "INDEX.md.j2"]},
    )
    codex_pack = _make_pack(
        tmp_path,
        "codex",
        depends_on=["base"],
        contributes={
            "doctor_checks": [
                {
                    "id": "unsupported",
                    "check_type": "not_real",
                }
            ]
        },
    )
    _write_template(base_pack.root_dir / "GROVE.md.j2", "# Grove\n")
    _write_template(base_pack.root_dir / "INDEX.md.j2", "# Index\n")
    (tmp_path / ".grove" / "GROVE.md").write_text("# Grove\n", encoding="utf-8")
    (tmp_path / ".grove" / "INDEX.md").write_text("# Index\n", encoding="utf-8")
    monkeypatch.setattr("grove.core.doctor.load_manifest", lambda _path: manifest)
    monkeypatch.setattr(
        "grove.core.doctor.get_builtin_pack_roots_and_packs",
        lambda: (
            {"base": base_pack.root_dir, "codex": codex_pack.root_dir},
            [base_pack, codex_pack],
        ),
    )
    monkeypatch.setattr(
        "grove.core.doctor.analyze",
        lambda _root: _make_profile(tmp_path),
    )

    # Act - run doctor with the unsupported pack-owned check
    report = run_doctor(tmp_path)

    # Assert - the bad check becomes a reported issue instead of crashing
    assert any(issue.code == "doctor-check-unsupported" for issue in report.issues)
