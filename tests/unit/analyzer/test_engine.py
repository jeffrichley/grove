"""Unit tests for analyzer engine: merge detectors into ProjectProfile."""

from pathlib import Path

import pytest

from grove.analyzer.engine import analyze
from grove.core.models import ProjectProfile


@pytest.mark.unit
def test_analyze_empty_dir_minimal_profile(tmp_path: Path) -> None:
    """analyze() on empty dir returns minimal profile with project_root set."""
    profile = analyze(tmp_path)
    assert isinstance(profile, ProjectProfile)
    assert profile.project_root == tmp_path.resolve()
    assert profile.project_name == ""
    assert profile.language == ""
    assert profile.package_manager == ""
    assert profile.test_framework == ""
    assert profile.tools == []


@pytest.mark.unit
def test_analyze_pyproject_toml_returns_python_and_name(tmp_path: Path) -> None:
    """analyze() on dir with pyproject.toml [project] returns language and name."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "my-pkg"\nrequires-python = ">=3.12"\n'
    )
    profile = analyze(tmp_path)
    assert profile.project_name == "my-pkg"
    assert profile.language == "python"
    assert profile.project_root == tmp_path.resolve()


@pytest.mark.unit
def test_analyze_pyproject_and_uv_returns_uv(tmp_path: Path) -> None:
    """analyze() with pyproject.toml + uv.lock returns package_manager=uv."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "p"\nrequires-python = ">=3.12"\n'
    )
    (tmp_path / "uv.lock").write_text("")
    profile = analyze(tmp_path)
    assert profile.language == "python"
    assert profile.package_manager == "uv"


@pytest.mark.unit
def test_analyze_optional_pytest_ruff_mypy_from_config(tmp_path: Path) -> None:
    """analyze() with [tool.pytest], [tool.ruff], [tool.mypy] populates profile."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "p"\nrequires-python = ">=3.12"\n\n'
        '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n\n'
        "[tool.ruff]\nline-length = 88\n\n"
        '[tool.mypy]\npython_version = "3.12"\n'
    )
    profile = analyze(tmp_path)
    assert profile.test_framework == "pytest"
    assert "ruff" in profile.tools
    assert "mypy" in profile.tools


@pytest.mark.unit
def test_analyze_no_optional_tools_without_config(tmp_path: Path) -> None:
    """analyze() does not set test_framework or tools when no config evidence."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "p"\nrequires-python = ">=3.12"\n'
    )
    profile = analyze(tmp_path)
    assert profile.test_framework == ""
    assert profile.tools == []
