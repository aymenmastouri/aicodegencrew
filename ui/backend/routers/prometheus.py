"""Prometheus metrics endpoint for Grafana integration.

Exposes SDLC pipeline metrics in Prometheus text format at /metrics.
Only active when PROMETHEUS_ENABLED=true.
"""

import logging
import os

from fastapi import APIRouter, Response

logger = logging.getLogger(__name__)

router = APIRouter(tags=["prometheus"])

# Lazy-init prometheus collectors (only when endpoint is hit)
_collectors_initialized = False
_phase_duration = None
_phase_status = None
_tokens_total = None


def _init_collectors():
    """Initialize Prometheus collectors on first request."""
    global _collectors_initialized, _phase_duration, _phase_status, _tokens_total

    if _collectors_initialized:
        return

    try:
        from prometheus_client import Counter, Histogram

        _phase_duration = Histogram(
            "sdlc_phase_duration_seconds",
            "Duration of SDLC phase execution",
            labelnames=["phase_id"],
            buckets=(5, 15, 30, 60, 120, 300, 600, 1800, 3600),
        )
        _phase_status = Counter(
            "sdlc_phase_status_total",
            "Count of SDLC phase completions by status",
            labelnames=["phase_id", "status"],
        )
        _tokens_total = Counter(
            "sdlc_tokens_total",
            "Total LLM tokens consumed",
            labelnames=["phase_id", "token_type"],
        )
        _collectors_initialized = True
    except ImportError:
        logger.warning("[Prometheus] prometheus-client not installed — metrics disabled")


def record_phase_metric(phase_id: str, duration: float, status: str, tokens: dict[str, int] | None = None):
    """Record phase metrics for Prometheus export.

    Called from logger.log_metric() when PROMETHEUS_ENABLED=true.
    """
    if os.getenv("PROMETHEUS_ENABLED", "").strip().lower() not in ("true", "1", "yes"):
        return

    _init_collectors()

    if _phase_duration is not None:
        _phase_duration.labels(phase_id=phase_id).observe(duration)
    if _phase_status is not None:
        _phase_status.labels(phase_id=phase_id, status=status).inc()
    if _tokens_total is not None and tokens:
        for token_type, count in tokens.items():
            if count > 0:
                _tokens_total.labels(phase_id=phase_id, token_type=token_type).inc(count)


@router.get("/metrics")
def metrics_endpoint():
    """Prometheus metrics in text exposition format."""
    _init_collectors()

    if not _collectors_initialized:
        return Response(
            content="# prometheus-client not installed\n",
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
