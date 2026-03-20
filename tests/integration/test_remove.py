"""Integration tests for remove planning behavior."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from grove.analyzer import analyze
from grove.cli.app import app
from grove.core.manifest import (
    MANIFEST_SCHEMA_VERSION,
    load_manifest,
    save_manifest,
)
from grove.core.models import (
    GeneratedFileRecord,
    GroveSection,
    InitProvenance,
    InstalledPackRecord,
    ManifestState,
    PackManifest,
    ProjectSection,
)
from grove.core.registry import get_builtin_pack_roots_and_packs
from grove.core.remove_impl import build_remove_context, plan_remove

runner = CliRunner()


def _init_grove(root: Path, packs: list[str]) -> None:
    """Run grove init with the requested built-in packs."""
    args = ["init", "--root", str(root)]
    for pack_id in packs:
        args.extend(["--pack", pack_id])
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output


def _make_pack(
    tmp_path: Path,
    pack_id: str,
    *,
    depends_on: list[str],
    contributes: dict[str, object],
) -> PackManifest:
    """Create a temporary pack manifest for integration tests."""
    pack_root = tmp_path / "custom-packs" / pack_id
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
    """Write one pack template fixture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.mark.integration
def test_plan_remove_python_reports_rewrites_and_deletes_without_mutating_disk(
    tmp_path: Path,
) -> None:
    """Python remove planning rewrites shared files and deletes python-only files."""
    # Arrange - init Grove with base plus python and capture current managed content
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1.0"\n',
        encoding="utf-8",
    )
    _init_grove(tmp_path, ["base", "python"])
    manifest = load_manifest(tmp_path / ".grove" / "manifest.toml")
    grove_before = (tmp_path / ".grove" / "GROVE.md").read_text(encoding="utf-8")
    pack_roots, packs = get_builtin_pack_roots_and_packs()
    # Act - plan removal without applying any filesystem changes
    plan = plan_remove(
        "python",
        build_remove_context(
            tmp_path,
            manifest,
            pack_roots,
            analyze(tmp_path),
            packs,
        ),
    )
    changes = {(change.path, change.surface): change for change in plan.changes}
    # Assert - shared composed files rewrite, python-only files delete,
    # and disk stays unchanged.
    assert changes[(".grove/GROVE.md", "managed_file")].action == "rewrite"
    assert changes[(".grove/INDEX.md", "managed_file")].action == "rewrite"
    assert changes[(".grove/rules/python.md", "managed_file")].action == "delete"
    assert (
        changes[(".grove/skills/python-testing.md", "managed_file")].action == "delete"
    )
    assert (tmp_path / ".grove" / "GROVE.md").read_text(
        encoding="utf-8"
    ) == grove_before


@pytest.mark.integration
def test_plan_remove_codex_rewrites_agents_and_deletes_repo_local_skills(
    tmp_path: Path,
) -> None:
    """Codex remove planning treats AGENTS as rewrite-only and skills as deletions."""
    # Arrange - init Grove with Codex and add user-owned content
    # around the managed block.
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1.0"\n',
        encoding="utf-8",
    )
    _init_grove(tmp_path, ["base", "codex"])
    agents_path = tmp_path / "AGENTS.md"
    agents_path.write_text(
        "User intro\n\n" + agents_path.read_text(encoding="utf-8") + "\nUser outro\n",
        encoding="utf-8",
    )
    agents_before = agents_path.read_text(encoding="utf-8")
    manifest = load_manifest(tmp_path / ".grove" / "manifest.toml")
    pack_roots, packs = get_builtin_pack_roots_and_packs()
    # Act - plan Codex removal without mutating AGENTS or repo-local skills
    plan = plan_remove(
        "codex",
        build_remove_context(
            tmp_path,
            manifest,
            pack_roots,
            analyze(tmp_path),
            packs,
        ),
    )
    changes = {(change.path, change.surface): change for change in plan.changes}
    # Assert - AGENTS is scheduled for rewrite only, repo-local skills are deletions
    assert changes[("AGENTS.md", "tool_hook")].action == "rewrite"
    assert (
        changes[
            (".agents/skills/planning-execution/SKILL.md", "pack_local_skill")
        ].action
        == "delete"
    )
    assert (
        changes[(".agents/skills/memory-writeback/SKILL.md", "pack_local_skill")].action
        == "delete"
    )
    assert agents_path.read_text(encoding="utf-8") == agents_before


