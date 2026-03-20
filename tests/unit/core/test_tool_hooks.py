"""Unit tests for grove.core.tool_hooks."""

from pathlib import Path

import pytest

from grove.core.manifest import MANIFEST_SCHEMA_VERSION
from grove.core.models import (
    GroveSection,
    InstalledPackRecord,
    ManifestState,
    PackManifest,
    ProjectProfile,
    ProjectSection,
)
from grove.core.tool_hooks import apply_tool_hooks, collect_tool_hooks


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
