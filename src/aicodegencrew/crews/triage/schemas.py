"""Pydantic schemas for Issue Triage."""

from typing import Literal

from pydantic import BaseModel, Field


# =============================================================================
# Request
# =============================================================================


class TriageRequest(BaseModel):
    """Input for a triage run."""

    issue_id: str = Field(..., description="Unique issue/ticket identifier")
    title: str = Field(default="", description="Issue title / summary")
    description: str = Field(default="", description="Detailed description")
    task_file: str | None = Field(default=None, description="Path to task file (XML, DOCX, …)")
    supplementary_files: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Category → file paths (requirements, logs, reference)",
    )


# =============================================================================
# Deterministic findings
# =============================================================================


class EntryPoint(BaseModel):
    """A candidate entry point component."""

    component: str = Field(..., description="Component name")
    file_path: str = Field(default="", description="Source file path")
    score: float = Field(default=0.0, description="Confidence score 0-1")
    signals: list[str] = Field(default_factory=list, description="Matching signals")


class BlastRadiusResult(BaseModel):
    """Result of blast-radius BFS."""

    affected: list[dict] = Field(default_factory=list, description="Affected components")
    depth: int = Field(default=0)
    component_count: int = Field(default=0)
    containers_affected: list[str] = Field(default_factory=list)


class DuplicateMatch(BaseModel):
    """A similar code/issue match."""

    chunk_id: str = Field(default="")
    path: str = Field(default="")
    score: float = Field(default=0.0)
    snippet: str = Field(default="")


class TestCoverageResult(BaseModel):
    """Test coverage for affected components."""

    covered: list[str] = Field(default_factory=list)
    uncovered: list[str] = Field(default_factory=list)
    coverage_ratio: float = Field(default=0.0)


class RiskAssessmentResult(BaseModel):
    """Risk assessment aggregation."""

    risk_level: Literal["low", "medium", "high", "critical"] = Field(default="medium")
    security_sensitive: bool = Field(default=False)
    flags: list[str] = Field(default_factory=list)


class TriageFindings(BaseModel):
    """All deterministic analysis results."""

    classification: dict = Field(default_factory=dict)
    entry_points: list[EntryPoint] = Field(default_factory=list)
    blast_radius: BlastRadiusResult = Field(default_factory=BlastRadiusResult)
    duplicates: list[DuplicateMatch] = Field(default_factory=list)
    test_coverage: TestCoverageResult = Field(default_factory=TestCoverageResult)
    risk_assessment: RiskAssessmentResult = Field(default_factory=RiskAssessmentResult)


# =============================================================================
# LLM outputs
# =============================================================================


class CustomerSummary(BaseModel):
    """Non-technical customer-facing summary."""

    summary: str = Field(default="", description="Plain-language summary")
    impact_level: Literal["low", "medium", "high", "critical"] = Field(default="medium")
    is_bug: bool = Field(default=False)
    workaround: str = Field(default="", description="Suggested workaround if any")
    eta_category: Literal["quick-fix", "short", "medium", "long", "unknown"] = Field(default="unknown")


class DeveloperBrief(BaseModel):
    """Technical developer brief."""

    root_cause_hypothesis: str = Field(default="")
    affected_files: list[str] = Field(default_factory=list)
    affected_components: list[str] = Field(default_factory=list)
    action_steps: list[str] = Field(default_factory=list)
    linked_tasks: list[str] = Field(default_factory=list)
    test_strategy: str = Field(default="")
    architecture_notes: str = Field(default="")


class TriageResult(BaseModel):
    """Combined structured output for both audiences."""

    issue_id: str
    classification: dict = Field(default_factory=dict)
    customer_summary: CustomerSummary = Field(default_factory=CustomerSummary)
    developer_brief: DeveloperBrief = Field(default_factory=DeveloperBrief)
    findings: TriageFindings = Field(default_factory=TriageFindings)
