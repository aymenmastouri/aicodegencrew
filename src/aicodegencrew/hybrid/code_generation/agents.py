"""Implement Crew: Single developer agent for Phase 5 v3.

One agent handles all code generation. Build verification is Python-controlled.
"""

from __future__ import annotations

from typing import Any

from crewai import Agent
from crewai.mcp import MCPServerStdio

from ...shared.utils.llm_factory import create_llm

AGENT_CONFIGS = {
    "developer": {
        "role": "Senior Software Developer",
        "goal": (
            "Implement code changes that match existing architecture and style. "
            "Read the original task source first, then use import and dependency "
            "lookup tools before writing code. Produce complete file content."
        ),
        "backstory": (
            "You are a pragmatic full-stack developer working on a large enterprise "
            "codebase. You ALWAYS follow this workflow for EVERY file:\n"
            "1. Read the original task source to understand intent\n"
            "2. Read existing files before modifying them\n"
            "3. Preserve external dependency imports (node_modules, Maven jars) from the original file\n"
            "4. Use lookup_import() for internal/project imports only\n"
            "5. Check dependency order\n"
            "6. Write COMPLETE file content via write_code()\n"
            "7. Process ALL files in the task - never skip files\n\n"
            "CRITICAL: You NEVER skip files just because external imports can't be resolved. "
            "External imports (npm packages, Maven dependencies) should be preserved from the original file. "
            "Only use lookup_import() for project-internal symbols. "
            "You handle Java (Spring Boot), TypeScript/JavaScript, HTML, SCSS, and config files."
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
    """Create a CrewAI Agent from config.

    Args:
        agent_key: Agent config key (currently only 'developer').
        tools: List of CrewAI tool instances for this agent.
        mcp_server_path: Path to the MCP server script (optional).
        verbose: Enable verbose logging.

    Returns:
        Configured CrewAI Agent.
    """
    cfg = AGENT_CONFIGS[agent_key]
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
