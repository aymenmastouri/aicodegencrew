"""
SDLC Pipeline Orchestrator
==========================

Simple, clear orchestration of SDLC phases.

Design Principles:
- Single Responsibility: Only orchestrates phase execution
- Explicit over Implicit: No magic, clear flow
- Fail Fast: Stop on first error by default
- Dependency Injection: Phases are registered, not hardcoded
"""

import concurrent.futures as _cf
import json as _json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from .phase_registry import PHASES, outputs_exist
from .pipeline_contract import (
    PhaseContext,
    PipelineContract,
    build_pipeline_contract,
    compute_run_outcome,
    is_phase_result_success,
    load_pipeline_contract,
    normalize_phase_result_status,
    phase_result_to_phase_state_status,
)
from .shared.utils.logger import RUN_ID, log_metric, logger
from .shared.utils.phase_state import init_run, set_phase_completed, set_phase_failed, set_phase_running

# =============================================================================
# PHASE CONTRACTS (ARCH-5)
# =============================================================================
# Declares what each phase requires and provides. Used by _check_dependencies()
# to log contract violations (observational — not a hard gate; the existing
# get_dependencies() system already handles blocking).
PHASE_CONTRACTS: dict[str, dict] = {
    "discover":  {"requires": [],              "provides": ["discover"]},
    "extract":   {"requires": ["discover"],    "provides": ["extract"]},
    "analyze":   {"requires": ["extract"],     "provides": ["analyze"]},
    "document":  {"requires": ["analyze"],     "provides": ["document"]},
    "plan":      {"requires": ["extract"],     "provides": ["plan"]},
    "implement": {"requires": ["plan"],        "provides": ["implement"]},
    "verify":    {"requires": ["implement"],   "provides": ["verify"]},
    "deliver":   {"requires": ["implement"],   "provides": ["deliver"]},
}

# Phase-level wall-clock timeout (ARCH-6). Thread-based — compatible with Windows.
# Override with PHASE_TIMEOUT_SECONDS env var (default: 3600s = 1 hour).
_PHASE_TIMEOUT_S: int = int(os.getenv("PHASE_TIMEOUT_SECONDS", "3600"))

# =============================================================================
# PROTOCOLS (Interfaces)
# =============================================================================


class PhaseExecutable(Protocol):
    """Interface for executable phases (Pipeline or Crew)."""

    def kickoff(self, inputs: dict[str, Any] = None) -> dict[str, Any]:
        """Execute the phase and return results."""
        ...


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class PhaseResult:
    """Result of a single phase execution."""

    phase_id: str
    status: str  # 'success', 'partial', 'failed', 'skipped'
    message: str = ""
    output: Any = None
    duration_seconds: float = 0.0

    def is_success(self) -> bool:
        return is_phase_result_success(self.status)

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase_id,
            "status": self.status,
            "message": self.message,
            "duration": f"{self.duration_seconds:.2f}s",
        }


@dataclass
class PipelineResult:
    """Result of entire pipeline execution."""

    status: str  # 'success', 'failed'
    message: str
    phases: list[PhaseResult] = field(default_factory=list)
    total_duration: str = ""
    run_outcome: str = ""  # 'success', 'all_skipped', 'partial', 'failed'
    skipped_phase_count: int = 0
    completed_phase_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "message": self.message,
            "phases": [p.to_dict() for p in self.phases],
            "total_duration": self.total_duration,
            "run_outcome": self.run_outcome,
            "skipped_phase_count": self.skipped_phase_count,
            "completed_phase_count": self.completed_phase_count,
        }


# =============================================================================
# ORCHESTRATOR
# =============================================================================


