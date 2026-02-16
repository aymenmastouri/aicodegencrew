"""
MCP Registry - Central registration of all MCP servers with metadata.

This registry provides:
1. Metadata for each MCP (name, description, status, tools)
2. Dashboard integration (for frontend display)
3. Runtime status tracking
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class MCPStatus(str, Enum):
    """MCP server status."""
    AVAILABLE = "available"  # MCP is configured and can be used
    REQUIRES_API_KEY = "requires_api_key"  # Needs API key in env
    NOT_INSTALLED = "not_installed"  # npm package not found
    RUNNING = "running"  # Currently active in a crew
    ERROR = "error"  # Error occurred


@dataclass
class MCPMetadata:
    """Metadata for an MCP server (for dashboard display)."""

    # Identity
    id: str  # Unique ID (e.g., "sequential_thinking")
    name: str  # Display name (e.g., "Sequential Thinking")
    package: str  # npm package (e.g., "@modelcontextprotocol/server-sequential-thinking")

    # Description
    description: str  # Short description
    use_cases: list[str]  # List of use cases
    phases: list[int]  # Phases that use this MCP (e.g., [3, 4])

    # Requirements
    requires_api_key: bool  # Whether API key is needed
    api_key_env_var: str | None  # Env var name (e.g., "BRAVE_API_KEY")
    api_key_url: str | None  # URL to get API key

    # Tools provided
    tools: list[str]  # Tool names (e.g., ["playwright_navigate", "playwright_snapshot"])

    # Status
    status: MCPStatus  # Current status

    # Configuration
    command: str  # Command to run (e.g., "npx")
    args: list[str]  # Default arguments


# =============================================================================
# MCP Definitions (Dashboard will read this)
# =============================================================================

MCP_REGISTRY: dict[str, MCPMetadata] = {
    "sequential_thinking": MCPMetadata(
        id="sequential_thinking",
        name="Sequential Thinking",
        package="@modelcontextprotocol/server-sequential-thinking",
        description="Complex multi-step reasoning and analysis",
        use_cases=[
            "Architecture pattern analysis",
            "Multi-step planning decisions",
            "Complex dependency resolution",
            "Trade-off evaluation"
        ],
        phases=[3, 4],  # Phase 3 (Analyze), Phase 4 (Plan)
        requires_api_key=False,
        api_key_env_var=None,
        api_key_url=None,
        tools=[
            "sequential_think",
            "sequential_analyze",
            "sequential_reason"
        ],
        status=MCPStatus.AVAILABLE,
        command="npx",
        args=["-y", "@modelcontextprotocol/server-sequential-thinking"],
    ),

    "memory": MCPMetadata(
        id="memory",
        name="Memory",
        package="@modelcontextprotocol/server-memory",
        description="Persistent learning across sessions",
        use_cases=[
            "Remember user preferences",
            "Learn from past mistakes",
            "Store project conventions",
            "Track successful patterns"
        ],
        phases=[4, 5],  # Phase 4 (Plan), Phase 5 (Implement)
        requires_api_key=False,
        api_key_env_var=None,
        api_key_url=None,
        tools=[
            "memory_store",
            "memory_retrieve",
            "memory_search",
            "memory_delete"
        ],
        status=MCPStatus.AVAILABLE,
        command="npx",
        args=["-y", "@modelcontextprotocol/server-memory"],
    ),

    "brave_search": MCPMetadata(
        id="brave_search",
        name="Brave Search",
        package="@modelcontextprotocol/server-brave-search",
        description="Search technical documentation and APIs",
        use_cases=[
            "Find current API documentation",
            "Search migration patterns",
            "Look up error solutions",
            "Discover best practices"
        ],
        phases=[4, 5],  # Phase 4 (Plan), Phase 5 (Implement)
        requires_api_key=True,
        api_key_env_var="BRAVE_API_KEY",
        api_key_url="https://brave.com/search/api/",
        tools=[
            "brave_web_search",
            "brave_local_search"
        ],
        status=MCPStatus.REQUIRES_API_KEY,  # Will be AVAILABLE if key is set
        command="npx",
        args=["-y", "@modelcontextprotocol/server-brave-search"],
    ),

    "filesystem": MCPMetadata(
        id="filesystem",
        name="Filesystem",
        package="@modelcontextprotocol/server-filesystem",
        description="Structured file operations with permissions",
        use_cases=[
            "Safe file reading/writing",
            "Directory traversal",
            "File search",
            "Permission-controlled access"
        ],
        phases=[5],  # Phase 5 (Implement)
        requires_api_key=False,
        api_key_env_var=None,
        api_key_url=None,
        tools=[
            "read_file",
            "write_file",
            "list_directory",
            "search_files",
            "get_file_info"
        ],
        status=MCPStatus.AVAILABLE,
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem"],
    ),

    "playwright": MCPMetadata(
        id="playwright",
        name="Playwright",
        package="@playwright/mcp",
        description="Web content fetching with JavaScript rendering",
        use_cases=[
            "Fetch Angular upgrade guides",
            "Extract documentation from SPAs",
            "Web scraping",
            "Page screenshots"
        ],
        phases=[4],  # Phase 4 (Plan)
        requires_api_key=False,
        api_key_env_var=None,
        api_key_url=None,
        tools=[
            "playwright_navigate",
            "playwright_snapshot",
            "playwright_click",
            "playwright_fill",
            "playwright_screenshot"
        ],
        status=MCPStatus.AVAILABLE,
        command="npx",
        args=["@playwright/mcp@latest", "--headless", "--timeout-action", "30000", "--isolated"],
    ),

    "github": MCPMetadata(
        id="github",
        name="GitHub",
        package="@modelcontextprotocol/server-github",
        description="GitHub API integration for PR/Issue management",
        use_cases=[
            "Create pull requests",
            "Create/update issues",
            "Query repository data",
            "Manage labels/milestones"
        ],
        phases=[8],  # Phase 8 (Deliver)
        requires_api_key=True,
        api_key_env_var="GITHUB_TOKEN",
        api_key_url="https://github.com/settings/tokens",
        tools=[
            "github_create_pr",
            "github_create_issue",
            "github_list_prs",
            "github_update_pr",
            "github_search_code"
        ],
        status=MCPStatus.REQUIRES_API_KEY,
        command="npx",
        args=["-y", "@modelcontextprotocol/server-github"],
    ),
}


# =============================================================================
# Registry Functions (for dashboard API)
# =============================================================================

def get_all_mcps() -> dict[str, MCPMetadata]:
    """Get all registered MCPs (for dashboard display)."""
    return MCP_REGISTRY


def get_mcp_by_id(mcp_id: str) -> MCPMetadata | None:
    """Get MCP metadata by ID."""
    return MCP_REGISTRY.get(mcp_id)


def get_mcps_by_phase(phase: int) -> list[MCPMetadata]:
    """Get all MCPs used in a specific phase."""
    return [mcp for mcp in MCP_REGISTRY.values() if phase in mcp.phases]


def get_mcp_status_summary() -> dict[str, Any]:
    """
    Get summary of MCP status (for dashboard).

    Returns:
        {
            "total": 6,
            "available": 4,
            "requires_api_key": 2,
            "by_phase": {3: ["sequential_thinking"], 4: [...], ...}
        }
    """
    import os

    # Update status based on API keys
    for mcp in MCP_REGISTRY.values():
        if mcp.requires_api_key and mcp.api_key_env_var:
            if os.getenv(mcp.api_key_env_var):
                mcp.status = MCPStatus.AVAILABLE
            else:
                mcp.status = MCPStatus.REQUIRES_API_KEY

    # Count by status
    status_counts = {}
    for mcp in MCP_REGISTRY.values():
        status = mcp.status.value
        status_counts[status] = status_counts.get(status, 0) + 1

    # Group by phase
    by_phase = {}
    for mcp in MCP_REGISTRY.values():
        for phase in mcp.phases:
            if phase not in by_phase:
                by_phase[phase] = []
            by_phase[phase].append(mcp.id)

    return {
        "total": len(MCP_REGISTRY),
        **status_counts,
        "by_phase": by_phase,
    }
