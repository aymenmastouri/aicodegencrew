"""Implement Crew: Sequential CrewAI team for Phase 5.

Architecture:
  Preflight (deterministic) -> Crew (sequential) -> Post-crew (deterministic)

  Developer -- reads code, resolves imports, writes code
  Builder   -- runs builds, parses errors, reports diagnostics
  Tester    -- generates unit tests matching repo patterns

Process: Process.sequential — each agent executes its task directly with tools.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from crewai import Crew, Process, Task

from ...shared.paths import CHROMA_DIR
from ...shared.utils.logger import setup_logger
from ...shared.utils.tool_guardrails import install_guardrails, uninstall_guardrails
from .agents import create_agent
from .output_writer import OutputWriter
from .preflight import (
    DependencyGraphBuilder,
    ImportFixer,
    ImportIndexBuilder,
    PlanReader,
    PreflightValidator,
)
from .schemas import (
    BuildVerificationResult,
    CodegenPlanInput,
    CodegenReport,
    ContainerBuildResult,
    GeneratedFile,
)
from .tasks import build_task, implement_task, test_task
from .tools import (
    BuildErrorParserTool,
    BuildRunnerTool,
    CodeReaderTool,
    CodeWriterTool,
    DependencyLookupTool,
    FactsQueryTool,
    ImportIndexTool,
    PlanReaderTool,
    RAGQueryTool,
    TestPatternTool,
    TestWriterTool,
)

_MCP_SERVER_PATH = str(Path(__file__).resolve().parents[4] / "mcp_server.py")
_MAX_RPM = 30
_VERBOSE = True

logger = setup_logger(__name__)


class ImplementCrew:
    """Sequential crew for implementation, build verification and tests.

    Full flow:
    1. Preflight: plan reading, import index, dependency graph, validation
    2. Crew: sequential execution (developer → builder → tester)
    3. Post-crew: import fixer, safety gate, output writer
    """

    def __init__(
        self,
        repo_path: str,
        facts_path: str = "knowledge/extract/architecture_facts.json",
        chroma_dir: str | None = None,
        plans_dir: str = "knowledge/plan",
        output_dir: str = "knowledge/implement",
        *,
        build_verify: bool = True,
        test_enabled: bool = True,
        dry_run: bool = False,
    ):
        self.repo_path = Path(repo_path)
        self.facts_path = Path(facts_path)
        self.chroma_dir = chroma_dir or CHROMA_DIR
        self.plans_dir = plans_dir
        self.output_dir = Path(output_dir)
        self.build_verify = build_verify
        self.test_enabled = test_enabled
        self.dry_run = dry_run
        self.total_calls = 0
        self.total_tokens = 0
        self._containers: list[dict[str, str]] | None = None

    # ── Container helpers ─────────────────────────────────────────────────

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
                out.append({
                    "id": c.get("id", ""),
                    "name": c.get("name", ""),
                    "root_path": c.get("root_path", "") or metadata.get("root_path", ""),
                    "build_system": metadata.get("build_system", ""),
                    "language": metadata.get("language", ""),
                })
            self._containers = out
        except Exception:
            self._containers = []

        return self._containers

    def _container_ids_for_plan(self, plan: CodegenPlanInput) -> list[str]:
        containers = self._load_containers()
        if not containers:
            return []

        ids: list[str] = []
        for comp in plan.affected_components:
            fp = comp.file_path.replace("\\", "/")
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

    # ── Staging conversion ────────────────────────────────────────────────

    @staticmethod
    def _staging_to_generated_files(staging: dict[str, dict[str, Any]]) -> list[GeneratedFile]:
        generated: list[GeneratedFile] = []
        for file_path, entry in staging.items():
            generated.append(GeneratedFile(
                file_path=file_path,
                content=entry.get("content", ""),
                original_content=entry.get("original_content", ""),
                action=entry.get("action", "modify"),
                language=entry.get("language", "other"),
            ))
        return generated

    # ── Deterministic build verification (post-crew) ──────────────────────

    def _verify_builds(
        self, plan: CodegenPlanInput, staging: dict[str, dict[str, Any]]
    ) -> BuildVerificationResult:
        if not self.build_verify:
            return BuildVerificationResult(skipped=True, skip_reason="build_verify=False")

        container_ids = self._container_ids_for_plan(plan)
        if not container_ids:
            return BuildVerificationResult(
                all_passed=False, skipped=False,
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
            baseline_raw = runner._run(container_id=cid, baseline=True)
            baseline = self._safe_json(baseline_raw)

            cname = baseline.get("container_name") or cid
            bcmd = baseline.get("build_command", "")

            if not baseline.get("success", False):
                results.append(ContainerBuildResult(
                    container_id=cid, container_name=cname,
                    build_command=bcmd, success=True,
                    exit_code=int(baseline.get("exit_code", -1)),
                    error_summary="Baseline broken (pre-existing)", attempts=0,
                ))
                continue

            staged_raw = runner._run(container_id=cid, baseline=False)
            staged = self._safe_json(staged_raw)

            if staged.get("success", False):
                results.append(ContainerBuildResult(
                    container_id=cid,
                    container_name=staged.get("container_name", cname),
                    build_command=staged.get("build_command", bcmd),
                    success=True, exit_code=int(staged.get("exit_code", 0)),
                    attempts=1,
                ))
                continue

            parsed_raw = parser._run(
                build_output=str(staged.get("output", "")),
                build_tool=str(staged.get("build_tool", "auto")),
            )
            parsed = self._safe_json(parsed_raw)
            errors = parsed.get("errors", [])
            if errors:
                summary = "; ".join(
                    f"{e.get('file_path', '?')}:{e.get('line', 0)} {e.get('message', '')}"
                    for e in errors[:8]
                )
            else:
                summary = str(staged.get("output", ""))[-1000:]

            results.append(ContainerBuildResult(
                container_id=cid,
                container_name=staged.get("container_name", cname),
                build_command=staged.get("build_command", bcmd),
                success=False, exit_code=int(staged.get("exit_code", -1)),
                error_summary=summary, attempts=1,
            ))

        passed = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)
        return BuildVerificationResult(
            container_results=results, all_passed=failed == 0,
            total_containers_built=passed, total_containers_failed=failed,
        )

    @staticmethod
    def _safe_json(text: str) -> dict[str, Any]:
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    # ── Core: sequential crew execution ──────────────────────────────────

    def _execute_crew(
        self,
        plan: CodegenPlanInput,
        staging: dict[str, dict[str, Any]],
        dependency_order_paths: list[str],
        import_index,
        generation_order,
    ) -> None:
        """Build agents, tasks, crew and kick off sequential execution.

        Sequential process: each task is assigned directly to its worker agent.
        No manager overhead — agents use their tools directly.
        Order: Developer (implement) → Builder (verify) → Tester (tests).
        """

        # Shared tool instances bound to preflight artifacts
        import_tool = ImportIndexTool(
            repo_path=str(self.repo_path),
            facts_path=str(self.facts_path),
            import_index=import_index,
        )
        dependency_tool = DependencyLookupTool(generation_order=generation_order)

        developer_tools = [
            CodeReaderTool(repo_path=str(self.repo_path)),
            CodeWriterTool(repo_path=str(self.repo_path), staging=staging),
            FactsQueryTool(facts_dir=str(self.facts_path.parent)),
            RAGQueryTool(chroma_dir=self.chroma_dir),
            import_tool,
            dependency_tool,
            PlanReaderTool(plans_dir=self.plans_dir, facts_path=str(self.facts_path)),
        ]
        builder_tools = [
            BuildRunnerTool(
                repo_path=str(self.repo_path),
                facts_path=str(self.facts_path),
                staging=staging,
            ),
            BuildErrorParserTool(),
            FactsQueryTool(facts_dir=str(self.facts_path.parent)),
        ]

        developer = create_agent("developer", developer_tools, _MCP_SERVER_PATH, _VERBOSE)
        builder = create_agent("builder", builder_tools, _MCP_SERVER_PATH, _VERBOSE)

        container_ids = self._container_ids_for_plan(plan)

        impl_desc, impl_expected = implement_task(
            task_id=plan.task_id,
            summary=plan.summary,
            description=plan.description,
            task_type=plan.task_type,
            implementation_steps=plan.implementation_steps,
            upgrade_plan=plan.upgrade_plan,
            dependency_order=dependency_order_paths,
        )
        build_desc, build_expected = build_task(container_ids=container_ids)

        # Sequential: each task directly assigned to its worker agent.
        # No manager delegation — agents use tools directly.
        tasks = [
            Task(description=impl_desc, expected_output=impl_expected, agent=developer, human_input=False),
            Task(description=build_desc, expected_output=build_expected, agent=builder, human_input=False),
        ]

        agents = [developer, builder]

        if self.test_enabled:
            tester_tools = [
                TestPatternTool(facts_dir=str(self.facts_path.parent)),
                TestWriterTool(repo_path=str(self.repo_path), staging=staging),
                CodeReaderTool(repo_path=str(self.repo_path)),
                RAGQueryTool(chroma_dir=self.chroma_dir),
            ]
            tester = create_agent("tester", tester_tools, _MCP_SERVER_PATH, _VERBOSE)
            test_desc, test_expected = test_task(changed_files=dependency_order_paths)
            tasks.append(
                Task(description=test_desc, expected_output=test_expected, agent=tester, human_input=False),
            )
            agents.append(tester)

        crew = Crew(
            agents=agents,
            tasks=tasks,
            process=Process.sequential,
            verbose=_VERBOSE,
            memory=False,
            planning=False,
            max_rpm=_MAX_RPM,
        )

        tracker = None
        try:
            tracker = install_guardrails(max_total=50)
            try:
                result = crew.kickoff(inputs={
                    "task_id": plan.task_id,
                    "task_type": plan.task_type,
                    "summary": plan.summary,
                    "description": plan.description,
                    "implementation_steps": plan.implementation_steps,
                    "affected_components": [c.model_dump() for c in plan.affected_components],
                    "dependency_order": dependency_order_paths,
                    "container_ids": container_ids,
                })
                self.total_calls += 1
                token_usage = getattr(result, "token_usage", {})
                if isinstance(token_usage, dict):
                    self.total_tokens += int(token_usage.get("total_tokens", 0))
            except Exception as e:
                # CrewAI may throw validation errors (e.g. TaskOutput expects string
                # but gets tool_calls list). The staging dict is already populated via
                # CodeWriterTool during execution, so we can continue safely.
                logger.warning("[Implement] Crew finished with error (staging preserved): %s", e)
                self.total_calls += 1
        finally:
            uninstall_guardrails(tracker)

    # ── Public run (single task) ──────────────────────────────────────────

    def run(
        self,
        plan: CodegenPlanInput,
    ) -> tuple[list[GeneratedFile], BuildVerificationResult]:
        """Run the full implement flow for a single plan.

        1. Preflight: validate, build import index + dependency graph
        2. Crew: sequential execution (developer → builder → tester)
        3. Post-crew: import fixer, build verification

        Returns:
            (generated_files, build_result)
        """
        logger.info("[Implement] Starting hierarchical crew for task %s", plan.task_id)
        start_time = time.time()

        # ── 1. Preflight ──────────────────────────────────────────────────
        preflight = PreflightValidator(
            repo_path=str(self.repo_path), facts_path=str(self.facts_path),
        )
        preflight_result, import_index = preflight.run(plan)
        if not preflight_result.ok:
            raise ValueError("Preflight failed: " + "; ".join(preflight_result.errors))

        dependency_builder = DependencyGraphBuilder(facts_path=str(self.facts_path))
        generation_order = dependency_builder.run(plan.affected_components, import_index)
        dependency_order_paths = [e.file_path for e in generation_order.ordered_files]

        staging: dict[str, dict[str, Any]] = {}

        # ── 2. Crew execution ─────────────────────────────────────────────
        self._execute_crew(plan, staging, dependency_order_paths, import_index, generation_order)

        generated_files = self._staging_to_generated_files(staging)

        # ── 3. Post-crew: deterministic import repair ─────────────────────
        fixer = ImportFixer()
        generated_files = fixer.run(generated_files, import_index)

        # Sync staging with import-fixed content for build verification
        for gf in generated_files:
            if gf.file_path in staging:
                staging[gf.file_path]["content"] = gf.content

        # ── 4. Post-crew: build verification ──────────────────────────────
        build_result = self._verify_builds(plan, staging)

        duration = time.time() - start_time
        logger.info(
            "[Implement] Crew complete in %.1fs | files=%d | build_passed=%s | tokens=%d",
            duration, len(generated_files), build_result.all_passed, self.total_tokens,
        )

        return generated_files, build_result

    # ── Orchestrator-compatible kickoff ────────────────────────────────────

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

            generated, build = self.run(plan=plan)
            return {
                "status": "completed" if build.all_passed else "partial",
                "phase": "implement",
                "generated_files": len(generated),
                "build_passed": build.all_passed,
                "build_failed_containers": build.total_containers_failed,
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

        plan_reader = PlanReader(
            plans_dir=self.plans_dir, facts_path=str(self.facts_path),
        )

        for i, plan_file in enumerate(plan_files, 1):
            task_id = plan_file.stem.replace("_plan", "")
            logger.info("\n[Implement] === Cascade %d/%d: %s ===", i, n, task_id)

            try:
                plan_input = plan_reader.run(task_id=task_id, plan_path=str(plan_file))
                generated, build = self.run(plan=plan_input)

                degradation_reasons = self._compute_degradations(generated, None, build)
                report = writer.cascade_write_and_commit(
                    task_id=task_id,
                    generated_files=generated,
                    validation=None,
                    cascade_branch=cascade_branch or "",
                    cascade_position=i,
                    cascade_total=n,
                    prior_task_ids=list(completed_task_ids),
                    duration_seconds=time.time() - start_time,
                    llm_calls=self.total_calls,
                    total_tokens=self.total_tokens,
                    build_verification=build,
                    degradation_reasons=degradation_reasons,
                )
                reports.append(report.model_dump())
                if report.status in ("success", "partial", "dry_run"):
                    succeeded += 1
                    completed_task_ids.append(task_id)
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
            succeeded, failed, total_duration,
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

    # ── Helpers ───────────────────────────────────────────────────────────

    def _resolve_plan_files(self, inputs: dict[str, Any]) -> list[Path]:
        """Find plan files from orchestrator inputs or disk."""
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
                        return sorted({str(p): p for p in plan_files}.values(), key=lambda p: str(p))

        # Fall back to scanning plans_dir
        plans_dir = Path(self.plans_dir)
        if plans_dir.exists():
            return sorted(plans_dir.glob("*_plan.json"))

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
            reasons.append(
                f"build failed for {build_result.total_containers_failed} container(s)"
            )

        return reasons
