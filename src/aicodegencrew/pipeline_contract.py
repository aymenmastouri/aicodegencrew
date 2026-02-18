"""Central contract for phase/preset definitions and status normalization."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .phase_registry import PHASES, PhaseDescriptor

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Status constants
# ---------------------------------------------------------------------------

# Phase result status (orchestrator internal API)
PHASE_RESULT_SUCCESS = "success"
PHASE_RESULT_PARTIAL = "partial"
PHASE_RESULT_SKIPPED = "skipped"
PHASE_RESULT_FAILED = "failed"

# Phase progress/status (UI/API/executor)
PHASE_PROGRESS_PENDING = "pending"
PHASE_PROGRESS_RUNNING = "running"
PHASE_PROGRESS_COMPLETED = "completed"
PHASE_PROGRESS_PARTIAL = "partial"
PHASE_PROGRESS_SKIPPED = "skipped"
PHASE_PROGRESS_FAILED = "failed"

# Pipeline card status (phase runner)
PIPELINE_PHASE_IDLE = "idle"
PIPELINE_PHASE_READY = "ready"
PIPELINE_PHASE_PLANNED = "planned"

# Run outcome
RUN_OUTCOME_SUCCESS = "success"
RUN_OUTCOME_ALL_SKIPPED = "all_skipped"
RUN_OUTCOME_PARTIAL = "partial"
RUN_OUTCOME_FAILED = "failed"

PHASE_RESULT_NON_BLOCKING = frozenset(
    {
        PHASE_RESULT_SUCCESS,
        PHASE_RESULT_PARTIAL,
        PHASE_RESULT_SKIPPED,
    }
)

PHASE_PROGRESS_COMPLETE = frozenset(
    {
        PHASE_PROGRESS_COMPLETED,
        PHASE_PROGRESS_PARTIAL,
        PHASE_PROGRESS_SKIPPED,
    }
)


def _normalize_token(value: str | None) -> str:
    return str(value or "").strip().lower()


def normalize_phase_result_status(value: str | None, default: str = PHASE_RESULT_SUCCESS) -> str:
    """Normalize arbitrary status strings to orchestrator phase-result status."""
    token = _normalize_token(value)

    if token in {"failed", "failure", "error", "exception", "cancelled", "canceled"}:
        return PHASE_RESULT_FAILED
    if token in {"partial", "degraded", "warning", "warn"}:
        return PHASE_RESULT_PARTIAL
    if token in {"skipped", "skip", "up_to_date", "uptodate", "noop", "no_change", "no_changes"}:
        return PHASE_RESULT_SKIPPED
    if token in {"completed", "complete", "success", "ok", "done", "dry_run", "dryrun"}:
        return PHASE_RESULT_SUCCESS
    return default


def phase_result_to_phase_state_status(value: str | None) -> str:
    """Convert phase-result status to phase_state.json status values."""
    normalized = normalize_phase_result_status(value)
    if normalized == PHASE_RESULT_PARTIAL:
        return PHASE_PROGRESS_PARTIAL
    if normalized == PHASE_RESULT_SKIPPED:
        return PHASE_PROGRESS_SKIPPED
    if normalized == PHASE_RESULT_FAILED:
        return PHASE_PROGRESS_FAILED
    return PHASE_PROGRESS_COMPLETED


def normalize_phase_progress_status(value: str | None, default: str = PHASE_PROGRESS_PENDING) -> str:
    """Normalize status strings to API/UI phase-progress status values."""
    token = _normalize_token(value)

    if token in {"running", "in_progress", "in-progress", "active"}:
        return PHASE_PROGRESS_RUNNING
    if token in {"failed", "failure", "error", "exception", "cancelled", "canceled"}:
        return PHASE_PROGRESS_FAILED
    if token in {"partial", "degraded", "warning", "warn"}:
        return PHASE_PROGRESS_PARTIAL
    if token in {"skipped", "skip", "up_to_date", "uptodate", "noop", "no_change", "no_changes"}:
        return PHASE_PROGRESS_SKIPPED
    if token in {"completed", "complete", "success", "ok", "done", "dry_run", "dryrun"}:
        return PHASE_PROGRESS_COMPLETED
    if token in {"pending", "queued", "idle", "ready", "planned"}:
        return PHASE_PROGRESS_PENDING
    return default


def normalize_pipeline_phase_status(value: str | None, default: str = PIPELINE_PHASE_IDLE) -> str:
    """Normalize status values used by pipeline-status cards."""
    token = _normalize_token(value)

    if token in {
        PIPELINE_PHASE_IDLE,
        PIPELINE_PHASE_READY,
        PIPELINE_PHASE_PLANNED,
        PHASE_PROGRESS_RUNNING,
        PHASE_PROGRESS_COMPLETED,
        PHASE_PROGRESS_PARTIAL,
        PHASE_PROGRESS_SKIPPED,
        PHASE_PROGRESS_FAILED,
    }:
        return token

    if token in {"success", "ok", "done", "dry_run", "dryrun"}:
        return PHASE_PROGRESS_COMPLETED
    if token in {"pending", "queued"}:
        return PIPELINE_PHASE_READY

    return default


def is_phase_result_success(status: str | None) -> bool:
    return normalize_phase_result_status(status) in PHASE_RESULT_NON_BLOCKING


def is_phase_progress_complete(status: str | None) -> bool:
    return normalize_phase_progress_status(status) in PHASE_PROGRESS_COMPLETE


def compute_run_outcome(statuses: Iterable[str | None]) -> str:
    """Compute aggregate run outcome from phase statuses."""
    normalized = [normalize_phase_progress_status(value, default=PHASE_PROGRESS_FAILED) for value in statuses]
    if not normalized:
        return RUN_OUTCOME_FAILED

    if any(status == PHASE_PROGRESS_FAILED for status in normalized):
        return RUN_OUTCOME_FAILED

    if all(status == PHASE_PROGRESS_SKIPPED for status in normalized):
        return RUN_OUTCOME_ALL_SKIPPED

    # A phase explicitly reporting 'partial' (degraded output) → partial run.
    # Legitimately skipped phases (discover=unchanged, implement=no tasks) are
    # expected behaviour and must NOT pollute the outcome with 'partial'.
    if any(status == PHASE_PROGRESS_PARTIAL for status in normalized):
        return RUN_OUTCOME_PARTIAL

    return RUN_OUTCOME_SUCCESS


# ---------------------------------------------------------------------------
# Contract data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PhaseDefinition:
    """One runtime phase definition merged from config + static registry."""

    phase_id: str
    name: str
    order: int
    enabled: bool
    required: bool
    phase_type: str
    dependencies: tuple[str, ...] = ()
    config: dict[str, Any] = field(default_factory=dict)
    raw_config: dict[str, Any] = field(default_factory=dict)
    primary_output: str = ""
    cleanup_targets: tuple[str, ...] = ()
    resettable: bool = True


@dataclass(frozen=True)
class PresetDefinition:
    """One preset definition from phases_config.yaml."""

    preset_id: str
    phases: tuple[str, ...]
    display_name: str = ""
    description: str = ""
    icon: str = "playlist_play"


@dataclass
class PhaseContext:
    """Shared execution context passed across pipeline phases."""

    run_id: str | None = None
    preset_id: str | None = None
    requested_phases: list[str] = field(default_factory=list)
    resolved_phases: list[str] = field(default_factory=list)
    current_phase: str | None = None
    artifacts: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    env_overrides: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def set_phase_result(self, phase_id: str, status: str, output: Any = None, message: str = "") -> None:
        self.artifacts[phase_id] = {
            "status": normalize_phase_result_status(status),
            "output": output,
            "message": message,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "preset_id": self.preset_id,
            "requested_phases": list(self.requested_phases),
            "resolved_phases": list(self.resolved_phases),
            "current_phase": self.current_phase,
            "artifacts": self.artifacts,
            "metrics": self.metrics,
            "env_overrides": self.env_overrides,
            "errors": self.errors,
        }


@dataclass(frozen=True)
class PipelineContract:
    """Central runtime contract for phases/presets/dependencies."""

    raw_config: dict[str, Any]
    phases: dict[str, PhaseDefinition]
    presets: dict[str, PresetDefinition]
    config_path: str | None = None

    def get_phase_ids(self) -> list[str]:
        return list(self.phases.keys())

    def get_preset_names(self) -> list[str]:
        return list(self.presets.keys())

    def get_enabled_phases(self) -> list[str]:
        enabled = [phase for phase in self.phases.values() if phase.enabled]
        enabled.sort(key=lambda item: (item.order, item.phase_id))
        return [phase.phase_id for phase in enabled]

    def get_preset_phases(self, preset_name: str) -> list[str]:
        preset = self.presets.get(preset_name)
        return list(preset.phases) if preset else []

    def get_dependencies(self, phase_id: str) -> list[str]:
        definition = self.phases.get(phase_id)
        return list(definition.dependencies) if definition else []

    def get_phase_config(self, phase_id: str) -> dict[str, Any]:
        definition = self.phases.get(phase_id)
        return dict(definition.raw_config) if definition else {}

    def resolve_requested_phases(self, preset: str | None, explicit_phases: list[str] | None) -> list[str]:
        if explicit_phases:
            return _deduplicate_preserving_order(explicit_phases)
        if preset:
            return self.get_preset_phases(preset)
        return self.get_enabled_phases()

    def get_unknown_phases(self, phase_ids: Iterable[str]) -> list[str]:
        return [phase_id for phase_id in phase_ids if phase_id not in self.phases]


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def load_pipeline_contract(
    config_path: str | Path | None = None,
    fallback_config: dict[str, Any] | None = None,
) -> PipelineContract:
    """Load and normalize pipeline config into a typed contract."""
    path: Path | None = Path(config_path) if config_path else None
    config_data: dict[str, Any] = {}
    parsed_from_file = False

    if path and path.exists():
        try:
            with open(path, encoding="utf-8") as file_handle:
                parsed = yaml.safe_load(file_handle) or {}
                if isinstance(parsed, dict):
                    config_data = parsed
                    parsed_from_file = True
                else:
                    logger.warning("[PipelineContract] Config root is not a dict: %s", path)
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.warning("[PipelineContract] Failed to load %s: %s", path, exc)
    elif fallback_config:
        config_data = dict(fallback_config)

    if not parsed_from_file and not config_data:
        config_data = dict(fallback_config or {})

    return build_pipeline_contract(config_data, config_path=str(path) if path else None)


def build_pipeline_contract(config_data: dict[str, Any], config_path: str | None = None) -> PipelineContract:
    """Build contract from already loaded config dict."""
    phases_config = config_data.get("phases", {})
    if not isinstance(phases_config, dict):
        logger.warning("[PipelineContract] 'phases' is not a dict, ignoring malformed config section")
        phases_config = {}

    presets_config = config_data.get("presets", {})
    if not isinstance(presets_config, dict):
        logger.warning("[PipelineContract] 'presets' is not a dict, ignoring malformed config section")
        presets_config = {}

    merged_phases = _merge_phase_definitions(phases_config)
    merged_presets = _merge_presets(presets_config)

    return PipelineContract(
        raw_config=config_data,
        phases=merged_phases,
        presets=merged_presets,
        config_path=config_path,
    )


def _merge_phase_definitions(phases_config: dict[str, Any]) -> dict[str, PhaseDefinition]:
    phase_ids = set(PHASES.keys()) | set(phases_config.keys())
    merged: dict[str, PhaseDefinition] = {}

    for phase_id in sorted(phase_ids):
        raw_cfg = phases_config.get(phase_id, {})
        if not isinstance(raw_cfg, dict):
            raw_cfg = {}

        descriptor = PHASES.get(phase_id)
        merged[phase_id] = _build_phase_definition(phase_id, raw_cfg, descriptor)

    return dict(sorted(merged.items(), key=lambda item: (item[1].order, item[0])))


def _build_phase_definition(
    phase_id: str,
    raw_cfg: dict[str, Any],
    descriptor: PhaseDescriptor | None,
) -> PhaseDefinition:
    cfg_order = raw_cfg.get("order")
    order = int(cfg_order) if isinstance(cfg_order, int) else (descriptor.order if descriptor else 999)

    name = str(raw_cfg.get("name") or (descriptor.display_name if descriptor else phase_id))
    enabled = bool(raw_cfg.get("enabled", descriptor.required if descriptor else False))
    required = bool(raw_cfg.get("required", descriptor.required if descriptor else False))
    phase_type = str(raw_cfg.get("type") or (descriptor.phase_type if descriptor else "pipeline"))

    cfg_deps = raw_cfg.get("dependencies")
    if isinstance(cfg_deps, list):
        dependencies = tuple(str(dep) for dep in cfg_deps if str(dep).strip())
    else:
        dependencies = descriptor.dependencies if descriptor else ()

    if descriptor and isinstance(cfg_deps, list):
        descriptor_deps = tuple(descriptor.dependencies)
        if tuple(dependencies) != descriptor_deps:
            logger.warning(
                "[PipelineContract] Dependency drift for %s: config=%s registry=%s",
                phase_id,
                list(dependencies),
                list(descriptor_deps),
            )

    cfg_payload = raw_cfg.get("config", {})
    if not isinstance(cfg_payload, dict):
        cfg_payload = {}

    return PhaseDefinition(
        phase_id=phase_id,
        name=name,
        order=order,
        enabled=enabled,
        required=required,
        phase_type=phase_type,
        dependencies=dependencies,
        config=dict(cfg_payload),
        raw_config=dict(raw_cfg),
        primary_output=descriptor.primary_output if descriptor else "",
        cleanup_targets=descriptor.cleanup_targets if descriptor else (),
        resettable=descriptor.resettable if descriptor else True,
    )


def _merge_presets(presets_config: dict[str, Any]) -> dict[str, PresetDefinition]:
    merged: dict[str, PresetDefinition] = {}
    for preset_id, value in presets_config.items():
        merged[preset_id] = _build_preset_definition(preset_id, value)
    return merged


def _build_preset_definition(preset_id: str, value: Any) -> PresetDefinition:
    display_name = preset_id
    description = ""
    icon = "playlist_play"

    if isinstance(value, list):
        phases = tuple(str(phase_id) for phase_id in value if str(phase_id).strip())
    elif isinstance(value, dict):
        phases_value = value.get("phases", [])
        if isinstance(phases_value, list):
            phases = tuple(str(phase_id) for phase_id in phases_value if str(phase_id).strip())
        else:
            phases = ()
        display_name = str(value.get("display_name", preset_id))
        description = str(value.get("description", ""))
        icon = str(value.get("icon", "playlist_play"))
    else:
        phases = ()

    return PresetDefinition(
        preset_id=preset_id,
        phases=phases,
        display_name=display_name,
        description=description,
        icon=icon,
    )


def _deduplicate_preserving_order(items: Iterable[str]) -> list[str]:
    deduplicated: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        deduplicated.append(item)
    return deduplicated
