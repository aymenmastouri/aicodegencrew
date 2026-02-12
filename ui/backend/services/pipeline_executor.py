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

            # Build command
            cmd = [sys.executable, "-m", "aicodegencrew", "run"]
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
                    # No matching preset — use full_pipeline as fallback
                    cmd.extend(["--preset", "full_pipeline"])

            # Write temp .env with overrides if needed
            env_path = settings.env_file
            if env_overrides:
                env_path = settings.project_root / ".env.run"
                self._write_env_with_overrides(env_overrides, env_path)

            cmd.extend(["--env", str(env_path)])

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
                logger.info("Pipeline cancelled: run_id=%s", self.current_run.run_id if self.current_run else "?")
                return True
            except Exception as exc:
                logger.error("Failed to cancel pipeline: %s", exc)
                return False

    def get_status(self) -> dict:
        """Get current execution status."""
        elapsed = None
        if self._started_at and self.state == "running":
            elapsed = round(time.monotonic() - self._started_at, 1)
        elif self._started_at and self.state in ("completed", "failed", "cancelled"):
            # Keep last elapsed
            elapsed = round(time.monotonic() - self._started_at, 1)

        phase_progress = self._read_phase_progress()

        return {
            "state": self.state,
            "run_id": self.current_run.run_id if self.current_run else None,
            "preset": self.current_run.preset if self.current_run else None,
            "phases": self.current_run.phases if self.current_run else [],
            "started_at": self.current_run.started_at if self.current_run else None,
            "elapsed_seconds": elapsed,
            "phase_progress": phase_progress,
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

        # Check for archived reports in knowledge archive
        archive_dir = settings.knowledge_dir / "archive"
        if archive_dir.exists():
            for report_file in sorted(archive_dir.glob("run_report*.json"), reverse=True):
                try:
                    with open(report_file, encoding="utf-8") as f:
                        data = json.load(f)
                    reports.append(self._format_history_entry(data))
                except (json.JSONDecodeError, KeyError):
                    continue

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
                    logger.info(
                        "Pipeline finished: run_id=%s, exit_code=%d, state=%s",
                        self.current_run.run_id if self.current_run else "?",
                        self._exit_code,
                        self.state,
                    )
        except Exception as exc:
            logger.error("Monitor thread error: %s", exc)
            with self._state_lock:
                if self.state == "running":
                    self.state = "failed"

    def _read_phase_progress(self) -> list[dict]:
        """Read phase progress from metrics.jsonl tail."""
        progress: dict[str, dict] = {}
        metrics_file = settings.metrics_file

        if not metrics_file.exists():
            return []

        try:
            with open(metrics_file, encoding="utf-8") as f:
                lines = f.readlines()

            # Only look at recent lines (last 200)
            for line in lines[-200:]:
                try:
                    event = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue

                event_name = event.get("event", "")
                data = event.get("data", {})

                # Match current run by checking recent timestamps
                if event_name == "phase_start":
                    phase_id = data.get("phase", "")
                    progress[phase_id] = {
                        "phase_id": phase_id,
                        "name": data.get("name", phase_id),
                        "status": "running",
                        "started_at": event.get("timestamp"),
                        "duration_seconds": None,
                    }
                elif event_name == "phase_complete":
                    phase_id = data.get("phase", "")
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
                        }
                elif event_name == "phase_failed":
                    phase_id = data.get("phase", "")
                    if phase_id in progress:
                        progress[phase_id]["status"] = "failed"
                    else:
                        progress[phase_id] = {
                            "phase_id": phase_id,
                            "name": data.get("name", phase_id),
                            "status": "failed",
                            "started_at": None,
                            "duration_seconds": None,
                        }
        except Exception as exc:
            logger.warning("Failed to read metrics for progress: %s", exc)

        return list(progress.values())

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
