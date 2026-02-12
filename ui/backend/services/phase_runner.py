"""Service for reading phase configuration and status."""

import yaml

from ..config import settings
from ..schemas import PhaseInfo, PhaseStatus, PipelineStatus, PresetInfo
from .phase_outputs import check_phase_output_exists


def _load_phases_config() -> dict:
    """Load phases_config.yaml."""
    if not settings.phases_config.exists():
        return {"phases": {}, "presets": {}}
    with open(settings.phases_config, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


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
    """Get current pipeline status based on output files.

    Uses the shared PHASE_OUTPUTS config (phase_outputs.py) as single
    source of truth for output detection — same paths used by reset.
    """
    config = _load_phases_config()
    statuses = []

    for phase_id, phase_cfg in sorted(
        config.get("phases", {}).items(),
        key=lambda x: x[1].get("order", 99),
    ):
        output_exists = check_phase_output_exists(phase_id, settings.project_root)
        enabled = phase_cfg.get("enabled", False)

        if output_exists:
            status = "completed"
        elif enabled:
            status = "ready"
        else:
            status = "planned"

        statuses.append(
            PhaseStatus(
                id=phase_id,
                name=phase_cfg.get("name", phase_id),
                status=status,
                enabled=enabled,
                output_exists=output_exists,
            )
        )

    return PipelineStatus(phases=statuses, is_running=False)
