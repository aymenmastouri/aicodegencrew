"""
Architecture Analysis Crew - Phase 2
=====================================
Mini-Crew pattern: 5 independent crews, each with fresh LLM context.
NO YAML. All configuration in Python constants.

ANALYSIS APPROACH:
- Input: architecture_facts.json + evidence_map.json + ChromaDB Index
- 4 Specialized Agents: Technical, Functional, Quality, Synthesis
- 17 Focused Tasks in 5 Mini-Crews
- Output: analyzed_architecture.json

Mini-Crew Layout:
  1. tech_analysis    (tech_architect)   -> 4 tasks
  2. domain_analysis  (func_analyst)     -> 4 tasks
  3. workflow_analysis (func_analyst)    -> 4 tasks
  4. quality_analysis (quality_analyst)  -> 4 tasks
  5. synthesis        (synthesis_lead)   -> 1 task
"""
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, Any, Set, List

from crewai import Agent, Crew, LLM, Task, Process
from crewai.mcp import MCPServerStdio
from crewai_tools import FileWriterTool

from .tools import FactsStatisticsTool, FactsQueryTool, RAGQueryTool, StereotypeListTool, PartialResultsTool
from ...shared.utils.tool_guardrails import install_guardrails, uninstall_guardrails

# MCP server script path (project root)
_MCP_SERVER_PATH = str(Path(__file__).resolve().parents[4] / "mcp_server.py")

# Import Pydantic schemas for output validation
from ...shared.models import (
    MacroArchitectureOutput,
    BackendPatternOutput,
    FrontendPatternOutput,
    ArchitectureQualityOutput,
    DomainModelOutput,
    BusinessCapabilitiesOutput,
    BoundedContextsOutput,
    StateMachinesOutput,
    WorkflowEnginesOutput,
    SagaPatternsOutput,
    RuntimeScenariosOutput,
    ApiDesignOutput,
    ComplexityOutput,
    TechnicalDebtOutput,
    SecurityOutput,
    OperationalReadinessOutput,
    AnalyzedArchitecture,
)

logger = logging.getLogger(__name__)


# =============================================================================
# AGENT CONFIGURATIONS (moved from config/agents.yaml)
# =============================================================================

AGENT_CONFIGS = {
    "tech_architect": {
        "role": "Senior Technical Architect",
        "goal": (
            "Analyze architecture styles, design patterns, technology stack, and layer "
            "structure from extracted architecture facts. Produce structured JSON output "
            "for each analysis dimension."
        ),
        "backstory": (
            "You are a senior technical architect with 15+ years of experience in "
            "enterprise software. You specialize in identifying architecture patterns "
            "(Layered, Hexagonal, Clean Architecture, CQRS, Event-Driven) from code "
            "structure. You always start with get_facts_statistics() to understand the "
            "scale before diving into details. You use stereotype filters (controller, "
            "service, repository) to identify layer distribution. You never invent "
            "components - every claim must be backed by tool query results. Tools return "
            "max 50 results, so use filters wisely. Output strictly valid JSON matching "
            "the expected schema."
        ),
    },
    "func_analyst": {
        "role": "Senior Functional Analyst",
        "goal": (
            "Analyze domain model, business capabilities, bounded contexts, workflows, "
            "and API design from extracted architecture facts. Produce structured JSON "
            "output for each analysis dimension."
        ),
        "backstory": (
            "You are a senior functional analyst who bridges business and technology. "
            "You specialize in Domain-Driven Design (DDD) and identifying bounded "
            "contexts from code structure. You group entities and services by naming "
            'prefix to discover domain areas (e.g., OrderService + OrderEntity = '
            '"Order Management" domain). You detect state machines from enum types '
            "and status fields, workflow engines from BPMN/Camunda patterns. You always "
            "start with get_facts_statistics() for overview. Tools return max 50 results - "
            "use stereotype and container filters. Never invent domain concepts - derive "
            "them strictly from component names and relations. Output strictly valid JSON."
        ),
    },
    "quality_analyst": {
        "role": "Senior Quality Architect",
        "goal": (
            "Analyze technical debt, structural complexity, security posture, and "
            "operational readiness from architecture facts and code search. Produce "
            "structured JSON output for each quality dimension."
        ),
        "backstory": (
            "You are a quality-focused architect who identifies risks, technical debt, "
            "and operational gaps. You calculate metrics like relations-per-component "
            "ratio for coupling assessment. You use RAG search to find TODO/FIXME markers, "
            "deprecated annotations, security configurations (@PreAuthorize, Spring "
            "Security), and operational patterns (Actuator, health checks). You classify "
            "complexity by component count thresholds (<500=Low, 500-5000=Medium, "
            "5000+=High). You always start with get_facts_statistics() for scale context. "
            "Tools return max 50 results. Never speculate about security issues - only "
            "report what tool queries confirm. Output strictly valid JSON."
        ),
    },
    "synthesis_lead": {
        "role": "Lead Architect - Synthesis",
        "goal": (
            "Merge all 16 partial analysis results into a unified analyzed_architecture.json "
            "that matches the AnalyzedArchitecture schema. Produce a complete, coherent "
            "architecture document with executive summary and overall grade."
        ),
        "backstory": (
            "You are the lead architect responsible for consolidating all analysis "
            "perspectives into one coherent architecture document. You use "
            "read_partial_results() to load all 16 JSON analysis files. You "
            "cross-validate numbers (component counts must be consistent across sections). "
            "You resolve conflicts between agent assessments by favoring evidence-backed "
            "conclusions. You calculate an overall architecture grade (A-F) based on "
            "quality metrics. You write a concise executive summary. You NEVER invent "
            'data - if a section has no analysis, mark it as "UNKNOWN" or "NOT_ANALYZED". '
            "Your output must be valid JSON matching the AnalyzedArchitecture Pydantic schema."
        ),
    },
}


