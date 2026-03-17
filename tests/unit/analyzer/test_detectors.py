"""Unit tests for each detector: expected facts from config evidence."""

from pathlib import Path

import pytest

from grove.analyzer.detectors.mypy import detect as mypy_detect
from grove.analyzer.detectors.pyproject import detect as pyproject_detect
from grove.analyzer.detectors.pytest import detect as pytest_detect
from grove.analyzer.detectors.ruff import detect as ruff_detect
from grove.analyzer.detectors.uv import detect as uv_detect


@pytest.mark.unit
def test_pyproject_detector_empty_dir(tmp_path: Path) -> None:
    """Pyproject detector returns no facts when pyproject.toml is missing."""
    assert pyproject_detect(tmp_path) == []


@pytest.mark.unit
def test_pyproject_detector_name_and_language(tmp_path: Path) -> None:
    """Pyproject detector returns project_name and language from [project]."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "my-app"\nrequires-python = ">=3.12"\n'
    )
    facts = pyproject_detect(tmp_path)
    keys = [f.key for f in facts]
    assert "project_name" in keys
    assert "language" in keys
    by_key = {f.key: f.value for f in facts}
    assert by_key["project_name"] == "my-app"
    assert by_key["language"] == "python"


@pytest.mark.unit
def test_uv_detector_uv_lock(tmp_path: Path) -> None:
    """UV detector returns package_manager=uv when uv.lock exists."""
    (tmp_path / "uv.lock").write_text("")
    facts = uv_detect(tmp_path)
    assert len(facts) == 1
    assert facts[0].key == "package_manager"
    assert facts[0].value == "uv"


@pytest.mark.unit
def test_uv_detector_tool_uv(tmp_path: Path) -> None:
    """UV detector returns package_manager=uv when [tool.uv] in pyproject.toml."""
    (tmp_path / "pyproject.toml").write_text("[tool.uv]\ndev-dependencies = []\n")
    facts = uv_detect(tmp_path)
    assert len(facts) == 1
    assert facts[0].value == "uv"
    assert "tool.uv" in facts[0].evidence


@pytest.mark.unit
def test_pytest_detector_ini_options(tmp_path: Path) -> None:
    """Pytest detector returns test_framework=pytest when [tool.pytest.ini_options]."""
    (tmp_path / "pyproject.toml").write_text(
        "[tool.pytest.ini_options]\ntestpaths = []\n"
    )
    facts = pytest_detect(tmp_path)
    assert len(facts) == 1
    assert facts[0].key == "test_framework"
    assert facts[0].value == "pytest"


@pytest.mark.unit
def test_pytest_detector_pytest_ini(tmp_path: Path) -> None:
    """Pytest detector returns test_framework=pytest when pytest.ini exists."""
    (tmp_path / "pytest.ini").write_text("[pytest]\n")
    facts = pytest_detect(tmp_path)
    assert len(facts) == 1
    assert facts[0].value == "pytest"


@pytest.mark.unit
def test_ruff_detector_tool_ruff(tmp_path: Path) -> None:
    """Ruff detector returns tools=[ruff] when [tool.ruff] in pyproject.toml."""
    (tmp_path / "pyproject.toml").write_text("[tool.ruff]\nline-length = 88\n")
    facts = ruff_detect(tmp_path)
    assert len(facts) == 1
    assert facts[0].key == "tools"
    assert facts[0].value == ["ruff"]


@pytest.mark.unit
def test_ruff_detector_ruff_toml(tmp_path: Path) -> None:
    """Ruff detector returns tools=[ruff] when .ruff.toml exists."""
    (tmp_path / ".ruff.toml").write_text("line-length = 88\n")
    facts = ruff_detect(tmp_path)
    assert len(facts) == 1
    assert facts[0].value == ["ruff"]


@pytest.mark.unit
def test_mypy_detector_tool_mypy(tmp_path: Path) -> None:
    """Mypy detector returns tools=[mypy] when [tool.mypy] in pyproject.toml."""
    (tmp_path / "pyproject.toml").write_text('[tool.mypy]\npython_version = "3.12"\n')
    facts = mypy_detect(tmp_path)
    assert len(facts) == 1
    assert facts[0].key == "tools"
    assert facts[0].value == ["mypy"]


@pytest.mark.unit
def test_mypy_detector_mypy_ini(tmp_path: Path) -> None:
    """Mypy detector returns tools=[mypy] when mypy.ini exists."""
    (tmp_path / "mypy.ini").write_text("[mypy]\n")
    facts = mypy_detect(tmp_path)
    assert len(facts) == 1
    assert facts[0].value == ["mypy"]


@pytest.mark.unit
def test_pytest_detector_no_evidence_returns_empty(tmp_path: Path) -> None:
    """Pytest detector returns empty when no pytest config or deps."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')
    assert pytest_detect(tmp_path) == []
