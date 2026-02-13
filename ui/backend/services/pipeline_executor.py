"""Pipeline execution service using subprocess isolation."""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import threading
import time
import uuid
from collections.abc import Generator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

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
                # Pass phases as a custom preset isn't possible via CLI;
                # use the preset that matches or run individual phases
                # For now, find the best-matching preset
                from .phase_runner import get_presets

                for p in get_presets():
                    if set(p.phases) == set(phases):
                        cmd.extend(["--preset", p.name])
                        break
                else:
                    # No matching preset — use full as fallback
                    cmd.extend(["--preset", "full"])

            self.current_run = RunInfo(
                run_id=run_id,
                preset=preset,
                phases=phase_list,
                started_at=now,
            )
            self.state = "running"
            self._log_lines = []
            self._exit_code = None
            self._started_at = time.monotonic()
            self._finished_at = None

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

    def cancel(self) -> bool:
        """Cancel the running pipeline. Returns True if cancelled."""
        with self._state_lock:
            if self.state != "running" or self._process is None:
                return False

            try:
                self._process.terminate()
                # Give it 5 seconds to terminate gracefully
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._process.kill()
                self.state = "cancelled"
                self._finished_at = time.monotonic()
                logger.info("Pipeline cancelled: run_id=%s", self.current_run.run_id if self.current_run else "?")
                return True
            except Exception as exc:
                logger.error("Failed to cancel pipeline: %s", exc)
                return False

    def get_status(self) -> dict:
        """Get current execution status."""
        # Auto-reset to idle after 120s in a terminal state
        if self.state in ("completed", "failed", "cancelled") and self._finished_at:
            if time.monotonic() - self._finished_at > 120:
                with self._state_lock:
                    self.state = "idle"
                    self._finished_at = None

        elapsed = None
        if self._started_at and self.state == "running":
            elapsed = round(time.monotonic() - self._started_at, 1)
        elif self._started_at and self.state in ("completed", "failed", "cancelled"):
            # Show elapsed since run started (not growing endlessly)
            elapsed = round((self._finished_at or time.monotonic()) - self._started_at, 1)

        phase_progress = self._read_phase_progress() if self.state in ("running", "completed", "failed") else []

        # Compute progress percent
        total = len(self.current_run.phases) if self.current_run else 0
        if total == 0 and phase_progress:
            total = len(phase_progress)
        completed = sum(1 for p in phase_progress if p.get("status") == "completed")
        running = sum(1 for p in phase_progress if p.get("status") == "running")
        progress = round((completed + running * 0.5) / total * 100, 1) if total > 0 else 0

        # Live metrics
        live_metrics = self._read_live_metrics() if self.state == "running" else None

        # ETA estimation
        eta = self._estimate_eta(elapsed) if self.state == "running" and elapsed else None

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
            "total_phase_count": total,
            "eta_seconds": eta,
            "live_metrics": live_metrics,
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
        return {
            "run_id": data.get("run_id", "unknown"),
            "status": data.get("status", "unknown"),
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

    def _append_history_entry(self) -> None:
        """Append a run entry to the JSONL history."""
        if not self.current_run:
            return
        try:
            from .history_service import append_run_to_history

            duration = round(time.monotonic() - self._started_at, 1) if self._started_at else None
            append_run_to_history({
                "run_id": self.current_run.run_id,
                "status": self.state,
                "trigger": "pipeline",
                "preset": self.current_run.preset,
                "phases": self.current_run.phases,
                "started_at": self.current_run.started_at,
                "completed_at": datetime.now(UTC).isoformat(),
                "duration_seconds": duration,
            })
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
        # Phase 4 (Planning)
        "planning_crew": "plan",
        # Phase 5 (CodeGen)
        "code_generation_crew": "implement",
        "code_validation_crew": "implement",
    }

    def _read_phase_progress(self) -> list[dict]:
        """Read phase progress from metrics.jsonl tail, including sub-phase data."""
        progress: dict[str, dict] = {}
        sub_phases: dict[str, list[dict]] = {}  # phase_id -> list of sub-phase dicts
        metrics_file = settings.metrics_file

        if not metrics_file.exists():
            return []

        try:
            with open(metrics_file, encoding="utf-8") as f:
                lines = f.readlines()

            recent = lines[-500:]

            # Detect the most recent run_id to filter out old runs
            current_run_id = None
            for line in reversed(recent):
                try:
                    ev = json.loads(line.strip())
                    data = ev.get("data", {})
                    evt = data.get("event") or ev.get("msg", "")
                    if evt == "phase_start" and data.get("run_id"):
                        current_run_id = data["run_id"]
                        break
                except (json.JSONDecodeError, KeyError):
                    continue

            for line in recent:
                try:
                    event = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue

                data = event.get("data", {})
                event_name = data.get("event") or event.get("msg", "")

                # Filter to current run only
                if current_run_id and data.get("run_id") and data["run_id"] != current_run_id:
                    continue

                if event_name == "phase_start":
                    phase_id = data.get("phase") or data.get("phase_id", "")
                    if not phase_id:
                        continue
                    progress[phase_id] = {
                        "phase_id": phase_id,
                        "name": data.get("name", phase_id),
                        "status": "running",
                        "started_at": event.get("ts"),
                        "duration_seconds": None,
                        "sub_phases": [],
                        "total_tokens": 0,
                    }
                elif event_name == "phase_complete":
                    phase_id = data.get("phase") or data.get("phase_id", "")
                    if not phase_id:
                        continue
                    if phase_id in progress:
                        progress[phase_id]["status"] = "completed"
                        progress[phase_id]["duration_seconds"] = data.get("duration_seconds")
                    else:
                        progress[phase_id] = {
                            "phase_id": phase_id,
                            "name": data.get("name", phase_id),
                            "status": "completed",
                            "started_at": None,
                            "duration_seconds": data.get("duration_seconds"),
                            "sub_phases": [],
                            "total_tokens": 0,
                        }
                elif event_name == "phase_failed":
                    phase_id = data.get("phase") or data.get("phase_id", "")
                    if not phase_id:
                        continue
                    if phase_id in progress:
                        progress[phase_id]["status"] = "failed"
                    else:
                        progress[phase_id] = {
                            "phase_id": phase_id,
                            "name": data.get("name", phase_id),
                            "status": "failed",
                            "started_at": None,
                            "duration_seconds": None,
                            "sub_phases": [],
                            "total_tokens": 0,
                        }
                elif event_name in ("mini_crew_complete", "mini_crew_failed"):
                    crew_type = data.get("crew_type", "")
                    parent_phase = self._CREW_PHASE_MAP.get(crew_type, "")
                    tokens = data.get("total_tokens", 0) or data.get("tokens", 0) or 0
                    sub = {
                        "name": data.get("crew_name", crew_type),
                        "status": "completed" if event_name == "mini_crew_complete" else "failed",
                        "duration_seconds": data.get("duration_seconds"),
                        "total_tokens": tokens,
                        "tasks": data.get("tasks", []),
                    }
                    if parent_phase not in sub_phases:
                        sub_phases[parent_phase] = []
                    sub_phases[parent_phase].append(sub)
        except Exception as exc:
            logger.warning("Failed to read metrics for progress: %s", exc)

        # Attach sub-phases and aggregate tokens
        for phase_id, phase_data in progress.items():
            subs = sub_phases.get(phase_id, [])
            phase_data["sub_phases"] = subs
            phase_data["total_tokens"] = sum(s.get("total_tokens", 0) for s in subs)

        return list(progress.values())

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

            for line in lines[-300:]:
                try:
                    event = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue

                data = event.get("data", {})
                evt = data.get("event") or event.get("msg", "")
                if evt == "mini_crew_complete":
                    total_tokens += data.get("total_tokens", 0) or data.get("tokens", 0) or 0
                    crew_completions += 1
        except Exception as exc:
            logger.warning("Failed to read live metrics: %s", exc)
            return None

        return {"total_tokens": total_tokens, "crew_completions": crew_completions}

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
