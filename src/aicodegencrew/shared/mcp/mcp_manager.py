"""
Centralized MCP Server Management for AICodeGenCrew.

Provides configured MCP servers for different phases:
- Sequential Thinking: Complex reasoning (Phase 3, 4)
- Memory: Learning across sessions (Phase 4, 5)
- Brave Search: Technical documentation search (Phase 4, 5)
- Filesystem: Structured file operations (Phase 5)
- Playwright: Web fetching (Phase 4, already integrated)

Usage:
    from aicodegencrew.shared.mcp import get_mcp_servers

    mcps = get_mcp_servers(["sequential_thinking", "memory"])
    agent = Agent(mcps=mcps, ...)
"""

import logging
import os
import shutil
from pathlib import Path
from typing import Literal

from crewai.mcp import MCPServerStdio

logger = logging.getLogger(__name__)

def _npx_available() -> bool:
    """Check if npx is available on the system PATH."""
    return shutil.which("npx") is not None

# MCP server types
MCPServerType = Literal["sequential_thinking", "memory", "brave_search", "filesystem", "playwright", "github", "sovai"]


class MCPManager:
    """Manager for MCP server configurations."""

    def __init__(self, project_root: Path | None = None):
        """
        Initialize MCP manager.

        Args:
            project_root: Project root directory (auto-detected if None)
        """
        if project_root is None:
            # Auto-detect project root
            project_root = Path(__file__).resolve().parent.parent.parent.parent

        self.project_root = project_root
        self.uvz_repo = Path(os.getenv("REPO_PATH", "C:/uvz"))

    def get_sequential_thinking_mcp(self) -> MCPServerStdio:
        """
        Sequential Thinking MCP for complex reasoning.

        Use for: Architecture analysis, multi-step planning decisions
        """
        return MCPServerStdio(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-sequential-thinking"],
            cache_tools_list=True,
        )

    def get_memory_mcp(self) -> MCPServerStdio:
        """
        Memory MCP for persistent learning across sessions.

        Use for: Remembering user preferences, learning from mistakes,
                 project-specific conventions
        """
        return MCPServerStdio(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-memory"],
            cache_tools_list=True,
        )

    def get_brave_search_mcp(self) -> MCPServerStdio:
        """
        Brave Search MCP for technical documentation search.

        Use for: Finding current API docs, migration patterns, examples

        Requires: BRAVE_API_KEY environment variable
                  Get key from: https://brave.com/search/api/
        """
        brave_api_key = os.getenv("BRAVE_API_KEY", "")

        if not brave_api_key:
            raise ValueError(
                "BRAVE_API_KEY environment variable required for Brave Search MCP. "
                "Get API key from: https://brave.com/search/api/"
            )

        return MCPServerStdio(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-brave-search"],
            env={"BRAVE_API_KEY": brave_api_key},
            cache_tools_list=True,
        )

    def get_filesystem_mcp(self, allowed_directories: list[str] | None = None) -> MCPServerStdio:
        """
        Filesystem MCP for structured file operations.

        Use for: Safe file access with permission control

        Args:
            allowed_directories: List of allowed directories.
                                Defaults to [project_root, uvz_repo]
        """
        if allowed_directories is None:
            allowed_directories = [
                str(self.project_root),
                str(self.uvz_repo),
            ]

        return MCPServerStdio(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", *allowed_directories],
            cache_tools_list=True,
        )

    def get_playwright_mcp(self, headless: bool = True, timeout_ms: int = 30000) -> MCPServerStdio:
        """
        Playwright MCP for web fetching.

        Use for: Fetching Angular upgrade guides, documentation

        Args:
            headless: Run in headless mode (default True)
            timeout_ms: Action timeout in milliseconds (default 30000)
        """
        args = ["@playwright/mcp@latest"]

        if headless:
            args.append("--headless")

        args.extend(["--timeout-action", str(timeout_ms), "--isolated"])

        return MCPServerStdio(
            command="npx",
            args=args,
            cache_tools_list=True,
        )

    def get_github_mcp(self) -> MCPServerStdio:
        """
        GitHub MCP for GitHub API access.

        Use for: PR creation, issue management, repository queries

        Requires: GITHUB_TOKEN environment variable
        """
        github_token = os.getenv("GITHUB_TOKEN", "")

        if not github_token:
            raise ValueError(
                "GITHUB_TOKEN environment variable required for GitHub MCP. "
                "Create token at: https://github.com/settings/tokens"
            )

        return MCPServerStdio(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={"GITHUB_TOKEN": github_token},
            cache_tools_list=True,
        )

    def get_sovai_mcp(self) -> MCPServerStdio:
        """
        SovAI MCP for Sovereign AI platform tools.

        Requires: SOVAI_MCP_URL environment variable
        """
        sovai_url = os.getenv("SOVAI_MCP_URL", "")

        if not sovai_url:
            raise ValueError(
                "SOVAI_MCP_URL environment variable required for SovAI MCP."
            )

        return MCPServerStdio(
            command="npx",
            args=["-y", "@sovai/mcp-server"],
            env={"SOVAI_MCP_URL": sovai_url},
            cache_tools_list=True,
        )

    def get_mcp_servers(self, server_types: list[MCPServerType]) -> list[MCPServerStdio]:
        """
        Get multiple MCP servers by type.

        Args:
            server_types: List of MCP server types to get

        Returns:
            List of configured MCPServerStdio instances (empty if npx unavailable)

        Example:
            >>> manager = MCPManager()
            >>> mcps = manager.get_mcp_servers(["sequential_thinking", "memory"])
            >>> agent = Agent(mcps=mcps, ...)
        """
        # Check if HTTP transport is enabled via MCPO
        from .mcp_http_adapter import is_http_transport, mcpo_available

        if is_http_transport() and mcpo_available():
            logger.info("[MCP] Using HTTP transport via MCPO")
            # In HTTP mode, we still return empty — the HTTP adapter is used
            # directly by tools/agents that need MCP functionality.
            # CrewAI's MCPServerStdio is stdio-only; HTTP tools are registered
            # as custom CrewAI tools by the phase crews that need them.
            return []

        if not _npx_available():
            logger.info("[MCP] npx not found — skipping MCP servers (running in Docker?)")
            return []

        servers = []

        dispatch = {
            "sequential_thinking": self.get_sequential_thinking_mcp,
            "memory": self.get_memory_mcp,
            "brave_search": self.get_brave_search_mcp,
            "filesystem": self.get_filesystem_mcp,
            "playwright": self.get_playwright_mcp,
            "github": self.get_github_mcp,
            "sovai": self.get_sovai_mcp,
        }

        for server_type in server_types:
            try:
                factory = dispatch.get(server_type)
                if factory is None:
                    raise ValueError(f"Unknown MCP server type: {server_type}")
                servers.append(factory())
            except ValueError as e:
                # Skip if API key missing, log warning
                logger.warning(f"Skipping {server_type} MCP: {e}")

        return servers


