"""Run history service using append-only JSONL storage."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from ..config import settings

logger = logging.getLogger(__name__)


def _history_path() -> Path:
    return settings.run_history


def append_run_to_history(entry: dict) -> None:
    """Append a single entry to the JSONL history file."""
    path = _history_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except OSError as exc:
        logger.error("Failed to append to run history: %s", exc)


def get_run_history(limit: int = 50, offset: int = 0) -> list[dict]:
    """Read run history from JSONL, newest first.

    Falls back to legacy ``run_report.json`` + archive when the JSONL
    file doesn't exist or is empty.
    """
    path = _history_path()
    entries: list[dict] = []

    if path.exists() and path.stat().st_size > 0:
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except OSError as exc:
            logger.warning("Failed to read run history: %s", exc)

    # Fallback to legacy run_report.json + archive when JSONL is empty
    if not entries:
        entries = _read_legacy_history()

    # Newest first
    entries.reverse()
    return entries[offset : offset + limit]


def get_run_detail(run_id: str) -> dict | None:
    """Get detailed run info by run_id — combines JSONL entry + run_report + metrics."""
    path = _history_path()
    entry: dict | None = None

    # Search JSONL for matching run_id
    if path.exists() and path.stat().st_size > 0:
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        parsed = json.loads(line)
                        if parsed.get("run_id") == run_id:
                            entry = parsed
                    except json.JSONDecodeError:
                        continue
        except OSError as exc:
            logger.warning("Failed to read run history: %s", exc)

    # Fallback: check legacy history
    if entry is None:
        for legacy in _read_legacy_history():
            if legacy.get("run_id") == run_id:
                entry = legacy
                break

    if entry is None:
        return None

    # Enrich with run_report.json if the run matches current report
    if not entry.get("phase_results"):
        report_path = settings.run_report
        if report_path.exists():
            try:
                with open(report_path, encoding="utf-8") as f:
                    report = json.load(f)
                if report.get("run_id") == run_id:
                    entry["phase_results"] = report.get("phases", [])
                    entry["environment"] = report.get("environment", {})
            except (json.JSONDecodeError, OSError):
                pass

    # Enrich with filtered metrics events
    entry["metrics_events"] = _get_metrics_for_run(run_id)

    # Add environment info if not already present
    if not entry.get("environment"):
        entry["environment"] = {
            "knowledge_dir": str(settings.knowledge_dir),
            "logs_dir": str(settings.logs_dir),
        }

    return entry


def _get_metrics_for_run(run_id: str) -> list[dict]:
    """Filter metrics.jsonl events for a specific run_id."""
    metrics_path = settings.metrics_file
    events: list[dict] = []

    if not metrics_path.exists():
        return events

    try:
        with open(metrics_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    parsed = json.loads(line)
                    data = parsed.get("data", {})
                    if data.get("run_id") == run_id or parsed.get("run_id") == run_id:
                        events.append(parsed)
                except json.JSONDecodeError:
                    continue
    except OSError as exc:
        logger.warning("Failed to read metrics: %s", exc)

    return events


def _read_legacy_history() -> list[dict]:
    """Read from run_report.json and knowledge/archive/run_report*.json."""
    entries: list[dict] = []

    if settings.run_report.exists():
        try:
            with open(settings.run_report, encoding="utf-8") as f:
                data = json.load(f)
            entries.append(_format_legacy(data))
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Failed to parse run_report.json: %s", exc)

    archive_dir = settings.knowledge_dir / "archive"
    if archive_dir.exists():
        for report_file in sorted(archive_dir.glob("run_report*.json"), reverse=True):
            try:
                with open(report_file, encoding="utf-8") as f:
                    data = json.load(f)
                entries.append(_format_legacy(data))
            except (json.JSONDecodeError, KeyError):
                continue

    return entries


def _format_legacy(data: dict) -> dict:
    """Convert a legacy run_report.json entry to history format."""
    return {
        "run_id": data.get("run_id", "unknown"),
        "status": data.get("status", "unknown"),
        "preset": data.get("environment", {}).get("preset"),
        "phases": data.get("planned_phases", []),
        "started_at": data.get("timestamp"),
        "completed_at": None,
        "duration": data.get("total_duration"),
        "duration_seconds": None,
        "trigger": "pipeline",
        "phase_results": data.get("phases", []),
    }
