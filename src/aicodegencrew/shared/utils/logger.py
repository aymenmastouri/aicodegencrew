"""
Logging System - Simple, Structured, Archived

Log Structure:
    logs/
    +-- current.log          # Active session (overwritten each run)
    +-- archive/             # Archived sessions
    |   +-- 2026-02-03_11-30-00_session.log
    |   +-- ...
    +-- errors.log           # Persistent error log (rotating)

Step Logging:
    step_start("Indexing")     -> [STEP] ====== Indexing ======
    step_done("Indexing")      -> [DONE] ====== Indexing ====== (12.3s)
    step_fail("Indexing", err) -> [FAIL] ====== Indexing ======
"""

from __future__ import annotations

import atexit
import json as _json
import logging
import os
import shutil
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import ClassVar

# Short UUID per process — injected into every metric for cross-event correlation
RUN_ID = str(uuid.uuid4())[:8]


# =============================================================================
# Run ID Filter — injects run_id into every log record for correlation
# =============================================================================


class RunIdFilter(logging.Filter):
    """Logging filter that adds ``run_id`` to every log record.

    This enables correlation of log messages across phases within a single
    pipeline run. The ``run_id`` field is available in format strings as
    ``%(run_id)s``.
    """

    def __init__(self, run_id: str | None = None):
        super().__init__()
        self.run_id = run_id or RUN_ID

    def filter(self, record: logging.LogRecord) -> bool:
        record.run_id = self.run_id  # type: ignore[attr-defined]
        return True


def set_run_id(new_run_id: str) -> None:
    """Update the run_id on all RunIdFilter instances attached to the logger.

    Called at pipeline start to set the correlation ID, and may be called
    at pipeline end to clear it.
    """
    global RUN_ID
    RUN_ID = new_run_id
    _logger = logging.getLogger("aicodegencrew")
    for handler in _logger.handlers:
        for f in handler.filters:
            if isinstance(f, RunIdFilter):
                f.run_id = new_run_id
    # Also update filters on the logger itself
    for f in _logger.filters:
        if isinstance(f, RunIdFilter):
            f.run_id = new_run_id


# =============================================================================
# Configuration
# =============================================================================

LOG_DIR = Path("logs")
ARCHIVE_DIR = LOG_DIR / "archive"
CURRENT_LOG = LOG_DIR / "current.log"
ERRORS_LOG = LOG_DIR / "errors.log"
METRICS_LOG = LOG_DIR / "metrics.jsonl"

MAX_ARCHIVE_FILES = 20  # Keep last 20 session logs
MAX_ERROR_SIZE = 5 * 1024 * 1024  # 5MB
MAX_ERROR_BACKUPS = 3


# =============================================================================
# Step Tracker - Track execution steps with timing
# =============================================================================


