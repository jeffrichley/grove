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
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1.0"\n'
    )
    result = _run_grove_init(tmp_path, dry_run=True)
    assert result.returncode == 0, result.stderr
    assert not (tmp_path / ".grove").exists()


@pytest.mark.integration
def test_init_creates_grove_and_manifest(tmp_path: Path) -> None:
    """Grove init creates .grove/, manifest.toml, GROVE.md and manifest lists packs."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0.1.0"\n'
    )
    result = _run_grove_init(tmp_path, dry_run=False)
    assert result.returncode == 0, result.stderr

    grove_dir = tmp_path / ".grove"
    assert grove_dir.is_dir()
    manifest_path = grove_dir / "manifest.toml"
    assert manifest_path.is_file()
    content = manifest_path.read_text()
    assert "[grove]" in content
    assert "[project]" in content
    assert "base" in content
    assert "python" in content

    grove_md = grove_dir / "GROVE.md"
    assert grove_md.is_file()
    assert "GROVE" in grove_md.read_text()
