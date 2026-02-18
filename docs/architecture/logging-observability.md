# Logging & Observability

Structured logging, metrics, and run correlation across all SDLC phases.

## Design Principles

1. **Single output path**: Everything through `logger`, zero `print()` in production code
2. **Structured metrics**: JSON events for every measurable phase, crew, guardrail, and tool event
3. **Run correlation**: `RUN_ID` (UUID) on every metric event for cross-event joining
4. **Dead code removal**: No unused callback classes or alias wrappers

## Log Structure

```
logs/
├── current.log          # Active session (overwritten each run)
├── metrics.jsonl        # Structured JSON metrics (append-only)
├── run_history.jsonl    # Pipeline run history (append-only)
└── errors.log           # Persistent errors (rotating, 5MB x 3)
```

## Run Correlation

Every process generates a `RUN_ID` (e.g., `a3f8b2c1`) — a short UUID injected into:
- Every `log_metric()` event in `metrics.jsonl`
- The session banner in `current.log`

```
============================================================
SESSION START: 2026-02-07T23:40:28 | run_id=a3f8b2c1
Log Level: INFO
============================================================
```

Query all events from a single run:
```bash
python -c "import json; [print(json.loads(l)['data']) for l in open('logs/metrics.jsonl') if 'a3f8b2c1' in l]"
```

## Step Logging API

```python
from .shared.utils.logger import (
    step_start,     # [STEP] ══════ Name ══════
    step_done,      # [DONE] ══════ Name ══════ (12.3s)
    step_fail,      # [FAIL] ══════ Name ══════
    step_info,      #        Info message
    step_warn,      #        Warning message
    step_progress,  #        [██████░░░░] 5/10 - items
    log_metric,     # Structured JSON event → metrics.jsonl
    RUN_ID,         # Short UUID for this process
)
```

## Structured Metrics (metrics.jsonl)

Each line is a JSON object with `run_id` for correlation:

```json
{"ts": "2026-02-07T14:30:00", "level": "INFO", "logger": "aicodegencrew", "msg": "mini_crew_complete", "data": {"event": "mini_crew_complete", "run_id": "a3f8b2c1", "crew_type": "C4", "crew_name": "context", "duration_seconds": 180.5, "total_tokens": 1500, "estimated": false}}
```

### Event Catalog

| Event | Source | Key Fields |
|-------|--------|------------|
| `phase_start` | orchestrator | `phase_id` |
| `phase_complete` | orchestrator | `phase_id`, `duration_seconds`, `status` |
| `phase_failed` | orchestrator | `phase_id`, `duration_seconds`, `error` |
| `pipeline_complete` | orchestrator | `status`, `total_duration`, `phases_run`, `phases_succeeded` |
| `mini_crew_complete` | base_crew / crew.py | `crew_type`, `crew_name`, `duration_seconds`, `tasks`, `attempts`, `total_tokens`, `estimated` |
| `mini_crew_failed` | base_crew / crew.py | `crew_type`, `crew_name`, `duration_seconds`, `error_type`, `error` |
| `guardrail_blocked` | tool_guardrails | `tool_name`, `reason` (`identical_call` / `budget_exhausted`) |
| `guardrail_summary` | base_crew / crew.py | `crew_name`, `total_calls`, `unique_calls`, `blocked` |

All events share `run_id` for correlation.

## CrewAI Callbacks

Agent step and task callbacks (`crew_callbacks.py`) route through `logger`:

| Event | Log Level | Destination | Example |
|-------|-----------|-------------|---------|
| Agent thinking | `DEBUG` | File only | `[THINK] Architect: Analyzing macro...` |
| Tool call | `INFO` | File + console | `[TOOL] get_statistics: {}` |
| Tool result | `DEBUG` | File only | `[TOOL_RESULT] {"components": 951...}` |
| Task completion | `INFO` | File + console | `[TASK] Completed: Analyze macro arch...` |

## Features

| Feature | Description |
|---------|-------------|
| **Run Correlation** | `RUN_ID` (uuid4[:8]) on every metric event |
| **Run History** | Append-only `run_history.jsonl` tracking all pipeline runs and resets |
| **Step Tracking** | Automatic timing per step |
| **Progress Bar** | Visual progress with `step_progress()` |
| **Structured Metrics** | JSON events in `metrics.jsonl` via `log_metric()` |
| **Guardrail Metrics** | Blocked tool calls + summary stats per crew |
| **Token Tracking** | Real token counts when available, `estimated=true` as fallback |
| **Unbuffered** | Real-time log viewing |
| **Singleton** | Logger initialized once |
| **MCP-Safe** | Console logging disabled when `MCP_STDIO_MODE` is set |
