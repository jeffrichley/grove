"""Analyzer-specific models: detected facts with optional confidence/evidence."""

from pydantic import BaseModel, Field


class DetectedFact(BaseModel):
    """A single fact produced by a detector (e.g. language=python, tool=ruff).

    Used to merge into ProjectProfile. confidence and evidence are optional
    and go into raw when present.
    """

    key: str = Field(..., description="Fact key (e.g. language, package_manager).")
    value: str | list[str] = Field(
        ...,
        description="Fact value; list for multi-value (e.g. tools).",
    )
    confidence: str = Field(
        default="",
        description="Optional confidence level (e.g. high, low).",
    )
    evidence: str = Field(
        default="",
        description="Optional evidence (e.g. [tool.pytest.ini_options] present).",
    )
