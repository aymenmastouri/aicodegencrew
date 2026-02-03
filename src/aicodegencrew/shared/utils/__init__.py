"""Utilities package."""

from .logger import (
    setup_logger,
    logger,
    log_execution_start,
    log_execution_end,
    step_start,
    step_done,
    step_fail,
    step_info,
    step_warn,
    step_progress,
)
from .file_filters import should_include_file, collect_files
from .ollama_client import OllamaClient

__all__ = [
    "setup_logger",
    "logger",
    "log_execution_start",
    "log_execution_end",
    "step_start",
    "step_done",
    "step_fail",
    "step_info",
    "step_warn",
    "step_progress",
    "should_include_file",
    "collect_files",
    "OllamaClient",
]
