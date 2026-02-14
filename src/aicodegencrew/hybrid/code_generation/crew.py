"""
Implement Crew - Main Orchestration
====================================
Mini-Crew pattern for code generation:
  A. Code Generation  (Senior Dev)          — 1 task per container
  B. Build + Heal loop (DevOps + Senior Dev) — verify+heal, max 3 iters
  C. Test Generation   (Tester)             — 1 task per container

Follows the same patterns as ArchitectureAnalysisCrew:
- Fresh LLM per agent
- Checkpoint/resume
- Tool guardrails (budget=50)
- MCP server integration
- Process.sequential

Execution flow:
  run(plan, context)
    -> _group_files_by_container(context)
    -> For each container:
        -> Mini-Crew A: _run_code_generation()
        -> Mini-Crew B: _run_build_heal()    (Python loop, max 3)
        -> Mini-Crew C: _run_test_generation()
    -> _staging_to_generated_files(staging)
    -> return (generated_files, BuildVerificationResult)
"""

import json
import re
import time
from pathlib import Path
from typing import Any

from crewai import LLM, Agent, Crew, Process, Task
from crewai.mcp import MCPServerStdio

from .schemas import (
    BuildVerificationResult,
    CodegenPlanInput,
    CollectedContext,
    ContainerBuildResult,
    GeneratedFile,
)
from ...shared.paths import CHROMA_DIR
from ...shared.utils.llm_factory import create_llm
from ...shared.utils.logger import setup_logger
from ...shared.utils.tool_guardrails import install_guardrails, uninstall_guardrails
from .agents import AGENT_CONFIGS
from .tasks import (
    build_heal_task,
    build_verify_task,
    code_generation_task,
    test_generation_task,
)
from .tools import (
    BuildErrorParserTool,
    BuildRunnerTool,
    CodeReaderTool,
    CodeWriterTool,
    FactsQueryTool,
    RAGQueryTool,
    TestPatternTool,
    TestWriterTool,
)

# MCP server script path (project root)
_MCP_SERVER_PATH = str(Path(__file__).resolve().parents[4] / "mcp_server.py")

# Internal constants (no env vars needed)
_MAX_RETRIES = 2       # transient error retries per mini-crew
_MAX_RPM = 30          # CrewAI rate-limit per crew
_VERBOSE = True        # CrewAI verbose logging

logger = setup_logger(__name__)


