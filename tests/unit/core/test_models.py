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
        # Arrange - minimal required fields
        # Act - construct PackManifest
        m = PackManifest(id="base", name="Base Pack", version="0.1.0")
        # Assert - fields and defaults
        assert m.id == "base"
        assert m.name == "Base Pack"
        assert m.version == "0.1.0"
        assert m.depends_on == []
        assert m.contributes == {}

    def test_full_valid(self) -> None:
        """PackManifest with depends_on and contributes."""
        # Arrange - full optional fields
        # Act - construct PackManifest
        m = PackManifest(
            id="python",
            name="Python Pack",
            version="0.1.0",
            depends_on=["base"],
            compatible_with=["python"],
            contributes={"templates": ["GROVE.md.j2"]},
        )
        # Assert - depends_on and contributes
        assert m.depends_on == ["base"]
        assert m.contributes["templates"] == ["GROVE.md.j2"]

    def test_missing_id_invalid(self) -> None:
        """Missing required id raises ValidationError."""
        # Arrange - omit required id
        # Act - construct PackManifest
        # Assert - ValidationError
        with pytest.raises(ValidationError):
            PackManifest(name="X", version="0.1.0")  # type: ignore[call-arg]


@pytest.mark.unit
class TestProjectProfile:
    """ProjectProfile validation and defaults."""

    def test_defaults(self) -> None:
        """ProjectProfile has sensible defaults."""
        # Arrange - none
        # Act - construct default ProjectProfile
        p = ProjectProfile()
        # Assert - default field values
        assert p.project_name == ""
        assert p.language == ""
        assert p.project_root == Path(".")
        assert p.raw == {}

    def test_serialization_round_trip(self) -> None:
        """ProjectProfile can be serialized and re-created."""
        # Arrange - populated ProjectProfile
        p = ProjectProfile(
            project_name="my-app",
            project_root=Path("/repo"),
            language="python",
            package_manager="uv",
            test_framework="pytest",
            tools=["ruff", "mypy"],
        )
        # Act - dump to dict and validate back
        data = p.model_dump(mode="json")
        p2 = ProjectProfile.model_validate(data)
        # Assert - project_root in data and restored profile matches
        assert Path(data["project_root"]) == Path("/repo")
        assert p2.project_name == p.project_name
        assert p2.project_root == Path("/repo")


@pytest.mark.unit
class TestPlannedFileAndInstallPlan:
    """PlannedFile and InstallPlan serialization."""

    def test_planned_file_serialization(self) -> None:
        """PlannedFile serializes src/dst as paths and round-trips."""
        # Arrange - PlannedFile with paths and variables
        pf = PlannedFile(
            src=Path("templates/GROVE.md.j2"),
            dst=Path(".grove/GROVE.md"),
            variables={"project_name": "foo"},
            managed=True,
        )
        # Act - dump and validate back
        data = pf.model_dump(mode="json")
        pf2 = PlannedFile.model_validate(data)
        # Assert - paths in data and restored object matches
        assert Path(data["src"]) == Path("templates/GROVE.md.j2")
        assert Path(data["dst"]) == Path(".grove/GROVE.md")
        assert pf2.src == pf.src
        assert pf2.dst == pf.dst

    def test_install_plan_serialization(self) -> None:
        """InstallPlan round-trips with list of PlannedFile."""
        # Arrange - InstallPlan with two PlannedFiles
        plan = InstallPlan(
            install_root=Path(".grove"),
            files=[
                PlannedFile(src=Path("a.j2"), dst=Path(".grove/a")),
                PlannedFile(
                    src=Path("b.j2"), dst=Path(".grove/b"), variables={"x": "y"}
                ),
            ],
        )
        # Act - dump and validate back
        data = plan.model_dump(mode="json")
        plan2 = InstallPlan.model_validate(data)
        # Assert - file count and restored plan structure
        assert len(data["files"]) == 2
        assert plan2.install_root == Path(".grove")
        assert len(plan2.files) == 2
        assert plan2.files[1].variables == {"x": "y"}


@pytest.mark.unit
class TestManifestState:
    """ManifestState (manifest.toml shape) validation."""

    def test_valid_minimal(self) -> None:
        """Minimal valid ManifestState."""
        # Arrange - grove and project sections only
        # Act - construct ManifestState
        state = ManifestState(
            grove=GroveSection(version="0.1.0", schema_version=1),
            project=ProjectSection(root="/repo", analysis_summary=""),
        )
        # Assert - version and empty lists
        assert state.grove.version == "0.1.0"
        assert state.installed_packs == []
        assert state.generated_files == []

    def test_valid_full(self) -> None:
        """ManifestState with packs and generated_files."""
        # Arrange - full sections including packs and generated_files
        # Act - construct ManifestState
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
        # Assert - packs and files counts and first pack id
        assert len(state.installed_packs) == 2
        assert state.installed_packs[0].id == "base"
        assert len(state.generated_files) == 2

    def test_invalid_missing_grove(self) -> None:
        """ManifestState requires grove section."""
        # Arrange - omit grove section
        # Act - construct ManifestState
        # Assert - ValidationError
        with pytest.raises(ValidationError):
            ManifestState(project=ProjectSection(root="/repo", analysis_summary=""))  # type: ignore[call-arg]

    def test_invalid_missing_project(self) -> None:
        """ManifestState requires project section."""
        # Arrange - omit project section
        # Act - construct ManifestState
        # Assert - ValidationError
        with pytest.raises(ValidationError):
            ManifestState(grove=GroveSection(version="0.1.0", schema_version=1))  # type: ignore[call-arg]
