"""Pydantic schemas for Phase 2 Task Outputs.

Each task outputs a focused JSON structure that gets merged
by the synthesis_lead into analyzed_architecture.json.

These schemas enable:
1. Validation of agent outputs
2. Type hints for downstream processing
3. Documentation of expected structure
"""

from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field


# =============================================================================
# TECHNICAL ARCHITECT TASK OUTPUTS (Tasks 1.1 - 1.4)
# =============================================================================

class MacroArchitectureOutput(BaseModel):
    """Task 1.1: analyze_macro_architecture output."""
    style: Literal["Modular Monolith", "Microservices", "Layered", "Event-Driven", "Hybrid"]
    container_count: int = Field(..., ge=0)
    reasoning: str
    scalability_approach: Literal["horizontal", "vertical", "hybrid"]
    deployment_model: Literal["monolith", "distributed", "serverless"]
    communication_pattern: Literal["sync REST", "async messaging", "mixed"]


class TechnologyInfo(BaseModel):
    """Technology details from container."""
    framework: str
    language: str


class ComponentCounts(BaseModel):
    """Component counts by type."""
    controllers: int = Field(default=0, ge=0)
    services: int = Field(default=0, ge=0)
    repositories: int = Field(default=0, ge=0)


class BackendPatternOutput(BaseModel):
    """Task 1.2: analyze_backend_pattern output."""
    primary_pattern: Literal["Layered", "Hexagonal", "Clean Architecture", "CQRS", "Traditional"]
    layer_structure: List[str]
    component_counts: ComponentCounts
    technology: TechnologyInfo
    reasoning: str


class FrontendPatternOutput(BaseModel):
    """Task 1.3: analyze_frontend_pattern output."""
    primary_pattern: Literal["Component-Based SPA", "Micro-Frontends", "Monolithic", "Server-Rendered"]
    framework: Literal["Angular", "React", "Vue", "Other"]
    module_structure: Literal["NgModule", "Standalone", "Feature Modules", "N/A"]
    state_management: str  # NgRx, Redux, Services, None detected
    routing_strategy: Literal["lazy-loading", "eager", "hybrid", "none"]
    component_count: int = Field(default=0, ge=0)
    reasoning: str


class ArchitectureQualityOutput(BaseModel):
    """Task 1.4: analyze_architecture_quality output."""
    separation_of_concerns: Literal["good", "moderate", "poor"]
    layer_violations_count: int = Field(default=0, ge=0)
    layer_violations_examples: List[str] = Field(default_factory=list)
    coupling_assessment: Literal["loose", "moderate", "tight"]
    avg_dependencies_per_component: float = Field(default=0.0, ge=0)
    cohesion_assessment: Literal["high", "moderate", "low"]
    circular_dependencies: int = Field(default=0, ge=0)
    god_classes: List[str] = Field(default_factory=list)
    overall_grade: Literal["A", "B", "C", "D", "F"]
    reasoning: str


# =============================================================================
# FUNCTIONAL ANALYST TASK OUTPUTS (Tasks 2.1 - 2.8)
# =============================================================================

class DomainArea(BaseModel):
    """A domain area within the system."""
    name: str
    entity_count: int = Field(default=0, ge=0)
    key_entities: List[str] = Field(default_factory=list)
    business_significance: Literal["core", "supporting", "generic"]


class DomainModelOutput(BaseModel):
    """Task 2.1: analyze_domain_model output."""
    total_entities: int = Field(default=0, ge=0)
    domain_complexity: Literal["simple", "moderate", "complex", "enterprise"]
    domain_maturity: Literal["emerging", "growing", "mature", "legacy"]
    core_domain_areas: List[DomainArea] = Field(default_factory=list)
    naming_consistency: Literal["consistent", "mixed", "inconsistent"]
    reasoning: str


class BusinessCapability(BaseModel):
    """A business capability identified from services."""
    capability: str
    description: str
    services_count: int = Field(default=0, ge=0)
    key_services: List[str] = Field(default_factory=list)
    maturity: Literal["basic", "intermediate", "advanced"]
    api_surface: Literal["REST", "GraphQL", "Events", "Internal"]


class BusinessCapabilitiesOutput(BaseModel):
    """Task 2.2: analyze_business_capabilities output."""
    capabilities: List[BusinessCapability] = Field(default_factory=list, alias="business_capabilities")
    capability_coverage: Literal["comprehensive", "partial", "minimal"]
    reasoning: str
    
    model_config = {"populate_by_name": True}


