"""
Output Schemas für Architecture Facts Phase 1.

Definiert die JSON-Struktur für alle 11 Dimension Files:
1. system.json
2. containers.json
3. components.json
4. interfaces.json
5. relations.json
6. data_model.json
7. runtime.json
8. infrastructure.json
9. dependencies.json
10. workflows.json
11. evidence_map.json

Jedes Schema ist als TypedDict + JSON Schema definiert für Validierung.
"""

from typing import TypedDict, List, Dict, Optional, Any, Literal
from dataclasses import dataclass, field, asdict
import json


# =============================================================================
# 1. SYSTEM SCHEMA
# =============================================================================

class SystemSchema(TypedDict):
    """system.json schema"""
    name: str                          # System name (repo directory)
    version: Optional[str]             # Version from build file
    description: Optional[str]         # Description from build file
    contexts: List[str]                # Bounded contexts detected


SYSTEM_JSON_SCHEMA = {
    "type": "object",
    "required": ["name", "contexts"],
    "properties": {
        "name": {"type": "string", "minLength": 1},
        "version": {"type": ["string", "null"]},
        "description": {"type": ["string", "null"]},
        "contexts": {
            "type": "array",
            "items": {"type": "string"}
        }
    }
}


# =============================================================================
# 2. CONTAINERS SCHEMA
# =============================================================================

class ContainerSchema(TypedDict):
    """Single container in containers.json"""
    id: str                            # Unique ID (e.g., "backend", "frontend")
    name: str                          # Display name
    type: Literal["backend", "frontend", "test", "batch", "library", "database", "messaging", "cache"]
    technology: str                    # e.g., "Spring Boot", "Angular"
    path: str                          # Relative path from repo root
    category: Literal["application", "infrastructure", "test", "library"]


CONTAINER_JSON_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "required": ["id", "name", "type", "technology", "path"],
        "properties": {
            "id": {"type": "string"},
            "name": {"type": "string"},
            "type": {"type": "string", "enum": ["backend", "frontend", "test", "batch", "library", "database", "messaging", "cache"]},
            "technology": {"type": "string"},
            "path": {"type": "string"},
            "category": {"type": "string", "enum": ["application", "infrastructure", "test", "library"]}
        }
    }
}


# =============================================================================
# 3. COMPONENTS SCHEMA
# =============================================================================

class ComponentSchema(TypedDict):
    """Single component in components.json"""
    id: str                            # Unique ID (e.g., "backend.WorkflowController")
    name: str                          # Class/component name
    container: str                     # Container ID this belongs to
    stereotype: Literal["controller", "service", "repository", "entity", "module", "component", "guard", "pipe", "directive"]
    layer: Optional[Literal["presentation", "application", "domain", "data_access"]]
    module: str                        # Package/module path
    file: str                          # Source file path
    evidence: List[str]                # Evidence IDs


COMPONENT_JSON_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "required": ["id", "name", "container", "stereotype", "file"],
        "properties": {
            "id": {"type": "string"},
            "name": {"type": "string"},
            "container": {"type": "string"},
            "stereotype": {"type": "string"},
            "layer": {"type": ["string", "null"]},
            "module": {"type": "string"},
            "file": {"type": "string"},
            "evidence": {"type": "array", "items": {"type": "string"}}
        }
    }
}


# =============================================================================
# 4. INTERFACES SCHEMA
# =============================================================================

class InterfaceSchema(TypedDict):
    """Single interface in interfaces.json"""
    id: str                            # Unique ID
    name: str                          # Endpoint/route name
    container: str                     # Container ID
    type: Literal["rest_endpoint", "route", "scheduler", "kafka_listener", "rabbit_listener", "graphql"]
    method: Optional[str]              # HTTP method (GET, POST, etc.)
    path: Optional[str]                # URL path or route
    implemented_by: str                # Component ID that implements this
    evidence: List[str]                # Evidence IDs


