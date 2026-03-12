"""
Tests for Parallel Task Execution — phase progress, run outcome, task states.

Covers the bug fix: in parallel mode, phase progress must be synthesised from
_task_states (not metrics.jsonl) because multiple subprocesses writing to the
same metrics file causes race conditions (first-to-finish marks phases as
"completed" while other task subprocesses are still running).

Scenarios:
- Phase progress synthesis from task states (running / completed / partial / failed / cancelled)
- Progress percent uses task completion fraction, not phase completion
- task_progress dict included in status response
- parallel_mode flag in status response
- run_outcome uses _parallel_outcome
- Normal (non-parallel) mode still reads from metrics.jsonl (backward compat)
- History entry captures parallel metadata
"""

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures  (reuse pattern from test_progress_and_ux.py)
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_project(tmp_path):
    """Create a temporary project structure."""
    (tmp_path / "knowledge").mkdir()
    (tmp_path / "logs").mkdir()
    (tmp_path / "config").mkdir()
    (tmp_path / ".cache" / ".chroma").mkdir(parents=True)

    (tmp_path / "config" / "phases_config.yaml").write_text(
        """
phases:
  triage:
    enabled: true
    name: "Triage"
    order: 0
    dependencies: []
  plan:
    enabled: true
    name: "Development Planning"
    order: 1
    dependencies: [triage]
  implement:
    enabled: true
    name: "Code Generation"
    order: 2
    dependencies: [plan]
"""
    )
    return tmp_path


@pytest.fixture()
def mock_settings(tmp_project):
    """Patch settings for pipeline_executor and history_service."""
    with (
        patch("ui.backend.services.pipeline_executor.settings") as se,
        patch("ui.backend.services.history_service.settings") as sh,
    ):
        se.project_root = tmp_project
        se.knowledge_dir = tmp_project / "knowledge"
        se.phases_config = tmp_project / "config" / "phases_config.yaml"
        se.metrics_file = tmp_project / "logs" / "metrics.jsonl"
        se.run_report = tmp_project / "knowledge" / "run_report.json"
        se.run_history = tmp_project / "logs" / "run_history.jsonl"
        se.logs_dir = tmp_project / "logs"
        se.env_file = tmp_project / ".env"

        sh.project_root = tmp_project
        sh.knowledge_dir = tmp_project / "knowledge"
        sh.run_report = tmp_project / "knowledge" / "run_report.json"
        sh.run_history = tmp_project / "logs" / "run_history.jsonl"
        sh.logs_dir = tmp_project / "logs"
        sh.metrics_file = tmp_project / "logs" / "metrics.jsonl"

        yield se


@pytest.fixture()
def metrics_file(tmp_project):
    """Return path to the metrics.jsonl file."""
    return tmp_project / "logs" / "metrics.jsonl"


