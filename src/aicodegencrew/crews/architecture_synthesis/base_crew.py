"""
MiniCrewBase - Base class for Mini-Crew pattern
================================================
Extracts shared infrastructure from C4Crew and Arc42Crew:
- JSON loading, LLM creation, agent factory
- Mini-crew execution with fresh context per crew
- Facts summarization helpers
- MCP server setup

Subclasses only need to implement:
- crew_name: str property
- agent_config: dict property (role, goal, backstory)
- _get_extra_tools() -> list (optional)
- _summarize_facts() -> dict
- run() -> str
"""

import json
import os
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from crewai import LLM, Agent, Crew, Process, Task
from crewai.mcp import MCPServerStdio

from ...shared.paths import CHROMA_DIR
from ...shared.utils.llm_factory import create_llm
from ...shared.utils.logger import setup_logger
from ...shared.utils.tool_guardrails import install_guardrails, uninstall_guardrails
from ...shared.tools import RAGQueryTool
from .tools import (
    DocWriterTool,
    DrawioDiagramTool,
    FactsQueryTool,
    FileReadTool,
    StereotypeListTool,
)

logger = setup_logger(__name__)

# Retry settings for transient LLM connection failures
_MAX_RETRIES = 2
_RETRY_DELAY_BASE = 5  # seconds, doubled each retry


# Shared tool instruction for all doc-writing tasks (with few-shot example)
TOOL_INSTRUCTION = """
CRITICAL INSTRUCTION: You MUST use the doc_writer tool to write the output file.
Do NOT include the full document in your response text.

MANDATORY RULES:
1. If you are about to write more than 200 characters, STOP and call doc_writer.
2. Your final message MUST be a one-liner confirmation.
3. Do NOT call the same MCP tool more than 3 times with identical arguments.
4. Maximum 25 tool calls per task, then you MUST call doc_writer.

## CORRECT EXECUTION PATTERN (follow this exactly):

Step 1: Call MCP tools to gather REAL data (4-10 tool calls). Query EVERY stereotype,
        get endpoints, get relations. More data = better documentation.
Step 2: Call doc_writer(file_path="<path>", content="# Full markdown document...") ONCE.
Step 3: Respond ONLY with a short confirmation message.

If your content exceeds 15000 characters, use chunked_writer instead of doc_writer:
1. chunked_writer(mode="create", file_path="<path>", content="first part...")
2. chunked_writer(mode="append", file_path="<path>", content="next part...")
3. chunked_writer(mode="finalize", file_path="<path>", content="")

## CRITICAL REQUIREMENT - READ THIS CAREFULLY:

You MUST actually CALL the doc_writer tool. Do NOT just write text that says "calling doc_writer".
Do NOT write example responses like "Your response: File written successfully".
Do NOT write the markdown content in your response text.

CORRECT execution pattern:
1. Call 5-10 information-gathering tools (get_statistics, list_components_by_stereotype, etc.)
2. Build your complete markdown document in memory (8-12 pages)
3. ACTUALLY CALL: doc_writer(file_path="<path>", content="<FULL_MARKDOWN_HERE>")
4. After the tool returns success, respond with ONLY: "Chapter completed."

WRONG examples (do NOT do this):
- Writing: "I will now call doc_writer(file_path=..., content=...)"
- Writing: "Call 4: doc_writer(...)"
- Writing: "Your response: File written successfully"
- Putting markdown content in your response instead of the tool parameter
- Saying "File written" without actually calling the tool

RIGHT example (DO this):
- Gather data with 10 tool calls
- Call doc_writer with 8000+ character markdown as content parameter
- Respond with: "Chapter completed."

The doc_writer tool MUST appear in your tool_calls, not in your text response!
"""


