"""Task Lifecycle API — unified view of a task's journey through all SDLC phases."""

import re

from fastapi import APIRouter, HTTPException

from ..services.task_lifecycle_service import get_task_lifecycle, list_tasks

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


@router.get("")
def get_tasks():
    """List all discovered tasks with phase status summaries."""
    return {"tasks": list_tasks()}


@router.get("/{task_id}")
def get_task(task_id: str):
    """Get full lifecycle data for a single task."""
    if not _SAFE_ID_RE.match(task_id):
        raise HTTPException(status_code=400, detail="Invalid task_id")

    result = get_task_lifecycle(task_id)

    # 404 if task has no data at all
    if not result["has_input"] and all(
        p["status"] == "not_started" for p in result["phases"].values()
    ):
        raise HTTPException(status_code=404, detail=f"No data found for task {task_id}")

    return result
