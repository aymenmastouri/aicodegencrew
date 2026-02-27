"""Service for reading phase configuration and status."""

import logging
import re

from aicodegencrew.phase_registry import check_phase_output_exists
from aicodegencrew.pipeline_contract import (
    PHASE_PROGRESS_CANCELLED,
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
from .history_service import get_phase_duration_averages

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

        if st == PHASE_PROGRESS_CANCELLED:
            # Cancelled always wins — even if partial output exists on disk.
            return PHASE_PROGRESS_CANCELLED, duration, None

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
            if st == PHASE_PROGRESS_COMPLETED and not duration:
                # Backward compatibility: a phase with no measured duration
                # (None) or zero duration (0.0 from old NoopPlan) was never
                # actually executed.  No output + no real duration = skipped.
                return PHASE_PROGRESS_SKIPPED, duration, None
            if st == PHASE_PROGRESS_PARTIAL:
                # A partial run may leave no detectable output (e.g. safety
                # gate rejected all commits, or only checkpoint files exist).
                # Trust phase_state.json — demoting to "ready" hides the fact
                # that the phase ran and produced partial results.
                return PHASE_PROGRESS_PARTIAL, duration, None
            if enabled:
                # completed + no output = phase was reset after completion
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


_SAFE_PHASE_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def toggle_phase(phase_id: str, enabled: bool) -> PhaseInfo:
    """Toggle a phase's enabled state in phases_config.yaml.

    Raises ValueError if the phase is not found or is required (cannot disable).
    """
    if not _SAFE_PHASE_ID_RE.match(phase_id):
        raise ValueError(f"Invalid phase_id: {phase_id}")

    import yaml  # lazy import — only needed here

    config_path = settings.phases_config
    try:
        with open(config_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"Failed to read config: {exc}") from exc

    phases_section = raw.get("phases", {})
    if phase_id not in phases_section:
        raise ValueError(f"Unknown phase: {phase_id}")

    definition = phases_section[phase_id]
    if not isinstance(definition, dict):
        definition = {}
        phases_section[phase_id] = definition
    if definition.get("required") and not enabled:
        raise ValueError(f"Phase '{phase_id}' is required and cannot be disabled")

    definition["enabled"] = enabled
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(raw, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"Failed to write config: {exc}") from exc

    contract = _load_contract()
    defn = contract.phases[phase_id]
    return PhaseInfo(
        id=phase_id,
        name=defn.name,
        order=defn.order,
        enabled=defn.enabled,
        required=defn.required,
        type=defn.phase_type,
        dependencies=list(defn.dependencies),
    )


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

    Dependency rule: a phase is only "ready" if ALL its dependencies have a
    terminal-success status (completed, partial, skipped).  Otherwise it shows
    as "planned" (not yet available).
    """
    contract = _load_contract()
    state_data = _read_phase_state()
    state_phases = state_data.get("phases", {})

    # First pass: resolve raw status for every phase
    raw: dict[str, str] = {}
    phase_data: list[tuple] = []
    for phase_id, definition in contract.phases.items():
        output_exists = check_phase_output_exists(phase_id, settings.project_root)
        state_entry = state_phases.get(phase_id)
        status, duration, _error = _resolve_status(state_entry, output_exists, definition.enabled)
        raw[phase_id] = status
        phase_data.append((phase_id, definition, status, duration, state_entry, output_exists))

    # Load historical phase duration averages for ETA display
    try:
        avg_durations = get_phase_duration_averages()
    except Exception as exc:
        logger.debug("Failed to load phase duration averages: %s", exc)
        avg_durations = {}

    # Second pass: downgrade "ready" → "planned" when dependencies are not yet satisfied
    _success = {PHASE_PROGRESS_COMPLETED, PHASE_PROGRESS_PARTIAL, PHASE_PROGRESS_SKIPPED}
    statuses = []
    any_running = False

    for phase_id, definition, status, duration, state_entry, output_exists in phase_data:
        if status == PIPELINE_PHASE_READY and definition.dependencies:
            deps_done = all(raw.get(dep) in _success for dep in definition.dependencies)
            if not deps_done:
                status = PIPELINE_PHASE_PLANNED

        if status == PHASE_PROGRESS_RUNNING:
            any_running = True

        statuses.append(
            PhaseStatus(
                id=phase_id,
                name=definition.name,
                status=status,
                enabled=definition.enabled,
                output_exists=output_exists,
                duration_seconds=duration,
                last_run=state_entry.get("completed_at") if state_entry else None,
                avg_duration_seconds=avg_durations.get(phase_id),
            )
        )

    return PipelineStatus(phases=statuses, is_running=any_running)