class MiniCrewBase(ABC):
    """
    Base class for Mini-Crew based synthesis crews.

    Provides shared infrastructure:
    - Facts/analysis/evidence loading from JSON
    - LLM creation from env vars
    - Agent creation with MCP server
    - Mini-crew execution with fresh context
    - Checkpoint tracking per mini-crew
    """

    def __init__(
        self,
        facts_path: str = "knowledge/extract/architecture_facts.json",
        analyzed_path: str | None = None,
        chroma_dir: str | None = None,
        output_dir: str | None = None,
    ):
        self.facts_path = Path(facts_path)
        if analyzed_path:
            self.analyzed_path = Path(analyzed_path)
        else:
            # Derive from facts_path: knowledge/extract/ → knowledge/analyze/
            knowledge_base = self.facts_path.parent.parent
            self.analyzed_path = knowledge_base / "analyze" / "analyzed_architecture.json"
        self.chroma_dir = chroma_dir or CHROMA_DIR

        # Load data
        self.facts = self._load_json(self.facts_path)
        self.analysis = self._load_json(self.analyzed_path)
        self.evidence_map = self._load_json(self.facts_path.parent / "evidence_map.json")

        # Build template variables for tasks
        self.summaries = self._summarize_facts()

        # MCP server config (resolved once, reused across mini-crews)
        self._mcp_server_path = self._resolve_mcp_server_path()

        # Output directory: explicit or derived from facts_path
        self._output_dir = Path(output_dir) if output_dir else self.facts_path.parent.parent / "document"

        # Checkpoint tracking
        self._checkpoints: list[dict[str, Any]] = []

        # Token budget tracking
        self._token_budget = int(os.getenv("LLM_CONTEXT_WINDOW", "120000"))
        self._token_usage: list[dict[str, Any]] = []
        # Track quality degradations (fallback writes, stubs, mini-crew failures).
        self._degradation_reasons: list[str] = []

    # -------------------------------------------------------------------------
    # ABSTRACT - Subclasses must implement
    # -------------------------------------------------------------------------

    @property
    @abstractmethod
    def crew_name(self) -> str:
        """Short name for logging, e.g. 'C4' or 'Arc42'."""
        ...

    @property
    @abstractmethod
    def agent_config(self) -> dict[str, str]:
        """Agent configuration dict with keys: role, goal, backstory."""
        ...

    @abstractmethod
    def _summarize_facts(self) -> dict[str, str]:
        """Create template variables from facts + analysis for task descriptions."""
        ...

    @abstractmethod
    def run(self) -> str | dict:
        """Execute all mini-crews and return summary or result dict."""
        ...

    # -------------------------------------------------------------------------
    # DATA LOADING
    # -------------------------------------------------------------------------

    @staticmethod
    def _load_json(path: Path) -> dict:
        """Load JSON file, return empty dict on error."""
        if path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    @staticmethod
    def escape_braces(text: str) -> str:
        """Escape curly braces for .format() compatibility in task descriptions."""
        return text.replace("{", "{{").replace("}", "}}")

    # -------------------------------------------------------------------------
    # LLM FACTORY
    # -------------------------------------------------------------------------

    def _create_llm(self) -> LLM:
        """Create LLM instance from environment variables."""
        return create_llm()

    # -------------------------------------------------------------------------
    # TOOL FACTORY
    # -------------------------------------------------------------------------

    def _create_base_tools(self) -> list:
        """Create base tool set shared by all synthesis crews."""
        out = str(self._output_dir)
        return [
            DrawioDiagramTool(output_dir=out),
            DocWriterTool(output_dir=out),
            FileReadTool(),
            FactsQueryTool(facts_path=str(self.facts_path)),
            StereotypeListTool(facts_path=str(self.facts_path)),
            RAGQueryTool(chroma_dir=self.chroma_dir),
        ]

    def _get_extra_tools(self) -> list:
        """Override to add crew-specific tools (e.g. ChunkedWriterTool)."""
        return []

    def _create_tools(self) -> list:
        """Create complete tool set (base + extras)."""
        return self._create_base_tools() + self._get_extra_tools()

    # -------------------------------------------------------------------------
    # AGENT FACTORY
    # -------------------------------------------------------------------------

    @staticmethod
    def _resolve_mcp_server_path() -> str:
        """Resolve absolute path to mcp_server.py at project root (once)."""
        current = Path(__file__).resolve().parent
        for _ in range(10):
            candidate = current / "mcp_server.py"
            if candidate.exists():
                return str(candidate)
            current = current.parent
        # Fallback
        return str(Path(__file__).resolve().parents[4] / "mcp_server.py")

    def _create_mcp_config(self) -> MCPServerStdio:
        """Create MCP server config (reuses cached path)."""
        return MCPServerStdio(
            command="python",
            args=[self._mcp_server_path],
            cache_tools_list=True,
        )

    def _create_agent(self) -> Agent:
        """Create a fresh agent with fresh LLM context."""
        config = self.agent_config
        return Agent(
            role=config["role"],
            goal=config["goal"],
            backstory=config["backstory"],
            llm=self._create_llm(),
            tools=self._create_tools(),
            mcps=[self._create_mcp_config()],
            verbose=True,
            max_iter=30,
            max_retry_limit=10,
        )

    # -------------------------------------------------------------------------
    # MINI-CREW EXECUTION
    # -------------------------------------------------------------------------

    def _run_mini_crew(
        self,
        name: str,
        tasks: list[Task],
        expected_files: list[str] | None = None,
    ) -> str:
        """
        Run a Mini-Crew with fresh context, retry, and recovery.

        Each Mini-Crew gets a fresh agent and fresh LLM context,
        preventing the context overflow that occurs with many sequential tasks.

        Reliability features:
        - Retries with exponential backoff on transient connection errors
        - Logs failure metrics (not just successes) for diagnostics
        - Attempts output file recovery on non-retryable errors
        - Records checkpoint with timing for resume capability

        Args:
            name: Mini-crew identifier for logging/checkpointing.
            tasks: Tasks to execute.
            expected_files: Optional list of output files to validate after
                completion. If files are missing but the result contains
                markdown content, the result is written as a fallback.
        """
        logger.info(f"[{self.crew_name}] Starting Mini-Crew: {name} ({len(tasks)} tasks)")
        start_time = time.time()

        for attempt in range(1, _MAX_RETRIES + 1):
            tracker = None
            try:
                crew = Crew(
                    agents=[tasks[0].agent],
                    tasks=tasks,
                    process=Process.sequential,
                    verbose=True,
                    memory=False,
                    respect_context_window=True,
                    max_rpm=30,
                )
                tracker = install_guardrails()
                result = crew.kickoff(inputs=self.summaries)

                # === SUCCESS ===
                duration = time.time() - start_time
                token_info = self._extract_token_usage(result)
                logger.info(
                    f"[{self.crew_name}] Completed Mini-Crew: {name} "
                    f"({duration:.1f}s, ~{token_info.get('total_tokens', '?')} tokens)"
                )

                result_str = str(result)
                if expected_files:
                    self._validate_and_fallback(name, result_str, expected_files, tracker)

                checkpoint = {
                    "crew": name,
                    "status": "completed",
                    "duration_seconds": round(duration, 1),
                    "tasks": len(tasks),
                    "attempts": attempt,
                    **token_info,
                }
                self._checkpoints.append(checkpoint)
                self._save_checkpoint()

                from ...shared.utils.logger import log_metric

                log_metric(
                    "mini_crew_complete",
                    crew_type=self.crew_name,
                    crew_name=name,
                    duration_seconds=round(duration, 1),
                    tasks=len(tasks),
                    attempts=attempt,
                    total_tokens=token_info.get("total_tokens", 0),
                    estimated=token_info.get("estimated", token_info.get("total_tokens", 0) == 0),
                )
                return result_str

            except (ConnectionError, TimeoutError, OSError) as e:
                # Transient connection error — retry with backoff
                if attempt < _MAX_RETRIES:
                    delay = _RETRY_DELAY_BASE * (2 ** (attempt - 1))
                    logger.warning(
                        f"[{self.crew_name}] {name}: Connection error "
                        f"(attempt {attempt}/{_MAX_RETRIES}), "
                        f"retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)
                    # Fresh agent to avoid stale LLM connections
                    new_agent = self._create_agent()
                    for t in tasks:
                        t.agent = new_agent
                    continue

                # Final attempt failed — recover and continue
                self._handle_crew_failure(name, tasks, e, start_time, expected_files)
                return None  # Recovery done in _handle_crew_failure

            except Exception as e:
                # Non-retryable: Pydantic validation, unexpected errors
                self._handle_crew_failure(name, tasks, e, start_time, expected_files)
                return None  # Recovery done in _handle_crew_failure

            finally:
                if tracker and tracker.calls:
                    from ...shared.utils.logger import log_metric as _log_metric

                    _log_metric(
                        "guardrail_summary",
                        crew_name=name,
                        total_calls=len(tracker.calls),
                        unique_calls=len(set(tracker.calls)),
                        blocked=len(tracker.calls) - len(set(tracker.calls)),
                    )
                uninstall_guardrails(tracker)

        # Should never reach here, but satisfy type checker
        raise RuntimeError(f"Mini-crew {name} failed after {_MAX_RETRIES} attempts")

    def _handle_crew_failure(
        self,
        name: str,
        tasks: list[Task],
        error: Exception,
        start_time: float,
        expected_files: list[str] | None,
    ) -> None:
        """Handle mini-crew failure: log metric, save checkpoint, attempt recovery."""
        duration = time.time() - start_time
        error_type = type(error).__name__
        error_msg = str(error)[:500]
        self._mark_degraded(f"{name}: {error_type}")

        logger.error(f"[{self.crew_name}] Failed Mini-Crew: {name} ({duration:.1f}s, {error_type}): {error_msg}")

        # Log failure metric to metrics.jsonl
        from ...shared.utils.logger import log_metric

        log_metric(
            "mini_crew_failed",
            crew_type=self.crew_name,
            crew_name=name,
            duration_seconds=round(duration, 1),
            tasks=len(tasks),
            error_type=error_type,
            error=error_msg,
        )

        # Attempt to recover missing output files
        if expected_files:
            self._recover_missing_files(name, expected_files)

        # Record failed checkpoint
        self._checkpoints.append(
            {
                "crew": name,
                "status": "failed",
                "duration_seconds": round(duration, 1),
                "tasks": len(tasks),
                "error": error_msg,
            }
        )
        self._save_checkpoint()

    # -------------------------------------------------------------------------
    # OUTPUT VALIDATION
    # -------------------------------------------------------------------------

    @staticmethod
    def _extract_content(result: str) -> str:
        """Extract markdown content from result, handling JSON tool-call wrappers.

        The on-prem model sometimes returns the doc_writer tool-call arguments
        as JSON in its response text instead of actually calling the tool:
            {"file_path": "arc42/05-building-blocks.md", "content": "# 05 ..."}
        This extracts the 'content' field so we write clean markdown.
        """
        stripped = result.strip()
        if stripped.startswith("{") and '"content"' in stripped:
            import re

            match = re.search(r'"content"\s*:\s*"', stripped)
            if match:
                start = match.end()
                raw = stripped[start:].rstrip('"}\n\r\t ').rstrip("\\")
                content = raw.replace("\\n", "\n").replace("\\t", "\t").replace('\\"', '"')
                if len(content) > 200:
                    return content
        return result

    def _validate_and_fallback(self, crew_name: str, result: str, expected_files: list[str], tracker=None) -> None:
        """Check expected output files exist; fallback-write from result if not.

        When the agent writes doc content in its response instead of using
        the doc_writer tool, the crew 'completes' but no file is written.
        This detects that and writes the result as a last resort.

        Also handles JSON-wrapped content where the agent returns the
        tool-call arguments as text instead of actually executing the tool.

        Args:
            crew_name: Name of the mini-crew for logging
            result: The crew's output result as string
            expected_files: List of files that should have been written
            tracker: Optional ToolCallTracker to check if doc_writer was called
        """
        base = self._output_dir
        for file_path in expected_files:
            full = base / file_path

            # Check if file exists and has content (possibly JSON-wrapped)
            if full.exists() and full.stat().st_size > 100:
                # Fix JSON-wrapped files in-place
                try:
                    with open(full, encoding="utf-8") as f:
                        existing = f.read()
                    if existing.strip().startswith("{") and '"content"' in existing:
                        cleaned = self._extract_content(existing)
                        if cleaned != existing:
                            with open(full, "w", encoding="utf-8") as f:
                                f.write(cleaned)
                            logger.info(
                                f"[{self.crew_name}] {crew_name}: Fixed JSON-wrapped {file_path} ({len(cleaned)} chars)"
                            )
                except Exception:
                    pass
                continue

            # File missing — check if doc_writer was even called
            doc_writer_called = False
            if tracker and tracker.calls:
                doc_writer_called = any("doc_writer:" in call for call in tracker.calls)

            if not doc_writer_called:
                self._mark_degraded(f"{crew_name}: missing doc_writer for {file_path}")
                logger.warning(
                    f"[{self.crew_name}] {crew_name}: Agent did NOT call doc_writer! "
                    f"Tool calls made: {len(tracker.calls) if tracker else 0}. "
                    f"Accepting as 'skipped' to allow pipeline continuation."
                )
                # Instead of failing the entire pipeline, create a minimal stub
                # so the pipeline can continue. Phase 3 is optional anyway.
                stub_content = self._create_minimal_stub(file_path, crew_name)
                full.parent.mkdir(parents=True, exist_ok=True)
                with open(full, "w", encoding="utf-8") as f:
                    f.write(stub_content)
                logger.info(
                    f"[{self.crew_name}] {crew_name}: Created minimal stub for {file_path} "
                    f"({len(stub_content)} chars) to allow pipeline continuation."
                )
                continue  # Skip to next expected file

            # doc_writer was called but file still missing — try fallback from result
            content = self._extract_content(result)
            if len(content) > 300 and ("# " in content or "## " in content):
                self._mark_degraded(f"{crew_name}: fallback write for {file_path}")
                logger.warning(
                    f"[{self.crew_name}] {crew_name}: {file_path} NOT written by agent! "
                    f"Fallback-writing {len(content)} chars from result."
                )
                full.parent.mkdir(parents=True, exist_ok=True)
                with open(full, "w", encoding="utf-8") as f:
                    f.write(content)
            else:
                self._mark_degraded(f"{crew_name}: stub fallback for {file_path}")
                logger.warning(
                    f"[{self.crew_name}] {crew_name}: {file_path} NOT written, "
                    f"result too short for fallback ({len(content)} chars). "
                    f"Creating stub to allow pipeline continuation."
                )
                stub_content = self._create_minimal_stub(file_path, crew_name)
                full.parent.mkdir(parents=True, exist_ok=True)
                with open(full, "w", encoding="utf-8") as f:
                    f.write(stub_content)

    def _create_minimal_stub(self, file_path: str, crew_name: str) -> str:
        """Create a minimal stub document when agent fails to call doc_writer.

        This allows the pipeline to continue instead of completely failing.
        The stub includes basic statistics and a note that LLM synthesis failed.

        Args:
            file_path: The expected output file path (e.g., "arc42/05-building-blocks.md")
            crew_name: Name of the mini-crew that failed

        Returns:
            Minimal stub document content as markdown
        """
        chapter_name = file_path.split("/")[-1].replace(".md", "").replace("-", " ").title()

        stats = self.facts.get("statistics", {})
        total_components = stats.get("total_components", 0)
        total_containers = stats.get("total_containers", 0)

        return f"""# {chapter_name}

> **NOTE**: This document was auto-generated as a stub because the AI agent
> failed to produce content for this chapter. The LLM did not call the
> doc_writer tool as instructed.
>
> **Mini-Crew**: {crew_name}
> **File**: {file_path}

## System Overview

The system has {total_components} components across {total_containers} containers.

For detailed architecture information, refer to the facts:
- `knowledge/extract/architecture_facts.json`
- `knowledge/analyze/analyzed_architecture.json`

## Next Steps

This chapter requires manual completion or re-running with a more capable LLM.
"""

    def _recover_missing_files(self, crew_name: str, expected_files: list[str]) -> None:
        """Generate minimal stub documents for missing output files after failure.

        When a mini-crew fails entirely (e.g. Pydantic validation error),
        this creates skeleton documents from facts so the documentation set
        isn't left with gaps. Stubs are clearly marked as auto-generated.
        """
        base = self._output_dir
        facts = self.facts
        system_name = facts.get("system", {}).get("name", "System")

        for file_path in expected_files:
            full = base / file_path
            if full.exists() and full.stat().st_size > 100:
                continue
            if file_path.endswith(".drawio"):
                continue  # Can't auto-generate diagrams

            # Build minimal content from facts
            stem = Path(file_path).stem
            containers = facts.get("containers", [])
            components = facts.get("components", [])

            by_stereo: dict[str, int] = {}
            for comp in components:
                s = comp.get("stereotype", "unknown")
                by_stereo[s] = by_stereo.get(s, 0) + 1

            stats_lines = "\n".join(f"| {s} | {n} |" for s, n in sorted(by_stereo.items()))
            container_lines = "\n".join(f"| {c.get('name', '?')} | {c.get('technology', '?')} |" for c in containers)

            content = (
                f"# {stem}\n\n"
                f"> **Auto-generated stub** — the AI agent failed to produce "
                f"this document. Re-run the pipeline to generate full content.\n\n"
                f"## System: {system_name}\n\n"
                f"### Component Statistics\n\n"
                f"| Stereotype | Count |\n|---|---|\n{stats_lines}\n\n"
                f"### Containers\n\n"
                f"| Name | Technology |\n|---|---|\n{container_lines}\n"
            )

            full.parent.mkdir(parents=True, exist_ok=True)
            with open(full, "w", encoding="utf-8") as f:
                f.write(content)
            self._mark_degraded(f"{crew_name}: recovered stub for {file_path}")
            logger.warning(
                f"[{self.crew_name}] {crew_name}: Recovery-generated stub for {file_path} ({len(content)} chars)"
            )

    def _mark_degraded(self, reason: str) -> None:
        """Record a degradation reason once."""
        if reason not in self._degradation_reasons:
            self._degradation_reasons.append(reason)

    def has_degraded_outputs(self) -> bool:
        """Whether this crew produced degraded output."""
        return bool(self._degradation_reasons)

    def get_degradation_reasons(self) -> list[str]:
        """Get degradation reasons for reporting."""
        return list(self._degradation_reasons)

    # -------------------------------------------------------------------------
    # CHECKPOINT PERSISTENCE
    # -------------------------------------------------------------------------

    def _checkpoint_path(self) -> Path:
        """Path to checkpoint file for this crew."""
        return self._output_dir / f".checkpoint_{self.crew_name.lower()}.json"

    def _save_checkpoint(self) -> None:
        """Save current checkpoints to disk for resume capability."""
        path = self._checkpoint_path()
        data = {
            "crew_name": self.crew_name,
            "checkpoints": self._checkpoints,
            "completed_crews": [c["crew"] for c in self._checkpoints if c["status"] == "completed"],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.debug(f"[{self.crew_name}] Checkpoint saved: {path}")

    def _load_checkpoint(self) -> set[str]:
        """Load completed mini-crew names from checkpoint file.

        Returns set of mini-crew names that completed successfully.
        """
        path = self._checkpoint_path()
        if not path.exists():
            return set()
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            completed = set(data.get("completed_crews", []))
            if completed:
                logger.info(f"[{self.crew_name}] Resuming: {len(completed)} mini-crews already completed")
            return completed
        except Exception:
            return set()

    def _clear_checkpoint(self) -> None:
        """Remove checkpoint file (called on full success)."""
        path = self._checkpoint_path()
        if path.exists():
            path.unlink()
            logger.debug(f"[{self.crew_name}] Checkpoint cleared")

    def should_skip(self, crew_name: str, completed: set[str]) -> bool:
        """Check if a mini-crew should be skipped (already completed in previous run)."""
        if crew_name in completed:
            logger.info(f"[{self.crew_name}] Skipping Mini-Crew: {crew_name} (already completed)")
            return True
        return False

    def get_checkpoints(self) -> list[dict[str, Any]]:
        """Get checkpoint data for all completed mini-crews."""
        return list(self._checkpoints)

    def get_total_duration(self) -> float:
        """Get total execution time across all mini-crews."""
        return sum(c.get("duration_seconds", 0) for c in self._checkpoints)

    # -------------------------------------------------------------------------
    # TOKEN BUDGET TRACKING
    # -------------------------------------------------------------------------

    @staticmethod
    def _extract_token_usage(result: Any) -> dict[str, Any]:
        """Extract token usage from CrewAI result (best-effort)."""
        info: dict[str, Any] = {}
        try:
            # CrewAI stores token usage in result.token_usage
            if hasattr(result, "token_usage"):
                usage = result.token_usage
                if isinstance(usage, dict):
                    info["total_tokens"] = usage.get("total_tokens", 0)
                    info["prompt_tokens"] = usage.get("prompt_tokens", 0)
                    info["completion_tokens"] = usage.get("completion_tokens", 0)
                    return info

            # Fallback: estimate from result text length
            result_str = str(result)
            estimated = len(result_str) // 4  # ~4 chars per token
            info["total_tokens"] = estimated
            info["estimated"] = True
        except Exception:
            info["total_tokens"] = 0
            info["estimated"] = True
        return info

    def get_token_summary(self) -> str:
        """Get human-readable token usage summary across all mini-crews."""
        total = sum(c.get("total_tokens", 0) for c in self._checkpoints)
        budget = self._token_budget
        usage_pct = (total / budget * 100) if budget else 0

        lines = [
            f"Token Budget: {budget:,} tokens",
            f"Total Used:   ~{total:,} tokens ({usage_pct:.0f}%)",
            "",
            "Per Mini-Crew:",
        ]
        for cp in self._checkpoints:
            tokens = cp.get("total_tokens", 0)
            status = cp.get("status", "?")
            est = " (est)" if cp.get("estimated") else ""
            lines.append(f"  {cp['crew']:25s} {status:10s} ~{tokens:,} tokens{est}")

        return "\n".join(lines)