@pytest.mark.integration
def test_remove_dry_run_reports_changes_without_mutating_files(tmp_path: Path) -> None:
    """Remove dry-run leaves manifest and managed files unchanged."""
    # Arrange - init Grove with python and capture current manifest and content
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1.0"\n',
        encoding="utf-8",
    )
    _init_grove(tmp_path, ["base", "python"])
    manifest_before = (tmp_path / ".grove" / "manifest.toml").read_text(
        encoding="utf-8"
    )
    grove_before = (tmp_path / ".grove" / "GROVE.md").read_text(encoding="utf-8")
    # Act - run remove in dry-run mode
    result = runner.invoke(
        app,
        ["remove", "python", "--root", str(tmp_path), "--dry-run"],
    )
    # Assert - report includes rewrite/delete classification and disk stays unchanged
    assert result.exit_code == 0, result.output
    assert "Dry run" in result.output
    assert "Deleted:" in result.output
    assert "Rewritten:" in result.output
    assert (tmp_path / ".grove" / "manifest.toml").read_text(
        encoding="utf-8"
    ) == manifest_before
    assert (tmp_path / ".grove" / "GROVE.md").read_text(
        encoding="utf-8"
    ) == grove_before


@pytest.mark.integration
def test_remove_python_updates_manifest_and_removes_python_outputs(
    tmp_path: Path,
) -> None:
    """Remove rewrites shared Grove files and deletes python-only outputs."""
    # Arrange - init Grove with base plus python
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1.0"\n',
        encoding="utf-8",
    )
    _init_grove(tmp_path, ["base", "python"])
    # Act - remove the python pack
    result = runner.invoke(app, ["remove", "python", "--root", str(tmp_path)])
    # Assert - command succeeds, manifest drops python, and python-only outputs are gone
    assert result.exit_code == 0, result.output
    assert "Removed pack python." in result.output
    manifest = load_manifest(tmp_path / ".grove" / "manifest.toml")
    assert [record.id for record in manifest.installed_packs] == ["base"]
    assert not (tmp_path / ".grove" / "rules" / "python.md").exists()
    assert not (tmp_path / ".grove" / "skills" / "python-testing.md").exists()
    assert "### Python Workflow" not in (tmp_path / ".grove" / "GROVE.md").read_text(
        encoding="utf-8"
    )


@pytest.mark.integration
def test_remove_base_exits_nonzero_with_clear_error(tmp_path: Path) -> None:
    """Removing base fails with a clear non-removable error."""
    # Arrange - init Grove with the required base pack
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1.0"\n',
        encoding="utf-8",
    )
    _init_grove(tmp_path, ["base", "python"])
    # Act - try to remove base through the CLI
    result = runner.invoke(app, ["remove", "base", "--root", str(tmp_path)])
    # Assert - command fails and reports the base-pack lifecycle rule
    assert result.exit_code != 0
    assert "cannot be removed" in result.output


@pytest.mark.integration
def test_remove_pack_with_installed_dependent_exits_nonzero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Removing a pack with an installed dependent is blocked by the CLI."""
    # Arrange - create a temporary manifest with base, python, and an extra dependent
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1.0"\n',
        encoding="utf-8",
    )
    manifest = ManifestState(
        grove=GroveSection(version="0.1.0", schema_version=MANIFEST_SCHEMA_VERSION),
        project=ProjectSection(root=str(tmp_path), analysis_summary="python"),
        installed_packs=[
            InstalledPackRecord(id="base", version="0.1.0"),
            InstalledPackRecord(id="python", version="0.1.0"),
            InstalledPackRecord(id="extra", version="0.1.0"),
        ],
        generated_files=[
            GeneratedFileRecord(path="GROVE.md", pack_id="base"),
            GeneratedFileRecord(path="INDEX.md", pack_id="base"),
            GeneratedFileRecord(path="rules/python.md", pack_id="python"),
        ],
        init_provenance=InitProvenance(install_root=".grove"),
    )
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
    extra_pack = _make_pack(
        tmp_path,
        "extra",
        depends_on=["python"],
        contributes={"templates": []},
    )
    _write_template(base_pack.root_dir / "GROVE.md.j2", "# Grove\n")
    _write_template(base_pack.root_dir / "INDEX.md.j2", "# Index\n")
    _write_template(python_pack.root_dir / "rules/python.md.j2", "# Python Rules\n")
    monkeypatch.setattr(
        "grove.core.remove.get_builtin_pack_roots_and_packs",
        lambda: (
            {
                "base": base_pack.root_dir,
                "python": python_pack.root_dir,
                "extra": extra_pack.root_dir,
            },
            [base_pack, python_pack, extra_pack],
        ),
    )
    # Act - try to remove python while the extra pack still depends on it
    result = runner.invoke(app, ["remove", "python", "--root", str(tmp_path)])
    # Assert - the CLI blocks removal and explains which dependent is installed
    assert result.exit_code != 0
    assert "installed dependents: extra" in result.output
