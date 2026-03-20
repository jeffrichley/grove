"""Unit tests for grove.core.registry."""

from pathlib import Path

import pytest

from grove.core.registry import discover_packs


@pytest.mark.unit
def test_discover_packs_returns_phase2_pack_set_in_dependency_order() -> None:
    """discover_packs() returns the Phase 2 builtins with base before dependents."""
    # Arrange - default Phase 2 builtins
    # Act - discover_packs
    packs = discover_packs()
    ids = [p.id for p in packs]
    # Assert - Phase 2 builtins are present and base loads before dependents
    assert ids == [
        "base",
        "codex",
        "commands",
        "knowledge",
        "memory",
        "project-context",
        "python",
    ]


@pytest.mark.unit
def test_discover_packs_assert_metadata() -> None:
    """Discovered builtins expose expected metadata for core Phase 2 packs."""
    # Arrange - default builtins
    # Act - discover_packs
    packs = discover_packs()
    by_id = {p.id: p for p in packs}
    base = by_id["base"]
    codex = by_id["codex"]
    memory = by_id["memory"]
    python = by_id["python"]
    # Assert - selected builtins have the expected metadata
    assert base.name == "Base Pack"
    assert base.version == "0.1.0"
    assert base.depends_on == []
    assert codex.name == "Codex Integration Pack"
    assert codex.depends_on == ["base"]
    assert memory.name == "Memory Pack"
    assert memory.depends_on == ["base"]
    assert python.name == "Python Pack"
    assert python.depends_on == ["base"]
    assert "python" in python.compatible_with


@pytest.mark.unit
def test_discover_packs_custom_dir(tmp_path: Path) -> None:
    """discover_packs(builtins_dir) uses custom directory."""
    # Arrange - custom dir with one pack
    sub = tmp_path / "mybase"
    sub.mkdir()
    (sub / "pack.toml").write_text(
        'id = "mybase"\nname = "My Base"\nversion = "0.1.0"\n'
    )
    # Act - discover_packs with builtins_dir
    packs = discover_packs(builtins_dir=tmp_path)
    # Assert - single pack with expected id
    assert len(packs) == 1
    assert packs[0].id == "mybase"


@pytest.mark.unit
def test_discover_packs_dependency_order(tmp_path: Path) -> None:
    """Packs are returned in dependency order (dep first)."""
    # Arrange - base and ext pack, ext depends on base
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    (base_dir / "pack.toml").write_text(
        'id = "base"\nname = "Base"\nversion = "0.1.0"\n'
    )
    ext_dir = tmp_path / "ext"
    ext_dir.mkdir()
    (ext_dir / "pack.toml").write_text(
        'id = "ext"\nname = "Ext"\nversion = "0.1.0"\ndepends_on = ["base"]\n'
    )
    # Act - discover_packs
    packs = discover_packs(builtins_dir=tmp_path)
    ids = [p.id for p in packs]
    # Assert - base before ext
    assert ids == ["base", "ext"]


@pytest.mark.unit
def test_discover_packs_missing_dependency_raises(tmp_path: Path) -> None:
    """Pack depending on non-present pack raises ValueError."""
    # Arrange - pack that depends on missing base
    only_dir = tmp_path / "only"
    only_dir.mkdir()
    (only_dir / "pack.toml").write_text(
        'id = "only"\nname = "Only"\nversion = "0.1.0"\ndepends_on = ["base"]\n'
    )
    # Act - discover_packs
    # Assert - ValueError about missing dependency
    with pytest.raises(ValueError, match=r"depends on 'base'.*not in the builtins"):
        discover_packs(builtins_dir=tmp_path)


@pytest.mark.unit
def test_discover_packs_nonexistent_dir_raises() -> None:
    """discover_packs(nonexistent_path) raises FileNotFoundError."""
    # Arrange - nonexistent builtins path
    # Act - discover_packs
    # Assert - FileNotFoundError
    with pytest.raises(FileNotFoundError, match="Builtins directory not found"):
        discover_packs(builtins_dir=Path("/nonexistent/builtins/path"))
