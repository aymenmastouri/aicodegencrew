# MCP Server for AICodeGenCrew Knowledge Base
"""
Model Context Protocol (MCP) server that exposes Phase 1 architecture facts
as structured tools for LLM agents.

Solves the token limit problem by providing targeted queries instead of
dumping entire codebase into context.
"""

from .knowledge_tools import KnowledgeTools
from .server import create_server, run_server

__all__ = ["KnowledgeTools", "create_server", "run_server"]
