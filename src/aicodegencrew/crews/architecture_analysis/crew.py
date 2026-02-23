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
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from crewai import LLM, Agent, Crew, Process, Task
from crewai_tools import FileWriterTool

from ...shared.mcp import get_phase3_mcps
from ...shared.paths import CHROMA_DIR, get_chroma_dir
from ...shared.utils.llm_factory import create_llm
from ...shared.utils.crew_callbacks import step_callback, task_callback
from ...shared.utils.embedder_config import get_crew_embedder
from ...shared.utils.logger import setup_logger
from ...shared.utils.task_guardrails import validate_json_output
from ...shared.utils.tool_guardrails import install_guardrails, uninstall_guardrails
from .agents import AGENT_CONFIGS
from .tasks import (
    DOMAIN_ANALYSIS_TASKS,
    QUALITY_ANALYSIS_TASKS,
    SYNTHESIS_TASKS,
    TECH_ANALYSIS_TASKS,
    WORKFLOW_ANALYSIS_TASKS,
)
from .tools import (
    FactsQueryTool,
    FactsStatisticsTool,
    PartialResultsTool,
    RAGQueryTool,
    StereotypeListTool,
    SymbolQueryTool,
)

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
        self.chroma_dir = chroma_dir or get_chroma_dir()
        self.output_dir = Path(output_dir)
        self._analysis_dir = self.output_dir / "analysis"
        self._checkpoint_file = self.output_dir / ".checkpoint_analysis.json"
        self._checkpoint_lock = threading.Lock()  # Thread-safe checkpoint writes

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
        """Create a fresh agent with fresh LLM context.

        MCPs provide tools automatically — CrewAI handles tool discovery.
        """
        config = AGENT_CONFIGS[agent_key]
        return Agent(
            role=config["role"],
            goal=config["goal"],
            backstory=config["backstory"],
            llm=self._create_llm(),
            tools=tools,
            mcps=get_phase3_mcps(),
            verbose=True,
            max_iter=25,
            max_retry_limit=3,
            allow_delegation=False,
            respect_context_window=True,
            inject_date=True,
        )

    def _preload_dimension_cache(self, dimension_names: list[str]) -> dict:
        """Pre-load the heaviest dimension files once for sharing across mini-crews (PERF-3).

        Returns a plain dict keyed by dimension name that can be passed to
        FactsQueryTool(preloaded_cache=...) — each mini-crew gets its own
        FactsQueryTool instance initialised with a copy of this data, avoiding
        repeated disk I/O for the same files.
        """
        import json as _json

        facts_dir = self.facts_path.parent
        dimension_file_map = {
            "components": "components.json",
            "relations": "relations.json",
            "interfaces": "interfaces.json",
            "containers": "containers.json",
            "data_model": "data_model.json",
            "runtime": "runtime.json",
            "evidence": "evidence_map.json",
        }

        preloaded: dict = {}
        for name in dimension_names:
            filename = dimension_file_map.get(name)
            if not filename:
                continue
            path = facts_dir / filename
            if not path.exists():
                logger.debug("[Phase2] Preload skip (not found): %s", path.name)
                continue
            try:
                raw = _json.loads(path.read_text(encoding="utf-8"))
                # Normalise to list for component/relation/interface/container categories
                if isinstance(raw, dict) and name in raw:
                    raw = raw[name]
                preloaded[name] = raw
                size = len(raw) if isinstance(raw, (list, dict)) else "?"
                logger.debug("[Phase2] Preloaded dimension %s: %s items", name, size)
            except Exception as e:
                logger.warning("[Phase2] Could not preload dimension %s: %s", name, e)

        if preloaded:
            logger.info(
                "[Phase2] Preloading dimension cache: %s",
                ", ".join(preloaded.keys()),
            )
        return preloaded

    def _create_analysis_tools(self, preloaded_cache: dict | None = None) -> list:
        """Create tools for analysis agents (tech, func, quality).

        Args:
            preloaded_cache: Optional pre-loaded dimension data to inject into
                FactsQueryTool, avoiding repeated disk reads across parallel
                mini-crews (PERF-3).
        """
        return [
            FactsStatisticsTool(facts_path=str(self.facts_path)),
            FactsQueryTool(facts_dir=str(self.facts_path.parent), preloaded_cache=preloaded_cache),
            RAGQueryTool(chroma_dir=self.chroma_dir),
            StereotypeListTool(facts_path=str(self.facts_path)),
            SymbolQueryTool(),
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
        """Build Task objects from task definitions.

        NOTE: output_pydantic is intentionally omitted (BUG-C3 fix).
        On-prem LLMs can truncate output, causing CrewAI to raise Pydantic
        ValidationError before custom repair code can run. We rely on
        output_file + _repair_task_output_files() for JSON persistence.
        """
        tasks = []
        for desc, expected, _pydantic_model, filename in task_defs:
            tasks.append(
                Task(
                    description=desc,
                    expected_output=expected,
                    agent=agent,
                    context=[],
                    output_file=str(output_dir / filename),
                    human_input=False,
                    guardrail=validate_json_output,
                    guardrail_max_retries=1,
                )
            )
        return tasks

    @staticmethod
    def _extract_json_from_raw(raw: str) -> dict:
        """Extract and repair JSON from raw LLM output."""
        text = raw.strip()
        # Strip markdown fences if present
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        # Try direct parse first
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else {"content": data}
        except json.JSONDecodeError:
            pass

        # Try to repair truncated JSON by closing open structures
        repaired = text.rstrip()
        in_string = False
        escape_next = False
        stack = []
        for ch in repaired:
            if escape_next:
                escape_next = False
                continue
            if ch == "\\" and in_string:
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch in ("{", "["):
                stack.append(ch)
            elif ch == "}" and stack and stack[-1] == "{":
                stack.pop()
            elif ch == "]" and stack and stack[-1] == "[":
                stack.pop()
        if in_string:
            repaired += '"'
        repaired = re.sub(r",\s*$", "", repaired)
        for opener in reversed(stack):
            repaired += "]" if opener == "[" else "}"

        try:
            data = json.loads(repaired)
            return data if isinstance(data, dict) else {"content": data}
        except json.JSONDecodeError as e:
            raise ValueError(f"Could not parse or repair JSON: {e}") from e

    def _repair_task_output_files(self, tasks: list[Task]) -> None:
        """Repair partial/malformed JSON written to task output_file paths.

        When output_pydantic is removed, CrewAI writes the raw LLM text to
        output_file. This method ensures each file contains valid JSON,
        repairing truncated output or writing a fallback if repair fails.
        """
        for task in tasks:
            if not task.output_file:
                continue
            output_path = Path(task.output_file)
            if not output_path.exists():
                continue
            try:
                raw = output_path.read_text(encoding="utf-8")
                json.loads(raw)  # Already valid — nothing to do
            except json.JSONDecodeError:
                try:
                    repaired = self._extract_json_from_raw(raw)
                    output_path.write_text(
                        json.dumps(repaired, indent=2, ensure_ascii=False),
                        encoding="utf-8",
                    )
                    logger.info("[Phase2] Repaired JSON in %s", output_path.name)
                except Exception as repair_err:
                    fallback = {"raw_output": raw[:2000], "parse_error": True}
                    output_path.write_text(
                        json.dumps(fallback, indent=2, ensure_ascii=False),
                        encoding="utf-8",
                    )
                    logger.warning(
                        "[Phase2] Could not repair %s (%s), wrote fallback",
                        output_path.name,
                        repair_err,
                    )

    _MAX_RETRIES = 2  # transient error retries

    def _run_mini_crew(self, name: str, tasks: list[Task]) -> str:
        """Run a mini-crew with fresh context, retry on transient errors."""
        logger.info(f"[Phase2] Starting Mini-Crew: {name} ({len(tasks)} tasks)")
        start_time = time.time()

        for attempt in range(1, self._MAX_RETRIES + 1):
            tracker = None
            try:
                log_dir = self._analysis_dir / "logs"
                log_dir.mkdir(parents=True, exist_ok=True)
                crew = Crew(
                    agents=[tasks[0].agent],
                    tasks=tasks,
                    process=Process.sequential,
                    verbose=True,
                    memory=False,
                    max_rpm=30,
                    planning=False,
                    step_callback=step_callback,
                    task_callback=task_callback,
                    output_log_file=str(log_dir / f"{name}.json"),
                    embedder=get_crew_embedder(),
                )
                tracker = install_guardrails()
                result = crew.kickoff()
                duration = time.time() - start_time
                logger.info(f"[Phase2] Completed Mini-Crew: {name} ({duration:.1f}s)")

                # Repair any truncated JSON in task output files (BUG-C3 companion fix)
                self._repair_task_output_files(tasks)

                # Log success metric
                try:
                    from ...shared.utils.logger import log_metric

                    # BUG-C1 fix: UsageMetrics is not a dict; use getattr with dict fallback
                    token_usage = getattr(result, "token_usage", None)
                    if token_usage is not None:
                        if isinstance(token_usage, dict):
                            total_tokens = int(token_usage.get("total_tokens", 0))
                        else:
                            total_tokens = int(getattr(token_usage, "total_tokens", 0))
                    else:
                        total_tokens = 0
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
                            duplicates=len(tracker.calls) - len(set(tracker.calls)),
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
        """Save completed mini-crew to checkpoint (thread-safe via lock)."""
        with self._checkpoint_lock:
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
                f"Missing Phase 1 files: {', '.join(missing_files)}. Run Phase 1 first: python run.py --phases extract"
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

            # Also delete the mini-crew checkpoint so no crews are skipped on this fresh run
            if self._checkpoint_file.exists():
                self._checkpoint_file.unlink()
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
            # BUG-Y1 fix: on resume, delete stale output files for incomplete mini-crews.
            # The synthesis crew reads ALL files from _analysis_dir; stale files from a
            # previously failed run would corrupt the synthesis output if kept.
            logger.info("[Phase2] Resuming — cleaning stale files for incomplete mini-crews")
            completed_on_resume = self._load_checkpoint()
            crew_output_files: dict[str, list[str]] = {
                "tech_analysis": [t[3] for t in TECH_ANALYSIS_TASKS],
                "domain_analysis": [t[3] for t in DOMAIN_ANALYSIS_TASKS],
                "workflow_analysis": [t[3] for t in WORKFLOW_ANALYSIS_TASKS],
                "quality_analysis": [t[3] for t in QUALITY_ANALYSIS_TASKS],
                "synthesis": [t[3] for t in SYNTHESIS_TASKS],
            }
            for crew_name, filenames in crew_output_files.items():
                if crew_name not in completed_on_resume:
                    # Choose the correct directory for each crew type
                    base_dir = self.output_dir if crew_name == "synthesis" else self._analysis_dir
                    for fn in filenames:
                        stale = base_dir / fn
                        if stale.exists():
                            stale.unlink()
                            logger.info(f"   [DELETED STALE] {stale.name} ({crew_name} incomplete)")

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

    def _inject_schema_version(self) -> None:
        """Inject _schema_version into analyzed_architecture.json if absent."""
        from ...shared.schema_version import add_schema_version

        output_file = self.output_dir / "analyzed_architecture.json"
        if not output_file.exists():
            return
        try:
            data = json.loads(output_file.read_text(encoding="utf-8"))
            if "_schema_version" not in data:
                versioned = add_schema_version(data, "analyze")
                output_file.write_text(json.dumps(versioned, indent=2, ensure_ascii=False), encoding="utf-8")
                logger.info("[Phase2] Schema version injected into analyzed_architecture.json")
        except Exception as e:
            logger.warning("[Phase2] Could not inject schema version: %s", e)

    # =========================================================================
    # MAIN EXECUTION
    # =========================================================================

    def run(self) -> dict[str, Any]:
        """Execute all 5 mini-crews with parallel analysis phase + sequential synthesis.

        Performance (R1): Mini-Crews 1-4 (tech/domain/workflow/quality) have ZERO data
        dependency on each other — all read the same static architecture_facts.json.
        Running them in parallel cuts Phase 2 wall-clock time by ~4x.

        Mini-Crew 5 (synthesis) runs AFTER all 4 complete, reading their output files.
        """
        completed = self._load_checkpoint()
        is_resume = len(completed) > 0

        self._prepare_clean_run(is_resume=is_resume)

        # Re-read checkpoint after cleanup (BUG-Y1: stale files may have been deleted)
        completed = self._load_checkpoint()

        # ── Mini-Crews 1-4: Parallel Analysis ────────────────────────────────
        # Each mini-crew uses fresh agent + tool instances → thread-safe.
        # Checkpoint writes are guarded by _checkpoint_lock.
        analysis_specs: list[tuple[str, str, list[tuple]]] = [
            ("tech_analysis", "tech_architect", TECH_ANALYSIS_TASKS),
            ("domain_analysis", "func_analyst", DOMAIN_ANALYSIS_TASKS),
            ("workflow_analysis", "func_analyst", WORKFLOW_ANALYSIS_TASKS),
            ("quality_analysis", "quality_analyst", QUALITY_ANALYSIS_TASKS),
        ]

        pending = [(name, key, defs) for name, key, defs in analysis_specs if name not in completed]

        if pending:
            logger.info(
                "[Phase2] Launching %d analysis mini-crews in parallel: %s",
                len(pending),
                [n for n, _, _ in pending],
            )
            # PERF-3: Preload the three heaviest dimension files once; each
            # parallel mini-crew receives a copy via FactsQueryTool(preloaded_cache=…)
            # — 4 tool instances x ~500 KB each is <<10 MB and saves 4 disk reads.
            shared_preloaded = self._preload_dimension_cache(["components", "relations", "interfaces"])
            with ThreadPoolExecutor(max_workers=len(pending)) as executor:
                futures: dict = {}
                for name, agent_key, task_defs in pending:
                    agent = self._create_agent(agent_key, self._create_analysis_tools(shared_preloaded))
                    tasks = self._build_tasks(task_defs, agent, self._analysis_dir)
                    futures[executor.submit(self._run_mini_crew, name, tasks)] = name

                errors: list[str] = []
                for future in as_completed(futures):
                    crew_name = futures[future]
                    try:
                        future.result()
                    except Exception as exc:
                        logger.error("[Phase2] Mini-crew %s failed: %s", crew_name, exc)
                        errors.append(f"{crew_name}: {exc}")

                if errors:
                    raise RuntimeError(f"[Phase2] {len(errors)} parallel mini-crew(s) failed: {'; '.join(errors)}")
        else:
            logger.info("[Phase2] All analysis mini-crews already completed (checkpoint)")

        # ── Mini-Crew 5: Synthesis (sequential — depends on 1-4 output files) ──
        completed = self._load_checkpoint()  # Re-read after parallel phase
        if "synthesis" not in completed:
            agent = self._create_agent("synthesis_lead", self._create_synthesis_tools())
            tasks = self._build_tasks(SYNTHESIS_TASKS, agent, self.output_dir)
            self._run_mini_crew("synthesis", tasks)

        # Post-processing
        self._format_json_outputs()
        self._inject_schema_version()

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
