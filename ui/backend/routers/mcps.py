"""
MCP Registry API Routes.

Provides endpoints for dashboard to query MCP server status and metadata.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from aicodegencrew.shared.mcp.registry import (
    MCPMetadata,
    MCPStatus,
    get_all_mcps,
    get_mcp_by_id,
    get_mcps_by_phase,
    get_mcp_status_summary,
)

router = APIRouter(prefix="/api/mcps", tags=["MCPs"])


# =============================================================================
# Response Models
# =============================================================================


class MCPMetadataResponse(BaseModel):
    """MCP metadata response for API."""

    id: str
    name: str
    package: str
    description: str
    use_cases: list[str]
    phases: list[int]
    requires_api_key: bool
    api_key_env_var: str | None
    api_key_url: str | None
    tools: list[str]
    status: MCPStatus
    command: str
    args: list[str]


class MCPStatusSummaryResponse(BaseModel):
    """MCP status summary response."""

    total: int
    available: int = 0
    requires_api_key: int = 0
    not_installed: int = 0
    running: int = 0
    error: int = 0
    by_phase: dict[int, list[str]]


class MCPListResponse(BaseModel):
    """Response for listing all MCPs."""

    mcps: list[MCPMetadataResponse]
    summary: MCPStatusSummaryResponse


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/", response_model=MCPListResponse)
async def list_mcps():
    """
    Get all registered MCP servers with metadata.

    Returns list of all MCPs with their status, tools, and configuration.
    Used by dashboard to display MCP overview page.
    """
    mcps_dict = get_all_mcps()
    summary = get_mcp_status_summary()

    mcps_list = [
        MCPMetadataResponse(
            id=mcp.id,
            name=mcp.name,
            package=mcp.package,
            description=mcp.description,
            use_cases=mcp.use_cases,
            phases=mcp.phases,
            requires_api_key=mcp.requires_api_key,
            api_key_env_var=mcp.api_key_env_var,
            api_key_url=mcp.api_key_url,
            tools=mcp.tools,
            status=mcp.status,
            command=mcp.command,
            args=mcp.args,
        )
        for mcp in mcps_dict.values()
    ]

    return MCPListResponse(
        mcps=mcps_list,
        summary=MCPStatusSummaryResponse(**summary),
    )


@router.get("/summary", response_model=MCPStatusSummaryResponse)
async def get_summary():
    """
    Get MCP status summary.

    Returns counts by status and grouping by phase.
    Used for dashboard widgets and statistics.
    """
    summary = get_mcp_status_summary()
    return MCPStatusSummaryResponse(**summary)


@router.get("/{mcp_id}", response_model=MCPMetadataResponse)
async def get_mcp(mcp_id: str):
    """
    Get detailed information about a specific MCP server.

    Args:
        mcp_id: MCP identifier (e.g., "sequential_thinking")

    Returns:
        Detailed MCP metadata

    Raises:
        404: MCP not found
    """
    mcp = get_mcp_by_id(mcp_id)

    if not mcp:
        raise HTTPException(status_code=404, detail=f"MCP '{mcp_id}' not found")

    return MCPMetadataResponse(
        id=mcp.id,
        name=mcp.name,
        package=mcp.package,
        description=mcp.description,
        use_cases=mcp.use_cases,
        phases=mcp.phases,
        requires_api_key=mcp.requires_api_key,
        api_key_env_var=mcp.api_key_env_var,
        api_key_url=mcp.api_key_url,
        tools=mcp.tools,
        status=mcp.status,
        command=mcp.command,
        args=mcp.args,
    )


@router.get("/by-phase/{phase}", response_model=list[MCPMetadataResponse])
async def get_mcps_for_phase(phase: int):
    """
    Get all MCPs used in a specific phase.

    Args:
        phase: Phase number (3, 4, 5, 8, etc.)

    Returns:
        List of MCPs used in this phase
    """
    mcps = get_mcps_by_phase(phase)

    return [
        MCPMetadataResponse(
            id=mcp.id,
            name=mcp.name,
            package=mcp.package,
            description=mcp.description,
            use_cases=mcp.use_cases,
            phases=mcp.phases,
            requires_api_key=mcp.requires_api_key,
            api_key_env_var=mcp.api_key_env_var,
            api_key_url=mcp.api_key_url,
            tools=mcp.tools,
            status=mcp.status,
            command=mcp.command,
            args=mcp.args,
        )
        for mcp in mcps
    ]
