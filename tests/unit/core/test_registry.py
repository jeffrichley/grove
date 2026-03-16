"""Unit tests for grove.core.registry."""

from pathlib import Path

import pytest

from grove.core.registry import discover_packs


@pytest.mark.unit
def test_discover_packs_returns_base_and_python_in_order() -> None:
    """discover_packs() returns base and python when both present; base first."""
    packs = discover_packs()
    ids = [p.id for p in packs]
    assert "base" in ids
    assert "python" in ids
    assert ids.index("base") < ids.index("python")


@pytest.mark.unit
def test_discover_packs_assert_metadata() -> None:
    """Discovered Base and Python packs have expected metadata."""
    packs = discover_packs()
    by_id = {p.id: p for p in packs}
    base = by_id["base"]
    assert base.name == "Base Pack"
    assert base.version == "0.1.0"
    assert base.depends_on == []
    python = by_id["python"]
    assert python.name == "Python Pack"
    assert python.depends_on == ["base"]
    assert "python" in python.compatible_with


@pytest.mark.unit
def test_discover_packs_custom_dir(tmp_path: Path) -> None:
    """discover_packs(builtins_dir) uses custom directory."""
    sub = tmp_path / "mybase"
    sub.mkdir()
    (sub / "pack.toml").write_text(
        'id = "mybase"\nname = "My Base"\nversion = "0.1.0"\n'
    )
    packs = discover_packs(builtins_dir=tmp_path)
    assert len(packs) == 1
    assert packs[0].id == "mybase"


@pytest.mark.unit
def test_discover_packs_dependency_order(tmp_path: Path) -> None:
    """Packs are returned in dependency order (dep first)."""
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
    packs = discover_packs(builtins_dir=tmp_path)
    ids = [p.id for p in packs]
    assert ids == ["base", "ext"]


@pytest.mark.unit
def test_discover_packs_missing_dependency_raises(tmp_path: Path) -> None:
    """Pack depending on non-present pack raises ValueError."""
    only_dir = tmp_path / "only"
    only_dir.mkdir()
    (only_dir / "pack.toml").write_text(
        'id = "only"\nname = "Only"\nversion = "0.1.0"\ndepends_on = ["base"]\n'
    )
    with pytest.raises(ValueError, match=r"depends on 'base'.*not in the builtins"):
        discover_packs(builtins_dir=tmp_path)


@pytest.mark.unit
def test_discover_packs_nonexistent_dir_raises() -> None:
    """discover_packs(nonexistent_path) raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="Builtins directory not found"):
        discover_packs(builtins_dir=Path("/nonexistent/builtins/path"))
