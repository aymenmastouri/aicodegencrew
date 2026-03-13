"""Tests for logger, token_budget, and tool_guardrails utilities.

All tests run offline -- no LLM, no network, no CrewAI runtime.
CrewAI hook functions are mocked at the module level.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING
from unittest.mock import patch

if TYPE_CHECKING:
    from aicodegencrew.shared.utils.tool_guardrails import ToolCallTracker

import pytest

# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_step_tracker_singleton():
    """Reset StepTracker singleton between tests so each test is isolated."""
    from aicodegencrew.shared.utils.logger import StepTracker

    old = StepTracker._instance
    StepTracker._instance = None
    yield
    StepTracker._instance = old


@pytest.fixture()
def fresh_logger(tmp_path, monkeypatch):
    """Return a throwaway logger with a metrics handler writing to *tmp_path*.

    We build the logger and its JsonFormatter handler manually, then
    monkey-patch the module-level ``logger`` so that ``log_metric()`` writes
    to our temporary metrics file instead of the real one.
    """

    mod = sys.modules["aicodegencrew.shared.utils.logger"]
    metrics_file = tmp_path / "metrics.jsonl"

    # Build a standalone logger with a metrics handler
    unique_name = f"test_logger_{id(tmp_path)}"
    lg = logging.getLogger(unique_name)
    lg.setLevel(logging.DEBUG)

    handler = logging.FileHandler(str(metrics_file), mode="a", encoding="utf-8")
    handler.setLevel(logging.INFO)
    handler.setFormatter(mod.JsonFormatter())
    handler.addFilter(lambda r: hasattr(r, "metric_data"))
    lg.addHandler(handler)

    # Point the module-level ``logger`` at our test logger so ``log_metric``
    # (which uses the module-level ``logger``) writes to our tmp metrics file.
    monkeypatch.setattr(mod, "logger", lg)
    return lg, tmp_path


# ============================================================================
# Logger tests
# ============================================================================


class TestSetupLogger:
    """Tests for setup_logger()."""

    def test_returns_logger_instance(self):
        from aicodegencrew.shared.utils.logger import setup_logger

        lg = setup_logger(name="test_returns_instance")
        assert isinstance(lg, logging.Logger)

    def test_level_debug(self, monkeypatch):
        from aicodegencrew.shared.utils.logger import setup_logger

        lg = setup_logger(name="test_level_debug", level="DEBUG")
        # The logger itself is always set to DEBUG; the *console handler*
        # level reflects the requested level. The logger should accept DEBUG.
        assert lg.isEnabledFor(logging.DEBUG)

    def test_returns_same_logger_on_second_call(self):
        from aicodegencrew.shared.utils.logger import setup_logger

        lg1 = setup_logger(name="test_same_logger")
        lg2 = setup_logger(name="test_same_logger")
        assert lg1 is lg2


class TestRUNID:
    """RUN_ID must be an 8-character hexadecimal string."""

    def test_run_id_format(self):
        from aicodegencrew.shared.utils.logger import RUN_ID

        assert isinstance(RUN_ID, str)
        assert len(RUN_ID) == 8
        # uuid4 hex chars: 0-9 a-f and the possible hyphen at position 8
        # Since we slice [:8], it can include a hyphen when the uuid is
        # e.g. "abcdefgh-...".  Actually uuid4().hex would avoid that, but
        # the code uses str(uuid4())[:8] which CAN include a hyphen.
        # Verify that it matches the pattern produced by str(uuid4())[:8]:
        assert re.match(r"^[0-9a-f-]{8}$", RUN_ID), f"Unexpected RUN_ID: {RUN_ID}"


class TestStepTracker:
    """StepTracker singleton, timing, and progress bar."""

    def test_get_returns_singleton(self):
        from aicodegencrew.shared.utils.logger import StepTracker

        a = StepTracker.get()
        b = StepTracker.get()
        assert a is b

    def test_start_records_time(self):
        from aicodegencrew.shared.utils.logger import StepTracker

        tracker = StepTracker.get()
        tracker.start("my_step")
        assert "my_step" in tracker._steps
        assert isinstance(tracker._steps["my_step"], float)

    def test_done_returns_positive_duration(self):
        from aicodegencrew.shared.utils.logger import StepTracker

        tracker = StepTracker.get()
        tracker.start("dur_step")
        time.sleep(0.05)
        duration = tracker.done("dur_step")
        assert duration > 0

    def test_fail_returns_positive_duration(self):
        from aicodegencrew.shared.utils.logger import StepTracker

        tracker = StepTracker.get()
        tracker.start("fail_step")
        time.sleep(0.05)
        duration = tracker.fail("fail_step")
        assert duration > 0

    def test_done_without_start_returns_zero_like(self):
        """done() on an unknown step still returns a float (uses time.time() fallback)."""
        from aicodegencrew.shared.utils.logger import StepTracker

        tracker = StepTracker.get()
        # No start() called -- ``_steps.pop`` falls back to ``time.time()``
        # so duration will be ~0.
        duration = tracker.done("nonexistent")
        assert isinstance(duration, float)

    @pytest.mark.parametrize(
        "current, total, expected_hashes",
        [
            (0, 100, 0),  # 0%  -> 0 hashes
            (5, 100, 1),  # 5%  -> 1 hash
            (25, 100, 5),  # 25% -> 5 hashes
            (50, 100, 10),  # 50% -> 10 hashes
            (100, 100, 20),  # 100% -> 20 hashes
        ],
    )
    def test_progress_bar_rendering(self, current, total, expected_hashes):
        """Progress bar should be 20 chars wide, with 5% per '#' character."""
        from aicodegencrew.shared.utils.logger import StepTracker

        tracker = StepTracker.get()
        # Attach a simple logger so that the progress method actually builds
        # the bar string.  We capture the output via a handler.
        captured: list[str] = []

        class _CaptureHandler(logging.Handler):
            def emit(self, record):
                captured.append(self.format(record))

        lg = logging.getLogger(f"progress_test_{current}_{total}")
        lg.setLevel(logging.DEBUG)
        lg.addHandler(_CaptureHandler())
        tracker.set_logger(lg)

        tracker.progress(current, total)

        assert len(captured) == 1
        msg = captured[0]

        # Extract the bar between [ and ]
        match = re.search(r"\[([#-]{20})\]", msg)
        assert match is not None, f"No progress bar found in: {msg}"
        bar = match.group(1)
        assert bar.count("#") == expected_hashes
        assert bar.count("-") == 20 - expected_hashes

    def test_progress_zero_total(self):
        """progress(0, 0) should not crash (0% bar)."""
        from aicodegencrew.shared.utils.logger import StepTracker

        tracker = StepTracker.get()
        captured: list[str] = []

        class _CaptureHandler(logging.Handler):
            def emit(self, record):
                captured.append(self.format(record))

        lg = logging.getLogger("progress_zero")
        lg.setLevel(logging.DEBUG)
        lg.addHandler(_CaptureHandler())
        tracker.set_logger(lg)

        tracker.progress(0, 0)  # should not raise
        assert len(captured) == 1
        assert "[--------------------]" in captured[0]


class TestLogMetric:
    """log_metric() should write JSON lines to the metrics file."""

    def test_writes_json_to_metrics_file(self, fresh_logger):
        from aicodegencrew.shared.utils.logger import RUN_ID, log_metric

        lg, tmp_path = fresh_logger
        metrics_file = tmp_path / "metrics.jsonl"

        log_metric("test_event", foo="bar", count=42)

        # Flush handlers
        for h in lg.handlers:
            h.flush()

        assert metrics_file.exists(), "metrics.jsonl was not created"
        lines = [ln for ln in metrics_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert len(lines) >= 1

        # The last line should be our event
        entry = json.loads(lines[-1])
        assert "data" in entry
        assert entry["data"]["event"] == "test_event"
        assert entry["data"]["foo"] == "bar"
        assert entry["data"]["count"] == 42
        assert entry["data"]["run_id"] == RUN_ID

    def test_metric_format_has_ts_and_level(self, fresh_logger):
        from aicodegencrew.shared.utils.logger import log_metric

        lg, tmp_path = fresh_logger
        metrics_file = tmp_path / "metrics.jsonl"

        log_metric("format_check")
        for h in lg.handlers:
            h.flush()

        line = [ln for ln in metrics_file.read_text(encoding="utf-8").splitlines() if ln.strip()][-1]
        entry = json.loads(line)
        assert "ts" in entry
        assert "level" in entry
        assert entry["level"] == "INFO"


# ============================================================================
# Token budget tests
# ============================================================================


class TestTokenBudgetDefaults:
    """Verify default constants and derived values."""

    def test_default_input_tokens(self):
        from aicodegencrew.shared.utils.token_budget import MAX_LLM_INPUT_TOKENS

        assert MAX_LLM_INPUT_TOKENS == 100_000

    def test_default_output_tokens(self, monkeypatch):
        monkeypatch.delenv("MAX_LLM_OUTPUT_TOKENS", raising=False)
        # Re-import to pick up the clean default
        import importlib
        import aicodegencrew.shared.utils.token_budget as tb
        importlib.reload(tb)
        assert tb.MAX_LLM_OUTPUT_TOKENS == 16_000

    def test_tool_max_chars_calculation(self):
        from aicodegencrew.shared.utils.token_budget import (
            CHARS_PER_TOKEN,
            MAX_LLM_INPUT_TOKENS,
            TOOL_BUDGET_RATIO,
            TOOL_MAX_CHARS,
        )

        expected = int(MAX_LLM_INPUT_TOKENS * TOOL_BUDGET_RATIO) * CHARS_PER_TOKEN
        assert TOOL_MAX_CHARS == expected
        # With defaults: 100000 * 0.15 = 15000 tokens * 4 = 60000 chars
        assert TOOL_MAX_CHARS == 60_000

    def test_get_max_response_chars(self):
        from aicodegencrew.shared.utils.token_budget import (
            TOOL_MAX_CHARS,
            get_max_response_chars,
        )

        assert get_max_response_chars() == TOOL_MAX_CHARS

    def test_get_rag_max_chars(self):
        from aicodegencrew.shared.utils.token_budget import (
            TOOL_MAX_CHARS,
            get_rag_max_chars,
        )

        expected = int(TOOL_MAX_CHARS * 0.75)
        assert get_rag_max_chars() == expected


class TestTruncateResponse:
    """truncate_response() behaviour."""

    def test_returns_unchanged_if_within_limit(self):
        from aicodegencrew.shared.utils.token_budget import truncate_response

        text = "Hello, world!"
        result = truncate_response(text, max_chars=100)
        assert result == text

    def test_truncates_with_marker(self):
        from aicodegencrew.shared.utils.token_budget import truncate_response

        text = "A" * 200
        result = truncate_response(text, max_chars=50)
        assert result.startswith("A" * 50)
        assert "[TRUNCATED at 50 chars]" in result
        # Original text is not fully present
        assert len(result) < len(text) + 100  # marker is short

    def test_truncates_with_hint(self):
        from aicodegencrew.shared.utils.token_budget import truncate_response

        text = "B" * 200
        result = truncate_response(text, max_chars=50, hint="use pagination")
        assert "use pagination" in result
        assert "[TRUNCATED at 50 chars" in result

    def test_exact_boundary(self):
        from aicodegencrew.shared.utils.token_budget import truncate_response

        text = "C" * 100
        result = truncate_response(text, max_chars=100)
        # Exactly at limit -> no truncation
        assert result == text

    def test_default_max_chars_uses_tool_max(self):
        from aicodegencrew.shared.utils.token_budget import (
            truncate_response,
        )

        short = "x" * 10
        result = truncate_response(short)
        # Should return unchanged because 10 < TOOL_MAX_CHARS
        assert result == short


# ============================================================================
# Tool guardrails tests
# ============================================================================


@dataclass
class _FakeContext:
    """Mimics the CrewAI hook context object."""

    tool_name: str
    tool_input: dict | None = None


class TestToolCallTracker:
    """Tests for ToolCallTracker logic (hook mocked, no CrewAI runtime)."""

    def _make_tracker(self, **kwargs) -> ToolCallTracker:
        """Create a tracker without installing into CrewAI."""
        from aicodegencrew.shared.utils.tool_guardrails import ToolCallTracker

        return ToolCallTracker(**kwargs)

    # -- _make_key determinism ------------------------------------------------

    def test_make_key_deterministic(self):
        tracker = self._make_tracker()
        key1 = tracker._make_key("my_tool", {"a": 1, "b": 2})
        key2 = tracker._make_key("my_tool", {"b": 2, "a": 1})
        assert key1 == key2, "Keys should be identical regardless of dict order"

    def test_make_key_different_tools(self):
        tracker = self._make_tracker()
        k1 = tracker._make_key("tool_a", {"x": 1})
        k2 = tracker._make_key("tool_b", {"x": 1})
        assert k1 != k2

    def test_make_key_different_args(self):
        tracker = self._make_tracker()
        k1 = tracker._make_key("tool", {"x": 1})
        k2 = tracker._make_key("tool", {"x": 2})
        assert k1 != k2

    # -- Tracking calls -------------------------------------------------------

    def test_tracks_calls(self):
        tracker = self._make_tracker()
        ctx = _FakeContext(tool_name="search", tool_input={"q": "hello"})
        result = tracker._before_hook(ctx)
        assert result is None  # allowed
        assert len(tracker.calls) == 1

    def test_tracks_multiple_calls(self):
        tracker = self._make_tracker()
        for i in range(5):
            ctx = _FakeContext(tool_name="search", tool_input={"q": f"query_{i}"})
            tracker._before_hook(ctx)
        assert len(tracker.calls) == 5

    # -- Identical-call blocking -----------------------------------------------

    def test_blocks_after_max_identical(self):
        tracker = self._make_tracker(max_identical=3)
        ctx = _FakeContext(tool_name="search", tool_input={"q": "same"})

        # First 3 calls are allowed
        for _ in range(3):
            result = tracker._before_hook(ctx)
            assert result is None

        # 4th identical call is blocked
        result = tracker._before_hook(ctx)
        assert result is False

    def test_identical_blocking_counts_per_key(self):
        """Different args should not affect each other's budget."""
        tracker = self._make_tracker(max_identical=2)
        ctx_a = _FakeContext(tool_name="search", tool_input={"q": "aaa"})
        ctx_b = _FakeContext(tool_name="search", tool_input={"q": "bbb"})

        # Two calls for each key
        tracker._before_hook(ctx_a)
        tracker._before_hook(ctx_b)
        tracker._before_hook(ctx_a)
        tracker._before_hook(ctx_b)

        # Third call for A is blocked
        assert tracker._before_hook(ctx_a) is False
        # Third call for B is also blocked
        assert tracker._before_hook(ctx_b) is False

    # -- Total budget exhaustion -----------------------------------------------

    def test_blocks_after_max_total(self):
        tracker = self._make_tracker(max_total=5)

        for i in range(5):
            ctx = _FakeContext(tool_name="search", tool_input={"q": f"q{i}"})
            result = tracker._before_hook(ctx)
            assert result is None  # all allowed

        # 6th call is blocked (budget exhausted)
        ctx = _FakeContext(tool_name="search", tool_input={"q": "q5_new"})
        result = tracker._before_hook(ctx)
        assert result is False

    # -- Output tools always allowed -------------------------------------------

    def test_doc_writer_always_allowed(self):
        tracker = self._make_tracker(max_total=2, max_identical=1)

        # Exhaust the budget
        for i in range(2):
            ctx = _FakeContext(tool_name="search", tool_input={"q": f"q{i}"})
            tracker._before_hook(ctx)

        # doc_writer should still be allowed
        ctx = _FakeContext(tool_name="doc_writer", tool_input={"path": "out.md"})
        result = tracker._before_hook(ctx)
        assert result is None  # allowed

    def test_create_drawio_diagram_always_allowed(self):
        tracker = self._make_tracker(max_total=2, max_identical=1)

        # Exhaust the budget
        for i in range(2):
            ctx = _FakeContext(tool_name="search", tool_input={"q": f"q{i}"})
            tracker._before_hook(ctx)

        ctx = _FakeContext(
            tool_name="create_drawio_diagram",
            tool_input={"path": "diagram.drawio"},
        )
        result = tracker._before_hook(ctx)
        assert result is None  # allowed

    def test_output_tool_allowed_even_with_identical_calls(self):
        """doc_writer with identical args should never be blocked."""
        tracker = self._make_tracker(max_identical=1)
        ctx = _FakeContext(tool_name="doc_writer", tool_input={"path": "out.md"})

        # Call it many times with identical args
        for _ in range(10):
            result = tracker._before_hook(ctx)
            assert result is None  # always allowed

    # -- None tool_input -------------------------------------------------------

    def test_none_tool_input_treated_as_empty_dict(self):
        tracker = self._make_tracker()
        ctx = _FakeContext(tool_name="some_tool", tool_input=None)
        result = tracker._before_hook(ctx)
        assert result is None
        assert len(tracker.calls) == 1


