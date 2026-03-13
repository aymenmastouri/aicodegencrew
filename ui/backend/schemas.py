"""Pydantic models for API responses."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

RunOutcome = Literal["success", "all_skipped", "partial", "failed"] | None


class PhaseInfo(BaseModel):
    id: str
    name: str
    order: int
    enabled: bool
    required: bool = False
    type: str = "pipeline"
    dependencies: list[str] = []


class PhaseStatus(BaseModel):
    id: str
    name: str
    status: str = "idle"  # idle | ready | running | completed | partial | skipped | failed | planned
    enabled: bool = True
    last_run: str | None = None
    duration_seconds: float | None = None
    output_exists: bool = False
    avg_duration_seconds: float | None = None


class PipelineStatus(BaseModel):
    phases: list[PhaseStatus]
    active_preset: str | None = None
    is_running: bool = False


class PresetInfo(BaseModel):
    name: str
    display_name: str = ""
    description: str = ""
    icon: str = "playlist_play"
    phases: list[str]


class KnowledgeFile(BaseModel):
    path: str
    name: str
    size_bytes: int
    modified: str
    type: str  # json | md | drawio


class KnowledgeSummary(BaseModel):
    total_files: int
    total_size_bytes: int
    files: list[KnowledgeFile]


class MetricEvent(BaseModel):
    timestamp: str
    event: str
    data: dict[str, Any] = {}


class MetricsSummary(BaseModel):
    total_events: int
    events: list[MetricEvent]
    run_ids: list[str] = []


class ReportSummary(BaseModel):
    task_id: str
    status: str
    files_changed: int = 0
    dry_run: bool = False


class ReportList(BaseModel):
    plans: list[dict[str, Any]] = []
    codegen_reports: list[dict[str, Any]] = []
    document_reports: list[dict[str, Any]] = []


class LogEntry(BaseModel):
    line: str
    level: str = "INFO"


class LogResponse(BaseModel):
    lines: list[str]
    total_lines: int
    file_path: str


class DiagramInfo(BaseModel):
    name: str
    path: str
    type: str  # drawio | mermaid
    size_bytes: int


class DiagramList(BaseModel):
    diagrams: list[DiagramInfo]


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = ""  # set dynamically from aicodegencrew.__version__
    knowledge_dir_exists: bool = False
    phases_config_exists: bool = False


# --- Pipeline Execution ---


class RunRequest(BaseModel):
    preset: str | None = None
    phases: list[str] | None = None
    task_ids: list[str] | None = None
    max_parallel: int = Field(default=4, ge=1, le=16)
    env_overrides: dict[str, str] | None = None

    @field_validator("task_ids")
    @classmethod
    def _validate_task_ids(cls, v: list[str] | None) -> list[str] | None:
        if v is not None:
            v = [tid.strip() for tid in v if tid and tid.strip()]
            if not v:
                return None  # treat empty-after-filter as None
        return v

    @field_validator("env_overrides")
    @classmethod
    def _validate_env_overrides(cls, v: dict[str, str] | None) -> dict[str, str] | None:
        if v is None:
            return v
        _ALLOWED_ENV_KEYS = {
            "LOG_LEVEL",
            "INDEX_MODE",
            "OUTPUT_DIR",
            "DOCS_OUTPUT_DIR",
            "MAX_LLM_OUTPUT_TOKENS",
            "LLM_CONTEXT_WINDOW",
            "CREWAI_MEMORY_ENABLED",
            "CREWAI_PLANNING_ENABLED",
            "CREWAI_DELEGATION_ENABLED",
            "TRIAGE_QUALITY_THRESHOLD",
            "PLAN_TRIAGE_WAIT_TIMEOUT",
            "CODEGEN_BUILD_VERIFY",
            "TZ",
        }
        for key in v:
            if key not in _ALLOWED_ENV_KEYS:
                allowed = ", ".join(sorted(_ALLOWED_ENV_KEYS))
                raise ValueError(
                    f"env_overrides key '{key}' is not permitted. "
                    f"Allowed keys: {allowed}"
                )
        return v


class RunResponse(BaseModel):
    run_id: str
    status: str
    message: str


class SubPhaseProgress(BaseModel):
    name: str
    status: str = "completed"  # pending | running | completed | failed
    duration_seconds: float | None = None
    total_tokens: int = 0
    tasks: list[str] = []

    @field_validator("tasks", mode="before")
    @classmethod
    def _coerce_tasks(cls, v: Any) -> list[str]:
        if isinstance(v, int):
            return [f"{v} tasks"]
        if isinstance(v, list):
            return v
        return []


class LiveMetrics(BaseModel):
    total_tokens: int = 0
    crew_completions: int = 0


class PhaseProgress(BaseModel):
    phase_id: str
    name: str
    status: str = "pending"  # pending | running | completed | partial | failed | skipped | cancelled
    started_at: str | None = None
    duration_seconds: float | None = None
    sub_phases: list[SubPhaseProgress] = []
    total_tokens: int = 0


class TaskProgress(BaseModel):
    state: str = "pending"  # pending | running | completed | failed | cancelled
    pid: int | None = None
    exit_code: int | None = None
    completed_phases: list[str] = []


class ExecutionStatus(BaseModel):
    state: str = "idle"  # idle | running | completed | failed | cancelled
    run_id: str | None = None
    preset: str | None = None
    phases: list[str] = []
    started_at: str | None = None
    elapsed_seconds: float | None = None
    phase_progress: list[PhaseProgress] = []
    progress_percent: float = 0
    completed_phase_count: int = 0
    skipped_phase_count: int = 0
    total_phase_count: int = 0
    eta_seconds: float | None = None
    live_metrics: LiveMetrics | None = None
    run_outcome: RunOutcome = None
    parallel_mode: bool = False
    task_progress: dict[str, TaskProgress] | None = None


class RunHistoryEntry(BaseModel):
    run_id: str
    status: str
    run_outcome: RunOutcome = None
    preset: str | None = None
    phases: list[str] = []
    started_at: str | None = None
    completed_at: str | None = None
    duration: str | None = None
    duration_seconds: float | None = None
    trigger: str = "pipeline"  # "pipeline" | "reset"
    phase_results: list[dict[str, Any]] = []
    deleted_count: int | None = None
    total_tokens: int | None = None


class RunDetail(BaseModel):
    """Full run detail with outcome data."""

    run_id: str
    status: str
    run_outcome: RunOutcome = None
    preset: str | None = None
    phases: list[str] = []
    started_at: str | None = None
    completed_at: str | None = None
    duration: str | None = None
    duration_seconds: float | None = None
    trigger: str = "pipeline"
    phase_results: list[dict[str, Any]] = []
    metrics_events: list[dict[str, Any]] = []
    environment: dict[str, Any] = {}


class HistoryStats(BaseModel):
    """Aggregated operational stats across all run history."""

    total_runs: int = 0
    total_resets: int = 0
    success_count: int = 0
    failed_count: int = 0
    cancelled_count: int = 0
    success_rate: float = 0.0
    avg_duration_seconds: float = 0.0
    total_tokens: int = 0
    total_deleted_files: int = 0
    most_used_preset: str | None = None
    last_run_at: str | None = None
    phase_frequency: dict[str, int] = {}


# --- Pipeline Reset ---


class ResetRequest(BaseModel):
    phase_ids: list[str]
    cascade: bool = True


class TaskResetRequest(BaseModel):
    task_ids: list[str]
    phase_ids: list[str] | None = None


class ResetPreview(BaseModel):
    phases_to_reset: list[str]
    files_to_delete: list[str]


class ResetResult(BaseModel):
    reset_phases: list[str]
    deleted_count: int
    timestamp: str


class TaskResetResult(BaseModel):
    task_ids: list[str]
    affected_phases: list[str]
    deleted_count: int
    timestamp: str


# --- Environment Config ---


class EnvVariable(BaseModel):
    name: str
    value: str = ""
    description: str = ""
    group: str = "General"
    required: bool = False


class EnvUpdate(BaseModel):
    values: dict[str, str]


# --- Git Branches ---


class BranchInfo(BaseModel):
    name: str  # "codegen/TASK-123"
    task_id: str  # "TASK-123"
    file_count: int = 0
    has_report: bool = False


class BranchList(BaseModel):
    branches: list[BranchInfo] = []
    repo_path: str = ""


# --- Collectors ---


class CollectorInfo(BaseModel):
    id: str
    name: str
    description: str
    dimension: str
    category: str  # "core" | "optional"
    collector_type: str | None = None
    step: int
    output_file: str
    can_disable: bool
    enabled: bool = True
    fact_count: int | None = None
    last_modified: str | None = None


class CollectorListResponse(BaseModel):
    collectors: list[CollectorInfo]
    total: int
    enabled_count: int


class CollectorToggleRequest(BaseModel):
    enabled: bool


class CollectorOutput(BaseModel):
    collector_id: str
    data: Any
    fact_count: int
    file_size_bytes: int
