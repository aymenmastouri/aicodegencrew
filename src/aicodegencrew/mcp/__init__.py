# MCP Server for AICodeGenCrew Knowledge Base
"""
Model Context Protocol (MCP) server that exposes Phase 1 architecture facts
as structured tools for LLM agents.

Solves the token limit problem by providing targeted queries instead of
dumping entire codebase into context.
"""

from .server import create_server, run_server
from .knowledge_tools import KnowledgeTools

__all__ = ["create_server", "run_server", "KnowledgeTools"]