INTERFACE_JSON_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "required": ["id", "name", "container", "type"],
        "properties": {
            "id": {"type": "string"},
            "name": {"type": "string"},
            "container": {"type": "string"},
            "type": {"type": "string"},
            "method": {"type": ["string", "null"]},
            "path": {"type": ["string", "null"]},
            "implemented_by": {"type": "string"},
            "evidence": {"type": "array", "items": {"type": "string"}}
        }
    }
}


# =============================================================================
# 5. RELATIONS SCHEMA
# =============================================================================

class RelationSchema(TypedDict):
    """Single relation in relations.json"""
    id: str                            # Unique ID
    from_id: str                       # Source component/container ID
    to_id: str                         # Target component/container ID
    type: Literal["uses", "calls", "extends", "implements", "produces", "consumes", "imports"]
    evidence: List[str]                # Evidence IDs


RELATION_JSON_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "required": ["id", "from_id", "to_id", "type"],
        "properties": {
            "id": {"type": "string"},
            "from_id": {"type": "string"},
            "to_id": {"type": "string"},
            "type": {"type": "string", "enum": ["uses", "calls", "extends", "implements", "produces", "consumes", "imports"]},
            "evidence": {"type": "array", "items": {"type": "string"}}
        }
    }
}


# =============================================================================
# 6. DATA MODEL SCHEMA
# =============================================================================

class ColumnSchema(TypedDict):
    """Column definition"""
    name: str
    type: str
    nullable: Optional[bool]
    primary_key: Optional[bool]


class EntitySchema(TypedDict):
    """Single entity in data_model.json"""
    id: str                            # Unique ID
    name: str                          # Entity/table name
    type: Literal["entity", "table", "view"]
    table_name: Optional[str]          # Database table name (for JPA entities)
    schema: Optional[str]              # Database schema
    columns: List[ColumnSchema]
    evidence: List[str]


DATA_MODEL_JSON_SCHEMA = {
    "type": "object",
    "required": ["entities", "tables"],
    "properties": {
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "name", "type"],
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "type": {"type": "string", "enum": ["entity", "table", "view"]},
                    "table_name": {"type": ["string", "null"]},
                    "schema": {"type": ["string", "null"]},
                    "columns": {"type": "array"},
                    "evidence": {"type": "array", "items": {"type": "string"}}
                }
            }
        },
        "tables": {
            "type": "array",
            "items": {"type": "object"}
        },
        "migrations": {
            "type": "array",
            "items": {"type": "object"}
        }
    }
}


# =============================================================================
# 7. RUNTIME SCHEMA
# =============================================================================

class RuntimeFactSchema(TypedDict):
    """Single runtime fact in runtime.json"""
    id: str
    name: str
    type: Literal["scheduler", "async", "event_listener", "batch_job", "workflow"]
    container: str
    schedule: Optional[str]            # Cron expression
    trigger: Optional[str]             # Event/message trigger
    evidence: List[str]


RUNTIME_JSON_SCHEMA = {
    "type": "object",
    "required": ["schedulers", "async_methods", "jobs"],
    "properties": {
        "schedulers": {"type": "array"},
        "async_methods": {"type": "array"},
        "jobs": {"type": "array"},
        "event_listeners": {"type": "array"}
    }
}


# =============================================================================
# 8. INFRASTRUCTURE SCHEMA
# =============================================================================

class InfraFactSchema(TypedDict):
    """Single infrastructure fact"""
    id: str
    name: str
    type: Literal["dockerfile", "docker_compose", "k8s_deployment", "ci_pipeline", "config_file"]
    category: Literal["container", "orchestration", "ci_cd", "configuration"]
    evidence: List[str]


