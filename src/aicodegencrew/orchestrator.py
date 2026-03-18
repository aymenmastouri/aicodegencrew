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
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from .phase_registry import PHASES, get_cleanup_targets
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
from .shared.utils.logger import RUN_ID, log_metric, logger, set_run_id
from .shared.utils.mlflow_tracker import MLflowTracker
from .shared.utils.phase_state import init_run, set_phase_completed, set_phase_failed, set_phase_running

# =============================================================================
# PHASE CONTRACTS (ARCH-5)
# =============================================================================
# Declares what each phase requires and provides. Used by _check_dependencies()
# to log contract violations (observational — not a hard gate; the existing
# get_dependencies() system already handles blocking).
PHASE_CONTRACTS: dict[str, dict] = {
    "discover": {"requires": [], "provides": ["discover"]},
    "extract": {"requires": ["discover"], "provides": ["extract"]},
    "analyze": {"requires": ["extract"], "provides": ["analyze"]},
    "document": {"requires": ["analyze"], "provides": ["document"]},
    "triage": {"requires": ["discover", "extract"], "provides": ["triage"]},
    "plan": {"requires": ["extract"], "provides": ["plan"]},
    "implement": {"requires": ["plan"], "provides": ["implement"]},
    "verify": {"requires": ["implement"], "provides": ["verify"]},
    "deliver": {"requires": ["implement"], "provides": ["deliver"]},
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

    def __init__(self, config_path: str | None = None, task_id: str | None = None):
        """Initialize with optional config path.

        Args:
            config_path: Path to phases_config.yaml.
            task_id: Optional single task ID filter (--task-id). Injected into
                     inputs["config"]["task_id"] so phases can filter accordingly.
        """
        self.config_path = config_path or self._default_config_path()
        self.config = self._load_config()
        self.contract: PipelineContract = build_pipeline_contract(self.config, config_path=self.config_path)
        self.phases: dict[str, PhaseExecutable] = {}
        self.results: dict[str, PhaseResult] = {}
        self.phase_context = PhaseContext()
        self._start_time: datetime | None = None
        self._task_id: str | None = task_id
        # PERF-2: architecture_facts.json cached after extract phase completes.
        # Downstream phases can read from inputs["previous_results"]["facts"]
        # instead of re-loading the 2.8 MB file from disk.
        self._facts_cache: dict = {}
        # Token usage tracking per phase (populated after each crew/pipeline finishes)
        self._token_usage: dict[str, dict[str, int]] = {}
        # MLflow experiment tracker (no-op when MLFLOW_TRACKING_URI is not set)
        self._mlflow = MLflowTracker()

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
        self._start_time = datetime.now(timezone.utc)
        self.results.clear()
        self._facts_cache.clear()
        self._token_usage.clear()
        self.contract = self._contract_from_current_config()

        # Use the logger's RUN_ID so that phase_state.json and metrics.jsonl
        # share the same run_id (avoids mismatch in executor progress tracking).
        run_id = RUN_ID

        # Start MLflow run for this pipeline execution
        self._mlflow.start_run(run_id=run_id)

        # In parallel (per-task) mode the parent process (PipelineExecutor)
        # has already initialised phase_state.json.  Calling init_run() here
        # would wipe state written by sibling subprocesses.
        if not self._task_id:
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

        # Pre-flight connectivity check: verify APIs are reachable BEFORE starting work
        needs_llm = any(p in phases_to_run for p in ("analyze", "document", "triage", "plan"))
        needs_embedding = "discover" in phases_to_run
        preflight_errors = self._preflight_api_check(needs_llm=needs_llm, needs_embedding=needs_embedding)
        if preflight_errors:
            error_msg = "Pre-flight API check failed:\n" + "\n".join(f"  - {e}" for e in preflight_errors)
            logger.error(f"[Orchestrator] {error_msg}")
            return self._build_result("failed", error_msg)

        # Execute phases sequentially
        for phase_id in phases_to_run:
            result = self._execute_phase(phase_id)
            self.results[phase_id] = result

            # Log phase metrics to MLflow
            phase_tokens = self._token_usage.get(phase_id, {})
            self._mlflow.log_phase_metrics(
                phase_id,
                duration=result.duration_seconds,
                tokens=phase_tokens.get("total_tokens", 0),
                status=result.status,
            )

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

    def _preflight_api_check(self, *, needs_llm: bool, needs_embedding: bool) -> list[str]:
        """Check API connectivity before starting pipeline work.

        Returns list of error messages (empty = all OK).
        """
        errors: list[str] = []

        if needs_llm:
            from .shared.utils.llm_factory import check_llm_connectivity
            reachable, msg = check_llm_connectivity(timeout=8)
            if reachable:
                logger.info(f"[Pre-flight] LLM API: OK — {msg}")
            else:
                errors.append(f"LLM API unreachable: {msg}")
                logger.error(f"[Pre-flight] LLM API: FAILED — {msg}")

        if needs_embedding:
            try:
                from .shared.utils.ollama_client import OllamaClient
                client = OllamaClient()
                if client.health_check():
                    logger.info(f"[Pre-flight] Embedding API: OK — {client.base_url}")
                else:
                    errors.append(f"Embedding API unreachable at {client.base_url}")
                    logger.error(f"[Pre-flight] Embedding API: FAILED — {client.base_url}")
            except Exception as e:
                errors.append(f"Embedding API check error: {e}")
                logger.error(f"[Pre-flight] Embedding API: ERROR — {e}")

        return errors

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
        start = datetime.now(timezone.utc)
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

        # Clean stale output before re-running (preserve checkpoint files for resume).
        # In --task-id mode (parallel), only clean this task's files — not the entire dir.
        if self._task_id:
            self._reset_task_files(phase_id, self._task_id)
        else:
            self._reset_phase_output(phase_id)

        # Execute
        display = PHASES[phase_id].display_name if phase_id in PHASES else phase_id
        logger.info(f"[Phase] {display} ({phase_id})")

        log_metric("phase_start", phase_id=phase_id)
        set_phase_running(phase_id)

        try:
            executable = self.phases[phase_id]
            config = self._contract_from_current_config().phases.get(phase_id)
            phase_config = dict(config.config) if config else {}
            # Make phase_id explicit in the config so timeout/error paths can
            # report a clear identifier instead of falling back to "unknown".
            phase_config["phase_id"] = phase_id
            if self._task_id:
                phase_config["task_id"] = self._task_id

            # Build inputs (PERF-2: include cached facts if available)
            # Include both successful and partial upstream results so downstream
            # phases can adapt (graceful degradation). Partial results carry a
            # "_upstream_status" marker that downstream phases can inspect.
            previous_results: dict[str, Any] = {}
            for pid, r in self.results.items():
                if r.is_success():
                    result_output = r.output if r.output is not None else {}
                    if isinstance(result_output, dict) and r.status == "partial":
                        result_output = {**result_output, "_upstream_status": "partial"}
                    previous_results[pid] = result_output
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

            duration = (datetime.now(timezone.utc) - start).total_seconds()
            metric_status = phase_result_to_phase_state_status(phase_status)
            phase_state_status = metric_status

            # ── Token usage extraction ──
            phase_tokens = self._extract_phase_token_usage(phase_id, output)
            if phase_tokens:
                self._token_usage[phase_id] = phase_tokens
                logger.info(
                    "[Phase] %s — tokens: %s total (%s prompt, %s completion)",
                    display,
                    f"{phase_tokens.get('total_tokens', 0):,}",
                    f"{phase_tokens.get('prompt_tokens', 0):,}",
                    f"{phase_tokens.get('completion_tokens', 0):,}",
                )

            logger.info(f"[Phase] {display} — {phase_status} in {duration:.2f}s")
            log_metric(
                "phase_complete",
                phase_id=phase_id,
                duration_seconds=round(duration, 2),
                status=metric_status,
                **({f"tokens_{k}": v for k, v in phase_tokens.items()} if phase_tokens else {}),
            )
            set_phase_completed(phase_id, duration, status=phase_state_status)
            self.phase_context.metrics[phase_id] = {
                "duration_seconds": round(duration, 2),
                "status": metric_status,
                **({"token_usage": phase_tokens} if phase_tokens else {}),
            }
            self.phase_context.set_phase_result(
                phase_id=phase_id, status=phase_status, output=output, message=phase_message
            )

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
                        from .shared.schema_version import check_schema_version

                        check_schema_version(self._facts_cache, "extract")
                    except Exception as cache_err:
                        logger.warning("[Orchestrator] Could not cache facts.json: %s", cache_err)
                        self._facts_cache = {}

                # Export architecture facts to Neo4J knowledge graph (non-blocking)
                if self._facts_cache:
                    import threading

                    def _neo4j_export(facts: dict) -> None:
                        try:
                            from .shared.utils.neo4j_client import Neo4jClient

                            neo4j = Neo4jClient()
                            if neo4j.enabled:
                                neo4j.export_architecture_facts(facts)
                                neo4j.close()
                                logger.info("[Orchestrator] Neo4J export completed")
                        except Exception as neo4j_err:
                            logger.warning("[Orchestrator] Neo4J export failed (non-fatal): %s", neo4j_err)

                    threading.Thread(
                        target=_neo4j_export,
                        args=(self._facts_cache,),
                        daemon=True,
                        name="neo4j-export",
                    ).start()

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
            duration = (datetime.now(timezone.utc) - start).total_seconds()

            # ── Graceful degradation: check for partial output on disk ──
            partial_output = self._check_partial_output(phase_id)
            if partial_output:
                logger.warning(
                    "[Phase] %s — failed with partial output (%d artifacts): %s",
                    display,
                    partial_output.get("artifact_count", 0),
                    e,
                )
                log_metric(
                    "phase_partial",
                    phase_id=phase_id,
                    duration_seconds=round(duration, 2),
                    error=str(e)[:500],
                    artifact_count=partial_output.get("artifact_count", 0),
                )
                metric_status = phase_result_to_phase_state_status("partial")
                set_phase_completed(phase_id, duration, status=metric_status)
                self.phase_context.errors.append(f"{phase_id}: {e} (partial output preserved)")
                degraded_output = {"status": "partial", "phase": phase_id, "message": str(e), **partial_output}
                self.phase_context.set_phase_result(
                    phase_id=phase_id,
                    status="partial",
                    output=degraded_output,
                    message=f"Partial: {e}",
                )
                return PhaseResult(
                    phase_id=phase_id,
                    status="partial",
                    message=f"Partial: {e}",
                    output=degraded_output,
                    duration_seconds=duration,
                )

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

    def _check_partial_output(self, phase_id: str) -> dict[str, Any] | None:
        """Check if a failed phase left usable partial output on disk.

        Returns a dict with artifact info if partial output exists, else None.
        Used for graceful degradation: a phase that crashes after writing some
        files can be marked 'partial' instead of 'failed', allowing downstream
        phases to proceed with degraded input.
        """
        from .phase_registry import PHASES

        desc = PHASES.get(phase_id)
        if not desc:
            return None

        base = Path.cwd()
        primary = base / desc.primary_output
        if not primary.exists():
            return None

        # Count artifacts
        if primary.is_dir():
            artifacts = list(primary.rglob("*"))
            files = [a for a in artifacts if a.is_file() and not a.name.startswith(".checkpoint")]
            if not files:
                return None
            return {
                "artifact_count": len(files),
                "partial_output_dir": str(primary),
            }
        else:
            # Single file output — check it has content
            try:
                size = primary.stat().st_size
                if size > 0:
                    return {
                        "artifact_count": 1,
                        "partial_output_file": str(primary),
                    }
            except OSError:
                pass
            return None

    def _get_upstream_status(self, phase_id: str) -> str | None:
        """Return the status of an upstream phase, or None if not yet run.

        Downstream phases can use this to adapt their behavior:
        - 'success': full upstream output available
        - 'partial': degraded upstream output — use deterministic data only
        - 'skipped'/'failed'/None: upstream not available
        """
        result = self.results.get(phase_id)
        return result.status if result else None

    @staticmethod
    def _extract_phase_token_usage(phase_id: str, output: Any) -> dict[str, int]:
        """Extract token usage metrics from a phase's output dict.

        Crew-based phases typically include ``total_tokens``, ``prompt_tokens``,
        ``completion_tokens`` either at the top level or nested under
        ``token_usage``/``metrics``. Pipeline phases (discover, extract) may not
        report tokens at all — returns empty dict in that case.
        """
        if not isinstance(output, dict):
            return {}

        tokens: dict[str, int] = {}

        # Path 1: top-level keys (implement phase, triage)
        if "total_tokens" in output:
            tokens["total_tokens"] = int(output.get("total_tokens", 0))
            tokens["prompt_tokens"] = int(output.get("prompt_tokens", 0))
            tokens["completion_tokens"] = int(output.get("completion_tokens", 0))
            return tokens

        # Path 2: nested under "token_usage" (architecture_synthesis base_crew pattern)
        usage = output.get("token_usage")
        if isinstance(usage, dict):
            tokens["total_tokens"] = int(usage.get("total_tokens", 0))
            tokens["prompt_tokens"] = int(usage.get("prompt_tokens", 0))
            tokens["completion_tokens"] = int(usage.get("completion_tokens", 0))
            return tokens

        # Path 3: nested under "metrics" (some phases embed it there)
        metrics = output.get("metrics")
        if isinstance(metrics, dict) and "total_tokens" in metrics:
            tokens["total_tokens"] = int(metrics.get("total_tokens", 0))
            tokens["prompt_tokens"] = int(metrics.get("prompt_tokens", 0))
            tokens["completion_tokens"] = int(metrics.get("completion_tokens", 0))
            return tokens

        return {}

    def _log_token_summary(self) -> None:
        """Log a summary of token usage across all phases at the end of a pipeline run."""
        if not self._token_usage:
            return

        logger.info("")
        logger.info("=" * 60)
        logger.info("[Orchestrator] TOKEN USAGE SUMMARY")
        logger.info("=" * 60)

        grand_total = 0
        grand_prompt = 0
        grand_completion = 0

        for pid, tokens in self._token_usage.items():
            total = tokens.get("total_tokens", 0)
            prompt = tokens.get("prompt_tokens", 0)
            completion = tokens.get("completion_tokens", 0)
            grand_total += total
            grand_prompt += prompt
            grand_completion += completion
            logger.info(
                "  %-15s %10s total  (%s prompt, %s completion)",
                pid,
                f"{total:,}",
                f"{prompt:,}",
                f"{completion:,}",
            )

        logger.info("-" * 60)
        logger.info(
            "  %-15s %10s total  (%s prompt, %s completion)",
            "TOTAL",
            f"{grand_total:,}",
            f"{grand_prompt:,}",
            f"{grand_completion:,}",
        )
        logger.info("=" * 60)

        log_metric(
            "pipeline_token_summary",
            total_tokens=grand_total,
            prompt_tokens=grand_prompt,
            completion_tokens=grand_completion,
            per_phase=self._token_usage,
        )

    def _reset_phase_output(self, phase_id: str) -> None:
        """Clean stale output files before re-running a phase.

        Two modes:
        - **Resume mode** (checkpoint files exist): Skip reset entirely.
          The crew's checkpoint logic will skip completed mini-crews and
          only re-run failed ones. Output files are needed for merging.
        - **Fresh mode** (no checkpoints): Delete all output files so the
          phase starts from a clean state. No stale stubs persist.

        Skips non-resettable phases (e.g., discover — manages own INDEX_MODE).
        """
        import shutil

        desc = PHASES.get(phase_id)
        if desc and not desc.resettable:
            return

        base = Path.cwd()
        for rel in get_cleanup_targets(phase_id):
            target = base / rel
            if not target.exists():
                continue
            if target.is_dir():
                # If checkpoint files exist, this is a resume — don't touch output
                checkpoints = list(target.glob(".checkpoint_*"))
                if checkpoints:
                    logger.info(
                        f"[Orchestrator] Skipping reset of {rel}/ — "
                        f"{len(checkpoints)} checkpoint(s) found (resume mode)"
                    )
                    continue
                shutil.rmtree(target)
                logger.info(f"[Orchestrator] Reset {rel}/")
            else:
                target.unlink()
                logger.info(f"[Orchestrator] Deleted {rel}")

    def _reset_task_files(self, phase_id: str, task_id: str) -> None:
        """Clean only this task's output files — safe for parallel execution.

        Instead of deleting the entire phase output directory (which would
        destroy other tasks' files running in parallel), only removes files
        matching ``{task_id}_*`` in the phase output directory.
        """
        base = Path.cwd()
        for rel in get_cleanup_targets(phase_id):
            target = base / rel
            if not target.exists() or not target.is_dir():
                continue
            # Ensure the dir and logs subdir exist (parallel tasks share them)
            (target / "logs").mkdir(parents=True, exist_ok=True)
            # Delete only this task's files
            for f in target.glob(f"{task_id}_*"):
                f.unlink()
                logger.info("[Orchestrator] Deleted %s (task-id=%s)", f.name, task_id)

    def _invoke_executable(self, executable: PhaseExecutable, inputs: dict[str, Any]) -> Any:
        """Invoke phase with a wall-clock timeout (ARCH-6).

        Uses a thread-based timeout that is compatible with Windows (no SIGALRM).
        If the phase exceeds _PHASE_TIMEOUT_S seconds, TimeoutError is raised and
        the orchestrator records a failure — the background thread may continue
        running until the process exits (acceptable; Gradle/LLM timeouts are a
        separate concern handled by their own subprocess kill logic).
        """
        pool = _cf.ThreadPoolExecutor(max_workers=1)
        future = pool.submit(executable.kickoff, inputs)
        try:
            return future.result(timeout=_PHASE_TIMEOUT_S)
        except _cf.TimeoutError:
            pool.shutdown(wait=False, cancel_futures=True)
            phase_id = inputs.get("config", {}).get("phase_id", "unknown")
            logger.error(
                "[Orchestrator] Phase '%s' timed out after %ds. Set PHASE_TIMEOUT_SECONDS env var to increase.",
                phase_id,
                _PHASE_TIMEOUT_S,
            )
            raise TimeoutError(
                f"Phase '{phase_id}' timed out after {_PHASE_TIMEOUT_S}s. "
                f"Set PHASE_TIMEOUT_SECONDS env var to increase."
            )
        finally:
            pool.shutdown(wait=False)

    def _check_dependencies(self, phase_id: str) -> bool:
        """Check if phase dependencies are satisfied (existence + validation).

        Delegates to DependencyChecker which also performs ARCH-5 contract
        validation: logs a warning if required phase outputs are absent
        (observational only — blocking is handled by the existing dependency
        system above).
        """
        from .shared.dependency_checker import DependencyChecker

        return DependencyChecker(self._contract_from_current_config(), self.results).check(phase_id)

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
            delta = datetime.now(timezone.utc) - self._start_time
            total_duration = str(delta).split(".")[0]  # Remove microseconds
            total_seconds = delta.total_seconds()

        run_outcome = self._compute_run_outcome()

        # Log token usage summary before final status
        self._log_token_summary()

        # End MLflow run and log key artifacts
        self._mlflow.log_artifact("knowledge/extract/architecture_facts.json")
        self._mlflow.end_run(outcome=run_outcome)

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
        """Auto-commit knowledge/ after successful phase.

        Delegates to PhaseGitHandler which guards with CODEGEN_COMMIT_KNOWLEDGE
        (default: true). Set CODEGEN_COMMIT_KNOWLEDGE=false to disable auto-commits
        (useful when knowledge/ is in .gitignore or without a clean git state).

        Args:
            phase_id: The completed phase ID.

        Returns:
            True if commit successful, False otherwise.
        """
        from .shared.phase_git_handler import PhaseGitHandler

        return PhaseGitHandler().commit_knowledge(phase_id)
