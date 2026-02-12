"""Pipeline reset API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from ..schemas import ResetPreview, ResetRequest, ResetResult
from ..services.pipeline_executor import executor
from ..services.reset_service import execute_reset, preview_reset

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reset", tags=["reset"])


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
    if executor.state == "running":
        raise HTTPException(
            status_code=409,
            detail="Cannot reset while pipeline is running",
        )

    return execute_reset(
        phase_ids=request.phase_ids,
        cascade=request.cascade,
        archive=request.archive,
    )


@router.post("/all", response_model=ResetResult)
def reset_all():
    """Reset all phases (with cascade and archive)."""
    if executor.state == "running":
        raise HTTPException(
            status_code=409,
            detail="Cannot reset while pipeline is running",
        )

    all_phases = [
        "phase0_indexing",
        "phase1_architecture_facts",
        "phase2_architecture_analysis",
        "phase3_architecture_synthesis",
        "phase4_development_planning",
        "phase5_code_generation",
    ]

    return execute_reset(
        phase_ids=all_phases,
        cascade=False,  # Already listing all phases
        archive=True,
    )
