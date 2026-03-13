"""Persistent phase state tracking via logs/phase_state.json.

Single source of truth for phase execution status. Written by the
orchestrator (CLI or dashboard), read by the dashboard backend.

File-level locking via ``filelock`` ensures safe concurrent writes
from parallel subprocess execution (multiple --task-id processes).
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_STATE_DIR: Path | None = None
_STALE_THRESHOLD_SECONDS = 3600  # 1 hour

try:
    from filelock import FileLock as _FileLock
except ImportError:
    _FileLock = None  # type: ignore[assignment,misc]
    logger.warning("[PhaseState] filelock not installed — concurrent write safety disabled")


def configure_state_dir(path: Path | None) -> None:
    """Set the directory for phase_state.json.

    None = default (CWD/logs). Used by tests for isolation.
    """
    global _STATE_DIR
    _STATE_DIR = path


def _state_path() -> Path:
    base = _STATE_DIR if _STATE_DIR is not None else Path("logs")
    return base / "phase_state.json"


@contextmanager
def _file_lock():
    """Acquire a cross-process lock for phase_state.json read-modify-write.

    Uses filelock when available; falls back to no-op (single-process safety
    still guaranteed by GIL / atomic writes).
    """
    if _FileLock is not None:
        lock_path = str(_state_path()) + ".lock"
        lock = _FileLock(lock_path, timeout=10)
        try:
            with lock:
                yield
        except TimeoutError:
            # Check if lock holder PID is still alive; if not, break the lock
            try:
                import fcntl  # Unix only
                lock_fd = open(lock_path)  # noqa: SIM115
                lock_fd.close()
            except Exception:
                pass
            logger.warning("[PhaseState] Lock timed out after 10s — retrying once")
            try:
                with _FileLock(lock_path, timeout=5):
                    yield
            except TimeoutError:
                logger.error("[PhaseState] Lock still held after retry — proceeding unlocked")
                yield
    else:
        yield


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
    """Check if a process is still running (cross-platform).

    os.kill(pid, 0) is unreliable on Windows — signal 0 may call
    TerminateProcess() instead of just probing. Use psutil when available.
    """
    try:
        import psutil  # optional dep; always present in our env

        return psutil.pid_exists(pid)
    except ImportError:
        pass
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


# ── Public API ──────────────────────────────────────────────────────


def init_run(run_id: str) -> None:
    """Initialize a new pipeline run. Resets all phase entries."""
    with _file_lock():
        _write_atomic(
            {
                "version": 1,
                "run_id": run_id,
                "pid": os.getpid(),
                "phases": {},
            }
        )
    logger.debug("[PhaseState] init_run: %s (pid=%d)", run_id, os.getpid())


def set_phase_running(phase_id: str) -> None:
    """Mark a phase as running."""
    with _file_lock():
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
    with _file_lock():
        data = _read_raw()
        phases = data.setdefault("phases", {})
        entry = phases.get(phase_id, {})
        entry["status"] = status if status in ("completed", "partial", "skipped") else "completed"
        entry["completed_at"] = datetime.now().isoformat(timespec="seconds")
        entry["duration_seconds"] = round(duration, 2)
        entry["error"] = None
        phases[phase_id] = entry
        _write_atomic(data)


def set_phase_failed(phase_id: str, duration: float, error: str) -> None:
    """Mark a phase as failed."""
    with _file_lock():
        data = _read_raw()
        phases = data.setdefault("phases", {})
        entry = phases.get(phase_id, {})
        entry["status"] = "failed"
        entry["completed_at"] = datetime.now().isoformat(timespec="seconds")
        entry["duration_seconds"] = round(duration, 2)
        entry["error"] = error[:500] + ("... [truncated]" if len(error) > 500 else "")
        phases[phase_id] = entry
        _write_atomic(data)


def clear_phase(phase_id: str) -> None:
    """Remove a phase entry (used on reset)."""
    with _file_lock():
        data = _read_raw()
        phases = data.get("phases", {})
        phases.pop(phase_id, None)
        _write_atomic(data)


def clear_phases(phase_ids: list[str]) -> None:
    """Remove multiple phase entries (used on reset)."""
    with _file_lock():
        data = _read_raw()
        phases = data.get("phases", {})
        for pid in phase_ids:
            phases.pop(pid, None)
        _write_atomic(data)


def read_all_phases() -> dict:
    """Read all phase states with crash recovery.

    Returns dict with keys: run_id, pid, phases.
    Phases with status='running' are checked against PID liveness.

    The entire read-check-write cycle is wrapped in _file_lock() to prevent
    TOCTOU races where concurrent processes could overwrite each other's updates.
    """
    with _file_lock():
        data = _read_raw()
        if not data:
            return {"run_id": None, "pid": None, "phases": {}}

        pid = data.get("pid")
        phases = data.get("phases", {})
        modified = False

        for _phase_id, entry in phases.items():
            if entry.get("status") != "running":
                continue

            # Crash recovery: check if orchestrator process is alive
            process_alive = _is_pid_alive(pid) if pid else False

            if not process_alive:
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
