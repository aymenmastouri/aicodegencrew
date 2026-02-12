"""
CrewAI Integration for AICodeGenCrew Knowledge MCP Server

This module provides easy integration of the Knowledge MCP Server
with CrewAI agents using the recommended DSL approach.

Usage with Simple DSL (Recommended):
    from crewai import Agent
    from crewai.mcp import MCPServerStdio

    agent = Agent(
        role="Architecture Analyst",
        goal="Analyze codebase architecture",
        mcps=[
            MCPServerStdio(
                command="python",
                args=["-m", "aicodegencrew.mcp.server"],
            )
        ]
    )

Usage with MCPServerAdapter (Advanced):
    from aicodegencrew.mcp.crewai_integration import get_knowledge_mcp_tools

    tools = get_knowledge_mcp_tools()
    agent = Agent(
        role="Architecture Analyst",
        tools=tools
    )
"""

import os
import sys
from typing import Any

# Check if crewai-tools with MCP support is available
try:
    from crewai_tools import MCPServerAdapter
    from mcp import StdioServerParameters

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


def get_mcp_server_params(
    knowledge_path: str | None = None, python_executable: str | None = None
) -> "StdioServerParameters":
    """
    Get StdioServerParameters for the Knowledge MCP Server.

    Args:
        knowledge_path: Optional path to knowledge directory.
            If not provided, uses current working directory.
        python_executable: Optional Python executable path.
            If not provided, uses sys.executable.

    Returns:
        StdioServerParameters configured for the Knowledge MCP Server.

    Example:
        from crewai.mcp import MCPServerStdio
        from aicodegencrew.mcp.crewai_integration import get_mcp_server_params

        params = get_mcp_server_params()
        # Use with MCPServerStdio or MCPServerAdapter
    """
    if not MCP_AVAILABLE:
        raise ImportError("MCP support not available. Install with: pip install 'crewai-tools[mcp]' mcp")

    python_exe = python_executable or sys.executable

    env = {**os.environ}
    if knowledge_path:
        env["AICODEGENCREW_KNOWLEDGE_PATH"] = knowledge_path

    return StdioServerParameters(command=python_exe, args=["-m", "aicodegencrew.mcp.server"], env=env)


def get_knowledge_mcp_tools(
    knowledge_path: str | None = None, tool_names: list[str] | None = None, connect_timeout: int = 60
) -> list[Any]:
    """
    Get Knowledge MCP tools for use with CrewAI agents.

    This function starts the MCP server and returns the tools.
    Use within a context manager or ensure proper cleanup.

    Args:
        knowledge_path: Optional path to knowledge directory.
        tool_names: Optional list of specific tools to include.
            Available tools:
            - get_component
            - get_component_by_id
            - list_components_by_stereotype
            - list_components_by_layer
            - search_components
            - get_relations_for
            - get_call_graph
            - get_endpoints
            - get_endpoint_by_path
            - get_routes
            - get_evidence
            - get_evidence_for_component
            - get_architecture_summary
            - get_statistics
        connect_timeout: Connection timeout in seconds (default: 60)

    Returns:
        List of MCP tools ready to use with CrewAI agents.

    Example:
        from aicodegencrew.mcp.crewai_integration import get_knowledge_mcp_tools

        # Get all tools
        with MCPServerAdapter(get_mcp_server_params()) as tools:
            agent = Agent(role="Analyst", tools=tools)

        # Or get specific tools
        with MCPServerAdapter(get_mcp_server_params(), "get_component", "get_relations_for") as tools:
            agent = Agent(role="Analyst", tools=tools)
    """
    if not MCP_AVAILABLE:
        raise ImportError("MCP support not available. Install with: pip install 'crewai-tools[mcp]' mcp")

    server_params = get_mcp_server_params(knowledge_path)

    if tool_names:
        adapter = MCPServerAdapter(server_params, *tool_names, connect_timeout=connect_timeout)
    else:
        adapter = MCPServerAdapter(server_params, connect_timeout=connect_timeout)

    return adapter


class KnowledgeMCPContext:
    """
    Context manager for Knowledge MCP tools.

    Example:
        from aicodegencrew.mcp.crewai_integration import KnowledgeMCPContext

        with KnowledgeMCPContext() as tools:
            agent = Agent(
                role="Architecture Analyst",
                goal="Analyze the codebase architecture",
                tools=tools
            )
            # ... use agent
    """

    def __init__(
        self, knowledge_path: str | None = None, tool_names: list[str] | None = None, connect_timeout: int = 60
    ):
        self.knowledge_path = knowledge_path
        self.tool_names = tool_names
        self.connect_timeout = connect_timeout
        self._adapter = None

    def __enter__(self) -> list[Any]:
        if not MCP_AVAILABLE:
            raise ImportError("MCP support not available. Install with: pip install 'crewai-tools[mcp]' mcp")

        server_params = get_mcp_server_params(self.knowledge_path)

        if self.tool_names:
            self._adapter = MCPServerAdapter(server_params, *self.tool_names, connect_timeout=self.connect_timeout)
        else:
            self._adapter = MCPServerAdapter(server_params, connect_timeout=self.connect_timeout)

        self._adapter.start()
        return self._adapter.tools

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._adapter and self._adapter.is_connected:
            self._adapter.stop()
        return False


# Convenience function for CrewBase integration
def get_mcp_server_config(knowledge_path: str | None = None) -> dict:
    """
    Get MCP server configuration for CrewBase.

    Example:
        @CrewBase
        class ArchitectureCrew:
            mcp_server_params = [get_mcp_server_config()]

            @agent
            def analyst(self):
                return Agent(
                    config=self.agents_config["analyst"],
                    tools=self.get_mcp_tools()
                )
    """
    python_exe = sys.executable

    config = {
        "command": python_exe,
        "args": ["-m", "aicodegencrew.mcp.server"],
    }

    if knowledge_path:
        config["env"] = {"AICODEGENCREW_KNOWLEDGE_PATH": knowledge_path}

    return config
