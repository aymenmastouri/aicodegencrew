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
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from aicodegencrew.pipeline_contract import (
    PHASE_PROGRESS_COMPLETED,
    PHASE_PROGRESS_FAILED,
    PHASE_PROGRESS_PENDING,
    PHASE_PROGRESS_PARTIAL,
    PHASE_PROGRESS_RUNNING,
    PHASE_PROGRESS_SKIPPED,
    compute_run_outcome,
    normalize_phase_progress_status,
)

from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class RunInfo:
    run_id: str
    preset: str | None
    phases: list[str]
    started_at: str
    pid: int | None = None


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

    @staticmethod
    def _filter_disabled_phases(phase_ids: list[str]) -> list[str]:
        """Hide config-disabled phases from UI progress totals/lists."""
        if not phase_ids:
            return phase_ids
        try:
            from .phase_runner import get_phases

            enabled_by_id = {p.id: bool(p.enabled) for p in get_phases()}
            return [phase_id for phase_id in phase_ids if enabled_by_id.get(phase_id, True)]
        except Exception:
            return phase_ids

    def cancel(self) -> bool:
        """Cancel the running pipeline. Returns True if cancelled."""
        with self._state_lock:
            if self.state != "running" or self._process is None:
                return False

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

                # Mark any "running" phases as failed in phase_state.json
                self._mark_running_phases_cancelled()

                return True
            except Exception as exc:
                logger.error("Failed to cancel pipeline: %s", exc)
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
                except Exception:
                    pass

            phases = data.setdefault("phases", {})
            modified = False

            # Mark any currently-running phases as failed
            for entry in phases.values():
                if entry.get("status") == "running":
                    entry["status"] = "failed"
                    entry["error"] = "Cancelled by user"
                    entry["completed_at"] = now
                    modified = True

            # Create 'cancelled' entries for phases that never started
            if self.current_run and self.current_run.phases:
                for phase_id in self.current_run.phases:
                    if phase_id not in phases:
                        phases[phase_id] = {
                            "status": "skipped",
                            "started_at": None,
                            "completed_at": now,
                            "duration_seconds": None,
                            "error": "Cancelled before phase started",
                        }
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
        # Auto-reset to idle after 120s in a terminal state
        if self.state in ("completed", "failed", "cancelled") and self._finished_at:
            if time.monotonic() - self._finished_at > 120:
                with self._state_lock:
                    self.state = "idle"
                    self._finished_at = None
                    self._started_at = None
                    self.current_run = None
                    self._engine_run_id = None
                    self._run_started_wall = None

        # Detect external CLI runs when executor is idle
        if self.state == "idle":
            ext = self._check_external_run()
            if ext:
                return ext

        elapsed = None
        if self._started_at and self.state == "running":
            elapsed = round(time.monotonic() - self._started_at, 1)
        elif self._started_at and self.state in ("completed", "failed", "cancelled"):
            # Show elapsed since run started (not growing endlessly)
            elapsed = round((self._finished_at or time.monotonic()) - self._started_at, 1)

        raw_phase_progress = (
            self._read_phase_progress() if self.state in ("running", "completed", "failed", "cancelled") else []
        )
        phase_progress = [p for p in raw_phase_progress if not self._is_unregistered_skip(p)]
        if self.current_run and self.current_run.phases:
            current_phase_ids = set(self.current_run.phases)
            unregistered_count = sum(
                1
                for phase in raw_phase_progress
                if self._is_unregistered_skip(phase) and phase.get("phase_id") in current_phase_ids
            )
        else:
            unregistered_count = len(raw_phase_progress) - len(phase_progress)

        # Compute progress percent
        total = len(self.current_run.phases) if self.current_run else 0
        completed = sum(1 for p in phase_progress if self._is_completed_phase(p))
        skipped = sum(
            1
            for p in phase_progress
            if normalize_phase_progress_status(p.get("status"), default=PHASE_PROGRESS_PENDING) == PHASE_PROGRESS_SKIPPED
        )
        running = sum(
            1
            for p in phase_progress
            if normalize_phase_progress_status(p.get("status"), default=PHASE_PROGRESS_PENDING) == PHASE_PROGRESS_RUNNING
        )
        if total > 0 and unregistered_count > 0:
            total = max(total - unregistered_count, 0)
        if phase_progress:
            observed = len(phase_progress)
            if total == 0:
                total = observed
            # Full preset may include phases that are intentionally unregistered/skipped
            # (e.g., verify/deliver planned but not implemented). Show 100% on success.
            elif self.state == "completed" and (completed + skipped) == observed:
                total = observed
        done = completed + skipped
        progress = round((done + running * 0.5) / total * 100, 1) if total > 0 else 0

        # Live metrics
        live_metrics = self._read_live_metrics() if self.state == "running" else None

        # ETA estimation
        eta = self._estimate_eta(elapsed) if self.state == "running" and elapsed else None

        # Compute run_outcome for terminal states
        run_outcome = None
        if self.state in ("completed", "failed"):
            run_outcome = self._compute_run_outcome(phase_progress) if phase_progress else (
                "success" if self.state == "completed" else "failed"
            )

        return {
            "state": self.state,
            "run_id": self.current_run.run_id if self.current_run else None,
            "preset": self.current_run.preset if self.current_run else None,
            "phases": self.current_run.phases if self.current_run else [],
            "started_at": self.current_run.started_at if self.current_run else None,
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
            "preset": data.get("environment", {}).get("preset"),
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

            self._exit_code = proc.wait()

            with self._state_lock:
                if self.state == "running":
                    self.state = "completed" if self._exit_code == 0 else "failed"
                    self._finished_at = time.monotonic()
                    logger.info(
                        "Pipeline finished: run_id=%s, exit_code=%d, state=%s",
                        self.current_run.run_id if self.current_run else "?",
                        self._exit_code,
                        self.state,
                    )

            # Append to JSONL run history
            self._append_history_entry()

        except Exception as exc:
            logger.error("Monitor thread error: %s", exc)
            with self._state_lock:
                if self.state == "running":
                    self.state = "failed"
                    self._finished_at = time.monotonic()
            self._append_history_entry()

    _RUN_ID_RE = re.compile(r"\brun_id=([0-9a-f]{8})\b")

    @classmethod
    def _extract_engine_run_id_from_line(cls, line: str) -> str | None:
        """Extract engine run_id from subprocess log output."""
        match = cls._RUN_ID_RE.search(line)
        if match:
            return match.group(1)
        return None

    def _append_history_entry(self) -> None:
        """Append a run entry to the JSONL history."""
        if not self.current_run:
            return
        try:
            from .history_service import append_run_to_history

            duration = round(time.monotonic() - self._started_at, 1) if self._started_at else None
            raw_phase_progress = self._read_phase_progress() if self.state in ("completed", "failed", "cancelled") else []
            phase_progress = [p for p in raw_phase_progress if not self._is_unregistered_skip(p)]
            run_outcome = None
            if self.state in ("completed", "failed"):
                if phase_progress:
                    run_outcome = self._compute_run_outcome(phase_progress)
                else:
                    # No metrics events — try phase_state.json as secondary source
                    # before falling back to a coarse success/failed value.
                    try:
                        state_path = settings.logs_dir / "phase_state.json"
                        if state_path.exists():
                            with open(state_path, encoding="utf-8") as _f:
                                _state = json.load(_f)
                            _statuses = [e.get("status") for e in _state.get("phases", {}).values()]
                            if _statuses:
                                run_outcome = compute_run_outcome(iter(_statuses))
                    except Exception:
                        pass
                    if run_outcome is None:
                        run_outcome = "success" if self.state == "completed" else "failed"
            append_run_to_history(
                {
                    "run_id": self.current_run.run_id,
                    "engine_run_id": self._engine_run_id,
                    "status": self.state,
                    "run_outcome": run_outcome,
                    "trigger": "pipeline",
                    "preset": self.current_run.preset,
                    "phases": self.current_run.phases,
                    "started_at": self.current_run.started_at,
                    "completed_at": datetime.now(UTC).isoformat(),
                    "duration_seconds": duration,
                }
            )
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
                        "status": PHASE_PROGRESS_COMPLETED if event_name == "mini_crew_complete" else PHASE_PROGRESS_FAILED,
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
            normalize_phase_progress_status(entry.get("status"), default=PHASE_PROGRESS_PENDING) == PHASE_PROGRESS_RUNNING
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
        except Exception:
            return None

    def _write_env_with_overrides(self, overrides: dict[str, str], target: Path) -> None:
        """Write a .env file based on the current one with overrides applied."""
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
