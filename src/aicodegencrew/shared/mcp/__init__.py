"""
MCP (Model Context Protocol) Server Management.

Centralized configuration for all MCP servers used in AICodeGenCrew.
"""

from .mcp_manager import (
    MCPManager,
    get_mcp_manager,
    get_mcp_servers,
    get_phase3_mcps,
    get_phase4_mcps,
    get_phase5_mcps,
    get_phase8_mcps,
)

__all__ = [
    "MCPManager",
    "get_mcp_manager",
    "get_mcp_servers",
    "get_phase3_mcps",
    "get_phase4_mcps",
    "get_phase5_mcps",
    "get_phase8_mcps",
]
