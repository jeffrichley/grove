"""Unit tests for grove.core.injections."""

import pytest

from grove.core.injections import RenderedInjection, assemble_injections


@pytest.mark.unit
def test_assemble_injections_replaces_anchor_body() -> None:
    """Anchor bodies are rebuilt from ordered rendered injections."""
    # Arrange - a base document with one anchor and one rendered injection
    base = (
        "# GROVE\n"
        "<!-- grove:anchor:guidance:start -->"
        "old body"
        "<!-- grove:anchor:guidance:end -->\n"
    )
    # Act - assemble the rendered injection into the anchor
    result = assemble_injections(
        base,
        [
            RenderedInjection(
                id="python-guidance",
                anchor="guidance",
                order=0,
                content="Python guidance",
            )
        ],
    )
    # Assert - the anchor body is replaced without managed wrapper markers
    assert "old body" not in result
    assert "Python guidance" in result
    assert "<!-- grove:managed:" not in result
    assert (
        "<!-- grove:anchor:guidance:start -->\n"
        "Python guidance\n"
        "<!-- grove:anchor:guidance:end -->"
    ) in result
    assert "<!-- grove:anchor:guidance:end -->" in result


@pytest.mark.unit
def test_assemble_injections_orders_by_order_then_id() -> None:
    """Injection ordering is deterministic for the same inputs."""
    # Arrange - injections with mixed order and id values
    base = "<!-- grove:anchor:guidance:start --><!-- grove:anchor:guidance:end -->"
    # Act - assemble the injections
    result = assemble_injections(
        base,
        [
            RenderedInjection(id="b", anchor="guidance", order=1, content="B"),
            RenderedInjection(id="a", anchor="guidance", order=1, content="A"),
            RenderedInjection(id="c", anchor="guidance", order=0, content="C"),
        ],
    )
    # Assert - ordering follows order first, id second
    assert result.index("C") < result.index("A") < result.index("B")
    assert "<!-- grove:anchor:guidance:start -->\n" in result
    assert "\n<!-- grove:anchor:guidance:end -->" in result


@pytest.mark.unit
def test_assemble_injections_separates_multiple_entries_with_blank_lines() -> None:
    """Multiple injections within one anchor are separated cleanly."""
    # Arrange - one anchor receiving two ordered injections
    base = "<!-- grove:anchor:guidance:start --><!-- grove:anchor:guidance:end -->"
    # Act - assemble both entries into the same anchor body
    result = assemble_injections(
        base,
        [
            RenderedInjection(id="a", anchor="guidance", order=0, content="First"),
            RenderedInjection(id="b", anchor="guidance", order=1, content="Second"),
        ],
    )
    # Assert - markers and injected entries are separated by line boundaries
    assert (
        "<!-- grove:anchor:guidance:start -->\n"
        "First\n\n"
        "Second\n"
        "<!-- grove:anchor:guidance:end -->"
    ) in result


@pytest.mark.unit
def test_assemble_injections_rejects_duplicate_ids() -> None:
    """Duplicate injection ids fail fast."""
    # Arrange - duplicate ids targeting the same anchor
    base = "<!-- grove:anchor:guidance:start --><!-- grove:anchor:guidance:end -->"
    # Act - assemble injections with duplicate ids
    # Assert - assembly fails before writing ambiguous output
    with pytest.raises(ValueError, match="Duplicate injection id"):
        assemble_injections(
            base,
            [
                RenderedInjection(id="dup", anchor="guidance", order=0, content="A"),
                RenderedInjection(id="dup", anchor="guidance", order=1, content="B"),
            ],
        )


@pytest.mark.unit
def test_assemble_injections_rejects_missing_anchor() -> None:
    """Missing target anchors raise a clear error."""
    # Arrange - a target document with no matching anchor
    # Act - assemble an injection into the target document
    # Assert - assembly fails with the missing anchor name
    with pytest.raises(ValueError, match="Missing anchor 'guidance'"):
        assemble_injections(
            "# GROVE",
            [RenderedInjection(id="py", anchor="guidance", order=0, content="A")],
        )


@pytest.mark.unit
def test_assemble_injections_keeps_empty_anchor_markers_on_separate_lines() -> None:
    """Empty anchors retain line separation between start and end markers."""
    # Arrange - a base document with one populated and one empty anchor
    base = (
        "# GROVE\n"
        "<!-- grove:anchor:guidance:start -->"
        "old guidance"
        "<!-- grove:anchor:guidance:end -->\n"
        "<!-- grove:anchor:commands:start -->"
        "old commands"
        "<!-- grove:anchor:commands:end -->\n"
    )
    # Act - rebuild the document while leaving one anchor without injections
    result = assemble_injections(
        base,
        [
            RenderedInjection(
                id="guidance",
                anchor="guidance",
                order=0,
                content="New guidance",
            )
        ],
    )
    # Assert - the untouched anchor is normalized to separate marker lines
    assert (
        "<!-- grove:anchor:commands:start -->\n<!-- grove:anchor:commands:end -->"
    ) in result
