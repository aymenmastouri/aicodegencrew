"""
Architecture Analysis Crew - Task Definitions
===============================================
17 focused tasks across 5 mini-crews for architecture analysis.

Each task is defined as (description, expected_output, output_pydantic, output_filename).
Task descriptions contain step-by-step instructions for the LLM agents.

Mini-Crew Layout:
  1. tech_analysis    (tech_architect)   -> 4 tasks
  2. domain_analysis  (func_analyst)     -> 4 tasks
  3. workflow_analysis (func_analyst)    -> 4 tasks
  4. quality_analysis (quality_analyst)  -> 4 tasks
  5. synthesis        (synthesis_lead)   -> 1 task
"""

from ...shared.models import (
    AnalyzedArchitecture,
    ApiDesignOutput,
    ArchitectureQualityOutput,
    BackendPatternOutput,
    BoundedContextsOutput,
    BusinessCapabilitiesOutput,
    ComplexityOutput,
    DomainModelOutput,
    FrontendPatternOutput,
    MacroArchitectureOutput,
    OperationalReadinessOutput,
    RuntimeScenariosOutput,
    SagaPatternsOutput,
    SecurityOutput,
    StateMachinesOutput,
    TechnicalDebtOutput,
    WorkflowEnginesOutput,
)

# =============================================================================
# TECH ARCHITECT TASKS (1.1 - 1.4)
# =============================================================================

ANALYZE_MACRO_ARCHITECTURE_DESC = """\
Analyze MACRO ARCHITECTURE style of the system.

STEPS:
1. Call: get_facts_statistics() to understand scale (component/container counts)
2. Call: list_components_by_stereotype(stereotype="architecture_style")
3. Call: query_facts(category="containers") to list all containers
4. Determine architecture style based on evidence:
   - 1 container = Monolith
   - 1 container + clear module boundaries = Modular Monolith
   - Multiple containers with REST APIs between them = Microservices
   - Mix = Hybrid
5. Identify deployment model and communication patterns

Base your analysis on tool query results."""

ANALYZE_MACRO_ARCHITECTURE_OUTPUT = """\
Valid JSON object with these exact keys:
{"style": "Monolith|Modular Monolith|Microservices|Hybrid",
 "container_count": <number>,
 "containers": [{"name": "...", "type": "..."}],
 "reasoning": "Evidence-based explanation",
 "scalability_approach": "vertical|horizontal",
 "deployment_model": "single|distributed",
 "communication_pattern": "sync REST|async messaging|mixed"}"""


ANALYZE_BACKEND_PATTERN_DESC = """\
Analyze BACKEND architectural pattern.

STEPS:
1. Call: get_facts_statistics() - check components_by_stereotype breakdown
2. Call: list_components_by_stereotype(stereotype="controller", limit=50)
3. Call: list_components_by_stereotype(stereotype="service", limit=50)
4. Call: list_components_by_stereotype(stereotype="repository", limit=50)
5. Analyze layer distribution to determine pattern:
   - Layered: clear controller -> service -> repository separation
   - Hexagonal: ports/adapters naming convention, domain isolation
   - Clean Architecture: use cases, entities, interfaces directories
   - CQRS: separate command/query handlers

Use actual component counts from tool results."""

ANALYZE_BACKEND_PATTERN_OUTPUT = """\
Valid JSON object with these exact keys:
{"primary_pattern": "Layered|Hexagonal|Clean Architecture|CQRS|Unknown",
 "layer_structure": ["Controller", "Service", "Repository"],
 "component_counts": {"controller": <n>, "service": <n>, "repository": <n>},
 "technology": {"framework": "<detected framework>", "language": "<detected language>"},
 "layer_violations": <number>,
 "reasoning": "Evidence-based explanation"}"""


ANALYZE_FRONTEND_PATTERN_DESC = """\
Analyze FRONTEND architectural pattern.

STEPS:
1. Call: query_facts(category="containers") - find frontend container(s)
2. Call: list_components_by_stereotype(stereotype="component", limit=50)
3. Call: list_components_by_stereotype(stereotype="module", limit=50)
4. Check container metadata for framework (Angular, React, Vue)
5. Determine pattern:
   - Component-Based SPA: Angular/React/Vue with components + modules
   - Micro-Frontends: multiple independent frontend applications
   - Server-Rendered: minimal JavaScript, server-side templates
   - No Frontend: backend-only system

If no frontend container exists, report "No Frontend"."""