# =============================================================================
# TASK DESCRIPTIONS (moved from config/tasks.yaml)
# =============================================================================

# --- TECH ARCHITECT TASKS (1.1 - 1.4) ---

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

IMPORTANT: Base your analysis ONLY on tool query results. Do not invent containers or components."""

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

IMPORTANT: Count actual components from tool results. Do not estimate."""

ANALYZE_BACKEND_PATTERN_OUTPUT = """\
Valid JSON object with these exact keys:
{"primary_pattern": "Layered|Hexagonal|Clean Architecture|CQRS|Unknown",
 "layer_structure": ["Controller", "Service", "Repository"],
 "component_counts": {"controller": <n>, "service": <n>, "repository": <n>},
 "technology": {"framework": "Spring Boot|Angular|...", "language": "Java|TypeScript|..."},
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

IMPORTANT: If no frontend container exists, report "No Frontend" - do not invent one."""

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

IMPORTANT: Use actual numbers from statistics. Do not estimate."""

ANALYZE_ARCHITECTURE_QUALITY_OUTPUT = """\
Valid JSON object with these exact keys:
{"separation_of_concerns": "good|moderate|poor",
 "layer_violations_count": <number>,
 "coupling_assessment": "loose|moderate|tight",
 "relations_per_component": <float>,
 "circular_dependencies": <number>,
 "overall_grade": "A|B|C|D|F",
 "reasoning": "Evidence-based explanation with actual numbers"}"""


# --- FUNCTIONAL ANALYST TASKS (2.1 - 2.8) ---

ANALYZE_DOMAIN_MODEL_DESC = """\
Analyze the DOMAIN MODEL of the system.

STEPS:
1. Call: get_facts_statistics() - check entity count and distribution
2. Call: list_components_by_stereotype(stereotype="entity", limit=100)
3. Group entities by naming prefix (e.g., Order*, User*, Document*)
4. Each prefix group = one domain area
5. Identify core domains (most entities) vs supporting domains (few entities)
6. Assess naming consistency

