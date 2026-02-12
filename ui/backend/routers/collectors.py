"""Collector management API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..schemas import CollectorInfo, CollectorListResponse, CollectorOutput, CollectorToggleRequest
from ..services.collector_service import (
    get_collector_output,
    list_collectors,
    toggle_collector_state,
)

router = APIRouter(prefix="/api/collectors", tags=["collectors"])


@router.get("", response_model=CollectorListResponse)
def get_collectors():
    """List all collectors with metadata, status, and output statistics."""
    return list_collectors()


@router.put("/{collector_id}/toggle", response_model=CollectorInfo)
def toggle_collector(collector_id: str, body: CollectorToggleRequest):
    """Enable or disable a collector."""
    try:
        return toggle_collector_state(collector_id, body.enabled)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{collector_id}/output", response_model=CollectorOutput)
def collector_output(collector_id: str):
    """Get a collector's output JSON data."""
    try:
        return get_collector_output(collector_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
