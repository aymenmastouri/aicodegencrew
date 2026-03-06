"""Pipeline execution service using subprocess isolation."""

from __future__ import annotations

import json
import logging
import platform
import re
import subprocess
import sys
import threading
import time
import uuid
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from aicodegencrew.pipeline_contract import (
    PHASE_PROGRESS_CANCELLED,
    PHASE_PROGRESS_COMPLETED,
    PHASE_PROGRESS_FAILED,
    PHASE_PROGRESS_PARTIAL,
    PHASE_PROGRESS_PENDING,
    PHASE_PROGRESS_RUNNING,
    PHASE_PROGRESS_SKIPPED,
    compute_run_outcome,
    normalize_phase_progress_status,
)
from aicodegencrew.shared.utils.phase_state import init_run as _init_phase_state

from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class RunInfo:
    run_id: str
    preset: str | None
    phases: list[str]
    started_at: str
    pid: int | None = None
    parallel_mode: bool = False
    task_ids: list[str] = field(default_factory=list)


_MAX_LOG_LINES = 10_000


class PipelineExecutor:
    """Singleton executor that manages one pipeline subprocess at a time."""

    _instance: PipelineExecutor | None = None
    _lock = threading.Lock()

    def __new__(cls) -> PipelineExecutor:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self) -> None:
        self.state: str = "idle"  # idle | running | completed | failed | cancelled
        self.current_run: RunInfo | None = None
        self._engine_run_id: str | None = None
        self._run_started_wall: str | None = None
        self._process: subprocess.Popen | None = None
        self._log_lines: list[str] = []
        self._log_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._started_at: float | None = None
        self._finished_at: float | None = None
        self._exit_code: int | None = None
        # Parallel task execution state
        self._task_processes: dict[str, subprocess.Popen] = {}
        self._task_states: dict[str, dict] = {}  # task_id -> {state, pid, exit_code, log_lines}
        self._task_states_lock = threading.Lock()
        self._parallel_outcome: str | None = None  # "success" | "partial" | "failed"

    def start(
        self,
        preset: str | None = None,
        phases: list[str] | None = None,
        env_overrides: dict[str, str] | None = None,
    ) -> RunInfo:
        """Start a pipeline run. Raises RuntimeError if already running."""
        with self._state_lock:
            if self.state == "running":
                raise RuntimeError("A pipeline is already running")

            run_id = uuid.uuid4().hex[:8]
            now = datetime.now(UTC).isoformat()

            # Write temp .env with overrides if needed
            env_path = settings.env_file
            if env_overrides:
                env_path = settings.project_root / ".env.run"
                self._write_env_with_overrides(env_overrides, env_path)

            # Build command — --env is a global arg, must come BEFORE the subcommand
            cmd = [sys.executable, "-m", "aicodegencrew", "--env", str(env_path), "run"]
            phase_list: list[str] = []

            if preset:
                cmd.extend(["--preset", preset])
                # Resolve phases from preset for display
                from .phase_runner import get_presets

                for p in get_presets():
                    if p.name == preset:
                        phase_list = p.phases
                        break
            elif phases:
                phase_list = phases
                # Try exact preset match first, otherwise use --phases directly
                from .phase_runner import get_presets

                for p in get_presets():
                    if set(p.phases) == set(phases):
                        cmd.extend(["--preset", p.name])
                        break
                else:
                    cmd.extend(["--phases", *phases])

            phase_list = self._filter_disabled_phases(phase_list)

            self.current_run = RunInfo(
                run_id=run_id,
                preset=preset,
                phases=phase_list,
                started_at=now,
            )
            self.state = "running"
            self._log_lines = []
            self._exit_code = None
            self._engine_run_id = None
            self._started_at = time.monotonic()
            self._finished_at = None
            # Wall-clock start time for filtering metrics.jsonl events (local time to match metrics format)
            self._run_started_wall = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

            # Spawn subprocess
            try:
                self._process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=str(settings.project_root),
                    bufsize=1,
                )
                self.current_run.pid = self._process.pid
                logger.info(
                    "Pipeline started: run_id=%s, pid=%d, cmd=%s",
                    run_id,
                    self._process.pid,
                    " ".join(cmd),
                )
            except Exception as exc:
                self.state = "failed"
                logger.error("Failed to start pipeline: %s", exc)
                raise RuntimeError(f"Failed to start pipeline: {exc}") from exc

            # Monitor thread
            monitor = threading.Thread(
                target=self._monitor_process,
                name=f"pipeline-monitor-{run_id}",
                daemon=True,
            )
            monitor.start()

            return self.current_run

    def start_parallel_tasks(
        self,
        task_ids: list[str],
        phases: list[str],
        max_parallel: int = 4,
        env_overrides: dict[str, str] | None = None,
    ) -> RunInfo:
        """Start parallel subprocess execution — one subprocess per task.

        Each subprocess runs: python -m aicodegencrew run --phases <phases> --task-id <task_id>
        Uses a thread pool to cap concurrency at max_parallel.
        """
        with self._state_lock:
            if self.state == "running":
                raise RuntimeError("A pipeline is already running")

            run_id = uuid.uuid4().hex[:8]
            now = datetime.now(UTC).isoformat()

            # Write temp .env with overrides if needed
            env_path = settings.env_file
            if env_overrides:
                env_path = settings.project_root / ".env.run"
                self._write_env_with_overrides(env_overrides, env_path)

            phase_list = self._filter_disabled_phases(list(phases))

            self.current_run = RunInfo(
                run_id=run_id,
                preset=None,
                phases=phase_list,
                started_at=now,
                parallel_mode=True,
                task_ids=list(task_ids),
            )
            self.state = "running"
            self._log_lines = []
            self._exit_code = None
            self._engine_run_id = None
            self._started_at = time.monotonic()
            self._finished_at = None
            self._run_started_wall = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

            # Initialize per-task state
            with self._task_states_lock:
                self._task_processes = {}
                self._task_states = {
                    tid: {"state": "pending", "pid": None, "exit_code": None, "log_lines": []}
                    for tid in task_ids
                }

        with self._log_lock:
            self._log_lines.append(
                f"[PARALLEL] Starting {len(task_ids)} task(s) with max_parallel={max_parallel}"
            )

        # Initialize phase_state.json ONCE before spawning subprocesses.
        # Each subprocess skips init_run() when --task-id is set, so this
        # is the single point of initialization for the run.
        _init_phase_state(run_id)

        # Launch monitor thread that manages the parallel execution
        monitor = threading.Thread(
            target=self._run_parallel_tasks,
            args=(task_ids, phase_list, max_parallel, env_path),
            name=f"parallel-monitor-{run_id}",
            daemon=True,
        )
        monitor.start()

        return self.current_run

    def _run_parallel_tasks(
        self,
        task_ids: list[str],
        phases: list[str],
        max_parallel: int,
        env_path: Path,
    ) -> None:
        """Thread that manages parallel subprocess execution via a ThreadPoolExecutor."""
        results: dict[str, int] = {}

        def run_single_task(task_id: str) -> tuple[str, int]:
            """Spawn and monitor one subprocess for a single task."""
            cmd = [
                sys.executable, "-m", "aicodegencrew",
                "--env", str(env_path),
                "run",
                "--phases", *phases,
                "--task-id", task_id,
            ]

            with self._log_lock:
                self._log_lines.append(f"[PARALLEL] [{task_id}] Starting: {' '.join(cmd)}")

            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=str(settings.project_root),
                    bufsize=1,
                )
            except Exception as exc:
                with self._task_states_lock:
                    self._task_states[task_id]["state"] = "failed"
                with self._log_lock:
                    self._log_lines.append(f"[PARALLEL] [{task_id}] Failed to start: {exc}")
                return task_id, 1

            with self._task_states_lock:
                self._task_processes[task_id] = proc
                self._task_states[task_id]["state"] = "running"
                self._task_states[task_id]["pid"] = proc.pid
                self._task_states[task_id]["current_phase"] = None
                self._task_states[task_id]["completed_phases"] = []

            try:
                # Read stdout line by line
                if proc.stdout:
                    for line in proc.stdout:
                        line = line.rstrip("\n\r")
                        with self._log_lock:
                            self._log_lines.append(f"[{task_id}] {line}")
                            if len(self._log_lines) > _MAX_LOG_LINES:
                                self._log_lines = self._log_lines[-_MAX_LOG_LINES:]
                        with self._task_states_lock:
                            task_logs = self._task_states[task_id]["log_lines"]
                            task_logs.append(line)
                            if len(task_logs) > 500:
                                self._task_states[task_id]["log_lines"] = task_logs[-500:]
                            # Detect phase transitions from log output
                            self._detect_phase_from_log(task_id, line)

                try:
                    exit_code = proc.wait(timeout=3600)  # 1h max per task
                except subprocess.TimeoutExpired:
                    logger.warning("[PARALLEL] [%s] Timed out after 3600s — killing", task_id)
                    self._kill_process_tree(proc.pid)
                    try:
                        proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    exit_code = -1
            except Exception as io_exc:
                # Ensure process is killed if stdout reading or wait fails
                logger.error("[PARALLEL] [%s] I/O error: %s — killing process", task_id, io_exc)
                try:
                    self._kill_process_tree(proc.pid)
                    proc.wait(timeout=10)
                except Exception:
                    proc.kill()
                exit_code = -1

            with self._task_states_lock:
                self._task_states[task_id]["exit_code"] = exit_code
                self._task_states[task_id]["state"] = "completed" if exit_code == 0 else "failed"

            with self._log_lock:
                state_label = "completed" if exit_code == 0 else f"failed (exit={exit_code})"
                self._log_lines.append(f"[PARALLEL] [{task_id}] {state_label}")

            return task_id, exit_code

        try:
            with ThreadPoolExecutor(max_workers=min(max_parallel, len(task_ids))) as pool:
                futures = {pool.submit(run_single_task, tid): tid for tid in task_ids}
                for future in futures:
                    try:
                        task_id, exit_code = future.result()
                        results[task_id] = exit_code
                    except Exception as exc:
                        tid = futures[future]
                        results[tid] = 1
                        with self._task_states_lock:
                            self._task_states[tid]["state"] = "failed"
                        with self._log_lock:
                            self._log_lines.append(f"[PARALLEL] [{tid}] Exception: {exc}")

            # Determine overall outcome
            succeeded = sum(1 for code in results.values() if code == 0)
            total = len(results)

            with self._state_lock:
                if succeeded == total:
                    self.state = "completed"
                elif succeeded > 0:
                    self.state = "completed"  # partial success — still terminal "completed"
                else:
                    self.state = "failed"
                # Store outcome for history
                if succeeded == total:
                    self._parallel_outcome = "success"
                elif succeeded > 0:
                    self._parallel_outcome = "partial"
                else:
                    self._parallel_outcome = "failed"
                self._finished_at = time.monotonic()

            with self._log_lock:
                self._log_lines.append(
                    f"[PARALLEL] All tasks finished: {succeeded}/{total} succeeded"
                )

            snapshot = None
            with self._state_lock:
                snapshot = self._snapshot_for_history()
            self._append_history_entry(snapshot)

        except Exception as exc:
            logger.error("Parallel monitor thread error: %s", exc)
            with self._state_lock:
                if self.state == "running":
                    self.state = "failed"
                    self._finished_at = time.monotonic()
                snapshot = self._snapshot_for_history()
            self._append_history_entry(snapshot)

    @staticmethod
    def _filter_disabled_phases(phase_ids: list[str]) -> list[str]:
        """Hide config-disabled phases from UI progress totals/lists."""
        if not phase_ids:
            return phase_ids
        try:
            from .phase_runner import get_phases

            enabled_by_id = {p.id: bool(p.enabled) for p in get_phases()}
            return [phase_id for phase_id in phase_ids if enabled_by_id.get(phase_id, True)]
        except Exception as exc:
            logger.debug("Failed to filter disabled phases: %s", exc)
            return phase_ids

    def cancel(self) -> bool:
        """Cancel the running pipeline. Returns True if cancelled.

        Handles both dashboard-started runs (self._process) and stale
        subprocess runs detected via phase_state.json.
        """
        with self._state_lock:
            # Case 0: Parallel mode — kill all task subprocesses
            if self.state == "running" and self.current_run and self.current_run.parallel_mode:
                try:
                    with self._task_states_lock:
                        procs_snapshot = dict(self._task_processes)
                        for tid, proc in procs_snapshot.items():
                            try:
                                self._kill_process_tree(proc.pid)
                            except Exception as exc:
                                logger.warning("Failed to kill task %s (pid %s): %s", tid, proc.pid, exc)
                            if tid in self._task_states:
                                self._task_states[tid]["state"] = "cancelled"
                    self.state = "cancelled"
                    self._finished_at = time.monotonic()
                    logger.info("Parallel pipeline cancelled: run_id=%s", self.current_run.run_id)
                    return True
                except Exception as exc:
                    logger.error("Failed to cancel parallel pipeline: %s", exc)
                    return False

            # Case 1: Dashboard-started run with live process
            if self.state == "running" and self._process is not None:
                try:
                    pid = self._process.pid
                    self._kill_process_tree(pid)
                    # Give it 5 seconds to terminate gracefully after tree kill
                    try:
                        self._process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self._process.kill()
                    self.state = "cancelled"
                    self._finished_at = time.monotonic()
                    logger.info("Pipeline cancelled: run_id=%s", self.current_run.run_id if self.current_run else "?")
                    self._mark_running_phases_cancelled()
                    return True
                except Exception as exc:
                    logger.error("Failed to cancel pipeline: %s", exc)
                    return False

            # Case 2: Stale subprocess (e.g. server restarted while pipeline was running)
            if self._cancel_stale_subprocess():
                return True

            return False

    def _cancel_stale_subprocess(self) -> bool:
        """Kill a stale pipeline subprocess detected via phase_state.json."""
        import os as _os

        state_path = settings.logs_dir / "phase_state.json"
        if not state_path.exists():
            return False
        try:
            with open(state_path, encoding="utf-8") as f:
                data = json.load(f)
            pid = data.get("pid")
            phases = data.get("phases", {})
            has_running = any(e.get("status") == "running" for e in phases.values())
            if not (has_running and pid):
                return False
            # Check if process is still alive
            try:
                _os.kill(pid, 0)
            except (OSError, ProcessLookupError):
                # Process dead — just clean up the stale state
                self._mark_running_phases_cancelled()
                logger.info("Cleaned up stale phase_state.json (PID %s dead)", pid)
                return True
            # Process alive — kill it
            self._kill_process_tree(pid)
            self._mark_running_phases_cancelled()
            logger.info("Killed stale pipeline subprocess PID %s", pid)
            return True
        except Exception as exc:
            logger.warning("Failed to cancel stale subprocess: %s", exc)
            return False

    @staticmethod
    def _kill_process_tree(pid: int) -> None:
        """Kill a process and all its children (Windows-compatible)."""
        if platform.system() == "Windows":
            # taskkill /T kills the entire process tree; /F forces termination
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True,
                check=False,
            )
        else:
            import os
            import signal

            try:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
            except (ProcessLookupError, OSError):
                pass

    def _mark_running_phases_cancelled(self) -> None:
        """After cancel, update phase_state.json so running phases show as failed.

        Also creates 'cancelled' entries for phases in the current run that never
        reached 'running' status (early cancel before orchestrator wrote the entry).
        """
        state_path = settings.logs_dir / "phase_state.json"
        now = datetime.now(UTC).isoformat(timespec="seconds")
        try:
            data: dict = {}
            if state_path.exists():
                try:
                    with open(state_path, encoding="utf-8") as f:
                        data = json.load(f)
                except (json.JSONDecodeError, OSError) as exc:
                    logger.warning("Corrupted phase_state.json, resetting: %s", exc)

            phases = data.setdefault("phases", {})
            if not isinstance(phases, dict):
                phases = {}
                data["phases"] = phases
            modified = False

            # Mark any currently-running phases as cancelled
            for entry in phases.values():
                if not isinstance(entry, dict):
                    continue
                if entry.get("status") == "running":
                    entry["status"] = "cancelled"
                    entry["error"] = "Cancelled by user"
                    entry["completed_at"] = now
                    modified = True

            if modified:
                data["updated_at"] = now
                state_path.parent.mkdir(parents=True, exist_ok=True)
                with open(state_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            logger.warning("Failed to update phase_state.json after cancel: %s", exc)

    def get_status(self) -> dict:
        """Get current execution status."""
        # Auto-reset to idle after 120s in a terminal state.
        # Entire check+reset under lock to prevent race with start().
        # Snapshot mutable fields under lock to avoid TOCTOU races with
        # monitor/cancel threads that write outside this method.
        with self._state_lock:
            if self.state in ("completed", "failed", "cancelled") and self._finished_at:
                if time.monotonic() - self._finished_at > 120:
                    self.state = "idle"
                    self._finished_at = None
                    self._started_at = None
                    self.current_run = None
                    self._engine_run_id = None
                    self._run_started_wall = None
                    # Clean parallel task state to prevent ghost tasks in UI
                    with self._task_states_lock:
                        self._task_processes.clear()
                        self._task_states.clear()
            state = self.state
            started_at = self._started_at
            finished_at = self._finished_at
            current_run = self.current_run

        # Detect external CLI runs when executor is idle
        if state == "idle":
            ext = self._check_external_run()
            if ext:
                return ext

        elapsed = None
        if started_at and state == "running":
            elapsed = round(time.monotonic() - started_at, 1)
        elif started_at and state in ("completed", "failed", "cancelled"):
            # Show elapsed since run started (not growing endlessly)
            elapsed = round((finished_at or time.monotonic()) - started_at, 1)

        # ------------------------------------------------------------------
        # Parallel mode: synthesise phase_progress from task states
        # because metrics.jsonl has race conditions (first subprocess to
        # finish marks phases "completed" while others still run).
        # ------------------------------------------------------------------
        if current_run and current_run.parallel_mode:
            with self._task_states_lock:
                task_total = len(self._task_states)
                tasks_completed = sum(1 for ts in self._task_states.values() if ts["state"] == "completed")
                tasks_failed = sum(1 for ts in self._task_states.values() if ts["state"] == "failed")
                tasks_done = tasks_completed + tasks_failed
                requested_phases = set(current_run.phases) if current_run else set()
                task_progress = {}
                for tid, ts in self._task_states.items():
                    display_state = ts["state"]
                    # If subprocess is still "running" but all requested phases are in
                    # completed_phases, show as "completed" — subprocess is doing final
                    # cleanup/writes and proc.wait() hasn't returned yet.
                    if display_state == "running" and requested_phases:
                        done_phases = set(ts.get("completed_phases", []))
                        if requested_phases.issubset(done_phases):
                            display_state = "completed"
                    task_progress[tid] = {
                        "state": display_state,
                        "pid": ts["pid"],
                        "exit_code": ts["exit_code"],
                        "completed_phases": ts.get("completed_phases", []),
                    }

            # Determine per-phase status by aggregating per-task phase tracking.
            # A phase is:
            #   "completed" → ALL tasks have completed it
            #   "running"   → at least one task is currently executing it
            #   "pending"   → no task has reached it yet
            if state == "running":
                phase_progress = []
                for pid in current_run.phases:
                    tasks_on_phase = 0
                    tasks_past_phase = 0
                    for ts in self._task_states.values():
                        completed_phases = ts.get("completed_phases", [])
                        current_phase = ts.get("current_phase")
                        task_done = ts.get("state") in ("completed", "failed")
                        if task_done:
                            tasks_past_phase += 1
                        elif pid in completed_phases:
                            tasks_past_phase += 1
                        elif current_phase == pid:
                            tasks_on_phase += 1

                    if tasks_past_phase == task_total:
                        p_status = PHASE_PROGRESS_COMPLETED
                    elif tasks_on_phase > 0:
                        p_status = PHASE_PROGRESS_RUNNING
                    elif tasks_past_phase > 0:
                        # Some tasks passed this phase, none currently on it,
                        # but not all done → still running (waiting for remaining tasks)
                        p_status = PHASE_PROGRESS_RUNNING
                    else:
                        p_status = PHASE_PROGRESS_PENDING

                    phase_progress.append({
                        "phase_id": pid,
                        "name": pid.replace("_", " ").title(),
                        "status": p_status,
                        "started_at": current_run.started_at,
                        "duration_seconds": None,
                    })
            else:
                if state == "cancelled":
                    phase_status = PHASE_PROGRESS_CANCELLED
                elif tasks_completed == task_total:
                    phase_status = PHASE_PROGRESS_COMPLETED
                elif tasks_completed > 0:
                    phase_status = PHASE_PROGRESS_PARTIAL
                else:
                    phase_status = PHASE_PROGRESS_FAILED
                phase_progress = [
                    {
                        "phase_id": pid,
                        "name": pid.replace("_", " ").title(),
                        "status": phase_status,
                        "started_at": current_run.started_at,
                        "duration_seconds": elapsed,
                    }
                    for pid in current_run.phases
                ]

            total = len(current_run.phases)
            if state == "running":
                # Progress = fraction of phase-steps completed across all tasks.
                # E.g. 2 tasks × 2 phases = 4 steps; triage done for both = 50%.
                num_phases = len(current_run.phases)
                total_steps = num_phases * task_total
                completed_steps = 0
                for ts in self._task_states.values():
                    if ts["state"] in ("completed", "failed"):
                        # Fully-done task counts for all phases
                        completed_steps += num_phases
                    else:
                        completed_steps += len(ts.get("completed_phases", []))
                progress = round(completed_steps / total_steps * 100, 1) if total_steps > 0 else 0
                completed_count = sum(
                    1 for p in phase_progress if p.get("status") == PHASE_PROGRESS_COMPLETED
                )
                skipped_count = 0
            else:
                progress = 100.0
                completed_count = total
                skipped_count = 0

            live_metrics = self._read_live_metrics() if state == "running" else None
            eta = self._estimate_eta(elapsed) if state == "running" and elapsed else None

            run_outcome = None
            if state in ("completed", "failed", "cancelled"):
                run_outcome = self._parallel_outcome or (
                    "success" if state == "completed" else "failed"
                )

            return {
                "state": state,
                "run_id": current_run.run_id,
                "preset": current_run.preset,
                "phases": current_run.phases,
                "started_at": current_run.started_at,
                "elapsed_seconds": elapsed,
                "phase_progress": phase_progress,
                "progress_percent": progress,
                "completed_phase_count": completed_count,
                "skipped_phase_count": skipped_count,
                "total_phase_count": total,
                "eta_seconds": eta,
                "live_metrics": live_metrics,
                "run_outcome": run_outcome,
                "parallel_mode": True,
                "task_progress": task_progress,
            }

        # ------------------------------------------------------------------
        # Normal (non-parallel) mode: read from metrics.jsonl as before
        # ------------------------------------------------------------------
        raw_phase_progress = (
            self._read_phase_progress() if state in ("running", "completed", "failed", "cancelled") else []
        )

        # After cancel, any phase still marked "running" is actually dead
        if state == "cancelled":
            for p in raw_phase_progress:
                if normalize_phase_progress_status(p.get("status")) == PHASE_PROGRESS_RUNNING:
                    p["status"] = PHASE_PROGRESS_CANCELLED

        phase_progress = [p for p in raw_phase_progress if not self._is_unregistered_skip(p)]
        if current_run and current_run.phases:
            current_phase_ids = set(current_run.phases)
            unregistered_count = sum(
                1
                for phase in raw_phase_progress
                if self._is_unregistered_skip(phase) and phase.get("phase_id") in current_phase_ids
            )
        else:
            unregistered_count = len(raw_phase_progress) - len(phase_progress)

        # Compute progress percent
        total = len(current_run.phases) if current_run else 0
        completed = sum(1 for p in phase_progress if self._is_completed_phase(p))
        skipped = sum(
            1
            for p in phase_progress
            if normalize_phase_progress_status(p.get("status"), default=PHASE_PROGRESS_PENDING)
            == PHASE_PROGRESS_SKIPPED
        )
        running = sum(
            1
            for p in phase_progress
            if normalize_phase_progress_status(p.get("status"), default=PHASE_PROGRESS_PENDING)
            == PHASE_PROGRESS_RUNNING
        )
        if total > 0 and unregistered_count > 0:
            total = max(total - unregistered_count, 0)
        if phase_progress:
            observed = len(phase_progress)
            if total == 0:
                total = observed
            # Full preset may include phases that are intentionally unregistered/skipped
            # (e.g., verify/deliver planned but not implemented). Show 100% on success.
            elif state == "completed" and (completed + skipped) == observed:
                total = observed
        done = completed + skipped
        progress = round((done + running * 0.5) / total * 100, 1) if total > 0 else 0

        # Live metrics
        live_metrics = self._read_live_metrics() if state == "running" else None

        # ETA estimation
        eta = self._estimate_eta(elapsed) if state == "running" and elapsed else None

        # Compute run_outcome for terminal states
        run_outcome = None
        if state in ("completed", "failed", "cancelled"):
            if phase_progress:
                run_outcome = self._compute_run_outcome(phase_progress)
            else:
                run_outcome = "success" if state == "completed" else "failed"

        return {
            "state": state,
            "run_id": current_run.run_id if current_run else None,
            "preset": current_run.preset if current_run else None,
            "phases": current_run.phases if current_run else [],
            "started_at": current_run.started_at if current_run else None,
            "elapsed_seconds": elapsed,
            "phase_progress": phase_progress,
            "progress_percent": progress,
            "completed_phase_count": completed,
            "skipped_phase_count": skipped,
            "total_phase_count": total,
            "eta_seconds": eta,
            "live_metrics": live_metrics,
            "run_outcome": run_outcome,
        }

    def get_log_lines(self, since: int = 0) -> list[str]:
        """Get log lines since index. Returns (lines, next_index)."""
        with self._log_lock:
            return self._log_lines[since:]

    def get_log_stream(self) -> Generator[str, None, None]:
        """Yield log lines as they arrive (for SSE)."""
        idx = 0
        while True:
            with self._log_lock:
                new_lines = self._log_lines[idx:]
                idx = len(self._log_lines)

            for line in new_lines:
                yield line

            # Check if process is done
            if self.state != "running" and idx >= len(self._log_lines):
                # Yield any final lines
                with self._log_lock:
                    final = self._log_lines[idx:]
                for line in final:
                    yield line
                break

            time.sleep(0.5)

    def get_history(self) -> list[dict]:
        """Read run history from run_report.json."""
        reports: list[dict] = []

        # Check for current run_report.json
        if settings.run_report.exists():
            try:
                with open(settings.run_report, encoding="utf-8") as f:
                    data = json.load(f)
                reports.append(self._format_history_entry(data))
            except (json.JSONDecodeError, KeyError) as exc:
                logger.warning("Failed to parse run_report.json: %s", exc)

        return reports[:20]  # Last 20 runs

    def _format_history_entry(self, data: dict) -> dict:
        run_outcome = data.get("run_outcome")
        # Legacy run_report.json has no run_outcome — compute from phase statuses.
        if run_outcome is None:
            phase_statuses = [p.get("status") for p in data.get("phases", [])]
            if phase_statuses:
                run_outcome = compute_run_outcome(iter(phase_statuses))
            elif data.get("status") == "completed":
                run_outcome = "success"
            elif data.get("status") == "failed":
                run_outcome = "failed"
        return {
            "run_id": data.get("run_id", "unknown"),
            "status": data.get("status", "unknown"),
            "run_outcome": run_outcome,
            "preset": (data.get("environment") or {}).get("preset"),
            "phases": data.get("planned_phases", []),
            "started_at": data.get("timestamp"),
            "duration": data.get("total_duration"),
            "phase_results": data.get("phases", []),
        }

    def _monitor_process(self) -> None:
        """Background thread: read stdout and wait for process completion."""
        proc = self._process
        if proc is None or proc.stdout is None:
            return

        try:
            for line in proc.stdout:
                line = line.rstrip("\n\r")
                if self._engine_run_id is None:
                    parsed_run_id = self._extract_engine_run_id_from_line(line)
                    if parsed_run_id:
                        self._engine_run_id = parsed_run_id
                        logger.info(
                            "Detected engine run_id=%s for ui_run_id=%s",
                            parsed_run_id,
                            self.current_run.run_id if self.current_run else "?",
                        )
                with self._log_lock:
                    self._log_lines.append(line)
                    if len(self._log_lines) > _MAX_LOG_LINES:
                        self._log_lines = self._log_lines[-_MAX_LOG_LINES:]

            exit_code = proc.wait()

            with self._state_lock:
                self._exit_code = exit_code
                if self.state == "running":
                    self.state = "completed" if exit_code == 0 else "failed"
                    self._finished_at = time.monotonic()
                    logger.info(
                        "Pipeline finished: run_id=%s, exit_code=%d, state=%s",
                        self.current_run.run_id if self.current_run else "?",
                        exit_code,
                        self.state,
                    )
                snapshot = self._snapshot_for_history()

            # Append to JSONL run history (outside lock to avoid I/O under lock)
            self._append_history_entry(snapshot)

        except Exception as exc:
            logger.error("Monitor thread error: %s", exc)
            with self._state_lock:
                if self.state == "running":
                    self.state = "failed"
                    self._finished_at = time.monotonic()
                snapshot = self._snapshot_for_history()
            self._append_history_entry(snapshot)

    _RUN_ID_RE = re.compile(r"\brun_id=([0-9a-f]{8})\b")

    @classmethod
    def _extract_engine_run_id_from_line(cls, line: str) -> str | None:
        """Extract engine run_id from subprocess log output."""
        match = cls._RUN_ID_RE.search(line)
        if match:
            return match.group(1)
        return None

    def _snapshot_for_history(self) -> dict | None:
        """Capture mutable fields under _state_lock for history writing.

        Must be called while holding self._state_lock.
        """
        if not self.current_run:
            return None
        snap = {
            "run_id": self.current_run.run_id,
            "engine_run_id": self._engine_run_id,
            "state": self.state,
            "preset": self.current_run.preset,
            "phases": list(self.current_run.phases),
            "started_at": self.current_run.started_at,
            "mono_started_at": self._started_at,
        }
        # Include parallel-mode metadata for history
        if self.current_run.parallel_mode:
            snap["parallel_mode"] = True
            snap["parallel_outcome"] = self._parallel_outcome
            snap["task_ids"] = list(self.current_run.task_ids)
            with self._task_states_lock:
                snap["task_results"] = {
                    tid: {"state": ts["state"], "exit_code": ts.get("exit_code")}
                    for tid, ts in self._task_states.items()
                }
        else:
            snap["parallel_mode"] = False
        return snap

    def _append_history_entry(self, snapshot: dict | None) -> None:
        """Append a run entry to the JSONL history.

        Uses a pre-captured snapshot to avoid reading mutable executor
        state outside the lock.
        """
        if not snapshot:
            return
        try:
            from .history_service import append_run_to_history

            state = snapshot["state"]
            duration = round(time.monotonic() - snapshot["mono_started_at"], 1) if snapshot["mono_started_at"] else None
            raw_phase_progress = self._read_phase_progress() if state in ("completed", "failed", "cancelled") else []
            phase_progress = [p for p in raw_phase_progress if not self._is_unregistered_skip(p)]
            run_outcome = None
            if state in ("completed", "failed", "cancelled"):
                # Parallel mode: use _parallel_outcome (not phase_state.json which may be stale)
                if snapshot.get("parallel_mode"):
                    run_outcome = snapshot.get("parallel_outcome") or (
                        "success" if state == "completed" else "failed"
                    )
                elif phase_progress:
                    run_outcome = self._compute_run_outcome(phase_progress)
                else:
                    # No metrics events — try phase_state.json as secondary source
                    # before falling back to a coarse success/failed value.
                    try:
                        state_path = settings.logs_dir / "phase_state.json"
                        if state_path.exists():
                            with open(state_path, encoding="utf-8") as _f:
                                _state = json.load(_f)
                            _phases = _state.get("phases", {})
                            if isinstance(_phases, dict):
                                _statuses = [e.get("status") for e in _phases.values() if isinstance(e, dict)]
                                if _statuses:
                                    run_outcome = compute_run_outcome(iter(_statuses))
                    except Exception as exc:
                        logger.debug("Failed to read phase_state for run outcome: %s", exc)
                    if run_outcome is None:
                        run_outcome = "success" if state == "completed" else "failed"
            entry = {
                    "run_id": snapshot["run_id"],
                    "engine_run_id": snapshot["engine_run_id"],
                    "status": state,
                    "run_outcome": run_outcome,
                    "trigger": "pipeline",
                    "preset": snapshot["preset"],
                    "phases": snapshot["phases"],
                    "started_at": snapshot["started_at"],
                    "completed_at": datetime.now(UTC).isoformat(),
                    "duration_seconds": duration,
                }
            # Add parallel-mode metadata if present
            if snapshot.get("parallel_mode"):
                entry["parallel_mode"] = True
                entry["task_ids"] = snapshot.get("task_ids", [])
                entry["task_results"] = snapshot.get("task_results", {})
            append_run_to_history(entry)
        except Exception as exc:
            logger.warning("Failed to write history entry: %s", exc)

    # Mapping from crew_type in metrics to parent phase_id
    _CREW_PHASE_MAP: dict[str, str] = {
        # Phase 1 (Facts)
        "architecture_collector": "extract",
        "dependency_collector": "extract",
        "quality_collector": "extract",
        "security_collector": "extract",
        "test_collector": "extract",
        # Phase 2 (Analysis)
        "architecture_analyzer": "analyze",
        "dependency_analyzer": "analyze",
        "quality_analyzer": "analyze",
        "impact_analyzer": "analyze",
        # Phase 3 (Synthesis)
        "synthesis_crew": "document",
        "cross_cutting_crew": "document",
        "recommendation_crew": "document",
        "C4": "document",
        "Arc42": "document",
        "C4Crew": "document",
        "Arc42Crew": "document",
        # Phase 4 (Planning)
        "planning_crew": "plan",
        # Phase 5 (CodeGen)
        "code_generation_crew": "implement",
        "code_validation_crew": "implement",
    }

    def _resolve_bound_run_id(self) -> str | None:
        """Resolve the active engine run_id for this executor run."""
        if self._engine_run_id:
            return self._engine_run_id

        proc = self._process
        if proc is None or proc.pid is None:
            return None

        state_path = settings.logs_dir / "phase_state.json"
        if not state_path.exists():
            return None

        try:
            with open(state_path, encoding="utf-8") as f:
                state = json.load(f)
            if state.get("pid") == proc.pid and state.get("run_id"):
                self._engine_run_id = str(state["run_id"])
                return self._engine_run_id
        except (OSError, json.JSONDecodeError):
            return None

        return None

    @staticmethod
    def _extract_event_name(event: dict, data: dict) -> str:
        """Read event name across production and legacy metric shapes."""
        return data.get("event") or event.get("msg") or event.get("event") or ""

    @staticmethod
    def _extract_event_run_id(event: dict, data: dict) -> str | None:
        """Read run_id across production and legacy metric shapes."""
        run_id = data.get("run_id") or event.get("run_id")
        return str(run_id) if run_id else None

    def _event_in_active_scope(self, event: dict, data: dict, bound_run_id: str | None) -> bool:
        """Check whether a metric event belongs to this run."""
        event_run_id = self._extract_event_run_id(event, data)

        if bound_run_id:
            return event_run_id == bound_run_id

        if self._run_started_wall:
            event_ts = str(event.get("ts", ""))[:19]
            if event_ts and event_ts < self._run_started_wall:
                return False

        return True

    def _detect_phase_from_log(self, task_id: str, line: str) -> None:
        """Parse subprocess log line to detect phase transitions.

        Must be called with _task_states_lock held.
        Expected log patterns:
            [Phase] Triage (triage)
            [Phase] Development Planning (plan)
            [Phase] ... — completed in X.Xs
            [Phase] ... — skipped in X.Xs
            [Phase] ... — failed ...
        """
        if "[Phase]" not in line:
            return

        ts = self._task_states.get(task_id)
        if not ts:
            return

        # Phase completion: look for "completed" / "success" / "skipped" / "partial"
        # Orchestrator writes: "[Phase] Display — {status} in X.XXs"
        # where status is one of: success, partial, skipped, failed
        if "completed in" in line or "success in" in line or "skipped in" in line or "partial in" in line:
            current = ts.get("current_phase")
            if current:
                completed = ts.get("completed_phases", [])
                if current not in completed:
                    completed.append(current)
                ts["completed_phases"] = completed
                ts["current_phase"] = None
            return

        if "failed" in line.lower():
            # Mark current phase as completed (with failure) so stepper advances
            current = ts.get("current_phase")
            if current:
                completed = ts.get("completed_phases", [])
                if current not in completed:
                    completed.append(current)
                ts["completed_phases"] = completed
                ts["current_phase"] = None
            return

        # Phase start: extract phase_id from parentheses, e.g. "[Phase] Triage (triage)"
        m = re.search(r"\[Phase\]\s+.+?\((\w+)\)", line)
        if m:
            phase_id = m.group(1)
            ts["current_phase"] = phase_id

    def _read_phase_state_file(self) -> dict[str, dict]:
        """Read phase_state.json written by subprocesses to get actual per-phase status."""
        state_file = settings.project_root / "logs" / "phase_state.json"
        if not state_file.exists():
            return {}
        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
            return data.get("phases", {})
        except Exception:
            return {}

    def _read_phase_progress(self) -> list[dict]:
        """Read phase progress from metrics.jsonl tail, including sub-phase data."""
        progress: dict[str, dict] = {}
        sub_phases: dict[str, list[dict]] = {}  # phase_id -> list of sub-phase dicts
        metrics_file = settings.metrics_file

        if not metrics_file.exists():
            return []

        saw_active_event = False

        try:
            with open(metrics_file, encoding="utf-8") as f:
                lines = f.readlines()

            recent = lines[-1000:]
            bound_run_id = self._resolve_bound_run_id()

            for line in recent:
                try:
                    event = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue

                data = event.get("data", {})
                event_name = self._extract_event_name(event, data)
                if not event_name:
                    continue

                if not self._event_in_active_scope(event, data, bound_run_id):
                    continue
                saw_active_event = True

                if event_name == "phase_start":
                    phase_id = data.get("phase") or data.get("phase_id", "")
                    if not phase_id:
                        continue
                    progress[phase_id] = {
                        "phase_id": phase_id,
                        "name": data.get("name", phase_id),
                        "status": PHASE_PROGRESS_RUNNING,
                        "started_at": event.get("ts"),
                        "duration_seconds": None,
                        "skip_reason": None,
                        "sub_phases": [],
                        "total_tokens": 0,
                    }
                elif event_name == "phase_complete":
                    phase_id = data.get("phase") or data.get("phase_id", "")
                    if not phase_id:
                        continue
                    completed_status = normalize_phase_progress_status(
                        data.get("status"),
                        default=PHASE_PROGRESS_COMPLETED,
                    )
                    if completed_status in (PHASE_PROGRESS_PENDING, PHASE_PROGRESS_RUNNING):
                        completed_status = PHASE_PROGRESS_COMPLETED
                    if phase_id in progress:
                        progress[phase_id]["status"] = completed_status
                        progress[phase_id]["duration_seconds"] = data.get("duration_seconds")
                        progress[phase_id]["skip_reason"] = None
                    else:
                        progress[phase_id] = {
                            "phase_id": phase_id,
                            "name": data.get("name", phase_id),
                            "status": completed_status,
                            "started_at": None,
                            "duration_seconds": data.get("duration_seconds"),
                            "skip_reason": None,
                            "sub_phases": [],
                            "total_tokens": 0,
                        }
                elif event_name == "phase_failed":
                    phase_id = data.get("phase") or data.get("phase_id", "")
                    if not phase_id:
                        continue
                    if phase_id in progress:
                        progress[phase_id]["status"] = PHASE_PROGRESS_FAILED
                        progress[phase_id]["skip_reason"] = None
                    else:
                        progress[phase_id] = {
                            "phase_id": phase_id,
                            "name": data.get("name", phase_id),
                            "status": PHASE_PROGRESS_FAILED,
                            "started_at": None,
                            "duration_seconds": None,
                            "skip_reason": None,
                            "sub_phases": [],
                            "total_tokens": 0,
                        }
                elif event_name == "phase_skipped":
                    phase_id = data.get("phase") or data.get("phase_id", "")
                    if not phase_id:
                        continue
                    reason = str(data.get("reason", "")).strip().lower() or None
                    progress[phase_id] = {
                        "phase_id": phase_id,
                        "name": data.get("name", phase_id),
                        "status": PHASE_PROGRESS_SKIPPED,
                        "started_at": None,
                        "duration_seconds": None,
                        "skip_reason": reason,
                        "sub_phases": [],
                        "total_tokens": 0,
                    }
                elif event_name in ("mini_crew_complete", "mini_crew_failed"):
                    crew_type = data.get("crew_type", "")
                    parent_phase = self._CREW_PHASE_MAP.get(crew_type, "")
                    tokens = data.get("total_tokens", 0) or data.get("tokens", 0) or 0
                    raw_tasks = data.get("tasks", [])
                    tasks_list = raw_tasks if isinstance(raw_tasks, list) else []
                    sub = {
                        "name": data.get("crew_name", crew_type),
                        "status": PHASE_PROGRESS_COMPLETED
                        if event_name == "mini_crew_complete"
                        else PHASE_PROGRESS_FAILED,
                        "duration_seconds": data.get("duration_seconds"),
                        "total_tokens": tokens,
                        "tasks": tasks_list,
                    }
                    if parent_phase not in sub_phases:
                        sub_phases[parent_phase] = []
                    sub_phases[parent_phase].append(sub)
        except Exception as exc:
            logger.warning("Failed to read metrics for progress: %s", exc)

        if self.state == "running" and not saw_active_event:
            return self._pending_phase_list()

        # Attach sub-phases and aggregate tokens
        for phase_id, phase_data in progress.items():
            subs = sub_phases.get(phase_id, [])
            phase_data["sub_phases"] = subs
            phase_data["total_tokens"] = sum(s.get("total_tokens", 0) for s in subs)

        if not progress and self.state == "running":
            return self._pending_phase_list()

        if self.current_run and self.current_run.phases:
            ordered: list[dict] = []
            seen: set[str] = set()
            for phase_id in self.current_run.phases:
                if phase_id in progress:
                    ordered.append(progress[phase_id])
                    seen.add(phase_id)
            for phase_id, phase_data in progress.items():
                if phase_id not in seen:
                    ordered.append(phase_data)
            return ordered

        return list(progress.values())

    @staticmethod
    def _is_unregistered_skip(phase: dict) -> bool:
        status = normalize_phase_progress_status(phase.get("status"), default=PHASE_PROGRESS_PENDING)
        if status != PHASE_PROGRESS_SKIPPED:
            return False
        return str(phase.get("skip_reason") or "").strip().lower() == "unregistered"

    @staticmethod
    def _is_completed_phase(phase: dict) -> bool:
        status = normalize_phase_progress_status(phase.get("status"), default=PHASE_PROGRESS_PENDING)
        return status in (PHASE_PROGRESS_COMPLETED, PHASE_PROGRESS_PARTIAL)

    @staticmethod
    def _compute_run_outcome(phase_progress: list[dict]) -> str:
        """Compute aggregate run outcome from phase progress.

        Returns one of: 'success', 'all_skipped', 'partial', 'failed'.
        """
        return compute_run_outcome(p.get("status") for p in phase_progress)

    def _read_live_metrics(self) -> dict | None:
        """Aggregate live token usage and crew completions from metrics.jsonl."""
        metrics_file = settings.metrics_file
        if not metrics_file.exists():
            return None

        total_tokens = 0
        crew_completions = 0

        try:
            with open(metrics_file, encoding="utf-8") as f:
                lines = f.readlines()

            bound_run_id = self._resolve_bound_run_id()

            for line in lines[-500:]:
                try:
                    event = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue

                data = event.get("data", {})
                event_name = self._extract_event_name(event, data)
                if not event_name:
                    continue
                if not self._event_in_active_scope(event, data, bound_run_id):
                    continue

                if event_name == "mini_crew_complete":
                    total_tokens += data.get("total_tokens", 0) or data.get("tokens", 0) or 0
                    crew_completions += 1
        except Exception as exc:
            logger.warning("Failed to read live metrics: %s", exc)
            return None

        return {"total_tokens": total_tokens, "crew_completions": crew_completions}

    def _pending_phase_list(self) -> list[dict]:
        """Return expected phases as pending placeholders (before subprocess writes events)."""
        if not self.current_run or not self.current_run.phases:
            return []
        return [
            {
                "phase_id": phase_id,
                "name": phase_id.replace("_", " ").title(),
                "status": PHASE_PROGRESS_PENDING,
                "started_at": None,
                "duration_seconds": None,
                "sub_phases": [],
                "total_tokens": 0,
            }
            for phase_id in self.current_run.phases
        ]

    def _check_external_run(self) -> dict | None:
        """Check phase_state.json for an external CLI run in progress."""
        import os as _os

        state_path = settings.logs_dir / "phase_state.json"
        if not state_path.exists():
            return None

        try:
            with open(state_path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

        pid = data.get("pid")
        phases = data.get("phases", {})

        # Check if any phase is running and PID is alive
        has_running = any(
            normalize_phase_progress_status(entry.get("status"), default=PHASE_PROGRESS_PENDING)
            == PHASE_PROGRESS_RUNNING
            for entry in phases.values()
        )
        if not has_running:
            return None

        # Verify the process is actually alive
        try:
            _os.kill(pid, 0)
        except (OSError, ProcessLookupError, TypeError):
            return None

        # External run is active — build a status response
        run_id = data.get("run_id", "cli")
        phase_progress = []
        for phase_id, entry in phases.items():
            normalized_status = normalize_phase_progress_status(
                entry.get("status"),
                default=PHASE_PROGRESS_PENDING,
            )
            phase_progress.append(
                {
                    "phase_id": phase_id,
                    "name": phase_id.replace("_", " ").title(),
                    "status": normalized_status,
                    "started_at": entry.get("started_at"),
                    "duration_seconds": entry.get("duration_seconds"),
                    "sub_phases": [],
                    "total_tokens": 0,
                }
            )

        completed = sum(1 for phase in phase_progress if self._is_completed_phase(phase))
        skipped = sum(
            1
            for phase in phase_progress
            if normalize_phase_progress_status(phase.get("status"), default=PHASE_PROGRESS_PENDING)
            == PHASE_PROGRESS_SKIPPED
        )
        total = len(phase_progress) if phase_progress else 1
        progress = round((completed + skipped) / total * 100, 1)

        return {
            "state": "running",
            "run_id": run_id,
            "preset": None,
            "phases": list(phases.keys()),
            "started_at": data.get("updated_at"),
            "elapsed_seconds": None,
            "phase_progress": phase_progress,
            "progress_percent": progress,
            "completed_phase_count": completed,
            "skipped_phase_count": skipped,
            "total_phase_count": total,
            "eta_seconds": None,
            "live_metrics": None,
        }

    def _estimate_eta(self, elapsed: float | None) -> float | None:
        """Estimate remaining time based on historical run durations."""
        if not elapsed or elapsed < 5:
            return None

        try:
            from .history_service import get_run_history

            recent = get_run_history(limit=10)
            durations = [
                r["duration_seconds"]
                for r in recent
                if r.get("duration_seconds") and r.get("status") == "completed" and r.get("trigger") == "pipeline"
            ]
            if len(durations) < 2:
                return None
            avg_duration = sum(durations) / len(durations)
            remaining = avg_duration - elapsed
            return round(max(remaining, 0), 1)
        except Exception as exc:
            logger.debug("Failed to estimate ETA: %s", exc)
            return None

    def _write_env_with_overrides(self, overrides: dict[str, str], target: Path) -> None:
        """Write a .env file based on the current one with overrides applied."""
        # Validate overrides against injection
        for key, value in overrides.items():
            if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
                raise ValueError(f"Invalid env key: {key!r}")
            if "\n" in value or "\r" in value or "\x00" in value:
                raise ValueError(f"Env value for {key!r} contains invalid characters")

        lines: list[str] = []

        if settings.env_file.exists():
            with open(settings.env_file, encoding="utf-8") as f:
                lines = f.readlines()

        applied = set()
        result: list[str] = []

        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                key = stripped.split("=", 1)[0].strip()
                if key in overrides:
                    result.append(f"{key}={overrides[key]}\n")
                    applied.add(key)
                    continue
            result.append(line)

        # Add any new keys not in original
        for key, value in overrides.items():
            if key not in applied:
                result.append(f"{key}={value}\n")

        with open(target, "w", encoding="utf-8") as f:
            f.writelines(result)


# Module-level singleton
executor = PipelineExecutor()
