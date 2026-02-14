"""
AICodeGenCrew Knowledge MCP Server

A Model Context Protocol (MCP) server that exposes Phase 1 architecture facts
as tools for LLM agents. This solves the token limit problem by providing
targeted queries instead of dumping entire codebase into context.

Usage:
    # Run standalone for testing
    python -m aicodegencrew.mcp.server

    # Or via uv
    uv run python -m aicodegencrew.mcp.server

Best Practices (from MCP docs):
    - NEVER use print() - it corrupts JSON-RPC on STDIO
    - Use logging to stderr instead
    - Validate all tool inputs
    - Return structured JSON responses

CRITICAL: This module MUST NOT import from aicodegencrew main package!
          The main package logs to stdout which corrupts STDIO transport.
"""

import json
import logging
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .knowledge_tools import KnowledgeConfig, KnowledgeTools

# Configure logging to stderr (CRITICAL: never use stdout for STDIO servers!)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", stream=sys.stderr
)
logger = logging.getLogger("aicodegencrew.mcp")

# Initialize FastMCP server
mcp = FastMCP("aicodegencrew-knowledge")

# Global knowledge tools instance (initialized on first use)
_knowledge_tools: KnowledgeTools | None = None


def get_knowledge_tools() -> KnowledgeTools:
    """Get or create the knowledge tools instance."""
    global _knowledge_tools
    if _knowledge_tools is None:
        # Try to find knowledge directory
        knowledge_path = Path.cwd() / "knowledge" / "architecture"
        if not knowledge_path.exists():
            # Try parent directories
            for parent in Path.cwd().parents:
                candidate = parent / "knowledge" / "architecture"
                if candidate.exists():
                    knowledge_path = candidate
                    break

        config = KnowledgeConfig(knowledge_path=knowledge_path)
        _knowledge_tools = KnowledgeTools(config)
        logger.info(f"Knowledge tools initialized from: {knowledge_path}")

    return _knowledge_tools


# ========== Component Tools ==========


@mcp.tool()
def get_component(name: str) -> str:
    """
    Get a component by name (case-insensitive partial match).

    Args:
        name: Component name or partial name (e.g., "WorkflowController", "UserService")

    Returns:
        Component details including ID, stereotype, layer, module, and file paths.
        If multiple matches, returns a list of candidates.
    """
    tools = get_knowledge_tools()
    result = tools.get_component(name)
    return json.dumps(result, indent=2)


@mcp.tool()
def get_component_by_id(component_id: str) -> str:
    """
    Get a component by exact ID.

    Args:
        component_id: Full component ID (e.g., "component.backend.service.workflow_service")

    Returns:
        Complete component details or error if not found.
    """
    tools = get_knowledge_tools()
    result = tools.get_component_by_id(component_id)
    return json.dumps(result, indent=2)


@mcp.tool()
def list_components_by_stereotype(stereotype: str) -> str:
    """
    List all components of a given stereotype.

    Args:
        stereotype: Component stereotype - one of:
            - "service" (168 components)
            - "controller" (32 components)
            - "repository" (38 components)
            - "entity" (199 components)
            - "component" (128 Angular components)
            - "rest_interface" (21 REST interfaces)
            - "module" (16 Angular modules)
            - "pipe" (67 Angular pipes)
            - "adapter" (50 adapters)

    Returns:
        List of components with ID, name, and layer.
    """
    tools = get_knowledge_tools()
    result = tools.list_components_by_stereotype(stereotype)
    return json.dumps(result, indent=2)


@mcp.tool()
def list_components_by_layer(layer: str) -> str:
    """
    List all components in a given architectural layer.

    Args:
        layer: Architecture layer - one of:
            - "presentation" (246 components - UI/Controllers)
            - "application" (168 components - Services)
            - "domain" (199 components - Entities)
            - "dataaccess" (38 components - Repositories)
            - "infrastructure" (1 component - Configuration)
            - "unknown" (81 components - Other)

    Returns:
        List of components with ID, name, and stereotype.
    """
    tools = get_knowledge_tools()
    result = tools.list_components_by_layer(layer)
    return json.dumps(result, indent=2)


@mcp.tool()
def search_components(pattern: str) -> str:
    """
    Search components by regex pattern.

    Args:
        pattern: Regex pattern to match against name, module, or file path.
            Examples:
            - "Workflow.*Service" - all workflow-related services
            - ".*Controller$" - all controllers
            - "deed.*" - anything related to deeds

    Returns:
        List of matching components (max 50 results).
    """
    tools = get_knowledge_tools()
    result = tools.search_components(pattern)
    return json.dumps(result, indent=2)


