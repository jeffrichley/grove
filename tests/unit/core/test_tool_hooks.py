"""Unit tests for grove.core.tool_hooks."""

from pathlib import Path

import pytest

from grove.core.manifest import MANIFEST_SCHEMA_VERSION
from grove.core.models import (
    CodexSkillTargetState,
    GroveSection,
    InstalledPackRecord,
    ManifestState,
    PackManifest,
    ProjectProfile,
    ProjectSection,
    ToolHookTargetState,
)
from grove.core.tool_hooks import (
    apply_tool_hooks,
    collect_codex_skills,
    collect_tool_hooks,
    plan_codex_skill_targets,
    plan_tool_hook_targets,
)


def _make_manifest(tmp_path: Path, pack_id: str = "demo-tool") -> ManifestState:
    """Build a manifest with one installed integration pack."""
    return ManifestState(
        grove=GroveSection(version="0.1.0", schema_version=MANIFEST_SCHEMA_VERSION),
        project=ProjectSection(root=str(tmp_path), analysis_summary="python"),
        installed_packs=[InstalledPackRecord(id=pack_id, version="0.1.0")],
    )


def _make_profile(tmp_path: Path) -> ProjectProfile:
    """Build a basic project profile for template rendering."""
    return ProjectProfile(
        project_name="fixture",
        project_root=tmp_path,
        language="python",
        package_manager="uv",
        test_framework="pytest",
        tools=["ruff"],
    )


@pytest.mark.unit
def test_collect_tool_hooks_orders_by_order_then_id(tmp_path: Path) -> None:
    """Tool hooks are collected deterministically for selected packs only."""
    # Arrange - two selected hook contributions with different order and id
    pack_root = tmp_path / "pack"
    pack_root.mkdir()
    pack = PackManifest(
        id="demo-tool",
        name="Demo Tool",
        version="0.1.0",
        root_dir=pack_root,
        contributes={
            "tool_hooks": [
                {
                    "id": "second",
                    "tool": "demo",
                    "hook_type": "managed_block",
                    "target": "HOOKS.md",
                    "content": "second",
                    "order": 20,
                },
                {
                    "id": "first",
                    "tool": "demo",
                    "hook_type": "managed_block",
                    "target": "HOOKS.md",
                    "content": "first",
                    "order": 10,
                },
            ]
        },
    )
    # Act - collect hooks
    hooks = collect_tool_hooks([pack], {"demo-tool"})
    # Assert - deterministic order and parsed fields
    assert [hook.id for hook in hooks] == ["first", "second"]
    assert hooks[0].target == Path("HOOKS.md")


@pytest.mark.unit
def test_apply_tool_hooks_updates_only_managed_block(tmp_path: Path) -> None:
    """Managed block hooks preserve user content outside the Grove block."""
    # Arrange - one integration pack writing to a project-root hook file
    pack_root = tmp_path / "pack"
    hooks_dir = pack_root / "hooks"
    hooks_dir.mkdir(parents=True)
    (hooks_dir / "demo.md.j2").write_text("Hello {{ project_name }} from Grove")
    pack = PackManifest(
        id="demo-tool",
        name="Demo Tool",
        version="0.1.0",
        root_dir=pack_root,
        contributes={
            "tool_hooks": [
                {
                    "id": "demo-shim",
                    "tool": "demo",
                    "hook_type": "managed_block",
                    "target": "HOOKS.md",
                    "source": "hooks/demo.md.j2",
                    "order": 10,
                }
            ]
        },
    )
    target = tmp_path / "HOOKS.md"
    target.write_text(
        "User-owned header\n\n"
        "<!-- grove:tool-hook:demo:demo-shim:start -->\n"
        "stale block\n"
        "<!-- grove:tool-hook:demo:demo-shim:end -->\n"
    )
    # Act - apply hooks to the existing file
    changed = apply_tool_hooks(
        tmp_path,
        _make_manifest(tmp_path),
        [pack],
        _make_profile(tmp_path),
    )
    # Assert - user content remains and only the managed block changes
    assert changed == ["HOOKS.md"]
    content = target.read_text()
    assert "User-owned header" in content
    assert "Hello fixture from Grove" in content
    assert "stale block" not in content


