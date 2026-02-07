"""Utilities package."""

from .logger import (
    setup_logger,
    logger,
    log_metric,
    RUN_ID,
    step_start,
    step_done,
    step_fail,
    step_info,
    step_warn,
    step_progress,
)
from .file_filters import should_include_file, collect_files
from .ollama_client import OllamaClient
from .tool_guardrails import install_guardrails, uninstall_guardrails

__all__ = [
    "setup_logger",
    "logger",
    "log_metric",
    "RUN_ID",
    "step_start",
    "step_done",
    "step_fail",
    "step_info",
    "step_warn",
    "step_progress",
    "should_include_file",
    "collect_files",
    "OllamaClient",
    "install_guardrails",
    "uninstall_guardrails",
]