class BoundedContext(BaseModel):
    """A DDD bounded context."""
    name: str
    entities: int = Field(default=0, ge=0)
    services: int = Field(default=0, ge=0)
    controllers: int = Field(default=0, ge=0)
    cohesion: Literal["high", "moderate", "low"]


class BoundedContextsOutput(BaseModel):
    """Task 2.3: analyze_bounded_contexts output."""
    contexts_identified: int = Field(default=0, ge=0)
    contexts: List[BoundedContext] = Field(default_factory=list)
    cross_context_coupling: Literal["minimal", "acceptable", "concerning"]
    recommendations: List[str] = Field(default_factory=list)
    reasoning: str


class StateTransition(BaseModel):
    """A state transition in a state machine."""
    from_state: str = Field(..., alias="from")
    to_state: str = Field(..., alias="to")
    trigger: str
    
    model_config = {"populate_by_name": True}


class StatefulEntity(BaseModel):
    """An entity with state/status field."""
    entity: str
    state_field: str
    states: List[str] = Field(default_factory=list)
    transitions: List[StateTransition] = Field(default_factory=list)


class StateMachinesOutput(BaseModel):
    """Task 2.4: analyze_state_machines output."""
    detected: bool = False
    implementation: Literal["Spring State Machine", "Custom", "Enum-based", "None"]
    stateful_entities: List[StatefulEntity] = Field(default_factory=list)
    state_machine_classes: List[str] = Field(default_factory=list)
    reasoning: str


class BpmnProcess(BaseModel):
    """A BPMN process definition."""
    name: str
    file: str
    tasks: List[str] = Field(default_factory=list)


class WorkflowEnginesOutput(BaseModel):
    """Task 2.5: analyze_workflow_engines output."""
    engine: Literal["Camunda", "Flowable", "Activiti", "None"]
    version: Optional[str] = None
    bpmn_processes: List[BpmnProcess] = Field(default_factory=list)
    integration_style: Literal["embedded", "external", "none"]
    workflow_services: List[str] = Field(default_factory=list)
    reasoning: str


class Saga(BaseModel):
    """A saga for distributed transactions."""
    name: str
    steps: List[str] = Field(default_factory=list)
    compensations: List[str] = Field(default_factory=list)


class SagaPatternsOutput(BaseModel):
    """Task 2.6: analyze_saga_patterns output."""
    detected: bool = False
    style: Literal["orchestration", "choreography", "none"]
    sagas: List[Saga] = Field(default_factory=list)
    outbox_pattern: bool = False
    event_store: Literal["Kafka", "RabbitMQ", "Database", "None"]
    reasoning: str


class RuntimeScenario(BaseModel):
    """A runtime scenario for Arc42 Section 6."""
    name: str
    trigger: str
    actors: List[str] = Field(default_factory=list)
    steps: List[str] = Field(default_factory=list)
    end_state: str
    error_handling: Optional[str] = None


class RuntimeScenariosOutput(BaseModel):
    """Task 2.7: analyze_runtime_scenarios output."""
    scenarios: List[RuntimeScenario] = Field(default_factory=list)
    orchestration_style: Literal["orchestrated", "choreographed", "mixed"]
    arc42_section6_ready: bool = False
    reasoning: str


class VerbDistribution(BaseModel):
    """HTTP verb distribution."""
    GET: int = Field(default=0, ge=0)
    POST: int = Field(default=0, ge=0)
    PUT: int = Field(default=0, ge=0)
    DELETE: int = Field(default=0, ge=0)
    PATCH: int = Field(default=0, ge=0)


class ApiDesignOutput(BaseModel):
    """Task 2.8: analyze_api_design output."""
    total_endpoints: int = Field(default=0, ge=0)
    restfulness: Literal["RESTful", "REST-like", "RPC-over-HTTP"]
    verb_distribution: VerbDistribution
    consistency: Literal["consistent", "mixed", "inconsistent"]
    versioning_strategy: Literal["path", "header", "none"]
    naming_quality: Literal["good", "acceptable", "poor"]
    recommendations: List[str] = Field(default_factory=list)
    reasoning: str


# =============================================================================
# QUALITY ANALYST TASK OUTPUTS (Tasks 3.1 - 3.4)
# =============================================================================

class ComplexityOutput(BaseModel):
    """Task 3.1: analyze_complexity output."""
    total_components: int = Field(default=0, ge=0)
    total_relations: int = Field(default=0, ge=0)
    relations_per_component: float = Field(default=0.0, ge=0)
    structural_complexity: Literal["low", "moderate", "high", "critical"]
    cognitive_complexity: Literal["low", "moderate", "high", "critical"]
    scale: Literal["small", "medium", "large", "enterprise"]
    hotspots: List[str] = Field(default_factory=list)
    reasoning: str


