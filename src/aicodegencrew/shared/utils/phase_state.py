"""Persistent phase state tracking via logs/phase_state.json.

Single source of truth for phase execution status. Written by the
orchestrator (CLI or dashboard), read by the dashboard backend.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_STATE_FILE = Path("logs") / "phase_state.json"
_STALE_THRESHOLD_SECONDS = 3600  # 1 hour


def _state_path() -> Path:
    return _STATE_FILE


def _read_raw() -> dict:
    """Read state file, return empty dict if missing or corrupt."""
    path = _state_path()
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read phase state file: %s", exc)
        return {}


def _write_atomic(data: dict) -> None:
    """Write state file atomically via tmp + os.replace."""
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = datetime.now().isoformat(timespec="seconds")

    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, str(path))
    except OSError:
        # Clean up temp file on failure
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _is_pid_alive(pid: int) -> bool:
    """Check if a process is still running."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


# ── Public API ──────────────────────────────────────────────────────


def init_run(run_id: str) -> None:
    """Initialize a new pipeline run. Resets all phase entries."""
    _write_atomic({
        "version": 1,
        "run_id": run_id,
        "pid": os.getpid(),
        "phases": {},
    })
    logger.debug("[PhaseState] init_run: %s (pid=%d)", run_id, os.getpid())


def set_phase_running(phase_id: str) -> None:
    """Mark a phase as running."""
    data = _read_raw()
    phases = data.setdefault("phases", {})
    phases[phase_id] = {
        "status": "running",
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "completed_at": None,
        "duration_seconds": None,
        "error": None,
    }
    _write_atomic(data)


def set_phase_completed(phase_id: str, duration: float, status: str = "completed") -> None:
    """Mark a phase as completed (or partial)."""
    data = _read_raw()
    phases = data.setdefault("phases", {})
    entry = phases.get(phase_id, {})
    entry["status"] = status if status in ("completed", "partial") else "completed"
    entry["completed_at"] = datetime.now().isoformat(timespec="seconds")
    entry["duration_seconds"] = round(duration, 2)
    entry["error"] = None
    phases[phase_id] = entry
    _write_atomic(data)


def set_phase_failed(phase_id: str, duration: float, error: str) -> None:
    """Mark a phase as failed."""
    data = _read_raw()
    phases = data.setdefault("phases", {})
    entry = phases.get(phase_id, {})
    entry["status"] = "failed"
    entry["completed_at"] = datetime.now().isoformat(timespec="seconds")
    entry["duration_seconds"] = round(duration, 2)
    entry["error"] = error[:500]
    phases[phase_id] = entry
    _write_atomic(data)


def clear_phase(phase_id: str) -> None:
    """Remove a phase entry (used on reset)."""
    data = _read_raw()
    phases = data.get("phases", {})
    phases.pop(phase_id, None)
    _write_atomic(data)


def clear_phases(phase_ids: list[str]) -> None:
    """Remove multiple phase entries (used on reset)."""
    data = _read_raw()
    phases = data.get("phases", {})
    for pid in phase_ids:
        phases.pop(pid, None)
    _write_atomic(data)


def read_all_phases() -> dict:
    """Read all phase states with crash recovery.

    Returns dict with keys: run_id, pid, phases.
    Phases with status='running' are checked against PID liveness.
    """
    data = _read_raw()
    if not data:
        return {"run_id": None, "pid": None, "phases": {}}

    pid = data.get("pid")
    phases = data.get("phases", {})
    modified = False

    for phase_id, entry in phases.items():
        if entry.get("status") != "running":
            continue

        # Crash recovery: check if orchestrator process is alive
        process_alive = _is_pid_alive(pid) if pid else False

        if not process_alive:
            # Check staleness as fallback
            started = entry.get("started_at", "")
            stale = False
            if started:
                try:
                    start_dt = datetime.fromisoformat(started)
                    elapsed = (datetime.now() - start_dt).total_seconds()
                    stale = elapsed > _STALE_THRESHOLD_SECONDS
                except ValueError:
                    stale = True

            if not process_alive or stale:
                entry["status"] = "failed"
                entry["error"] = "Process terminated unexpectedly"
                entry["completed_at"] = datetime.now().isoformat(timespec="seconds")
                modified = True

    if modified:
        _write_atomic(data)

    return {
        "run_id": data.get("run_id"),
        "pid": pid,
        "phases": phases,
    }
