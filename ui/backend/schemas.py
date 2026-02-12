"""Pydantic models for API responses."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class PhaseInfo(BaseModel):
    id: str
    name: str
    order: int
    enabled: bool
    required: bool = False
    dependencies: list[str] = []


class PhaseStatus(BaseModel):
    id: str
    name: str
    status: str = "idle"  # idle | ready | running | completed | failed | planned
    enabled: bool = True
    last_run: str | None = None
    duration_seconds: float | None = None
    output_exists: bool = False


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
    version: str = "0.3.0"
    knowledge_dir_exists: bool = False
    phases_config_exists: bool = False


# --- Pipeline Execution ---


class RunRequest(BaseModel):
    preset: str | None = None
    phases: list[str] | None = None
    env_overrides: dict[str, str] | None = None


class RunResponse(BaseModel):
    run_id: str
    status: str
    message: str


class PhaseProgress(BaseModel):
    phase_id: str
    name: str
    status: str = "pending"  # pending | running | completed | failed
    started_at: str | None = None
    duration_seconds: float | None = None


class ExecutionStatus(BaseModel):
    state: str = "idle"  # idle | running | completed | failed | cancelled
    run_id: str | None = None
    preset: str | None = None
    phases: list[str] = []
    started_at: str | None = None
    elapsed_seconds: float | None = None
    phase_progress: list[PhaseProgress] = []


class RunHistoryEntry(BaseModel):
    run_id: str
    status: str
    preset: str | None = None
    phases: list[str] = []
    started_at: str | None = None
    duration: str | None = None
    phase_results: list[dict[str, Any]] = []


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
