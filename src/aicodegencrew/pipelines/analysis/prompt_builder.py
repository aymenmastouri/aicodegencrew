"""AnalysisPromptBuilder — constructs LLM prompts for analysis sections and synthesis.

Uses task descriptions from tasks.py as the basis for each section prompt.
Output schema comes from the Pydantic models in task_output_schemas.py.
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Maximum characters for data sections to avoid context overflow
_MAX_DATA_CHARS = 30000
_MAX_RAG_CHARS = 12000


def _truncate(text: str, max_chars: int) -> str:
    """Truncate text with indicator."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... [truncated]"


def _fmt_json(data: Any, max_chars: int = _MAX_DATA_CHARS) -> str:
    """Serialise *data* as indented JSON, truncated to *max_chars*."""
    try:
        serialised = json.dumps(data, indent=2, ensure_ascii=False, default=str)
    except Exception:
        serialised = str(data)
    return _truncate(serialised, max_chars)


def _fmt_rag_results(results: list[dict], label: str) -> str:
    """Format a list of RAG result dicts as readable text."""
    if not results:
        return f"No results for: {label}"
    lines = [f"### RAG: {label}"]
    for r in results[:5]:
        fp = r.get("file_path", "unknown")
        score = r.get("relevance_score", 0)
        content = r.get("content", "")[:400]
        lines.append(f"**{fp}** (score: {score})\n```\n{content}\n```")
    return "\n".join(lines)


def _fmt_section_data(data: dict) -> str:
    """Convert the section data dict into a human-readable prompt block."""
    parts: list[str] = []
    for key, value in data.items():
        if not value:
            continue
        label = key.replace("_", " ").title()
        if key.startswith("rag_"):
            # value is a list[dict] of RAG results
            parts.append(_fmt_rag_results(value, label))
        elif isinstance(value, (dict, list)):
            serialised = _fmt_json(value)
            parts.append(f"### {label}\n```json\n{serialised}\n```")
        else:
            parts.append(f"### {label}\n{value}")
    raw = "\n\n".join(parts)
    return _truncate(raw, _MAX_DATA_CHARS + _MAX_RAG_CHARS)


# =============================================================================
# SECTION METADATA
# =============================================================================

