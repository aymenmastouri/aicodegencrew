"""Service for reading phase configuration and status."""

import logging

from aicodegencrew.phase_registry import check_phase_output_exists
from aicodegencrew.pipeline_contract import (
    PHASE_PROGRESS_COMPLETED,
    PHASE_PROGRESS_FAILED,
    PHASE_PROGRESS_PARTIAL,
    PHASE_PROGRESS_RUNNING,
    PHASE_PROGRESS_SKIPPED,
    PIPELINE_PHASE_PLANNED,
    PIPELINE_PHASE_READY,
    PipelineContract,
    load_pipeline_contract,
    normalize_pipeline_phase_status,
)
from aicodegencrew.shared.utils.phase_state import read_all_phases

from ..config import settings
from ..schemas import PhaseInfo, PhaseStatus, PipelineStatus, PresetInfo

logger = logging.getLogger(__name__)


def _load_phases_config() -> dict:
    """Load phases_config.yaml."""
    return _load_contract().raw_config


def _load_contract() -> PipelineContract:
    """Load the central pipeline contract."""
    return load_pipeline_contract(settings.phases_config)


def _read_phase_state() -> dict:
    """Read phase state with crash recovery handled upstream."""
    return read_all_phases()


def _resolve_status(
    state_entry: dict | None,
    output_exists: bool,
    enabled: bool,
) -> tuple[str, float | None, str | None]:
    """Resolve effective phase status.

    Crash recovery (running -> failed when PID dead) is handled
    upstream in phase_state.read_all_phases(). This function only
    maps persisted state + output existence to display status.
    """
    if state_entry:
        st = normalize_pipeline_phase_status(state_entry.get("status", ""))
        duration = state_entry.get("duration_seconds")
        error = state_entry.get("error")

        if st == PHASE_PROGRESS_RUNNING:
            return PHASE_PROGRESS_RUNNING, None, None

        if st == PHASE_PROGRESS_FAILED:
            return PHASE_PROGRESS_FAILED, duration, error

        if st == PHASE_PROGRESS_SKIPPED:
            # Disabled phases marked "skipped" are not "up to date" — they
            # were never meant to run.  Show them as "planned" (not available).
            if not enabled:
                return PIPELINE_PHASE_PLANNED, None, None
            return PHASE_PROGRESS_SKIPPED, duration, None

        if st in (PHASE_PROGRESS_COMPLETED, PHASE_PROGRESS_PARTIAL):
            if output_exists:
                return st, duration, None
            if st == PHASE_PROGRESS_COMPLETED and duration is None:
                # Backward compatibility: a phase with no measured duration was
                # never actually executed (old NoopPlan stored as "completed").
                # Only triggers when duration is truly absent — not for fast
                # phases that measured ~0 s, which store duration=0.0.
                return PHASE_PROGRESS_SKIPPED, duration, None
            if enabled:
                # Output deleted (reset happened after completion)
                return PIPELINE_PHASE_READY, None, None

        if st in (PIPELINE_PHASE_READY, PIPELINE_PHASE_PLANNED):
            return st, duration, error

    # No state entry - backward compatible: check output files
    if output_exists:
        return PHASE_PROGRESS_COMPLETED, None, None
    if enabled:
        return PIPELINE_PHASE_READY, None, None
    return PIPELINE_PHASE_PLANNED, None, None


def get_phases() -> list[PhaseInfo]:
    """Get all configured phases."""
    contract = _load_contract()
    phases = []
    for phase_id, definition in contract.phases.items():
        phases.append(
            PhaseInfo(
                id=phase_id,
                name=definition.name,
                order=definition.order,
                enabled=definition.enabled,
                required=definition.required,
                type=definition.phase_type,
                dependencies=list(definition.dependencies),
            )
        )
    return sorted(phases, key=lambda phase: phase.order)


def get_presets() -> list[PresetInfo]:
    """Get all configured presets."""
    contract = _load_contract()
    presets = []
    for preset in contract.presets.values():
        presets.append(
            PresetInfo(
                name=preset.preset_id,
                display_name=preset.display_name,
                description=preset.description,
                icon=preset.icon,
                phases=list(preset.phases),
            )
        )
    return presets


def get_pipeline_status() -> PipelineStatus:
    """Get current pipeline status by merging state file with output-file checks.

    Priority: state file (running/failed/completed) > output existence > config enabled.
    Backward compatible: no state file = old output-only behavior.
    """
    contract = _load_contract()
    state_data = _read_phase_state()
    state_phases = state_data.get("phases", {})

    statuses = []
    any_running = False

    for phase_id, definition in contract.phases.items():
        output_exists = check_phase_output_exists(phase_id, settings.project_root)
        enabled = definition.enabled
        state_entry = state_phases.get(phase_id)

        status, duration, _error = _resolve_status(state_entry, output_exists, enabled)

        if status == PHASE_PROGRESS_RUNNING:
            any_running = True

        statuses.append(
            PhaseStatus(
                id=phase_id,
                name=definition.name,
                status=status,
                enabled=enabled,
                output_exists=output_exists,
                duration_seconds=duration,
                last_run=state_entry.get("completed_at") if state_entry else None,
            )
        )

    return PipelineStatus(phases=statuses, is_running=any_running)
