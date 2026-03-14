"""Data Recipes — defines exactly what data each chapter needs.

Each recipe specifies:
- facts: list of (category, params) tuples for query_facts
- rag_queries: list of search queries for rag_query
- components: list of stereotypes for list_components_by_stereotype
- sections: expected markdown sections in output
- min_length / max_length: character bounds for validation
"""

from dataclasses import dataclass, field


@dataclass
class ChapterRecipe:
    """Data requirements for one chapter."""

    id: str
    title: str
    output_file: str
    facts: list[tuple[str, dict]] = field(default_factory=list)
    rag_queries: list[str] = field(default_factory=list)
    components: list[str] = field(default_factory=list)
    sections: list[str] = field(default_factory=list)
    min_length: int = 2000
    max_length: int = 25000
    use_fast_model: bool = False
    merge_into: str | None = None
    diagram_file: str | None = None  # DrawIO diagram to generate
    context_hint: str = ""  # Chapter-specific guidance for the LLM


# =============================================================================
# ARC42 RECIPES
# =============================================================================

ARC42_RECIPES: list[ChapterRecipe] = [
    ChapterRecipe(
        id="arc42-ch01",
        title="Introduction and Goals",
        output_file="arc42/01-introduction.md",
        facts=[("all", {}), ("containers", {}), ("interfaces", {})],
        components=["controller", "service"],
        rag_queries=["quality goals non-functional requirements", "business domain terminology purpose"],
        sections=["## 1.1 Requirements Overview", "## 1.2 Quality Goals", "## 1.3 Stakeholders"],
        use_fast_model=True,
        context_hint="Focus on the business purpose of the system, key quality attributes, and who uses it. "
        "Derive stakeholders from the architecture (API consumers, DB admins, end users).",
    ),
    ChapterRecipe(
        id="arc42-ch02",
        title="Architecture Constraints",
        output_file="arc42/02-constraints.md",
        facts=[("all", {}), ("containers", {})],
        rag_queries=["naming convention package structure configuration", "Oracle datasource database connection jdbc"],
        sections=["## 2.1 Technical Constraints", "## 2.2 Organizational Constraints", "## 2.3 Convention Constraints"],
        use_fast_model=True,
        context_hint="Derive constraints from the technology stack, naming conventions, and architecture patterns visible in the code.",
    ),
    ChapterRecipe(
        id="arc42-ch03",
        title="System Scope and Context",
        output_file="arc42/03-context.md",
        facts=[("containers", {}), ("interfaces", {}), ("relations", {})],
        rag_queries=["external system integration API client", "authentication authorization SSO"],
        sections=["## 3.1 Business Context", "## 3.2 Technical Context"],
        context_hint="Identify all external actors (users, external systems, databases) and how they interact with the system. "
        "Create a context table with: Actor | Channel | Data exchanged.",
    ),
    ChapterRecipe(
        id="arc42-ch04",
        title="Solution Strategy",
        output_file="arc42/04-solution-strategy.md",
        facts=[("all", {}), ("containers", {})],
        components=["configuration"],
        rag_queries=["architecture pattern repository service framework"],
        sections=["## 4.1 Technology Decisions", "## 4.2 Architecture Patterns", "## 4.3 Achieving Quality Goals"],
        context_hint="Explain WHY these technologies and patterns were chosen. Connect each technology decision to a quality goal.",
    ),
    # Chapter 5: Building Blocks (4 parts → merged)
    ChapterRecipe(
        id="arc42-ch05-p1",
        title="Building Block View — Overview",
        output_file="arc42/05-part1-overview.md",
        facts=[("all", {}), ("containers", {})],
        components=["controller", "service", "repository"],
        sections=["## 5.1 Overview", "## 5.2 Whitebox Overall System"],
        merge_into="arc42/05-building-blocks.md",
        context_hint="Show the layered architecture as a whitebox. Include component counts per layer.",
    ),
    ChapterRecipe(
        id="arc42-ch05-p2a",
        title="Building Block View — Controller Layer",
        output_file="arc42/05-part2a-controllers.md",
        facts=[("interfaces", {})],
        components=["controller"],
        rag_queries=["REST controller patterns RequestMapping validation security"],
        sections=["## 5.3 Presentation Layer", "### 5.3.1 Layer Overview", "### 5.3.2 Key Controllers"],
        merge_into="arc42/05-building-blocks.md",
        context_hint="Deep-dive the top 5 most important controllers. Show their endpoints, HTTP methods, and responsibilities.",
    ),
    ChapterRecipe(
        id="arc42-ch05-p2b",
        title="Building Block View — Controller Inventory",
        output_file="arc42/05-part2b-inventory.md",
        facts=[("all", {}), ("interfaces", {})],
        components=["controller"],
        sections=["### 5.3.3 Controller Inventory"],
        min_length=1000,
        merge_into="arc42/05-building-blocks.md",
        context_hint="Create a table with ALL controllers: Name | Endpoints | HTTP Methods | Description.",
    ),
    ChapterRecipe(
        id="arc42-ch05-p3",
        title="Building Block View — Service Layer",
        output_file="arc42/05-part3-services.md",
        facts=[("containers", {}), ("relations", {})],
        components=["service"],
        rag_queries=["service implementation transaction"],
        sections=["## 5.4 Business Layer", "### 5.4.1 Layer Overview", "### 5.4.2 Service Inventory"],
        merge_into="arc42/05-building-blocks.md",
        context_hint="Deep-dive top 5 services. Show their dependencies, transaction patterns, and business responsibilities.",
    ),
    ChapterRecipe(
        id="arc42-ch05-p4",
        title="Building Block View — Domain and Persistence",
        output_file="arc42/05-part4-domain.md",
        facts=[("relations", {})],
        components=["entity", "repository"],
        rag_queries=["Oracle datasource database connection spring"],
        sections=["## 5.5 Domain Layer", "## 5.6 Persistence Layer", "## 5.7 Component Dependencies"],
        merge_into="arc42/05-building-blocks.md",
        context_hint="Show entity relationships, repository patterns, and the database technology stack.",
    ),
    # Chapter 6: Runtime View (2 parts → merged)
    ChapterRecipe(
        id="arc42-ch06-p1",
        title="Runtime View — API Flows",
        output_file="arc42/06-part1-api-flows.md",
        facts=[("interfaces", {}), ("containers", {}), ("relations", {})],
        components=["controller"],
        rag_queries=["request flow authentication security"],
        sections=["## 6.1 Runtime View Overview", "## 6.2 Authentication Flow", "## 6.3 CRUD Operation Flows"],
        merge_into="arc42/06-runtime-view.md",
        context_hint="Use Mermaid sequence diagrams to show the request lifecycle: Client → Controller → Service → Repository → DB.",
    ),
    ChapterRecipe(
        id="arc42-ch06-p2",
        title="Runtime View — Business Flows",
        output_file="arc42/06-part2-business-flows.md",
        facts=[("containers", {}), ("relations", {})],
        components=["service"],
        rag_queries=["workflow state transition scheduled task batch", "exception error handling recovery"],
        sections=["## 6.4 Core Business Workflows", "## 6.5 Error and Recovery Scenarios"],
        merge_into="arc42/06-runtime-view.md",
        context_hint="Show complex business processes as Mermaid sequence or flowchart diagrams. Include error paths.",
    ),
    ChapterRecipe(
        id="arc42-ch07",
        title="Deployment View",
        output_file="arc42/07-deployment.md",
        facts=[("all", {}), ("containers", {})],
        rag_queries=["docker dockerfile kubernetes deployment", "application properties profile environment"],
        sections=["## 7.1 Infrastructure Overview", "## 7.2 Infrastructure Nodes", "## 7.3 Container Deployment"],
        context_hint="Derive deployment topology from Docker/K8s configs and application properties found in the code.",
    ),
    # Chapter 8: Crosscutting Concepts (3 parts → merged)
    ChapterRecipe(
        id="arc42-ch08-p1a",
        title="Crosscutting Concepts — Domain and Security",
        output_file="arc42/08-part1a-domain-security.md",
        facts=[],
        components=["entity"],
        rag_queries=["security authentication authorization JWT", "@Entity JPA domain model"],
        sections=["## 8.1 Domain Model", "## 8.2 Security Concept"],
        merge_into="arc42/08-crosscutting.md",
        context_hint="Show the domain model as a Mermaid class diagram. Explain the security architecture: AuthN, AuthZ, token handling.",
    ),
    ChapterRecipe(
        id="arc42-ch08-p1b",
        title="Crosscutting Concepts — Persistence and Operations",
        output_file="arc42/08-part1b-persistence-ops.md",
        facts=[],
        components=["repository"],
        rag_queries=["Transactional JPA persistence", "ControllerAdvice exception error handling", "slf4j logback logging"],
        sections=["## 8.3 Persistence", "## 8.4 Error Handling", "## 8.5 Logging"],
        merge_into="arc42/08-crosscutting.md",
        context_hint="Show persistence patterns (JPA, transactions), error handling strategy (@ControllerAdvice), and logging setup.",
    ),
    ChapterRecipe(
        id="arc42-ch08-p2",
        title="Crosscutting Concepts — Patterns and Conventions",
        output_file="arc42/08-part2-patterns.md",
        facts=[("all", {}), ("containers", {})],
        rag_queries=[
            "configuration properties profile cache",
            "validation Bean JSR dependency injection",
            "test junit mockito SpringBootTest",
        ],
        sections=["## 8.6 Dependency Injection", "## 8.7 Validation", "## 8.8 Testing Concept"],
        merge_into="arc42/08-crosscutting.md",
        context_hint="Document the crosscutting patterns: DI, validation, caching, testing approach. With code evidence.",
    ),
    ChapterRecipe(
        id="arc42-ch09",
        title="Architecture Decisions",
        output_file="arc42/09-decisions.md",
        facts=[("containers", {}), ("all", {}), ("interfaces", {})],
        rag_queries=["architecture decision spring framework database"],
        sections=["## 9.1 Decision Log Overview", "## 9.2 Architecture Decision Records"],
        context_hint="Create 10+ ADRs in the format: Title | Status | Context | Decision | Consequences. Derive from technology choices in the code.",
    ),
    ChapterRecipe(
        id="arc42-ch10",
        title="Quality Requirements",
        output_file="arc42/10-quality.md",
        facts=[("containers", {}), ("all", {}), ("relations", {})],
        rag_queries=["quality performance test"],
        sections=["## 10.1 Quality Tree", "## 10.2 Quality Scenarios"],
        context_hint="Create a quality tree (Maintainability, Performance, Security, Reliability) with 15+ concrete scenarios derived from the architecture.",
    ),
    ChapterRecipe(
        id="arc42-ch11",
        title="Risks and Technical Debt",
        output_file="arc42/11-risks.md",
        facts=[("containers", {}), ("all", {}), ("relations", {})],
        rag_queries=["deprecated legacy TODO FIXME coupling circular"],
        sections=["## 11.1 Risk Overview", "## 11.2 Architecture Risks", "## 11.3 Technical Debt Inventory"],
        context_hint="Identify 8+ risks and 10+ tech debt items. Include: severity, probability, mitigation strategy. Base on real code evidence.",
    ),
    ChapterRecipe(
        id="arc42-ch12",
        title="Glossary",
        output_file="arc42/12-glossary.md",
        facts=[("all", {}), ("containers", {})],
        components=["entity", "service"],
        rag_queries=["domain model business terminology"],
        sections=["## 12.1 Business Terms", "## 12.2 Technical Terms"],
        use_fast_model=True,
        context_hint="Extract domain terms from entity names, service names, and business logic. Include both German and English terms if the codebase uses both.",
    ),
]