IMPORTANT: List ALL entity names from tool results. Group by actual naming patterns."""

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
Detect STATE MACHINES in the codebase.

STEPS:
1. Call: rag_query("state machine StateMachine enum Status")
2. Call: rag_query("status transition PENDING APPROVED REJECTED")
3. Call: list_components_by_stereotype(stereotype="entity", limit=50)
4. Look for entities with status/state fields in names

INDICATORS:
- Spring State Machine annotations
- Enum types with state values (PENDING, APPROVED, REJECTED, ACTIVE, INACTIVE)
- Classes with "State" or "Status" in name
- Transition methods (approve(), reject(), activate())

IMPORTANT: If no state machines found, report detected=false. Do not invent them."""

ANALYZE_STATE_MACHINES_OUTPUT = """\
Valid JSON object with these exact keys:
{"detected": true|false,
 "implementation_type": "Spring State Machine|Enum-based|Custom|None",
 "stateful_entities": ["EntityName"],
 "state_transitions": [{"entity": "...", "states": ["STATE1", "STATE2"]}],
 "reasoning": "Evidence-based explanation"}"""


ANALYZE_WORKFLOW_ENGINES_DESC = """\
Detect WORKFLOW ENGINES (BPMN, Camunda, Flowable).

STEPS:
1. Call: rag_query("Camunda BPMN workflow ProcessEngine")
2. Call: rag_query("Flowable Activiti process definition")
3. Call: list_components_by_stereotype(stereotype="design_pattern")
4. Check for workflow-related components or configurations

INDICATORS:
- Camunda/Flowable library dependencies
- .bpmn or .bpmn20.xml files
- ProcessEngine or RuntimeService beans
- @ProcessVariable annotations

IMPORTANT: If no workflow engine found, report engine="None". Do not invent."""

ANALYZE_WORKFLOW_ENGINES_OUTPUT = """\
Valid JSON object with these exact keys:
{"engine": "Camunda|Flowable|Activiti|None",
 "version": "...|Unknown",
 "bpmn_processes": ["process_name"],
 "integration_style": "embedded|standalone|None",
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

IMPORTANT: If no saga patterns found, report detected=false. Do not invent."""

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


# --- QUALITY ANALYST TASKS (3.1 - 3.4) ---

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

IMPORTANT: Use actual numbers from get_facts_statistics(). Do not estimate."""

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

IMPORTANT: Only report what RAG search actually finds. Do not speculate."""

ANALYZE_TECHNICAL_DEBT_OUTPUT = """\
Valid JSON object with these exact keys:
{"debt_level": "low|moderate|high|critical",
 "indicators_found": <number>,
 "categories": {"code_debt": <n>, "design_debt": <n>, "test_debt": <n>},
 "top_items": [{"type": "TODO|FIXME|deprecated", "location": "file/class", "description": "..."}],
 "estimated_effort": "days|weeks|months",
 "reasoning": "Evidence-based explanation with actual findings"}"""


ANALYZE_SECURITY_DESC = """\
Assess SECURITY POSTURE.

STEPS:
1. Call: rag_query("Spring Security WebSecurityConfigurer SecurityConfig")
2. Call: rag_query("JWT OAuth2 token authentication")
3. Call: rag_query("@PreAuthorize @Secured @RolesAllowed")
4. Call: rag_query("CSRF XSS input validation sanitize")
5. Assess each security dimension:
   - Authentication: mechanism used (JWT, OAuth2, Basic, Session)
   - Authorization: framework used (Spring Security, custom)
   - Input validation: annotation-based or manual
   - Audit logging: present or absent

IMPORTANT: Only report security patterns found by RAG search. Do not assume."""

ANALYZE_SECURITY_OUTPUT = """\
Valid JSON object with these exact keys:
{"authentication": {"mechanism": "JWT|OAuth2|Basic|Session|Unknown", "configured": true|false},
 "authorization": {"framework": "Spring Security|Custom|None", "method_level": true|false},
 "input_validation": "annotation-based|manual|none|unknown",
 "audit_logging": true|false,
 "security_framework": "Spring Security|None|Unknown",
 "overall_posture": "strong|moderate|weak|unknown",
 "concerns": ["..."],
 "recommendations": ["..."],
 "reasoning": "Evidence-based explanation"}"""


