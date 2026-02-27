"""Phase management API routes."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..schemas import PhaseInfo, PipelineStatus, PresetInfo
from ..services.phase_runner import get_phases, get_pipeline_status, get_presets, toggle_phase

router = APIRouter(prefix="/api/phases", tags=["phases"])


class PhaseToggleRequest(BaseModel):
    enabled: bool


@router.get("", response_model=list[PhaseInfo])
def list_phases():
    """Get all configured phases."""
    try:
        return get_phases()
    except (OSError, ValueError) as e:
        raise HTTPException(status_code=500, detail=f"Failed to load phases: {e}")


@router.get("/presets", response_model=list[PresetInfo])
def list_presets():
    """Get all configured presets."""
    try:
        return get_presets()
    except (OSError, ValueError) as e:
        raise HTTPException(status_code=500, detail=f"Failed to load presets: {e}")


@router.get("/status", response_model=PipelineStatus)
def pipeline_status():
    """Get current pipeline status."""
    try:
        return get_pipeline_status()
    except (OSError, ValueError) as e:
        raise HTTPException(status_code=500, detail=f"Failed to load status: {e}")


@router.put("/{phase_id}/toggle", response_model=PhaseInfo)
def toggle_phase_endpoint(phase_id: str, body: PhaseToggleRequest):
    """Enable or disable a phase in phases_config.yaml."""
    try:
        return toggle_phase(phase_id, body.enabled)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
