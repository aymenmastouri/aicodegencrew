"""Models package."""

from .analysis_schema import (
    ApiEndpoint,
    ArchitectureAnalysis,
    CodeGenContext,
    CodingPattern,
    ComponentClass,
    DataHint,
    DeploymentHint,
    EntityClass,
    Evidence,
    Interface,
    ProjectUnit,
    ServiceClass,
    # Code generation structures
    SourceDirectory,
    Technology,
)
from .architecture_facts_schema import (
    ArchitectureFacts,
    Component,
    Container,
    EvidenceItem,
    Relation,
    SystemInfo,
)
from .architecture_facts_schema import (
    Interface as FactInterface,
)
from .task_output_schemas import (
    # Synthesis output
    AnalyzedArchitecture,
    ApiDesignOutput,
    ArchitectureQualityOutput,
    BackendPatternOutput,
    BoundedContextsOutput,
    BusinessCapabilitiesOutput,
    # Quality Analyst outputs
    ComplexityOutput,
    # Func Analyst outputs
    DomainModelOutput,
    FrontendPatternOutput,
    # Tech Architect outputs
    MacroArchitectureOutput,
    OperationalReadinessOutput,
    RuntimeScenariosOutput,
    SagaPatternsOutput,
    SecurityOutput,
    StateMachinesOutput,
    TechnicalDebtOutput,
    WorkflowEnginesOutput,
)

__all__ = [
    "AnalyzedArchitecture",
    "ApiDesignOutput",
    "ApiEndpoint",
    "ArchitectureAnalysis",
    "ArchitectureFacts",
    "ArchitectureQualityOutput",
    "BackendPatternOutput",
    "BoundedContextsOutput",
    "BusinessCapabilitiesOutput",
    "CodeGenContext",
    "CodingPattern",
    "ComplexityOutput",
    "Component",
    "ComponentClass",
    "Container",
    "DataHint",
    "DeploymentHint",
    "DomainModelOutput",
    "EntityClass",
    "Evidence",
    # Architecture facts schema (Phase 1)
    "EvidenceItem",
    "FactInterface",
    "FrontendPatternOutput",
    "Interface",
    # Task output schemas (Phase 2)
    "MacroArchitectureOutput",
    "OperationalReadinessOutput",
    "ProjectUnit",
    "Relation",
    "RuntimeScenariosOutput",
    "SagaPatternsOutput",
    "SecurityOutput",
    "ServiceClass",
    # Code generation structures
    "SourceDirectory",
    "StateMachinesOutput",
    "SystemInfo",
    "TechnicalDebtOutput",
    "Technology",
    "WorkflowEnginesOutput",
]