# ========== Relation Tools ==========


@mcp.tool()
def get_relations_for(component: str) -> str:
    """
    Get all relations for a component (incoming and outgoing).

    Args:
        component: Component name or full ID.
            Examples: "WorkflowService", "component.backend.service.workflow_service"

    Returns:
        Outgoing relations (what this component uses) and
        incoming relations (what uses this component).
    """
    tools = get_knowledge_tools()
    result = tools.get_relations_for(component)
    return json.dumps(result, indent=2)


@mcp.tool()
def get_call_graph(component: str, depth: int = 2) -> str:
    """
    Get the call graph for a component up to specified depth.

    Args:
        component: Component name or full ID to start from.
        depth: How many levels deep to traverse (default: 2, max recommended: 3).

    Returns:
        Graph with nodes (components) and edges (relations).
        Useful for understanding impact of changes.
    """
    tools = get_knowledge_tools()
    # Limit depth to prevent huge responses
    depth = min(depth, 4)
    result = tools.get_call_graph(component, depth)
    return json.dumps(result, indent=2)


# ========== Interface Tools ==========


@mcp.tool()
def get_endpoints(path_pattern: str = None) -> str:
    """
    Get REST endpoints, optionally filtered by path pattern.

    Args:
        path_pattern: Optional regex to filter paths.
            Examples:
            - "/workflow.*" - all workflow endpoints
            - "/api/v1/action.*" - action API endpoints
            - None - all REST endpoints

    Returns:
        List of endpoints with path, method, and implementing component.
    """
    tools = get_knowledge_tools()
    result = tools.get_endpoints(path_pattern)
    return json.dumps(result, indent=2)


@mcp.tool()
def get_endpoint_by_path(path: str, method: str = None) -> str:
    """
    Get endpoint details by exact path.

    Args:
        path: Exact API path (e.g., "/api/v1/resource/{id}")
        method: Optional HTTP method (GET, POST, PUT, DELETE, PATCH)

    Returns:
        Complete endpoint details including implementing component.
    """
    tools = get_knowledge_tools()
    result = tools.get_endpoint_by_path(path, method)
    return json.dumps(result, indent=2)


@mcp.tool()
def get_routes() -> str:
    """
    Get all frontend routes (Angular).

    Returns:
        List of 29 frontend routes with paths.
    """
    tools = get_knowledge_tools()
    result = tools.get_routes()
    return json.dumps(result, indent=2)


# ========== Evidence Tools ==========


@mcp.tool()
def get_evidence(evidence_id: str) -> str:
    """
    Get evidence by ID (the actual code snippet).

    Args:
        evidence_id: Evidence ID (e.g., "ev_123")

    Returns:
        Evidence details including file path, line numbers, and code snippet.
    """
    tools = get_knowledge_tools()
    result = tools.get_evidence(evidence_id)
    return json.dumps(result, indent=2)


@mcp.tool()
def get_evidence_for_component(component: str) -> str:
    """
    Get all evidence (code snippets) for a component.

    Args:
        component: Component name or ID

    Returns:
        List of evidence items with file paths and code snippets.
    """
    tools = get_knowledge_tools()
    result = tools.get_evidence_for_component(component)
    return json.dumps(result, indent=2)


# ========== Summary Tools ==========


@mcp.tool()
def get_architecture_summary() -> str:
    """
    Get high-level architecture summary.

    Returns:
        Overview of the entire codebase:
        - Total components (733) by layer and stereotype
        - Total relations (169) by type
        - Total interfaces (125) by type
    """
    tools = get_knowledge_tools()
    result = tools.get_architecture_summary()
    return json.dumps(result, indent=2)


@mcp.tool()
def get_statistics() -> str:
    """
    Get detailed statistics about the knowledge base.

    Returns:
        Complete statistics including file paths, counts, and categories.
    """
    tools = get_knowledge_tools()
    result = tools.get_statistics()
    return json.dumps(result, indent=2)


# ========== Module Dimension Tools ==========