ANALYZE_FRONTEND_PATTERN_OUTPUT = """\
Valid JSON object with these exact keys:
{"primary_pattern": "Component-Based SPA|Micro-Frontends|Server-Rendered|No Frontend",
 "framework": "Angular|React|Vue|None",
 "module_structure": "feature-based|flat|layered",
 "state_management": "NgRx|Redux|Vuex|None|Unknown",
 "routing_strategy": "lazy-loaded|eager|Unknown",
 "component_count": <number>,
 "reasoning": "Evidence-based explanation"}"""


ANALYZE_ARCHITECTURE_QUALITY_DESC = """\
Assess ARCHITECTURE QUALITY metrics.

STEPS:
1. Call: get_facts_statistics() - get total components, relations, interfaces
2. Call: query_facts(category="relations", limit=100)
3. Calculate: relations_per_component = total_relations / total_components
4. Check for layer violations (controller directly calling repository)
5. Look for circular dependencies (A->B->C->A)
6. Assess coupling:
   - ratio < 1.0 = loose coupling
   - ratio 1.0-3.0 = moderate coupling
   - ratio > 3.0 = tight coupling

Use actual numbers from statistics."""

ANALYZE_ARCHITECTURE_QUALITY_OUTPUT = """\
Valid JSON object with these exact keys:
{"separation_of_concerns": "good|moderate|poor",
 "layer_violations_count": <number>,
 "coupling_assessment": "loose|moderate|tight",
 "relations_per_component": <float>,
 "circular_dependencies": <number>,
 "overall_grade": "A|B|C|D|F",
 "reasoning": "Evidence-based explanation with actual numbers"}"""


# =============================================================================
# FUNCTIONAL ANALYST TASKS (2.1 - 2.8)
# =============================================================================

ANALYZE_DOMAIN_MODEL_DESC = """\
Analyze the DOMAIN MODEL of the system.

STEPS:
1. Call: get_facts_statistics() - check entity count and distribution
2. Call: list_components_by_stereotype(stereotype="entity", limit=100)
3. Group entities by naming prefix (e.g., Order*, User*, Document*)
4. Each prefix group = one domain area
5. Identify core domains (most entities) vs supporting domains (few entities)
6. Assess naming consistency

List ALL entity names from tool results. Group by actual naming patterns."""

ANALYZE_DOMAIN_MODEL_OUTPUT = """\
Valid JSON object with these exact keys:
{"total_entities": <number>,
 "domain_areas": [{"name": "...", "entities": ["Entity1", "Entity2"], "type": "core|supporting"}],
 "domain_complexity": "simple|moderate|complex",
 "naming_consistency": "consistent|mixed|inconsistent",
 "reasoning": "Evidence-based explanation listing actual entity names"}"""


ANALYZE_BUSINESS_CAPABILITIES_DESC = """\
Identify BUSINESS CAPABILITIES from services.

STEPS:
1. Call: list_components_by_stereotype(stereotype="service", limit=100)
2. Group services by naming prefix (e.g., OrderService, OrderValidationService = "Order Management")
3. Each prefix group = one business capability
4. Assess capability maturity (number of services per capability)
5. Identify gaps (entities without corresponding services)

EXAMPLE GROUPING:
- OrderService, OrderValidationService, OrderMapper -> "Order Management"
- UserService, AuthService, LoginService -> "User & Authentication\""""

ANALYZE_BUSINESS_CAPABILITIES_OUTPUT = """\
Valid JSON object with these exact keys:
{"capabilities": [{"name": "...", "services": ["Service1", "Service2"],
                   "description": "...", "maturity": "basic|intermediate|mature"}],
 "total_services": <number>,
 "capability_coverage": "comprehensive|partial|minimal",
 "reasoning": "Evidence-based explanation"}"""


ANALYZE_BOUNDED_CONTEXTS_DESC = """\
Identify BOUNDED CONTEXTS (DDD perspective).

STEPS:
1. Call: get_facts_statistics() - understand overall scale
2. Call: list_components_by_stereotype(stereotype="entity", limit=50)
3. Call: list_components_by_stereotype(stereotype="service", limit=50)
4. Cross-reference: entities + services with same naming prefix = one bounded context
5. Call: query_facts(category="relations", limit=50) to find cross-context dependencies
6. Assess coupling between contexts

CONTEXT DETECTION: Components sharing a naming prefix belong to the same context."""

