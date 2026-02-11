"""Pydantic models for API responses."""

from __future__ import annotations

from typing import Any, Optional
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
    status: str = "idle"  # idle | running | completed | failed
    last_run: Optional[str] = None
    duration_seconds: Optional[float] = None
    output_exists: bool = False


class PipelineStatus(BaseModel):
    phases: list[PhaseStatus]
    active_preset: Optional[str] = None
    is_running: bool = False


class PresetInfo(BaseModel):
    name: str
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
    version: str = "0.1.0"
    knowledge_dir_exists: bool = False
    phases_config_exists: bool = False


# --- Pipeline Execution ---


class RunRequest(BaseModel):
    preset: Optional[str] = None
    phases: Optional[list[str]] = None
    env_overrides: Optional[dict[str, str]] = None


class RunResponse(BaseModel):
    run_id: str
    status: str
    message: str


class PhaseProgress(BaseModel):
    phase_id: str
    name: str
    status: str = "pending"  # pending | running | completed | failed
    started_at: Optional[str] = None
    duration_seconds: Optional[float] = None


class ExecutionStatus(BaseModel):
    state: str = "idle"  # idle | running | completed | failed | cancelled
    run_id: Optional[str] = None
    preset: Optional[str] = None
    phases: list[str] = []
    started_at: Optional[str] = None
    elapsed_seconds: Optional[float] = None
    phase_progress: list[PhaseProgress] = []


class RunHistoryEntry(BaseModel):
    run_id: str
    status: str
    preset: Optional[str] = None
    phases: list[str] = []
    started_at: Optional[str] = None
    duration: Optional[str] = None
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
