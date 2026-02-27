"""Service for reading metrics.jsonl."""

import json

from ..config import settings
from ..schemas import MetricEvent, MetricsSummary


def read_metrics(limit: int = 200, event_filter: str | None = None) -> MetricsSummary:
    """Read metrics events from metrics.jsonl."""
    metrics_file = settings.metrics_file
    if not metrics_file.exists():
        return MetricsSummary(total_events=0, events=[], run_ids=[])

    events: list[MetricEvent] = []
    run_ids: set[str] = set()

    with open(metrics_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Skip structured log entries (they have 'level'/'msg' but no 'event').
            # Only metric events have an 'event' key.
            if "event" not in data:
                continue

            event_name = data.get("event", "")
            timestamp = data.get("timestamp", "")

            if "run_id" in data:
                run_ids.add(data["run_id"])

            if event_filter and event_name != event_filter:
                continue

            # Build payload without mutating the parsed dict
            payload = {k: v for k, v in data.items() if k not in ("event", "timestamp")}
            events.append(MetricEvent(timestamp=timestamp, event=event_name, data=payload))

    # Return most recent events first, up to limit
    events.reverse()
    return MetricsSummary(
        total_events=len(events),
        events=events[:limit],
        run_ids=sorted(run_ids),
    )