@dataclass
class StepTracker:
    """Track execution steps with timing and status."""

    _steps: dict[str, float] = field(default_factory=dict)
    _current: str | None = None
    _logger: logging.Logger | None = None

    # Class-level singleton
    _instance: ClassVar[StepTracker | None] = None

    @classmethod
    def get(cls) -> StepTracker:
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_logger(self, logger: logging.Logger) -> None:
        """Set the logger to use."""
        self._logger = logger

    def start(self, name: str, message: str = "") -> None:
        """Start a step."""
        self._current = name
        self._steps[name] = time.time()

        line = f"====== {name} ======"
        if self._logger:
            self._logger.info("")
            self._logger.info(f"[STEP] {line}")
            if message:
                self._logger.info(f"       {message}")

    def done(self, name: str | None = None, message: str = "") -> float:
        """Complete a step successfully. Returns duration in seconds."""
        step = name or self._current
        if not step:
            return 0.0

        start_time = self._steps.pop(step, time.time())
        duration = time.time() - start_time

        line = f"====== {step} ======"
        if self._logger:
            self._logger.info(f"[DONE] {line} ({duration:.1f}s)")
            if message:
                self._logger.info(f"       {message}")

        self._current = None
        return duration

    def fail(self, name: str | None = None, error: str = "") -> float:
        """Mark a step as failed. Returns duration in seconds."""
        step = name or self._current
        if not step:
            return 0.0

        start_time = self._steps.pop(step, time.time())
        duration = time.time() - start_time

        line = f"====== {step} ======"
        if self._logger:
            self._logger.error(f"[FAIL] {line} ({duration:.1f}s)")
            if error:
                self._logger.error(f"       {error}")

        self._current = None
        return duration

    def info(self, message: str) -> None:
        """Log info within current step."""
        if self._logger:
            self._logger.info(f"       {message}")

    def warn(self, message: str) -> None:
        """Log warning within current step."""
        if self._logger:
            self._logger.warning(f"       [WARN] {message}")

    def progress(self, current: int, total: int, item: str = "") -> None:
        """Log progress within current step."""
        pct = (current / total * 100) if total > 0 else 0
        bar = "#" * int(pct // 5) + "-" * (20 - int(pct // 5))
        msg = f"[{bar}] {current}/{total}"
        if item:
            msg += f" - {item}"
        if self._logger:
            self._logger.info(f"       {msg}")


# =============================================================================
# Run ID Formatter — safe format that never raises KeyError on run_id
# =============================================================================


class RunIdFormatter(logging.Formatter):
    """Formatter that injects ``run_id`` into log records before formatting.

    Standard ``logging.Formatter`` raises ``KeyError`` if the format string
    contains ``%(run_id)s`` but no filter has added the attribute to the
    record.  This subclass provides a safe default so that logging never
    crashes, even during early import-time logging before filters are wired.
    """

    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "run_id"):
            record.run_id = RUN_ID  # type: ignore[attr-defined]
        return super().format(record)


# =============================================================================
# JSON Formatter for structured logs (metrics.jsonl)
# =============================================================================


