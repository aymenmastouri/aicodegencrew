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


@router.get("/stream")
async def pipeline_stream():
    """SSE endpoint for real-time pipeline events."""

    async def event_generator() -> AsyncGenerator[str, None]:
        idx = 0
        while True:
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

            await asyncio.sleep(0.5)

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
def pipeline_history():
    """Get run history from run_report.json."""
    return executor.get_history()
