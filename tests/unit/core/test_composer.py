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
        "[contributes]\n"
        'templates = ["GROVE.md.j2", "INDEX.md.j2"]\n'
    )
    (base_dir / "GROVE.md.j2").write_text(
        "<!-- grove:anchor:guidance:start --><!-- grove:anchor:guidance:end -->"
    )
    (base_dir / "INDEX.md.j2").write_text(
        "<!-- grove:anchor:guidance:start --><!-- grove:anchor:guidance:end -->\n"
        "<!-- grove:anchor:rules:start --><!-- grove:anchor:rules:end -->"
    )
    py_dir = tmp_path / "python"
    py_dir.mkdir()
    (py_dir / "pack.toml").write_text(
        'id = "python"\nname = "Python"\nversion = "0.1.0"\ndepends_on = ["base"]\n'
        '[contributes]\ntemplates = ["rules/python.md.j2"]\n'
        "[[contributes.injections]]\n"
        'id = "python-guidance"\n'
        'anchor = "guidance"\n'
        'source = "snippets/guidance.md.j2"\n'
        "order = 10\n"
        "[[contributes.injections]]\n"
        'id = "python-rules"\n'
        'target = "INDEX.md"\n'
        'anchor = "rules"\n'
        'content = """### Python Rules\n\n'
        "Python guidance.\n\n"
        'When to use: Use when editing Python code."""\n'
        "order = 10\n"
        "[[contributes.injections]]\n"
        'id = "python-testing"\n'
        'target = "INDEX.md"\n'
        'anchor = "rules"\n'
        'content = """### Python Testing\n\n'
        "Testing guidance.\n\n"
        'When to use: Use when updating pytest coverage."""\n'
        "order = 20\n"
    )
    (py_dir / "rules").mkdir()
    (py_dir / "rules" / "python.md.j2").write_text("# Python")
    (py_dir / "snippets").mkdir()
    (py_dir / "snippets" / "guidance.md.j2").write_text("Injected guidance")
    return discover_packs(builtins_dir=tmp_path)


@pytest.mark.unit
def test_compose_plan_includes_base_and_python_files_when_both_selected(
    tmp_path: Path,
) -> None:
    """Plan includes files from Base and Python packs when both selected."""
    # Arrange - base and python packs, profile, install root
    packs = _packs_with_templates(tmp_path)
    profile = ProjectProfile(
        project_name="my-app",
        language="python",
        package_manager="uv",
        test_framework="pytest",
    )
    install_root = tmp_path / ".grove"
    # Act - compose with base and python selected
    plan = compose(profile, ["base", "python"], install_root, packs)
    # Assert - install_root and three files from both packs
    assert plan.install_root == install_root
    file_dsts = [f.dst for f in plan.files]
    assert (install_root / "GROVE.md") in file_dsts
    assert (install_root / "INDEX.md") in file_dsts
    assert (install_root / "rules" / "python.md") in file_dsts
    assert len(plan.files) == 3
    base_files = [f for f in plan.files if f.pack_id == "base"]
    python_files = [f for f in plan.files if f.pack_id == "python"]
    assert len(base_files) == 2
    assert len(python_files) == 1


@pytest.mark.unit
def test_compose_variables_include_profile_fields(tmp_path: Path) -> None:
    """Variables include project_name, package_manager, test_framework from profile."""
    # Arrange - packs and profile with all variable fields set
    packs = _packs_with_templates(tmp_path)
    profile = ProjectProfile(
        project_name="my-project",
        language="python",
        package_manager="uv",
        test_framework="pytest",
        tools=["ruff", "mypy"],
    )
    install_root = tmp_path / ".grove"
    # Act - compose
    plan = compose(profile, ["base", "python"], install_root, packs)
    # Assert - every planned file has profile fields in variables
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
    # Arrange - packs and minimal profile
    packs = _packs_with_templates(tmp_path)
    profile = ProjectProfile(project_name="x")
    install_root = tmp_path / ".grove"
    # Act - compose base only
    plan = compose(profile, ["base"], install_root, packs)
    # Assert - install_root resolved and each file has valid structure
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
    # Arrange - packs without nonexistent id
    packs = _packs_with_templates(tmp_path)
    profile = ProjectProfile()
    install_root = tmp_path / ".grove"
    # Act - compose with nonexistent pack id
    # Assert - ValueError with message about pack not available
    with pytest.raises(ValueError, match=r"Pack id 'nonexistent'.*not available"):
        compose(profile, ["base", "nonexistent"], install_root, packs)


@pytest.mark.unit
def test_compose_empty_selection_empty_files(tmp_path: Path) -> None:
    """Selecting no packs yields no files."""
    # Arrange - packs and profile, empty selection
    packs = _packs_with_templates(tmp_path)
    profile = ProjectProfile()
    install_root = tmp_path / ".grove"
    # Act - compose with no packs selected
    plan = compose(profile, [], install_root, packs)
    # Assert - install_root set and no files
    assert plan.install_root == install_root
    assert plan.files == []


@pytest.mark.unit
def test_compose_base_only_yields_base_templates(tmp_path: Path) -> None:
    """Selecting only base yields base pack files."""
    # Arrange - packs and profile, base only selected
    packs = _packs_with_templates(tmp_path)
    profile = ProjectProfile(project_name="a")
    install_root = tmp_path / ".grove"
    # Act - compose base only
    plan = compose(profile, ["base"], install_root, packs)
    # Assert - all files from base pack, count two
    assert all(f.pack_id == "base" for f in plan.files)
    assert len(plan.files) == 2


@pytest.mark.unit
def test_compose_renders_injected_content_into_target_file(tmp_path: Path) -> None:
    """Compose pre-renders target files that receive injections."""
    # Arrange - pack fixtures with a GROVE target and a python injection
    packs = _packs_with_templates(tmp_path)
    profile = ProjectProfile(project_name="my-app")
    install_root = tmp_path / ".grove"
    # Act - compose the selected packs
    plan = compose(profile, ["base", "python"], install_root, packs)
    grove_file = next(file for file in plan.files if file.dst.name == "GROVE.md")
    index_file = next(file for file in plan.files if file.dst.name == "INDEX.md")
    # Assert - target files contain injected content without managed wrappers
    assert grove_file.rendered_content is not None
    assert index_file.rendered_content is not None
    assert "Injected guidance" in grove_file.rendered_content
    assert "Injected guidance" in index_file.rendered_content
    assert "<!-- grove:managed:" not in grove_file.rendered_content
    assert "### Python Rules" in index_file.rendered_content
    assert "### Python Testing" in index_file.rendered_content
    assert "When to use: Use when editing Python code." in index_file.rendered_content
    assert index_file.rendered_content.index(
        "### Python Rules"
    ) < index_file.rendered_content.index("### Python Testing")
