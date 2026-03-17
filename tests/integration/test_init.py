"""Integration tests: grove init CLI end-to-end."""

import subprocess
import sys
from pathlib import Path

import pytest


def _run_grove_init(
    root: Path, dry_run: bool = False
) -> subprocess.CompletedProcess[str]:
    """Run grove init --root <root> [--dry-run] using current interpreter."""
    args = [
        sys.executable,
        "-m",
        "grove.cli.app",
        "init",
        "--root",
        str(root),
    ]
    if dry_run:
        args.append("--dry-run")
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.integration
def test_init_dry_run_does_not_create_grove_dir(tmp_path: Path) -> None:
    """--dry-run exits 0 and does not create .grove/."""
    # Arrange - project with pyproject.toml
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1.0"\n'
    )
    # Act - grove init --dry-run
    result = _run_grove_init(tmp_path, dry_run=True)
    # Assert - success and no .grove directory
    assert result.returncode == 0, result.stderr
    assert not (tmp_path / ".grove").exists()


@pytest.mark.integration
def test_init_creates_grove_and_manifest(tmp_path: Path) -> None:
    """Grove init creates .grove/, manifest.toml, GROVE.md and manifest lists packs."""
    # Arrange - project with pyproject.toml
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1.0"\n'
    )
    # Act - grove init
    result = _run_grove_init(tmp_path, dry_run=False)
    grove_dir = tmp_path / ".grove"
    manifest_path = grove_dir / "manifest.toml"
    content = manifest_path.read_text() if manifest_path.exists() else ""
    grove_md = grove_dir / "GROVE.md"
    # Assert - exit 0, .grove dir, manifest with sections and packs, GROVE.md
    assert result.returncode == 0, result.stderr
    assert grove_dir.is_dir()
    assert manifest_path.is_file()
    assert "[grove]" in content
    assert "[project]" in content
    assert "base" in content
    assert "python" in content
    assert grove_md.is_file()
    assert "GROVE" in grove_md.read_text()
