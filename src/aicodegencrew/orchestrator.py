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

import yaml
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Protocol
from datetime import datetime
from dataclasses import dataclass, field

from .shared.utils.logger import logger, log_metric


# =============================================================================
# PROTOCOLS (Interfaces)
# =============================================================================

class PhaseExecutable(Protocol):
    """Interface for executable phases (Pipeline or Crew)."""
    
    def kickoff(self, inputs: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute the phase and return results."""
        ...


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class PhaseResult:
    """Result of a single phase execution."""
    phase_id: str
    status: str  # 'success', 'failed', 'skipped'
    message: str = ""
    output: Any = None
    duration_seconds: float = 0.0
    
    def is_success(self) -> bool:
        return self.status == "success"
    
    def to_dict(self) -> Dict[str, Any]:
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
    phases: List[PhaseResult] = field(default_factory=list)
    total_duration: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "message": self.message,
            "phases": [p.to_dict() for p in self.phases],
            "total_duration": self.total_duration,
        }


# =============================================================================
# ORCHESTRATOR
# =============================================================================

class SDLCOrchestrator:
    """
    Orchestrates SDLC phase execution.
    
    Usage:
        orchestrator = SDLCOrchestrator()
        orchestrator.register("phase0_indexing", IndexingPipeline(...))
        orchestrator.register("phase1_architecture_facts", ArchFactsPipeline(...))
        orchestrator.register("phase2_architecture_synthesis", SynthesisCrew(...))
        
        result = orchestrator.run(preset="architecture_workflow")
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize with optional config path."""
        self.config_path = config_path or self._default_config_path()
        self.config = self._load_config()
        self.phases: Dict[str, PhaseExecutable] = {}
        self.results: Dict[str, PhaseResult] = {}
        self._start_time: Optional[datetime] = None
        
        logger.info(f"[Orchestrator] Initialized")
    
    # -------------------------------------------------------------------------
    # PUBLIC API
    # -------------------------------------------------------------------------
    
    def register(self, phase_id: str, executable: PhaseExecutable) -> "SDLCOrchestrator":
        """
        Register a phase for execution.
        
        Args:
            phase_id: Unique phase identifier (e.g., "phase0_indexing")
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
        self, 
        preset: Optional[str] = None, 
        phases: Optional[List[str]] = None,
        stop_on_error: bool = True
    ) -> PipelineResult:
        """
        Execute the SDLC pipeline.
        
        Args:
            preset: Named preset from config (e.g., "architecture_workflow")
            phases: Explicit list of phases to run (overrides preset)
            stop_on_error: Stop execution on first failure
            
        Returns:
            PipelineResult with status and phase details
        """
        self._start_time = datetime.now()
        self.results.clear()
        
        # Determine phases to run
        phases_to_run = self._resolve_phases(preset, phases)
        
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
    
    def get_presets(self) -> List[str]:
        """Get available preset names."""
        return list(self.config.get("presets", {}).keys())
    
    def get_phase_config(self, phase_id: str) -> Dict[str, Any]:
        """Get configuration for a specific phase."""
        return self.config.get("phases", {}).get(phase_id, {})
    
    def is_phase_enabled(self, phase_id: str) -> bool:
        """Check if a phase is enabled in configuration."""
        return self.get_phase_config(phase_id).get("enabled", False)
    
    def get_enabled_phases(self) -> List[str]:
        """Get enabled phases sorted by order."""
        return self._get_enabled_phases()
    
    def get_preset_phases(self, preset_name: str) -> List[str]:
        """Get phases for a preset execution mode."""
        return self.config.get("presets", {}).get(preset_name, [])
    
    # -------------------------------------------------------------------------
    # CONTEXT (Backward Compatibility)
    # -------------------------------------------------------------------------
    
    @property
    def context(self) -> Dict[str, Any]:
        """Backward compatibility: return context-like structure."""
        return {
            "phases": {
                pid: {"status": r.status, "output": r.output}
                for pid, r in self.results.items()
            },
            "knowledge": {},
            "shared": {},
        }
    
    # -------------------------------------------------------------------------
    # PRIVATE METHODS
    # -------------------------------------------------------------------------
    
    def _resolve_phases(
        self, 
        preset: Optional[str], 
        explicit_phases: Optional[List[str]]
    ) -> List[str]:
        """Resolve which phases to run."""
        if explicit_phases:
            phases = explicit_phases
        elif preset:
            phases = self.config.get("presets", {}).get(preset, [])
            if not phases:
                logger.warning(f"[Orchestrator] Unknown preset: {preset}")
        else:
            # Default: return enabled phases in order
            phases = self._get_enabled_phases()
        
        # Filter out unregistered phases (e.g., phase0 when INDEX_MODE=off)
        filtered = []
        for phase_id in phases:
            if phase_id in self.phases:
                filtered.append(phase_id)
            else:
                logger.info(f"[Orchestrator] Skipping unregistered phase: {phase_id}")
        
        return filtered
    
    def _get_enabled_phases(self) -> List[str]:
        """Get enabled phases sorted by order."""
        phases_config = self.config.get("phases", {})
        enabled = [
            (cfg.get("order", 999), pid)
            for pid, cfg in phases_config.items()
            if cfg.get("enabled", False)
        ]
        enabled.sort(key=lambda x: x[0])
        return [pid for _, pid in enabled]
    
    def _execute_phase(self, phase_id: str) -> PhaseResult:
        """Execute a single phase."""
        start = datetime.now()
        
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
        
        # Archive knowledge before starting (for rollback capability)
        if phase_id.startswith("phase1") or phase_id.startswith("phase2") or phase_id.startswith("phase3"):
            self.archive_knowledge(label=f"before_{phase_id}")
        
        # Execute
        logger.info(f"\n{'=' * 60}")
        logger.info(f"[Phase] {phase_id} - Starting")
        logger.info(f"{'=' * 60}")
        
        log_metric("phase_start", phase_id=phase_id)

        try:
            executable = self.phases[phase_id]
            config = self.get_phase_config(phase_id).get("config", {})
            
            # Build inputs
            inputs = {
                "config": config,
                "previous_results": {
                    pid: r.output for pid, r in self.results.items() if r.is_success()
                },
            }
            
            # Handle different execution styles
            output = self._invoke_executable(executable, inputs)
            
            duration = (datetime.now() - start).total_seconds()
            
            logger.info(f"[Phase] {phase_id} - Completed in {duration:.2f}s")
            log_metric("phase_complete", phase_id=phase_id, duration_seconds=round(duration, 2), status="success")

            # Auto-commit after successful phase
            self._git_commit_after_phase(phase_id)
            
            return PhaseResult(
                phase_id=phase_id,
                status="success",
                message="Completed",
                output=output,
                duration_seconds=duration,
            )
            
        except Exception as e:
            duration = (datetime.now() - start).total_seconds()
            logger.error(f"[Phase] {phase_id} - Failed: {e}", exc_info=True)
            log_metric("phase_failed", phase_id=phase_id, duration_seconds=round(duration, 2), error=str(e)[:500])

            return PhaseResult(
                phase_id=phase_id,
                status="failed",
                message=str(e),
                duration_seconds=duration,
            )
    
    def _invoke_executable(self, executable: PhaseExecutable, inputs: Dict[str, Any]) -> Any:
        """
        Invoke an executable (Pipeline or Crew).
        
        Handles different execution patterns:
        1. Crew with run() method
        2. CrewBase with crew() method
        3. Pipeline with kickoff() method
        """
        # Add summaries if available (for Crews)
        if hasattr(executable, "summaries") and isinstance(executable.summaries, dict):
            inputs.update(executable.summaries)
        
        # Style 1: Crew with run() method (ArchitectureSynthesisCrew)
        if hasattr(executable, "run") and callable(executable.run):
            return executable.run()
        
        # Style 2: CrewBase with crew() factory method
        if hasattr(executable, "crew") and callable(executable.crew):
            crew = executable.crew()
            result = crew.kickoff(inputs=inputs)
            # Normalize CrewOutput
            if hasattr(result, "raw"):
                return {"raw": result.raw, "status": "success"}
            return result
        
        # Style 3: Pipeline with kickoff() method
        if hasattr(executable, "kickoff"):
            return executable.kickoff(inputs)
        
        raise ValueError(f"Unknown executable type: {type(executable)}")
    
    def _check_dependencies(self, phase_id: str) -> bool:
        """Check if phase dependencies are satisfied (existence + validation)."""
        from .shared.validation import PhaseOutputValidator

        phase_config = self.get_phase_config(phase_id)
        dependencies = phase_config.get("dependencies", [])

        validator = PhaseOutputValidator()

        for dep in dependencies:
            # Check if ran successfully in this session
            if dep in self.results and self.results[dep].is_success():
                continue

            # Check if output files exist from previous run
            if self._outputs_exist(dep):
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

        return True
    
    def _outputs_exist(self, phase_id: str) -> bool:
        """Check if phase outputs exist from previous run."""
        output_files = {
            "phase0_indexing": [".cache/.chroma"],
            "phase1_architecture_facts": [
                "knowledge/architecture/architecture_facts.json",
                "knowledge/architecture/evidence_map.json",
            ],
            "phase2_architecture_analysis": [
                "knowledge/architecture/analyzed_architecture.json",
            ],
            "phase3_architecture_synthesis": [
                "knowledge/architecture/c4/c4-context.md",
            ],
        }
        
        expected = output_files.get(phase_id, [])
        if not expected:
            return False
        return all(Path(f).exists() for f in expected)
    
    def _build_result(self, status: str, message: str) -> PipelineResult:
        """Build final pipeline result."""
        total_duration = ""
        total_seconds = 0.0
        if self._start_time:
            delta = datetime.now() - self._start_time
            total_duration = str(delta).split(".")[0]  # Remove microseconds
            total_seconds = delta.total_seconds()

        logger.info("=" * 60)
        logger.info(f"[Orchestrator] Pipeline {status.upper()}: {message}")
        logger.info(f"[Orchestrator] Duration: {total_duration}")
        logger.info("=" * 60)

        log_metric(
            "pipeline_complete",
            status=status,
            total_duration=round(total_seconds, 2),
            phases_run=len(self.results),
            phases_succeeded=sum(1 for r in self.results.values() if r.is_success()),
        )

        return PipelineResult(
            status=status,
            message=message,
            phases=list(self.results.values()),
            total_duration=total_duration,
        )
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            logger.warning(f"[Orchestrator] Config not found: {self.config_path}")
            return self._default_config()
        except Exception as e:
            logger.error(f"[Orchestrator] Config load error: {e}")
            return self._default_config()
    
    def _default_config_path(self) -> str:
        """Get default config path."""
        return str(Path(__file__).parent.parent.parent / "config" / "phases_config.yaml")
    
    def _default_config(self) -> Dict[str, Any]:
        """Return minimal default config."""
        return {
            "phases": {
                "phase0_indexing": {"enabled": True, "order": 0},
            },
            "presets": {
                "indexing_only": ["phase0_indexing"],
            },
        }
    
    # -------------------------------------------------------------------------
    # ARCHIVE & GIT OPERATIONS
    # -------------------------------------------------------------------------
    
    def archive_knowledge(self, label: str = "manual") -> Path:
        """
        Archive the entire knowledge/ directory as knowledge-{timestamp}/.
        
        Args:
            label: Label for the archive (e.g., 'manual', 'phase1', 'phase2')
            
        Returns:
            Path to the archive directory
        """
        knowledge_dir = Path("knowledge")
        if not knowledge_dir.exists():
            logger.warning("[Orchestrator] knowledge/ directory does not exist")
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_dir = Path(f"knowledge-{timestamp}")
        
        # Copy entire knowledge directory
        shutil.copytree(knowledge_dir, archive_dir, dirs_exist_ok=True)
        
        logger.info(f"[Orchestrator] Knowledge archived to: {archive_dir}")
        return archive_dir
    
    def _git_commit_after_phase(self, phase_id: str) -> bool:
        """
        Auto-commit knowledge/ after successful phase.
        
        Args:
            phase_id: The completed phase ID
            
        Returns:
            True if commit successful, False otherwise
        """
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
