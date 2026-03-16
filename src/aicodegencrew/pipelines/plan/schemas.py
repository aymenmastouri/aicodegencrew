"""
Pydantic Schemas for Development Planning Pipeline (Phase 4).

All outputs are strongly typed for validation and documentation.
"""

from typing import Literal

from pydantic import BaseModel, Field

# =============================================================================
# Stage 1: Input Processing Schemas
# =============================================================================


class TaskInput(BaseModel):
    """Normalized task input from any format."""

    task_id: str = Field(..., description="Unique task identifier (e.g., PROJ-123)")
    source_file: str = Field(..., description="Source file path")
    source_format: Literal["xml", "docx", "excel", "text"] = Field(..., description="Detected format")
    summary: str = Field(..., description="Task summary/title")
    description: str = Field(default="", description="Detailed description")
    acceptance_criteria: list[str] = Field(default_factory=list, description="Acceptance criteria")
    technical_notes: str = Field(default="", description="Technical implementation notes")
    labels: list[str] = Field(default_factory=list, description="Labels/tags")
    priority: str = Field(default="Medium", description="Priority level")
    task_type: Literal["feature", "bugfix", "upgrade", "refactoring"] = Field(
        default="feature", description="Detected task type"
    )
    jira_type: str = Field(default="Task", description="JIRA issue type (Task, Sub-Task, Epic, Story, Bug)")
    linked_tasks: list[str] = Field(
        default_factory=list, description="Linked ticket IDs (from issuelinks, subtasks, description references)"
    )
    upgrade_context: dict | None = Field(default=None, description="Upgrade context (framework, versions)")


# =============================================================================
# Stage 2: Component Discovery Schemas
# =============================================================================


class ComponentMatch(BaseModel):
    """A discovered component with relevance scoring."""

    id: str = Field(..., description="Component ID")
    name: str = Field(..., description="Component name")
    stereotype: str = Field(..., description="Component stereotype (service, controller, etc.)")
    layer: str = Field(..., description="Architecture layer (presentation, application, etc.)")
    package: str = Field(default="", description="Package path")
    file_path: str = Field(default="", description="Source file path")
    relevance_score: float = Field(..., ge=0, le=1, description="Relevance score (0-1)")
    change_type: Literal["modify", "create", "delete"] = Field(default="modify", description="Type of change")
    source: str = Field(default="", description="Discovery source (vector_search, name_match, etc.)")


class InterfaceMatch(BaseModel):
    """A discovered interface (REST endpoint, etc.)."""

    id: str
    type: str  # REST, GraphQL, etc.
    path: str
    method: str | None = None
    implemented_by: str


class DependencyRelation(BaseModel):
    """A component dependency."""

    from_component: str
    to_component: str
    relation_type: str  # uses, depends, etc.


# =============================================================================
# Stage 3: Pattern Matching Schemas
# =============================================================================


class TestPattern(BaseModel):
    """A matched test pattern."""

    name: str
    file_path: str
    test_type: str  # unit, integration, e2e
    framework: str  # junit, cucumber, etc.
    scenarios: list[str] = Field(default_factory=list)
    relevance_score: float = Field(..., ge=0, le=1)
    pattern_description: str


class SecurityPattern(BaseModel):
    """A matched security pattern."""

    security_type: str  # cors, csrf, authentication, etc.
    class_name: str
    pattern_name: str
    file_path: str
    recommendation: str


class ValidationPattern(BaseModel):
    """A matched validation pattern."""

    validation_type: str  # not_null, email, etc.
    target_class: str
    field_hint: str
    pattern_name: str
    recommendation: str
    usage_count: int = 1


class ErrorHandlingPattern(BaseModel):
    """A matched error handling pattern."""

    handling_type: str  # custom_exception, exception_handler
    exception_class: str
    handler_method: str | None = None
    pattern_name: str
    recommendation: str


class WorkflowContext(BaseModel):
    """Business workflow context."""

    workflow_name: str
    steps: list[str]
    components_involved: list[str]
    impact: str


# =============================================================================
# Stage 4: Plan Generation Schema (LLM Output)
# =============================================================================


class ImplementationPlan(BaseModel):
    """Complete implementation plan (final output)."""

    task_id: str
    source_files: list[str]

    # Understanding
    understanding: dict = Field(..., description="Task understanding (summary, requirements, AC, technical_notes)")

    # Development Plan
    development_plan: dict = Field(..., description="Complete development plan with all sections")


class UpgradeRule(BaseModel):
    """Single upgrade rule from migration sequence."""

    rule_id: str = Field(..., description="Rule ID (e.g., ng19-standalone-default)")
    title: str = Field(..., description="Short title of the rule")
    severity: Literal["breaking", "deprecated", "recommended"] = Field(..., description="Impact severity")
    migration_steps: list[str] = Field(default_factory=list, description="Step-by-step migration guide")
    affected_files: list[str] = Field(default_factory=list, description="Files matched by this rule")
    estimated_effort_minutes: int = Field(default=0, description="Estimated effort per occurrence")
    schematic: str | None = Field(default=None, description="Angular schematic command (if applicable)")


class UpgradePlan(BaseModel):
    """Framework upgrade plan with migration sequence."""

    framework: str = Field(..., description="Framework name (e.g., Angular)")
    from_version: str = Field(..., description="Current version")
    to_version: str = Field(..., description="Target version")
    migration_sequence: list[UpgradeRule] = Field(
        default_factory=list, description="Ordered migration rules by severity"
    )
    verification_commands: list[str] = Field(
        default_factory=list, description="Commands to verify upgrade (e.g., ng build, ng test)"
    )
    total_estimated_effort_hours: float = Field(default=0.0, description="Total estimated effort in hours")
    pre_migration_checks: list[str] = Field(default_factory=list, description="Checks to run before migration")
    post_migration_checks: list[str] = Field(default_factory=list, description="Checks to run after migration")


class DevelopmentPlan(BaseModel):
    """Detailed development plan structure."""

    # Components
    affected_components: list[ComponentMatch]
    interfaces: list[InterfaceMatch] = Field(default_factory=list)
    dependencies: list[DependencyRelation] = Field(default_factory=list)

    # Upgrade Plan (for framework upgrade tasks only)
    upgrade_plan: UpgradePlan | None = Field(default=None, description="Framework upgrade migration plan")

    # Implementation
    implementation_steps: list[str] = Field(..., min_items=1, description="Ordered implementation steps")

    # Testing
    test_strategy: dict = Field(..., description="Test strategy with unit_tests, integration_tests, similar_patterns")

    # Patterns
    security_considerations: list[SecurityPattern] = Field(default_factory=list)
    validation_strategy: list[ValidationPattern] = Field(default_factory=list)
    error_handling: list[ErrorHandlingPattern] = Field(default_factory=list)

    # Architecture
    architecture_context: dict = Field(
        default_factory=dict, description="Architecture style, layer_pattern, quality_grade, layer_compliance"
    )

    # Workflow
    workflow_context: list[WorkflowContext] = Field(default_factory=list)

    # Metadata
    estimated_complexity: Literal["Low", "Medium", "High"]
    complexity_reasoning: str
    estimated_files_changed: int = Field(ge=1)
    risks: list[str] = Field(default_factory=list)

    # Traceability
    evidence_sources: dict = Field(
        default_factory=dict, description="Sources of evidence (components, test_patterns, etc.)"
    )


# =============================================================================
# Stage 5: Validation Results
# =============================================================================


class ValidationResult(BaseModel):
    """Plan validation result."""

    is_valid: bool
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
