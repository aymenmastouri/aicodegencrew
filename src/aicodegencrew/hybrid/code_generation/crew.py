"""Implement Crew: Single-agent CrewAI with Python-controlled build-fix loop.

Architecture (Phase 5 v3):
  Preflight (deterministic) -> Build-Fix Loop (max 3 attempts) -> Post-crew (commit)

  Build-Fix Loop:
    - Attempt 1: Developer implements all files
    - Import fixer runs (deterministic)
    - Build verification runs (deterministic subprocess)
    - If build fails: Developer fixes errors (attempts 2-3)
    - If build passes or max attempts reached: exit loop

Process: Process.sequential with 1 agent, 1 task per iteration.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

from crewai import Crew, Process, Task

from ...shared.mcp import get_phase5_mcps
from ...shared.utils.crew_callbacks import step_callback, task_callback
from ...shared.utils.crewai_patches import apply_patches
from ...shared.utils.embedder_config import get_crew_embedder
from ...shared.utils.logger import setup_logger
from ...shared.utils.tool_guardrails import install_guardrails, uninstall_guardrails

# Apply CrewAI patches for on-prem LLM compatibility (idempotent)
apply_patches()
from ...shared.tools import RAGQueryTool, SymbolQueryTool
from .agents import create_agent
from .output_writer import OutputWriter
from .preflight import (
    DependencyGraphBuilder,
    ImportFixer,
    ImportIndex,
    ImportIndexBuilder,
    PlanReader,
    PreflightValidator,
    TaskSourceReader,
)
from .schemas import (
    BuildVerificationResult,
    CodegenPlanInput,
    ContainerBuildResult,
    GeneratedFile,
)
from .tasks import fix_task, implement_task
from .tools import (
    BuildErrorParserTool,
    BuildRunnerTool,
    CodeReaderTool,
    CodeWriterTool,
    DependencyLookupTool,
    FactsQueryTool,
    ImportIndexTool,
    PlanReaderTool,
    TaskSourceTool,
)

# MCPs loaded dynamically from shared/mcp/mcp_manager.py
_MAX_RPM = 30
_VERBOSE = True
MAX_BUILD_RETRIES = 3

# Matches file paths ending with a known extension followed by :line_number
# Handles Windows absolute paths (C:\...) where ":" appears in the drive letter
_FAILED_FILE_RE = re.compile(
    r"(.+?\.(?:java|kt|ts|tsx|html|scss|css|json|xml|gradle|properties)):\d+",
    re.IGNORECASE,
)

logger = setup_logger(__name__)


class ImplementCrew:
    """Single-agent crew with Python-controlled build-fix loop.

    Full flow:
    1. Preflight: plan reading, import index, dependency graph, validation
    2. Build-fix loop (max 3 attempts):
       - Crew execution (1 developer agent, 1 task)
       - Import fixer (deterministic)
       - Build verification (deterministic subprocess)
       - If build fails: format errors, loop back with fix task
    3. Output writer: commit if safety gate passes
    """

    def __init__(
        self,
        repo_path: str,
        facts_path: str = "knowledge/extract/architecture_facts.json",
        plans_dir: str = "knowledge/plan",
        output_dir: str = "knowledge/implement",
        task_input_dir: str | None = None,
        *,
        build_verify: bool = True,
        dry_run: bool = False,
    ):
        self.repo_path = Path(repo_path)
        self.facts_path = Path(facts_path)
        self.plans_dir = plans_dir
        self.output_dir = Path(output_dir)
        self.task_input_dir = (task_input_dir or os.getenv("TASK_INPUT_DIR", "")).strip()
        self.build_verify = build_verify
        self.dry_run = dry_run
        self.total_calls = 0
        self.total_tokens = 0
        self._containers: list[dict[str, str]] | None = None

    # ── Container helpers ───────────────────────────────────────────────────

    def _load_facts(self) -> dict:
        """Load architecture_facts.json; returns empty dict on failure."""
        if not self.facts_path.exists():
            return {}
        try:
            return json.loads(self.facts_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _load_containers(self) -> list[dict[str, str]]:
        if self._containers is not None:
            return self._containers

        if not self.facts_path.exists():
            self._containers = []
            return self._containers

        try:
            data = json.loads(self.facts_path.read_text(encoding="utf-8"))
            out: list[dict[str, str]] = []
            for c in data.get("containers", []):
                metadata = c.get("metadata", {})
                out.append(
                    {
                        "id": c.get("id", ""),
                        "name": c.get("name", ""),
                        "root_path": c.get("root_path", "") or metadata.get("root_path", ""),
                        "build_system": metadata.get("build_system", ""),
                        "language": metadata.get("language", ""),
                    }
                )
            self._containers = out
        except Exception:
            self._containers = []

        return self._containers

    def _container_ids_for_plan(self, plan: CodegenPlanInput) -> list[str]:
        containers = self._load_containers()
        if not containers:
            return []

        # Normalize repo_path once for stripping absolute prefixes
        repo_prefix = str(self.repo_path).replace("\\", "/").rstrip("/") + "/"

        ids: list[str] = []
        for comp in plan.affected_components:
            fp = comp.file_path.replace("\\", "/")
            # Strip absolute repo prefix so comparison is always repo-relative
            if fp.startswith(repo_prefix):
                fp = fp[len(repo_prefix):]
            for c in containers:
                root = (c.get("root_path", "") or "").replace("\\", "/").strip("/")
                if root and (fp.startswith(root + "/") or fp == root):
                    cid = c.get("id", "")
                    if cid and cid not in ids:
                        ids.append(cid)
                    break

        if not ids:
            ids = [c.get("id", "") for c in containers if c.get("id") and c.get("build_system")]

        return [cid for cid in ids if cid]

    # ── Staging conversion ──────────────────────────────────────────────────

    @staticmethod
    def _staging_to_generated_files(staging: dict[str, dict[str, Any]]) -> list[GeneratedFile]:
        generated: list[GeneratedFile] = []
        for file_path, entry in staging.items():
            generated.append(
                GeneratedFile(
                    file_path=file_path,
                    content=entry.get("content", ""),
                    original_content=entry.get("original_content", ""),
                    action=entry.get("action", "modify"),
                    language=entry.get("language", "other"),
                )
            )
        return generated

    # ── Deterministic build verification (post-crew) ───────────────────────

    def _verify_builds(
        self,
        plan: CodegenPlanInput,
        staging: dict[str, dict[str, Any]],
        baseline_cache: dict[str, dict] | None = None,
    ) -> BuildVerificationResult:
        if not self.build_verify:
            return BuildVerificationResult(skipped=True, skip_reason="build_verify=False")

        container_ids = self._container_ids_for_plan(plan)
        if not container_ids:
            return BuildVerificationResult(
                all_passed=False,
                skipped=False,
                skip_reason="No buildable containers detected for plan",
            )

        runner = BuildRunnerTool(
            repo_path=str(self.repo_path),
            facts_path=str(self.facts_path),
            staging=staging,
        )
        parser = BuildErrorParserTool()
        results: list[ContainerBuildResult] = []

        for cid in container_ids:
            # Use cached baseline result to avoid re-running on fix attempts
            if baseline_cache is not None and cid in baseline_cache:
                baseline = baseline_cache[cid]
            else:
                baseline_raw = runner._run(container_id=cid, baseline=True)
                baseline = self._safe_json(baseline_raw)
                if baseline_cache is not None:
                    baseline_cache[cid] = baseline

            cname = baseline.get("container_name") or cid
            bcmd = baseline.get("build_command", "")

            if not baseline.get("success", False):
                results.append(
                    ContainerBuildResult(
                        container_id=cid,
                        container_name=cname,
                        build_command=bcmd,
                        success=False,
                        exit_code=int(baseline.get("exit_code", -1)),
                        error_summary="Baseline broken (pre-existing); staged build not executed",
                        attempts=0,
                    )
                )
                continue

            staged_raw = runner._run(container_id=cid, baseline=False)
            staged = self._safe_json(staged_raw)
            raw_output = str(staged.get("output", ""))

            if staged.get("success", False):
                results.append(
                    ContainerBuildResult(
                        container_id=cid,
                        container_name=staged.get("container_name", cname),
                        build_command=staged.get("build_command", bcmd),
                        success=True,
                        exit_code=int(staged.get("exit_code", 0)),
                        raw_output=raw_output,
                        attempts=1,
                    )
                )
                continue

            parsed_raw = parser._run(
                build_output=raw_output,
                build_tool=str(staged.get("build_tool", "auto")),
            )
            parsed = self._safe_json(parsed_raw)
            errors = parsed.get("errors", [])
            if errors:
                summary = "; ".join(
                    f"{e.get('file_path', '?')}:{e.get('line', 0)} {e.get('message', '')}" for e in errors[:8]
                )
            else:
                summary = raw_output[-1000:]

            results.append(
                ContainerBuildResult(
                    container_id=cid,
                    container_name=staged.get("container_name", cname),
                    build_command=staged.get("build_command", bcmd),
                    success=False,
                    exit_code=int(staged.get("exit_code", -1)),
                    error_summary=summary,
                    raw_output=raw_output,
                    attempts=1,
                )
            )

        passed = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)
        return BuildVerificationResult(
            container_results=results,
            all_passed=failed == 0,
            total_containers_built=passed,
            total_containers_failed=failed,
        )

    @staticmethod
    def _safe_json(text: str) -> dict[str, Any]:
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _task_source_snapshot(self, task_id: str) -> str:
        """Load deterministic task-source context for prompt grounding."""
        source = TaskSourceReader(task_input_dir=self.task_input_dir).run(task_id=task_id)
        if not source.get("found", False):
            return f"(not found: {source.get('error', 'unknown')})"

        summary = str(source.get("summary", "") or "")
        description = str(source.get("description", "") or "")
        source_file = str(source.get("source_file", "") or "")
        excerpt = description[:800] if description else ""
        return (f"- source_file: {source_file}\n- summary: {summary}\n- description_excerpt: {excerpt}").strip()

    def _format_build_errors(self, build_result: BuildVerificationResult) -> str:
        """Format build errors for fix task prompt."""
        lines = []
        for cr in build_result.container_results:
            if not cr.success:
                lines.append(f"Container: {cr.container_name} ({cr.container_id})")
                lines.append(f"  Command: {cr.build_command}")
                lines.append(f"  Exit code: {cr.exit_code}")
                lines.append(f"  Errors: {cr.error_summary}")
        return "\n".join(lines)

    def _extract_failed_files(self, build_result: BuildVerificationResult) -> list[str]:
        """Extract file paths from build error summaries.

        Uses regex instead of split(":") to correctly handle Windows absolute
        paths (e.g. C:\\path\\to\\File.java:42) where ":" appears in the drive letter.
        """
        failed = set()
        for cr in build_result.container_results:
            if not cr.success and cr.error_summary:
                for segment in cr.error_summary.split(";"):
                    m = _FAILED_FILE_RE.search(segment.strip())
                    if m:
                        failed.add(m.group(1).strip())
        return sorted(failed)

    # ── Core: crew execution (implement or fix) ────────────────────────────

    def _execute_implement(
        self,
        plan: CodegenPlanInput,
        staging: dict[str, dict[str, Any]],
        dependency_order_paths: list[str],
        import_index,
        generation_order,
    ) -> None:
        """Execute implement task: developer generates all files."""
        # Shared tool instances bound to preflight artifacts
        import_tool = ImportIndexTool(
            repo_path=str(self.repo_path),
            facts_path=str(self.facts_path),
            import_index=import_index,
        )
        dependency_tool = DependencyLookupTool(generation_order=generation_order)
        task_source_tool = TaskSourceTool(task_input_dir=self.task_input_dir)

        developer_tools = [
            CodeReaderTool(repo_path=str(self.repo_path), staging=staging),
            CodeWriterTool(repo_path=str(self.repo_path), staging=staging),
            FactsQueryTool(facts_dir=str(self.facts_path.parent)),
            RAGQueryTool(),
            SymbolQueryTool(),
            import_tool,
            dependency_tool,
            task_source_tool,
            PlanReaderTool(plans_dir=self.plans_dir, facts_path=str(self.facts_path)),
        ]

        developer = create_agent("developer", developer_tools, get_phase5_mcps(), _VERBOSE)

        task_source_snapshot = self._task_source_snapshot(plan.task_id)

        impl_desc, impl_expected, _ = implement_task(
            task_id=plan.task_id,
            summary=plan.summary,
            description=plan.description,
            task_type=plan.task_type,
            implementation_steps=plan.implementation_steps,
            upgrade_plan=plan.upgrade_plan,
            dependency_order=dependency_order_paths,
            task_source_snapshot=task_source_snapshot,
            source_files=plan.source_files,
            requirements=plan.requirements,
            acceptance_criteria=plan.acceptance_criteria,
            technical_notes=plan.technical_notes,
            risks=plan.risks,
            estimated_complexity=plan.estimated_complexity,
            architecture_context=plan.architecture_context,
        )

        task = Task(
            description=impl_desc,
            expected_output=impl_expected,
            agent=developer,
            human_input=False,
        )

        log_dir = self.output_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        crew = Crew(
            agents=[developer],
            tasks=[task],
            process=Process.sequential,
            verbose=_VERBOSE,
            memory=False,
            planning=False,
            max_rpm=_MAX_RPM,
            step_callback=step_callback,
            task_callback=task_callback,
            output_log_file=str(log_dir / f"{plan.task_id}_impl.json"),
            embedder=get_crew_embedder(),
        )

        tracker = None
        try:
            # Scale budget: at least 50, or 4 tool calls per file in the dependency order
            guardrail_budget = max(50, len(dependency_order_paths) * 4)
            tracker = install_guardrails(max_total=guardrail_budget)
            try:
                result = crew.kickoff(
                    inputs={
                        "task_id": plan.task_id,
                        "task_type": plan.task_type,
                        "summary": plan.summary,
                        "description": plan.description,
                        "task_input_dir": self.task_input_dir,
                        "task_source_snapshot": task_source_snapshot,
                        "implementation_steps": plan.implementation_steps,
                        "affected_components": [c.model_dump() for c in plan.affected_components],
                        "dependency_order": dependency_order_paths,
                    }
                )
                self.total_calls += 1
                token_usage = getattr(result, "token_usage", None)
                if token_usage is not None:
                    if isinstance(token_usage, dict):
                        self.total_tokens += int(token_usage.get("total_tokens", 0))
                    else:
                        # CrewAI UsageMetrics object (total_tokens attribute)
                        self.total_tokens += int(getattr(token_usage, "total_tokens", 0))
            except (ConnectionError, TimeoutError, OSError) as e:
                # Transient network/API errors — re-raise so the caller can retry or abort.
                # These indicate network issues, LLM API outages, etc. where proceeding makes no sense.
                logger.error("[Implement] Transient error during crew execution: %s", e)
                raise
            except Exception as e:
                # CrewAI may throw validation errors but staging dict is already populated
                # via write_code() side effects. Only tolerate these if staging has content.
                self.total_calls += 1
                if staging:
                    logger.warning("[Implement] Crew finished with error (staging has %d files): %s", len(staging), e)
                else:
                    logger.error("[Implement] Crew failed with 0 staged files: %s", e)
                    raise
        finally:
            uninstall_guardrails(tracker)

    def _execute_fix(
        self,
        plan: CodegenPlanInput,
        staging: dict[str, dict[str, Any]],
        build_errors: str,
        failed_files: list[str],
        dependency_order_paths: list[str],
        import_index,
        generation_order,
    ) -> None:
        """Execute fix task: developer corrects build errors."""
        import_tool = ImportIndexTool(
            repo_path=str(self.repo_path),
            facts_path=str(self.facts_path),
            import_index=import_index,
        )
        dependency_tool = DependencyLookupTool(generation_order=generation_order)
        task_source_tool = TaskSourceTool(task_input_dir=self.task_input_dir)

        developer_tools = [
            CodeReaderTool(repo_path=str(self.repo_path), staging=staging),
            CodeWriterTool(repo_path=str(self.repo_path), staging=staging),
            FactsQueryTool(facts_dir=str(self.facts_path.parent)),
            RAGQueryTool(),
            SymbolQueryTool(),
            import_tool,
            dependency_tool,
            task_source_tool,
            PlanReaderTool(plans_dir=self.plans_dir, facts_path=str(self.facts_path)),
        ]

        developer = create_agent("developer", developer_tools, get_phase5_mcps(), _VERBOSE)

        fix_desc, fix_expected, _ = fix_task(
            task_id=plan.task_id,
            build_errors=build_errors,
            failed_files=failed_files,
            dependency_order=dependency_order_paths,
        )

        task = Task(
            description=fix_desc,
            expected_output=fix_expected,
            agent=developer,
            human_input=False,
        )

        log_dir = self.output_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        crew = Crew(
            agents=[developer],
            tasks=[task],
            process=Process.sequential,
            verbose=_VERBOSE,
            memory=False,
            planning=False,
            max_rpm=_MAX_RPM,
            step_callback=step_callback,
            task_callback=task_callback,
            output_log_file=str(log_dir / f"{plan.task_id}_fix.json"),
            embedder=get_crew_embedder(),
        )

        tracker = None
        try:
            # Scale budget: at least 50, or 4 tool calls per file in the dependency order
            guardrail_budget = max(50, len(dependency_order_paths) * 4)
            tracker = install_guardrails(max_total=guardrail_budget)
            try:
                result = crew.kickoff(
                    inputs={
                        "task_id": plan.task_id,
                        "build_errors": build_errors,
                        "failed_files": failed_files,
                        "dependency_order": dependency_order_paths,
                    }
                )
                self.total_calls += 1
                token_usage = getattr(result, "token_usage", None)
                if token_usage is not None:
                    if isinstance(token_usage, dict):
                        self.total_tokens += int(token_usage.get("total_tokens", 0))
                    else:
                        # CrewAI UsageMetrics object (total_tokens attribute)
                        self.total_tokens += int(getattr(token_usage, "total_tokens", 0))
            except (ConnectionError, TimeoutError, OSError) as e:
                logger.error("[Implement] Transient error during fix crew: %s", e)
                raise
            except Exception as e:
                # Fix crew validation errors — staging should still have content from previous attempt
                logger.warning("[Implement] Fix crew finished with error (staging preserved): %s", e)
                self.total_calls += 1
        finally:
            uninstall_guardrails(tracker)

    # ── Public run (single task) ────────────────────────────────────────────

    # ── Cascade checkpoint helpers ───────────────────────────────────────────

    @staticmethod
    def _checkpoint_path() -> Path:
        return Path("knowledge/implement/.checkpoint_implement.json")

    def _load_cascade_checkpoint(self) -> set[str]:
        """Load completed task IDs from cascade checkpoint file."""
        p = self._checkpoint_path()
        if not p.exists():
            return set()
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return set(data.get("completed", []))
        except Exception:
            return set()

    def _save_cascade_checkpoint(self, task_id: str, completed: set[str]) -> None:
        """Persist completed task ID to cascade checkpoint (atomic write)."""
        completed.add(task_id)
        p = self._checkpoint_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps({"completed": sorted(completed)}, indent=2),
            encoding="utf-8",
        )

    def run(
        self,
        plan: CodegenPlanInput,
        shared_baseline_cache: dict[str, dict] | None = None,
        shared_import_index: ImportIndex | None = None,
    ) -> tuple[list[GeneratedFile], BuildVerificationResult, Any]:
        """Run the full implement flow for a single plan with build-fix loop.

        1. Preflight: validate, build import index + dependency graph
        1b. Strategy pre-execution (deterministic, task-type-specific)
        2. Build-fix loop (max 3 attempts):
           - Crew: developer implements or fixes code
           - Import fixer: deterministic import correction
           - Build verification: deterministic subprocess
           - If build fails: format errors, loop back with fix task
        3. Strategy verification enrichment (error clusters, deprecation warnings)

        Args:
            plan: Parsed plan input for this task.
            shared_baseline_cache: Optional dict shared across cascade tasks (BUG-Y5).
                When provided, baseline build results are reused across tasks on the
                same containers — avoids redundant baseline builds per cascade task.
            shared_import_index: Optional ImportIndex built once before the cascade
                loop (BUG-Y6). When provided, preflight skips rebuilding the index
                — avoids N full source-tree scans for N cascade tasks.

        Returns:
            (generated_files, build_result, rich_report)
        """
        logger.info("[Implement] Starting single-agent crew with build-fix loop for task %s", plan.task_id)
        start_time = time.time()

        # ── 1. Preflight ────────────────────────────────────────────────────
        # Pass shared_import_index so preflight skips rebuild when already available.
        preflight = PreflightValidator(
            repo_path=str(self.repo_path),
            facts_path=str(self.facts_path),
        )
        preflight_result, import_index = preflight.run(plan, import_index=shared_import_index)
        if not preflight_result.ok:
            raise ValueError("Preflight failed: " + "; ".join(preflight_result.errors))

        dependency_builder = DependencyGraphBuilder(facts_path=str(self.facts_path))
        generation_order = dependency_builder.run(plan.affected_components, import_index)
        dependency_order_paths = [e.file_path for e in generation_order.ordered_files]

        staging: dict[str, dict[str, Any]] = {}
        build_result = BuildVerificationResult(skipped=True, skip_reason="No attempts made")
        # BUG-Y5 fix: use shared baseline cache when provided by cascade, otherwise fresh.
        # The baseline build for a container cannot change between cascade tasks on the same
        # session, so sharing avoids N x containers redundant baseline builds.
        baseline_cache: dict[str, dict] = shared_baseline_cache if shared_baseline_cache is not None else {}

        # ── 1b. Strategy: enrich plan + pre-execution (deterministic) ────
        from .strategies import get_strategy

        strategy = get_strategy(plan.task_type)

        facts = self._load_facts()
        plan_enrichment = strategy.enrich_plan(plan.model_dump(), facts)
        if plan_enrichment.warnings:
            logger.warning(
                "[Implement] Plan enrichment warnings: %s",
                "; ".join(plan_enrichment.warnings),
            )
        if plan_enrichment.additional_context:
            logger.info(
                "[Implement] Plan enrichment context keys: %s",
                list(plan_enrichment.additional_context.keys()),
            )
            # H1 fix: Abort early if strategy declares the plan infeasible
            if not plan_enrichment.additional_context.get("is_feasible", True):
                raise ValueError(
                    "Strategy declared plan infeasible: " + "; ".join(plan_enrichment.warnings)
                )

        det_result = strategy.pre_execute(plan, staging, str(self.repo_path), self.dry_run)
        if det_result.steps:
            logger.info(
                "[Implement] Pre-execution: %d steps, %d files, %d errors",
                len(det_result.steps),
                det_result.total_files_modified,
                len(det_result.errors),
            )
        # H2 fix: Surface pre-execution errors so they're visible
        if det_result.errors:
            logger.warning(
                "[Implement] Pre-execution errors (continuing with LLM): %s",
                "; ".join(det_result.errors),
            )

        # ── 2. Build-fix loop ───────────────────────────────────────────────
        raw_build_outputs: list[str] = []
        for attempt in range(1, MAX_BUILD_RETRIES + 1):
            logger.info("[Implement] Build-fix attempt %d/%d", attempt, MAX_BUILD_RETRIES)

            # 2a. Crew execution (implement or fix)
            if attempt == 1:
                self._execute_implement(plan, staging, dependency_order_paths, import_index, generation_order)
                # M5 fix: If the crew produced 0 files, skip build verification entirely.
                # Running builds on unchanged code wastes time and gives a misleading "build passed".
                if not staging:
                    logger.error("[Implement] Crew produced 0 staged files — aborting build-fix loop")
                    break
            else:
                build_errors = self._format_build_errors(build_result)
                failed_files = self._extract_failed_files(build_result)
                self._execute_fix(
                    plan, staging, build_errors, failed_files, dependency_order_paths, import_index, generation_order
                )

            generated_files = self._staging_to_generated_files(staging)

            # 2b. Import fixer (deterministic)
            fixer = ImportFixer()
            generated_files = fixer.run(generated_files, import_index)

            # Sync staging with import-fixed content
            for gf in generated_files:
                if gf.file_path in staging:
                    staging[gf.file_path]["content"] = gf.content

            # 2c. Build verification (deterministic subprocess)
            build_result = self._verify_builds(plan, staging, baseline_cache)

            # Collect raw build outputs for strategy verification enrichment
            for cr in build_result.container_results:
                if cr.raw_output:
                    raw_build_outputs.append(cr.raw_output)

            # 2d. Exit if build passed or skipped
            if build_result.all_passed or build_result.skipped:
                logger.info("[Implement] Build passed on attempt %d", attempt)
                break

            if attempt < MAX_BUILD_RETRIES:
                logger.warning("[Implement] Build failed on attempt %d, retrying with fix task", attempt)
            else:
                logger.warning("[Implement] Build failed after %d attempts, exiting loop", MAX_BUILD_RETRIES)

        # ── 3. Strategy: verification enrichment ─────────────────────────
        rich_report = strategy.enrich_verification(
            build_result,
            staging,
            plan,
            raw_build_outputs,
            det_result,
        )
        if rich_report.error_clusters:
            logger.info(
                "[Implement] Report: %d error clusters, %d deprecations",
                len(rich_report.error_clusters),
                len(rich_report.deprecation_warnings),
            )

        duration = time.time() - start_time
        logger.info(
            "[Implement] Crew complete in %.1fs | files=%d | build_passed=%s | tokens=%d",
            duration,
            len(generated_files),
            build_result.all_passed,
            self.total_tokens,
        )

        return generated_files, build_result, rich_report

    # ── Orchestrator-compatible kickoff ─────────────────────────────────────

    def kickoff(self, inputs: dict[str, Any] | None = None) -> dict[str, Any]:
        """Orchestrator-compatible kickoff interface.

        Supports two modes:
        1. Single task: inputs contains 'plan' (CodegenPlanInput)
        2. Multi-task cascade: inputs contains 'previous_results' from plan phase

        Returns dict with status, phase, metrics.
        """
        if not inputs:
            raise ValueError("kickoff requires inputs")

        # Single-task mode (plan already parsed)
        if "plan" in inputs:
            plan = inputs["plan"]
            if not isinstance(plan, CodegenPlanInput):
                raise ValueError("kickoff input 'plan' must be CodegenPlanInput")

            task_start = time.time()
            generated, build, rich = self.run(plan=plan)
            duration = time.time() - task_start

            writer = OutputWriter(
                repo_path=str(self.repo_path),
                report_dir=str(self.output_dir),
                dry_run=self.dry_run,
            )
            degradation_reasons = self._compute_degradations(generated, None, build)
            report = writer.run(
                task_id=plan.task_id,
                generated_files=generated,
                validation=None,
                duration_seconds=duration,
                llm_calls=self.total_calls,
                total_tokens=self.total_tokens,
                build_verification=build,
                degradation_reasons=degradation_reasons,
                rich_verification=rich.to_dict() if rich else None,
            )
            return {
                "status": report.status,
                "phase": "implement",
                "generated_files": len(generated),
                "build_passed": build.all_passed,
                "build_failed_containers": build.total_containers_failed,
                "branch_name": report.branch_name,
                "rich_verification": rich.to_dict() if rich else None,
            }

        # Multi-task cascade mode (reads plan files from disk)
        return self._run_cascade(inputs)

    def _run_cascade(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Process all plan files as a cascade on a single integration branch."""
        start_time = time.time()

        plan_files = self._resolve_plan_files(inputs)
        if not plan_files:
            return {
                "status": "skipped",
                "phase": "implement",
                "message": "No plan files found",
                "reports": [],
            }

        n = len(plan_files)
        logger.info("=" * 80)
        logger.info("[Implement] Cascade mode: %d plans on single integration branch", n)
        logger.info("=" * 80)

        writer = OutputWriter(
            repo_path=str(self.repo_path),
            report_dir=str(self.output_dir),
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

        reports = []
        succeeded = 0
        failed = 0
        completed_task_ids: list[str] = []

        # R3: Load cascade checkpoint — skip already-completed tasks on resume
        cascade_completed = self._load_cascade_checkpoint()
        if cascade_completed:
            logger.info(
                "[Implement] Cascade checkpoint: %d task(s) already done: %s",
                len(cascade_completed),
                sorted(cascade_completed),
            )

        # BUG-Y5: single baseline cache shared across all cascade tasks
        shared_baseline_cache: dict[str, dict] = {}

        # BUG-Y6: build ImportIndex ONCE before the task loop.
        # Each call to run() previously triggered a full source-tree scan inside
        # PreflightValidator — for 10 cascade tasks that is 10 x 3-10s of I/O.
        # Passing the pre-built index lets preflight skip the rebuild entirely.
        shared_import_index: ImportIndex | None = None
        try:
            shared_import_index = ImportIndexBuilder(
                repo_path=str(self.repo_path),
                facts_path=str(self.facts_path),
            ).run()
            logger.info(
                "[Implement] Shared ImportIndex built: %d symbols — reusing across %d cascade tasks",
                shared_import_index.total_symbols,
                n,
            )
        except Exception as idx_err:
            logger.warning(
                "[Implement] Could not build shared ImportIndex: %s — will build per-task",
                idx_err,
            )

        plan_reader = PlanReader(
            plans_dir=self.plans_dir,
            facts_path=str(self.facts_path),
        )

        for i, plan_file in enumerate(plan_files, 1):
            task_id = plan_file.stem.removesuffix("_plan")
            logger.info("\n[Implement] === Cascade %d/%d: %s ===", i, n, task_id)

            # R3: Skip tasks already committed — but verify output exists on disk
            if task_id in cascade_completed:
                output_file = self.output_dir / f"{task_id}_implement_report.json"
                if output_file.exists():
                    logger.info("[Implement] Skipping %s (cascade checkpoint)", task_id)
                    completed_task_ids.append(task_id)
                    succeeded += 1
                    continue
                else:
                    logger.warning(
                        "[Implement] Checkpoint says %s done but output missing — re-running",
                        task_id,
                    )
                    cascade_completed.discard(task_id)

            try:
                # Capture per-task baseline metrics so reports reflect this task only
                task_start = time.time()
                calls_before = self.total_calls
                tokens_before = self.total_tokens

                plan_input = plan_reader.run(task_id=task_id, plan_path=str(plan_file))
                generated, build, rich = self.run(
                    plan=plan_input,
                    shared_baseline_cache=shared_baseline_cache,
                    shared_import_index=shared_import_index,
                )

                task_duration = time.time() - task_start
                task_calls = self.total_calls - calls_before
                task_tokens = self.total_tokens - tokens_before

                degradation_reasons = self._compute_degradations(generated, None, build)
                report = writer.cascade_write_and_commit(
                    task_id=task_id,
                    generated_files=generated,
                    validation=None,
                    cascade_branch=cascade_branch or "",
                    cascade_position=i,
                    cascade_total=n,
                    prior_task_ids=list(completed_task_ids),
                    duration_seconds=task_duration,
                    llm_calls=task_calls,
                    total_tokens=task_tokens,
                    build_verification=build,
                    degradation_reasons=degradation_reasons,
                    rich_verification=rich.to_dict() if rich else None,
                )
                reports.append(report.model_dump())
                if report.status in ("success", "partial", "dry_run"):
                    succeeded += 1
                    completed_task_ids.append(task_id)
                    # R3: Persist checkpoint so a re-run skips this task
                    self._save_cascade_checkpoint(task_id, cascade_completed)
                else:
                    failed += 1
            except Exception as e:
                logger.error("[Implement] Cascade task %s failed: %s", task_id, e)
                failed += 1
                reports.append({"task_id": task_id, "status": "failed", "error": str(e)})

        writer.teardown_cascade()
        total_duration = time.time() - start_time

        logger.info("=" * 80)
        logger.info(
            "[Implement] Cascade complete: %d succeeded, %d failed, %.2fs",
            succeeded,
            failed,
            total_duration,
        )
        logger.info("=" * 80)

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

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _resolve_plan_files(self, inputs: dict[str, Any]) -> list[Path]:
        """Find plan files from orchestrator inputs or disk."""
        # Extract task_id filter from config (passed via --task-id CLI arg)
        config = inputs.get("config") or {}
        task_id_filter = config.get("task_id") if isinstance(config, dict) else None

        # Try orchestrator-provided file list first
        previous_results = inputs.get("previous_results")
        if isinstance(previous_results, dict):
            plan_result = previous_results.get("plan")
            if isinstance(plan_result, dict):
                output_files = plan_result.get("output_files")
                if isinstance(output_files, list):
                    plan_files = []
                    for path_str in output_files:
                        path = Path(str(path_str))
                        if path.name.endswith("_plan.json") and path.exists():
                            plan_files.append(path)
                    if plan_files:
                        result = sorted({str(p): p for p in plan_files}.values(), key=lambda p: str(p))
                        if task_id_filter:
                            result = [f for f in result if f.stem == f"{task_id_filter}_plan"]
                        return result

        # Fall back to scanning plans_dir
        plans_dir = Path(self.plans_dir)
        if plans_dir.exists():
            all_files = sorted(plans_dir.glob("*_plan.json"))
            if task_id_filter:
                all_files = [f for f in all_files if f.stem == f"{task_id_filter}_plan"]
                logger.info("[Implement] --task-id=%s → filtered to %d plan(s)", task_id_filter, len(all_files))
            return all_files

        return []

    @staticmethod
    def _compute_degradations(
        generated_files: list[GeneratedFile],
        validation,
        build_result: BuildVerificationResult | None,
    ) -> list[str]:
        reasons: list[str] = []
        if validation and getattr(validation, "total_invalid", 0) > 0:
            reasons.append(f"{validation.total_invalid} file(s) failed validation")

        if build_result and not build_result.skipped and not build_result.all_passed:
            reasons.append(f"build failed for {build_result.total_containers_failed} container(s)")

        return reasons
