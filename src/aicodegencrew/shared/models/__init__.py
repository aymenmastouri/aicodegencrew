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

from .task_output_schemas import (
    # Tech Architect outputs
    MacroArchitectureOutput,
    BackendPatternOutput,
    FrontendPatternOutput,
    ArchitectureQualityOutput,
    # Func Analyst outputs
    DomainModelOutput,
    BusinessCapabilitiesOutput,
    BoundedContextsOutput,
    StateMachinesOutput,
    WorkflowEnginesOutput,
    SagaPatternsOutput,
    RuntimeScenariosOutput,
    ApiDesignOutput,
    # Quality Analyst outputs
    ComplexityOutput,
    TechnicalDebtOutput,
    SecurityOutput,
    OperationalReadinessOutput,
    # Synthesis output
    AnalyzedArchitecture,
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
    # Task output schemas (Phase 2)
    "MacroArchitectureOutput",
    "BackendPatternOutput",
    "FrontendPatternOutput",
    "ArchitectureQualityOutput",
    "DomainModelOutput",
    "BusinessCapabilitiesOutput",
    "BoundedContextsOutput",
    "StateMachinesOutput",
    "WorkflowEnginesOutput",
    "SagaPatternsOutput",
    "RuntimeScenariosOutput",
    "ApiDesignOutput",
    "ComplexityOutput",
    "TechnicalDebtOutput",
    "SecurityOutput",
    "OperationalReadinessOutput",
    "AnalyzedArchitecture",
]