class ImplementCrew:
    """
    Implement Crew — Code Generation via CrewAI agents.

    Mini-Crew layout per container:
      A. code_generation  (senior_developer)  -> 1 task
      B. build_heal       (devops + dev)      -> verify+heal loop (max 3)
      C. test_generation  (tester)            -> 1 task
    """

    def __init__(
        self,
        repo_path: str,
        facts_path: str = "knowledge/extract/architecture_facts.json",
        chroma_dir: str | None = None,
        output_dir: str = "knowledge/implement",
        *,
        resume: bool = False,
        build_verify: bool = True,
        test_enabled: bool = True,
    ):
        """Initialize crew with paths.

        Args:
            repo_path: Absolute path to the target repository.
            facts_path: Path to architecture_facts.json.
            chroma_dir: ChromaDB directory for RAG queries.
            output_dir: Output directory for checkpoints and reports.
            resume: If True, skip already-completed mini-crews (checkpoint).
            build_verify: If True, run build+heal loop after code generation.
            test_enabled: If True, run test generation after build.
        """
        self.repo_path = Path(repo_path)
        self.facts_path = Path(facts_path)
        self.chroma_dir = chroma_dir or CHROMA_DIR
        self.output_dir = Path(output_dir)
        self._checkpoint_file = self.output_dir / ".checkpoint_implement.json"
        self._mcp_server_path = _MCP_SERVER_PATH

        # Behavior flags (constructor params, not env vars)
        self.resume = resume
        self.build_verify = build_verify
        self.test_enabled = test_enabled

        # Metrics (exposed for pipeline)
        self.total_calls = 0
        self.total_tokens = 0

        # Cache containers from facts (loaded lazily)
        self._containers: list[dict] | None = None

    # =========================================================================
    # CONTAINER DISCOVERY
    # =========================================================================

    def _load_containers(self) -> list[dict]:
        """Load container configs from architecture_facts.json."""
        if self._containers is not None:
            return self._containers

        if not self.facts_path.exists():
            logger.warning(f"[Implement] Facts file not found: {self.facts_path}")
            self._containers = []
            return self._containers

        try:
            data = json.loads(self.facts_path.read_text(encoding="utf-8"))
            raw_containers = data.get("containers", [])
            self._containers = []
            for c in raw_containers:
                metadata = c.get("metadata", {})
                self._containers.append({
                    "id": c.get("id", ""),
                    "name": c.get("name", ""),
                    "root_path": metadata.get("root_path", ""),
                    "build_system": metadata.get("build_system", ""),
                    "language": metadata.get("language", ""),
                })
            logger.info(
                f"[Implement] Loaded {len(self._containers)} containers from facts"
            )
        except Exception as e:
            logger.error(f"[Implement] Failed to load containers: {e}")
            self._containers = []

        return self._containers

    def _group_files_by_container(
        self, context: CollectedContext
    ) -> dict[str, list]:
        """Group FileContexts by container based on root_path matching.

        Returns:
            Dict mapping container_id -> list[FileContext].
            Files that don't match any container go under "unmatched".
        """
        containers = self._load_containers()
        groups: dict[str, list] = {}

        # Sort by root_path length (longest first) for most-specific match
        sorted_containers = sorted(
            containers, key=lambda c: len(c.get("root_path", "")), reverse=True
        )

        for fc in context.file_contexts:
            normalized = fc.file_path.replace("\\", "/")
            matched = False
            for container in sorted_containers:
                root = container.get("root_path", "").replace("\\", "/")
                if root and normalized.startswith(root):
                    cid = container["id"]
                    groups.setdefault(cid, []).append(fc)
                    matched = True
                    break
            if not matched:
                groups.setdefault("unmatched", []).append(fc)

        return groups

    def _get_container_by_id(self, container_id: str) -> dict:
        """Get container info dict by ID."""
        for c in self._load_containers():
            if c["id"] == container_id:
                return c
        return {
            "id": container_id,
            "name": container_id,
            "root_path": "",
            "build_system": "",
            "language": "",
        }

    # =========================================================================
    # LLM FACTORY (identical to ArchitectureAnalysisCrew)
    # =========================================================================

    @staticmethod
    def _create_llm() -> LLM:
        """Create LLM instance from environment variables."""
        return create_llm()

    # =========================================================================
    # AGENT FACTORY
    # =========================================================================

    def _create_agent(self, agent_key: str, tools: list) -> Agent:
        """Create a fresh agent with fresh LLM context."""
        config = AGENT_CONFIGS[agent_key]
        return Agent(
            role=config["role"],
            goal=config["goal"],
            backstory=config["backstory"],
            llm=self._create_llm(),
            tools=tools,
            mcps=[
                MCPServerStdio(
                    command="python",
                    args=[self._mcp_server_path],
                    cache_tools_list=True,
                )
            ],
            verbose=_VERBOSE,
            max_iter=25,
            max_retry_limit=3,
            allow_delegation=False,
            respect_context_window=True,
        )

    # =========================================================================
    # TOOL FACTORIES (shared staging dict)
    # =========================================================================

    def _create_senior_dev_tools(self, staging: dict) -> list:
        """Create tools for the Senior Developer agent."""
        return [
            CodeReaderTool(repo_path=str(self.repo_path)),
            CodeWriterTool(repo_path=str(self.repo_path), staging=staging),
            FactsQueryTool(facts_dir=str(self.facts_path.parent)),
            RAGQueryTool(chroma_dir=self.chroma_dir),
        ]

    def _create_devops_tools(self, staging: dict) -> list:
        """Create tools for the DevOps agent."""
        return [
            BuildRunnerTool(
                repo_path=str(self.repo_path),
                facts_path=str(self.facts_path),
                staging=staging,
            ),
            BuildErrorParserTool(),
            FactsQueryTool(facts_dir=str(self.facts_path.parent)),
        ]

    def _create_tester_tools(self, staging: dict) -> list:
        """Create tools for the Tester agent."""
        return [
            TestPatternTool(facts_dir=str(self.facts_path.parent)),
            TestWriterTool(repo_path=str(self.repo_path), staging=staging),
            CodeReaderTool(repo_path=str(self.repo_path)),
            RAGQueryTool(chroma_dir=self.chroma_dir),
        ]

    # =========================================================================
    # MINI-CREW EXECUTION (follows ArchitectureAnalysisCrew pattern)
    # =========================================================================

    def _run_mini_crew(self, name: str, tasks: list[Task]) -> str:
        """Run a mini-crew with fresh context, retry on transient errors."""

        logger.info(
            f"[Implement] Starting Mini-Crew: {name} ({len(tasks)} tasks)"
        )
        start_time = time.time()

        for attempt in range(1, _MAX_RETRIES + 1):
            tracker = None
            try:
                # Collect unique agents from tasks
                agents = list({id(t.agent): t.agent for t in tasks}.values())
                crew = Crew(
                    agents=agents,
                    tasks=tasks,
                    process=Process.sequential,
                    verbose=_VERBOSE,
                    memory=False,
                    max_rpm=_MAX_RPM,
                    planning=False,
                )
                tracker = install_guardrails(max_total=50)
                result = crew.kickoff()
                duration = time.time() - start_time
                logger.info(
                    f"[Implement] Completed Mini-Crew: {name} ({duration:.1f}s)"
                )

                # Accumulate metrics
                tokens = getattr(result, "token_usage", {})
                crew_tokens = (
                    tokens.get("total_tokens", 0)
                    if isinstance(tokens, dict)
                    else 0
                )
                self.total_tokens += crew_tokens
                self.total_calls += 1

                try:
                    from ...shared.utils.logger import log_metric

                    log_metric(
                        "mini_crew_complete",
                        crew_type="Implement",
                        crew_name=name,
                        duration_seconds=round(duration, 1),
                        tasks=len(tasks),
                        attempts=attempt,
                        total_tokens=crew_tokens,
                    )
                except Exception:
                    pass

                self._save_checkpoint(name)
                return str(result)

            except (ConnectionError, TimeoutError, OSError) as e:
                if attempt < _MAX_RETRIES:
                    delay = 5 * (2 ** (attempt - 1))
                    logger.warning(
                        f"[Implement] {name}: Connection error "
                        f"(attempt {attempt}/{_MAX_RETRIES}), "
                        f"retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)
                    continue
                self._log_crew_failure(name, tasks, e, start_time)
                raise

            except Exception as e:
                self._log_crew_failure(name, tasks, e, start_time)
                raise

            finally:
                if tracker and tracker.calls:
                    try:
                        from ...shared.utils.logger import log_metric as _log_metric

                        _log_metric(
                            "guardrail_summary",
                            crew_name=name,
                            total_calls=len(tracker.calls),
                            unique_calls=len(set(tracker.calls)),
                        )
                    except Exception:
                        pass
                uninstall_guardrails(tracker)

        raise RuntimeError(f"Mini-crew {name} failed after {_MAX_RETRIES} attempts")

    def _log_crew_failure(
        self,
        name: str,
        tasks: list[Task],
        error: Exception,
        start_time: float,
    ) -> None:
        """Log failure metric and error details."""
        duration = time.time() - start_time
        error_type = type(error).__name__
        error_msg = str(error)[:500]
        logger.error(
            f"[Implement] Failed Mini-Crew: {name} "
            f"({duration:.1f}s, {error_type}): {error_msg}"
        )
        try:
            from ...shared.utils.logger import log_metric

            log_metric(
                "mini_crew_failed",
                crew_type="Implement",
                crew_name=name,
                duration_seconds=round(duration, 1),
                tasks=len(tasks),
                error_type=error_type,
                error=error_msg,
            )
        except Exception:
            pass

    # =========================================================================
    # CHECKPOINT (identical pattern to ArchitectureAnalysisCrew)
    # =========================================================================

    def _load_checkpoint(self) -> set[str]:
        """Load completed mini-crew names from checkpoint."""
        if not self._checkpoint_file.exists():
            return set()
        try:
            data = json.loads(self._checkpoint_file.read_text(encoding="utf-8"))
            completed = set(data.get("completed_crews", []))
            if completed:
                logger.info(
                    f"[Implement] Resuming: {len(completed)} crews already "
                    f"completed: {sorted(completed)}"
                )
            return completed
        except Exception:
            return set()

    def _save_checkpoint(self, crew_name: str):
        """Save completed mini-crew to checkpoint."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        completed = self._load_checkpoint()
        completed.add(crew_name)
        data = {"completed_crews": sorted(completed)}
        self._checkpoint_file.write_text(
            json.dumps(data, indent=2), encoding="utf-8"
        )
        logger.debug(f"[Implement] Checkpoint saved: {crew_name}")

    # =========================================================================
    # MINI-CREW A: CODE GENERATION
    # =========================================================================

    def _run_code_generation(
        self,
        container: dict,
        files: list,
        plan: CodegenPlanInput,
        staging: dict,
    ) -> str:
        """Run Mini-Crew A: Senior Developer generates code for one container."""
        crew_name = f"codegen_{container['name']}"
        completed = self._load_checkpoint()
        if self.resume and crew_name in completed:
            logger.info(f"[Implement] Skipping {crew_name} (already completed)")
            return "resumed — skipped"

        dev_tools = self._create_senior_dev_tools(staging)
        dev = self._create_agent("senior_developer", dev_tools)

        desc, expected = code_generation_task(container, plan, files)
        task = Task(
            description=desc,
            expected_output=expected,
            agent=dev,
            human_input=False,
        )

        return self._run_mini_crew(crew_name, [task])

    # =========================================================================
    # MINI-CREW B: BUILD + HEAL LOOP
    # =========================================================================

    def _run_build_heal(
        self,
        container: dict,
        plan: CodegenPlanInput,
        staging: dict,
    ) -> ContainerBuildResult:
        """Run Mini-Crew B: DevOps verifies, Senior Dev heals. Max N iterations.

        Each iteration:
          1. DevOps agent runs build verification (separate mini-crew)
          2. If build passes -> return success
          3. Senior Dev agent heals build errors (separate mini-crew)
          4. Loop back to step 1

        Returns:
            ContainerBuildResult with success status and attempt count.
        """
        build_max_retries = 3
        container_name = container["name"]
        container_id = container["id"]
        start_time = time.time()

        for attempt in range(1, build_max_retries + 1):
            # Step 1: DevOps runs build verification
            devops_tools = self._create_devops_tools(staging)
            devops = self._create_agent("devops_engineer", devops_tools)

            verify_desc, verify_expected = build_verify_task(
                container_name, container_id
            )
            verify = Task(
                description=verify_desc,
                expected_output=verify_expected,
                agent=devops,
                human_input=False,
            )

            verify_result = self._run_mini_crew(
                f"build_verify_{container_name}_{attempt}", [verify]
            )

            # Check if build passed
            if self._check_build_result(verify_result):
                duration = time.time() - start_time
                logger.info(
                    f"[Implement] Build PASSED for {container_name} "
                    f"(attempt {attempt})"
                )
                return ContainerBuildResult(
                    container_id=container_id,
                    container_name=container_name,
                    success=True,
                    exit_code=0,
                    attempts=attempt,
                    healed_files=(
                        list(staging.keys()) if attempt > 1 else []
                    ),
                    duration_seconds=round(duration, 1),
                )

            # Step 2: Senior Dev heals (only if more attempts remain)
            if attempt < build_max_retries:
                dev_tools = self._create_senior_dev_tools(staging)
                dev = self._create_agent("senior_developer", dev_tools)

                heal_desc, heal_expected = build_heal_task(
                    container, plan.task_id, verify_result
                )
                heal = Task(
                    description=heal_desc,
                    expected_output=heal_expected,
                    agent=dev,
                    human_input=False,
                )

                self._run_mini_crew(
                    f"build_heal_{container_name}_{attempt}", [heal]
                )
            else:
                logger.warning(
                    f"[Implement] Build FAILED for {container_name} "
                    f"after {build_max_retries} attempts"
                )

        duration = time.time() - start_time
        return ContainerBuildResult(
            container_id=container_id,
            container_name=container_name,
            success=False,
            exit_code=-1,
            error_summary=f"Build failed after {build_max_retries} attempts",
            attempts=build_max_retries,
            duration_seconds=round(duration, 1),
        )

    def _check_build_result(self, result_text: str) -> bool:
        """Heuristic parse of DevOps agent output to determine build success.

        Looks for explicit success/failure markers in the agent's natural
        language output. Defaults to False (triggers heal) if ambiguous.
        """
        text = result_text.lower()

        # Explicit baseline failure
        if "baseline_broken" in text and "true" in text:
            return False

        # Check for explicit success markers
        success_patterns = [
            r"build_passed\s*[:=]\s*true",
            r"success\s*[:=]\s*true",
            r"build\s+passed",
            r"build\s+successful",
            r"exit_code\s*[:=]\s*0",
        ]
        for pattern in success_patterns:
            if re.search(pattern, text):
                return True

        # Check for explicit failure markers
        failure_patterns = [
            r"build_passed\s*[:=]\s*false",
            r"success\s*[:=]\s*false",
            r"build\s+failed",
            r"error_count\s*[:=]\s*[1-9]",
        ]
        for pattern in failure_patterns:
            if re.search(pattern, text):
                return False

        # Default: assume failure (safer — triggers heal attempt)
        return False

    # =========================================================================
    # MINI-CREW C: TEST GENERATION
    # =========================================================================

    def _run_test_generation(
        self,
        container: dict,
        plan: CodegenPlanInput,
        staging: dict,
        files: list[str],
    ) -> str:
        """Run Mini-Crew C: Tester generates tests for modified files."""
        crew_name = f"testgen_{container['name']}"
        completed = self._load_checkpoint()

        if self.resume and crew_name in completed:
            logger.info(f"[Implement] Skipping {crew_name} (already completed)")
            return "resumed — skipped"

        tester_tools = self._create_tester_tools(staging)
        tester = self._create_agent("tester", tester_tools)

        # Use file paths that exist in staging (modified by code generation),
        # falling back to the original list
        modified_files = [f for f in files if f in staging]
        if not modified_files:
            modified_files = files

        desc, expected = test_generation_task(
            container, plan.task_id, modified_files
        )
        task = Task(
            description=desc,
            expected_output=expected,
            agent=tester,
            human_input=False,
        )

        return self._run_mini_crew(crew_name, [task])

    # =========================================================================
    # STAGING -> GeneratedFile CONVERSION
    # =========================================================================

    def _staging_to_generated_files(self, staging: dict) -> list[GeneratedFile]:
        """Convert the shared staging dict to a list of GeneratedFile objects.

        The staging dict is populated by CodeWriterTool and TestWriterTool:
          staging[file_path] = {
              "content": str,
              "action": "modify"|"create"|"delete",
              "original_content": str,
              "language": str,
          }
        """
        generated = []
        for file_path, entry in staging.items():
            content = entry.get("content", "") if isinstance(entry, dict) else str(entry)
            action = entry.get("action", "modify") if isinstance(entry, dict) else "modify"
            original = entry.get("original_content", "") if isinstance(entry, dict) else ""
            language = entry.get("language", "other") if isinstance(entry, dict) else self._detect_language(file_path)

            generated.append(
                GeneratedFile(
                    file_path=file_path,
                    content=content,
                    original_content=original,
                    action=action,
                    language=language,
                )
            )
        return generated

    @staticmethod
    def _detect_language(file_path: str) -> str:
        """Detect language from file extension."""
        ext = Path(file_path).suffix.lower()
        return {
            ".java": "java",
            ".ts": "typescript",
            ".html": "html",
            ".scss": "scss",
            ".css": "css",
            ".json": "json",
            ".xml": "xml",
            ".py": "python",
            ".js": "javascript",
        }.get(ext, "other")

    # =========================================================================
    # MAIN EXECUTION
    # =========================================================================

    def run(
        self,
        plan: CodegenPlanInput,
        context: CollectedContext,
    ) -> tuple[list[GeneratedFile], BuildVerificationResult]:
        """Execute the implement crew for all containers.

        Args:
            plan: Validated plan from Stage 1 (Plan Reader).
            context: Collected file contexts from Stage 2 (Context Collector).

        Returns:
            Tuple of (generated_files, build_verification_result).
        """
        logger.info("")
        logger.info("=" * 60)
        logger.info(
            f"[Implement] Starting Implement Crew for task: {plan.task_id}"
        )
        logger.info(
            f"[Implement] Task type: {plan.task_type} | "
            f"Files: {context.total_files}"
        )
        logger.info("=" * 60)

        start_time = time.time()
        self.output_dir.mkdir(parents=True, exist_ok=True)

        build_verify_enabled = self.build_verify
        test_enabled = self.test_enabled

        # Shared staging dict across all agents and containers
        staging: dict = {}

        # Group files by container
        container_groups = self._group_files_by_container(context)
        logger.info(
            f"[Implement] Files grouped into {len(container_groups)} "
            f"container(s)"
        )

        container_build_results: list[ContainerBuildResult] = []

        for container_id, file_contexts in container_groups.items():
            if container_id == "unmatched":
                logger.warning(
                    f"[Implement] {len(file_contexts)} files could not be "
                    f"matched to a container — skipping"
                )
                continue

            container = self._get_container_by_id(container_id)
            logger.info(
                f"[Implement] Processing container: {container['name']} "
                f"({len(file_contexts)} files)"
            )

            # Mini-Crew A: Code Generation
            self._run_code_generation(container, file_contexts, plan, staging)

            # Mini-Crew B: Build + Heal (optional)
            if build_verify_enabled and container.get("build_system"):
                build_result = self._run_build_heal(container, plan, staging)
                container_build_results.append(build_result)
            else:
                reason = (
                    "disabled"
                    if not build_verify_enabled
                    else "no build_system configured"
                )
                logger.info(
                    f"[Implement] Skipping build verification for "
                    f"{container['name']} ({reason})"
                )
                container_build_results.append(
                    ContainerBuildResult(
                        container_id=container_id,
                        container_name=container["name"],
                        success=True,
                        exit_code=-1,
                    )
                )

            # Mini-Crew C: Test Generation (optional)
            if test_enabled:
                file_paths = [fc.file_path for fc in file_contexts]
                self._run_test_generation(
                    container, plan, staging, file_paths
                )
            else:
                logger.info(
                    f"[Implement] Skipping test generation for "
                    f"{container['name']} (disabled)"
                )

        # Convert staging -> GeneratedFile list
        generated_files = self._staging_to_generated_files(staging)

        # Aggregate build results
        passed = sum(1 for r in container_build_results if r.success)
        failed = sum(1 for r in container_build_results if not r.success)
        total_heal = sum(
            max(r.attempts - 1, 0) for r in container_build_results
        )
        heal_success = sum(
            1
            for r in container_build_results
            if r.success and r.attempts > 1
        )

        build_result = BuildVerificationResult(
            container_results=container_build_results,
            all_passed=failed == 0,
            total_containers_built=passed,
            total_containers_failed=failed,
            total_heal_attempts=total_heal,
            total_heal_successes=heal_success,
            duration_seconds=round(time.time() - start_time, 1),
            skipped=not build_verify_enabled,
            skip_reason=(
                "" if build_verify_enabled else "build_verify=False"
            ),
        )

        duration = time.time() - start_time
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"[Implement] Crew COMPLETE ({duration:.1f}s)")
        logger.info(f"[Implement] Files generated: {len(generated_files)}")
        logger.info(f"[Implement] Builds: {passed} passed, {failed} failed")
        logger.info(
            f"[Implement] Tokens: {self.total_tokens} | "
            f"Crew calls: {self.total_calls}"
        )
        logger.info("=" * 60)

        return generated_files, build_result

    def kickoff(self, inputs: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute crew — compatible with orchestrator interface."""
        plan = inputs.get("plan") if inputs else None
        context = inputs.get("context") if inputs else None
        if not plan or not context:
            raise ValueError(
                "kickoff requires 'plan' (CodegenPlanInput) and "
                "'context' (CollectedContext) in inputs"
            )
        generated, build = self.run(plan, context)
        return {
            "status": "completed",
            "phase": "implement",
            "generated_files": len(generated),
            "build_passed": build.all_passed,
        }
