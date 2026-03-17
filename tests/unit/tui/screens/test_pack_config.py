"""Unit tests for pack_config screen helpers and has_setup_questions."""

from unittest.mock import patch

import pytest

from grove.core.models import PackManifest
from grove.tui.screens.pack_config import (
    _collect_setup_questions,
    _normalize_question,
    _widgets_for_checkbox,
    _widgets_for_question,
    _widgets_for_select,
    has_setup_questions,
)


@pytest.mark.unit
def test_normalize_question_valid_text() -> None:
    """_normalize_question returns dict for valid text question."""
    # Arrange - valid dict with id, prompt, type text
    item = {"id": "q1", "prompt": "Name?", "type": "text"}
    # Act - normalize the question dict
    out = _normalize_question(item, "mypack")
    # Assert - dict has expected keys and type text
    assert out is not None
    assert out["pack_id"] == "mypack"
    assert out["id"] == "q1"
    assert out["prompt"] == "Name?"
    assert out["type"] == "text"
    assert out["options"] == []


@pytest.mark.unit
def test_normalize_question_valid_select_with_options() -> None:
    """_normalize_question returns dict for select with options."""
    # Arrange - select question with options
    item = {"id": "env", "prompt": "Env?", "type": "select", "options": ["dev", "prod"]}
    # Act - normalize the question
    out = _normalize_question(item, "mypack")
    # Assert - type select and options preserved
    assert out is not None
    assert out["type"] == "select"
    assert out["options"] == ["dev", "prod"]


@pytest.mark.unit
def test_normalize_question_valid_checkbox() -> None:
    """_normalize_question returns dict for checkbox type."""
    # Arrange - checkbox question with default
    item = {"id": "opt", "prompt": "Enable?", "type": "checkbox", "default": True}
    # Act - normalize the question
    out = _normalize_question(item, "mypack")
    # Assert - type checkbox and default preserved
    assert out is not None
    assert out["type"] == "checkbox"
    assert out.get("default") is True


@pytest.mark.unit
def test_normalize_question_invalid_not_dict() -> None:
    """_normalize_question returns None when item is not a dict."""
    # Arrange - non-dict item
    # Act - normalize invalid item
    out = _normalize_question("not a dict", "mypack")
    # Assert - returns None
    assert out is None


@pytest.mark.unit
def test_normalize_question_invalid_missing_id() -> None:
    """_normalize_question returns None when id is missing."""
    # Arrange - dict without id
    item = {"prompt": "Name?", "type": "text"}
    # Act - normalize
    out = _normalize_question(item, "mypack")
    # Assert - returns None
    assert out is None


@pytest.mark.unit
def test_normalize_question_invalid_missing_prompt() -> None:
    """_normalize_question returns None when prompt is missing."""
    # Arrange - dict without prompt
    item = {"id": "q1", "type": "text"}
    # Act - normalize
    out = _normalize_question(item, "mypack")
    # Assert - returns None
    assert out is None


@pytest.mark.unit
def test_normalize_question_invalid_type_falls_back_to_text() -> None:
    """_normalize_question uses 'text' when type not in text/select/checkbox."""
    # Arrange - invalid type value
    item = {"id": "q1", "prompt": "X?", "type": "unknown"}
    # Act - normalize
    out = _normalize_question(item, "mypack")
    # Assert - type falls back to text
    assert out is not None
    assert out["type"] == "text"


@pytest.mark.unit
def test_normalize_question_options_not_list_becomes_empty() -> None:
    """_normalize_question uses [] when options is not a list."""
    # Arrange - options not a list
    item = {"id": "q1", "prompt": "X?", "options": "not-a-list"}
    # Act - normalize
    out = _normalize_question(item, "mypack")
    # Assert - options becomes empty list
    assert out is not None
    assert out["options"] == []


@pytest.mark.unit
def test_collect_setup_questions_empty_when_no_packs() -> None:
    """_collect_setup_questions returns [] when discover_packs returns empty."""
    # Arrange - discover_packs returns empty
    with patch("grove.tui.screens.pack_config.discover_packs") as m:
        m.return_value = []
        # Act - collect questions for base and python
        out = _collect_setup_questions(["base", "python"])
        # Assert - result is empty
        assert out == []


@pytest.mark.unit
def test_collect_setup_questions_returns_questions_from_pack() -> None:
    """_collect_setup_questions returns normalized questions from pack contributes."""
    # Arrange - pack with setup_questions
    pack = PackManifest(
        id="testpack",
        name="Test",
        version="0.1.0",
        contributes={
            "setup_questions": [
                {"id": "q1", "prompt": "Name?", "type": "text"},
                {"id": "q2", "prompt": "Env?", "type": "select", "options": ["a", "b"]},
            ]
        },
    )
    with patch("grove.tui.screens.pack_config.discover_packs") as m:
        m.return_value = [pack]
        # Act - collect questions for testpack
        out = _collect_setup_questions(["testpack"])
        # Assert - two questions returned and types correct
        assert len(out) == 2
        assert out[0]["id"] == "q1"
        assert out[0]["type"] == "text"
        assert out[1]["id"] == "q2"
        assert out[1]["type"] == "select"
        assert out[1]["options"] == ["a", "b"]


@pytest.mark.unit
def test_collect_setup_questions_skips_unknown_pack_id() -> None:
    """_collect_setup_questions skips selected ids not in discovered packs."""
    # Arrange - only base pack discovered
    pack = PackManifest(id="base", name="Base", version="0.1.0", contributes={})
    with patch("grove.tui.screens.pack_config.discover_packs") as m:
        m.return_value = [pack]
        # Act - collect for base and nonexistent
        out = _collect_setup_questions(["base", "nonexistent"])
        # Assert - no questions from base so empty
        assert out == []