ANALYZE_BOUNDED_CONTEXTS_OUTPUT = """\
Valid JSON object with these exact keys:
{"contexts_identified": <number>,
 "contexts": [{"name": "...", "entities": ["..."], "services": ["..."],
               "component_count": <n>}],
 "cross_context_coupling": "low|moderate|high",
 "recommendations": ["..."],
 "reasoning": "Evidence-based explanation"}"""


ANALYZE_STATE_MACHINES_DESC = """\
Detect STATE MACHINES in the codebase (framework-agnostic).

STEPS:
1. Call: rag_query("state machine StateMachine enum Status")
2. Call: rag_query("status transition PENDING APPROVED REJECTED")
3. Call: list_components_by_stereotype(stereotype="entity", limit=50)
4. Look for entities with status/state fields in names

INDICATORS (examples across languages):
- Enum types with state values (PENDING, APPROVED, REJECTED, ACTIVE, INACTIVE)
- Classes/modules with "State" or "Status" in name
- Transition methods (approve(), reject(), activate(), transition_to())
- State machine libraries (e.g., Spring State Machine in Java,
  python-statemachine/transitions in Python, Stateless in C#,
  looplab/fsm in Go, xstate in TypeScript)

If not found, report detected=false."""

ANALYZE_STATE_MACHINES_OUTPUT = """\
Valid JSON object with these exact keys:
{"detected": true|false,
 "implementation_type": "Library-based|Enum-based|Custom|None",
 "stateful_entities": ["EntityName"],
 "state_transitions": [{"entity": "...", "states": ["STATE1", "STATE2"]}],
 "reasoning": "Evidence-based explanation"}"""


ANALYZE_WORKFLOW_ENGINES_DESC = """\
Detect WORKFLOW / PROCESS ENGINES (framework-agnostic).

STEPS:
1. Call: rag_query("workflow engine process BPMN pipeline")
2. Call: rag_query("Camunda Flowable Activiti Temporal Celery Airflow")
3. Call: list_components_by_stereotype(stereotype="design_pattern")
4. Check for workflow-related components or configurations

INDICATORS (examples across languages):
- Java/Spring: Camunda, Flowable, Activiti dependencies; .bpmn files; ProcessEngine beans
- Python: Celery task chains, Airflow DAGs, Prefect flows
- .NET: Workflow Foundation, Elsa Workflows
- Go/Node: Temporal workers, Bull queues
- General: State machine libraries, pipeline/step patterns

If not found, report engine="None"."""

ANALYZE_WORKFLOW_ENGINES_OUTPUT = """\
Valid JSON object with these exact keys:
{"engine": "<detected engine name or None>",
 "version": "...|Unknown",
 "bpmn_processes": ["process_name"],
 "integration_style": "embedded|standalone|library|None",
 "workflow_services": ["ServiceName"],
 "reasoning": "Evidence-based explanation"}"""


ANALYZE_SAGA_PATTERNS_DESC = """\
Detect SAGA patterns for distributed transactions.

STEPS:
1. Call: rag_query("saga pattern compensation rollback")
2. Call: rag_query("outbox pattern event publishing")
3. Call: list_components_by_stereotype(stereotype="design_pattern")
4. Look for saga orchestrator or choreography patterns

INDICATORS:
- Saga orchestrator classes
- Compensation/rollback methods
- Outbox tables or event sourcing
- @SagaEventHandler annotations

If not found, report detected=false."""

ANALYZE_SAGA_PATTERNS_OUTPUT = """\
Valid JSON object with these exact keys:
{"detected": true|false,
 "style": "orchestration|choreography|None",
 "sagas": ["SagaName"],
 "outbox_pattern": true|false,
 "event_store": true|false,
 "reasoning": "Evidence-based explanation"}"""


