"""Unit tests for grove.core.doctor and grove.core.doctor_checks."""

from pathlib import Path

import pytest

from grove.core.doctor import run_doctor
from grove.core.doctor_checks import check_pack_coherence
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
    """Build a profile fixture for doctor tests."""
    return ProjectProfile(
        project_name="fixture",
        project_root=tmp_path,
        language="python",
        package_manager="uv",
        test_framework="pytest",
        tools=["ruff"],
    )


def _make_manifest(
    tmp_path: Path,
    pack_ids: list[str],
    generated_files: list[GeneratedFileRecord] | None = None,
) -> ManifestState:
    """Build a manifest fixture for doctor checks."""
    return ManifestState(
        grove=GroveSection(version="0.1.0", schema_version=MANIFEST_SCHEMA_VERSION),
        project=ProjectSection(root=str(tmp_path), analysis_summary="python"),
        installed_packs=[
            InstalledPackRecord(id=pack_id, version="0.1.0") for pack_id in pack_ids
        ],
        generated_files=generated_files
        or [
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
    """Create a temporary pack manifest for doctor unit tests."""
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
def test_check_pack_coherence_reports_missing_dependency() -> None:
    """Missing installed dependencies are reported as doctor issues."""
    # Arrange - manifest installs python without its required base dependency
    manifest = _make_manifest(Path("E:/tmp"), ["python"])
    python_pack = PackManifest(
        id="python",
        name="Python",
        version="0.1.0",
        depends_on=["base"],
    )
    # Act - evaluate generic pack coherence checks
    issues = check_pack_coherence(manifest, [python_pack])
    # Assert - doctor reports the missing dependency against the pack
    assert len(issues) == 1
    assert issues[0].code == "pack-dependency-missing"
    assert issues[0].pack_id == "python"


@pytest.mark.unit
def test_run_doctor_reports_missing_manifest(tmp_path: Path) -> None:
    """Doctor returns a manifest issue when no Grove install exists."""
    # Arrange - project root without any Grove files
    # Act - run doctor against the empty project
    report = run_doctor(tmp_path)
    # Assert - the missing manifest is reported as an error
    assert report.healthy is False
    assert report.issues[0].code == "manifest-missing"


@pytest.mark.unit
def test_run_doctor_reports_drifted_managed_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Doctor reports drift when a managed file no longer matches desired output."""
    # Arrange - manifest, packs, and drifted GROVE content on disk
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
    _write_template(base_pack.root_dir / "GROVE.md.j2", "# Grove\n")
    _write_template(base_pack.root_dir / "INDEX.md.j2", "# Index\n")
    (tmp_path / ".grove" / "GROVE.md").write_text("stale grove\n", encoding="utf-8")
    (tmp_path / ".grove" / "INDEX.md").write_text("# Index\n", encoding="utf-8")
    monkeypatch.setattr(
        "grove.core.doctor.load_manifest",
        lambda _path: manifest,
    )
    monkeypatch.setattr(
        "grove.core.doctor.get_builtin_pack_roots_and_packs",
        lambda: ({"base": base_pack.root_dir}, [base_pack]),
    )
    monkeypatch.setattr(
        "grove.core.doctor.analyze",
        lambda _root: _make_profile(tmp_path),
    )
    # Act - run doctor against the drifted install
    report = run_doctor(tmp_path)
    # Assert - doctor reports managed file drift and marks the repo unhealthy
    assert report.healthy is False
    assert any(issue.code == "managed-file-drift" for issue in report.issues)


@pytest.mark.unit
def test_run_doctor_reports_missing_tool_target_and_skill(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Doctor reports missing tool-hook targets and pack-local skills."""
    # Arrange - manifest selects codex but its outputs are absent on disk
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
            "tool_hooks": [
                {
                    "id": "codex-agents-shim",
                    "tool": "codex",
                    "hook_type": "managed_block",
                    "target": "AGENTS.md",
                    "content": "shim",
                    "order": 10,
                }
            ],
            "codex_skills": [
                {
                    "id": "codex-planning",
                    "path": "planning-execution",
                    "content": "# Skill",
                    "order": 10,
                }
            ],
        },
    )
    _write_template(base_pack.root_dir / "GROVE.md.j2", "# Grove\n")
    _write_template(base_pack.root_dir / "INDEX.md.j2", "# Index\n")
    (tmp_path / ".grove").mkdir(parents=True, exist_ok=True)
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
    # Act - run doctor against the missing tool outputs
    report = run_doctor(tmp_path)
    # Assert - both the hook target and the skill file are reported
    codes = {issue.code for issue in report.issues}
    assert "tool-hook-target-missing" in codes
    assert "pack-local-skill-missing" in codes


@pytest.mark.unit
def test_run_doctor_reports_skill_front_matter_issues(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Doctor reports missing and malformed front matter from pack-owned checks."""
    # Arrange - manifest selects codex and materializes invalid skill files on disk
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
            "codex_skills": [
                {
                    "id": "codex-planning-execution",
                    "path": "planning-execution",
                    "content": (
                        "---\nname: Planning Execution\n"
                        "description: Good\n---\n\n# Planning Execution"
                    ),
                    "order": 10,
                },
                {
                    "id": "codex-memory-writeback",
                    "path": "memory-writeback",
                    "content": (
                        "---\nname: Memory Writeback\n"
                        "description: Good\n---\n\n# Memory Writeback"
                    ),
                    "order": 20,
                },
            ],
            "doctor_checks": [
                {
                    "id": "codex-planning-execution-front-matter",
                    "check_type": "skill_front_matter",
                    "tool": "codex",
                    "skill_path": "planning-execution",
                    "required_front_matter": ["name", "description"],
                    "order": 10,
                },
                {
                    "id": "codex-memory-writeback-front-matter",
                    "check_type": "skill_front_matter",
                    "tool": "codex",
                    "skill_path": "memory-writeback",
                    "required_front_matter": ["name", "description"],
                    "order": 20,
                },
            ],
        },
    )
    _write_template(base_pack.root_dir / "GROVE.md.j2", "# Grove\n")
    _write_template(base_pack.root_dir / "INDEX.md.j2", "# Index\n")
    (tmp_path / ".grove" / "GROVE.md").write_text("# Grove\n", encoding="utf-8")
    (tmp_path / ".grove" / "INDEX.md").write_text("# Index\n", encoding="utf-8")
    planning_skill = tmp_path / ".agents" / "skills" / "planning-execution" / "SKILL.md"
    memory_skill = tmp_path / ".agents" / "skills" / "memory-writeback" / "SKILL.md"
    planning_skill.parent.mkdir(parents=True, exist_ok=True)
    memory_skill.parent.mkdir(parents=True, exist_ok=True)
    planning_skill.write_text("# Planning Execution\n", encoding="utf-8")
    memory_skill.write_text(
        "---\nname Memory Writeback\n---\n\n# Memory Writeback\n",
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
    # Act - run doctor against the invalid skill front matter
    report = run_doctor(tmp_path)
    # Assert - missing and malformed front matter issues are both reported
    codes = {issue.code for issue in report.issues}
    assert "skill-front-matter-missing" in codes
    assert "skill-front-matter-malformed" in codes