def write_metrics(metrics_file: Path, events: list[dict]) -> None:
    with open(metrics_file, "w", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")


def _make_executor(*, parallel_mode=True, phases=None, task_ids=None, state="running"):
    """Create a fresh PipelineExecutor instance with parallel mode configured."""
    from ui.backend.services.pipeline_executor import PipelineExecutor, RunInfo

    executor = PipelineExecutor.__new__(PipelineExecutor)
    executor._init()
    executor.state = state
    executor.current_run = RunInfo(
        run_id="test_run",
        preset=None,
        phases=phases or ["triage", "plan"],
        started_at="2026-02-28T10:00:00",
        parallel_mode=parallel_mode,
        task_ids=task_ids or [],
    )
    executor._started_at = time.monotonic() - 30
    executor._finished_at = None

    if parallel_mode and task_ids:
        with executor._task_states_lock:
            executor._task_states = {
                tid: {"state": "pending", "pid": None, "exit_code": None, "log_lines": []}
                for tid in task_ids
            }

    return executor


# =============================================================================
# Phase Progress Synthesis — The Core Bug Fix
# =============================================================================


class TestParallelPhaseProgressSynthesis:
    """Verify that parallel mode synthesises phase progress from task states,
    NOT from metrics.jsonl (which has race conditions)."""

    def test_running_phases_show_running_even_if_metrics_says_completed(
        self, mock_settings, metrics_file
    ):
        """THE BUG: First subprocess completing writes phase_complete to metrics.
        But other tasks are still running. Phase stepper must NOT show 'completed'."""
        # Simulate the race condition: metrics.jsonl says both phases completed
        # (from the first subprocess that finished), but executor is still "running"
        write_metrics(
            metrics_file,
            [
                {"msg": "phase_start", "data": {"event": "phase_start", "phase": "triage", "name": "Triage"}},
                {"msg": "phase_complete", "data": {"event": "phase_complete", "phase": "triage", "duration_seconds": 30}},
                {"msg": "phase_start", "data": {"event": "phase_start", "phase": "plan", "name": "Plan"}},
                {"msg": "phase_complete", "data": {"event": "phase_complete", "phase": "plan", "duration_seconds": 60}},
            ],
        )

        executor = _make_executor(
            task_ids=["TASK-001", "TASK-002"],
            state="running",
        )
        # Task 1 completed, Task 2 still running
        with executor._task_states_lock:
            executor._task_states["TASK-001"]["state"] = "completed"
            executor._task_states["TASK-001"]["exit_code"] = 0
            executor._task_states["TASK-002"]["state"] = "running"
            executor._task_states["TASK-002"]["pid"] = 12345

        status = executor.get_status()

        # Both phases MUST show "running" — NOT "completed"
        assert status["state"] == "running"
        for phase in status["phase_progress"]:
            assert phase["status"] == "running", (
                f"Phase {phase['phase_id']} shows '{phase['status']}' but should be 'running' "
                f"because TASK-002 is still running"
            )

    def test_all_tasks_completed_phases_show_completed(self, mock_settings):
        """When all tasks succeed, phases should show 'completed'."""
        executor = _make_executor(
            task_ids=["TASK-001", "TASK-002"],
            state="completed",
        )
        executor._parallel_outcome = "success"
        executor._finished_at = time.monotonic()

        with executor._task_states_lock:
            for tid in ("TASK-001", "TASK-002"):
                executor._task_states[tid]["state"] = "completed"
                executor._task_states[tid]["exit_code"] = 0

        status = executor.get_status()

        assert status["state"] == "completed"
        for phase in status["phase_progress"]:
            assert phase["status"] == "completed"

    def test_some_tasks_failed_phases_show_partial(self, mock_settings):
        """When some tasks succeed but others fail → phases show 'partial'."""
        executor = _make_executor(
            task_ids=["TASK-001", "TASK-002"],
            state="completed",
        )
        executor._parallel_outcome = "partial"
        executor._finished_at = time.monotonic()

        with executor._task_states_lock:
            executor._task_states["TASK-001"]["state"] = "completed"
            executor._task_states["TASK-001"]["exit_code"] = 0
            executor._task_states["TASK-002"]["state"] = "failed"
            executor._task_states["TASK-002"]["exit_code"] = 1

        status = executor.get_status()

        for phase in status["phase_progress"]:
            assert phase["status"] == "partial"

    def test_all_tasks_failed_phases_show_failed(self, mock_settings):
        """When ALL tasks fail → phases show 'failed'."""
        executor = _make_executor(
            task_ids=["TASK-001", "TASK-002"],
            state="failed",
        )
        executor._parallel_outcome = "failed"
        executor._finished_at = time.monotonic()

        with executor._task_states_lock:
            for tid in ("TASK-001", "TASK-002"):
                executor._task_states[tid]["state"] = "failed"
                executor._task_states[tid]["exit_code"] = 1

        status = executor.get_status()

        for phase in status["phase_progress"]:
            assert phase["status"] == "failed"

    def test_cancelled_phases_show_cancelled(self, mock_settings):
        """After cancellation, phases show 'cancelled'."""
        executor = _make_executor(
            task_ids=["TASK-001", "TASK-002"],
            state="cancelled",
        )
        executor._finished_at = time.monotonic()

        with executor._task_states_lock:
            executor._task_states["TASK-001"]["state"] = "completed"
            executor._task_states["TASK-001"]["exit_code"] = 0
            executor._task_states["TASK-002"]["state"] = "cancelled"

        status = executor.get_status()

        for phase in status["phase_progress"]:
            assert phase["status"] == "cancelled"

    def test_phase_progress_has_correct_phase_ids(self, mock_settings):
        """Phase progress entries match the requested phases."""
        executor = _make_executor(
            phases=["triage", "plan", "implement"],
            task_ids=["T1"],
            state="running",
        )
        with executor._task_states_lock:
            executor._task_states["T1"]["state"] = "running"

        status = executor.get_status()

        ids = [p["phase_id"] for p in status["phase_progress"]]
        assert ids == ["triage", "plan", "implement"]

    def test_phase_progress_names_are_humanized(self, mock_settings):
        """Phase names are title-cased from phase_id."""
        executor = _make_executor(
            phases=["triage", "plan"],
            task_ids=["T1"],
            state="running",
        )
        with executor._task_states_lock:
            executor._task_states["T1"]["state"] = "running"

        status = executor.get_status()

        names = [p["name"] for p in status["phase_progress"]]
        assert names == ["Triage", "Plan"]


# =============================================================================
# Progress Percent — Uses Task Completion, Not Phase Completion
# =============================================================================


class TestParallelProgressPercent:
    """In parallel mode, progress = tasks_done / total_tasks * 100."""

    def test_no_tasks_done_zero_percent(self, mock_settings):
        executor = _make_executor(task_ids=["T1", "T2", "T3"], state="running")
        with executor._task_states_lock:
            for tid in ("T1", "T2", "T3"):
                executor._task_states[tid]["state"] = "running"

        status = executor.get_status()
        assert status["progress_percent"] == 0.0

    def test_one_of_two_tasks_done_fifty_percent(self, mock_settings):
        executor = _make_executor(task_ids=["T1", "T2"], state="running")
        with executor._task_states_lock:
            executor._task_states["T1"]["state"] = "completed"
            executor._task_states["T1"]["exit_code"] = 0
            executor._task_states["T2"]["state"] = "running"

        status = executor.get_status()
        assert status["progress_percent"] == 50.0

    def test_one_of_three_tasks_failed_counts_as_done(self, mock_settings):
        """Failed tasks count towards progress (they are 'done')."""
        executor = _make_executor(task_ids=["T1", "T2", "T3"], state="running")
        with executor._task_states_lock:
            executor._task_states["T1"]["state"] = "failed"
            executor._task_states["T1"]["exit_code"] = 1
            executor._task_states["T2"]["state"] = "running"
            executor._task_states["T3"]["state"] = "pending"

        status = executor.get_status()
        assert status["progress_percent"] == pytest.approx(33.3, abs=0.1)

    def test_all_done_terminal_state_hundred_percent(self, mock_settings):
        executor = _make_executor(task_ids=["T1", "T2"], state="completed")
        executor._parallel_outcome = "success"
        executor._finished_at = time.monotonic()
        with executor._task_states_lock:
            executor._task_states["T1"]["state"] = "completed"
            executor._task_states["T2"]["state"] = "completed"

        status = executor.get_status()
        assert status["progress_percent"] == 100.0

    def test_single_task_running_zero_percent(self, mock_settings):
        executor = _make_executor(task_ids=["T1"], state="running")
        with executor._task_states_lock:
            executor._task_states["T1"]["state"] = "running"

        status = executor.get_status()
        assert status["progress_percent"] == 0.0

    def test_single_task_completed_hundred_percent(self, mock_settings):
        executor = _make_executor(task_ids=["T1"], state="completed")
        executor._parallel_outcome = "success"
        executor._finished_at = time.monotonic()
        with executor._task_states_lock:
            executor._task_states["T1"]["state"] = "completed"

        status = executor.get_status()
        assert status["progress_percent"] == 100.0


# =============================================================================
# Task Progress Dict in Status Response
# =============================================================================


class TestTaskProgressInStatus:
    """Verify task_progress dict is included in parallel mode status."""

    def test_task_progress_included_in_parallel(self, mock_settings):
        executor = _make_executor(task_ids=["BNUVZ-12529", "BNUVZ-12568"], state="running")
        with executor._task_states_lock:
            executor._task_states["BNUVZ-12529"]["state"] = "running"
            executor._task_states["BNUVZ-12529"]["pid"] = 1111
            executor._task_states["BNUVZ-12568"]["state"] = "pending"

        status = executor.get_status()

        assert "task_progress" in status
        assert "BNUVZ-12529" in status["task_progress"]
        assert "BNUVZ-12568" in status["task_progress"]
        assert status["task_progress"]["BNUVZ-12529"]["state"] == "running"
        assert status["task_progress"]["BNUVZ-12529"]["pid"] == 1111
        assert status["task_progress"]["BNUVZ-12568"]["state"] == "pending"

    def test_task_progress_captures_exit_codes(self, mock_settings):
        executor = _make_executor(task_ids=["T1", "T2"], state="completed")
        executor._parallel_outcome = "partial"
        executor._finished_at = time.monotonic()
        with executor._task_states_lock:
            executor._task_states["T1"]["state"] = "completed"
            executor._task_states["T1"]["exit_code"] = 0
            executor._task_states["T2"]["state"] = "failed"
            executor._task_states["T2"]["exit_code"] = 1

        status = executor.get_status()

        assert status["task_progress"]["T1"]["exit_code"] == 0
        assert status["task_progress"]["T2"]["exit_code"] == 1

    def test_parallel_mode_flag_in_status(self, mock_settings):
        executor = _make_executor(task_ids=["T1"], state="running")
        with executor._task_states_lock:
            executor._task_states["T1"]["state"] = "running"

        status = executor.get_status()
        assert status.get("parallel_mode") is True

    def test_non_parallel_has_no_task_progress(self, mock_settings, metrics_file):
        """Non-parallel mode should NOT include task_progress."""
        write_metrics(
            metrics_file,
            [
                {"msg": "phase_start", "data": {"event": "phase_start", "phase": "triage", "name": "Triage"}},
            ],
        )

        executor = _make_executor(parallel_mode=False, task_ids=[], state="running")

        status = executor.get_status()
        assert "task_progress" not in status
        assert "parallel_mode" not in status


# =============================================================================
# Run Outcome — Uses _parallel_outcome
# =============================================================================


class TestParallelRunOutcome:
    """run_outcome should use _parallel_outcome, not metrics.jsonl."""

    def test_outcome_success(self, mock_settings):
        executor = _make_executor(task_ids=["T1", "T2"], state="completed")
        executor._parallel_outcome = "success"
        executor._finished_at = time.monotonic()
        with executor._task_states_lock:
            for tid in ("T1", "T2"):
                executor._task_states[tid]["state"] = "completed"

        status = executor.get_status()
        assert status["run_outcome"] == "success"

    def test_outcome_partial(self, mock_settings):
        executor = _make_executor(task_ids=["T1", "T2"], state="completed")
        executor._parallel_outcome = "partial"
        executor._finished_at = time.monotonic()
        with executor._task_states_lock:
            executor._task_states["T1"]["state"] = "completed"
            executor._task_states["T2"]["state"] = "failed"

        status = executor.get_status()
        assert status["run_outcome"] == "partial"

    def test_outcome_failed(self, mock_settings):
        executor = _make_executor(task_ids=["T1", "T2"], state="failed")
        executor._parallel_outcome = "failed"
        executor._finished_at = time.monotonic()
        with executor._task_states_lock:
            for tid in ("T1", "T2"):
                executor._task_states[tid]["state"] = "failed"

        status = executor.get_status()
        assert status["run_outcome"] == "failed"

    def test_outcome_none_while_running(self, mock_settings):
        executor = _make_executor(task_ids=["T1"], state="running")
        with executor._task_states_lock:
            executor._task_states["T1"]["state"] = "running"

        status = executor.get_status()
        assert status["run_outcome"] is None

    def test_outcome_fallback_when_parallel_outcome_not_set(self, mock_settings):
        """Edge case: _parallel_outcome not set, fall back to state-based."""
        executor = _make_executor(task_ids=["T1"], state="completed")
        executor._parallel_outcome = None  # not set
        executor._finished_at = time.monotonic()
        with executor._task_states_lock:
            executor._task_states["T1"]["state"] = "completed"

        status = executor.get_status()
        assert status["run_outcome"] == "success"  # fallback


# =============================================================================
# Backward Compatibility — Non-Parallel Still Uses metrics.jsonl
# =============================================================================


class TestNonParallelBackwardCompat:
    """Normal (non-parallel) runs must continue reading from metrics.jsonl."""

    def test_non_parallel_reads_metrics_file(self, mock_settings, metrics_file):
        write_metrics(
            metrics_file,
            [
                {"msg": "phase_start", "data": {"event": "phase_start", "phase": "triage", "name": "Triage"}},
                {"msg": "phase_complete", "data": {"event": "phase_complete", "phase": "triage", "duration_seconds": 10}},
                {"msg": "phase_start", "data": {"event": "phase_start", "phase": "plan", "name": "Plan"}},
            ],
        )

        executor = _make_executor(parallel_mode=False, task_ids=[], state="running")

        status = executor.get_status()

        # Should have phase progress from metrics.jsonl
        ids = [p["phase_id"] for p in status["phase_progress"]]
        assert "triage" in ids
        assert "plan" in ids
        # triage completed, plan running
        triage = next(p for p in status["phase_progress"] if p["phase_id"] == "triage")
        plan = next(p for p in status["phase_progress"] if p["phase_id"] == "plan")
        assert triage["status"] == "completed"
        assert plan["status"] == "running"

    def test_non_parallel_completed_uses_metrics_for_outcome(self, mock_settings, metrics_file):
        write_metrics(
            metrics_file,
            [
                {"msg": "phase_start", "data": {"event": "phase_start", "phase": "triage", "name": "Triage"}},
                {"msg": "phase_complete", "data": {"event": "phase_complete", "phase": "triage", "duration_seconds": 10}},
            ],
        )

        executor = _make_executor(parallel_mode=False, task_ids=[], state="completed")
        executor._finished_at = time.monotonic()

        status = executor.get_status()
        assert status["run_outcome"] == "success"


# =============================================================================
# Phase Count & Total — Parallel Mode
# =============================================================================


class TestParallelPhaseCounts:
    """Phase counts in parallel mode."""

    def test_total_phase_count_matches_requested_phases(self, mock_settings):
        executor = _make_executor(
            phases=["triage", "plan", "implement"],
            task_ids=["T1"],
            state="running",
        )
        with executor._task_states_lock:
            executor._task_states["T1"]["state"] = "running"

        status = executor.get_status()
        assert status["total_phase_count"] == 3

    def test_completed_count_zero_while_running(self, mock_settings):
        executor = _make_executor(task_ids=["T1", "T2"], state="running")
        with executor._task_states_lock:
            executor._task_states["T1"]["state"] = "completed"
            executor._task_states["T2"]["state"] = "running"

        status = executor.get_status()
        assert status["completed_phase_count"] == 0  # still running
        assert status["skipped_phase_count"] == 0

    def test_completed_count_equals_total_when_terminal(self, mock_settings):
        executor = _make_executor(
            phases=["triage", "plan"],
            task_ids=["T1"],
            state="completed",
        )
        executor._parallel_outcome = "success"
        executor._finished_at = time.monotonic()
        with executor._task_states_lock:
            executor._task_states["T1"]["state"] = "completed"

        status = executor.get_status()
        assert status["completed_phase_count"] == 2
        assert status["total_phase_count"] == 2


# =============================================================================
# Many-Task Scenarios
# =============================================================================


class TestManyTaskScenarios:
    """Edge cases with many tasks."""

    def test_eight_tasks_progress(self, mock_settings):
        """8 tasks, 5 done, 3 running → 62.5%."""
        tids = [f"T{i}" for i in range(1, 9)]
        executor = _make_executor(task_ids=tids, state="running")
        with executor._task_states_lock:
            for i, tid in enumerate(tids):
                if i < 5:
                    executor._task_states[tid]["state"] = "completed"
                    executor._task_states[tid]["exit_code"] = 0
                else:
                    executor._task_states[tid]["state"] = "running"

        status = executor.get_status()
        assert status["progress_percent"] == 62.5

    def test_mixed_completed_failed_pending(self, mock_settings):
        """3 completed, 2 failed, 1 running, 2 pending → done=5/8 → 62.5%."""
        tids = [f"T{i}" for i in range(1, 9)]
        executor = _make_executor(task_ids=tids, state="running")
        with executor._task_states_lock:
            for i, tid in enumerate(tids):
                if i < 3:
                    executor._task_states[tid]["state"] = "completed"
                    executor._task_states[tid]["exit_code"] = 0
                elif i < 5:
                    executor._task_states[tid]["state"] = "failed"
                    executor._task_states[tid]["exit_code"] = 1
                elif i < 6:
                    executor._task_states[tid]["state"] = "running"
                else:
                    executor._task_states[tid]["state"] = "pending"

        status = executor.get_status()
        assert status["progress_percent"] == 62.5

    def test_empty_task_list(self, mock_settings):
        """Edge case: parallel mode with no tasks should not crash."""
        executor = _make_executor(task_ids=[], state="running")

        status = executor.get_status()
        assert status["progress_percent"] == 0.0
        assert status.get("task_progress") == {}


# =============================================================================
# Cancel & phase_state.json Consistency
# =============================================================================


class TestParallelCancelAndPhaseState:
    """Ensure cancel() and stale subprocess handling keep phase_state.json consistent."""

    def test_cancel_parallel_marks_tasks_cancelled_and_state_terminal(self, mock_settings, tmp_project):
        from ui.backend.services.pipeline_executor import PipelineExecutor

        executor = PipelineExecutor.__new__(PipelineExecutor)
        executor._init()
        executor.current_run = None

        # Simulate a running parallel run with two tasks and fake Popen objects
        class _FakeProc:
            def __init__(self, pid: int):
                self.pid = pid

        executor.state = "running"
        executor.current_run = executor.current_run = type("R", (), {"run_id": "test-par", "parallel_mode": True})()
        with executor._task_states_lock:
            executor._task_processes = {"T1": _FakeProc(1111), "T2": _FakeProc(2222)}
            executor._task_states = {
                "T1": {"state": "running", "pid": 1111, "exit_code": None, "log_lines": []},
                "T2": {"state": "running", "pid": 2222, "exit_code": None, "log_lines": []},
            }

        # Monkeypatch kill to avoid actually killing anything
        with patch.object(executor, "_kill_process_tree") as kill_tree:
            cancelled = executor.cancel()

        assert cancelled is True
        assert executor.state == "cancelled"
        with executor._task_states_lock:
            assert executor._task_states["T1"]["state"] == "cancelled"
            assert executor._task_states["T2"]["state"] == "cancelled"
        kill_tree.assert_called()  # at least once

    def test_cancel_stale_subprocess_marks_running_phases_cancelled(self, mock_settings, tmp_project, monkeypatch):
        from ui.backend.services.pipeline_executor import PipelineExecutor

        # Prepare a fake phase_state.json with a dead PID and running phases
        state_path = tmp_project / "logs" / "phase_state.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps(
                {
                    "run_id": "cli-run",
                    "pid": 999999,  # non-existent
                    "phases": {
                        "triage": {"status": "running", "started_at": "2026-03-09T10:00:00"},
                        "plan": {"status": "completed", "duration_seconds": 12.3},
                    },
                }
            ),
            encoding="utf-8",
        )

        # os.kill should report the process as dead
        def _fake_kill(pid: int, sig: int) -> None:
            raise ProcessLookupError()

        monkeypatch.setattr("os.kill", _fake_kill)

        executor = PipelineExecutor.__new__(PipelineExecutor)
        executor._init()

        # Point logs_dir at tmp_project/logs via patched settings fixture
        cancelled = executor._cancel_stale_subprocess()
        assert cancelled is True

        # phase_state.json should now mark running phase as cancelled/failed, but file must remain valid JSON
        data = json.loads(state_path.read_text(encoding="utf-8"))
        phases = data.get("phases", {})
        assert phases["triage"]["status"] in {"cancelled", "failed"}


