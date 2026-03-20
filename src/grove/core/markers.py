"""Helpers for Grove anchor, managed-block, and user-region markers."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class MarkerRange:
    """One paired marker range in a document."""

    name: str
    start: int
    end: int
    start_token: str
    end_token: str


_ANCHOR_RE = re.compile(r"<!--\s*grove:anchor:([^:]+):(start|end)\s*-->")
_MANAGED_RE = re.compile(r"<!--\s*grove:managed:([^:]+):(start|end)\s*-->")
_USER_RE = re.compile(r"<!--\s*grove:user:([^:]+):(start|end)\s*-->")


def anchor_start(name: str) -> str:
    """Return the canonical anchor start marker.

    Args:
        name: Anchor identifier.

    Returns:
        Canonical anchor start marker string.
    """
    return f"<!-- grove:anchor:{name}:start -->"


def anchor_end(name: str) -> str:
    """Return the canonical anchor end marker.

    Args:
        name: Anchor identifier.

    Returns:
        Canonical anchor end marker string.
    """
    return f"<!-- grove:anchor:{name}:end -->"


def managed_start(injection_id: str) -> str:
    """Return the canonical managed-block start marker.

    Args:
        injection_id: Managed injection identifier.

    Returns:
        Canonical managed-block start marker string.
    """
    return f"<!-- grove:managed:{injection_id}:start -->"


def managed_end(injection_id: str) -> str:
    """Return the canonical managed-block end marker.

    Args:
        injection_id: Managed injection identifier.

    Returns:
        Canonical managed-block end marker string.
    """
    return f"<!-- grove:managed:{injection_id}:end -->"


def user_start(region_id: str) -> str:
    """Return the canonical user-region start marker.

    Args:
        region_id: User region identifier.

    Returns:
        Canonical user-region start marker string.
    """
    return f"<!-- grove:user:{region_id}:start -->"


def user_end(region_id: str) -> str:
    """Return the canonical user-region end marker.

    Args:
        region_id: User region identifier.

    Returns:
        Canonical user-region end marker string.
    """
    return f"<!-- grove:user:{region_id}:end -->"


def find_anchor_ranges(content: str) -> dict[str, MarkerRange]:
    """Return anchor ranges keyed by anchor name.

    Args:
        content: Document text to inspect.

    Returns:
        Anchor marker ranges keyed by anchor name.
    """
    return _find_marker_ranges(content, _ANCHOR_RE, "anchor")


def find_managed_blocks(content: str) -> dict[str, MarkerRange]:
    """Return managed-block ranges keyed by injection id.

    Args:
        content: Document text to inspect.

    Returns:
        Managed-block ranges keyed by injection id.
    """
    return _find_marker_ranges(content, _MANAGED_RE, "managed")


def find_user_regions(content: str) -> dict[str, MarkerRange]:
    """Return user-region ranges keyed by region id.

    Args:
        content: Document text to inspect.

    Returns:
        User-region ranges keyed by region id.
    """
    return _find_marker_ranges(content, _USER_RE, "user")


def _find_marker_ranges(
    content: str,
    pattern: re.Pattern[str],
    label: str,
) -> dict[str, MarkerRange]:
    """Parse paired marker ranges with strict pairing rules.

    Args:
        content: Document text to inspect.
        pattern: Regex that matches start and end markers.
        label: Marker label used in validation errors.

    Returns:
        Marker ranges keyed by marker name.
    """
    ranges: dict[str, MarkerRange] = {}
    open_ranges: dict[str, tuple[int, str]] = {}
    for match in pattern.finditer(content):
        name = match.group(1)
        kind = match.group(2)
        token = match.group(0)
        if kind == "start":
            if name in open_ranges:
                raise ValueError(f"Duplicate {label} start marker for '{name}'")
            open_ranges[name] = (match.start(), token)
            continue
        start_data = open_ranges.pop(name, None)
        if start_data is None:
            raise ValueError(f"{label.title()} end marker without start for '{name}'")
        start_index, start_token = start_data
        ranges[name] = MarkerRange(
            name=name,
            start=start_index,
            end=match.end(),
            start_token=start_token,
            end_token=token,
        )
    if open_ranges:
        missing = ", ".join(sorted(open_ranges))
        raise ValueError(f"Unclosed {label} marker(s): {missing}")
    return ranges