class JsonFormatter(logging.Formatter):
    """Outputs log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "run_id": getattr(record, "run_id", RUN_ID),
            "msg": record.getMessage(),
        }
        if hasattr(record, "metric_data"):
            entry["data"] = record.metric_data
        if record.exc_info and record.exc_info[1]:
            entry["error"] = str(record.exc_info[1])
        return _json.dumps(entry, default=str)


# =============================================================================
# Archive Management
# =============================================================================


def archive_current_log() -> None:
    """Archive current.log if it exists and is not locked."""
    if not CURRENT_LOG.exists():
        return

    # Check if log has content
    try:
        if CURRENT_LOG.stat().st_size == 0:
            return
    except OSError:
        return

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    # Create archive filename with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    archive_name = f"{timestamp}_session.log"
    archive_path = ARCHIVE_DIR / archive_name

    # Try to copy (not move) - safer on Windows with locked files
    try:
        shutil.copy2(CURRENT_LOG, archive_path)
    except (PermissionError, OSError):
        # File is locked, skip archiving this time
        return

    # Cleanup old archives (keep MAX_ARCHIVE_FILES)
    try:
        archives = sorted(ARCHIVE_DIR.glob("*_session.log"), reverse=True)
        for old_archive in archives[MAX_ARCHIVE_FILES:]:
            old_archive.unlink()
    except OSError:
        pass


def archive_metrics() -> None:
    """Archive metrics.jsonl if > 1MB."""
    if METRICS_LOG.exists():
        try:
            if METRICS_LOG.stat().st_size > 1_000_000:
                ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
                ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                shutil.copy2(METRICS_LOG, ARCHIVE_DIR / f"{ts}_metrics.jsonl")
                METRICS_LOG.write_text("", encoding="utf-8")
        except OSError:
            pass


def cleanup_old_archives(max_metrics: int = 5) -> int:
    """Remove old archive files. Returns number of files removed."""
    if not ARCHIVE_DIR.exists():
        return 0

    removed = 0

    # Session logs: keep MAX_ARCHIVE_FILES (20)
    for old in sorted(ARCHIVE_DIR.glob("*_session.log"), reverse=True)[MAX_ARCHIVE_FILES:]:
        old.unlink()
        removed += 1

    # Metrics archives: keep max_metrics (5)
    for old in sorted(ARCHIVE_DIR.glob("*_metrics.jsonl"), reverse=True)[max_metrics:]:
        old.unlink()
        removed += 1

    return removed


# =============================================================================
# Logger Setup
# =============================================================================

_initialized = False


def setup_logger(name: str = "aicodegencrew", level: str | None = None) -> logging.Logger:
    """Setup logger with archiving and step support.

    Args:
        name: Logger name
        level: Log level (default: from LOG_LEVEL env or INFO)

    Returns:
        Configured logger
    """
    global _initialized

    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO")

    log_level = getattr(logging, level.upper(), logging.INFO)

    # Return existing logger if already set up
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # Always attach RunIdFilter so %(run_id)s resolves even for child loggers
    # or when setup_logger is called before the root logger is initialised.
    logger.addFilter(RunIdFilter(RUN_ID))

    # Only do full setup once (for main logger)
    if not _initialized and name == "aicodegencrew":
        _initialized = True

        # Create directories
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        # Archive previous session and large metrics
        archive_current_log()
        archive_metrics()

        # ==========================================================================
        # Console Handler - Clean, readable format
        # Skip console logging if MCP_STDIO_MODE is set (corrupts JSON-RPC)
        # ==========================================================================
        if not os.getenv("MCP_STDIO_MODE"):
            # Use UTF-8 encoding for Windows console to handle emojis
            if sys.platform == "win32":
                import io

                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
                sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

            console = logging.StreamHandler(sys.stdout)
            console.setLevel(log_level)
            console.setFormatter(
                RunIdFormatter(
                    "%(asctime)s - %(name)s - %(levelname)s - [%(run_id)s] %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            console.addFilter(lambda r: not hasattr(r, "metric_data"))
            logger.addHandler(console)

        # ==========================================================================
        # Session Log - current.log (overwritten each run, detailed)
        # ==========================================================================
        try:
            session = logging.FileHandler(CURRENT_LOG, mode="w", encoding="utf-8")
            session.setLevel(logging.DEBUG)
            session.setFormatter(
                RunIdFormatter(
                    "%(asctime)s.%(msecs)03d | %(levelname)-5s | [%(run_id)s] %(message)s", datefmt="%H:%M:%S"
                )
            )
            session.addFilter(lambda r: not hasattr(r, "metric_data"))
            # Unbuffered for real-time viewing
            session.stream.reconfigure(write_through=True)
            logger.addHandler(session)
        except Exception as e:
            print(f"[WARN] Could not create session log: {e}")

        # ==========================================================================
        # Error Log - errors.log (persistent, rotating)
        # ==========================================================================
        try:
            errors = RotatingFileHandler(
                ERRORS_LOG, maxBytes=MAX_ERROR_SIZE, backupCount=MAX_ERROR_BACKUPS, encoding="utf-8"
            )
            errors.setLevel(logging.ERROR)
            errors.setFormatter(
                logging.Formatter(
                    "%(asctime)s | %(name)s | %(funcName)s:%(lineno)d\n  %(message)s\n", datefmt="%Y-%m-%d %H:%M:%S"
                )
            )
            logger.addHandler(errors)
        except Exception as e:
            print(f"[WARN] Could not create error log: {e}")

        # ==========================================================================
        # Metrics Log - metrics.jsonl (structured JSON, one line per event)
        # ==========================================================================
        try:
            metrics = logging.FileHandler(METRICS_LOG, mode="a", encoding="utf-8")
            metrics.setLevel(logging.INFO)
            metrics.setFormatter(JsonFormatter())
            metrics.addFilter(lambda r: hasattr(r, "metric_data"))
            logger.addHandler(metrics)
        except Exception as e:
            print(f"[WARN] Could not create metrics log: {e}")

        logger.propagate = False

        # Connect step tracker
        StepTracker.get().set_logger(logger)

        # Log session start
        logger.info("=" * 60)
        logger.info(f"SESSION START: {datetime.now().isoformat()} | run_id={RUN_ID}")
        logger.info(f"Log Level: {level.upper()}")
        logger.info("=" * 60)
    else:
        # For sub-loggers, just inherit from parent
        logger.propagate = True

    return logger


# =============================================================================
# Convenience Functions
# =============================================================================


def step_start(name: str, message: str = "") -> None:
    """Start a named step."""
    StepTracker.get().start(name, message)


def step_done(name: str | None = None, message: str = "") -> float:
    """Complete current or named step. Returns duration."""
    return StepTracker.get().done(name, message)


def step_fail(name: str | None = None, error: str = "") -> float:
    """Mark current or named step as failed. Returns duration."""
    return StepTracker.get().fail(name, error)


def step_info(message: str) -> None:
    """Log info within current step."""
    StepTracker.get().info(message)


def step_warn(message: str) -> None:
    """Log warning within current step."""
    StepTracker.get().warn(message)


def step_progress(current: int, total: int, item: str = "") -> None:
    """Log progress within current step."""
    StepTracker.get().progress(current, total, item)


def log_phase_start(phase: str) -> None:
    """Log phase start (alias for step_start)."""
    step_start(phase)


def log_phase_end(phase: str, status: str = "success", duration: float = 0) -> None:
    """Log phase end."""
    if status in ("success", "completed", "partial", "skipped"):
        step_done(phase, f"{status} in {duration:.2f}s" if duration else "")
    else:
        step_fail(phase, status)


def log_metric(event: str, **data) -> None:
    """Log a structured metric event to metrics.jsonl.

    Every event automatically includes ``run_id`` for cross-event correlation.
    When PROMETHEUS_ENABLED=true, phase metrics are also pushed to Prometheus counters.

    Usage:
        log_metric("mini_crew_complete", crew="context", duration=12.3, tokens=1500)
        log_metric("phase_complete", phase="phase3", files_created=8)
    """
    record = logger.makeRecord(
        logger.name,
        logging.INFO,
        "",
        0,
        event,
        (),
        None,
    )
    record.metric_data = {"event": event, "run_id": RUN_ID, **data}
    logger.handle(record)

    # Push phase metrics to Prometheus (no-op when disabled or package missing)
    if event == "phase_complete" and os.getenv("PROMETHEUS_ENABLED", "").strip().lower() in ("true", "1", "yes"):
        try:
            from ui.backend.routers.prometheus import record_phase_metric

            tokens = {k.replace("tokens_", ""): v for k, v in data.items() if k.startswith("tokens_")}
            record_phase_metric(
                phase_id=data.get("phase_id", "unknown"),
                duration=data.get("duration_seconds", 0),
                status=data.get("status", "unknown"),
                tokens=tokens or None,
            )
        except Exception:
            pass


# =============================================================================
# Default Logger Instance
# =============================================================================

logger = setup_logger()


# =============================================================================
# Session End Hook
# =============================================================================


def _log_session_end() -> None:
    """Log session end on program exit.

    During Python shutdown, stderr/stdout and handler streams may already be
    closed, causing ``ValueError: I/O operation on closed file``.
    Check every handler's stream before attempting to write.
    """
    try:
        for handler in logger.handlers:
            stream = getattr(handler, "stream", None)
            if stream is not None and getattr(stream, "closed", False):
                return
        logger.info("=" * 60)
        logger.info(f"SESSION END: {datetime.now().isoformat()}")
        logger.info("=" * 60)
    except Exception:
        pass


atexit.register(_log_session_end)
