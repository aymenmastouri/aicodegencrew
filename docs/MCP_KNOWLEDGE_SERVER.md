# MCP Knowledge Server

> **Solves the Token Limit Problem**: Instead of dumping 500k lines of code into LLM context, query specific facts on-demand.

## Overview

The AICodeGenCrew MCP Server exposes Phase 1 architecture facts as tools that LLM agents can query. This enables:

- **Targeted Queries**: Ask for specific components, relations, or endpoints
- **Structured Responses**: Get JSON data, not raw code
- **Token Efficient**: Only load what you need into context
- **Always Current**: Reads from Phase 1 JSON output

## Quick Start

### 1. Run MCP Server Standalone

```bash
# From aicodegencrew directory
uv run python -m aicodegencrew.mcp.server
```

### 2. Use with CrewAI (Recommended DSL)

```python
from crewai import Agent
from crewai.mcp import MCPServerStdio

agent = Agent(
    role="Architecture Analyst",
    goal="Analyze codebase architecture and answer questions",
    backstory="Expert software architect with deep knowledge of the codebase",
    mcps=[
        MCPServerStdio(
            command="python",
            args=["-m", "aicodegencrew.mcp.server"],
        )
    ]
)
```

### 3. Use with MCPServerAdapter

```python
from crewai import Agent
from crewai_tools import MCPServerAdapter
from mcp import StdioServerParameters

server_params = StdioServerParameters(
    command="python",
    args=["-m", "aicodegencrew.mcp.server"],
)

with MCPServerAdapter(server_params) as tools:
    print(f"Available tools: {[t.name for t in tools]}")
    
    agent = Agent(
        role="Architecture Analyst",
        goal="Analyze the codebase",
        tools=tools
    )
```

## Available Tools (14)

### Component Tools

| Tool | Description | Example |
|------|-------------|---------|
| `get_component` | Find component by name | `get_component("WorkflowService")` |
| `get_component_by_id` | Get by exact ID | `get_component_by_id("component.backend.service.workflow")` |
| `list_components_by_stereotype` | List by type | `list_components_by_stereotype("service")` |
| `list_components_by_layer` | List by layer | `list_components_by_layer("application")` |
| `search_components` | Regex search | `search_components(".*Controller$")` |

### Relation Tools

| Tool | Description | Example |
|------|-------------|---------|
| `get_relations_for` | Get all relations | `get_relations_for("DeedEntryService")` |
| `get_call_graph` | Get dependency graph | `get_call_graph("WorkflowService", depth=2)` |

### Interface Tools

| Tool | Description | Example |
|------|-------------|---------|
| `get_endpoints` | List REST endpoints | `get_endpoints("/workflow.*")` |
| `get_endpoint_by_path` | Get specific endpoint | `get_endpoint_by_path("/uvz/v1/workflow/{id}", "GET")` |
| `get_routes` | List frontend routes | `get_routes()` |

### Evidence Tools

| Tool | Description | Example |
|------|-------------|---------|
| `get_evidence` | Get code snippet | `get_evidence("ev_123")` |
| `get_evidence_for_component` | Get all evidence | `get_evidence_for_component("UserService")` |

### Summary Tools

| Tool | Description | Example |
|------|-------------|---------|
| `get_architecture_summary` | High-level overview | `get_architecture_summary()` |
| `get_statistics` | Detailed stats | `get_statistics()` |

## Example Queries

### "What services does DeedEntryService call?"

```
Tool: get_relations_for
Input: "DeedEntryService"

Response:
{
  "component_id": "component.backend.deedentry_logic_impl.deed_entry_service_impl",
  "outgoing": {
    "count": 6,
    "relations": [
      {"to": "correction_note_service", "type": "uses"},
      {"to": "deed_entry_log_service", "type": "uses"},
      {"to": "deed_registry_service", "type": "uses"},
      ...
    ]
  }
}
```

### "What endpoints handle workflow operations?"

```
Tool: get_endpoints
Input: "/workflow"

Response:
{
  "filter": "/workflow",
  "count": 5,
  "endpoints": [
    {"path": "/uvz/v1/workflow/{id}", "method": "GET"},
    {"path": "/uvz/v1/workflow/{id}/status", "method": "PUT"},
    ...
  ]
}
```

### "Show me the architecture overview"

```
Tool: get_architecture_summary

Response:
{
  "components": {
    "total": 951,
    "by_layer": {
      "presentation": 246,
      "application": 168,
      "domain": 199,
      "dataaccess": 38
    }
  },
  "relations": {"total": 169},
  "interfaces": {"total": 125}
}
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AICODEGENCREW_KNOWLEDGE_PATH` | Path to knowledge directory | `./knowledge/architecture` |

### Claude Desktop Config

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "aicodegencrew-knowledge": {
      "command": "uv",
      "args": [
        "--directory",
        "C:/projects/aicodegencrew",
        "run",
        "python",
        "-m",
        "aicodegencrew.mcp.server"
      ]
    }
  }
}
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  LLM Agent (CrewAI, Claude, etc.)                               │
│  "What services does WorkflowController call?"                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ MCP Protocol (JSON-RPC over STDIO)
┌─────────────────────────────────────────────────────────────────┐
│  AICodeGenCrew MCP Server                                       │
│                                                                 │
│  14 Tools:                                                      │
│  - get_component, search_components, ...                        │
│  - get_relations_for, get_call_graph, ...                       │
│  - get_endpoints, get_routes, ...                               │
│  - get_architecture_summary, get_statistics                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ File I/O
┌─────────────────────────────────────────────────────────────────┐
│  Phase 1 Knowledge Base (JSON)                                  │
│                                                                 │
│  knowledge/architecture/                                        │
│  ├── components.json    (951+ components)                       │
│  ├── relations.json     (190 relations)                         │
│  ├── interfaces.json    (226 endpoints/routes)                  │
│  ├── evidence_map.json  (1005 code snippets)                    │
│  └── ...                                                        │
└─────────────────────────────────────────────────────────────────┘
```

## Token Savings

| Approach | Context Size | Problem |
|----------|-------------|---------|
| **Dump entire codebase** | ~500k tokens | Exceeds all LLM limits |
| **RAG chunks** | ~10k tokens | Fragmented, loses context |
| **MCP Targeted Query** | ~500 tokens | Precise, structured data |

**Example**: Asking "What does UserService depend on?"

- Without MCP: Need to load UserService.java + all imported files (~5k lines)
- With MCP: Single tool call returns structured JSON (~50 lines)

## Best Practices

1. **Start with Summary**: Use `get_architecture_summary()` to understand the codebase structure
2. **Search First**: Use `search_components()` with regex to find relevant components
3. **Follow Relations**: Use `get_relations_for()` to trace dependencies
4. **Get Evidence**: Use `get_evidence_for_component()` to see actual code

## Troubleshooting

### Server won't start

```bash
# Check if mcp is installed
python -c "import mcp; print(mcp.__version__)"

# Run with debug logging
python -m aicodegencrew.mcp.server 2>&1 | head -20
```

### No knowledge found

```bash
# Ensure knowledge directory exists
ls knowledge/architecture/

# Run Phase 1 first
python -m aicodegencrew run --phases phase1_architecture_facts
```

### Connection timeout

Increase timeout in CrewAI:

```python
MCPServerStdio(
    command="python",
    args=["-m", "aicodegencrew.mcp.server"],
    connect_timeout=120  # 2 minutes
)
```
