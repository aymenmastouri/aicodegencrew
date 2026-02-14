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


class DevelopmentPlanningPipeline:
    """
    Phase 4: Development Planning Pipeline.

    Hybrid architecture with 5 stages:
    1. Input Parser (deterministic)
    2. Component Discovery (RAG + scoring)
    3. Pattern Matcher (TF-IDF + rules)
    4. Plan Generator (LLM)
    5. Validator (Pydantic)
    """

    # JIRA priority ordering (lower = higher priority)
    PRIORITY_ORDER = {
        "Blocker": 1,
        "Critical": 2,
        "Major": 3,
        "Minor": 4,
        "Trivial": 5,
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
            chroma_dir: ChromaDB directory (Phase 0)
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
        self.supplementary_context: str = ""
        self._stages_initialized = False

    def kickoff(self, inputs: dict[str, Any] = None) -> dict[str, Any]:
        """
        Execute pipeline (Orchestrator-compatible interface).

        Args:
            inputs: Optional inputs (not used, input_files from __init__)

        Returns:
            Dict with status, output_files, metrics
        """
        return self.run()

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
        )
        self.stage5 = ValidatorStage(analyzed_architecture=self.analyzed_architecture)
        self._stages_initialized = True

    def run(self) -> dict[str, Any]:
        """
        Run pipeline for all input files.

        Single file: run directly.
        Multiple files: parse all (Stage 1), sort by priority, process each sequentially.

        Returns:
            Dict with status, output_files, duration, metrics, results
        """
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

        # Step 2: Sort by content (priority, task_type, dependencies)
        sorted_tasks = self._sort_tasks(parsed_tasks)

        logger.info("[Phase4] Processing order:")
        for i, task in enumerate(sorted_tasks, 1):
            logger.info(f"  {i}. {task.task_id} [{task.priority}] type={task.task_type} links={task.linked_tasks}")

        # Step 3: Process each task sequentially (Stages 2-5)
        results = []
        succeeded = 0
        failed = 0

        for i, task in enumerate(sorted_tasks, 1):
            logger.info(f"\n[Phase4] === Task {i}/{len(sorted_tasks)}: {task.task_id} ===")
            try:
                result = self._run_stages_2_to_5(task)
                results.append(result)
                succeeded += 1
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
        """Sort tasks by JIRA priority, task type, and dependency order."""
        task_ids = {t.task_id for t in tasks}

        def sort_key(task: TaskInput):
            # 1. JIRA priority (Blocker=1 .. Trivial=5)
            prio = self.PRIORITY_ORDER.get(task.priority, 3)
            # 2. Task type (upgrade=1, bugfix=2, feature=3, refactoring=4)
            ttype = self.TASK_TYPE_ORDER.get(task.task_type, 3)
            # 3. Dependency: if this task links to another task in the batch,
            #    it's a child/subtask → process AFTER the parent (higher number)
            is_child = 1 if any(link in task_ids for link in task.linked_tasks) else 0
            return (is_child, prio, ttype, task.task_id)

        return sorted(tasks, key=sort_key)

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
        step_start(f"Stage 4: Plan Generation ({task.task_id})")
        stage4_start = time.time()
        plan = self.stage4.run(task, discovery_result, pattern_result)
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
        try:
            plan_dict = plan.model_dump()

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(plan_dict, f, indent=2, ensure_ascii=False)

            logger.info(f"[Phase4] Plan written to: {output_file}")

        except Exception as e:
            logger.error(f"[Phase4] Failed to write plan: {e}")
            raise