# =============================================================================
# C4 RECIPES
# =============================================================================

C4_RECIPES: list[ChapterRecipe] = [
    ChapterRecipe(
        id="c4-context",
        title="C4 Level 1 — System Context",
        output_file="c4/c4-context.md",
        facts=[("containers", {}), ("interfaces", {}), ("relations", {})],
        components=["controller"],
        sections=["## 1.1 Overview", "## 1.2 The System", "## 1.3 Actors", "## 1.4 External Systems"],
        min_length=1500,
        max_length=15000,
        diagram_file="c4/c4-context.drawio",
        context_hint="Identify the system boundary, all external actors (users, admins), and external systems (databases, auth providers, message queues).",
    ),
    ChapterRecipe(
        id="c4-container",
        title="C4 Level 2 — Container Diagram",
        output_file="c4/c4-container.md",
        facts=[("containers", {}), ("relations", {}), ("interfaces", {})],
        sections=["## 2.1 Overview", "## 2.2 Container Inventory", "## 2.3 Container Interactions"],
        min_length=1500,
        max_length=15000,
        diagram_file="c4/c4-container.drawio",
        context_hint="Show all containers (backend app, frontend, database, cache, message queue) and their interactions with protocols.",
    ),
    ChapterRecipe(
        id="c4-component",
        title="C4 Level 3 — Component Diagram",
        output_file="c4/c4-component.md",
        facts=[("relations", {})],
        components=["controller", "service", "repository", "entity"],
        sections=["## 3.1 Overview", "## 3.2 Backend Components", "## 3.3 Component Dependencies"],
        min_length=1500,
        max_length=15000,
        diagram_file="c4/c4-component.drawio",
        context_hint="Show component layers (presentation, business, data access, domain) with counts. NOT individual components — show layer interactions.",
    ),
    ChapterRecipe(
        id="c4-deployment",
        title="C4 Level 4 — Deployment",
        output_file="c4/c4-deployment.md",
        facts=[("containers", {}), ("relations", {})],
        sections=["## 4.1 Overview", "## 4.2 Infrastructure Nodes", "## 4.3 Container Mapping"],
        min_length=1500,
        max_length=15000,
        diagram_file="c4/c4-deployment.drawio",
        context_hint="Derive deployment from Docker/K8s configs. Show network zones, load balancers, scaling strategy.",
    ),
]

# Merge groups: which parts combine into which final file
MERGE_GROUPS: dict[str, list[str]] = {
    "arc42/05-building-blocks.md": [
        "arc42/05-part1-overview.md",
        "arc42/05-part2a-controllers.md",
        "arc42/05-part2b-inventory.md",
        "arc42/05-part3-services.md",
        "arc42/05-part4-domain.md",
    ],
    "arc42/06-runtime-view.md": [
        "arc42/06-part1-api-flows.md",
        "arc42/06-part2-business-flows.md",
    ],
    "arc42/08-crosscutting.md": [
        "arc42/08-part1a-domain-security.md",
        "arc42/08-part1b-persistence-ops.md",
        "arc42/08-part2-patterns.md",
    ],
}
