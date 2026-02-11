"""Metrics API routes."""

from fastapi import APIRouter, Query

from ..services.metrics_reader import read_metrics
from ..schemas import MetricsSummary

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("", response_model=MetricsSummary)
def get_metrics(
    limit: int = Query(200, ge=1, le=5000),
    event: str | None = Query(None, description="Filter by event name"),
):
    """Get metrics events from metrics.jsonl."""
    return read_metrics(limit=limit, event_filter=event)
