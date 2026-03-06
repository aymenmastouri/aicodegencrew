"""Task Lifecycle API — unified view of a task's journey through all SDLC phases."""

import re

from fastapi import APIRouter, HTTPException

from ..services.task_lifecycle_service import get_input_task_ids, get_task_lifecycle, list_tasks

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _validate_task_id(task_id: str) -> None:
    if not _SAFE_ID_RE.match(task_id):
        raise HTTPException(status_code=400, detail="Invalid task_id")


def _load_or_404(task_id: str) -> dict:
    result = get_task_lifecycle(task_id)
    if not result["has_input"] and all(
        p.get("status") == "not_started" for p in result["phases"].values()
    ):
        raise HTTPException(status_code=404, detail=f"No data found for task {task_id}")
    return result


@router.get("")
def get_tasks():
    """List all discovered tasks with phase status summaries."""
    return {"tasks": list_tasks()}


@router.get("/input-ids")
def get_input_ids():
    """Return task IDs from inputs/tasks/ directory (for parallel task selection)."""
    return {"task_ids": get_input_task_ids()}


@router.get("/{task_id}")
def get_task(task_id: str):
    """Get full lifecycle data for a single task (all phases)."""
    _validate_task_id(task_id)
    return _load_or_404(task_id)


@router.get("/{task_id}/lifecycle")
def get_task_lifecycle_endpoint(task_id: str):
    """Get full lifecycle data — alias for /{task_id} (REST best practice)."""
    _validate_task_id(task_id)
    return _load_or_404(task_id)


@router.get("/{task_id}/phases/{phase}")
def get_task_phase(task_id: str, phase: str):
    """Get data for a single phase of a task."""
    _validate_task_id(task_id)
    result = _load_or_404(task_id)
    phase_data = result["phases"].get(phase)
    if phase_data is None:
        raise HTTPException(status_code=404, detail=f"Unknown phase: {phase}")
    return {"task_id": task_id, "phase": phase, **phase_data}
