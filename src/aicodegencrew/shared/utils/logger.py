"""
Logging System - Simple, Structured, Archived

Log Structure:
    logs/
    ├── current.log          # Active session (overwritten each run)
    ├── archive/             # Archived sessions
    │   ├── 2026-02-03_11-30-00_session.log
    │   └── ...
    └── errors.log           # Persistent error log (rotating)

Step Logging:
    step_start("Indexing")     → [STEP] ══════ Indexing ══════
    step_done("Indexing")      → [DONE] ══════ Indexing ══════ (12.3s)
    step_fail("Indexing", err) → [FAIL] ══════ Indexing ══════
"""

from __future__ import annotations

import atexit
import logging
import os
import shutil
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import ClassVar


# =============================================================================
# Configuration
# =============================================================================

LOG_DIR = Path("logs")
ARCHIVE_DIR = LOG_DIR / "archive"
CURRENT_LOG = LOG_DIR / "current.log"
ERRORS_LOG = LOG_DIR / "errors.log"

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
    _instance: ClassVar["StepTracker | None"] = None
    
    @classmethod
    def get(cls) -> "StepTracker":
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
        
        line = f"══════ {name} ══════"
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
        
        line = f"══════ {step} ══════"
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
        
        line = f"══════ {step} ══════"
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
            self._logger.warning(f"       ⚠ {message}")
    
    def progress(self, current: int, total: int, item: str = "") -> None:
        """Log progress within current step."""
        pct = (current / total * 100) if total > 0 else 0
        bar = "█" * int(pct // 5) + "░" * (20 - int(pct // 5))
        msg = f"[{bar}] {current}/{total}"
        if item:
            msg += f" - {item}"
        if self._logger:
            self._logger.info(f"       {msg}")


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


def cleanup_old_archives() -> int:
    """Remove old archive files. Returns number of files removed."""
    if not ARCHIVE_DIR.exists():
        return 0
    
    archives = sorted(ARCHIVE_DIR.glob("*_session.log"), reverse=True)
    removed = 0
    for old_archive in archives[MAX_ARCHIVE_FILES:]:
        old_archive.unlink()
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
    
    # Only do full setup once (for main logger)
    if not _initialized and name == "aicodegencrew":
        _initialized = True
        
        # Create directories
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        
        # Archive previous session
        archive_current_log()
        
        # ==========================================================================
        # Console Handler - Clean, readable format
        # ==========================================================================
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(log_level)
        console.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        logger.addHandler(console)
        
        # ==========================================================================
        # Session Log - current.log (overwritten each run, detailed)
        # ==========================================================================
        try:
            session = logging.FileHandler(CURRENT_LOG, mode='w', encoding='utf-8')
            session.setLevel(logging.DEBUG)
            session.setFormatter(logging.Formatter(
                '%(asctime)s.%(msecs)03d │ %(levelname)-5s │ %(message)s',
                datefmt='%H:%M:%S'
            ))
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
                ERRORS_LOG,
                maxBytes=MAX_ERROR_SIZE,
                backupCount=MAX_ERROR_BACKUPS,
                encoding='utf-8'
            )
            errors.setLevel(logging.ERROR)
            errors.setFormatter(logging.Formatter(
                '%(asctime)s │ %(name)s │ %(funcName)s:%(lineno)d\n'
                '  %(message)s\n',
                datefmt='%Y-%m-%d %H:%M:%S'
            ))
            logger.addHandler(errors)
        except Exception as e:
            print(f"[WARN] Could not create error log: {e}")
        
        logger.propagate = False
        
        # Connect step tracker
        StepTracker.get().set_logger(logger)
        
        # Log session start
        logger.info("=" * 60)
        logger.info(f"SESSION START: {datetime.now().isoformat()}")
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
    if status == "success":
        step_done(phase)
    else:
        step_fail(phase)


# Backward compatibility aliases
log_execution_start = log_phase_start
log_execution_end = log_phase_end


# =============================================================================
# Default Logger Instance
# =============================================================================

logger = setup_logger()


# =============================================================================
# Session End Hook
# =============================================================================

def _log_session_end() -> None:
    """Log session end on program exit."""
    try:
        logger.info("=" * 60)
        logger.info(f"SESSION END: {datetime.now().isoformat()}")
        logger.info("=" * 60)
    except Exception:
        pass


atexit.register(_log_session_end)
