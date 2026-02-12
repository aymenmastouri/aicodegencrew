"""
Collector Registry — Single source of truth for all collector metadata.

Used by:
- CollectorOrchestrator (to know step ordering and IDs)
- Dashboard backend (to list collectors with metadata)
- Collector config (to validate IDs)
"""

from __future__ import annotations

COLLECTOR_REGISTRY: list[dict] = [
    {
        "id": "system",
        "name": "System Facts",
        "description": "System name, version, subsystems from pom.xml/package.json",
        "dimension": "system",
        "category": "core",
        "step": 1,
        "output_file": "system.json",
        "class_name": "SystemCollector",
        "can_disable": False,
    },
    {
        "id": "containers",
        "name": "Container Detection",
        "description": "Deployable units (Spring Boot, Angular, databases, Docker)",
        "dimension": "containers",
        "category": "core",
        "step": 2,
        "output_file": "containers.json",
        "class_name": "ContainerCollector",
        "can_disable": False,
    },
    {
        "id": "components",
        "name": "Component Extraction",
        "description": "Controllers, services, repositories + Spring/Angular specialists",
        "dimension": "components",
        "category": "core",
        "step": 3,
        "output_file": "components.json",
        "class_name": "ComponentCollector",
        "can_disable": False,
    },
    {
        "id": "interfaces",
        "name": "Interface Extraction",
        "description": "REST endpoints, Angular routes, message channels",
        "dimension": "interfaces",
        "category": "optional",
        "step": 4,
        "output_file": "interfaces.json",
        "class_name": "InterfaceCollector",
        "can_disable": True,
    },
    {
        "id": "data_model",
        "name": "Data Model",
        "description": "JPA entities, database tables, Flyway/Liquibase migrations",
        "dimension": "data_model",
        "category": "optional",
        "step": 5,
        "output_file": "data_model.json",
        "class_name": "DataModelCollector",
        "can_disable": True,
    },
    {
        "id": "runtime",
        "name": "Runtime Facts",
        "description": "Schedulers, async methods, event listeners",
        "dimension": "runtime",
        "category": "optional",
        "step": 6,
        "output_file": "runtime.json",
        "class_name": "RuntimeCollector",
        "can_disable": True,
    },
    {
        "id": "infrastructure",
        "name": "Infrastructure",
        "description": "Docker, Kubernetes, CI/CD pipelines",
        "dimension": "infrastructure",
        "category": "optional",
        "step": 7,
        "output_file": "infrastructure.json",
        "class_name": "InfrastructureCollector",
        "can_disable": True,
    },
    {
        "id": "dependencies",
        "name": "Dependencies",
        "description": "External libraries and packages from pom.xml/package.json",
        "dimension": "dependencies",
        "category": "optional",
        "step": 8,
        "output_file": "dependencies.json",
        "class_name": "DependencyCollector",
        "can_disable": True,
    },
    {
        "id": "workflows",
        "name": "Workflows",
        "description": "State machines, BPMN processes, NgRx stores",
        "dimension": "workflows",
        "category": "optional",
        "step": 9,
        "output_file": "workflows.json",
        "class_name": "WorkflowCollector",
        "can_disable": True,
    },
    {
        "id": "tech_versions",
        "name": "Technology Versions",
        "description": "Framework and library versions for upgrade planning",
        "dimension": "tech_versions",
        "category": "optional",
        "step": 10,
        "output_file": "tech_versions.json",
        "class_name": "TechStackVersionCollector",
        "can_disable": True,
    },
    {
        "id": "security_details",
        "name": "Security Details",
        "description": "Method-level security, CSRF, CORS, Spring Security config",
        "dimension": "security_details",
        "category": "optional",
        "step": 11,
        "output_file": "security_details.json",
        "class_name": "SecurityDetailCollector",
        "can_disable": True,
    },
    {
        "id": "validation",
        "name": "Validation Rules",
        "description": "Bean Validation annotations, custom validators, Angular form validation",
        "dimension": "validation",
        "category": "optional",
        "step": 12,
        "output_file": "validation.json",
        "class_name": "ValidationCollector",
        "can_disable": True,
    },
    {
        "id": "tests",
        "name": "Tests",
        "description": "Unit, integration, e2e tests and Cucumber scenarios",
        "dimension": "tests",
        "category": "optional",
        "step": 13,
        "output_file": "tests.json",
        "class_name": "TestCollector",
        "can_disable": True,
    },
    {
        "id": "error_handling",
        "name": "Error Handling",
        "description": "Exception handlers, @ControllerAdvice, custom exceptions",
        "dimension": "error_handling",
        "category": "optional",
        "step": 14,
        "output_file": "error_handling.json",
        "class_name": "ErrorHandlingCollector",
        "can_disable": True,
    },
    {
        "id": "evidence",
        "name": "Evidence Aggregation",
        "description": "Cross-references and source evidence from all collectors",
        "dimension": "evidence",
        "category": "core",
        "step": 15,
        "output_file": "evidence_map.json",
        "class_name": "EvidenceCollector",
        "can_disable": False,
    },
]


def get_registry_by_id() -> dict[str, dict]:
    """Return registry as a dict keyed by collector ID."""
    return {c["id"]: c for c in COLLECTOR_REGISTRY}


def get_disableable_ids() -> list[str]:
    """Return list of collector IDs that can be disabled."""
    return [c["id"] for c in COLLECTOR_REGISTRY if c["can_disable"]]