@pytest.mark.unit
def test_collect_codex_skills_orders_and_preserves_paths(tmp_path: Path) -> None:
    """Codex skills are collected from selected packs in deterministic order."""
    # Arrange - one integration pack with two Codex skill contributions
    pack_root = tmp_path / "pack"
    pack_root.mkdir()
    pack = PackManifest(
        id="codex",
        name="Codex",
        version="0.1.0",
        root_dir=pack_root,
        contributes={
            "codex_skills": [
                {
                    "id": "memory",
                    "path": "memory-writeback",
                    "content": "memory",
                    "order": 20,
                },
                {
                    "id": "planning",
                    "path": "planning-execution",
                    "content": "planning",
                    "order": 10,
                },
            ]
        },
    )
    # Act - collect skills
    skills = collect_codex_skills([pack], {"codex"})
    # Assert - deterministic order and preserved destination paths
    assert [skill.id for skill in skills] == ["planning", "memory"]
    assert skills[0].path == Path("planning-execution")


@pytest.mark.unit
def test_apply_tool_hooks_materializes_codex_skills_under_repo_local_agents_dir(
    tmp_path: Path,
) -> None:
    """Codex skills materialize under .agents/skills within the project root."""
    # Arrange - one Codex integration pack with a single inline skill body
    pack_root = tmp_path / "pack"
    pack_root.mkdir()
    pack = PackManifest(
        id="codex",
        name="Codex",
        version="0.1.0",
        root_dir=pack_root,
        contributes={
            "codex_skills": [
                {
                    "id": "planning",
                    "path": "planning-execution",
                    "content": "# Planning Execution",
                    "order": 10,
                }
            ]
        },
    )
    # Act - apply tool hooks for the selected Codex pack
    changed = apply_tool_hooks(
        tmp_path,
        _make_manifest(tmp_path, pack_id="codex"),
        [pack],
        _make_profile(tmp_path),
    )
    # Assert - skill body is written under the repo-local .agents tree
    skill_path = tmp_path / ".agents" / "skills" / "planning-execution" / "SKILL.md"
    assert changed == [".agents/skills/planning-execution/SKILL.md"]
    assert skill_path.exists()
    assert "Planning Execution" in skill_path.read_text(encoding="utf-8")


@pytest.mark.unit
def test_plan_tool_hook_targets_groups_rendered_blocks_by_target_path(
    tmp_path: Path,
) -> None:
    """Tool-hook planning returns deterministic per-target state for remove."""
    # Arrange - two managed-block hooks render into the same target file
    pack_root = tmp_path / "pack"
    pack_root.mkdir()
    pack = PackManifest(
        id="codex",
        name="Codex",
        version="0.1.0",
        root_dir=pack_root,
        contributes={
            "tool_hooks": [
                {
                    "id": "shim-a",
                    "tool": "codex",
                    "hook_type": "managed_block",
                    "target": "AGENTS.md",
                    "content": "A {{ project_name }}",
                    "order": 10,
                },
                {
                    "id": "shim-b",
                    "tool": "codex",
                    "hook_type": "managed_block",
                    "target": "AGENTS.md",
                    "content": "B {{ project_name }}",
                    "order": 20,
                },
            ]
        },
    )
    # Act - plan desired tool-hook targets for the selected pack
    states = plan_tool_hook_targets(
        tmp_path,
        [pack],
        _make_profile(tmp_path),
        {"codex"},
    )
    # Assert - one grouped target keeps deterministic hook metadata and blocks
    assert states == [
        ToolHookTargetState(
            path="AGENTS.md",
            hook_type="managed_block",
            tools=["codex", "codex"],
            hook_ids=["shim-a", "shim-b"],
            pack_ids=["codex", "codex"],
            rendered_blocks=["A fixture", "B fixture"],
        )
    ]


@pytest.mark.unit
def test_plan_codex_skill_targets_render_repo_local_skill_state(tmp_path: Path) -> None:
    """Codex skill planning returns rendered repo-local skill targets."""
    # Arrange - one Codex pack contributes one repo-local skill
    pack_root = tmp_path / "pack"
    pack_root.mkdir()
    pack = PackManifest(
        id="codex",
        name="Codex",
        version="0.1.0",
        root_dir=pack_root,
        contributes={
            "codex_skills": [
                {
                    "id": "planning",
                    "path": "planning-execution",
                    "content": "# {{ project_name }} Planning",
                    "order": 10,
                }
            ]
        },
    )
    # Act - plan rendered repo-local skill state
    states = plan_codex_skill_targets(
        tmp_path,
        [pack],
        _make_profile(tmp_path),
        {"codex"},
    )
    # Assert - target state is project-root-relative with rendered content
    assert states == [
        CodexSkillTargetState(
            path=".agents/skills/planning-execution/SKILL.md",
            skill_id="planning",
            pack_id="codex",
            rendered_content="# fixture Planning\n",
        )
    ]