class DebtIndicators(BaseModel):
    """Technical debt indicators found."""
    todo_fixme: str  # count or "few" | "many"
    deprecated: str
    workarounds: str


class DebtCategories(BaseModel):
    """Technical debt by category."""
    code_quality: Literal["low", "moderate", "high"]
    architecture: Literal["low", "moderate", "high"]
    documentation: Literal["low", "moderate", "high"]


class TechnicalDebtOutput(BaseModel):
    """Task 3.2: analyze_technical_debt output."""
    debt_level: Literal["low", "moderate", "high", "critical"]
    indicators_found: DebtIndicators
    categories: DebtCategories
    estimated_effort: Literal["days", "weeks", "months"]
    priority_items: List[str] = Field(default_factory=list)
    reasoning: str


class SecurityOutput(BaseModel):
    """Task 3.3: analyze_security output."""
    authentication: Literal["implemented", "partial", "missing", "unknown"]
    authorization: Literal["implemented", "partial", "missing", "unknown"]
    input_validation: Literal["implemented", "partial", "missing", "unknown"]
    audit_logging: Literal["implemented", "partial", "missing", "unknown"]
    security_framework: str  # Spring Security, JWT, OAuth2, None detected
    concerns: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    overall_posture: Literal["strong", "adequate", "weak", "unknown"]
    reasoning: str


class OperationalReadinessOutput(BaseModel):
    """Task 3.4: analyze_operational_readiness output."""
    health_checks: Literal["implemented", "partial", "missing"]
    monitoring: Literal["ready", "partial", "not ready"]
    logging: Literal["structured", "basic", "insufficient"]
    metrics: Literal["implemented", "partial", "missing"]
    configuration: Literal["externalized", "hardcoded", "mixed"]
    deployment_readiness: Literal["production-ready", "needs-work", "not-ready"]
    recommendations: List[str] = Field(default_factory=list)
    reasoning: str


# =============================================================================
# SYNTHESIS OUTPUT (Task 4 - Final Merged Output)
# =============================================================================

class SystemInfo(BaseModel):
    """System metadata."""
    name: str
    description: str


class MicroArchitecture(BaseModel):
    """Micro architecture (backend + frontend patterns)."""
    backend: BackendPatternOutput
    frontend: FrontendPatternOutput


class DomainSection(BaseModel):
    """Domain-related analysis."""
    model: DomainModelOutput
    capabilities: BusinessCapabilitiesOutput
    bounded_contexts: BoundedContextsOutput


class WorkflowsSection(BaseModel):
    """Workflow-related analysis."""
    state_machines: StateMachinesOutput
    workflow_engines: WorkflowEnginesOutput
    saga_patterns: SagaPatternsOutput
    runtime_scenarios: RuntimeScenariosOutput


class QualitySection(BaseModel):
    """Quality-related analysis."""
    complexity: ComplexityOutput
    technical_debt: TechnicalDebtOutput
    security: SecurityOutput
    operational_readiness: OperationalReadinessOutput


class AnalyzedArchitecture(BaseModel):
    """Task 4: synthesize_architecture final output.
    
    This is the complete analyzed_architecture.json schema.
    """
    system: SystemInfo
    macro_architecture: MacroArchitectureOutput
    micro_architecture: MicroArchitecture
    architecture_quality: ArchitectureQualityOutput
    domain: DomainSection
    workflows: WorkflowsSection
    api: ApiDesignOutput
    quality: QualitySection
    overall_grade: Literal["A", "B", "C", "D", "F"]
    executive_summary: str
    top_recommendations: List[str] = Field(default_factory=list)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Tech Architect
    "MacroArchitectureOutput",
    "BackendPatternOutput",
    "FrontendPatternOutput",
    "ArchitectureQualityOutput",
    # Func Analyst
    "DomainModelOutput",
    "BusinessCapabilitiesOutput",
    "BoundedContextsOutput",
    "StateMachinesOutput",
    "WorkflowEnginesOutput",
    "SagaPatternsOutput",
    "RuntimeScenariosOutput",
    "ApiDesignOutput",
    # Quality Analyst
    "ComplexityOutput",
    "TechnicalDebtOutput",
    "SecurityOutput",
    "OperationalReadinessOutput",
    # Synthesis
    "AnalyzedArchitecture",
]
