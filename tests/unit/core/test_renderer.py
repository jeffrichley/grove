"""Unit tests for grove.core.renderer."""

from pathlib import Path

import pytest
from jinja2 import UndefinedError

from grove.core.renderer import render


@pytest.mark.unit
def test_render_substitutes_variables(tmp_path: Path) -> None:
    """Renderer produces expected content with variable substitution."""
    # Arrange - template with name variable and context
    template_path = tmp_path / "hello.j2"
    template_path.write_text("Hello {{ name }}!")
    # Act - render with variables
    out = render(template_path, {"name": "World"})
    # Assert - substituted output
    assert out == "Hello World!"


@pytest.mark.unit
def test_render_with_conditional(tmp_path: Path) -> None:
    """Renderer handles conditionals and filters."""
    # Arrange - template with if/else on show
    template_path = tmp_path / "cond.j2"
    template_path.write_text("{% if show %}yes{% else %}no{% endif %}")
    # Act - render with show True and False
    out_yes = render(template_path, {"show": True})
    out_no = render(template_path, {"show": False})
    # Assert - yes and no respectively
    assert out_yes == "yes"
    assert out_no == "no"


@pytest.mark.unit
def test_render_missing_variable_raises(tmp_path: Path) -> None:
    """Missing variable in template raises (no silent fallback)."""
    # Arrange - template referencing missing variable, empty context
    template_path = tmp_path / "missing.j2"
    template_path.write_text("Hi {{ missing_var }}")
    # Act - render
    # Assert - UndefinedError
    with pytest.raises(UndefinedError):
        render(template_path, {})


@pytest.mark.unit
def test_render_template_not_found_raises(tmp_path: Path) -> None:
    """Nonexistent template path raises FileNotFoundError."""
    # Arrange - path to non-existent template
    # Act - render
    # Assert - FileNotFoundError
    with pytest.raises(FileNotFoundError, match="Template not found"):
        render(tmp_path / "nonexistent.j2", {})