@mcp.tool()
def get_module_overview(module: str) -> str:
    """
    Get complete overview of a module: all components, relations, and endpoints.

    Args:
        module: Module name (e.g., "workflow", "deed", "user")

    Returns:
        Complete module analysis with components, internal/external relations, and endpoints.
    """
    tools = get_knowledge_tools()
    result = tools.get_module_overview(module)
    return json.dumps(result, indent=2)


@mcp.tool()
def list_modules() -> str:
    """
    List all modules/packages in the codebase with component counts.

    Returns:
        List of modules sorted by component count, with stereotype breakdown.
    """
    tools = get_knowledge_tools()
    result = tools.list_modules()
    return json.dumps(result, indent=2)


# ========== Dependency Dimension Tools ==========


@mcp.tool()
def get_dependencies_tree(component_id: str, depth: int = 3, direction: str = "outgoing") -> str:
    """
    Get full dependency tree for a component.

    Args:
        component_id: Component ID or name (e.g., "WorkflowService")
        depth: How deep to traverse (default: 3, max recommended: 5)
        direction: "outgoing" (what I depend on), "incoming" (what depends on me), or "both"

    Returns:
        Hierarchical dependency tree with all transitive dependencies.
    """
    tools = get_knowledge_tools()
    result = tools.get_dependencies_tree(component_id, depth, direction)
    return json.dumps(result, indent=2)


@mcp.tool()
def get_circular_dependencies() -> str:
    """
    Find potential circular dependencies in the codebase.

    Returns:
        List of dependency cycles (architectural smell that should be resolved).
    """
    tools = get_knowledge_tools()
    result = tools.get_circular_dependencies()
    return json.dumps(result, indent=2)


# ========== Data Dimension Tools ==========


@mcp.tool()
def get_entities() -> str:
    """
    Get all entity/domain model classes.

    Returns:
        List of all entities, models, aggregates, and value objects.
    """
    tools = get_knowledge_tools()
    result = tools.get_entities()
    return json.dumps(result, indent=2)


@mcp.tool()
def get_entity_relationships(entity_name: str) -> str:
    """
    Get all relationships for an entity (JPA relations, references, etc.).

    Args:
        entity_name: Entity name (e.g., "Order", "User")

    Returns:
        JPA relations (OneToMany, ManyToOne, etc.) and other references.
    """
    tools = get_knowledge_tools()
    result = tools.get_entity_relationships(entity_name)
    return json.dumps(result, indent=2)


# ========== API Dimension Tools ==========


@mcp.tool()
def get_api_overview() -> str:
    """
    Get complete API overview: all endpoints grouped by resource.

    Returns:
        All REST endpoints organized by base path/resource.
    """
    tools = get_knowledge_tools()
    result = tools.get_api_overview()
    return json.dumps(result, indent=2)


@mcp.tool()
def get_controllers_with_endpoints() -> str:
    """
    Get all controllers with their endpoints.

    Returns:
        List of controllers and the endpoints they expose.
    """
    tools = get_knowledge_tools()
    result = tools.get_controllers_with_endpoints()
    return json.dumps(result, indent=2)


# ========== Batch Query Tool ==========


@mcp.tool()
def batch_query(queries: str) -> str:
    """
    Execute multiple queries in ONE call to minimize token usage.
    This is the most efficient way to gather multiple pieces of information.

    Args:
        queries: JSON array of query objects, each with 'tool' and 'args'.
                 Example: '[{"tool": "get_component", "args": {"name": "WorkflowService"}},
                           {"tool": "get_relations_for", "args": {"component_id": "..."}}]'

    Available tools for batch:
        - get_component, get_component_by_id, search_components
        - list_components_by_stereotype, list_components_by_layer
        - get_relations_for, get_call_graph, get_dependencies_tree
        - get_endpoints, get_endpoint_by_path, get_routes
        - get_evidence, get_evidence_for_component
        - get_module_overview, list_modules
        - get_entities, get_entity_relationships
        - get_api_overview, get_controllers_with_endpoints
        - get_architecture_summary, get_statistics

    Returns:
        Results for all queries in a single response.
    """
    tools = get_knowledge_tools()
    try:
        parsed_queries = json.loads(queries)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {e}"})

    result = tools.batch_query(parsed_queries)
    return json.dumps(result, indent=2)


# ========== Server Entry Point ==========


def create_server() -> FastMCP:
    """Create and return the MCP server instance."""
    return mcp


def run_server():
    """Run the MCP server with STDIO transport."""
    logger.info("Starting AICodeGenCrew Knowledge MCP Server...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run_server()
