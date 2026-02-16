"""Implement Crew: Agent definitions with dual-model routing.

Manager + Builder  -> MODEL (gpt-oss-120B) — analysis, coordination
Developer + Tester -> CODEGEN_MODEL (Coder 14B) — code generation
"""

from __future__ import annotations

from typing import Any

from crewai import Agent
from crewai.mcp import MCPServerStdio

from ...shared.utils.llm_factory import create_codegen_llm, create_llm

AGENT_CONFIGS = {
    "manager": {
        "role": "Technical Project Manager",
        "goal": (
            "Coordinate implementation work from plan to passing build and tests. "
            "Delegate coding, testing and build analysis to specialist agents and "
            "approve only coherent, buildable outputs."
        ),
        "backstory": (
            "You are a senior technical lead responsible for delivery quality. "
            "You read the development plan first, break work into concrete actions, "
            "delegate to specialists, and enforce strict scope control. "
            "Do not accept incomplete outputs; require concrete tool results."
        ),
        "allow_delegation": True,
        "llm_tier": "analysis",
    },
    "developer": {
        "role": "Senior Software Developer",
        "goal": (
            "Implement code changes that match existing architecture and style. "
            "Use import and dependency lookup tools before writing code."
        ),
        "backstory": (
            "You are a pragmatic full-stack developer. You always read existing files "
            "before writing, preserve local conventions, and produce complete file content. "
            "You do not invent APIs or imports — you look them up with the import index tool."
        ),
        "allow_delegation": False,
        "llm_tier": "codegen",
    },
    "tester": {
        "role": "Senior Test Engineer",
        "goal": (
            "Generate unit tests matching repository patterns for changed code."
        ),
        "backstory": (
            "You build realistic, maintainable tests by reusing established project patterns. "
            "You always inspect existing tests before writing new ones."
        ),
        "allow_delegation": False,
        "llm_tier": "codegen",
    },
    "builder": {
        "role": "DevOps Build Engineer",
        "goal": (
            "Run builds for affected containers, parse failures, and report actionable errors."
        ),
        "backstory": (
            "You are responsible for compilation and CI readiness. "
            "You verify baseline health, run builds with staged changes, and provide "
            "structured diagnostics with file/line context."
        ),
        "allow_delegation": False,
        "llm_tier": "analysis",
    },
}


def create_agent(
    agent_key: str,
    tools: list[Any],
    mcp_server_path: str | None = None,
    verbose: bool = True,
) -> Agent:
    """Create a CrewAI Agent from config with dual-model routing.

    Args:
        agent_key: One of 'manager', 'developer', 'tester', 'builder'.
        tools: List of CrewAI tool instances for this agent.
        mcp_server_path: Path to the MCP server script (optional).
        verbose: Enable verbose logging.

    Returns:
        Configured CrewAI Agent.
    """
    cfg = AGENT_CONFIGS[agent_key]

    if cfg["llm_tier"] == "codegen":
        try:
            llm = create_codegen_llm()
        except Exception:
            llm = create_llm()
    else:
        llm = create_llm()

    mcps = []
    if mcp_server_path:
        mcps.append(MCPServerStdio(
            command="python",
            args=[mcp_server_path],
            cache_tools_list=True,
        ))

    return Agent(
        role=cfg["role"],
        goal=cfg["goal"],
        backstory=cfg["backstory"],
        llm=llm,
        tools=tools,
        mcps=mcps,
        verbose=verbose,
        max_iter=25,
        max_retry_limit=3,
        allow_delegation=cfg.get("allow_delegation", False),
        respect_context_window=True,
    )
