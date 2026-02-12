"""
Tool Call Guardrails
====================
Prevents on-prem model failure modes:
- Identical tool call loops (same tool + same args repeated)
- Runaway tool usage (exceeding total call budget)

Uses CrewAI's native before_tool_call hook to block calls at the
framework level, without touching MCP tools or doc_writer.

Usage:
    tracker = install_guardrails()
    try:
        crew.kickoff(...)
    finally:
        uninstall_guardrails(tracker)
"""

import json
import logging

from crewai.hooks.tool_hooks import (
    register_before_tool_call_hook,
    unregister_before_tool_call_hook,
)

from .logger import log_metric

logger = logging.getLogger(__name__)

# Tools that are always allowed (output-producing tools)
_OUTPUT_TOOLS = frozenset({"doc_writer", "create_drawio_diagram"})


class ToolCallTracker:
    """Tracks tool calls per crew execution and enforces budgets.

    Budgets:
    - max_identical: block after N identical calls (same tool + same args)
    - max_total: after N total calls, only allow output tools (doc_writer, etc.)
    """

    def __init__(self, max_identical: int = 3, max_total: int = 25):
        self.max_identical = max_identical
        self.max_total = max_total
        self.calls: list[str] = []  # list of "tool:args_hash" keys
        self._hook_ref = None

    def _make_key(self, tool_name: str, tool_input: dict) -> str:
        """Create a deterministic key from tool name + input."""
        try:
            args_str = json.dumps(tool_input, sort_keys=True, default=str)
        except (TypeError, ValueError):
            args_str = str(tool_input)
        return f"{tool_name}:{args_str}"

    def _before_hook(self, context) -> bool | None:
        """CrewAI before_tool_call hook. Return False to block."""
        tool_name = context.tool_name
        tool_input = context.tool_input or {}
        key = self._make_key(tool_name, tool_input)

        # Always allow output tools
        is_output_tool = tool_name in _OUTPUT_TOOLS

        # Check identical-call budget
        if not is_output_tool:
            identical_count = sum(1 for c in self.calls if c == key)
            if identical_count >= self.max_identical:
                logger.warning(
                    f"[GUARDRAIL] Blocked: {tool_name} called {identical_count}x "
                    f"with identical args. Synthesize and call doc_writer now."
                )
                log_metric("guardrail_blocked", tool_name=tool_name, reason="identical_call")
                return False  # Block execution

        # Check total budget
        if len(self.calls) >= self.max_total and not is_output_tool:
            logger.warning(
                f"[GUARDRAIL] Budget exhausted ({self.max_total} calls). "
                f"Blocked: {tool_name}. Agent must call doc_writer."
            )
            log_metric("guardrail_blocked", tool_name=tool_name, reason="budget_exhausted")
            return False  # Block non-output tools

        # Allow and track
        self.calls.append(key)
        if len(self.calls) % 5 == 0:
            logger.info(
                f"[GUARDRAIL] Tool call #{len(self.calls)}: {tool_name} (budget: {len(self.calls)}/{self.max_total})"
            )
        return None  # Allow

    def install(self) -> None:
        """Register the before_tool_call hook with CrewAI."""
        self._hook_ref = self._before_hook
        register_before_tool_call_hook(self._hook_ref)
        logger.info(f"[GUARDRAIL] Installed (max_identical={self.max_identical}, max_total={self.max_total})")

    def uninstall(self) -> None:
        """Unregister the hook (prevents cross-crew leaking)."""
        if self._hook_ref:
            unregister_before_tool_call_hook(self._hook_ref)
            total = len(self.calls)
            unique = len(set(self.calls))
            logger.info(
                f"[GUARDRAIL] Uninstalled. Stats: {total} total calls, {unique} unique, {total - unique} duplicates"
            )
            self._hook_ref = None


def install_guardrails(max_identical: int = 3, max_total: int = 25) -> ToolCallTracker:
    """Create and install a ToolCallTracker for a crew execution.

    Args:
        max_identical: Max times same tool+args can be called before blocking.
        max_total: Max total tool calls before only output tools are allowed.

    Returns:
        The tracker instance (pass to uninstall_guardrails).
    """
    tracker = ToolCallTracker(max_identical=max_identical, max_total=max_total)
    tracker.install()
    return tracker


def uninstall_guardrails(tracker: ToolCallTracker | None) -> None:
    """Uninstall guardrails for a crew execution.

    Safe to call with None (no-op).
    """
    if tracker is not None:
        tracker.uninstall()
