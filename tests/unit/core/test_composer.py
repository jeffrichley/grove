"""Unit tests for grove.core.composer."""

from pathlib import Path

import pytest

from grove.core.composer import compose
from grove.core.models import ProjectProfile
from grove.core.registry import discover_packs


def _packs_with_templates(tmp_path: Path) -> list:
    """Create base + python packs with templates and return discover_packs()."""
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    (base_dir / "pack.toml").write_text(
        'id = "base"\nname = "Base"\nversion = "0.1.0"\n'
        '[contributes]\ntemplates = ["GROVE.md.j2", "plans/.gitkeep.j2"]\n'
    )
    py_dir = tmp_path / "python"
    py_dir.mkdir()
    (py_dir / "pack.toml").write_text(
        'id = "python"\nname = "Python"\nversion = "0.1.0"\ndepends_on = ["base"]\n'
        '[contributes]\ntemplates = ["rules/python.md.j2"]\n'
    )
    return discover_packs(builtins_dir=tmp_path)


@pytest.mark.unit
def test_compose_plan_includes_base_and_python_files_when_both_selected(
    tmp_path: Path,
) -> None:
    """Plan includes files from Base and Python packs when both selected."""
    packs = _packs_with_templates(tmp_path)
    profile = ProjectProfile(
        project_name="my-app",
        language="python",
        package_manager="uv",
        test_framework="pytest",
    )
    install_root = tmp_path / ".grove"
    plan = compose(profile, ["base", "python"], install_root, packs)

    assert plan.install_root == install_root
    file_dsts = [f.dst for f in plan.files]
    assert (install_root / "GROVE.md") in file_dsts
    assert (install_root / "plans" / ".gitkeep") in file_dsts
    assert (install_root / "rules" / "python.md") in file_dsts
    assert len(plan.files) == 3

    base_files = [f for f in plan.files if f.pack_id == "base"]
    python_files = [f for f in plan.files if f.pack_id == "python"]
    assert len(base_files) == 2
    assert len(python_files) == 1


@pytest.mark.unit
def test_compose_variables_include_profile_fields(tmp_path: Path) -> None:
    """Variables include project_name, package_manager, test_framework from profile."""
    packs = _packs_with_templates(tmp_path)
    profile = ProjectProfile(
        project_name="my-project",
        language="python",
        package_manager="uv",
        test_framework="pytest",
        tools=["ruff", "mypy"],
    )
    install_root = tmp_path / ".grove"
    plan = compose(profile, ["base", "python"], install_root, packs)

    assert len(plan.files) >= 1
    for pf in plan.files:
        assert pf.variables["project_name"] == "my-project"
        assert pf.variables["package_manager"] == "uv"
        assert pf.variables["test_framework"] == "pytest"
        assert pf.variables["language"] == "python"
        assert pf.variables["tools"] == ["ruff", "mypy"]


@pytest.mark.unit
def test_compose_plan_structure(tmp_path: Path) -> None:
    """plan.install_root and plan.files structure are correct."""
    packs = _packs_with_templates(tmp_path)
    profile = ProjectProfile(project_name="x")
    install_root = tmp_path / ".grove"
    plan = compose(profile, ["base"], install_root, packs)

    assert plan.install_root == install_root.resolve()
    for pf in plan.files:
        assert pf.pack_id == "base"
        assert pf.src.suffix in ("", ".j2") or str(pf.src).endswith(".j2")
        under_root = pf.dst == install_root or (
            pf.dst.is_absolute() and install_root in pf.dst.parents
        )
        assert under_root
        assert isinstance(pf.variables, dict)
        assert pf.managed is True


@pytest.mark.unit
def test_compose_missing_pack_id_raises(tmp_path: Path) -> None:
    """Unknown selected pack id raises ValueError with clear message."""
    packs = _packs_with_templates(tmp_path)
    profile = ProjectProfile()
    install_root = tmp_path / ".grove"
    with pytest.raises(ValueError, match=r"Pack id 'nonexistent'.*not available"):
        compose(profile, ["base", "nonexistent"], install_root, packs)


@pytest.mark.unit
def test_compose_empty_selection_empty_files(tmp_path: Path) -> None:
    """Selecting no packs yields no files."""
    packs = _packs_with_templates(tmp_path)
    profile = ProjectProfile()
    install_root = tmp_path / ".grove"
    plan = compose(profile, [], install_root, packs)
    assert plan.install_root == install_root
    assert plan.files == []


@pytest.mark.unit
def test_compose_base_only_yields_base_templates(tmp_path: Path) -> None:
    """Selecting only base yields base pack files."""
    packs = _packs_with_templates(tmp_path)
    profile = ProjectProfile(project_name="a")
    install_root = tmp_path / ".grove"
    plan = compose(profile, ["base"], install_root, packs)
    assert all(f.pack_id == "base" for f in plan.files)
    assert len(plan.files) == 2