INFRASTRUCTURE_JSON_SCHEMA = {
    "type": "object",
    "required": ["docker", "kubernetes", "ci_cd"],
    "properties": {
        "docker": {
            "type": "object",
            "properties": {
                "dockerfiles": {"type": "array"},
                "compose": {"type": "array"}
            }
        },
        "kubernetes": {
            "type": "object",
            "properties": {
                "deployments": {"type": "array"},
                "services": {"type": "array"}
            }
        },
        "ci_cd": {
            "type": "object",
            "properties": {
                "pipelines": {"type": "array"}
            }
        }
    }
}


# =============================================================================
# 9. DEPENDENCIES SCHEMA
# =============================================================================

class DependencySchema(TypedDict):
    """Single dependency in dependencies.json"""
    id: str                            # Unique ID
    name: str                          # Package/library name
    type: Literal["maven", "npm", "python", "gradle", "nuget"]
    version: str                       # Version string
    scope: Literal["compile", "runtime", "test", "dev", "provided"]
    group: Optional[str]               # groupId for Maven
    evidence: List[str]                # Evidence IDs


DEPENDENCIES_JSON_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "required": ["id", "name", "type"],
        "properties": {
            "id": {"type": "string"},
            "name": {"type": "string"},
            "type": {"type": "string", "enum": ["maven", "npm", "python", "gradle", "nuget"]},
            "version": {"type": "string"},
            "scope": {"type": "string", "enum": ["compile", "runtime", "test", "dev", "provided"]},
            "group": {"type": ["string", "null"]},
            "evidence": {"type": "array", "items": {"type": "string"}}
        }
    }
}


# =============================================================================
# 10. WORKFLOWS SCHEMA
# =============================================================================

class WorkflowSchema(TypedDict):
    """Single workflow in workflows.json"""
    id: str                            # Unique ID
    name: str                          # Workflow/StateMachine name
    type: Literal["bpmn", "camunda", "flowable", "spring_statemachine", "xstate", "custom", "enum_based", "ngrx_effects", "ngrx_reducer", "rxjs_flow", "business_flow"]
    states: List[str]                  # List of states
    transitions: List[Dict[str, str]]  # [{from, to, trigger}]
    actions: List[str]                 # Actions/Events
    container: str                     # Container ID
    file: str                          # Source file
    evidence: List[str]                # Evidence IDs


WORKFLOWS_JSON_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "required": ["id", "name", "type"],
        "properties": {
            "id": {"type": "string"},
            "name": {"type": "string"},
            "type": {"type": "string", "enum": ["bpmn", "camunda", "flowable", "spring_statemachine", "xstate", "custom", "enum_based", "ngrx_effects", "ngrx_reducer", "rxjs_flow", "business_flow"]},
            "states": {"type": "array", "items": {"type": "string"}},
            "transitions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "from": {"type": "string"},
                        "to": {"type": "string"},
                        "trigger": {"type": "string"}
                    }
                }
            },
            "actions": {"type": "array", "items": {"type": "string"}},
            "container": {"type": "string"},
            "file": {"type": "string"},
            "evidence": {"type": "array", "items": {"type": "string"}}
        }
    }
}


# =============================================================================
# 11. EVIDENCE MAP SCHEMA
# =============================================================================

class EvidenceSchema(TypedDict):
    """Single evidence entry"""
    id: str                            # Unique evidence ID (e.g., "ev_0001")
    path: str                          # File path
    lines: str                         # Line range "start-end"
    reason: str                        # Why this is evidence
    snippet: Optional[str]             # Code snippet


EVIDENCE_MAP_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": {
        "type": "object",
        "required": ["path", "lines", "reason"],
        "properties": {
            "path": {"type": "string"},
            "lines": {"type": "string"},
            "reason": {"type": "string"},
            "snippet": {"type": ["string", "null"]},
            "referenced_by": {"type": "array", "items": {"type": "string"}}
        }
    }
}


# =============================================================================
# VALIDATION
# =============================================================================

