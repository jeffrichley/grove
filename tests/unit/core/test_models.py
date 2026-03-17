"""Unit tests for grove.core.models."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from grove.core.models import (
    GeneratedFileRecord,
    GroveSection,
    InstalledPackRecord,
    InstallPlan,
    ManifestState,
    PackManifest,
    PlannedFile,
    ProjectProfile,
    ProjectSection,
)


@pytest.mark.unit
class TestPackManifest:
    """PackManifest validation and serialization."""

    def test_minimal_valid(self) -> None:
        """Minimal valid PackManifest (id, name, version)."""
        m = PackManifest(id="base", name="Base Pack", version="0.1.0")
        assert m.id == "base"
        assert m.name == "Base Pack"
        assert m.version == "0.1.0"
        assert m.depends_on == []
        assert m.contributes == {}

    def test_full_valid(self) -> None:
        """PackManifest with depends_on and contributes."""
        m = PackManifest(
            id="python",
            name="Python Pack",
            version="0.1.0",
            depends_on=["base"],
            compatible_with=["python"],
            contributes={"templates": ["GROVE.md.j2"]},
        )
        assert m.depends_on == ["base"]
        assert m.contributes["templates"] == ["GROVE.md.j2"]

    def test_missing_id_invalid(self) -> None:
        """Missing required id raises ValidationError."""
        with pytest.raises(ValidationError):
            PackManifest(name="X", version="0.1.0")  # type: ignore[call-arg]


@pytest.mark.unit
class TestProjectProfile:
    """ProjectProfile validation and defaults."""

    def test_defaults(self) -> None:
        """ProjectProfile has sensible defaults."""
        p = ProjectProfile()
        assert p.project_name == ""
        assert p.language == ""
        assert p.project_root == Path(".")
        assert p.raw == {}

    def test_serialization_round_trip(self) -> None:
        """ProjectProfile can be serialized and re-created."""
        p = ProjectProfile(
            project_name="my-app",
            project_root=Path("/repo"),
            language="python",
            package_manager="uv",
            test_framework="pytest",
            tools=["ruff", "mypy"],
        )
        data = p.model_dump(mode="json")
        assert Path(data["project_root"]) == Path("/repo")
        p2 = ProjectProfile.model_validate(data)
        assert p2.project_name == p.project_name
        assert p2.project_root == Path("/repo")


@pytest.mark.unit
class TestPlannedFileAndInstallPlan:
    """PlannedFile and InstallPlan serialization."""

    def test_planned_file_serialization(self) -> None:
        """PlannedFile serializes src/dst as paths and round-trips."""
        pf = PlannedFile(
            src=Path("templates/GROVE.md.j2"),
            dst=Path(".grove/GROVE.md"),
            variables={"project_name": "foo"},
            managed=True,
        )
        data = pf.model_dump(mode="json")
        assert Path(data["src"]) == Path("templates/GROVE.md.j2")
        assert Path(data["dst"]) == Path(".grove/GROVE.md")
        pf2 = PlannedFile.model_validate(data)
        assert pf2.src == pf.src
        assert pf2.dst == pf.dst

    def test_install_plan_serialization(self) -> None:
        """InstallPlan round-trips with list of PlannedFile."""
        plan = InstallPlan(
            install_root=Path(".grove"),
            files=[
                PlannedFile(src=Path("a.j2"), dst=Path(".grove/a")),
                PlannedFile(
                    src=Path("b.j2"), dst=Path(".grove/b"), variables={"x": "y"}
                ),
            ],
        )
        data = plan.model_dump(mode="json")
        assert len(data["files"]) == 2
        plan2 = InstallPlan.model_validate(data)
        assert plan2.install_root == Path(".grove")
        assert len(plan2.files) == 2
        assert plan2.files[1].variables == {"x": "y"}


@pytest.mark.unit
class TestManifestState:
    """ManifestState (manifest.toml shape) validation."""

    def test_valid_minimal(self) -> None:
        """Minimal valid ManifestState."""
        state = ManifestState(
            grove=GroveSection(version="0.1.0", schema_version=1),
            project=ProjectSection(root="/repo", analysis_summary=""),
        )
        assert state.grove.version == "0.1.0"
        assert state.installed_packs == []
        assert state.generated_files == []

    def test_valid_full(self) -> None:
        """ManifestState with packs and generated_files."""
        state = ManifestState(
            grove=GroveSection(version="0.1.0", schema_version=1),
            project=ProjectSection(root="/repo", analysis_summary="Python, uv"),
            installed_packs=[
                InstalledPackRecord(id="base", version="0.1.0"),
                InstalledPackRecord(id="python", version="0.1.0"),
            ],
            generated_files=[
                GeneratedFileRecord(path="GROVE.md", pack_id="base"),
                GeneratedFileRecord(path="rules/python.md", pack_id="python"),
            ],
        )
        assert len(state.installed_packs) == 2
        assert state.installed_packs[0].id == "base"
        assert len(state.generated_files) == 2

    def test_invalid_missing_grove(self) -> None:
        """ManifestState requires grove section."""
        with pytest.raises(ValidationError):
            ManifestState(project=ProjectSection(root="/repo", analysis_summary=""))  # type: ignore[call-arg]

    def test_invalid_missing_project(self) -> None:
        """ManifestState requires project section."""
        with pytest.raises(ValidationError):
            ManifestState(grove=GroveSection(version="0.1.0", schema_version=1))  # type: ignore[call-arg]
