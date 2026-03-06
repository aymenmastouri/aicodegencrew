"""Pipeline execution API routes."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..schemas import (
    ExecutionStatus,
    HistoryStats,
    RunDetail,
    RunHistoryEntry,
    RunRequest,
    RunResponse,
)
from ..services.pipeline_executor import executor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.post("/run", response_model=RunResponse)
def start_pipeline(request: RunRequest):
    """Start a pipeline execution."""
    if not request.preset and not request.phases:
        raise HTTPException(
            status_code=400,
            detail="Either 'preset' or 'phases' must be provided",
        )

    try:
        # Route to parallel mode when task_ids provided with task-bearing phases
        _TASK_BEARING_PHASES = {"triage", "plan", "implement", "verify", "deliver"}
        if request.task_ids and request.phases:
            non_task_phases = [p for p in request.phases if p not in _TASK_BEARING_PHASES]
            if non_task_phases:
                raise HTTPException(
                    status_code=400,
                    detail=f"Parallel mode requires task-bearing phases only. "
                    f"Invalid: {non_task_phases}. Valid: {sorted(_TASK_BEARING_PHASES)}",
                )
            run_info = executor.start_parallel_tasks(
                task_ids=request.task_ids,
                phases=request.phases,
                max_parallel=request.max_parallel,
                env_overrides=request.env_overrides,
            )
            return RunResponse(
                run_id=run_info.run_id,
                status="started",
                message=f"Parallel pipeline started: {len(request.task_ids)} task(s), run_id={run_info.run_id}",
            )
        if request.task_ids and request.preset:
            raise HTTPException(
                status_code=400,
                detail="Parallel mode requires explicit 'phases', not a 'preset'. "
                "Convert the preset to phases on the client side.",
            )

        run_info = executor.start(
            preset=request.preset,
            phases=request.phases,
            env_overrides=request.env_overrides,
        )
        return RunResponse(
            run_id=run_info.run_id,
            status="started",
            message=f"Pipeline started with run_id={run_info.run_id}",
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/cancel")
def cancel_pipeline():
    """Cancel the running pipeline."""
    success = executor.cancel()
    if success:
        return {"success": True, "message": "Pipeline cancelled"}
    return {"success": False, "message": "No running pipeline to cancel"}


@router.get("/status", response_model=ExecutionStatus)
def pipeline_status():
    """Get current pipeline execution status."""
    return executor.get_status()


_SSE_MAX_DURATION = 30 * 60  # 30 minutes max stream lifetime
_SSE_IDLE_TIMEOUT = 60  # Stop after 60s of no pipeline activity


@router.get("/stream")
async def pipeline_stream(start_idx: int = 0):
    """SSE endpoint for real-time pipeline events.

    Args:
        start_idx: Resume log stream from this index (avoids duplicate lines
                   when the client reconnects mid-run).
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        idx = start_idx
        started = asyncio.get_event_loop().time()
        idle_since: float | None = None
        while True:
            try:
                # Max stream lifetime guard
                elapsed = asyncio.get_event_loop().time() - started
                if elapsed > _SSE_MAX_DURATION:
                    yield f"data: {json.dumps({'type': 'timeout', 'data': 'Stream max duration reached'})}\n\n"
                    break

                lines = executor.get_log_lines(since=idx)
                idx += len(lines)

                for line in lines:
                    yield f"data: {json.dumps({'type': 'log_line', 'data': line})}\n\n"

                # Send status update
                status = executor.get_status()
                yield f"data: {json.dumps({'type': 'status', 'data': status})}\n\n"

                # If pipeline is no longer running, send final event and stop
                if status["state"] not in ("running", "idle"):
                    yield f"data: {json.dumps({'type': 'pipeline_complete', 'data': status})}\n\n"
                    break

                # Idle timeout: if state is 'idle' for too long, stop streaming
                if status["state"] == "idle":
                    now = asyncio.get_event_loop().time()
                    if idle_since is None:
                        idle_since = now
                    elif now - idle_since > _SSE_IDLE_TIMEOUT:
                        yield f"data: {json.dumps({'type': 'idle_timeout', 'data': 'No pipeline activity'})}\n\n"
                        break
                else:
                    idle_since = None

                await asyncio.sleep(0.5)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning("SSE generator error: %s", exc)
                try:
                    yield f"data: {json.dumps({'type': 'error', 'data': str(exc)})}\n\n"
                except Exception:
                    pass
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history", response_model=list[RunHistoryEntry])
def pipeline_history(limit: int = 50):
    """Get run history from JSONL (with legacy fallback)."""
    from ..services.history_service import get_run_history

    return get_run_history(limit=limit)


@router.get("/history/stats", response_model=HistoryStats)
def pipeline_history_stats():
    """Get aggregated operational stats across all run history."""
    from ..services.history_service import get_history_stats

    return get_history_stats()


@router.get("/history/{run_id}", response_model=RunDetail)
def pipeline_history_detail(run_id: str):
    """Get detailed outcome for a specific run, including phase results and metrics."""
    from ..services.history_service import get_run_detail

    detail = get_run_detail(run_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return detail