# =============================================================================
# History Entry — Parallel Metadata
# =============================================================================


class TestParallelHistoryEntry:
    """Verify _snapshot_for_history captures parallel metadata."""

    def test_snapshot_includes_parallel_fields(self, mock_settings):
        executor = _make_executor(task_ids=["T1", "T2"], state="completed")
        executor._parallel_outcome = "partial"
        executor._finished_at = time.monotonic()
        with executor._task_states_lock:
            executor._task_states["T1"]["state"] = "completed"
            executor._task_states["T1"]["exit_code"] = 0
            executor._task_states["T2"]["state"] = "failed"
            executor._task_states["T2"]["exit_code"] = 1

        with executor._state_lock:
            snap = executor._snapshot_for_history()

        assert snap is not None
        assert snap["parallel_mode"] is True
        assert snap["parallel_outcome"] == "partial"
        assert snap["task_ids"] == ["T1", "T2"]
        assert snap["task_results"]["T1"]["state"] == "completed"
        assert snap["task_results"]["T2"]["state"] == "failed"
        assert snap["task_results"]["T2"]["exit_code"] == 1

    def test_snapshot_non_parallel(self, mock_settings, metrics_file):
        """Non-parallel snapshot sets parallel_mode=False, no task_results."""
        write_metrics(metrics_file, [])

        executor = _make_executor(parallel_mode=False, task_ids=[], state="completed")
        executor._finished_at = time.monotonic()

        with executor._state_lock:
            snap = executor._snapshot_for_history()

        assert snap is not None
        assert snap["parallel_mode"] is False
        assert "task_results" not in snap
        assert "task_ids" not in snap
