"""Collector service — list, toggle, read output for dashboard API."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

# Import registry and config from the core pipeline
from src.aicodegencrew.pipelines.architecture_facts.collectors.collector_config import (
    load_collector_config,
    toggle_collector,
)
from src.aicodegencrew.pipelines.architecture_facts.collectors.registry import (
    COLLECTOR_REGISTRY,
)

from ..config import settings
from ..schemas import CollectorInfo, CollectorListResponse, CollectorOutput


def _config_dir() -> Path:
    """Return the config directory (alongside phases_config.yaml)."""
    return settings.project_root / "config"


def _output_dir() -> Path:
    """Return the knowledge/extract output directory."""
    return settings.knowledge_dir / "extract"


def _get_output_stats(output_file: str) -> tuple[int | None, str | None, int]:
    """Get fact count, last_modified, and file size for an output file.

    Returns (fact_count, last_modified_iso, file_size_bytes).
    """
    filepath = _output_dir() / output_file
    if not filepath.exists():
        return None, None, 0

    try:
        stat = filepath.stat()
        file_size = stat.st_size
        mtime = datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat()

        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        # Count facts: if list, len; if dict with list values, sum of list lengths
        if isinstance(data, list):
            fact_count = len(data)
        elif isinstance(data, dict):
            # For data_model.json: sum of entities + tables + migrations
            total = 0
            for v in data.values():
                if isinstance(v, list):
                    total += len(v)
            fact_count = total if total > 0 else 1
        else:
            fact_count = 1

        return fact_count, mtime, file_size
    except (json.JSONDecodeError, OSError):
        return None, None, 0


def list_collectors() -> CollectorListResponse:
    """List all collectors with status, config, and output stats."""
    config = load_collector_config(_config_dir())

    collectors = []
    for reg in COLLECTOR_REGISTRY:
        cid = reg["id"]
        enabled = config.get(cid, True)
        # Core collectors are always enabled regardless of config
        if not reg["can_disable"]:
            enabled = True

        fact_count, last_modified, _ = _get_output_stats(reg["output_file"])

        collectors.append(
            CollectorInfo(
                id=cid,
                name=reg["name"],
                description=reg["description"],
                dimension=reg["dimension"],
                category=reg["category"],
                collector_type=reg.get("collector_type"),
                step=reg["step"],
                output_file=reg["output_file"],
                can_disable=reg["can_disable"],
                enabled=enabled,
                fact_count=fact_count,
                last_modified=last_modified,
            )
        )

    enabled_count = sum(1 for c in collectors if c.enabled)
    return CollectorListResponse(
        collectors=collectors,
        total=len(collectors),
        enabled_count=enabled_count,
    )


def toggle_collector_state(collector_id: str, enabled: bool) -> CollectorInfo:
    """Toggle a collector's enabled state and return updated info."""
    toggle_collector(_config_dir(), collector_id, enabled)

    # Find the registry entry
    for reg in COLLECTOR_REGISTRY:
        if reg["id"] == collector_id:
            fact_count, last_modified, _ = _get_output_stats(reg["output_file"])
            return CollectorInfo(
                id=collector_id,
                name=reg["name"],
                description=reg["description"],
                dimension=reg["dimension"],
                category=reg["category"],
                collector_type=reg.get("collector_type"),
                step=reg["step"],
                output_file=reg["output_file"],
                can_disable=reg["can_disable"],
                enabled=enabled,
                fact_count=fact_count,
                last_modified=last_modified,
            )

    raise ValueError(f"Unknown collector: {collector_id}")


def get_collector_output(collector_id: str) -> CollectorOutput:
    """Read a collector's output JSON file."""
    # Find the registry entry
    reg = None
    for r in COLLECTOR_REGISTRY:
        if r["id"] == collector_id:
            reg = r
            break

    if reg is None:
        raise ValueError(f"Unknown collector: {collector_id}")

    filepath = _output_dir() / reg["output_file"]
    if not filepath.exists():
        raise FileNotFoundError(f"Output file not found: {reg['output_file']}")

    try:
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {reg['output_file']}: {e}") from e

    fact_count, _, file_size = _get_output_stats(reg["output_file"])

    return CollectorOutput(
        collector_id=collector_id,
        data=data,
        fact_count=fact_count or 0,
        file_size_bytes=file_size,
    )
