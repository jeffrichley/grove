"""Anchor-based injection assembly for composed Grove documents."""

from dataclasses import dataclass

from grove.core.markers import MarkerRange, find_anchor_ranges


@dataclass(frozen=True)
class RenderedInjection:
    """A rendered snippet ready to be inserted into a target anchor."""

    id: str
    anchor: str
    order: int
    content: str


def order_injections(injections: list[RenderedInjection]) -> list[RenderedInjection]:
    """Return injections in deterministic order.

    Args:
        injections: Rendered injections for one or more anchors.

    Returns:
        Injections sorted by order then id.
    """
    return sorted(injections, key=lambda item: (item.order, item.id))


def assemble_injections(
    base_content: str,
    injections: list[RenderedInjection],
) -> str:
    """Insert managed blocks into matching anchors in a rendered base document.

    Args:
        base_content: Rendered base document with anchor markers.
        injections: Rendered injections to insert into anchors.

    Returns:
        Document content with managed blocks inserted into matching anchors.
    """
    if not injections:
        return base_content
    anchors = find_anchor_ranges(base_content)
    by_anchor: dict[str, list[RenderedInjection]] = {}
    ids: set[str] = set()
    for injection in injections:
        if injection.id in ids:
            raise ValueError(f"Duplicate injection id: {injection.id}")
        ids.add(injection.id)
        if injection.anchor not in anchors:
            raise ValueError(
                f"Missing anchor '{injection.anchor}' for injection '{injection.id}'"
            )
        by_anchor.setdefault(injection.anchor, []).append(injection)

    output = base_content
    for anchor_name, anchor_range in sorted(
        anchors.items(), key=lambda item: item[1].start, reverse=True
    ):
        rendered = by_anchor.get(anchor_name, [])
        insertion = _render_anchor_body(rendered)
        body_start = _body_start(anchor_range)
        body_end = _body_end(anchor_range)
        output = f"{output[:body_start]}{insertion}{output[body_end:]}"
    return output


def _render_anchor_body(injections: list[RenderedInjection]) -> str:
    """Render the full replacement body for a single anchor.

    Args:
        injections: Rendered injections targeting one anchor.

    Returns:
        Anchor body content ready to place inside the anchor range.
    """
    if not injections:
        return "\n"
    body = "\n\n".join(
        injection.content.strip() for injection in order_injections(injections)
    ).strip()
    if not body:
        return "\n"
    return f"\n{body}\n"


def _body_start(marker_range: MarkerRange) -> int:
    """Return the string offset immediately after a marker range start token.

    Args:
        marker_range: Parsed marker range.

    Returns:
        Offset immediately after the start token.
    """
    return marker_range.start + len(marker_range.start_token)


def _body_end(marker_range: MarkerRange) -> int:
    """Return the string offset immediately before a marker range end token.

    Args:
        marker_range: Parsed marker range.

    Returns:
        Offset immediately before the end token.
    """
    return marker_range.end - len(marker_range.end_token)