SECTION_META: dict[str, dict[str, str]] = {
    "01": {
        "title": "Macro Architecture Analysis",
        "output_file": "01_macro_architecture.json",
        "schema_key": "MacroArchitectureOutput",
        "description": (
            "Analyze the MACRO ARCHITECTURE style of the system.\n\n"
            "STEPS:\n"
            "1. Examine the statistics (component/container counts)\n"
            "2. Review all containers and their types\n"
            "3. Determine architecture style based on evidence:\n"
            "   - 1 container = Monolith\n"
            "   - 1 container + clear module boundaries = Modular Monolith\n"
            "   - Multiple containers with REST APIs between them = Microservices\n"
            "   - Mix = Hybrid\n"
            "4. Identify deployment model and communication patterns\n\n"
            "Base your analysis only on the provided facts."
        ),
        "output_schema": """{
  "style": "Monolith|Modular Monolith|Microservices|Hybrid",
  "container_count": <number>,
  "containers": [{"name": "...", "type": "..."}],
  "reasoning": "Evidence-based explanation",
  "scalability_approach": "vertical|horizontal",
  "deployment_model": "single|distributed",
  "communication_pattern": "sync REST|async messaging|mixed"
}""",
    },
    "02": {
        "title": "Backend Pattern Analysis",
        "output_file": "02_backend_pattern.json",
        "schema_key": "BackendPatternOutput",
        "description": (
            "Analyze the BACKEND architectural pattern.\n\n"
            "STEPS:\n"
            "1. Check the statistics breakdown for controller/service/repository counts\n"
            "2. Review the component lists for each stereotype\n"
            "3. Analyze layer distribution to determine pattern:\n"
            "   - Layered: clear controller → service → repository separation\n"
            "   - Hexagonal: ports/adapters naming convention, domain isolation\n"
            "   - Clean Architecture: use cases, entities, interfaces directories\n"
            "   - CQRS: separate command/query handlers\n\n"
            "Use actual component counts from the provided data."
        ),
        "output_schema": """{
  "primary_pattern": "Layered|Hexagonal|Clean Architecture|CQRS|Unknown",
  "layer_structure": ["Controller", "Service", "Repository"],
  "component_counts": {"controller": <n>, "service": <n>, "repository": <n>},
  "technology": {"framework": "<detected framework>", "language": "<detected language>"},
  "layer_violations": <number>,
  "reasoning": "Evidence-based explanation"
}""",
    },
    "03": {
        "title": "Frontend Pattern Analysis",
        "output_file": "03_frontend_pattern.json",
        "schema_key": "FrontendPatternOutput",
        "description": (
            "Analyze the FRONTEND architectural pattern.\n\n"
            "STEPS:\n"
            "1. Check containers for frontend container(s)\n"
            "2. Review component and module lists\n"
            "3. Check container metadata for framework (Angular, React, Vue)\n"
            "4. Determine pattern:\n"
            "   - Component-Based SPA: Angular/React/Vue with components + modules\n"
            "   - Micro-Frontends: multiple independent frontend applications\n"
            "   - Server-Rendered: minimal JavaScript, server-side templates\n"
            "   - No Frontend: backend-only system\n\n"
            "If no frontend container exists, report 'No Frontend'."
        ),
        "output_schema": """{
  "primary_pattern": "Component-Based SPA|Micro-Frontends|Server-Rendered|No Frontend",
  "framework": "Angular|React|Vue|None",
  "module_structure": "feature-based|flat|layered",
  "state_management": "NgRx|Redux|Vuex|None|Unknown",
  "routing_strategy": "lazy-loaded|eager|Unknown",
  "component_count": <number>,
  "reasoning": "Evidence-based explanation"
}""",
    },
    "04": {
        "title": "Architecture Quality Assessment",
        "output_file": "04_architecture_quality.json",
        "schema_key": "ArchitectureQualityOutput",
        "description": (
            "Assess ARCHITECTURE QUALITY metrics.\n\n"
            "STEPS:\n"
            "1. Use the statistics to get total components, relations, interfaces\n"
            "2. Calculate: relations_per_component = total_relations / total_components\n"
            "3. Check for layer violations (controller directly calling repository)\n"
            "4. Look for circular dependencies (A→B→C→A)\n"
            "5. Assess coupling:\n"
            "   - ratio < 1.0 = loose coupling\n"
            "   - ratio 1.0-3.0 = moderate coupling\n"
            "   - ratio > 3.0 = tight coupling\n\n"
            "Use actual numbers from the statistics."
        ),
        "output_schema": """{
  "separation_of_concerns": "good|moderate|poor",
  "layer_violations_count": <number>,
  "coupling_assessment": "loose|moderate|tight",
  "relations_per_component": <float>,
  "circular_dependencies": <number>,
  "overall_grade": "A|B|C|D|F",
  "reasoning": "Evidence-based explanation with actual numbers"
}""",
    },
    "05": {
        "title": "Domain Model Analysis",
        "output_file": "05_domain_model.json",
        "schema_key": "DomainModelOutput",
        "description": (
            "Analyze the DOMAIN MODEL of the system.\n\n"
            "STEPS:\n"
            "1. Count total entities from the statistics\n"
            "2. Review the entity list\n"
            "3. Group entities by naming prefix (e.g., Order*, User*, Document*)\n"
            "4. Each prefix group = one domain area\n"
            "5. Identify core domains (most entities) vs supporting domains (few entities)\n"
            "6. Assess naming consistency\n\n"
            "List ALL entity names from the data. Group by actual naming patterns."
        ),
        "output_schema": """{
  "total_entities": <number>,
  "domain_areas": [{"name": "...", "entities": ["Entity1", "Entity2"], "type": "core|supporting"}],
  "domain_complexity": "simple|moderate|complex",
  "naming_consistency": "consistent|mixed|inconsistent",
  "reasoning": "Evidence-based explanation listing actual entity names"
}""",
    },
    "06": {
        "title": "Business Capabilities Analysis",
        "output_file": "06_business_capabilities.json",
        "schema_key": "BusinessCapabilitiesOutput",
        "description": (
            "Identify BUSINESS CAPABILITIES from services.\n\n"
            "STEPS:\n"
            "1. Review all services in the provided list\n"
            "2. Group services by naming prefix (e.g., OrderService, OrderValidationService → 'Order Management')\n"
            "3. Each prefix group = one business capability\n"
            "4. Assess capability maturity (number of services per capability)\n"
            "5. Identify gaps (entities without corresponding services)\n\n"
            "EXAMPLE GROUPING:\n"
            "- OrderService, OrderValidationService, OrderMapper → 'Order Management'\n"
            "- UserService, AuthService, LoginService → 'User & Authentication'"
        ),
        "output_schema": """{
  "capabilities": [{"name": "...", "services": ["Service1", "Service2"],
                    "description": "...", "maturity": "basic|intermediate|mature"}],
  "total_services": <number>,
  "capability_coverage": "comprehensive|partial|minimal",
  "reasoning": "Evidence-based explanation"
}""",
    },
    "07": {
        "title": "Bounded Contexts Analysis",
        "output_file": "07_bounded_contexts.json",
        "schema_key": "BoundedContextsOutput",
        "description": (
            "Identify BOUNDED CONTEXTS (DDD perspective).\n\n"
            "STEPS:\n"
            "1. Use the statistics to understand overall scale\n"
            "2. Review entities and services with same naming prefix = one bounded context\n"
            "3. Cross-reference relations to find cross-context dependencies\n"
            "4. Assess coupling between contexts\n\n"
            "CONTEXT DETECTION: Components sharing a naming prefix belong to the same context."
        ),
        "output_schema": """{
  "contexts_identified": <number>,
  "contexts": [{"name": "...", "entities": ["..."], "services": ["..."],
                "component_count": <n>}],
  "cross_context_coupling": "low|moderate|high",
  "recommendations": ["..."],
  "reasoning": "Evidence-based explanation"
}""",
    },
    "08": {
        "title": "State Machines Detection",
        "output_file": "08_state_machines.json",
        "schema_key": "StateMachinesOutput",
        "description": (
            "Detect STATE MACHINES in the codebase (framework-agnostic).\n\n"
            "STEPS:\n"
            "1. Review the RAG results for state machine patterns\n"
            "2. Review the entity list for status/state fields in names\n\n"
            "INDICATORS (examples across languages):\n"
            "- Enum types with state values (PENDING, APPROVED, REJECTED, ACTIVE, INACTIVE)\n"
            "- Classes/modules with 'State' or 'Status' in name\n"
            "- Transition methods (approve(), reject(), activate(), transition_to())\n"
            "- State machine libraries (Spring State Machine, python-statemachine, Stateless, xstate)\n\n"
            "If not found, report detected=false."
        ),
        "output_schema": """{
  "detected": true|false,
  "implementation_type": "Library-based|Enum-based|Custom|None",
  "stateful_entities": ["EntityName"],
  "state_transitions": [{"entity": "...", "states": ["STATE1", "STATE2"]}],
  "reasoning": "Evidence-based explanation"
}""",
    },
    "09": {
        "title": "Workflow Engines Detection",
        "output_file": "09_workflow_engines.json",
        "schema_key": "WorkflowEnginesOutput",
        "description": (
            "Detect WORKFLOW / PROCESS ENGINES (framework-agnostic).\n\n"
            "STEPS:\n"
            "1. Review the RAG results for workflow engine patterns\n"
            "2. Check for workflow-related components or configurations\n\n"
            "INDICATORS (examples across languages):\n"
            "- Java/Spring: Camunda, Flowable, Activiti dependencies; .bpmn files; ProcessEngine beans\n"
            "- Python: Celery task chains, Airflow DAGs, Prefect flows\n"
            "- .NET: Workflow Foundation, Elsa Workflows\n"
            "- Go/Node: Temporal workers, Bull queues\n"
            "- General: State machine libraries, pipeline/step patterns\n\n"
            "If not found, report engine='None'."
        ),
        "output_schema": """{
  "engine": "<detected engine name or None>",
  "version": "...|Unknown",
  "bpmn_processes": ["process_name"],
  "integration_style": "embedded|standalone|library|None",
  "workflow_services": ["ServiceName"],
  "reasoning": "Evidence-based explanation"
}""",
    },
    "10": {
        "title": "Saga Patterns Detection",
        "output_file": "10_saga_patterns.json",
        "schema_key": "SagaPatternsOutput",
        "description": (
            "Detect SAGA patterns for distributed transactions.\n\n"
            "STEPS:\n"
            "1. Review the RAG results for saga and outbox patterns\n"
            "2. Look for saga orchestrator or choreography patterns\n\n"
            "INDICATORS:\n"
            "- Saga orchestrator classes\n"
            "- Compensation/rollback methods\n"
            "- Outbox tables or event sourcing\n"
            "- @SagaEventHandler annotations\n\n"
            "If not found, report detected=false."
        ),
        "output_schema": """{
  "detected": true|false,
  "style": "orchestration|choreography|None",
  "sagas": ["SagaName"],
  "outbox_pattern": true|false,
  "event_store": true|false,
  "reasoning": "Evidence-based explanation"
}""",
    },
    "11": {
        "title": "Runtime Scenarios Analysis",
        "output_file": "11_runtime_scenarios.json",
        "schema_key": "RuntimeScenariosOutput",
        "description": (
            "Identify key RUNTIME SCENARIOS for Arc42 Section 6.\n\n"
            "STEPS:\n"
            "1. Review the controller list\n"
            "2. Review the interfaces/endpoints list\n"
            "3. For the top 3-5 most important endpoints, trace the call flow:\n"
            "   controller → service → repository → entity\n"
            "4. Document each scenario with trigger, steps, and end state\n\n"
            "SCENARIO FORMAT:\n"
            "- Name: descriptive name (e.g., 'Create Order')\n"
            "- Trigger: HTTP POST /api/orders\n"
            "- Steps: OrderController → OrderService → OrderRepository\n"
            "- End state: Order persisted, 201 Created returned"
        ),
        "output_schema": """{
  "scenarios": [{"name": "...", "trigger": "HTTP METHOD /path",
                 "steps": ["Component1", "Component2", "Component3"],
                 "end_state": "..."}],
  "total_endpoints": <number>,
  "orchestration_style": "synchronous|asynchronous|mixed",
  "reasoning": "Evidence-based explanation"
}""",
    },
    "12": {
        "title": "API Design Quality Assessment",
        "output_file": "12_api_design.json",
        "schema_key": "ApiDesignOutput",
        "description": (
            "Assess API DESIGN QUALITY.\n\n"
            "STEPS:\n"
            "1. Check the statistics for interface counts\n"
            "2. Review the interfaces/endpoints list\n"
            "3. Analyze HTTP verb distribution (GET, POST, PUT, DELETE, PATCH)\n"
            "4. Check URL patterns for versioning (/v1/, /api/v2/)\n"
            "5. Assess naming consistency across controllers\n"
            "6. Check for RESTful resource naming\n\n"
            "METRICS:\n"
            "- RESTfulness: proper verb usage with resource URLs\n"
            "- Consistency: same URL patterns across all controllers\n"
            "- Versioning: presence of API version in URLs\n"
            "- Completeness: CRUD coverage per resource"
        ),
        "output_schema": """{
  "total_endpoints": <number>,
  "verb_distribution": {"GET": <n>, "POST": <n>, "PUT": <n>, "DELETE": <n>},
  "restfulness": "good|moderate|poor",
  "consistency": "consistent|mixed|inconsistent",
  "versioning_strategy": "URL-based|header-based|none",
  "naming_quality": "good|moderate|poor",
  "recommendations": ["..."],
  "reasoning": "Evidence-based explanation with actual endpoint examples"
}""",
    },
    "13": {
        "title": "Structural Complexity Assessment",
        "output_file": "13_complexity.json",
        "schema_key": "ComplexityOutput",
        "description": (
            "Assess STRUCTURAL and COGNITIVE COMPLEXITY.\n\n"
            "STEPS:\n"
            "1. Use the statistics to get total counts\n"
            "2. Calculate: relations_per_component = total_relations / total_components\n"
            "3. Identify complexity hotspots (components with most relations)\n"
            "4. Classify scale:\n"
            "   - < 500 components: Low complexity\n"
            "   - 500-5000: Medium complexity\n"
            "   - 5000+: High/Enterprise complexity\n\n"
            "Use actual numbers from the statistics."
        ),
        "output_schema": """{
  "total_components": <number>,
  "total_relations": <number>,
  "total_interfaces": <number>,
  "relations_per_component": <float>,
  "structural_complexity": "low|medium|high",
  "scale": "small|medium|large|enterprise",
  "hotspots": [{"component": "...", "relation_count": <n>}],
  "reasoning": "Evidence-based explanation with actual numbers"
}""",
    },
    "14": {
        "title": "Technical Debt Assessment",
        "output_file": "14_technical_debt.json",
        "schema_key": "TechnicalDebtOutput",
        "description": (
            "Assess TECHNICAL DEBT level.\n\n"
            "STEPS:\n"
            "1. Review the RAG results for TODO/FIXME/HACK markers\n"
            "2. Review the RAG results for deprecated patterns\n"
            "3. Categorize debt indicators found:\n"
            "   - Code debt: TODO/FIXME markers\n"
            "   - Design debt: deprecated patterns still in use\n"
            "   - Test debt: missing test coverage indicators\n\n"
            "Report only what the RAG search finds."
        ),
        "output_schema": """{
  "debt_level": "low|moderate|high|critical",
  "indicators_found": <number>,
  "categories": {"code_debt": <n>, "design_debt": <n>, "test_debt": <n>},
  "top_items": [{"type": "TODO|FIXME|deprecated", "location": "file/class", "description": "..."}],
  "estimated_effort": "days|weeks|months",
  "reasoning": "Evidence-based explanation with actual findings"
}""",
    },
    "15": {
        "title": "Security Posture Assessment",
        "output_file": "15_security.json",
        "schema_key": "SecurityOutput",
        "description": (
            "Assess SECURITY POSTURE (framework-agnostic).\n\n"
            "STEPS:\n"
            "1. Review the RAG results for security config / authentication patterns\n"
            "2. Review the RAG results for JWT/OAuth2 token usage\n"
            "3. Review the RAG results for authorization/permission/role patterns\n"
            "4. Review the RAG results for CSRF/XSS/input validation patterns\n"
            "5. Assess each security dimension:\n"
            "   - Authentication: mechanism used (JWT, OAuth2, Basic, Session, API keys)\n"
            "   - Authorization: framework-level or manual\n"
            "   - Input validation: annotation-based, decorator-based, or manual\n"
            "   - Audit logging: present or absent\n\n"
            "Report only security patterns found in the RAG results."
        ),
        "output_schema": """{
  "authentication": {"mechanism": "JWT|OAuth2|Basic|Session|Unknown", "configured": true|false},
  "authorization": {"framework": "<detected framework or None>", "method_level": true|false},
  "input_validation": "annotation-based|decorator-based|middleware|manual|none|unknown",
  "audit_logging": true|false,
  "security_framework": "<detected framework or None|Unknown>",
  "overall_posture": "strong|moderate|weak|unknown",
  "concerns": ["..."],
  "recommendations": ["..."],
  "reasoning": "Evidence-based explanation"
}""",
    },
    "16": {
        "title": "Operational Readiness Assessment",
        "output_file": "16_operational_readiness.json",
        "schema_key": "OperationalReadinessOutput",
        "description": (
            "Assess OPERATIONAL READINESS (framework-agnostic).\n\n"
            "STEPS:\n"
            "1. Review the RAG results for health check / liveness / readiness patterns\n"
            "2. Review the RAG results for structured logging patterns\n"
            "3. Review the RAG results for metrics / prometheus / monitoring patterns\n"
            "4. Review the RAG results for externalized configuration / environment profiles\n"
            "5. Assess each operational dimension:\n"
            "   - Health checks: any framework, Kubernetes probes\n"
            "   - Monitoring: metrics endpoints, OpenTelemetry\n"
            "   - Logging: structured logging, SLF4J/Logback, structlog, Serilog\n"
            "   - Configuration: environment variables, profiles\n\n"
            "Report only what the RAG results confirm."
        ),
        "output_schema": """{
  "health_checks": {"present": true|false, "framework": "<detected framework or None>"},
  "monitoring": {"metrics": true|false, "framework": "<detected framework or None>"},
  "logging": {"framework": "<detected framework or Unknown>", "structured": true|false},
  "configuration": {"externalized": true|false, "profiles": true|false},
  "deployment_readiness": "production-ready|needs-work|minimal",
  "recommendations": ["..."],
  "reasoning": "Evidence-based explanation"
}""",
    },
}

