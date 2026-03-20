"""Unit tests for grove.core.remove_impl."""

from pathlib import Path

import pytest

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
from grove.core.remove import run_remove
from grove.core.remove_impl import build_remove_context, plan_remove
from grove.exceptions import GroveManifestError


def _make_profile(tmp_path: Path) -> ProjectProfile:
    """Build a profile fixture for remove planning tests."""
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
    """Build a manifest fixture with configurable generated files."""
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
            GeneratedFileRecord(path="rules/python.md", pack_id="python"),
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
    """Create a pack manifest with a writable root for template rendering."""
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
def test_plan_remove_rejects_base_pack(tmp_path: Path) -> None:
    """The base pack cannot be removed."""
    # Arrange - manifest and pack registry with only the required base pack
    manifest = _make_manifest(tmp_path, ["base"])
    base_pack = _make_pack(
        tmp_path,
        "base",
        depends_on=[],
        contributes={"templates": ["GROVE.md.j2", "INDEX.md.j2"]},
    )
    _write_template(base_pack.root_dir / "GROVE.md.j2", "# base\n")
    _write_template(base_pack.root_dir / "INDEX.md.j2", "# index\n")
    # Act - attempt to remove the required base pack.
    context = build_remove_context(
        tmp_path,
        manifest,
        {"base": base_pack.root_dir},
        _make_profile(tmp_path),
        [base_pack],
    )

    # Assert - removal is blocked by the base-pack lifecycle guardrail.
    with pytest.raises(ValueError, match="cannot be removed"):
        plan_remove("base", context)


@pytest.mark.unit
def test_plan_remove_rejects_pack_with_installed_dependents(tmp_path: Path) -> None:
    """A pack with installed dependents cannot be removed."""
    # Arrange - extra depends on python, so python cannot be removed first
    manifest = _make_manifest(tmp_path, ["base", "python", "extra"])
    base_pack = _make_pack(
        tmp_path,
        "base",
        depends_on=[],
        contributes={"templates": ["GROVE.md.j2", "INDEX.md.j2"]},
    )
    python_pack = _make_pack(
        tmp_path,
        "python",
        depends_on=["base"],
        contributes={},
    )
    extra_pack = _make_pack(
        tmp_path,
        "extra",
        depends_on=["python"],
        contributes={},
    )
    _write_template(base_pack.root_dir / "GROVE.md.j2", "# base\n")
    _write_template(base_pack.root_dir / "INDEX.md.j2", "# index\n")
    # Act - attempt to remove python while an installed dependent still exists.
    context = build_remove_context(
        tmp_path,
        manifest,
        {
            "base": base_pack.root_dir,
            "python": python_pack.root_dir,
            "extra": extra_pack.root_dir,
        },
        _make_profile(tmp_path),
        [base_pack, python_pack, extra_pack],
    )

    # Assert - removal is blocked until the dependent pack is removed first.
    with pytest.raises(ValueError, match="installed dependents: extra"):
        plan_remove("python", context)


@pytest.mark.unit
def test_plan_remove_classifies_managed_files_by_delete_rewrite_and_preserve(
    tmp_path: Path,
) -> None:
    """Managed files are classified from current and remaining desired state."""
    # Arrange - base owns shared files and python contributes one file plus one anchor
    manifest = _make_manifest(tmp_path, ["base", "python"])
    base_pack = _make_pack(
        tmp_path,
        "base",
        depends_on=[],
        contributes={"templates": ["GROVE.md.j2", "INDEX.md.j2"]},
    )
    python_pack = _make_pack(
        tmp_path,
        "python",
        depends_on=["base"],
        contributes={
            "templates": ["rules/python.md.j2"],
            "injections": [
                {
                    "id": "python-guidance",
                    "anchor": "guidance",
                    "content": "Python guidance",
                    "order": 10,
                }
            ],
        },
    )
    _write_template(
        base_pack.root_dir / "GROVE.md.j2",
        "<!-- grove:anchor:guidance:start -->\n<!-- grove:anchor:guidance:end -->\n",
    )
    _write_template(base_pack.root_dir / "INDEX.md.j2", "# Index\n")
    _write_template(python_pack.root_dir / "rules/python.md.j2", "# Python Rules\n")
    # Act - build the remove plan for python
    context = build_remove_context(
        tmp_path,
        manifest,
        {"base": base_pack.root_dir, "python": python_pack.root_dir},
        _make_profile(tmp_path),
        [base_pack, python_pack],
    )
    plan = plan_remove("python", context)
    changes = {(change.path, change.surface): change for change in plan.changes}
    # Assert - shared file rewrites, python-only file deletes, unrelated files preserve
    assert changes[(".grove/GROVE.md", "managed_file")].action == "rewrite"
    assert changes[(".grove/GROVE.md", "managed_file")].anchors == ["guidance"]
    assert changes[(".grove/INDEX.md", "managed_file")].action == "preserve"
    assert changes[(".grove/rules/python.md", "managed_file")].action == "delete"