@pytest.mark.unit
def test_collect_setup_questions_skips_when_not_list() -> None:
    """_collect_setup_questions skips pack when setup_questions is not a list."""
    # Arrange - pack with setup_questions that is not a list
    pack = PackManifest(
        id="x",
        name="X",
        version="0.1.0",
        contributes={"setup_questions": "not-a-list"},
    )
    with patch("grove.tui.screens.pack_config.discover_packs") as m:
        m.return_value = [pack]
        # Act - collect for pack with non-list setup_questions
        out = _collect_setup_questions(["x"])
        # Assert - skipped so empty
        assert out == []


@pytest.mark.unit
def test_collect_setup_questions_returns_empty_on_exception() -> None:
    """_collect_setup_questions returns [] when discover_packs raises."""
    # Arrange - discover_packs raises
    with patch("grove.tui.screens.pack_config.discover_packs") as m:
        m.side_effect = FileNotFoundError()
        # Act - collect when discover fails
        out = _collect_setup_questions(["base"])
        # Assert - returns empty list
        assert out == []


@pytest.mark.unit
def test_widgets_for_checkbox_default_true() -> None:
    """_widgets_for_checkbox uses default True when current is None."""
    # Arrange - checkbox question, no current
    q = {"prompt": "Enable?", "default": True}
    # Act - build checkbox widgets
    widgets = _widgets_for_checkbox(q, "q0", None)
    # Assert - two widgets and switch value True
    assert len(widgets) == 2
    assert widgets[0].value is True


@pytest.mark.unit
def test_widgets_for_checkbox_current_overrides_default() -> None:
    """_widgets_for_checkbox uses current when provided."""
    # Arrange - checkbox with current False
    q = {"prompt": "Enable?", "default": True}
    # Act - build checkbox widgets
    widgets = _widgets_for_checkbox(q, "q0", False)
    # Assert - switch value is False
    assert len(widgets) == 2
    assert widgets[0].value is False


@pytest.mark.unit
def test_widgets_for_select_with_options_returns_select() -> None:
    """_widgets_for_select returns Select widget when options present."""
    # Arrange - select question with options
    q = {"prompt": "Env?", "options": ["dev", "prod"], "default": "dev"}
    # Act - build select widgets
    widgets = _widgets_for_select(q, "q0", None)
    # Assert - Select widget (value requires app context to read)
    assert len(widgets) == 2
    assert widgets[1].__class__.__name__ == "Select"


@pytest.mark.unit
def test_widgets_for_select_without_options_returns_input() -> None:
    """_widgets_for_select returns Input when options empty."""
    # Arrange - select with no options
    q = {"prompt": "Name?", "options": []}
    # Act - build select widgets (falls back to Input)
    widgets = _widgets_for_select(q, "q0", None)
    # Assert - Input widget returned
    assert len(widgets) == 2
    assert widgets[1].__class__.__name__ == "Input"


@pytest.mark.unit
def test_widgets_for_select_current_in_options() -> None:
    """_widgets_for_select uses current when it is in options."""
    # Arrange - select question with options and current value
    q = {"prompt": "Env?", "options": ["dev", "prod"]}
    # Act - build select widgets with current prod
    widgets = _widgets_for_select(q, "q0", "prod")
    # Assert - second widget is Select (value needs app context to read)
    assert len(widgets) == 2
    assert widgets[1].__class__.__name__ == "Select"


@pytest.mark.unit
def test_widgets_for_question_checkbox_branch() -> None:
    """_widgets_for_question returns checkbox widgets for type checkbox."""
    # Arrange - checkbox question dict
    q = {
        "pack_id": "p",
        "id": "c",
        "prompt": "On?",
        "type": "checkbox",
        "default": True,
    }
    # Act - build widgets for question
    widgets = _widgets_for_question(q, 0, {})
    # Assert - Switch and label returned
    assert len(widgets) == 2
    assert widgets[0].__class__.__name__ == "Switch"


@pytest.mark.unit
def test_widgets_for_question_select_branch() -> None:
    """_widgets_for_question returns select widgets for type select with options."""
    # Arrange - select question dict with options
    q = {
        "pack_id": "p",
        "id": "s",
        "prompt": "X?",
        "type": "select",
        "options": ["a"],
    }
    # Act - build widgets for question
    widgets = _widgets_for_question(q, 0, {})
    # Assert - Select widget returned
    assert len(widgets) == 2
    assert widgets[1].__class__.__name__ == "Select"


@pytest.mark.unit
def test_has_setup_questions_true_when_any_pack_has_questions() -> None:
    """has_setup_questions returns True when _collect returns non-empty."""
    # Arrange - pack with setup_questions in contributes
    pack = PackManifest(
        id="x",
        name="X",
        version="0.1.0",
        contributes={"setup_questions": [{"id": "q1", "prompt": "?"}]},
    )
    with patch("grove.tui.screens.pack_config.discover_packs") as m:
        m.return_value = [pack]
        # Act - check if any pack has questions
        result = has_setup_questions(["x"])
        # Assert - True when pack has questions
        assert result is True


@pytest.mark.unit
def test_has_setup_questions_false_when_no_questions() -> None:
    """has_setup_questions returns False when _collect returns empty."""
    # Arrange - pack with no setup_questions
    with patch("grove.tui.screens.pack_config.discover_packs") as m:
        m.return_value = [
            PackManifest(id="base", name="Base", version="0.1.0", contributes={}),
        ]
        # Act - check when no questions
        result = has_setup_questions(["base"])
        # Assert - False
        assert result is False
