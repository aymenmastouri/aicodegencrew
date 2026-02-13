"""
Code Generation Pipeline (Phase 5)

HYBRID ARCHITECTURE:
- Stages 1, 2, 4: Deterministic (plan reading, context, validation)
- Stage 3: LLM (code generation, 1 call per file)
- Stage 5: Deterministic (git operations, file writing)

Total Duration: 30s-5min (depending on file count)
LLM Calls: 1 per affected file
"""

import time
from pathlib import Path
from typing import Any

from ...shared.utils.logger import log_metric, setup_logger, step_done, step_start
from .schemas import CodegenReport
from .stages import (
    CodeGeneratorStage,
    CodeValidatorStage,
    ContextCollectorStage,
    OutputWriterStage,
    PlanReaderStage,
)

logger = setup_logger(__name__)


class CodeGenerationPipeline:
    """
    Phase 5: Code Generation Pipeline.

    Hybrid architecture with 5 stages:
    1. Plan Reader (deterministic)
    2. Context Collector (file I/O)
    3. Code Generator (LLM, 1 call per file)
    4. Code Validator (deterministic)
    5. Output Writer (git + file I/O)
    """

    def __init__(
        self,
        repo_path: str,
        task_id: str | None = None,
        plans_dir: str = "knowledge/plan",
        facts_path: str = "knowledge/extract/architecture_facts.json",
        report_dir: str = "knowledge/implement",
        dry_run: bool = False,
    ):
        self.repo_path = str(repo_path)
        self.task_id = task_id
        self.plans_dir = Path(plans_dir)
        self.facts_path = Path(facts_path)
        self.report_dir = Path(report_dir)
        self.dry_run = dry_run

        # Ensure output dir exists
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def kickoff(self, inputs: dict[str, Any] = None) -> dict[str, Any]:
        """Execute pipeline (Orchestrator-compatible interface)."""
        return self.run()

    def run(self) -> dict[str, Any]:
        """
        Run code generation pipeline.

        If task_id is set, process single task. Otherwise, process all
        available plan files in plans_dir.
        """
        if self.task_id:
            report = self._run_single(self.task_id)
            report_dict = report.model_dump()
            return {
                "status": report.status,
                "phase": "implement",
                "task_id": report.task_id,
                "report": report_dict,
                "reports": [report_dict],
                "metrics": {
                    "files_changed": report.files_changed,
                    "files_created": report.files_created,
                    "files_failed": report.files_failed,
                    "llm_calls": report.llm_calls,
                    "total_tokens": report.total_tokens,
                    "duration_seconds": report.duration_seconds,
                },
            }

        return self._run_all()

    def _run_all(self) -> dict[str, Any]:
        """Process all plan files in plans_dir."""
        start_time = time.time()

        # Find all plan files
        plan_files = sorted(self.plans_dir.glob("*_plan.json"))
        if not plan_files:
            logger.warning(f"[Phase5] No plan files found in {self.plans_dir}")
            return {
                "status": "skipped",
                "phase": "implement",
                "message": "No plan files found",
                "reports": [],
            }

        logger.info("=" * 80)
        logger.info(f"[Phase5] Code Generation Pipeline - {len(plan_files)} plans")
        logger.info("=" * 80)

        reports = []
        succeeded = 0
        failed = 0

        for i, plan_file in enumerate(plan_files, 1):
            task_id = plan_file.stem.replace("_plan", "")
            logger.info(f"\n[Phase5] === Task {i}/{len(plan_files)}: {task_id} ===")

            try:
                report = self._run_single(task_id, plan_path=str(plan_file))
                reports.append(report.model_dump())
                if report.status in ("success", "partial", "dry_run"):
                    succeeded += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"[Phase5] Task {task_id} failed: {e}")
                failed += 1
                reports.append({"task_id": task_id, "status": "failed", "error": str(e)})

        total_duration = time.time() - start_time

        logger.info("=" * 80)
        logger.info(f"[Phase5] Complete: {succeeded} succeeded, {failed} failed, {total_duration:.2f}s")
        logger.info("=" * 80)

        log_metric(
            "phase_complete",
            phase="implement",
            status="success" if failed == 0 else "partial",
            duration_seconds=total_duration,
            tasks_total=len(plan_files),
            tasks_succeeded=succeeded,
            tasks_failed=failed,
        )

        return {
            "status": "completed" if failed == 0 else "partial",
            "phase": "implement",
            "reports": reports,
            "metrics": {
                "tasks_total": len(plan_files),
                "tasks_succeeded": succeeded,
                "tasks_failed": failed,
                "duration_seconds": total_duration,
            },
        }

    def _run_single(
        self,
        task_id: str,
        plan_path: str | None = None,
    ) -> CodegenReport:
        """Run the full pipeline (Stages 1-5) for a single task."""
        start_time = time.time()

        logger.info("=" * 80)
        logger.info("[Phase5] Code Generation Pipeline - HYBRID ARCHITECTURE")
        logger.info(f"[Phase5] Task: {task_id}")
        logger.info(f"[Phase5] Target repo: {self.repo_path}")
        logger.info(f"[Phase5] Dry run: {self.dry_run}")
        logger.info("=" * 80)

        try:
            # Stage 1: Plan Reader
            step_start(f"Stage 1: Plan Reader ({task_id})")
            stage1_start = time.time()
            stage1 = PlanReaderStage(
                plans_dir=str(self.plans_dir),
                facts_path=str(self.facts_path),
            )
            plan_input, strategy = stage1.run(task_id=task_id, plan_path=plan_path)
            stage1_duration = time.time() - stage1_start
            step_done(f"Stage 1: Plan Reader ({task_id})")

            log_metric(
                "stage_complete",
                phase="implement",
                stage="stage1_plan_reader",
                duration_seconds=stage1_duration,
                task_id=task_id,
                task_type=plan_input.task_type,
                components=len(plan_input.affected_components),
            )

            # Stage 2: Context Collector
            step_start(f"Stage 2: Context Collector ({task_id})")
            stage2_start = time.time()
            stage2 = ContextCollectorStage(repo_path=self.repo_path)
            context = stage2.run(plan_input)
            stage2_duration = time.time() - stage2_start
            step_done(f"Stage 2: Context Collector ({task_id})")

            log_metric(
                "stage_complete",
                phase="implement",
                stage="stage2_context_collector",
                duration_seconds=stage2_duration,
                task_id=task_id,
                files_collected=context.total_files,
                files_skipped=context.skipped_files,
            )

            if context.total_files == 0:
                logger.warning(f"[Phase5] No files to process for {task_id}")
                return CodegenReport(
                    task_id=task_id,
                    status="failed",
                    duration_seconds=time.time() - start_time,
                )

            # Stage 3: Code Generator (LLM)
            step_start(f"Stage 3: Code Generator ({task_id})")
            stage3_start = time.time()
            stage3 = CodeGeneratorStage()
            generated_files = stage3.run(plan_input, context, strategy)
            stage3_duration = time.time() - stage3_start
            step_done(f"Stage 3: Code Generator ({task_id})")

            log_metric(
                "stage_complete",
                phase="implement",
                stage="stage3_code_generator",
                duration_seconds=stage3_duration,
                task_id=task_id,
                files_generated=len(generated_files),
                llm_calls=stage3.total_calls,
                total_tokens=stage3.total_tokens,
            )

            # Stage 4: Code Validator
            step_start(f"Stage 4: Code Validator ({task_id})")
            stage4_start = time.time()
            stage4 = CodeValidatorStage()
            validation = stage4.run(generated_files)
            stage4_duration = time.time() - stage4_start
            step_done(f"Stage 4: Code Validator ({task_id})")

            log_metric(
                "stage_complete",
                phase="implement",
                stage="stage4_code_validator",
                duration_seconds=stage4_duration,
                task_id=task_id,
                valid=validation.total_valid,
                invalid=validation.total_invalid,
                security_issues=len(validation.security_issues),
            )

            # Stage 5: Output Writer
            step_start(f"Stage 5: Output Writer ({task_id})")
            stage5_start = time.time()
            stage5 = OutputWriterStage(
                repo_path=self.repo_path,
                report_dir=str(self.report_dir),
                dry_run=self.dry_run,
            )
            total_duration = time.time() - start_time
            report = stage5.run(
                task_id=task_id,
                generated_files=generated_files,
                validation=validation,
                duration_seconds=total_duration,
                llm_calls=stage3.total_calls,
                total_tokens=stage3.total_tokens,
            )
            stage5_duration = time.time() - stage5_start
            step_done(f"Stage 5: Output Writer ({task_id})")

            log_metric(
                "stage_complete",
                phase="implement",
                stage="stage5_output_writer",
                duration_seconds=stage5_duration,
                task_id=task_id,
                branch=report.branch_name,
                status=report.status,
            )

            total_duration = time.time() - start_time
            report.duration_seconds = total_duration

            logger.info("=" * 80)
            logger.info(f"[Phase5] Pipeline completed: {report.status}")
            logger.info(f"[Phase5] Branch: {report.branch_name}")
            logger.info(
                f"[Phase5] Files: {report.files_changed} changed, "
                f"{report.files_created} created, {report.files_failed} failed"
            )
            logger.info(f"[Phase5] Duration: {total_duration:.2f}s")
            logger.info("=" * 80)

            log_metric(
                "phase_complete",
                phase="implement",
                status=report.status,
                task_id=task_id,
                duration_seconds=total_duration,
                files_changed=report.files_changed,
                files_created=report.files_created,
                files_failed=report.files_failed,
                llm_calls=report.llm_calls,
                total_tokens=report.total_tokens,
            )

            return report

        except Exception as e:
            total_duration = time.time() - start_time
            logger.error(f"[Phase5] Pipeline failed: {e}", exc_info=True)

            log_metric(
                "phase_failed",
                phase="implement",
                error=str(e),
                task_id=task_id,
                duration_seconds=total_duration,
            )

            raise
