"""
Architecture Analysis Crew - Phase 2
=====================================
Mini-Crew pattern: 5 independent crews, each with fresh LLM context.
NO YAML. All configuration in Python constants.

ANALYSIS APPROACH:
- Input: architecture_facts.json + evidence_map.json + ChromaDB Index
- 4 Specialized Agents: Technical, Functional, Quality, Synthesis
- 17 Focused Tasks in 5 Mini-Crews
- Output: analyzed_architecture.json

Mini-Crew Layout:
  1. tech_analysis    (tech_architect)   -> 4 tasks
  2. domain_analysis  (func_analyst)     -> 4 tasks
  3. workflow_analysis (func_analyst)    -> 4 tasks
  4. quality_analysis (quality_analyst)  -> 4 tasks
  5. synthesis        (synthesis_lead)   -> 1 task
"""

import json
import time
from pathlib import Path
from typing import Any

from crewai import LLM, Agent, Crew, Process, Task
from crewai.mcp import MCPServerStdio
from crewai_tools import FileWriterTool

from ...shared.paths import CHROMA_DIR
from ...shared.utils.llm_factory import create_llm
from ...shared.utils.logger import setup_logger
from ...shared.utils.tool_guardrails import install_guardrails, uninstall_guardrails
from .agents import AGENT_CONFIGS
from .tasks import (
    DOMAIN_ANALYSIS_TASKS,
    QUALITY_ANALYSIS_TASKS,
    SYNTHESIS_TASKS,
    TECH_ANALYSIS_TASKS,
    WORKFLOW_ANALYSIS_TASKS,
)
from .tools import FactsQueryTool, FactsStatisticsTool, PartialResultsTool, RAGQueryTool, StereotypeListTool

# MCP server script path (project root)
_MCP_SERVER_PATH = str(Path(__file__).resolve().parents[4] / "mcp_server.py")

logger = setup_logger(__name__)


# =============================================================================
# CREW CLASS
# =============================================================================


