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
    BuildVerifierStage,
    CodeGeneratorStage,
    CodeValidatorStage,
    ContextCollectorStage,
    OutputWriterStage,
    PlanReaderStage,
)
from .crew import ImplementCrew

logger = setup_logger(__name__)

_USE_CREW = False  # Set True to use CrewAI agents instead of direct LLM pipeline


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
        chroma_dir: str | None = None,
    ):
        self.repo_path = str(repo_path)
        self.task_id = task_id
        self.plans_dir = Path(plans_dir)
        self.facts_path = Path(facts_path)
        self.report_dir = Path(report_dir)
        self.dry_run = dry_run
        self.chroma_dir = chroma_dir
        self._plan_files_override: list[Path] | None = None

        # Ensure output dir exists
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def kickoff(self, inputs: dict[str, Any] = None) -> dict[str, Any]:
        """Execute pipeline (Orchestrator-compatible interface)."""
        self._plan_files_override = self._extract_plan_files_from_inputs(inputs)
        return self.run()

    def _validate_prerequisites(self, plan_path: str | None = None) -> list[str]:
        """Validate required inputs before running Phase 5."""
        errors: list[str] = []

        if not self.plans_dir.exists():
            errors.append(f"plans_dir missing: {self.plans_dir}")

        if self.task_id:
            # Single-task mode requires specific plan file
            candidate = plan_path or str(self.plans_dir / f"{self.task_id}_plan.json")
            if not Path(candidate).exists():
                errors.append(f"plan file not found for task_id={self.task_id}: {candidate}")

        return errors

    def run(self) -> dict[str, Any]:
        """
        Run code generation pipeline.

        If task_id is set, process single task. Otherwise, process all
        available plan files in plans_dir.
        """
        prereq_errors = self._validate_prerequisites()
        if prereq_errors:
            return {
                "status": "failed",
                "phase": "implement",
                "message": "; ".join(prereq_errors),
                "reports": [],
            }

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
        """Process all plan files as a cascade on a single integration branch."""
        start_time = time.time()

        if self._plan_files_override is not None:
            plan_files = sorted(self._plan_files_override)
            logger.info(f"[Phase5] Using {len(plan_files)} plan file(s) from previous phase output")
        else:
            plan_files = sorted(self.plans_dir.glob("*_plan.json"))
        if not plan_files:
            logger.warning(f"[Phase5] No plan files found in {self.plans_dir}")
            return {
                "status": "skipped",
                "phase": "implement",
                "message": "No plan files found",
                "reports": [],
            }

        n = len(plan_files)

        logger.info("=" * 80)
        logger.info(f"[Phase5] Cascade mode: {n} plans on single integration branch")
        logger.info("=" * 80)

        # 1. Setup: create ONE integration branch
        writer = OutputWriterStage(
            repo_path=self.repo_path,
            report_dir=str(self.report_dir),
            dry_run=self.dry_run,
        )
        cascade_branch = writer.setup_cascade_branch()
        if not cascade_branch and not self.dry_run:
            return {
                "status": "failed",
                "phase": "implement",
                "message": "Could not create integration branch",
                "reports": [],
            }

        # 2. Process each task sequentially — each sees prior changes
        reports = []
        succeeded = 0
        failed = 0
        completed_task_ids: list[str] = []

        for i, plan_file in enumerate(plan_files, 1):
            task_id = plan_file.stem.replace("_plan", "")
            logger.info(f"\n[Phase5] === Cascade {i}/{n}: {task_id} ===")

            try:
                report = self._run_single_cascade(
                    task_id=task_id,
                    plan_path=str(plan_file),
                    writer=writer,
                    cascade_branch=cascade_branch or "",
                    cascade_position=i,
                    cascade_total=n,
                    prior_task_ids=list(completed_task_ids),
                )
                reports.append(report.model_dump())
                if report.status in ("success", "partial", "dry_run"):
                    succeeded += 1
                    completed_task_ids.append(task_id)
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"[Phase5] Cascade task {task_id} failed: {e}")
                failed += 1
                reports.append({"task_id": task_id, "status": "failed", "error": str(e)})

        # 3. Teardown: switch back to original branch
        writer.teardown_cascade()

        total_duration = time.time() - start_time

        logger.info("=" * 80)
        logger.info(f"[Phase5] Cascade complete: {succeeded} succeeded, {failed} failed, {total_duration:.2f}s")
        logger.info(f"[Phase5] Integration branch: {cascade_branch}")
        logger.info("=" * 80)

        log_metric(
            "phase_complete",
            phase="implement",
            status="success" if failed == 0 else "partial",
            duration_seconds=total_duration,
            tasks_total=n,
            tasks_succeeded=succeeded,
            tasks_failed=failed,
        )

        return {
            "status": "completed" if failed == 0 else "partial",
            "phase": "implement",
            "cascade_branch": cascade_branch or "",
            "reports": reports,
            "metrics": {
                "tasks_total": n,
                "tasks_succeeded": succeeded,
                "tasks_failed": failed,
                "duration_seconds": total_duration,
            },
        }

    @staticmethod
    def _extract_plan_files_from_inputs(inputs: dict[str, Any] | None) -> list[Path] | None:
        """Prefer current-run plan outputs when orchestrator provides them."""
        if not isinstance(inputs, dict):
            return None

        previous_results = inputs.get("previous_results")
        if not isinstance(previous_results, dict):
            return None

        plan_result = previous_results.get("plan")
        if not isinstance(plan_result, dict):
            return None

        output_files = plan_result.get("output_files")
        if not isinstance(output_files, list):
            return None

        plan_files: list[Path] = []
        for path_str in output_files:
            path = Path(str(path_str))
            if path.name.endswith("_plan.json") and path.exists():
                plan_files.append(path)

        # Distinct + stable order by string path
        unique = sorted({str(p): p for p in plan_files}.values(), key=lambda p: str(p))
        return unique

    def _run_single_cascade(
        self,
        task_id: str,
        plan_path: str,
        writer: OutputWriterStage,
        cascade_branch: str,
        cascade_position: int,
        cascade_total: int,
        prior_task_ids: list[str],
    ) -> CodegenReport:
        """Run Stages 1-4 normally, then cascade-write via shared writer."""
        task_start = time.time()

        # Stage 1: Plan Reader
        step_start(f"Stage 1: Plan Reader ({task_id})")
        stage1 = PlanReaderStage(
            plans_dir=str(self.plans_dir),
            facts_path=str(self.facts_path),
        )
        plan_input, strategy = stage1.run(task_id=task_id, plan_path=plan_path)
        step_done(f"Stage 1: Plan Reader ({task_id})")

        # Stage 2: Context Collector — reads CURRENT disk state (includes prior changes!)
        step_start(f"Stage 2: Context Collector ({task_id})")
        stage2 = ContextCollectorStage(repo_path=self.repo_path)
        context = stage2.run(plan_input)
        step_done(f"Stage 2: Context Collector ({task_id})")

        if context.total_files == 0:
            logger.warning(f"[Phase5] No files to process for {task_id}")
            return CodegenReport(
                task_id=task_id,
                status="failed",
                cascade_branch=cascade_branch,
                cascade_position=cascade_position,
                cascade_total=cascade_total,
                prior_task_ids=prior_task_ids,
                duration_seconds=time.time() - task_start,
            )

        if _USE_CREW:
            # CrewAI mode: ImplementCrew replaces Stage 3 + 4b
            step_start(f"Stage 3+4b: Implement Crew ({task_id})")
            crew = ImplementCrew(
                repo_path=self.repo_path,
                facts_path=str(self.facts_path),
                chroma_dir=self.chroma_dir,
            )
            generated_files, build_result = crew.run(plan_input, context)
            step_done(f"Stage 3+4b: Implement Crew ({task_id})")
            llm_calls = crew.total_calls
            total_tokens = crew.total_tokens

            # Stage 4: Code Validator (crew mode: post-check on crew output)
            step_start(f"Stage 4: Code Validator ({task_id})")
            stage4 = CodeValidatorStage()
            validation = stage4.run(generated_files)
            step_done(f"Stage 4: Code Validator ({task_id})")
        else:
            # Legacy mode: Stage 3 → Stage 4 → Stage 4b
            step_start(f"Stage 3: Code Generator ({task_id})")
            stage3 = CodeGeneratorStage()
            generated_files = stage3.run(plan_input, context, strategy)
            step_done(f"Stage 3: Code Generator ({task_id})")

            step_start(f"Stage 4: Code Validator ({task_id})")
            stage4 = CodeValidatorStage()
            validation = stage4.run(generated_files)
            step_done(f"Stage 4: Code Validator ({task_id})")

            step_start(f"Stage 4b: Build Verifier ({task_id})")
            stage4b = BuildVerifierStage(
                repo_path=self.repo_path,
                dry_run=self.dry_run,
            )
            generated_files, build_result = stage4b.run(
                generated_files, validation, plan_input, strategy
            )
            step_done(f"Stage 4b: Build Verifier ({task_id})")
            llm_calls = stage3.total_calls + stage4b.total_calls
            total_tokens = stage3.total_tokens + stage4b.total_tokens

        # Stage 5: Cascade write (no branch creation, no switchback)
        step_start(f"Stage 5: Cascade Write ({task_id})")
        task_duration = time.time() - task_start

        degradation_reasons = self._compute_degradations(
            generated_files=generated_files,
            validation=validation,
            build_result=build_result,
        )

        report = writer.cascade_write_and_commit(
            task_id=task_id,
            generated_files=generated_files,
            validation=validation,
            cascade_branch=cascade_branch,
            cascade_position=cascade_position,
            cascade_total=cascade_total,
            prior_task_ids=prior_task_ids,
            duration_seconds=task_duration,
            llm_calls=llm_calls,
            total_tokens=total_tokens,
            build_verification=build_result,
            degradation_reasons=degradation_reasons,
        )
        step_done(f"Stage 5: Cascade Write ({task_id})")

        return report

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

            if _USE_CREW:
                # CrewAI mode: ImplementCrew replaces Stage 3 + 4b
                step_start(f"Stage 3+4b: Implement Crew ({task_id})")
                crew_start = time.time()
                crew = ImplementCrew(
                    repo_path=self.repo_path,
                    facts_path=str(self.facts_path),
                )
                generated_files, build_result = crew.run(plan_input, context)
                crew_duration = time.time() - crew_start
                step_done(f"Stage 3+4b: Implement Crew ({task_id})")

                log_metric(
                    "stage_complete",
                    phase="implement",
                    stage="implement_crew",
                    duration_seconds=crew_duration,
                    task_id=task_id,
                    files_generated=len(generated_files),
                    llm_calls=crew.total_calls,
                    total_tokens=crew.total_tokens,
                    build_passed=build_result.all_passed,
                )

                llm_calls = crew.total_calls
                total_tokens = crew.total_tokens

                # Stage 4: Code Validator (crew mode: post-check on crew output)
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
            else:
                # Legacy mode: Stage 3 → Stage 4 → Stage 4b
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

                # Stage 4b: Build Verifier
                step_start(f"Stage 4b: Build Verifier ({task_id})")
                stage4b_start = time.time()
                stage4b = BuildVerifierStage(
                    repo_path=self.repo_path,
                    dry_run=self.dry_run,
                )
                generated_files, build_result = stage4b.run(
                    generated_files, validation, plan_input, strategy
                )
                stage4b_duration = time.time() - stage4b_start
                step_done(f"Stage 4b: Build Verifier ({task_id})")

                log_metric(
                    "stage_complete",
                    phase="implement",
                    stage="stage4b_build_verifier",
                    duration_seconds=stage4b_duration,
                    task_id=task_id,
                    all_passed=build_result.all_passed,
                    containers_built=build_result.total_containers_built,
                    containers_failed=build_result.total_containers_failed,
                    heal_attempts=build_result.total_heal_attempts,
                    skipped=build_result.skipped,
                )

                llm_calls = stage3.total_calls + stage4b.total_calls
                total_tokens = stage3.total_tokens + stage4b.total_tokens

            # Stage 5: Output Writer
            step_start(f"Stage 5: Output Writer ({task_id})")
            stage5_start = time.time()
            stage5 = OutputWriterStage(
                repo_path=self.repo_path,
                report_dir=str(self.report_dir),
                dry_run=self.dry_run,
            )
            total_duration = time.time() - start_time
            degradation_reasons = self._compute_degradations(
                generated_files=generated_files,
                validation=validation,
                build_result=build_result,
            )

            report = stage5.run(
                task_id=task_id,
                generated_files=generated_files,
                validation=validation,
                duration_seconds=total_duration,
                llm_calls=llm_calls,
                total_tokens=total_tokens,
                build_verification=build_result,
                degradation_reasons=degradation_reasons,
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
            if degradation_reasons:
                report.degradation_reasons = degradation_reasons
                if report.status == "success":
                    report.status = "partial"

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

    @staticmethod
    def _compute_degradations(
        generated_files: list,
        validation,
        build_result,
    ) -> list[str]:
        """Derive degradation reasons for implement phase."""
        reasons: list[str] = []
        if validation and getattr(validation, "total_invalid", 0) > 0:
            reasons.append(f"{validation.total_invalid} file(s) failed validation")

        # Compute failed_count similar to stage5 filtering
        invalid_paths = {r.file_path for r in getattr(validation, "file_results", []) if not r.is_valid}
        failed_count = len([gf for gf in generated_files if gf.file_path in invalid_paths])
        if failed_count > 0:
            reasons.append(f"{failed_count} generated file(s) dropped after validation")

        if build_result and not build_result.skipped and not build_result.all_passed:
            reasons.append(
                f"build failed for {build_result.total_containers_failed}/{build_result.total_containers_built} container(s)"
            )

        return reasons
