"""Service for reading phase configuration and status."""

import json
import logging
import os

import yaml

from aicodegencrew.phase_registry import check_phase_output_exists

from ..config import settings
from ..schemas import PhaseInfo, PhaseStatus, PipelineStatus, PresetInfo

logger = logging.getLogger(__name__)

_STATE_FILE_NAME = "phase_state.json"
_STALE_THRESHOLD = 3600  # 1 hour


def _load_phases_config() -> dict:
    """Load phases_config.yaml."""
    if not settings.phases_config.exists():
        return {"phases": {}, "presets": {}}
    with open(settings.phases_config, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _read_phase_state() -> dict:
    """Read logs/phase_state.json written by the orchestrator."""
    path = settings.project_root / "logs" / _STATE_FILE_NAME
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read phase state: %s", exc)
        return {}


def _is_pid_alive(pid: int | None) -> bool:
    """Check if a process is still running."""
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _resolve_status(
    state_entry: dict | None,
    output_exists: bool,
    enabled: bool,
    pid: int | None,
) -> tuple[str, float | None, str | None]:
    """Resolve effective phase status using priority matrix.

    Returns (status, duration_seconds, error).
    """
    if state_entry:
        st = state_entry.get("status", "")
        duration = state_entry.get("duration_seconds")
        error = state_entry.get("error")

        if st == "running":
            # Crash recovery: check PID liveness
            if _is_pid_alive(pid):
                return "running", None, None
            else:
                return "failed", duration, "Process terminated unexpectedly"

        if st == "failed":
            return "failed", duration, error

        if st in ("completed", "partial"):
            if output_exists:
                return st, duration, None
            elif enabled:
                # Output deleted (reset happened after completion)
                return "ready", None, None

    # No state entry — backward compatible: check output files
    if output_exists:
        return "completed", None, None
    if enabled:
        return "ready", None, None
    return "planned", None, None


def get_phases() -> list[PhaseInfo]:
    """Get all configured phases."""
    config = _load_phases_config()
    phases = []
    for phase_id, phase_cfg in config.get("phases", {}).items():
        phases.append(
            PhaseInfo(
                id=phase_id,
                name=phase_cfg.get("name", phase_id),
                order=phase_cfg.get("order", 99),
                enabled=phase_cfg.get("enabled", False),
                required=phase_cfg.get("required", False),
                type=phase_cfg.get("type", "pipeline"),
                dependencies=phase_cfg.get("dependencies", []),
            )
        )
    return sorted(phases, key=lambda p: p.order)


def get_presets() -> list[PresetInfo]:
    """Get all configured presets."""
    config = _load_phases_config()
    presets = []
    for name, value in config.get("presets", {}).items():
        if isinstance(value, list):
            # Legacy format: preset_name: [phase_list]
            presets.append(PresetInfo(name=name, phases=value))
        elif isinstance(value, dict):
            # New format: preset_name: {display_name, description, icon, phases}
            presets.append(
                PresetInfo(
                    name=name,
                    display_name=value.get("display_name", name),
                    description=value.get("description", ""),
                    icon=value.get("icon", "playlist_play"),
                    phases=value.get("phases", []),
                )
            )
    return presets


def get_pipeline_status() -> PipelineStatus:
    """Get current pipeline status by merging state file with output-file checks.

    Priority: state file (running/failed/completed) > output existence > config enabled.
    Backward compatible: no state file = old output-only behavior.
    """
    config = _load_phases_config()
    state_data = _read_phase_state()
    state_phases = state_data.get("phases", {})
    pid = state_data.get("pid")

    statuses = []
    any_running = False

    for phase_id, phase_cfg in sorted(
        config.get("phases", {}).items(),
        key=lambda x: x[1].get("order", 99),
    ):
        output_exists = check_phase_output_exists(phase_id, settings.project_root)
        enabled = phase_cfg.get("enabled", False)
        state_entry = state_phases.get(phase_id)

        status, duration, _error = _resolve_status(state_entry, output_exists, enabled, pid)

        if status == "running":
            any_running = True

        statuses.append(
            PhaseStatus(
                id=phase_id,
                name=phase_cfg.get("name", phase_id),
                status=status,
                enabled=enabled,
                output_exists=output_exists,
                duration_seconds=duration,
                last_run=state_entry.get("completed_at") if state_entry else None,
            )
        )

    return PipelineStatus(phases=statuses, is_running=any_running)
