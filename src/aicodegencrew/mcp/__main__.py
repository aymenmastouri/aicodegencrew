#!/usr/bin/env python3
"""
Direct MCP Server Entry Point

This file allows running the MCP server directly without importing
the main aicodegencrew package (which would log to stdout and corrupt
the JSON-RPC STDIO transport).

Usage:
    python -m aicodegencrew.mcp
"""

# CRITICAL: Do NOT import from aicodegencrew main package here!
# The main package logs to stdout which corrupts STDIO transport.

from .server import run_server

if __name__ == "__main__":
    run_server()
