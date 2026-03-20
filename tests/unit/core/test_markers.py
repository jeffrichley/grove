"""Unit tests for grove.core.markers."""

import pytest

from grove.core.markers import (
    find_anchor_ranges,
    find_user_regions,
)


@pytest.mark.unit
def test_find_anchor_ranges_returns_named_pairs() -> None:
    """Anchor parsing returns the expected range for a valid pair."""
    # Arrange - content with one valid anchor pair
    content = (
        "before\n"
        "<!-- grove:anchor:guidance:start -->x"
        "<!-- grove:anchor:guidance:end -->\n"
        "after"
    )
    # Act - parse the anchors
    ranges = find_anchor_ranges(content)
    # Assert - the parsed marker pair matches the content
    assert list(ranges) == ["guidance"]
    assert ranges["guidance"].start_token == "<!-- grove:anchor:guidance:start -->"
    assert ranges["guidance"].end_token == "<!-- grove:anchor:guidance:end -->"


@pytest.mark.unit
def test_find_anchor_ranges_rejects_missing_end() -> None:
    """Unclosed anchor markers raise a clear error."""
    # Arrange - content with a missing anchor end marker
    content = "<!-- grove:anchor:guidance:start -->"
    # Act - parse the invalid anchor content
    # Assert - parsing fails with a clear error
    with pytest.raises(ValueError, match="Unclosed anchor marker"):
        find_anchor_ranges(content)


@pytest.mark.unit
def test_find_user_regions_rejects_duplicate_start() -> None:
    """User regions cannot open the same region twice."""
    # Arrange - content with duplicate user-region start markers
    content = (
        "<!-- grove:user:notes:start -->"
        "<!-- grove:user:notes:start -->"
        "<!-- grove:user:notes:end -->"
    )
    # Act - parse the invalid user-region content
    # Assert - parsing fails with a clear error
    with pytest.raises(ValueError, match="Duplicate user start marker"):
        find_user_regions(content)
