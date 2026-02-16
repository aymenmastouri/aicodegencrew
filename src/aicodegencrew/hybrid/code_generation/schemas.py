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
# Stage 2A: Import Index Builder Schemas
# =============================================================================


class ImportEntry(BaseModel):
    """A resolved import mapping: symbol → exact import statement."""

    symbol: str
    qualified_name: str = ""
    import_path: str = ""
    file_path: str = ""
    kind: str = "class"
    language: str = "other"
    container: str = ""
    exports: list[str] = Field(default_factory=list)


# =============================================================================
# Stage 2B: Dependency Grapher Schemas
# =============================================================================


class FileGenerationEntry(BaseModel):
    """A file in the dependency-ordered generation queue."""

    file_path: str
    component: ComponentTarget | None = None
    depends_on: list[str] = Field(default_factory=list)
    depended_by: list[str] = Field(default_factory=list)
    generation_tier: int = 0


class GenerationOrder(BaseModel):
    """Topologically sorted file generation order."""

    ordered_files: list[FileGenerationEntry] = Field(default_factory=list)
    dependency_graph: dict[str, list[str]] = Field(default_factory=dict)


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
# Stage 4b: Build Verifier Schemas
# =============================================================================


class ContainerBuildResult(BaseModel):
    """Build result for a single container (backend/frontend)."""

    container_id: str = Field(..., description="e.g. container.backend")
    container_name: str = Field(..., description="e.g. backend")
    build_command: str = ""
    success: bool = False
    exit_code: int = -1
    error_summary: str = ""
    attempts: int = 1
    healed_files: list[str] = Field(default_factory=list)
    duration_seconds: float = 0.0


class BuildVerificationResult(BaseModel):
    """Aggregated build verification across all containers."""

    container_results: list[ContainerBuildResult] = Field(default_factory=list)
    all_passed: bool = False
    total_containers_built: int = 0
    total_containers_failed: int = 0
    total_heal_attempts: int = 0
    total_heal_successes: int = 0
    duration_seconds: float = 0.0
    skipped: bool = False
    skip_reason: str = ""


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
    degradation_reasons: list[str] = Field(default_factory=list)
    duration_seconds: float = 0.0
    llm_calls: int = 0
    total_tokens: int = 0
    dry_run: bool = False
    build_verification: BuildVerificationResult | None = None
    # Cascade mode fields (populated when processing multiple tasks sequentially)
    cascade_branch: str = ""
    cascade_position: int = 0
    cascade_total: int = 0
    prior_task_ids: list[str] = Field(default_factory=list)