class ArchitectureAnalysisCrew:
    """
    Architecture Analysis Crew - Phase 2.

    Mini-Crew pattern: 5 independent crews with fresh LLM context each.
    - tech_analysis:    4 tasks (tech_architect)
    - domain_analysis:  4 tasks (func_analyst)
    - workflow_analysis: 4 tasks (func_analyst)
    - quality_analysis: 4 tasks (quality_analyst)
    - synthesis:        1 task  (synthesis_lead)
    """

    def __init__(
        self,
        facts_path: str = "knowledge/extract/architecture_facts.json",
        chroma_dir: str = None,
        output_dir: str = "knowledge/analyze",
    ):
        """Initialize crew with paths."""
        self.facts_path = Path(facts_path)
        self.evidence_path = self.facts_path.parent / "evidence_map.json"
        self.chroma_dir = chroma_dir or CHROMA_DIR
        self.output_dir = Path(output_dir)
        self._analysis_dir = self.output_dir / "analysis"
        self._checkpoint_file = self.output_dir / ".checkpoint_analysis.json"

        # MCP server path (resolved once)
        self._mcp_server_path = _MCP_SERVER_PATH

    # =========================================================================
    # LLM FACTORY
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
            verbose=True,
            max_iter=25,
            max_retry_limit=3,
            allow_delegation=False,
            respect_context_window=True,
        )

    def _create_analysis_tools(self) -> list:
        """Create tools for analysis agents (tech, func, quality)."""
        return [
            FactsStatisticsTool(facts_path=str(self.facts_path)),
            FactsQueryTool(facts_path=str(self.facts_path)),
            RAGQueryTool(chroma_dir=self.chroma_dir),
            StereotypeListTool(facts_path=str(self.facts_path)),
        ]

    def _create_synthesis_tools(self) -> list:
        """Create tools for synthesis agent."""
        return [
            PartialResultsTool(analysis_dir=str(self._analysis_dir)),
            FileWriterTool(),
        ]

    # =========================================================================
    # MINI-CREW EXECUTION
    # =========================================================================

    def _build_tasks(
        self,
        task_defs: list[tuple],
        agent: Agent,
        output_dir: Path,
    ) -> list[Task]:
        """Build Task objects from task definitions."""
        tasks = []
        for desc, expected, pydantic_model, filename in task_defs:
            tasks.append(
                Task(
                    description=desc,
                    expected_output=expected,
                    agent=agent,
                    context=[],
                    output_pydantic=pydantic_model,
                    output_file=str(output_dir / filename),
                    human_input=False,
                )
            )
        return tasks

    _MAX_RETRIES = 2  # transient error retries

    def _run_mini_crew(self, name: str, tasks: list[Task]) -> str:
        """Run a mini-crew with fresh context, retry on transient errors."""
        logger.info(f"[Phase2] Starting Mini-Crew: {name} ({len(tasks)} tasks)")
        start_time = time.time()

        for attempt in range(1, self._MAX_RETRIES + 1):
            tracker = None
            try:
                crew = Crew(
                    agents=[tasks[0].agent],
                    tasks=tasks,
                    process=Process.sequential,
                    verbose=True,
                    memory=False,
                    max_rpm=30,
                    planning=False,
                )
                tracker = install_guardrails()
                result = crew.kickoff()
                duration = time.time() - start_time
                logger.info(f"[Phase2] Completed Mini-Crew: {name} ({duration:.1f}s)")

                # Log success metric
                try:
                    from ...shared.utils.logger import log_metric

                    tokens = getattr(result, "token_usage", {})
                    total_tokens = tokens.get("total_tokens", 0) if isinstance(tokens, dict) else 0
                    log_metric(
                        "mini_crew_complete",
                        crew_type="Phase2",
                        crew_name=name,
                        duration_seconds=round(duration, 1),
                        tasks=len(tasks),
                        attempts=attempt,
                        total_tokens=total_tokens,
                        estimated=total_tokens == 0,
                    )
                except Exception:
                    pass

                self._save_checkpoint(name)
                return str(result)

            except (ConnectionError, TimeoutError, OSError) as e:
                if attempt < self._MAX_RETRIES:
                    delay = 5 * (2 ** (attempt - 1))
                    logger.warning(
                        f"[Phase2] {name}: Connection error "
                        f"(attempt {attempt}/{self._MAX_RETRIES}), "
                        f"retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)
                    # Fresh agent for retry
                    new_agent = self._create_agent(
                        self._agent_key_for_crew(name),
                        self._create_analysis_tools(),
                    )
                    for t in tasks:
                        t.agent = new_agent
                    continue
                # Final attempt
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
                            blocked=len(tracker.calls) - len(set(tracker.calls)),
                        )
                    except Exception:
                        pass
                uninstall_guardrails(tracker)

        raise RuntimeError(f"Mini-crew {name} failed after {self._MAX_RETRIES} attempts")

    def _agent_key_for_crew(self, crew_name: str) -> str:
        """Map mini-crew name to agent config key."""
        mapping = {
            "tech_analysis": "tech_architect",
            "domain_analysis": "func_analyst",
            "workflow_analysis": "func_analyst",
            "quality_analysis": "quality_analyst",
            "synthesis": "synthesis_lead",
        }
        return mapping.get(crew_name, "tech_architect")

    def _log_crew_failure(self, name: str, tasks: list[Task], error: Exception, start_time: float) -> None:
        """Log failure metric and error details."""
        duration = time.time() - start_time
        error_type = type(error).__name__
        error_msg = str(error)[:500]
        logger.error(f"[Phase2] Failed Mini-Crew: {name} ({duration:.1f}s, {error_type}): {error_msg}")
        try:
            from ...shared.utils.logger import log_metric

            log_metric(
                "mini_crew_failed",
                crew_type="Phase2",
                crew_name=name,
                duration_seconds=round(duration, 1),
                tasks=len(tasks),
                error_type=error_type,
                error=error_msg,
            )
        except Exception:
            pass  # Don't let metric logging break error handling

    # =========================================================================
    # CHECKPOINT
    # =========================================================================

    def _load_checkpoint(self) -> set[str]:
        """Load completed mini-crew names from checkpoint."""
        if not self._checkpoint_file.exists():
            return set()
        try:
            data = json.loads(self._checkpoint_file.read_text(encoding="utf-8"))
            completed = set(data.get("completed_crews", []))
            if completed:
                logger.info(f"[Phase2] Resuming: {len(completed)} mini-crews already completed: {sorted(completed)}")
            return completed
        except Exception:
            return set()

    def _save_checkpoint(self, crew_name: str):
        """Save completed mini-crew to checkpoint."""
        completed = self._load_checkpoint()
        completed.add(crew_name)
        data = {"completed_crews": sorted(completed)}
        self._checkpoint_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.debug(f"[Phase2] Checkpoint saved: {crew_name}")

    # =========================================================================
    # PREREQUISITE VALIDATION + CLEANUP
    # =========================================================================

    def _prepare_clean_run(self, is_resume: bool = False):
        """Validate prerequisites and optionally clean old outputs."""
        logger.info("")
        logger.info("[Phase2] Preparing run...")

        # Step 1: Validate prerequisites
        logger.info("[Phase2] Step 1: Checking Phase 1 prerequisites...")

        missing_files = []

        if not self.facts_path.exists():
            missing_files.append(str(self.facts_path))
        else:
            try:
                with open(self.facts_path, encoding="utf-8") as f:
                    facts_data = json.load(f)
                if not isinstance(facts_data, dict) or "components" not in facts_data:
                    logger.error(f"   [INVALID] {self.facts_path}: missing 'components' key")
                    missing_files.append(f"{self.facts_path} (invalid JSON structure)")
                else:
                    comp_count = len(facts_data.get("components", []))
                    logger.info(f"   [OK] Found: {self.facts_path} ({comp_count} components)")
            except json.JSONDecodeError as e:
                logger.error(f"   [INVALID] {self.facts_path}: {e}")
                missing_files.append(f"{self.facts_path} (invalid JSON)")

        if not self.evidence_path.exists():
            missing_files.append(str(self.evidence_path))
        else:
            logger.info(f"   [OK] Found: {self.evidence_path}")

        if missing_files:
            logger.error("")
            logger.error("=" * 60)
            logger.error("[ERROR] PHASE 2 CANNOT START")
            logger.error("=" * 60)
            logger.error("")
            logger.error("Missing Phase 1 output files:")
            for f in missing_files:
                logger.error(f"   [MISSING] {f}")
            logger.error("")
            logger.error("[HINT] Solution: Run Phase 1 first:")
            logger.error("   python run.py --phases extract")
            logger.error("")
            logger.error("=" * 60)
            raise FileNotFoundError(
                f"Missing Phase 1 files: {', '.join(missing_files)}. "
                f"Run Phase 1 first: python run.py --phases extract"
            )

        logger.info("   [OK] All prerequisites satisfied!")

        # Step 2: Clean old outputs (skip on resume)
        if not is_resume:
            logger.info("[Phase2] Step 2: Clean old outputs...")

            output_files = [
                "analyzed_architecture.json",
                "analysis_technical.json",
                "analysis_functional.json",
                "analysis_quality.json",
                # Legacy names
                "temp_technical_analysis.json",
                "temp_functional_analysis.json",
                "temp_quality_analysis.json",
            ]

            deleted = 0
            for filename in output_files:
                f = self.output_dir / filename
                if f.exists():
                    f.unlink()
                    deleted += 1

            if deleted:
                logger.info(f"   [OK] {deleted} old files deleted")
            else:
                logger.info("   [OK] No old outputs to clean (first run)")

            # Step 3: Clean partial analysis outputs
            logger.info("[Phase2] Step 3: Cleaning partial analysis outputs...")
            if self._analysis_dir.exists():
                for json_file in self._analysis_dir.glob("*.json"):
                    json_file.unlink()
                    logger.info(f"   [DELETED] {json_file.name}")
        else:
            logger.info("[Phase2] Resuming — skipping clean")

        self._analysis_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"   [OK] Analysis directory ready: {self._analysis_dir}")
        logger.info("")

    def _format_json_outputs(self):
        """Format all JSON files with pretty-print."""
        logger.info("[Phase2] Formatting JSON outputs with pretty-print...")

        for json_file in self._analysis_dir.glob("*.json"):
            self._format_json_file(json_file)

        for json_file in self.output_dir.glob("*.json"):
            if json_file.name.startswith("."):
                continue
            self._format_json_file(json_file)

    @staticmethod
    def _format_json_file(json_file: Path) -> None:
        """Format a JSON file with pretty-print."""
        try:
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"   [OK] Formatted: {json_file.name}")
        except Exception as e:
            logger.warning(f"   [WARN] Could not format {json_file.name}: {e}")

    # =========================================================================
    # MAIN EXECUTION
    # =========================================================================

    def run(self) -> dict[str, Any]:
        """Execute all 5 mini-crews sequentially with checkpoint resume."""
        completed = self._load_checkpoint()
        is_resume = len(completed) > 0

        self._prepare_clean_run(is_resume=is_resume)

        # Mini-Crew 1: Technical Analysis (4 tasks)
        if "tech_analysis" not in completed:
            agent = self._create_agent("tech_architect", self._create_analysis_tools())
            tasks = self._build_tasks(TECH_ANALYSIS_TASKS, agent, self._analysis_dir)
            self._run_mini_crew("tech_analysis", tasks)

        # Mini-Crew 2: Domain Analysis (4 tasks)
        if "domain_analysis" not in completed:
            agent = self._create_agent("func_analyst", self._create_analysis_tools())
            tasks = self._build_tasks(DOMAIN_ANALYSIS_TASKS, agent, self._analysis_dir)
            self._run_mini_crew("domain_analysis", tasks)

        # Mini-Crew 3: Workflow Analysis (4 tasks)
        if "workflow_analysis" not in completed:
            agent = self._create_agent("func_analyst", self._create_analysis_tools())
            tasks = self._build_tasks(WORKFLOW_ANALYSIS_TASKS, agent, self._analysis_dir)
            self._run_mini_crew("workflow_analysis", tasks)

        # Mini-Crew 4: Quality Analysis (4 tasks)
        if "quality_analysis" not in completed:
            agent = self._create_agent("quality_analyst", self._create_analysis_tools())
            tasks = self._build_tasks(QUALITY_ANALYSIS_TASKS, agent, self._analysis_dir)
            self._run_mini_crew("quality_analysis", tasks)

        # Mini-Crew 5: Synthesis (1 task)
        if "synthesis" not in completed:
            agent = self._create_agent("synthesis_lead", self._create_synthesis_tools())
            tasks = self._build_tasks(SYNTHESIS_TASKS, agent, self.output_dir)
            self._run_mini_crew("synthesis", tasks)

        # Post-processing
        self._format_json_outputs()

        output_path = str(self.output_dir / "analyzed_architecture.json")

        logger.info("")
        logger.info("=" * 60)
        logger.info("PHASE 2 COMPLETE: Architecture Analysis finished")
        logger.info("=" * 60)
        logger.info(f"Output: {output_path}")

        return {
            "status": "completed",
            "phase": "analyze",
            "result": output_path,
        }

    def kickoff(self, inputs: dict[str, Any] = None) -> dict[str, Any]:
        """Execute crew - compatible with orchestrator interface."""
        return self.run()