def validate_output(data: Any, schema_name: str) -> List[str]:
    """
    Validate output data against schema.
    
    Returns list of validation errors (empty if valid).
    """
    errors = []
    
    schemas = {
        "system": SYSTEM_JSON_SCHEMA,
        "containers": CONTAINER_JSON_SCHEMA,
        "components": COMPONENT_JSON_SCHEMA,
        "interfaces": INTERFACE_JSON_SCHEMA,
        "relations": RELATION_JSON_SCHEMA,
        "data_model": DATA_MODEL_JSON_SCHEMA,
        "runtime": RUNTIME_JSON_SCHEMA,
        "infrastructure": INFRASTRUCTURE_JSON_SCHEMA,
        "dependencies": DEPENDENCIES_JSON_SCHEMA,
        "workflows": WORKFLOWS_JSON_SCHEMA,
        "evidence_map": EVIDENCE_MAP_JSON_SCHEMA,
    }
    
    schema = schemas.get(schema_name)
    if not schema:
        return [f"Unknown schema: {schema_name}"]
    
    # Basic type validation
    expected_type = schema.get("type")
    
    if expected_type == "object" and not isinstance(data, dict):
        errors.append(f"Expected object, got {type(data).__name__}")
        return errors
    
    if expected_type == "array" and not isinstance(data, list):
        errors.append(f"Expected array, got {type(data).__name__}")
        return errors
    
    # Check required fields for objects
    if expected_type == "object":
        required = schema.get("required", [])
        for field in required:
            if field not in data:
                errors.append(f"Missing required field: {field}")
    
    # Check array items
    if expected_type == "array":
        item_schema = schema.get("items", {})
        item_required = item_schema.get("required", [])
        
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                errors.append(f"Item {i}: expected object, got {type(item).__name__}")
                continue
            
            for field in item_required:
                if field not in item:
                    errors.append(f"Item {i}: missing required field '{field}'")
    
    return errors


# =============================================================================
# EXAMPLE OUTPUTS (for documentation)
# =============================================================================

EXAMPLE_SYSTEM = {
    "name": "myapp",
    "version": "1.0.0",
    "description": "Example application system",
    "contexts": ["orders", "customers", "inventory"]
}

EXAMPLE_CONTAINERS = [
    {
        "id": "backend",
        "name": "backend",
        "type": "backend",
        "technology": "Spring Boot",
        "path": "backend/",
        "category": "application"
    },
    {
        "id": "frontend",
        "name": "frontend",
        "type": "frontend",
        "technology": "Angular",
        "path": "frontend/",
        "category": "application"
    }
]

EXAMPLE_COMPONENTS = [
    {
        "id": "backend.WorkflowController",
        "name": "WorkflowController",
        "container": "backend",
        "stereotype": "controller",
        "layer": "presentation",
        "module": "com.company.app.orders.controller",
        "file": "backend/src/main/java/com/company/app/orders/controller/OrderController.java",
        "evidence": ["ev_0001"]
    }
]

EXAMPLE_INTERFACES = [
    {
        "id": "backend.POST./workflow/start",
        "name": "startWorkflow",
        "container": "backend",
        "type": "rest_endpoint",
        "method": "POST",
        "path": "/workflow/start",
        "implemented_by": "backend.WorkflowController",
        "evidence": ["ev_0002"]
    }
]

EXAMPLE_DATA_MODEL = {
    "entities": [
        {
            "id": "backend.WorkflowEntity",
            "name": "WorkflowEntity",
            "type": "entity",
            "table_name": "WORKFLOW",
            "columns": [
                {"name": "id", "type": "Long", "primary_key": True},
                {"name": "status", "type": "String", "nullable": False}
            ],
            "evidence": ["ev_0010"]
        }
    ],
    "tables": [
        {
            "id": "db.WORKFLOW",
            "name": "WORKFLOW",
            "type": "table",
            "schema": "APP",
            "columns": [
                {"name": "ID", "type": "NUMBER", "primary_key": True},
                {"name": "STATUS", "type": "VARCHAR2(50)", "nullable": False}
            ],
            "evidence": ["ev_0011"]
        }
    ],
    "migrations": []
}
