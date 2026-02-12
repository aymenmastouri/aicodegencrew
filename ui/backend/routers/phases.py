"""Phase management API routes."""

from fastapi import APIRouter

from ..schemas import PhaseInfo, PipelineStatus, PresetInfo
from ..services.phase_runner import get_phases, get_pipeline_status, get_presets

router = APIRouter(prefix="/api/phases", tags=["phases"])


@router.get("", response_model=list[PhaseInfo])
def list_phases():
    """Get all configured phases."""
    return get_phases()


@router.get("/presets", response_model=list[PresetInfo])
def list_presets():
    """Get all configured presets."""
    return get_presets()


@router.get("/status", response_model=PipelineStatus)
def pipeline_status():
    """Get current pipeline status."""
    return get_pipeline_status()