ANALYZE_OPERATIONAL_READINESS_DESC = """\
Assess OPERATIONAL READINESS.

STEPS:
1. Call: rag_query("actuator health endpoint HealthIndicator")
2. Call: rag_query("slf4j logback logging structured log")
3. Call: rag_query("@ConfigurationProperties environment profile")
4. Call: rag_query("micrometer prometheus metrics counter timer")
5. Assess each operational dimension:
   - Health checks: Spring Actuator / health endpoints
   - Monitoring: metrics endpoints, Prometheus, Grafana integration
   - Logging: structured logging, log levels, frameworks
   - Configuration: externalized config, profiles, environment variables

IMPORTANT: Only report what RAG search confirms. Do not assume."""

ANALYZE_OPERATIONAL_READINESS_OUTPUT = """\
Valid JSON object with these exact keys:
{"health_checks": {"present": true|false, "framework": "Spring Actuator|Custom|None"},
 "monitoring": {"metrics": true|false, "framework": "Micrometer|Prometheus|None"},
 "logging": {"framework": "Logback|Log4j|SLF4J|Unknown", "structured": true|false},
 "configuration": {"externalized": true|false, "profiles": true|false},
 "deployment_readiness": "production-ready|needs-work|minimal",
 "recommendations": ["..."],
 "reasoning": "Evidence-based explanation"}"""


# --- SYNTHESIS TASK (4.0) ---

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

