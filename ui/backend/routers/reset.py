"""Pipeline reset API routes."""

from __future__ import annotations

import json
import logging
import os

from fastapi import APIRouter, HTTPException

from aicodegencrew.phase_registry import get_resettable_phases

from ..config import settings
from ..schemas import ResetPreview, ResetRequest, ResetResult
from ..services.pipeline_executor import executor
from ..services.reset_service import execute_reset, preview_reset

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reset", tags=["reset"])


def _is_pipeline_running() -> bool:
    """Check if any pipeline is running (dashboard or CLI)."""
    # Dashboard-started run
    if executor.state == "running":
        return True

    # CLI-started run: check phase_state.json
    state_path = settings.project_root / "logs" / "phase_state.json"
    if not state_path.exists():
        return False
    try:
        with open(state_path, encoding="utf-8") as f:
            data = json.load(f)
        pid = data.get("pid")
        phases = data.get("phases", {})
        has_running = any(e.get("status") == "running" for e in phases.values())
        if has_running and pid:
            try:
                os.kill(pid, 0)
                return True  # Process alive + phase running
            except (OSError, ProcessLookupError):
                pass  # Process dead, stale state
    except (json.JSONDecodeError, OSError):
        pass
    return False


@router.post("/preview", response_model=ResetPreview)
def reset_preview(request: ResetRequest):
    """Dry-run: show which phases and files would be affected."""
    return preview_reset(
        phase_ids=request.phase_ids,
        cascade=request.cascade,
    )


@router.post("/execute", response_model=ResetResult)
def reset_execute(request: ResetRequest):
    """Execute a phase reset. Blocked if pipeline is running (409)."""
    if _is_pipeline_running():
        raise HTTPException(
            status_code=409,
            detail="Cannot reset while pipeline is running",
        )

    return execute_reset(
        phase_ids=request.phase_ids,
        cascade=request.cascade,
    )


@router.post("/all", response_model=ResetResult)
def reset_all():
    """Reset all phases except discover."""
    if _is_pipeline_running():
        raise HTTPException(
            status_code=409,
            detail="Cannot reset while pipeline is running",
        )

    all_phases = get_resettable_phases()

    return execute_reset(
        phase_ids=all_phases,
        cascade=False,
    )
