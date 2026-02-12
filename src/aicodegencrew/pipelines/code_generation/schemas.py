"""
Pydantic Schemas for Code Generation Pipeline (Phase 5).

All stage inputs/outputs are strongly typed.
"""

from typing import Literal

from pydantic import BaseModel, Field

# =============================================================================
# Stage 1: Plan Reader Schemas
# =============================================================================


class ComponentTarget(BaseModel):
    """A component targeted for code changes."""

    id: str = Field(..., description="Component ID from architecture_facts")
    name: str = Field(..., description="Component name")
    file_path: str = Field(..., description="Absolute path in target repo")
    stereotype: str = Field(default="unknown", description="Component stereotype")
    layer: str = Field(default="unknown", description="Architecture layer")
    change_type: Literal["modify", "create", "delete"] = Field(default="modify", description="Type of change")
    relevance_score: float = Field(default=0.0, ge=0, le=1)


class CodegenPlanInput(BaseModel):
    """Validated plan input from Phase 4."""

    task_id: str
    task_type: Literal["upgrade", "feature", "bugfix", "refactoring"]
    summary: str
    description: str = ""
    affected_components: list[ComponentTarget] = Field(default_factory=list)
    implementation_steps: list[str] = Field(default_factory=list)
    upgrade_plan: dict | None = Field(default=None, description="Migration rules for upgrade tasks")
    patterns: dict = Field(
        default_factory=dict,
        description="Test/security/validation patterns from Phase 4",
    )
    architecture_context: dict = Field(default_factory=dict)


# =============================================================================
# Stage 2: Context Collector Schemas
# =============================================================================


class FileContext(BaseModel):
    """Collected context for a single source file."""

    file_path: str
    content: str = Field(default="", description="Current file content (truncated)")
    language: Literal["java", "typescript", "html", "scss", "json", "xml", "other"] = "other"
    sibling_files: list[str] = Field(default_factory=list, description="Nearby files for pattern reference")
    related_patterns: list[str] = Field(default_factory=list, description="Matched test/security patterns")
    component: ComponentTarget | None = None


class CollectedContext(BaseModel):
    """Aggregated context for all targeted files."""

    file_contexts: list[FileContext] = Field(default_factory=list)
    total_files: int = 0
    skipped_files: int = 0


# =============================================================================
# Stage 3: Code Generator Schemas
# =============================================================================


class GeneratedFile(BaseModel):
    """A single generated/modified file."""

    file_path: str
    content: str = Field(default="", description="New/modified content")
    original_content: str = Field(default="", description="Original content (for diff)")
    action: Literal["modify", "create", "delete"] = "modify"
    diff: str = Field(default="", description="Unified diff")
    confidence: float = Field(default=0.5, ge=0, le=1)
    language: str = "other"
    error: str = Field(default="", description="Error if generation failed")


# =============================================================================
# Stage 4: Code Validator Schemas
# =============================================================================


class FileValidationResult(BaseModel):
    """Validation result for a single file."""

    file_path: str
    is_valid: bool = True
    syntax_ok: bool = True
    pattern_ok: bool = True
    security_ok: bool = True
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    """Aggregated validation result."""

    file_results: list[FileValidationResult] = Field(default_factory=list)
    total_valid: int = 0
    total_invalid: int = 0
    security_issues: list[str] = Field(default_factory=list)


# =============================================================================
# Stage 5: Output Writer Schemas
# =============================================================================


class CodegenReport(BaseModel):
    """Final report for a code generation run."""

    task_id: str
    branch_name: str = ""
    status: Literal["success", "partial", "failed", "dry_run"] = "failed"
    files_changed: int = 0
    files_created: int = 0
    files_failed: int = 0
    generated_files: list[GeneratedFile] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)
    duration_seconds: float = 0.0
    llm_calls: int = 0
    total_tokens: int = 0
    dry_run: bool = False
