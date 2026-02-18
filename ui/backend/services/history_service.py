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


def _read_all_entries() -> list[dict]:
    """Read all JSONL entries (with legacy fallback). Internal helper."""
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

    if not entries:
        entries = _read_legacy_history()

    return entries


def get_run_history(limit: int = 50, offset: int = 0) -> list[dict]:
    """Read run history from JSONL, newest first.

    Falls back to legacy ``run_report.json`` + archive when the JSONL
    file doesn't exist or is empty.
    """
    entries = _read_all_entries()

    # Enrich with token totals
    _enrich_tokens(entries)

    # Newest first
    entries.reverse()
    return entries[offset : offset + limit]


def get_history_stats() -> dict:
    """Compute aggregated operational stats across all run history."""
    entries = _read_all_entries()
    token_map = _aggregate_tokens()

    runs = [e for e in entries if e.get("trigger") != "reset"]
    resets = [e for e in entries if e.get("trigger") == "reset"]

    success_count = sum(1 for r in runs if r.get("status") == "completed")
    failed_count = sum(1 for r in runs if r.get("status") == "failed")
    total_runs = len(runs)

    # Average duration of completed runs
    durations = [r["duration_seconds"] for r in runs if r.get("status") == "completed" and r.get("duration_seconds")]
    avg_duration = sum(durations) / len(durations) if durations else 0.0

    # Total tokens from metrics
    total_tokens = sum(token_map.values())

    # Total deleted files from resets
    total_deleted = sum(r.get("deleted_count", 0) or 0 for r in resets)

    # Most used preset
    preset_counts: dict[str, int] = {}
    for r in runs:
        p = r.get("preset")
        if p:
            preset_counts[p] = preset_counts.get(p, 0) + 1
    most_used = max(preset_counts, key=preset_counts.get) if preset_counts else None  # type: ignore[arg-type]

    # Last run timestamp
    last_run = runs[-1].get("started_at") if runs else None

    # Phase frequency
    phase_freq: dict[str, int] = {}
    for r in runs:
        for ph in r.get("phases", []):
            phase_freq[ph] = phase_freq.get(ph, 0) + 1

    return {
        "total_runs": total_runs,
        "total_resets": len(resets),
        "success_count": success_count,
        "failed_count": failed_count,
        "success_rate": round(success_count / total_runs * 100, 1) if total_runs else 0.0,
        "avg_duration_seconds": round(avg_duration, 1),
        "total_tokens": total_tokens,
        "total_deleted_files": total_deleted,
        "most_used_preset": most_used,
        "last_run_at": last_run,
        "phase_frequency": phase_freq,
    }


def _metric_event_name(parsed: dict, data: dict) -> str:
    """Normalize metric event name across log shapes."""
    return data.get("event") or parsed.get("msg") or parsed.get("event") or ""


def _metric_run_id(parsed: dict, data: dict) -> str | None:
    """Normalize metric run_id across log shapes."""
    rid = data.get("run_id") or parsed.get("run_id")
    return str(rid) if rid else None


def _aggregate_tokens() -> dict[str, int]:
    """Scan metrics.jsonl for mini_crew_complete events and sum tokens by run_id."""
    metrics_path = settings.metrics_file
    token_map: dict[str, int] = {}

    if not metrics_path.exists():
        return token_map

    try:
        with open(metrics_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    parsed = json.loads(line)
                    data = parsed.get("data", {})
                    if _metric_event_name(parsed, data) != "mini_crew_complete":
                        continue
                    run_id = _metric_run_id(parsed, data)
                    tokens = data.get("total_tokens", 0) or data.get("tokens", 0) or 0
                    if run_id:
                        token_map[run_id] = token_map.get(run_id, 0) + tokens
                except json.JSONDecodeError:
                    continue
    except OSError as exc:
        logger.warning("Failed to read metrics for token aggregation: %s", exc)

    return token_map


def _enrich_tokens(entries: list[dict]) -> None:
    """Attach per-run token totals to history entries."""
    token_map = _aggregate_tokens()
    if not token_map:
        return
    for entry in entries:
        run_id = entry.get("run_id")
        engine_run_id = entry.get("engine_run_id")
        if run_id and run_id in token_map:
            entry["total_tokens"] = token_map[run_id]
        elif engine_run_id and engine_run_id in token_map:
            entry["total_tokens"] = token_map[engine_run_id]


def get_run_detail(run_id: str) -> dict | None:
    """Get detailed run info by run_id — combines JSONL entry + run_report + metrics."""
    path = _history_path()
    entry: dict | None = None

    # Search JSONL for matching run_id (UI run_id or engine_run_id)
    if path.exists() and path.stat().st_size > 0:
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        parsed = json.loads(line)
                        if parsed.get("run_id") == run_id or parsed.get("engine_run_id") == run_id:
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

    candidate_ids = {str(run_id)}
    if entry.get("run_id"):
        candidate_ids.add(str(entry["run_id"]))
    if entry.get("engine_run_id"):
        candidate_ids.add(str(entry["engine_run_id"]))

    # Enrich with run_report.json if the run matches current report
    if not entry.get("phase_results"):
        report_path = settings.run_report
        if report_path.exists():
            try:
                with open(report_path, encoding="utf-8") as f:
                    report = json.load(f)
                if str(report.get("run_id", "")) in candidate_ids:
                    entry["phase_results"] = report.get("phases", [])
                    entry["environment"] = report.get("environment", {})
                    entry.setdefault("run_outcome", report.get("run_outcome"))
            except (json.JSONDecodeError, OSError):
                pass

    # Enrich with filtered metrics events
    entry["metrics_events"] = _get_metrics_for_run_ids(candidate_ids)

    # Add environment info if not already present
    if not entry.get("environment"):
        entry["environment"] = {
            "knowledge_dir": str(settings.knowledge_dir),
            "logs_dir": str(settings.logs_dir),
        }

    return entry


def _get_metrics_for_run_ids(run_ids: set[str]) -> list[dict]:
    """Filter metrics.jsonl events for one or more run_ids."""
    metrics_path = settings.metrics_file
    events: list[dict] = []

    normalized_ids = {str(rid) for rid in run_ids if rid}
    if not metrics_path.exists() or not normalized_ids:
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
                    event_run_id = _metric_run_id(parsed, data)
                    if event_run_id in normalized_ids:
                        events.append(parsed)
                except json.JSONDecodeError:
                    continue
    except OSError as exc:
        logger.warning("Failed to read metrics: %s", exc)

    return events


def _read_legacy_history() -> list[dict]:
    """Read from run_report.json (legacy fallback)."""
    entries: list[dict] = []

    if settings.run_report.exists():
        try:
            with open(settings.run_report, encoding="utf-8") as f:
                data = json.load(f)
            entries.append(_format_legacy(data))
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Failed to parse run_report.json: %s", exc)

    return entries


def _format_legacy(data: dict) -> dict:
    """Convert a legacy run_report.json entry to history format."""
    return {
        "run_id": data.get("run_id", "unknown"),
        "status": data.get("status", "unknown"),
        "run_outcome": data.get("run_outcome"),
        "preset": data.get("environment", {}).get("preset"),
        "phases": data.get("planned_phases", []),
        "started_at": data.get("timestamp"),
        "completed_at": None,
        "duration": data.get("total_duration"),
        "duration_seconds": None,
        "trigger": "pipeline",
        "phase_results": data.get("phases", []),
    }
