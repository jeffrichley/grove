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
    # Arrange - empty directory with no pyproject.toml
    # Act - run pyproject detector
    facts = pyproject_detect(tmp_path)
    # Assert - no facts returned
    assert facts == []


@pytest.mark.unit
def test_pyproject_detector_name_and_language(tmp_path: Path) -> None:
    """Pyproject detector returns project_name and language from [project]."""
    # Arrange - pyproject.toml with [project] name and requires-python
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "my-app"\nrequires-python = ">=3.12"\n'
    )
    # Act - run pyproject detector
    facts = pyproject_detect(tmp_path)
    # Assert - project_name and language facts present with expected values
    keys = [f.key for f in facts]
    assert "project_name" in keys
    assert "language" in keys
    by_key = {f.key: f.value for f in facts}
    assert by_key["project_name"] == "my-app"
    assert by_key["language"] == "python"


@pytest.mark.unit
def test_uv_detector_uv_lock(tmp_path: Path) -> None:
    """UV detector returns package_manager=uv when uv.lock exists."""
    # Arrange - directory containing uv.lock
    (tmp_path / "uv.lock").write_text("")
    # Act - run uv detector
    facts = uv_detect(tmp_path)
    # Assert - single fact package_manager=uv
    assert len(facts) == 1
    assert facts[0].key == "package_manager"
    assert facts[0].value == "uv"


@pytest.mark.unit
def test_uv_detector_tool_uv(tmp_path: Path) -> None:
    """UV detector returns package_manager=uv when [tool.uv] in pyproject.toml."""
    # Arrange - pyproject.toml with [tool.uv]
    (tmp_path / "pyproject.toml").write_text("[tool.uv]\ndev-dependencies = []\n")
    # Act - run uv detector
    facts = uv_detect(tmp_path)
    # Assert - package_manager=uv with tool.uv evidence
    assert len(facts) == 1
    assert facts[0].value == "uv"
    assert "tool.uv" in facts[0].evidence


@pytest.mark.unit
def test_pytest_detector_ini_options(tmp_path: Path) -> None:
    """Pytest detector returns test_framework=pytest when [tool.pytest.ini_options]."""
    # Arrange - pyproject.toml with [tool.pytest.ini_options]
    (tmp_path / "pyproject.toml").write_text(
        "[tool.pytest.ini_options]\ntestpaths = []\n"
    )
    # Act - run pytest detector
    facts = pytest_detect(tmp_path)
    # Assert - test_framework=pytest fact
    assert len(facts) == 1
    assert facts[0].key == "test_framework"
    assert facts[0].value == "pytest"


@pytest.mark.unit
def test_pytest_detector_pytest_ini(tmp_path: Path) -> None:
    """Pytest detector returns test_framework=pytest when pytest.ini exists."""
    # Arrange - pytest.ini present
    (tmp_path / "pytest.ini").write_text("[pytest]\n")
    # Act - run pytest detector
    facts = pytest_detect(tmp_path)
    # Assert - test_framework=pytest
    assert len(facts) == 1
    assert facts[0].value == "pytest"


@pytest.mark.unit
def test_ruff_detector_tool_ruff(tmp_path: Path) -> None:
    """Ruff detector returns tools=[ruff] when [tool.ruff] in pyproject.toml."""
    # Arrange - pyproject.toml with [tool.ruff]
    (tmp_path / "pyproject.toml").write_text("[tool.ruff]\nline-length = 88\n")
    # Act - run ruff detector
    facts = ruff_detect(tmp_path)
    # Assert - tools=[ruff] fact
    assert len(facts) == 1
    assert facts[0].key == "tools"
    assert facts[0].value == ["ruff"]


@pytest.mark.unit
def test_ruff_detector_ruff_toml(tmp_path: Path) -> None:
    """Ruff detector returns tools=[ruff] when .ruff.toml exists."""
    # Arrange - .ruff.toml present
    (tmp_path / ".ruff.toml").write_text("line-length = 88\n")
    # Act - run ruff detector
    facts = ruff_detect(tmp_path)
    # Assert - tools=[ruff]
    assert len(facts) == 1
    assert facts[0].value == ["ruff"]


@pytest.mark.unit
def test_mypy_detector_tool_mypy(tmp_path: Path) -> None:
    """Mypy detector returns tools=[mypy] when [tool.mypy] in pyproject.toml."""
    # Arrange - pyproject.toml with [tool.mypy]
    (tmp_path / "pyproject.toml").write_text('[tool.mypy]\npython_version = "3.12"\n')
    # Act - run mypy detector
    facts = mypy_detect(tmp_path)
    # Assert - tools=[mypy] fact
    assert len(facts) == 1
    assert facts[0].key == "tools"
    assert facts[0].value == ["mypy"]


@pytest.mark.unit
def test_mypy_detector_mypy_ini(tmp_path: Path) -> None:
    """Mypy detector returns tools=[mypy] when mypy.ini exists."""
    # Arrange - mypy.ini present
    (tmp_path / "mypy.ini").write_text("[mypy]\n")
    # Act - run mypy detector
    facts = mypy_detect(tmp_path)
    # Assert - tools=[mypy]
    assert len(facts) == 1
    assert facts[0].value == ["mypy"]


@pytest.mark.unit
def test_pytest_detector_no_evidence_returns_empty(tmp_path: Path) -> None:
    """Pytest detector returns empty when no pytest config or deps."""
    # Arrange - pyproject.toml without pytest config
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')
    # Act - run pytest detector
    facts = pytest_detect(tmp_path)
    # Assert - no facts
    assert facts == []
