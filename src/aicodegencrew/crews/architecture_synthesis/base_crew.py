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
- agent_config_key: str property
- _get_extra_tools() -> list (optional)
- _summarize_facts() -> dict
- run() -> str
"""
import json
import logging
import os
import time
import yaml
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from crewai import Agent, Crew, LLM, Process, Task
from crewai.mcp import MCPServerStdio

from .tools import (
    DrawioDiagramTool,
    DocWriterTool,
    FactsQueryTool,
    FileReadTool,
    StereotypeListTool,
)
from ..architecture_analysis.tools import RAGQueryTool

logger = logging.getLogger(__name__)


# Shared tool instruction for all doc-writing tasks
TOOL_INSTRUCTION = """
CRITICAL INSTRUCTION: You MUST use the doc_writer tool to write the output file.
Do NOT include the full document in your response text.
STEP 1: Use MCP tools to gather data.
STEP 2: Use doc_writer(file_path="...", content="...") to write the complete document.
STEP 3: Respond with a brief confirmation that the file was written.
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
        facts_path: str = "knowledge/architecture/architecture_facts.json",
        analyzed_path: str | None = None,
        chroma_dir: str | None = None,
    ):
        self.facts_path = Path(facts_path)
        self.analyzed_path = (
            Path(analyzed_path)
            if analyzed_path
            else self.facts_path.parent / "analyzed_architecture.json"
        )
        self.chroma_dir = chroma_dir or os.getenv("CHROMA_DIR", ".cache/.chroma")

        # Load data
        self.facts = self._load_json(self.facts_path)
        self.analysis = self._load_json(self.analyzed_path)
        self.evidence_map = self._load_json(
            self.facts_path.parent / "evidence_map.json"
        )

        # Build template variables for tasks
        self.summaries = self._summarize_facts()

        # Load agent config from YAML
        agents_yaml_path = Path(self._get_agents_yaml_dir()) / "config" / "agents.yaml"
        with open(agents_yaml_path, "r", encoding="utf-8") as f:
            self.agents_config = yaml.safe_load(f)

        # MCP server config (resolved once, reused across mini-crews)
        self._mcp_server_path = self._resolve_mcp_server_path()

        # Checkpoint tracking
        self._checkpoints: list[dict[str, Any]] = []

        # Token budget tracking
        self._token_budget = int(os.getenv("LLM_CONTEXT_WINDOW", "120000"))
        self._token_usage: list[dict[str, Any]] = []

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
    def agent_config_key(self) -> str:
        """Key in agents.yaml, e.g. 'c4_architect' or 'arc42_architect'."""
        ...

    @abstractmethod
    def _get_agents_yaml_dir(self) -> str:
        """Return directory containing config/agents.yaml."""
        ...

    @abstractmethod
    def _summarize_facts(self) -> dict[str, str]:
        """Create template variables from facts + analysis for task descriptions."""
        ...

    @abstractmethod
    def run(self) -> str:
        """Execute all mini-crews and return summary."""
        ...

    # -------------------------------------------------------------------------
    # DATA LOADING
    # -------------------------------------------------------------------------

    @staticmethod
    def _load_json(path: Path) -> dict:
        """Load JSON file, return empty dict on error."""
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
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
        model = os.getenv("MODEL", "gpt-4o-mini")
        api_base = os.getenv("API_BASE", "")
        max_tokens = int(os.getenv("MAX_LLM_OUTPUT_TOKENS", "4000"))
        context_window = int(os.getenv("LLM_CONTEXT_WINDOW", "120000"))

        if max_tokens < 1:
            max_tokens = 4000

        llm = LLM(
            model=model,
            base_url=api_base,
            temperature=0.1,
            max_tokens=max_tokens,
            timeout=300,
        )
        # Set context window size directly (not via constructor kwargs,
        # which would pass it as additional_params to the API call)
        llm.context_window_size = context_window
        return llm

    # -------------------------------------------------------------------------
    # TOOL FACTORY
    # -------------------------------------------------------------------------

    def _create_base_tools(self) -> list:
        """Create base tool set shared by all synthesis crews."""
        return [
            DrawioDiagramTool(),
            DocWriterTool(),
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
        return Agent(
            config=self.agents_config[self.agent_config_key],
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

    def _run_mini_crew(self, name: str, tasks: list[Task]) -> str:
        """
        Run a Mini-Crew with fresh context.

        Each Mini-Crew gets a fresh agent and fresh LLM context,
        preventing the context overflow that occurs with many sequential tasks.

        Records checkpoint with timing for resume capability.
        """
        logger.info(f"[{self.crew_name}] Starting Mini-Crew: {name} ({len(tasks)} tasks)")
        start_time = time.time()

        crew = Crew(
            agents=[tasks[0].agent],
            tasks=tasks,
            process=Process.sequential,
            verbose=True,
            memory=False,
            respect_context_window=True,
            max_rpm=30,
        )

        try:
            result = crew.kickoff(inputs=self.summaries)
            duration = time.time() - start_time

            # Extract token usage from CrewAI result
            token_info = self._extract_token_usage(result)
            logger.info(
                f"[{self.crew_name}] Completed Mini-Crew: {name} "
                f"({duration:.1f}s, ~{token_info.get('total_tokens', '?')} tokens)"
            )

            # Record checkpoint, persist, and log metric
            checkpoint = {
                "crew": name,
                "status": "completed",
                "duration_seconds": round(duration, 1),
                "tasks": len(tasks),
                **token_info,
            }
            self._checkpoints.append(checkpoint)
            self._save_checkpoint()

            # Structured metric for metrics.jsonl
            from ...shared.utils.logger import log_metric
            log_metric(
                "mini_crew_complete",
                crew_type=self.crew_name,
                crew_name=name,
                duration_seconds=round(duration, 1),
                tasks=len(tasks),
                **token_info,
            )

            return str(result)

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"[{self.crew_name}] Failed Mini-Crew: {name} ({duration:.1f}s): {e}"
            )

            self._checkpoints.append({
                "crew": name,
                "status": "failed",
                "duration_seconds": round(duration, 1),
                "tasks": len(tasks),
                "error": str(e),
            })
            raise

    # -------------------------------------------------------------------------
    # CHECKPOINT PERSISTENCE
    # -------------------------------------------------------------------------

    def _checkpoint_path(self) -> Path:
        """Path to checkpoint file for this crew."""
        return self.facts_path.parent / f".checkpoint_{self.crew_name.lower()}.json"

    def _save_checkpoint(self) -> None:
        """Save current checkpoints to disk for resume capability."""
        path = self._checkpoint_path()
        data = {
            "crew_name": self.crew_name,
            "checkpoints": self._checkpoints,
            "completed_crews": [
                c["crew"] for c in self._checkpoints if c["status"] == "completed"
            ],
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
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            completed = set(data.get("completed_crews", []))
            if completed:
                logger.info(
                    f"[{self.crew_name}] Resuming: {len(completed)} mini-crews already completed"
                )
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
            lines.append(
                f"  {cp['crew']:25s} {status:10s} ~{tokens:,} tokens{est}"
            )

        return "\n".join(lines)
