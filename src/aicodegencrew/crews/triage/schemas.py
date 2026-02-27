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


class ContextBoundary(BaseModel):
    """An analytical insight about a constraint, risk, or boundary relevant to this issue."""

    category: Literal[
        "technology_constraint",
        "dependency_risk",
        "integration_boundary",
        "pattern_constraint",
        "data_boundary",
        "security_boundary",
        "testing_constraint",
        "workflow_constraint",
        "infrastructure_constraint",
    ] = Field(default="technology_constraint", description="Type of boundary or constraint")
    boundary: str = Field(default="", description="What does this fact MEAN for this issue? (analysis, not data)")
    severity: Literal["info", "caution", "blocking"] = Field(default="info", description="How critical is this boundary")
    source_facts: list[str] = Field(default_factory=list, description="Traceability: which extract data backs this")


class AnticipatedQuestion(BaseModel):
    """A question a developer would likely ask, with a preemptive answer."""

    question: str = Field(default="", description="What would a developer ask?")
    answer: str = Field(default="", description="The answer based on available context")


class DeveloperContext(BaseModel):
    """Technical developer context — big picture and scope, no action steps."""

    big_picture: str = Field(default="", description="North Star: What is this project? Who is the customer? What problem does this solve? Why NOW?")
    scope_boundary: str = Field(default="", description="What's IN scope vs OUT of scope for this issue")
    classification_assessment: str = Field(default="", description="For bugs: is the classification correct? For CR/Task: empty")
    classification_confidence: float = Field(default=-1.0, description="Bug confidence: 0.0 = definitely not a bug → 1.0 = confirmed bug. -1 = not applicable (CR/Task)")
    affected_components: list[str] = Field(default_factory=list, description="High-level component names (NOT file paths)")
    context_boundaries: list[ContextBoundary] = Field(default_factory=list, description="2-6 analytical insights about constraints, risks, and boundaries")
    architecture_notes: str = Field(default="", description="Architectural walkthrough: where does this piece fit? Container, layer, neighbors")
    anticipated_questions: list[AnticipatedQuestion] = Field(default_factory=list, description="3-5 questions a developer would ask, answered proactively")
    linked_tasks: list[str] = Field(default_factory=list)


class TriageResult(BaseModel):
    """Combined structured output for both audiences."""

    issue_id: str
    classification: dict = Field(default_factory=dict)
    customer_summary: CustomerSummary = Field(default_factory=CustomerSummary)
    developer_context: DeveloperContext = Field(default_factory=DeveloperContext)
    findings: TriageFindings = Field(default_factory=TriageFindings)