ANALYZE_RUNTIME_SCENARIOS_DESC = """\
Identify key RUNTIME SCENARIOS for Arc42 Section 6.

STEPS:
1. Call: list_components_by_stereotype(stereotype="controller", limit=30)
2. Call: query_facts(category="interfaces", limit=30)
3. For the top 3-5 most important endpoints, trace the call flow:
   controller -> service -> repository -> entity
4. Document each scenario with trigger, steps, and end state

SCENARIO FORMAT:
- Name: descriptive name (e.g., "Create Order")
- Trigger: HTTP POST /api/orders
- Steps: OrderController -> OrderService -> OrderRepository
- End state: Order persisted, 201 Created returned"""

ANALYZE_RUNTIME_SCENARIOS_OUTPUT = """\
Valid JSON object with these exact keys:
{"scenarios": [{"name": "...", "trigger": "HTTP METHOD /path",
                "steps": ["Component1", "Component2", "Component3"],
                "end_state": "..."}],
 "total_endpoints": <number>,
 "orchestration_style": "synchronous|asynchronous|mixed",
 "reasoning": "Evidence-based explanation"}"""


ANALYZE_API_DESIGN_DESC = """\
Assess API DESIGN QUALITY.

STEPS:
1. Call: get_facts_statistics() - check interface statistics
2. Call: query_facts(category="interfaces", limit=50)
3. Analyze HTTP verb distribution (GET, POST, PUT, DELETE, PATCH)
4. Check URL patterns for versioning (/v1/, /api/v2/)
5. Assess naming consistency across controllers
6. Check for RESTful resource naming

METRICS:
- RESTfulness: proper verb usage with resource URLs
- Consistency: same URL patterns across all controllers
- Versioning: presence of API version in URLs
- Completeness: CRUD coverage per resource"""

ANALYZE_API_DESIGN_OUTPUT = """\
Valid JSON object with these exact keys:
{"total_endpoints": <number>,
 "verb_distribution": {"GET": <n>, "POST": <n>, "PUT": <n>, "DELETE": <n>},
 "restfulness": "good|moderate|poor",
 "consistency": "consistent|mixed|inconsistent",
 "versioning_strategy": "URL-based|header-based|none",
 "naming_quality": "good|moderate|poor",
 "recommendations": ["..."],
 "reasoning": "Evidence-based explanation with actual endpoint examples"}"""


# =============================================================================
# QUALITY ANALYST TASKS (3.1 - 3.4)
# =============================================================================

ANALYZE_COMPLEXITY_DESC = """\
Assess STRUCTURAL and COGNITIVE COMPLEXITY.

STEPS:
1. Call: get_facts_statistics() - get total counts
2. Calculate: relations_per_component = total_relations / total_components
3. Identify complexity hotspots (components with most relations)
4. Classify scale:
   - < 500 components: Low complexity
   - 500-5000: Medium complexity
   - 5000+: High/Enterprise complexity

Use actual numbers from get_facts_statistics()."""

ANALYZE_COMPLEXITY_OUTPUT = """\
Valid JSON object with these exact keys:
{"total_components": <number>,
 "total_relations": <number>,
 "total_interfaces": <number>,
 "relations_per_component": <float>,
 "structural_complexity": "low|medium|high",
 "scale": "small|medium|large|enterprise",
 "hotspots": [{"component": "...", "relation_count": <n>}],
 "reasoning": "Evidence-based explanation with actual numbers"}"""


ANALYZE_TECHNICAL_DEBT_DESC = """\
Assess TECHNICAL DEBT level.

STEPS:
1. Call: rag_query("TODO FIXME HACK workaround")
2. Call: rag_query("deprecated @Deprecated SuppressWarnings")
3. Call: get_facts_statistics() - for context
4. Categorize debt indicators found:
   - Code debt: TODO/FIXME markers
   - Design debt: deprecated patterns still in use
   - Test debt: missing test coverage indicators

Report only what RAG search finds."""

ANALYZE_TECHNICAL_DEBT_OUTPUT = """\
Valid JSON object with these exact keys:
{"debt_level": "low|moderate|high|critical",
 "indicators_found": <number>,
 "categories": {"code_debt": <n>, "design_debt": <n>, "test_debt": <n>},
 "top_items": [{"type": "TODO|FIXME|deprecated", "location": "file/class", "description": "..."}],
 "estimated_effort": "days|weeks|months",
 "reasoning": "Evidence-based explanation with actual findings"}"""


