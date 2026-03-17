"""E2E tests: full grove init TUI flow in headless mode (Textual run_test + Pilot)."""

from pathlib import Path

import pytest

from grove.tui import GroveInitApp
from grove.tui.state import SetupState


@pytest.mark.e2e
async def test_init_tui_full_flow_headless(tmp_path: Path) -> None:
    """Drive full TUI flow via Pilot; assert .grove/ and manifest created.

    Uses Textual's run_test() (headless) and Pilot to simulate Enter key
    through Welcome -> Analysis -> Core install -> Recommended packs ->
    Pack config -> Components preview -> Final review -> Apply -> Finish -> Done.
    """
    # Arrange - project root with pyproject so analyzer finds a project
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1.0"\n'
    )
    state = SetupState(root=tmp_path)
    app = GroveInitApp(state)
    # Act - run app headless and drive flow with Enter (Next / Continue / Apply / Done)
    async with app.run_test() as pilot:
        await pilot.pause()  # let Welcome mount
        # Welcome -> Analysis
        await pilot.press("enter")
        await pilot.pause()  # let Analysis run analyzer and mount
        # Analysis -> Core install
        await pilot.press("enter")
        await pilot.pause()
        # Core install -> Recommended packs
        await pilot.press("enter")
        await pilot.pause()
        # Recommended packs -> Pack config or Components
        await pilot.press("enter")
        await pilot.pause()
        # Pack config -> Components (or we're already at Components)
        await pilot.press("enter")
        await pilot.pause()  # let compose() run and plan populate
        # Components -> Final review (or Conflicts; empty repo has no conflicts)
        await pilot.press("enter")
        await pilot.pause()
        # Final review -> Apply installation
        await pilot.press("enter")
        await pilot.pause()  # apply runs, then Finish screen pushes
        # Finish -> Done (exit)
        await pilot.press("enter")
    # Assert - install completed
    grove_dir = tmp_path / ".grove"
    manifest_path = grove_dir / "manifest.toml"
    assert grove_dir.is_dir(), "Expected .grove/ directory"
    assert manifest_path.is_file(), "Expected manifest.toml"
    content = manifest_path.read_text()
    assert "[grove]" in content
    assert "base" in content
