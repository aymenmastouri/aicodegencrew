"""Pipeline reset API routes."""

from __future__ import annotations

import json
import logging
import os

from fastapi import APIRouter, HTTPException

from aicodegencrew.phase_registry import get_resettable_phases

from ..config import settings
from ..schemas import ResetPreview, ResetRequest, ResetResult, TaskResetRequest, TaskResetResult
from ..services.pipeline_executor import executor
from ..services.reset_service import clear_phase_state_only, execute_reset, execute_task_reset, preview_reset

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reset", tags=["reset"])


def _is_pipeline_running() -> bool:
    """Check if any pipeline is running (dashboard or CLI)."""
    # Dashboard-started run
    if executor.state == "running":
        process = getattr(executor, "_process", None)
        if process is None:
            if executor.__class__.__name__ != "PipelineExecutor":
                return True
            logger.warning("Ignoring stale in-memory running state (no subprocess bound)")
        else:
            try:
                poll_result = process.poll()
                if poll_result is None:
                    return True
                # For mocked process objects, keep conservative behavior and block reset.
                if not isinstance(poll_result, int):
                    return True
            except Exception:
                logger.warning("Failed to inspect pipeline subprocess state", exc_info=True)
                return True

    # CLI-started run: check phase_state.json
    state_path = settings.logs_dir / "phase_state.json"
    if not state_path.exists():
        return False
    try:
        with open(state_path, encoding="utf-8") as f:
            data = json.load(f)
        pid = data.get("pid")
        phases = data.get("phases", {})
        if not isinstance(phases, dict):
            phases = {}
        has_running = any(e.get("status") == "running" for e in phases.values() if isinstance(e, dict))
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


@router.post("/clear-state")
def clear_state(request: ResetRequest):
    """Clear phase status only (no file deletion, no cascade). Used for Discover."""
    cleared = clear_phase_state_only(request.phase_ids)
    return {"cleared": cleared}


@router.post("/task", response_model=TaskResetResult)
def reset_task(request: TaskResetRequest):
    """Reset output files for specific task IDs only (granular per-task reset).

    Unlike full phase reset, this only deletes files matching {task_id}_* patterns
    in the specified phases, leaving other tasks' outputs untouched.
    """
    if _is_pipeline_running():
        raise HTTPException(
            status_code=409,
            detail="Cannot reset while pipeline is running",
        )

    return execute_task_reset(
        task_ids=request.task_ids,
        phase_ids=request.phase_ids,
    )


@router.post("/all", response_model=ResetResult)
def reset_all():
    """Reset all phases (including discover)."""
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