@pytest.mark.unit
def test_plan_remove_classifies_tool_hooks_and_codex_skills(tmp_path: Path) -> None:
    """Tool-native outputs are planned separately from Grove managed files."""
    # Arrange - one Codex integration contributes an AGENTS block and one skill
    manifest = _make_manifest(
        tmp_path,
        ["base", "codex"],
        generated_files=[
            GeneratedFileRecord(path="GROVE.md", pack_id="base"),
            GeneratedFileRecord(path="INDEX.md", pack_id="base"),
        ],
    )
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
                    "content": "Codex shim",
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
    # Act - build the remove plan for the Codex integration
    context = build_remove_context(
        tmp_path,
        manifest,
        {"base": base_pack.root_dir, "codex": codex_pack.root_dir},
        _make_profile(tmp_path),
        [base_pack, codex_pack],
    )
    plan = plan_remove("codex", context)
    changes = {(change.path, change.surface): change for change in plan.changes}
    # Assert - AGENTS is rewritten, the repo-local skill is deleted
    assert changes[("AGENTS.md", "tool_hook")].action == "rewrite"
    assert (
        changes[
            (".agents/skills/planning-execution/SKILL.md", "pack_local_skill")
        ].action
        == "delete"
    )


@pytest.mark.unit
def test_run_remove_restores_files_when_manifest_finalize_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Failed manifest finalization rolls back on-disk remove mutations."""
    # Arrange - build a removable base+python install and capture pre-remove state
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1.0"\n',
        encoding="utf-8",
    )
    manifest = _make_manifest(tmp_path, ["base", "python"])
    manifest_path = tmp_path / ".grove" / "manifest.toml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    save_manifest(manifest_path, manifest)
    base_pack = _make_pack(
        tmp_path,
        "base",
        depends_on=[],
        contributes={"templates": ["GROVE.md.j2", "INDEX.md.j2"]},
    )
    python_pack = _make_pack(
        tmp_path,
        "python",
        depends_on=["base"],
        contributes={"templates": ["rules/python.md.j2"]},
    )
    _write_template(base_pack.root_dir / "GROVE.md.j2", "# Grove\n")
    _write_template(base_pack.root_dir / "INDEX.md.j2", "# Index\n")
    _write_template(python_pack.root_dir / "rules/python.md.j2", "# Python Rules\n")
    (tmp_path / ".grove" / "GROVE.md").write_text("# Grove\n", encoding="utf-8")
    (tmp_path / ".grove" / "INDEX.md").write_text("# Index\n", encoding="utf-8")
    python_rules = tmp_path / ".grove" / "rules" / "python.md"
    python_rules.parent.mkdir(parents=True, exist_ok=True)
    python_rules.write_text("# Python Rules\n", encoding="utf-8")
    manifest_before = manifest_path.read_text(encoding="utf-8")
    python_before = python_rules.read_text(encoding="utf-8")
    monkeypatch.setattr(
        "grove.core.remove.get_builtin_pack_roots_and_packs",
        lambda: (
            {"base": base_pack.root_dir, "python": python_pack.root_dir},
            [base_pack, python_pack],
        ),
    )

    def _raise_disk_full(_self: Path, _target: Path) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(
        Path,
        "replace",
        _raise_disk_full,
    )

    # Act - attempt remove and force manifest finalization to fail
    with pytest.raises(GroveManifestError, match="disk full"):
        run_remove(tmp_path, "python")

    # Assert - the on-disk files and manifest are restored to their prior state
    assert python_rules.read_text(encoding="utf-8") == python_before
    assert manifest_path.read_text(encoding="utf-8") == manifest_before