ANALYZE_SECURITY_DESC = """\
Assess SECURITY POSTURE (framework-agnostic).

STEPS:
1. Call: rag_query("security config authentication middleware filter")
2. Call: rag_query("JWT OAuth2 token authentication session cookie")
3. Call: rag_query("authorization permission role access control")
4. Call: rag_query("CSRF XSS input validation sanitize")
5. Assess each security dimension:
   - Authentication: mechanism used (JWT, OAuth2, Basic, Session, API keys)
   - Authorization: Look for authorization annotations/decorators (e.g.,
     @PreAuthorize in Java/Spring, @login_required in Python/Django,
     [Authorize] in C#/.NET, auth middleware in Go/Express)
   - Input validation: annotation-based, decorator-based, or manual
   - Audit logging: present or absent

Report only security patterns found by RAG search."""

ANALYZE_SECURITY_OUTPUT = """\
Valid JSON object with these exact keys:
{"authentication": {"mechanism": "JWT|OAuth2|Basic|Session|Unknown", "configured": true|false},
 "authorization": {"framework": "<detected framework or None>", "method_level": true|false},
 "input_validation": "annotation-based|decorator-based|middleware|manual|none|unknown",
 "audit_logging": true|false,
 "security_framework": "<detected framework or None|Unknown>",
 "overall_posture": "strong|moderate|weak|unknown",
 "concerns": ["..."],
 "recommendations": ["..."],
 "reasoning": "Evidence-based explanation"}"""


ANALYZE_OPERATIONAL_READINESS_DESC = """\
Assess OPERATIONAL READINESS (framework-agnostic).

STEPS:
1. Call: rag_query("health check endpoint liveness readiness probe")
2. Call: rag_query("logging structured log level logger")
3. Call: rag_query("configuration environment profile settings")
4. Call: rag_query("metrics prometheus monitoring observability")
5. Assess each operational dimension:
   - Health checks: e.g., Spring Actuator in Java, /health endpoints in any
     framework, Kubernetes liveness/readiness probes, ASP.NET health checks
   - Monitoring: metrics endpoints (e.g., Micrometer/Prometheus in Java,
     prometheus_client in Python, OpenTelemetry in any language)
   - Logging: structured logging (e.g., SLF4J/Logback in Java, structlog in
     Python, Serilog in C#, zap/zerolog in Go)
   - Configuration: externalized config, environment variables, profiles

Report only what RAG search confirms."""

ANALYZE_OPERATIONAL_READINESS_OUTPUT = """\
Valid JSON object with these exact keys:
{"health_checks": {"present": true|false, "framework": "<detected framework or None>"},
 "monitoring": {"metrics": true|false, "framework": "<detected framework or None>"},
 "logging": {"framework": "<detected framework or Unknown>", "structured": true|false},
 "configuration": {"externalized": true|false, "profiles": true|false},
 "deployment_readiness": "production-ready|needs-work|minimal",
 "recommendations": ["..."],
 "reasoning": "Evidence-based explanation"}"""


# =============================================================================
# SYNTHESIS TASK (4.0)
# =============================================================================

SYNTHESIZE_ARCHITECTURE_DESC = """\
Synthesize ALL 16 analysis results into the final analyzed_architecture.json.

STEPS:
1. Call: read_partial_results() to load all 16 analysis JSON files
2. Review each section for completeness and consistency
3. Cross-validate numbers (component counts should match across sections)
4. Resolve any conflicts between agent assessments
5. Calculate overall architecture grade (A-F):
   - A: Well-structured, low debt, good security, production-ready
   - B: Good structure, moderate debt, some improvements needed
   - C: Acceptable but significant improvements needed
   - D: Poor structure, high debt, major concerns
   - F: Critical issues, needs immediate attention
6. Write executive summary (2-3 sentences)
7. Create top 5 recommendations list

STRUCTURE of output:
- system: name, description
- macro_architecture: from task 1.1
- micro_architecture: backend (1.2) + frontend (1.3)
- architecture_quality: from task 1.4
- domain: model (2.1) + capabilities (2.2) + contexts (2.3)
- workflows: state machines (2.4) + engines (2.5) + sagas (2.6) + scenarios (2.7)
- api: from task 2.8
- quality: complexity (3.1) + debt (3.2) + security (3.3) + ops (3.4)

If a section has no analysis, mark it "NOT_ANALYZED"."""