class TestInstallUninstallGuardrails:
    """Test the install/uninstall convenience functions with mocked CrewAI hooks."""

    def test_install_returns_tracker(self):
        with patch("aicodegencrew.shared.utils.tool_guardrails.register_before_tool_call_hook") as mock_register:
            from aicodegencrew.shared.utils.tool_guardrails import install_guardrails

            tracker = install_guardrails(max_identical=5, max_total=50)
            assert tracker is not None
            assert tracker.max_identical == 5
            assert tracker.max_total == 50
            mock_register.assert_called_once()

    def test_uninstall_calls_unregister(self):
        with (
            patch("aicodegencrew.shared.utils.tool_guardrails.register_before_tool_call_hook"),
            patch("aicodegencrew.shared.utils.tool_guardrails.unregister_before_tool_call_hook") as mock_unregister,
        ):
            from aicodegencrew.shared.utils.tool_guardrails import (
                install_guardrails,
                uninstall_guardrails,
            )

            tracker = install_guardrails()
            uninstall_guardrails(tracker)
            mock_unregister.assert_called_once()

    def test_uninstall_none_is_noop(self):
        """uninstall_guardrails(None) should not raise."""
        from aicodegencrew.shared.utils.tool_guardrails import uninstall_guardrails

        uninstall_guardrails(None)  # no exception

    def test_stats_on_uninstall(self, capsys):
        """After some calls, uninstall should log stats (total, unique, duplicates)."""
        with (
            patch("aicodegencrew.shared.utils.tool_guardrails.register_before_tool_call_hook"),
            patch("aicodegencrew.shared.utils.tool_guardrails.unregister_before_tool_call_hook"),
        ):
            from aicodegencrew.shared.utils.tool_guardrails import (
                install_guardrails,
                uninstall_guardrails,
            )

            tracker = install_guardrails()

            # Simulate some calls
            tracker._before_hook(_FakeContext(tool_name="t1", tool_input={"a": 1}))
            tracker._before_hook(_FakeContext(tool_name="t1", tool_input={"a": 1}))
            tracker._before_hook(_FakeContext(tool_name="t2", tool_input={"b": 2}))

            assert len(tracker.calls) == 3
            assert len(set(tracker.calls)) == 2  # 2 unique

            # Uninstall logs stats via logger -- just verify no crash
            uninstall_guardrails(tracker)

    def test_double_uninstall_is_safe(self):
        """Calling uninstall twice should not raise."""
        with (
            patch("aicodegencrew.shared.utils.tool_guardrails.register_before_tool_call_hook"),
            patch("aicodegencrew.shared.utils.tool_guardrails.unregister_before_tool_call_hook"),
        ):
            from aicodegencrew.shared.utils.tool_guardrails import (
                install_guardrails,
                uninstall_guardrails,
            )

            tracker = install_guardrails()
            uninstall_guardrails(tracker)
            # Second uninstall -- _hook_ref is now None, should be a no-op
            uninstall_guardrails(tracker)
