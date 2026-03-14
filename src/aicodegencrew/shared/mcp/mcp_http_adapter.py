"""MCP HTTP Transport Adapter — routes MCP tool calls through MCPO HTTP proxy.

When MCP_TRANSPORT=http and MCPO_URL is set, this adapter wraps MCP server
tool calls as HTTP requests to the MCPO proxy instead of stdio subprocesses.

Falls back to a CrewAI-compatible custom tool wrapper if CrewAI's native
MCP support does not handle HTTP transport.

Env vars:
    MCPO_URL: MCPO HTTP proxy base URL (e.g. http://localhost:8080)
    MCP_TRANSPORT: "stdio" (default) or "http"
"""

import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)


class MCPHttpAdapter:
    """Adapter that proxies MCP tool calls via MCPO HTTP endpoint.

    Usage:
        adapter = MCPHttpAdapter(server_name="sequential_thinking")
        result = adapter.call_tool("think", {"thought": "..."})
    """

    def __init__(self, server_name: str):
        self.server_name = server_name
        self.base_url = os.getenv("MCPO_URL", "").strip().rstrip("/")
        if not self.base_url:
            raise ValueError("MCPO_URL environment variable is required for HTTP transport")

    def call_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """Call an MCP tool via MCPO HTTP proxy."""
        url = f"{self.base_url}/{self.server_name}/tools/{tool_name}"
        try:
            response = requests.post(url, json=arguments or {}, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            logger.error("[MCPO] HTTP tool call failed: %s/%s — %s", self.server_name, tool_name, exc)
            return {"error": str(exc)}

    def list_tools(self) -> list[dict[str, Any]]:
        """List available tools on this MCP server via MCPO."""
        url = f"{self.base_url}/{self.server_name}/tools"
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json().get("tools", [])
        except requests.RequestException as exc:
            logger.error("[MCPO] Failed to list tools for %s: %s", self.server_name, exc)
            return []


def is_http_transport() -> bool:
    """Check if MCP_TRANSPORT is set to HTTP mode."""
    return os.getenv("MCP_TRANSPORT", "stdio").strip().lower() == "http"


def mcpo_available() -> bool:
    """Check if MCPO URL is configured."""
    return bool(os.getenv("MCPO_URL", "").strip())
