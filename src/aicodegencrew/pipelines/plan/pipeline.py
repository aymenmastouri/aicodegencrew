"""
Development Planning Pipeline (Phase 4)

HYBRID ARCHITECTURE:
- Stages 1-3: Deterministic (parsing, RAG, pattern matching)
- Stage 4: LLM (plan generation)
- Stage 5: Deterministic (validation)

Total Duration: 18-40 seconds
LLM Calls: 1 (only in Stage 4)
Success Rate: 95%+ (deterministic stages don't fail)
"""

import json
import os
import time
from pathlib import Path
from typing import Any

from ...shared.utils.logger import log_metric, setup_logger, step_done, step_fail, step_start
from .schemas import ImplementationPlan, TaskInput
from .stages import (
    ComponentDiscoveryStage,
    InputParserStage,
    PatternMatcherStage,
    PlanGeneratorStage,
    ValidatorStage,
)

logger = setup_logger(__name__)


class PlanPipeline:
    """
    Phase 4: Plan Pipeline.

    Hybrid architecture with 5 stages:
    1. Input Parser (deterministic)
    2. Component Discovery (RAG + scoring)
    3. Pattern Matcher (TF-IDF + rules)
    4. Plan Generator (LLM)
    5. Validator (Pydantic)
    """

    # JIRA priority ordering (lower = higher priority)
    # Covers both classic JIRA (Blocker..Trivial) and simplified (Highest..Lowest)
    PRIORITY_ORDER = {
        "Blocker": 1,
        "Highest": 1,
        "Critical": 2,
        "High": 2,
        "Major": 3,
        "Medium": 3,
        "Minor": 4,
        "Low": 4,
        "Trivial": 5,
        "Lowest": 5,
    }
    # Task type ordering for sorting
    TASK_TYPE_ORDER = {
        "upgrade": 1,
        "bugfix": 2,
        "feature": 3,
        "refactoring": 4,
    }

    def __init__(
        self,
        input_file: str = None,
        input_files: list[str] = None,
        facts_path: str = "knowledge/extract/architecture_facts.json",
        analyzed_path: str = "knowledge/analyze/analyzed_architecture.json",
        output_dir: str = "knowledge/plan",
        chroma_dir: str = None,
        repo_path: str = None,
        supplementary_files: dict[str, list[str]] = None,
    ):
        """
        Initialize development planning pipeline.

        Args:
            input_file: Single task input file (backward-compatible)
            input_files: List of task input files (multi-file mode)
            facts_path: Path to architecture_facts.json (Phase 1)
            analyzed_path: Path to analyzed_architecture.json (Phase 2)
            output_dir: Output directory for plans
            chroma_dir: Discover directory (Phase 0, legacy param name)
            repo_path: Target repository path (for upgrade code scanning)
            supplementary_files: Additional context files by category
                {"requirements": [...], "logs": [...], "reference": [...]}
        """
        # Support both single file and multi-file
        if input_files:
            self.input_files = [str(f) for f in input_files]
        elif input_file:
            self.input_files = [str(input_file)]
        else:
            raise ValueError("Either input_file or input_files must be provided")

        # Backward-compatible: first file
        self.input_file = self.input_files[0]

        self.facts_path = Path(facts_path)
        self.analyzed_path = Path(analyzed_path)
        self.output_dir = Path(output_dir)
        self.chroma_dir = chroma_dir
        self.repo_path = repo_path
        self.supplementary_files = supplementary_files or {}

        # Ensure output dir exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Defer data loading to run() so earlier phases can produce files first
        self.facts: dict = {}
        self.analyzed_architecture: dict = {}
        self.supplementary_context: dict[str, str] = {}
        self._stages_initialized = False

    # ── Cascade checkpoint helpers ────────────────────────────────────────────

    @staticmethod
    def _checkpoint_path() -> Path:
        return Path("knowledge/plan/.checkpoint_plan.json")

    def _load_plan_checkpoint(self) -> set[str]:
        """Load task IDs already planned from checkpoint file."""
        p = self._checkpoint_path()
        if not p.exists():
            return set()
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return set(data.get("completed", []))
        except Exception as exc:
            logger.warning("[Phase4] Plan checkpoint load failed (%s): %s — resuming fresh", p, exc)
            return set()

    def _save_plan_checkpoint(self, task_id: str, completed: set[str]) -> None:
        """Persist completed task ID to plan checkpoint file."""
        completed.add(task_id)
        p = self._checkpoint_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps({"completed": sorted(completed)}, indent=2),
            encoding="utf-8",
        )

    def _load_triage_from_disk(self) -> dict:
        """Disk fallback: load triage_context from knowledge/triage/{task_id}_triage.json.

        Used when plan runs in a separate subprocess without in-memory triage
        results (e.g. parallel mode where triage and plan are triggered separately).

        For single-task mode, returns the one matching context dict.
        For multi-task mode, returns the FIRST found context dict (caller
        uses _per_task_triage map built in _run_multi for per-task matching).
        """
        triage_dir = self.output_dir.parent / "triage"
        if not triage_dir.is_dir():
            return {}

        # Determine which task IDs we need triage for
        task_stems = {Path(f).stem for f in self.input_files}
        first_ctx: dict = {}

        for stem in sorted(task_stems):
            triage_file = triage_dir / f"{stem}_triage.json"
            if triage_file.exists():
                try:
                    data = json.loads(triage_file.read_text(encoding="utf-8"))
                    developer = data.get("developer_context", {})
                    classification = data.get("classification", {})
                    ctx = {
                        "issue_id": stem,
                        "classification_type": classification.get("type", "unknown"),
                        "classification_confidence": classification.get("confidence", 0),
                        "big_picture": developer.get("big_picture", ""),
                        "scope_boundary": developer.get("scope_boundary", ""),
                        "classification_assessment": developer.get("classification_assessment", ""),
                        "affected_components": developer.get("affected_components", []),
                        "context_boundaries": developer.get("context_boundaries", []),
                        "architecture_notes": developer.get("architecture_notes", ""),
                        "anticipated_questions": developer.get("anticipated_questions", []),
                    }
                    logger.info(
                        "[Phase4] Loaded triage_context from disk for %s: classification=%s",
                        stem,
                        ctx.get("classification_type"),
                    )
                    if not first_ctx:
                        first_ctx = ctx
                except Exception as exc:
                    logger.warning("[Phase4] Failed to read triage file %s: %s", triage_file, exc)

        if not first_ctx:
            logger.info("[Phase4] No triage files found on disk for task(s): %s", sorted(task_stems))
        return first_ctx

    def _wait_for_triage_then_load(self) -> dict:
        """Wait for triage results to appear on disk, then load them.

        When triage and plan run in parallel (e.g. orchestrated by different
        workers), triage may not have finished writing its output yet.  This
        method polls for triage files with a configurable timeout before
        falling back to deterministic-only data.

        Timeout is controlled by the PLAN_TRIAGE_WAIT_TIMEOUT env var
        (default: 120 seconds).  A value of 0 disables waiting entirely.
        """
        timeout = int(os.environ.get("PLAN_TRIAGE_WAIT_TIMEOUT", "120"))
        if timeout <= 0:
            return self._load_triage_from_disk()

        triage_dir = self.output_dir.parent / "triage"
        task_stems = {Path(f).stem for f in self.input_files}
        poll_interval = 2  # seconds

        elapsed = 0.0
        while elapsed < timeout:
            # Quick check: do any triage files exist for our tasks?
            if triage_dir.is_dir():
                found_any = any(
                    (triage_dir / f"{stem}_triage.json").exists()
                    for stem in task_stems
                )
                if found_any:
                    ctx = self._load_triage_from_disk()
                    if ctx:
                        return ctx

            time.sleep(poll_interval)
            elapsed += poll_interval

        logger.warning(
            "[Phase4] Triage wait timed out after %ds — proceeding with deterministic-only data "
            "(no triage context). Set PLAN_TRIAGE_WAIT_TIMEOUT=0 to disable waiting.",
            timeout,
        )
        return {}

    # Triage classification → Plan task_type mapping
    _TRIAGE_TO_PLAN_TYPE: dict[str, str] = {
        "bug": "bugfix",
        "feature": "feature",
        "refactor": "refactoring",
        "upgrade": "upgrade",
        "investigation": "feature",  # no direct equivalent
    }

    def kickoff(self, inputs: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Execute pipeline (Orchestrator-compatible interface).

        Args:
            inputs: Optional inputs from orchestrator. Reads
                    previous_results["analyze"] for quality hints and
                    previous_results["triage"] for classification + context.

        Returns:
            Dict with status, output_files, metrics
        """
        inputs = inputs or {}
        previous = inputs.get("previous_results", {})
        analyze_out = previous.get("analyze", {})
        quality_hints: dict = {}
        if isinstance(analyze_out, dict):
            quality_hints = {
                "architecture_quality": analyze_out.get("architecture_quality", {}),
                "critical_issues": analyze_out.get("critical_issues", []),
            }
        if quality_hints.get("architecture_quality") or quality_hints.get("critical_issues"):
            logger.info(
                "[Phase4] Received quality_hints from analyze phase: architecture_quality=%s, critical_issues=%d",
                bool(quality_hints.get("architecture_quality")),
                len(quality_hints.get("critical_issues", [])),
            )

        # Read triage context (classification, scope, boundaries)
        triage_out = previous.get("triage", {})
        triage_context: dict = {}
        if isinstance(triage_out, dict):
            triage_context = dict(triage_out.get("triage_context", {}))
            if triage_context:
                # Check if triage LLM failed — context will be incomplete
                triage_llm_status = triage_context.get("llm_status", "unknown")
                if triage_llm_status == "failed":
                    logger.warning(
                        "[Phase4] Triage LLM synthesis FAILED — developer_context is empty. "
                        "Plan will proceed with deterministic classification only. "
                        "Error: %s",
                        triage_context.get("llm_error", "unknown"),
                    )
                # Carry issue_id from summary level into triage_context
                triage_context.setdefault("issue_id", triage_out.get("issue_id", ""))
                logger.info(
                    "[Phase4] Received triage_context: classification=%s, llm_status=%s, components=%d, boundaries=%d",
                    triage_context.get("classification_type"),
                    triage_llm_status,
                    len(triage_context.get("affected_components", [])),
                    len(triage_context.get("context_boundaries", [])),
                )

        # Disk fallback: when plan runs in a separate subprocess (no in-memory
        # triage result), load triage_context from knowledge/triage/{task_id}_triage.json.
        if not triage_context:
            triage_context = self._wait_for_triage_then_load()

        return self.run(quality_hints=quality_hints, triage_context=triage_context)

    def _ensure_stages(self) -> None:
        """Load data and create stages on first run (deferred from __init__)."""
        if self._stages_initialized:
            return
        self.facts = self._load_json(self.facts_path)
        self.analyzed_architecture = self._load_json(self.analyzed_path)
        self.supplementary_context = self._load_supplementary_context()
        self.stage1 = InputParserStage()
        self.stage2 = ComponentDiscoveryStage(
            facts=self.facts,
            chroma_dir=self.chroma_dir,
        )
        self.stage3 = PatternMatcherStage(facts=self.facts, repo_path=self.repo_path)
        self.stage4 = PlanGeneratorStage(
            analyzed_architecture=self.analyzed_architecture,
            supplementary_context=self.supplementary_context,
            extract_facts=self.facts,
        )
        self.stage5 = ValidatorStage(analyzed_architecture=self.analyzed_architecture)
        self._stages_initialized = True

    def run(self, quality_hints: dict | None = None, triage_context: dict | None = None) -> dict[str, Any]:
        """
        Run pipeline for all input files.

        Single file: run directly.
        Multiple files: parse all (Stage 1), sort by priority, process each sequentially.

        Args:
            quality_hints: Optional quality context from analyze phase
                (architecture_quality, critical_issues). Stored in
                self._quality_hints for potential use by sub-stages.
            triage_context: Optional triage context with classification,
                scope_boundary, and context_boundaries from triage phase.

        Returns:
            Dict with status, output_files, duration, metrics, results
        """
        self._quality_hints = quality_hints or {}
        self._triage_context = triage_context or {}
        self._ensure_stages()
        if len(self.input_files) == 1:
            result = self._run_single(self.input_files[0])
            return {
                "status": "completed",
                "phase": "plan",
                "task_id": result["task_id"],
                "output_file": result["output_file"],
                "output_files": [result["output_file"]],
                "duration_seconds": result["duration_seconds"],
                "metrics": result["metrics"],
                "results": [result],
            }

        return self._run_multi()

    def _run_multi(self) -> dict[str, Any]:
        """Process multiple input files with content-based sorting."""
        start_time = time.time()
        n = len(self.input_files)

        logger.info("=" * 80)
        logger.info(f"[Phase4] Multi-file mode: {n} input files")
        logger.info("=" * 80)

        # Step 1: Parse all files with Stage 1 (fast, <1s each)
        step_start(f"Stage 1: Parsing {n} input files")
        parsed_tasks: list[TaskInput] = []
        for f in self.input_files:
            try:
                task = self.stage1.run(f)
                parsed_tasks.append(task)
            except Exception as e:
                logger.warning(f"[Phase4] Skipping {f}: {e}")
        step_done(f"Stage 1: Parsed {len(parsed_tasks)}/{n} files")

        if not parsed_tasks:
            raise ValueError("No input files could be parsed")

        # Apply triage classification override (match by issue_id).
        # ALWAYS build per-task triage map so _run_stages_2_to_5 can pick the
        # correct context per task. Global _triage_context is only used for
        # single-task mode; multi-task always uses per-task map.
        self._per_task_triage: dict[str, dict] = {}

        # Seed from global triage_context if it has a matching issue_id
        if self._triage_context:
            triage_issue_id = self._triage_context.get("issue_id", "")
            if triage_issue_id:
                self._per_task_triage[triage_issue_id] = self._triage_context
                for task in parsed_tasks:
                    if task.task_id == triage_issue_id:
                        self._apply_triage_classification(task)

        # Disk fallback: load triage for any tasks missing from the map
        triage_dir = self.output_dir.parent / "triage"
        if triage_dir.is_dir():
            for task in parsed_tasks:
                if task.task_id in self._per_task_triage:
                    continue  # Already have in-memory context for this task
                triage_file = triage_dir / f"{task.task_id}_triage.json"
                if triage_file.exists():
                    try:
                        data = json.loads(triage_file.read_text(encoding="utf-8"))
                        developer = data.get("developer_context", {})
                        classification = data.get("classification", {})
                        ctx = {
                            "issue_id": task.task_id,
                            "classification_type": classification.get("type", "unknown"),
                            "classification_confidence": classification.get("confidence", 0),
                            "big_picture": developer.get("big_picture", ""),
                            "scope_boundary": developer.get("scope_boundary", ""),
                            "classification_assessment": developer.get("classification_assessment", ""),
                            "affected_components": developer.get("affected_components", []),
                            "context_boundaries": developer.get("context_boundaries", []),
                            "architecture_notes": developer.get("architecture_notes", ""),
                            "anticipated_questions": developer.get("anticipated_questions", []),
                        }
                        self._per_task_triage[task.task_id] = ctx
                        self._apply_triage_classification_from_ctx(task, ctx)
                        logger.info("[Phase4] Loaded triage from disk for %s", task.task_id)
                    except Exception as exc:
                        logger.warning("[Phase4] Failed to read triage for %s: %s", task.task_id, exc)

        # Step 2: Sort by content (priority, task_type, dependencies)
        sorted_tasks = self._sort_tasks(parsed_tasks)

        logger.info("[Phase4] Processing order:")
        for i, task in enumerate(sorted_tasks, 1):
            logger.info(f"  {i}. {task.task_id} [{task.priority}] type={task.task_type} links={task.linked_tasks}")

        # Step 3: Process each task sequentially (Stages 2-5) with checkpoint resume
        results = []
        succeeded = 0
        failed = 0

        # R7: Load cascade checkpoint — skip already-planned tasks on resume
        cascade_completed = self._load_plan_checkpoint()
        if cascade_completed:
            logger.info(
                "[Phase4] Plan checkpoint: %d task(s) already done: %s",
                len(cascade_completed),
                sorted(cascade_completed),
            )

        for i, task in enumerate(sorted_tasks, 1):
            logger.info(f"\n[Phase4] === Task {i}/{len(sorted_tasks)}: {task.task_id} ===")

            # R7: Skip tasks already completed in a prior run — but only if
            # the output file still exists on disk (guards against stale checkpoint
            # after per-task reset deleted the output).
            if task.task_id in cascade_completed:
                output_file = str(self.output_dir / f"{task.task_id}_plan.json")
                if Path(output_file).exists():
                    logger.info(f"[Phase4] Skipping {task.task_id} (plan checkpoint)")
                    results.append({"status": "skipped", "task_id": task.task_id, "output_file": output_file})
                    succeeded += 1
                    continue
                else:
                    logger.warning(
                        "[Phase4] Checkpoint says %s is done but output file missing — re-planning",
                        task.task_id,
                    )
                    cascade_completed.discard(task.task_id)

            try:
                result = self._run_stages_2_to_5(task)
                results.append(result)
                succeeded += 1
                # R7: Persist checkpoint after successful plan generation
                self._save_plan_checkpoint(task.task_id, cascade_completed)
            except Exception as e:
                logger.error(f"[Phase4] Task {task.task_id} failed: {e}")
                results.append(
                    {
                        "status": "failed",
                        "task_id": task.task_id,
                        "error": str(e),
                    }
                )
                failed += 1

        total_duration = time.time() - start_time

        logger.info("=" * 80)
        logger.info(f"[Phase4] Multi-file complete: {succeeded} succeeded, {failed} failed")
        logger.info(f"[Phase4] Total Duration: {total_duration:.2f}s")
        logger.info("=" * 80)

        log_metric(
            "phase_complete",
            phase="plan",
            status="success" if failed == 0 else "partial",
            duration_seconds=total_duration,
            tasks_total=len(sorted_tasks),
            tasks_succeeded=succeeded,
            tasks_failed=failed,
        )

        output_files = [r["output_file"] for r in results if r.get("output_file")]

        return {
            "status": "completed" if failed == 0 else "partial",
            "phase": "plan",
            "output_files": output_files,
            "duration_seconds": total_duration,
            "results": results,
            "metrics": {
                "tasks_total": len(sorted_tasks),
                "tasks_succeeded": succeeded,
                "tasks_failed": failed,
            },
        }

    def _sort_tasks(self, tasks: list[TaskInput]) -> list[TaskInput]:
        """Sort tasks by dependency order (topological), then priority and type.

        Uses Kahn's algorithm for topological sort with cycle detection.
        Tasks in cycles are logged as warnings and sorted by priority fallback.
        """
        task_map = {t.task_id: t for t in tasks}
        batch_ids = set(task_map.keys())

        # Build adjacency: parent → children.
        # A task that links to another task in the batch is a child/subtask.
        # Edge: linked_id → task_id (parent must come before child).
        in_degree: dict[str, int] = {tid: 0 for tid in batch_ids}
        children: dict[str, list[str]] = {tid: [] for tid in batch_ids}

        for t in tasks:
            for link in t.linked_tasks:
                if link in batch_ids:
                    # link is the parent, t is the child
                    children[link].append(t.task_id)
                    in_degree[t.task_id] += 1

        # Kahn's algorithm: process nodes with in_degree 0
        # Among candidates, sort by priority + type for deterministic ordering
        def _priority_key(tid: str):
            t = task_map[tid]
            return (
                self.PRIORITY_ORDER.get(t.priority, 3),
                self.TASK_TYPE_ORDER.get(t.task_type, 3),
                tid,
            )

        queue = sorted(
            [tid for tid, deg in in_degree.items() if deg == 0],
            key=_priority_key,
        )
        ordered: list[str] = []

        while queue:
            tid = queue.pop(0)
            ordered.append(tid)
            for child in children[tid]:
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    # Insert in priority order
                    queue.append(child)
                    queue.sort(key=_priority_key)

        # Cycle detection: tasks not in ordered list have circular dependencies
        if len(ordered) < len(batch_ids):
            cycle_ids = batch_ids - set(ordered)
            logger.warning(
                "[Phase4] Circular dependency detected among tasks: %s — "
                "falling back to priority sort for these tasks",
                sorted(cycle_ids),
            )
            # Append cycle tasks sorted by priority
            cycle_tasks = sorted(cycle_ids, key=_priority_key)
            ordered.extend(cycle_tasks)

        return [task_map[tid] for tid in ordered]

    def _apply_triage_classification(self, task: TaskInput) -> TaskInput:
        """Override task_type with triage classification if available.

        Triage's LLM-validated classification is more accurate than Stage 1's
        keyword-based detection. The override only applies when the triage
        issue_id matches the task_id (or when processing a single task).
        """
        tc = self._triage_context
        if not tc:
            return task

        triage_type = tc.get("classification_type", "")
        if not triage_type or triage_type == "unknown":
            return task

        mapped = self._TRIAGE_TO_PLAN_TYPE.get(triage_type)
        if not mapped:
            logger.info("[Phase4] Unmapped triage type '%s' — keeping Stage 1 task_type '%s'", triage_type, task.task_type)
            return task

        if mapped != task.task_type:
            logger.info(
                "[Phase4] Triage classification override: %s → %s (triage=%s, confidence=%.2f)",
                task.task_type, mapped, triage_type,
                tc.get("classification_confidence", 0),
            )
            task.task_type = mapped

        return task

    def _apply_triage_classification_from_ctx(self, task: TaskInput, ctx: dict) -> TaskInput:
        """Override task_type from a specific triage context dict (disk fallback)."""
        triage_type = ctx.get("classification_type", "")
        if not triage_type or triage_type == "unknown":
            return task
        mapped = self._TRIAGE_TO_PLAN_TYPE.get(triage_type)
        if mapped and mapped != task.task_type:
            logger.info(
                "[Phase4] Triage classification override (disk): %s → %s (triage=%s)",
                task.task_type, mapped, triage_type,
            )
            task.task_type = mapped
        return task

    def _run_single(self, input_file: str) -> dict[str, Any]:
        """Run full pipeline (Stages 1-5) for a single input file."""
        start_time = time.time()

        logger.info("=" * 80)
        logger.info("[Phase4] Development Planning Pipeline - HYBRID ARCHITECTURE")
        logger.info(f"[Phase4] Input: {input_file}")
        logger.info("=" * 80)

        try:
            # Stage 1: Input Parser
            step_start("Stage 1: Input Parser")
            stage1_start = time.time()
            task = self.stage1.run(input_file)
            stage1_duration = time.time() - stage1_start
            step_done("Stage 1: Input Parser")

            # Override task_type from triage if available
            task = self._apply_triage_classification(task)

            log_metric(
                "stage_complete",
                phase="plan",
                stage="stage1_input_parser",
                duration_seconds=stage1_duration,
                task_id=task.task_id,
            )

            # Stages 2-5
            result = self._run_stages_2_to_5(task)
            result["metrics"]["stage1_duration"] = stage1_duration

            total_duration = time.time() - start_time
            result["duration_seconds"] = total_duration

            logger.info("=" * 80)
            logger.info("[Phase4] Pipeline completed successfully")
            logger.info(f"[Phase4] Task ID: {task.task_id}")
            logger.info(f"[Phase4] Output: {result['output_file']}")
            logger.info(f"[Phase4] Total Duration: {total_duration:.2f}s")
            logger.info("=" * 80)

            log_metric(
                "phase_complete",
                phase="plan",
                status="success",
                duration_seconds=total_duration,
                task_id=task.task_id,
                output_file=result["output_file"],
            )

            return result

        except Exception as e:
            total_duration = time.time() - start_time
            logger.error(f"[Phase4] Pipeline failed: {e}", exc_info=True)

            log_metric(
                "phase_failed",
                phase="plan",
                error=str(e),
                duration_seconds=total_duration,
            )

            raise

    def _run_stages_2_to_5(self, task: TaskInput) -> dict[str, Any]:
        """Run Stages 2-5 for a pre-parsed TaskInput."""

        # Stage 2: Component Discovery
        step_start(f"Stage 2: Component Discovery ({task.task_id})")
        stage2_start = time.time()
        discovery_result = self.stage2.run(task, top_k=10)
        stage2_duration = time.time() - stage2_start
        step_done(f"Stage 2: Component Discovery ({task.task_id})")

        log_metric(
            "stage_complete",
            phase="plan",
            stage="stage2_component_discovery",
            duration_seconds=stage2_duration,
            task_id=task.task_id,
            components_found=len(discovery_result["affected_components"]),
        )

        # Stage 3: Pattern Matching
        step_start(f"Stage 3: Pattern Matching ({task.task_id})")
        stage3_start = time.time()
        pattern_result = self.stage3.run(
            task,
            discovery_result["affected_components"],
            top_k=5,
        )
        stage3_duration = time.time() - stage3_start
        step_done(f"Stage 3: Pattern Matching ({task.task_id})")

        log_metric(
            "stage_complete",
            phase="plan",
            stage="stage3_pattern_matcher",
            duration_seconds=stage3_duration,
            task_id=task.task_id,
            test_patterns=len(pattern_result["test_patterns"]),
            security_patterns=len(pattern_result["security_patterns"]),
            validation_patterns=len(pattern_result["validation_patterns"]),
            error_patterns=len(pattern_result["error_patterns"]),
        )

        # Stage 4: Plan Generation (LLM)
        # Use per-task triage context if available (disk fallback), else global.
        # IMPORTANT: validate issue_id match — global _triage_context may belong
        # to a different task in multi-task mode.
        effective_triage = {}
        if hasattr(self, "_per_task_triage") and task.task_id in self._per_task_triage:
            effective_triage = self._per_task_triage[task.task_id]
        elif self._triage_context:
            triage_id = self._triage_context.get("issue_id", "")
            if triage_id and triage_id == task.task_id:
                effective_triage = self._triage_context
            else:
                logger.info(
                    "[Phase4] Skipping global triage_context (issue_id=%s != task_id=%s)",
                    triage_id, task.task_id,
                )
        step_start(f"Stage 4: Plan Generation ({task.task_id})")
        stage4_start = time.time()
        plan = self.stage4.run(task, discovery_result, pattern_result, triage_context=effective_triage)
        stage4_duration = time.time() - stage4_start
        step_done(f"Stage 4: Plan Generation ({task.task_id})")

        log_metric(
            "stage_complete",
            phase="plan",
            stage="stage4_plan_generator",
            duration_seconds=stage4_duration,
            task_id=task.task_id,
            llm_call=True,
        )

        # Enrich plan with discovery data if LLM omitted fields
        plan = self._enrich_plan(plan, discovery_result, pattern_result)

        # Stage 5: Validation
        step_start(f"Stage 5: Validation ({task.task_id})")
        stage5_start = time.time()
        validation = self.stage5.run(plan)
        stage5_duration = time.time() - stage5_start

        if not validation.is_valid:
            step_fail(f"Stage 5: Validation ({task.task_id})")
            logger.error(f"[Phase4] Validation failed for {task.task_id}:")
            for error in validation.errors:
                logger.error(f"  - {error}")
            for field in validation.missing_fields:
                logger.error(f"  - Missing: {field}")
            raise ValueError(f"Plan validation failed for {task.task_id}: {validation.errors}")

        if validation.warnings:
            logger.warning(f"[Phase4] Validation warnings for {task.task_id}:")
            for warning in validation.warnings:
                logger.warning(f"  - {warning}")

        step_done(f"Stage 5: Validation ({task.task_id})")

        log_metric(
            "stage_complete",
            phase="plan",
            stage="stage5_validator",
            duration_seconds=stage5_duration,
            task_id=task.task_id,
            is_valid=validation.is_valid,
            warnings=len(validation.warnings),
        )

        # Write plan to file
        output_file = self.output_dir / f"{task.task_id}_plan.json"
        self._write_plan(plan, output_file)

        return {
            "status": "completed",
            "task_id": task.task_id,
            "output_file": str(output_file),
            "metrics": {
                "stage2_duration": stage2_duration,
                "stage3_duration": stage3_duration,
                "stage4_duration": stage4_duration,
                "stage5_duration": stage5_duration,
                "components_found": len(discovery_result["affected_components"]),
                "test_patterns": len(pattern_result["test_patterns"]),
                "security_patterns": len(pattern_result["security_patterns"]),
                "validation_warnings": len(validation.warnings),
            },
        }

    @staticmethod
    def _enrich_plan(
        plan: "ImplementationPlan",
        discovery_result: dict[str, Any],
        pattern_result: dict[str, Any],
    ) -> "ImplementationPlan":
        """Enrich plan with deterministic data from earlier stages.

        The LLM sometimes omits fields that were available in the prompt.
        This fills gaps using the authoritative data from Stage 2/3.
        """
        dp = plan.development_plan or {}

        # Fill affected_components from discovery if LLM left it empty.
        # Preserve full ComponentMatch objects (id, name, stereotype, layer, file_path,
        # relevance_score, change_type) — Phase 5 plan_reader needs file_path to resolve files.
        if not dp.get("affected_components"):
            comps = discovery_result.get("affected_components", [])
            if comps:
                dp["affected_components"] = [c for c in comps if isinstance(c, dict) and "name" in c]
                logger.info(
                    f"[Enrich] Filled affected_components from discovery: {len(dp['affected_components'])} components"
                )

        # Fill interfaces from discovery if LLM left it empty
        if not dp.get("interfaces"):
            ifaces = discovery_result.get("interfaces", [])
            if ifaces:
                dp["interfaces"] = ifaces
                logger.info(f"[Enrich] Filled interfaces from discovery: {len(ifaces)} interfaces")

        # Fill dependencies from discovery if LLM left it empty
        if not dp.get("dependencies"):
            deps = discovery_result.get("dependencies", [])
            if deps:
                dp["dependencies"] = deps
                logger.info(f"[Enrich] Filled dependencies from discovery: {len(deps)} dependencies")

        # Fill upgrade_plan.migration_sequence from pattern_result if LLM left it empty
        upgrade = pattern_result.get("upgrade_assessment", {})
        if upgrade.get("is_upgrade"):
            up = dp.get("upgrade_plan")
            if isinstance(up, dict):
                ms = up.get("migration_sequence", [])
                if not ms:
                    up["migration_sequence"] = upgrade.get("migration_sequence", [])
                    logger.info(f"[Enrich] Filled migration_sequence from scan: {len(up['migration_sequence'])} rules")

        plan.development_plan = dp
        return plan

    def _load_supplementary_context(self) -> dict[str, str]:
        """Load supplementary files into text snippets for LLM context."""
        context: dict[str, str] = {}
        MAX_CHARS_PER_CATEGORY = 3000

        for category, files in self.supplementary_files.items():
            if not files:
                continue

            snippets = []
            total_chars = 0

            for file_path in files:
                p = Path(file_path)
                if not p.is_file():
                    continue

                ext = p.suffix.lower()
                try:
                    if ext in (".txt", ".log", ".md", ".csv"):
                        text = p.read_text(encoding="utf-8", errors="replace")
                    elif ext == ".json":
                        data = json.loads(p.read_text(encoding="utf-8"))
                        text = json.dumps(data, indent=2, ensure_ascii=False)
                    elif ext in (".docx", ".doc"):
                        try:
                            from .parsers.docx_parser import parse_docx

                            result = parse_docx(p)
                            sections = result.get("sections", [])
                            text = "\n".join(f"{s['title']}: {' '.join(s['content'])}" for s in sections[:5])
                        except Exception:
                            text = f"[DOCX file: {p.name}]"
                    elif ext in (".xlsx", ".xls"):
                        try:
                            from .parsers.excel_parser import parse_excel

                            result = parse_excel(p)
                            sheets = result.get("sheets", {})
                            rows = []
                            for _sheet_name, sheet in sheets.items():
                                for row in sheet.get("data", [])[:20]:
                                    rows.append(" | ".join(str(c) for c in row))
                            text = "\n".join(rows)
                        except Exception:
                            text = f"[Excel file: {p.name}]"
                    else:
                        # Binary files (images, PDF, drawio) — just note the filename
                        text = f"[{ext.upper()} file: {p.name}]"

                    # Truncate per file
                    remaining = MAX_CHARS_PER_CATEGORY - total_chars
                    if remaining <= 0:
                        break
                    snippet = text[:remaining]
                    snippets.append(f"--- {p.name} ---\n{snippet}")
                    total_chars += len(snippet)

                except Exception as e:
                    logger.warning(f"[Phase4] Could not read supplementary file {p.name}: {e}")

            if snippets:
                context[category] = "\n\n".join(snippets)
                logger.info(f"[Phase4] Loaded {len(snippets)} {category} file(s) ({total_chars} chars)")

        return context

    def _load_json(self, path: Path) -> dict:
        """Load JSON file."""
        if not path.exists():
            logger.warning(f"[Phase4] File not found: {path}, using empty dict")
            return {}

        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[Phase4] Failed to load {path}: {e}")
            return {}

    def _write_plan(self, plan: ImplementationPlan, output_file: Path):
        """Write plan to JSON file."""
        from ...shared.schema_version import add_schema_version

        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            plan_dict = add_schema_version(plan.model_dump(), "plan")

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(plan_dict, f, indent=2, ensure_ascii=False)

            logger.info(f"[Phase4] Plan written to: {output_file}")

        except Exception as e:
            logger.error(f"[Phase4] Failed to write plan: {e}")
            raise
