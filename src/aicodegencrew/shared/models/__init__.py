"""Models package."""

from .analysis_schema import (
    Evidence,
    Technology,
    Interface,
    DataHint,
    DeploymentHint,
    ProjectUnit,
    ArchitectureAnalysis,
    # Code generation structures
    SourceDirectory,
    ApiEndpoint,
    ServiceClass,
    EntityClass,
    ComponentClass,
    CodingPattern,
    CodeGenContext,
)

from .architecture_facts_schema import (
    EvidenceItem,
    SystemInfo,
    Container,
    Component,
    Interface as FactInterface,
    Relation,
    ArchitectureFacts,
)

__all__ = [
    "Evidence",
    "Technology",
    "Interface",
    "DataHint",
    "DeploymentHint",
    "ProjectUnit",
    "ArchitectureAnalysis",
    # Code generation structures
    "SourceDirectory",
    "ApiEndpoint",
    "ServiceClass",
    "EntityClass",
    "ComponentClass",
    "CodingPattern",
    "CodeGenContext",
    # Architecture facts schema (Phase 1)
    "EvidenceItem",
    "SystemInfo",
    "Container",
    "Component",
    "FactInterface",
    "Relation",
    "ArchitectureFacts",
]