SYNTHESIZE_ARCHITECTURE_OUTPUT = """\
Complete valid JSON matching the AnalyzedArchitecture schema. Must include:
executive_summary, overall_grade (A-F), all 16 analysis sections merged,
and top_recommendations list. Every section must be populated from
partial results or marked as "NOT_ANALYZED"."""


# =============================================================================
# MINI-CREW TASK LISTS
# Each tuple: (description, expected_output, output_pydantic, output_filename)
# =============================================================================

TECH_ANALYSIS_TASKS = [
    (
        ANALYZE_MACRO_ARCHITECTURE_DESC,
        ANALYZE_MACRO_ARCHITECTURE_OUTPUT,
        MacroArchitectureOutput,
        "01_macro_architecture.json",
    ),
    (ANALYZE_BACKEND_PATTERN_DESC, ANALYZE_BACKEND_PATTERN_OUTPUT, BackendPatternOutput, "02_backend_pattern.json"),
    (ANALYZE_FRONTEND_PATTERN_DESC, ANALYZE_FRONTEND_PATTERN_OUTPUT, FrontendPatternOutput, "03_frontend_pattern.json"),
    (
        ANALYZE_ARCHITECTURE_QUALITY_DESC,
        ANALYZE_ARCHITECTURE_QUALITY_OUTPUT,
        ArchitectureQualityOutput,
        "04_architecture_quality.json",
    ),
]

DOMAIN_ANALYSIS_TASKS = [
    (ANALYZE_DOMAIN_MODEL_DESC, ANALYZE_DOMAIN_MODEL_OUTPUT, DomainModelOutput, "05_domain_model.json"),
    (
        ANALYZE_BUSINESS_CAPABILITIES_DESC,
        ANALYZE_BUSINESS_CAPABILITIES_OUTPUT,
        BusinessCapabilitiesOutput,
        "06_business_capabilities.json",
    ),
    (ANALYZE_BOUNDED_CONTEXTS_DESC, ANALYZE_BOUNDED_CONTEXTS_OUTPUT, BoundedContextsOutput, "07_bounded_contexts.json"),
    (ANALYZE_STATE_MACHINES_DESC, ANALYZE_STATE_MACHINES_OUTPUT, StateMachinesOutput, "08_state_machines.json"),
]

WORKFLOW_ANALYSIS_TASKS = [
    (ANALYZE_WORKFLOW_ENGINES_DESC, ANALYZE_WORKFLOW_ENGINES_OUTPUT, WorkflowEnginesOutput, "09_workflow_engines.json"),
    (ANALYZE_SAGA_PATTERNS_DESC, ANALYZE_SAGA_PATTERNS_OUTPUT, SagaPatternsOutput, "10_saga_patterns.json"),
    (
        ANALYZE_RUNTIME_SCENARIOS_DESC,
        ANALYZE_RUNTIME_SCENARIOS_OUTPUT,
        RuntimeScenariosOutput,
        "11_runtime_scenarios.json",
    ),
    (ANALYZE_API_DESIGN_DESC, ANALYZE_API_DESIGN_OUTPUT, ApiDesignOutput, "12_api_design.json"),
]

QUALITY_ANALYSIS_TASKS = [
    (ANALYZE_COMPLEXITY_DESC, ANALYZE_COMPLEXITY_OUTPUT, ComplexityOutput, "13_complexity.json"),
    (ANALYZE_TECHNICAL_DEBT_DESC, ANALYZE_TECHNICAL_DEBT_OUTPUT, TechnicalDebtOutput, "14_technical_debt.json"),
    (ANALYZE_SECURITY_DESC, ANALYZE_SECURITY_OUTPUT, SecurityOutput, "15_security.json"),
    (
        ANALYZE_OPERATIONAL_READINESS_DESC,
        ANALYZE_OPERATIONAL_READINESS_OUTPUT,
        OperationalReadinessOutput,
        "16_operational_readiness.json",
    ),
]

SYNTHESIS_TASKS = [
    (SYNTHESIZE_ARCHITECTURE_DESC, SYNTHESIZE_ARCHITECTURE_OUTPUT, AnalyzedArchitecture, "analyzed_architecture.json"),
]
