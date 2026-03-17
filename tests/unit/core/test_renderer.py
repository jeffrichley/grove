"""Unit tests for grove.core.renderer."""

from pathlib import Path

import pytest
from jinja2 import UndefinedError

from grove.core.renderer import render


@pytest.mark.unit
def test_render_substitutes_variables(tmp_path: Path) -> None:
    """Renderer produces expected content with variable substitution."""
    template_path = tmp_path / "hello.j2"
    template_path.write_text("Hello {{ name }}!")
    out = render(template_path, {"name": "World"})
    assert out == "Hello World!"


@pytest.mark.unit
def test_render_with_conditional(tmp_path: Path) -> None:
    """Renderer handles conditionals and filters."""
    template_path = tmp_path / "cond.j2"
    template_path.write_text("{% if show %}yes{% else %}no{% endif %}")
    assert render(template_path, {"show": True}) == "yes"
    assert render(template_path, {"show": False}) == "no"


@pytest.mark.unit
def test_render_missing_variable_raises(tmp_path: Path) -> None:
    """Missing variable in template raises (no silent fallback)."""
    template_path = tmp_path / "missing.j2"
    template_path.write_text("Hi {{ missing_var }}")
    with pytest.raises(UndefinedError):
        render(template_path, {})


@pytest.mark.unit
def test_render_template_not_found_raises(tmp_path: Path) -> None:
    """Nonexistent template path raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="Template not found"):
        render(tmp_path / "nonexistent.j2", {})