IMPORTANT: Never invent data. If a section is missing, use "NOT_ANALYZED"."""

SYNTHESIZE_ARCHITECTURE_OUTPUT = """\
Complete valid JSON matching the AnalyzedArchitecture schema. Must include:
executive_summary, overall_grade (A-F), all 16 analysis sections merged,
and top_recommendations list. Every section must be populated from
partial results or marked as "NOT_ANALYZED"."""


# =============================================================================
# MINI-CREW TASK DEFINITIONS
# Each tuple: (description, expected_output, output_pydantic, output_filename)
# =============================================================================

TECH_ANALYSIS_TASKS = [
    (ANALYZE_MACRO_ARCHITECTURE_DESC, ANALYZE_MACRO_ARCHITECTURE_OUTPUT,
     MacroArchitectureOutput, "01_macro_architecture.json"),
    (ANALYZE_BACKEND_PATTERN_DESC, ANALYZE_BACKEND_PATTERN_OUTPUT,
     BackendPatternOutput, "02_backend_pattern.json"),
    (ANALYZE_FRONTEND_PATTERN_DESC, ANALYZE_FRONTEND_PATTERN_OUTPUT,
     FrontendPatternOutput, "03_frontend_pattern.json"),
    (ANALYZE_ARCHITECTURE_QUALITY_DESC, ANALYZE_ARCHITECTURE_QUALITY_OUTPUT,
     ArchitectureQualityOutput, "04_architecture_quality.json"),
]

DOMAIN_ANALYSIS_TASKS = [
    (ANALYZE_DOMAIN_MODEL_DESC, ANALYZE_DOMAIN_MODEL_OUTPUT,
     DomainModelOutput, "05_domain_model.json"),
    (ANALYZE_BUSINESS_CAPABILITIES_DESC, ANALYZE_BUSINESS_CAPABILITIES_OUTPUT,
     BusinessCapabilitiesOutput, "06_business_capabilities.json"),
    (ANALYZE_BOUNDED_CONTEXTS_DESC, ANALYZE_BOUNDED_CONTEXTS_OUTPUT,
     BoundedContextsOutput, "07_bounded_contexts.json"),
    (ANALYZE_STATE_MACHINES_DESC, ANALYZE_STATE_MACHINES_OUTPUT,
     StateMachinesOutput, "08_state_machines.json"),
]

WORKFLOW_ANALYSIS_TASKS = [
    (ANALYZE_WORKFLOW_ENGINES_DESC, ANALYZE_WORKFLOW_ENGINES_OUTPUT,
     WorkflowEnginesOutput, "09_workflow_engines.json"),
    (ANALYZE_SAGA_PATTERNS_DESC, ANALYZE_SAGA_PATTERNS_OUTPUT,
     SagaPatternsOutput, "10_saga_patterns.json"),
    (ANALYZE_RUNTIME_SCENARIOS_DESC, ANALYZE_RUNTIME_SCENARIOS_OUTPUT,
     RuntimeScenariosOutput, "11_runtime_scenarios.json"),
    (ANALYZE_API_DESIGN_DESC, ANALYZE_API_DESIGN_OUTPUT,
     ApiDesignOutput, "12_api_design.json"),
]

QUALITY_ANALYSIS_TASKS = [
    (ANALYZE_COMPLEXITY_DESC, ANALYZE_COMPLEXITY_OUTPUT,
     ComplexityOutput, "13_complexity.json"),
    (ANALYZE_TECHNICAL_DEBT_DESC, ANALYZE_TECHNICAL_DEBT_OUTPUT,
     TechnicalDebtOutput, "14_technical_debt.json"),
    (ANALYZE_SECURITY_DESC, ANALYZE_SECURITY_OUTPUT,
     SecurityOutput, "15_security.json"),
    (ANALYZE_OPERATIONAL_READINESS_DESC, ANALYZE_OPERATIONAL_READINESS_OUTPUT,
     OperationalReadinessOutput, "16_operational_readiness.json"),
]

SYNTHESIS_TASKS = [
    (SYNTHESIZE_ARCHITECTURE_DESC, SYNTHESIZE_ARCHITECTURE_OUTPUT,
     AnalyzedArchitecture, "analyzed_architecture.json"),
]


# =============================================================================
# CREW CLASS
# =============================================================================

class ArchitectureAnalysisCrew:
    """
    Architecture Analysis Crew - Phase 2.

    Mini-Crew pattern: 5 independent crews with fresh LLM context each.
    - tech_analysis:    4 tasks (tech_architect)
    - domain_analysis:  4 tasks (func_analyst)
    - workflow_analysis: 4 tasks (func_analyst)
    - quality_analysis: 4 tasks (quality_analyst)
    - synthesis:        1 task  (synthesis_lead)
    """

    def __init__(
        self,
        facts_path: str = "knowledge/architecture/architecture_facts.json",
        chroma_dir: str = None,
        output_dir: str = "knowledge/architecture",
    ):
        """Initialize crew with paths."""
        self.facts_path = Path(facts_path)
        self.evidence_path = self.facts_path.parent / "evidence_map.json"
        self.chroma_dir = chroma_dir or os.getenv("CHROMA_DIR", ".cache/.chroma")
        self.output_dir = Path(output_dir)
        self._analysis_dir = self.output_dir / "analysis"
        self._checkpoint_file = self.output_dir / ".checkpoint_analysis.json"

        # MCP server path (resolved once)
        self._mcp_server_path = _MCP_SERVER_PATH

    # =========================================================================
    # LLM FACTORY
    # =========================================================================

    @staticmethod
    def _create_llm() -> LLM:
        """Create LLM instance from environment variables."""
        model = os.getenv("MODEL", "gpt-4o-mini")
        api_base = os.getenv("API_BASE", "")
        max_tokens = int(os.getenv("MAX_LLM_OUTPUT_TOKENS", "4000"))
        context_window = int(os.getenv("LLM_CONTEXT_WINDOW", "120000"))

        if max_tokens < 1:
            max_tokens = 4000

        llm = LLM(
            model=model,
            base_url=api_base,
            temperature=0.1,
            max_tokens=max_tokens,
            timeout=300,
        )
        # Set context window size directly (not via constructor kwargs,
        # which would pass it as additional_params to the API call)
        llm.context_window_size = context_window
        return llm

    # =========================================================================
    # AGENT FACTORY
    # =========================================================================

    def _create_agent(self, agent_key: str, tools: list) -> Agent:
        """Create a fresh agent with fresh LLM context."""
        config = AGENT_CONFIGS[agent_key]
        return Agent(
            role=config["role"],
            goal=config["goal"],
            backstory=config["backstory"],
            llm=self._create_llm(),
            tools=tools,
            mcps=[
                MCPServerStdio(
                    command="python",
                    args=[self._mcp_server_path],
                    cache_tools_list=True,
                )
            ],
            verbose=True,
            max_iter=25,
            max_retry_limit=3,
            allow_delegation=False,
            respect_context_window=True,
        )

    def _create_analysis_tools(self) -> list:
        """Create tools for analysis agents (tech, func, quality)."""
        return [
            FactsStatisticsTool(facts_path=str(self.facts_path)),
            FactsQueryTool(facts_path=str(self.facts_path)),
            RAGQueryTool(chroma_dir=self.chroma_dir),
            StereotypeListTool(facts_path=str(self.facts_path)),
        ]

    def _create_synthesis_tools(self) -> list:
        """Create tools for synthesis agent."""
        return [
            PartialResultsTool(analysis_dir=str(self._analysis_dir)),
            FileWriterTool(),
        ]

    # =========================================================================
    # MINI-CREW EXECUTION
    # =========================================================================

    def _build_tasks(
        self,
        task_defs: List[tuple],
        agent: Agent,
        output_dir: Path,
    ) -> List[Task]:
        """Build Task objects from task definitions."""
        tasks = []
        for desc, expected, pydantic_model, filename in task_defs:
            tasks.append(Task(
                description=desc,
                expected_output=expected,
                agent=agent,
                context=[],
                output_pydantic=pydantic_model,
                output_file=str(output_dir / filename),
                human_input=False,
            ))
        return tasks

    def _run_mini_crew(self, name: str, tasks: List[Task]) -> str:
        """Run a mini-crew with fresh context, retry on transient errors."""
        max_retries = int(os.getenv("CREW_MAX_RETRIES", "2"))
        logger.info(f"[Phase2] Starting Mini-Crew: {name} ({len(tasks)} tasks)")
        start_time = time.time()

        for attempt in range(1, max_retries + 1):
            tracker = None
            try:
                crew = Crew(
                    agents=[tasks[0].agent],
                    tasks=tasks,
                    process=Process.sequential,
                    verbose=True,
                    memory=False,
                    max_rpm=30,
                    planning=False,
                )
                tracker = install_guardrails()
                result = crew.kickoff()
                duration = time.time() - start_time
                logger.info(f"[Phase2] Completed Mini-Crew: {name} ({duration:.1f}s)")
                self._save_checkpoint(name)
                return str(result)

            except (ConnectionError, TimeoutError, OSError) as e:
                if attempt < max_retries:
                    delay = 5 * (2 ** (attempt - 1))
                    logger.warning(
                        f"[Phase2] {name}: Connection error "
                        f"(attempt {attempt}/{max_retries}), "
                        f"retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)
                    # Fresh agent for retry
                    new_agent = self._create_agent(
                        self._agent_key_for_crew(name),
                        self._create_analysis_tools(),
                    )
                    for t in tasks:
                        t.agent = new_agent
                    continue
                # Final attempt
                self._log_crew_failure(name, tasks, e, start_time)
                raise

            except Exception as e:
                self._log_crew_failure(name, tasks, e, start_time)
                raise

            finally:
                uninstall_guardrails(tracker)

        raise RuntimeError(f"Mini-crew {name} failed after {max_retries} attempts")

    def _agent_key_for_crew(self, crew_name: str) -> str:
        """Map mini-crew name to agent config key."""
        mapping = {
            "tech_analysis": "tech_architect",
            "domain_analysis": "func_analyst",
            "workflow_analysis": "func_analyst",
            "quality_analysis": "quality_analyst",
            "synthesis": "synthesis_lead",
        }
        return mapping.get(crew_name, "tech_architect")

    def _log_crew_failure(
        self, name: str, tasks: List[Task], error: Exception, start_time: float
    ) -> None:
        """Log failure metric and error details."""
        duration = time.time() - start_time
        error_type = type(error).__name__
        error_msg = str(error)[:500]
        logger.error(
            f"[Phase2] Failed Mini-Crew: {name} "
            f"({duration:.1f}s, {error_type}): {error_msg}"
        )
        try:
            from ...shared.utils.logger import log_metric
            log_metric(
                "mini_crew_failed",
                crew_type="Phase2",
                crew_name=name,
                duration_seconds=round(duration, 1),
                tasks=len(tasks),
                error_type=error_type,
                error=error_msg,
            )
        except Exception:
            pass  # Don't let metric logging break error handling

    # =========================================================================
    # CHECKPOINT
    # =========================================================================

    def _load_checkpoint(self) -> Set[str]:
        """Load completed mini-crew names from checkpoint."""
        if not self._checkpoint_file.exists():
            return set()
        try:
            data = json.loads(self._checkpoint_file.read_text(encoding="utf-8"))
            completed = set(data.get("completed_crews", []))
            if completed:
                logger.info(
                    f"[Phase2] Resuming: {len(completed)} mini-crews already completed: "
                    f"{sorted(completed)}"
                )
            return completed
        except Exception:
            return set()

    def _save_checkpoint(self, crew_name: str):
        """Save completed mini-crew to checkpoint."""
        completed = self._load_checkpoint()
        completed.add(crew_name)
        data = {"completed_crews": sorted(completed)}
        self._checkpoint_file.write_text(
            json.dumps(data, indent=2), encoding="utf-8"
        )
        logger.debug(f"[Phase2] Checkpoint saved: {crew_name}")

    # =========================================================================
    # PREREQUISITE VALIDATION + CLEANUP
    # =========================================================================

    def _prepare_clean_run(self, is_resume: bool = False):
        """Validate prerequisites and optionally clean old outputs."""
        import shutil
        from datetime import datetime

        logger.info("")
        logger.info("[Phase2] Preparing run...")

        # Step 1: Validate prerequisites
        logger.info("[Phase2] Step 1: Checking Phase 1 prerequisites...")

        missing_files = []

        if not self.facts_path.exists():
            missing_files.append(str(self.facts_path))
        else:
            try:
                with open(self.facts_path, 'r', encoding='utf-8') as f:
                    facts_data = json.load(f)
                if not isinstance(facts_data, dict) or "components" not in facts_data:
                    logger.error(f"   [INVALID] {self.facts_path}: missing 'components' key")
                    missing_files.append(f"{self.facts_path} (invalid JSON structure)")
                else:
                    comp_count = len(facts_data.get("components", []))
                    logger.info(f"   [OK] Found: {self.facts_path} ({comp_count} components)")
            except json.JSONDecodeError as e:
                logger.error(f"   [INVALID] {self.facts_path}: {e}")
                missing_files.append(f"{self.facts_path} (invalid JSON)")

        if not self.evidence_path.exists():
            missing_files.append(str(self.evidence_path))
        else:
            logger.info(f"   [OK] Found: {self.evidence_path}")

        if missing_files:
            logger.error("")
            logger.error("=" * 60)
            logger.error("[ERROR] PHASE 2 CANNOT START")
            logger.error("=" * 60)
            logger.error("")
            logger.error("Missing Phase 1 output files:")
            for f in missing_files:
                logger.error(f"   [MISSING] {f}")
            logger.error("")
            logger.error("[HINT] Solution: Run Phase 1 first:")
            logger.error("   python run.py --phases phase1_architecture_facts")
            logger.error("")
            logger.error("=" * 60)
            raise FileNotFoundError(
                f"Missing Phase 1 files: {', '.join(missing_files)}. "
                f"Run Phase 1 first: python run.py --phases phase1_architecture_facts"
            )

        logger.info("   [OK] All prerequisites satisfied!")

        # Step 2: Archive and clean old outputs (skip on resume)
        if not is_resume:
            logger.info("[Phase2] Step 2: Archive and clean old outputs...")

            output_files = [
                "analyzed_architecture.json",
                "analysis_technical.json",
                "analysis_functional.json",
                "analysis_quality.json",
                # Legacy names
                "temp_technical_analysis.json",
                "temp_functional_analysis.json",
                "temp_quality_analysis.json",
            ]

            existing_files = [f for f in output_files if (self.output_dir / f).exists()]

            if existing_files:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                archive_dir = self.output_dir / "archive" / f"run_{timestamp}"
                archive_dir.mkdir(parents=True, exist_ok=True)

                for filename in existing_files:
                    src = self.output_dir / filename
                    dst = archive_dir / filename
                    shutil.copy2(src, dst)
                    src.unlink()
                    logger.info(f"   [ARCHIVED+DELETED] {filename}")

                logger.info(f"   [OK] {len(existing_files)} old files archived to: {archive_dir}")
            else:
                logger.info("   [OK] No old outputs to clean (first run)")

            # Step 3: Clean partial analysis outputs
            logger.info("[Phase2] Step 3: Cleaning partial analysis outputs...")
            if self._analysis_dir.exists():
                for json_file in self._analysis_dir.glob("*.json"):
                    json_file.unlink()
                    logger.info(f"   [DELETED] {json_file.name}")
        else:
            logger.info("[Phase2] Resuming — skipping archive/clean")

        self._analysis_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"   [OK] Analysis directory ready: {self._analysis_dir}")
        logger.info("")

    def _format_json_outputs(self):
        """Format all JSON files with pretty-print."""
        logger.info("[Phase2] Formatting JSON outputs with pretty-print...")

        for json_file in self._analysis_dir.glob("*.json"):
            self._format_json_file(json_file)

        for json_file in self.output_dir.glob("*.json"):
            if json_file.name.startswith("."):
                continue
            self._format_json_file(json_file)

    @staticmethod
    def _format_json_file(json_file: Path) -> None:
        """Format a JSON file with pretty-print."""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"   [OK] Formatted: {json_file.name}")
        except Exception as e:
            logger.warning(f"   [WARN] Could not format {json_file.name}: {e}")

    # =========================================================================
    # MAIN EXECUTION
    # =========================================================================

    def run(self) -> str:
        """Execute all 5 mini-crews sequentially with checkpoint resume."""
        completed = self._load_checkpoint()
        is_resume = len(completed) > 0

        self._prepare_clean_run(is_resume=is_resume)

        # Mini-Crew 1: Technical Analysis (4 tasks)
        if "tech_analysis" not in completed:
            agent = self._create_agent("tech_architect", self._create_analysis_tools())
            tasks = self._build_tasks(TECH_ANALYSIS_TASKS, agent, self._analysis_dir)
            self._run_mini_crew("tech_analysis", tasks)

        # Mini-Crew 2: Domain Analysis (4 tasks)
        if "domain_analysis" not in completed:
            agent = self._create_agent("func_analyst", self._create_analysis_tools())
            tasks = self._build_tasks(DOMAIN_ANALYSIS_TASKS, agent, self._analysis_dir)
            self._run_mini_crew("domain_analysis", tasks)

        # Mini-Crew 3: Workflow Analysis (4 tasks)
        if "workflow_analysis" not in completed:
            agent = self._create_agent("func_analyst", self._create_analysis_tools())
            tasks = self._build_tasks(WORKFLOW_ANALYSIS_TASKS, agent, self._analysis_dir)
            self._run_mini_crew("workflow_analysis", tasks)

        # Mini-Crew 4: Quality Analysis (4 tasks)
        if "quality_analysis" not in completed:
            agent = self._create_agent("quality_analyst", self._create_analysis_tools())
            tasks = self._build_tasks(QUALITY_ANALYSIS_TASKS, agent, self._analysis_dir)
            self._run_mini_crew("quality_analysis", tasks)

        # Mini-Crew 5: Synthesis (1 task)
        if "synthesis" not in completed:
            agent = self._create_agent("synthesis_lead", self._create_synthesis_tools())
            tasks = self._build_tasks(SYNTHESIS_TASKS, agent, self.output_dir)
            self._run_mini_crew("synthesis", tasks)

        # Post-processing
        self._format_json_outputs()

        logger.info("")
        logger.info("=" * 60)
        logger.info("PHASE 2 COMPLETE: Architecture Analysis finished")
        logger.info("=" * 60)
        logger.info(f"Output: {self.output_dir / 'analyzed_architecture.json'}")

        return str(self.output_dir / "analyzed_architecture.json")

    def kickoff(self, inputs: Dict[str, Any] = None) -> str:
        """Execute crew - compatible with orchestrator interface."""
        return self.run()