# System prompt used for all section calls
_SECTION_SYSTEM = (
    "You are a senior software architect with deep expertise in enterprise architecture patterns. "
    "Analyze the provided architecture facts and output ONLY valid JSON matching the exact schema. "
    "Never invent component names or patterns not present in the data. "
    "If evidence for a feature is absent, reflect that honestly in the output (e.g., detected=false, "
    "mechanism='Unknown')."
)

# System prompt used for the synthesis call
_SYNTHESIS_SYSTEM = (
    "You are a lead architect synthesizing 16 specialized analyses into the final architecture "
    "document. Merge all sections faithfully — never invent data. Resolve conflicts by taking the "
    "more specific or detailed value. Populate every field from the partial results; mark sections "
    "as 'NOT_ANALYZED' only when the corresponding partial result is genuinely absent."
)


class AnalysisPromptBuilder:
    """Builds chat-format messages for analysis sections and synthesis."""

    def build_section(self, section_id: str, data: dict) -> list[dict]:
        """Build [system, user] messages for one analysis section.

        Args:
            section_id: Two-digit section number e.g. "01".
            data: Collected data dict from AnalysisDataCollector.collect_section_data().

        Returns:
            List of two message dicts: [{"role": "system", ...}, {"role": "user", ...}]
        """
        meta = SECTION_META.get(section_id)
        if meta is None:
            raise ValueError(f"Unknown section_id: {section_id!r}")

        data_text = _fmt_section_data(data)

        user_content = (
            f"## Task: {meta['title']}\n\n"
            f"## Output Schema\n```json\n{meta['output_schema']}\n```\n\n"
            f"## Architecture Facts\n{data_text}\n\n"
            f"## Analysis Instructions\n{meta['description']}\n\n"
            "Output ONLY valid JSON. No markdown fences. No explanatory text."
        )

        return [
            {"role": "system", "content": _SECTION_SYSTEM},
            {"role": "user", "content": user_content},
        ]

    def build_synthesis(self, sections: dict[str, str]) -> list[dict]:
        """Build [system, user] messages for the final synthesis call.

        Args:
            sections: Mapping from output filename to JSON content string,
                      e.g. {"01_macro_architecture.json": "{...}", ...}.

        Returns:
            List of two message dicts.
        """
        from ...shared.models.task_output_schemas import AnalyzedArchitecture

        schema = json.dumps(
            AnalyzedArchitecture.model_json_schema(),
            indent=2,
            ensure_ascii=False,
        )

        # Format partial results — each section on its own block
        partial_parts: list[str] = []
        for filename, content in sorted(sections.items()):
            partial_parts.append(f"### {filename}\n```json\n{_truncate(content, 4000)}\n```")
        partial_text = "\n\n".join(partial_parts)

        synthesis_rules = (
            "## Synthesis Rules\n"
            "1. Populate EVERY field in the AnalyzedArchitecture schema from the partial results above.\n"
            "2. Cross-validate numbers: component counts should be consistent across sections.\n"
            "3. Resolve conflicts by taking the more specific or detailed value.\n"
            "4. Calculate overall_grade (A–F):\n"
            "   - A: Well-structured, low debt, good security, production-ready\n"
            "   - B: Good structure, moderate debt, some improvements needed\n"
            "   - C: Acceptable but significant improvements needed\n"
            "   - D: Poor structure, high debt, major concerns\n"
            "   - F: Critical issues, needs immediate attention\n"
            "5. Write executive_summary (2–3 sentences).\n"
            "6. List top_recommendations (top 5 items).\n"
            "7. If a section is absent in partial results, mark it 'NOT_ANALYZED'.\n\n"
            "Output ONLY valid JSON matching the schema. No markdown fences. No explanatory text."
        )

        user_content = (
            "## Task: Synthesize Architecture Analysis\n\n"
            f"## Output Schema\n```json\n{_truncate(schema, 8000)}\n```\n\n"
            f"## Partial Results\n{partial_text}\n\n"
            f"{synthesis_rules}"
        )

        return [
            {"role": "system", "content": _SYNTHESIS_SYSTEM},
            {"role": "user", "content": user_content},
        ]
