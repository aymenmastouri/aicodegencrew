"""Collector management API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..schemas import (
    CollectorInfo,
    CollectorListResponse,
    CollectorOutput,
    CollectorToggleRequest,
    EcosystemInfo,
    EcosystemListResponse,
    EcosystemPriorityRequest,
    EcosystemToggleRequest,
)
from ..services.collector_service import (
    get_collector_output,
    list_collectors,
    list_ecosystems,
    toggle_collector_state,
    toggle_ecosystem_state,
    update_ecosystem_priority,
)

router = APIRouter(prefix="/api/collectors", tags=["collectors"])


@router.get("", response_model=CollectorListResponse)
def get_collectors():
    """List all collectors with metadata, status, and output statistics."""
    return list_collectors()


@router.get("/ecosystems", response_model=EcosystemListResponse)
def get_ecosystems():
    """List all ecosystems with detection status and extracted facts."""
    return list_ecosystems()


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


@router.put("/ecosystems/{eco_id}/toggle", response_model=EcosystemInfo)
def toggle_ecosystem(eco_id: str, body: EcosystemToggleRequest):
    """Enable or disable an ecosystem."""
    try:
        return toggle_ecosystem_state(eco_id, body.enabled)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/ecosystems/{eco_id}/priority", response_model=EcosystemInfo)
def update_priority(eco_id: str, body: EcosystemPriorityRequest):
    """Update an ecosystem's priority."""
    try:
        return update_ecosystem_priority(eco_id, body.priority)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