class SDLCOrchestrator:
    """
    Orchestrates SDLC phase execution.

    Usage:
        orchestrator = SDLCOrchestrator()
        orchestrator.register("discover", IndexingPipeline(...))
        orchestrator.register("extract", ArchFactsPipeline(...))
        orchestrator.register("analyze", AnalysisCrew(...))

        result = orchestrator.run(preset="document")
    """

    def __init__(self, config_path: str | None = None):
        """Initialize with optional config path."""
        self.config_path = config_path or self._default_config_path()
        self.config = self._load_config()
        self.contract: PipelineContract = build_pipeline_contract(self.config, config_path=self.config_path)
        self.phases: dict[str, PhaseExecutable] = {}
        self.results: dict[str, PhaseResult] = {}
        self.phase_context = PhaseContext()
        self._start_time: datetime | None = None
        # PERF-2: architecture_facts.json cached after extract phase completes.
        # Downstream phases can read from inputs["previous_results"]["facts"]
        # instead of re-loading the 2.8 MB file from disk.
        self._facts_cache: dict = {}

        logger.info("[Orchestrator] Initialized")

    # -------------------------------------------------------------------------
    # PUBLIC API
    # -------------------------------------------------------------------------

    def register(self, phase_id: str, executable: PhaseExecutable) -> "SDLCOrchestrator":
        """
        Register a phase for execution.

        Args:
            phase_id: Unique phase identifier (e.g., "discover")
            executable: Pipeline or Crew instance with kickoff() method

        Returns:
            self (for chaining)
        """
        self.phases[phase_id] = executable
        logger.debug(f"[Orchestrator] Registered: {phase_id}")
        return self

    # Backward compatibility alias
    def register_phase(self, phase_id: str, executable: PhaseExecutable) -> "SDLCOrchestrator":
        """Alias for register() for backward compatibility."""
        return self.register(phase_id, executable)

    def run(
        self, preset: str | None = None, phases: list[str] | None = None, stop_on_error: bool = True
    ) -> PipelineResult:
        """
        Execute the SDLC pipeline.

        Args:
            preset: Named preset from config (e.g., "document")
            phases: Explicit list of phases to run (overrides preset)
            stop_on_error: Stop execution on first failure

        Returns:
            PipelineResult with status and phase details
        """
        self._start_time = datetime.now()
        self.results.clear()
        self.contract = self._contract_from_current_config()

        # Use the logger's RUN_ID so that phase_state.json and metrics.jsonl
        # share the same run_id (avoids mismatch in executor progress tracking).
        run_id = RUN_ID
        init_run(run_id)

        # Determine phases to run
        phases_to_run = self._resolve_phases(preset, phases)
        self.phase_context = PhaseContext(
            run_id=run_id,
            preset_id=preset,
            requested_phases=list(phases or []),
            resolved_phases=list(phases_to_run),
        )

        if not phases_to_run:
            return PipelineResult(
                status="failed",
                message="No phases to run",
            )

        logger.info("=" * 60)
        logger.info(f"[Orchestrator] Starting pipeline: {phases_to_run}")
        logger.info("=" * 60)

        # Execute phases sequentially
        for phase_id in phases_to_run:
            result = self._execute_phase(phase_id)
            self.results[phase_id] = result

            if not result.is_success() and stop_on_error:
                return self._build_result("failed", f"Phase {phase_id} failed: {result.message}")

        return self._build_result("success", "Pipeline completed successfully")

    def get_presets(self) -> list[str]:
        """Get available preset names."""
        return self._contract_from_current_config().get_preset_names()

    def get_phase_config(self, phase_id: str) -> dict[str, Any]:
        """Get configuration for a specific phase."""
        return self._contract_from_current_config().get_phase_config(phase_id)

    def is_phase_enabled(self, phase_id: str) -> bool:
        """Check if a phase is enabled in configuration."""
        return self.get_phase_config(phase_id).get("enabled", False)

    def get_enabled_phases(self) -> list[str]:
        """Get enabled phases sorted by order."""
        return self._contract_from_current_config().get_enabled_phases()

    def get_preset_phases(self, preset_name: str) -> list[str]:
        """Get phases for a preset execution mode."""
        return self._contract_from_current_config().get_preset_phases(preset_name)

    # -------------------------------------------------------------------------
    # CONTEXT (Backward Compatibility)
    # -------------------------------------------------------------------------

    @property
    def context(self) -> dict[str, Any]:
        """Backward compatibility: return context-like structure."""
        return {
            "phases": {pid: {"status": r.status, "output": r.output} for pid, r in self.results.items()},
            "knowledge": {},
            "shared": {},
            "pipeline_context": self.phase_context.to_dict(),
        }

    # -------------------------------------------------------------------------
    # PRIVATE METHODS
    # -------------------------------------------------------------------------

    def _resolve_phases(self, preset: str | None, explicit_phases: list[str] | None) -> list[str]:
        """Resolve which phases to run."""
        phases = self._contract_from_current_config().resolve_requested_phases(
            preset=preset,
            explicit_phases=explicit_phases,
        )
        if preset and not phases:
            logger.warning(f"[Orchestrator] Unknown preset: {preset}")

        # Filter out unregistered phases (e.g., phase0 when INDEX_MODE=off)
        filtered: list[str] = []
        for phase_id in phases:
            if phase_id in self.phases:
                filtered.append(phase_id)
            else:
                logger.info(f"[Orchestrator] Phase '{phase_id}' not registered — nothing to do")
                log_metric("phase_skipped", phase_id=phase_id, reason="unregistered")
                set_phase_completed(phase_id, duration=0.0, status="skipped")

        return filtered

    def _get_enabled_phases(self) -> list[str]:
        """Get enabled phases sorted by order."""
        return self._contract_from_current_config().get_enabled_phases()

    def _execute_phase(self, phase_id: str) -> PhaseResult:
        """Execute a single phase."""
        start = datetime.now()
        self.phase_context.current_phase = phase_id

        # Check if registered
        if phase_id not in self.phases:
            logger.warning(f"[Orchestrator] Phase not registered: {phase_id}")
            return PhaseResult(
                phase_id=phase_id,
                status="skipped",
                message="Not registered",
            )

        # Check dependencies
        if not self._check_dependencies(phase_id):
            return PhaseResult(
                phase_id=phase_id,
                status="failed",
                message="Dependencies not met",
            )

        # Execute
        display = PHASES[phase_id].display_name if phase_id in PHASES else phase_id
        logger.info(f"[Phase] {display} ({phase_id})")

        log_metric("phase_start", phase_id=phase_id)
        set_phase_running(phase_id)

        try:
            executable = self.phases[phase_id]
            config = self._contract_from_current_config().phases.get(phase_id)
            phase_config = dict(config.config) if config else {}

            # Build inputs (PERF-2: include cached facts if available)
            previous_results = {pid: r.output for pid, r in self.results.items() if r.is_success()}
            if self._facts_cache:
                previous_results["facts"] = self._facts_cache
            inputs = {
                "config": phase_config,
                "previous_results": previous_results,
                "phase_context": self.phase_context.to_dict(),
                "context": self.context,
            }

            # Handle different execution styles
            output = self._invoke_executable(executable, inputs)

            # Phase implementations may report their own status in returned dict.
            phase_status = "success"
            phase_message = "Completed"
            if isinstance(output, dict):
                raw_status = output.get("status")
                phase_status = normalize_phase_result_status(raw_status, default="success")
                raw_message = output.get("message")
                if phase_status == "failed":
                    raise RuntimeError(str(raw_message or f"Phase {phase_id} reported failure"))
                if phase_status == "partial":
                    phase_message = str(raw_message or "Completed with degradations")
                elif phase_status == "skipped":
                    phase_message = str(raw_message or "Skipped")
                elif phase_status == "success":
                    phase_message = str(raw_message or "Completed")

            duration = (datetime.now() - start).total_seconds()
            metric_status = phase_result_to_phase_state_status(phase_status)
            phase_state_status = phase_result_to_phase_state_status(phase_status)

            logger.info(f"[Phase] {display} — {phase_status} in {duration:.2f}s")
            log_metric("phase_complete", phase_id=phase_id, duration_seconds=round(duration, 2), status=metric_status)
            set_phase_completed(phase_id, duration, status=phase_state_status)
            self.phase_context.metrics[phase_id] = {
                "duration_seconds": round(duration, 2),
                "status": metric_status,
            }
            self.phase_context.set_phase_result(phase_id=phase_id, status=phase_status, output=output, message=phase_message)

            # PERF-2: Cache architecture_facts.json after extract phase so downstream
            # phases can read from inputs["previous_results"]["facts"] without I/O.
            if phase_id == "extract" and phase_status in ("success", "partial"):
                facts_path = Path("knowledge/extract/architecture_facts.json")
                if facts_path.exists():
                    try:
                        self._facts_cache = _json.loads(facts_path.read_text(encoding="utf-8"))
                        logger.info(
                            "[Orchestrator] facts.json cached: %d top-level keys",
                            len(self._facts_cache),
                        )
                    except Exception as cache_err:
                        logger.warning("[Orchestrator] Could not cache facts.json: %s", cache_err)
                        self._facts_cache = {}

            # Auto-commit after successful phase
            self._git_commit_after_phase(phase_id)

            return PhaseResult(
                phase_id=phase_id,
                status=phase_status,
                message=phase_message,
                output=output,
                duration_seconds=duration,
            )

        except Exception as e:
            duration = (datetime.now() - start).total_seconds()
            logger.error(f"[Phase] {display} — failed: {e}", exc_info=True)
            log_metric("phase_failed", phase_id=phase_id, duration_seconds=round(duration, 2), error=str(e)[:500])
            set_phase_failed(phase_id, duration, str(e))
            self.phase_context.errors.append(f"{phase_id}: {e}")
            self.phase_context.set_phase_result(phase_id=phase_id, status="failed", output=None, message=str(e))

            return PhaseResult(
                phase_id=phase_id,
                status="failed",
                message=str(e),
                duration_seconds=duration,
            )

    def _invoke_executable(self, executable: PhaseExecutable, inputs: dict[str, Any]) -> Any:
        """Invoke phase with a wall-clock timeout (ARCH-6).

        Uses a thread-based timeout that is compatible with Windows (no SIGALRM).
        If the phase exceeds _PHASE_TIMEOUT_S seconds, TimeoutError is raised and
        the orchestrator records a failure — the background thread may continue
        running until the process exits (acceptable; Gradle/LLM timeouts are a
        separate concern handled by their own subprocess kill logic).
        """
        with _cf.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(executable.kickoff, inputs)
            try:
                return future.result(timeout=_PHASE_TIMEOUT_S)
            except _cf.TimeoutError:
                phase_id = inputs.get("config", {}).get("phase_id", "unknown")
                logger.error(
                    "[Orchestrator] Phase '%s' timed out after %ds. "
                    "Set PHASE_TIMEOUT_SECONDS env var to increase.",
                    phase_id, _PHASE_TIMEOUT_S,
                )
                raise TimeoutError(
                    f"Phase '{phase_id}' timed out after {_PHASE_TIMEOUT_S}s. "
                    f"Set PHASE_TIMEOUT_SECONDS env var to increase."
                )

    def _check_dependencies(self, phase_id: str) -> bool:
        """Check if phase dependencies are satisfied (existence + validation).

        Also performs ARCH-5 contract validation: logs a warning if required
        phase outputs are absent (observational only — blocking is handled by
        the existing dependency system above).
        """
        from .shared.validation import PhaseOutputValidator

        dependencies = self._contract_from_current_config().get_dependencies(phase_id)

        validator = PhaseOutputValidator()

        for dep in dependencies:
            # Check if ran successfully in this session
            if dep in self.results and self.results[dep].is_success():
                continue

            # Check if output files exist from previous run (CWD-relative)
            if outputs_exist(dep, Path(".")):
                # Validate output quality
                errors = validator.validate_phase(dep)
                if errors:
                    logger.warning(f"[Orchestrator] Dependency {dep} has validation warnings:")
                    for err in errors[:5]:
                        logger.warning(f"   - {err}")
                else:
                    logger.info(f"[Orchestrator] Dependency {dep} satisfied (output valid)")
                continue

            logger.error(f"[Orchestrator] Dependency not met: {phase_id} requires {dep}")
            return False

        # ARCH-5: Log phase contract violations (observational — not a hard block)
        contract = PHASE_CONTRACTS.get(phase_id, {})
        for required in contract.get("requires", []):
            if required not in self.results and not outputs_exist(required, Path(".")):
                logger.warning(
                    "[Orchestrator] Contract violation: %s requires '%s' output but it is absent",
                    phase_id, required,
                )

        return True

    def _compute_run_outcome(self) -> str:
        """Compute the aggregate run outcome from individual phase results.

        Returns one of: 'success', 'all_skipped', 'partial', 'failed'.
        """
        return compute_run_outcome(result.status for result in self.results.values())

    def _build_result(self, status: str, message: str) -> PipelineResult:
        """Build final pipeline result."""
        total_duration = ""
        total_seconds = 0.0
        if self._start_time:
            delta = datetime.now() - self._start_time
            total_duration = str(delta).split(".")[0]  # Remove microseconds
            total_seconds = delta.total_seconds()

        run_outcome = self._compute_run_outcome()

        logger.info("=" * 60)
        logger.info(f"[Orchestrator] Pipeline {status.upper()}: {message}")
        logger.info(f"[Orchestrator] Run outcome: {run_outcome}")
        logger.info(f"[Orchestrator] Duration: {total_duration}")
        logger.info("=" * 60)

        skipped_count = sum(1 for r in self.results.values() if r.status == "skipped")
        completed_count = sum(1 for r in self.results.values() if r.status in ("success", "partial"))

        log_metric(
            "pipeline_complete",
            status=status,
            run_outcome=run_outcome,
            total_duration=round(total_seconds, 2),
            phases_run=len(self.results),
            phases_succeeded=sum(1 for r in self.results.values() if r.is_success()),
            phases_skipped=skipped_count,
        )

        return PipelineResult(
            status=status,
            message=message,
            phases=list(self.results.values()),
            total_duration=total_duration,
            run_outcome=run_outcome,
            skipped_phase_count=skipped_count,
            completed_phase_count=completed_count,
        )

    def _load_config(self) -> dict[str, Any]:
        """Load configuration from YAML via the central pipeline contract."""
        contract = load_pipeline_contract(self.config_path, fallback_config=self._default_config())
        return dict(contract.raw_config)

    def _contract_from_current_config(self) -> PipelineContract:
        """Build contract from mutable runtime config (respects CLI toggles)."""
        self.contract = build_pipeline_contract(self.config, config_path=self.config_path)
        return self.contract

    def _default_config_path(self) -> str:
        """Get default config path."""
        return str(Path(__file__).parent.parent.parent / "config" / "phases_config.yaml")

    def _default_config(self) -> dict[str, Any]:
        """Return minimal default config."""
        return {
            "phases": {
                "discover": {"enabled": True, "order": 0},
            },
            "presets": {
                "index": ["discover"],
            },
        }

    # -------------------------------------------------------------------------
    # GIT OPERATIONS
    # -------------------------------------------------------------------------

    def _git_commit_after_phase(self, phase_id: str) -> bool:
        """
        Auto-commit knowledge/ after successful phase.

        BUG-C5 fix: Guard with CODEGEN_COMMIT_KNOWLEDGE env var (default: true).
        Set CODEGEN_COMMIT_KNOWLEDGE=false to disable auto-commits (useful when
        knowledge/ is in .gitignore or when running without a clean git state).

        Args:
            phase_id: The completed phase ID

        Returns:
            True if commit successful, False otherwise
        """
        import os
        if os.getenv("CODEGEN_COMMIT_KNOWLEDGE", "true").lower() in ("false", "0", "no"):
            logger.debug("[Orchestrator] CODEGEN_COMMIT_KNOWLEDGE=false — skipping knowledge/ commit")
            return False

        try:
            # Check if git repo
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                logger.debug("[Orchestrator] Not a git repository, skipping commit")
                return False

            # Stage knowledge/ directory
            subprocess.run(
                ["git", "add", "knowledge/"],
                capture_output=True,
                check=True,
            )

            # Check if there are staged changes
            result = subprocess.run(
                ["git", "diff", "--cached", "--quiet"],
                capture_output=True,
            )
            if result.returncode == 0:
                logger.debug("[Orchestrator] No changes to commit")
                return True

            # Commit with descriptive message
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            commit_msg = f"[aicodegencrew] {phase_id} completed - {timestamp}"

            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                capture_output=True,
                check=True,
            )

            logger.info(f"[Orchestrator] Git commit: {commit_msg}")
            return True

        except subprocess.CalledProcessError as e:
            logger.warning(f"[Orchestrator] Git commit failed: {e}")
            return False
        except FileNotFoundError:
            logger.debug("[Orchestrator] Git not found, skipping commit")
            return False