# Convenience functions

_manager = None


def get_mcp_manager() -> MCPManager:
    """Get singleton MCP manager instance."""
    global _manager
    if _manager is None:
        _manager = MCPManager()
    return _manager


def get_mcp_servers(server_types: list[MCPServerType]) -> list[MCPServerStdio]:
    """
    Get configured MCP servers.

    Args:
        server_types: List of server types (e.g., ["sequential_thinking", "memory"])

    Returns:
        List of MCPServerStdio instances

    Example:
        >>> from aicodegencrew.shared.mcp import get_mcp_servers
        >>> mcps = get_mcp_servers(["sequential_thinking", "memory", "brave_search"])
        >>> agent = Agent(mcps=mcps, ...)
    """
    return get_mcp_manager().get_mcp_servers(server_types)


# Phase-specific MCP configurations


def get_phase3_mcps() -> list[MCPServerStdio]:
    """MCPs for Phase 3 (Architecture Analysis)."""
    return get_mcp_servers(["sequential_thinking"])


def get_phase4_mcps() -> list[MCPServerStdio]:
    """MCPs for Phase 4 (Development Planning)."""
    return get_mcp_servers(["sequential_thinking", "memory", "brave_search", "playwright"])


def get_phase5_mcps() -> list[MCPServerStdio]:
    """MCPs for Phase 5 (Code Generation).

    Returns empty list: Phase 5 uses dedicated CrewAI tools (CodeReaderTool,
    CodeWriterTool, ImportIndexTool, etc.) which are purpose-built for code
    generation. MCP filesystem conflicts with these custom tools and causes
    the LLM to call the wrong tool repeatedly (guardrail blocks, iterations
    wasted). Memory/brave_search/playwright add no value for code generation.
    """
    return []


def get_phase8_mcps() -> list[MCPServerStdio]:
    """MCPs for Phase 8 (Delivery - PR/Issue creation)."""
    return get_mcp_servers(["github", "memory"])
