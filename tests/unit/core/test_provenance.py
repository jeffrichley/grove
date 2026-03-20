"""Unit tests for provenance mapping in composed Grove files."""

from pathlib import Path

import pytest

from grove.core.composer import compose
from grove.core.models import ProjectProfile
from grove.core.registry import discover_packs


def _packs_with_anchor_injections(tmp_path: Path) -> list:
    """Create minimal packs that exercise ordered anchor provenance."""
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    (base_dir / "pack.toml").write_text(
        'id = "base"\nname = "Base"\nversion = "0.1.0"\n'
        "[contributes]\n"
        'templates = ["GROVE.md.j2"]\n'
    )
    (base_dir / "GROVE.md.j2").write_text(
        "<!-- grove:anchor:guidance:start --><!-- grove:anchor:guidance:end -->\n"
        "<!-- grove:anchor:commands:start --><!-- grove:anchor:commands:end -->\n"
    )

    python_dir = tmp_path / "python"
    python_dir.mkdir()
    (python_dir / "pack.toml").write_text(
        'id = "python"\nname = "Python"\nversion = "0.1.0"\ndepends_on = ["base"]\n'
        "[contributes]\n"
        "[[contributes.injections]]\n"
        'id = "python-guidance"\n'
        'anchor = "guidance"\n'
        'content = "Python guidance"\n'
        "order = 20\n"
        "[[contributes.injections]]\n"
        'id = "python-commands"\n'
        'anchor = "commands"\n'
        'content = "Python commands"\n'
        "order = 10\n"
        "[[contributes.injections]]\n"
        'id = "python-guidance-early"\n'
        'anchor = "guidance"\n'
        'content = "Early guidance"\n'
        "order = 10\n"
    )
    return discover_packs(builtins_dir=tmp_path)


@pytest.mark.unit
def test_compose_records_anchor_provenance_by_anchor_and_order(tmp_path: Path) -> None:
    """Compose stores deterministic provenance entries for each changed anchor."""
    # Arrange - minimal packs with multiple ordered injections targeting anchors
    packs = _packs_with_anchor_injections(tmp_path)
    # Act - compose the Grove plan and inspect the composed base file
    plan = compose(
        ProjectProfile(project_name="fixture"),
        ["base", "python"],
        tmp_path / ".grove",
        packs,
    )

    grove_file = next(file for file in plan.files if file.dst.name == "GROVE.md")

    # Assert - per-anchor provenance preserves deterministic ordering and owner ids
    assert [item.injection_id for item in grove_file.anchor_provenance["guidance"]] == [
        "python-guidance-early",
        "python-guidance",
    ]
    assert [item.pack_id for item in grove_file.anchor_provenance["guidance"]] == [
        "python",
        "python",
    ]
    assert [item.injection_id for item in grove_file.anchor_provenance["commands"]] == [
        "python-commands"
    ]
