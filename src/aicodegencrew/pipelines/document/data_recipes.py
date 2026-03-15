"""Data Recipes — defines exactly what data each chapter needs.

Each recipe specifies:
- facts: list of (category, params) tuples for query_facts
- rag_queries: list of search queries for rag_query
- components: list of stereotypes for list_components_by_stereotype
- sections: expected markdown sections in output
- min_length / max_length: character bounds for validation
- context_hint: chapter-specific guidance for the LLM
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
    min_length: int = 5000
    max_length: int = 30000
    use_fast_model: bool = False
    merge_into: str | None = None
    diagram_file: str | None = None
    context_hint: str = ""


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
        rag_queries=[
            "quality goals non-functional requirements",
            "business domain terminology purpose",
            "README project description documentation",
        ],
        sections=["## 1.1 Requirements Overview", "## 1.2 Quality Goals", "## 1.3 Stakeholders"],
        min_length=8000,
        context_hint=(
            "Write a comprehensive introduction that explains:\n"
            "- What is the business purpose of this system? Who uses it and why?\n"
            "- What are the top 5 quality goals (as a table: Priority | Quality Goal | Motivation)?\n"
            "- Who are the stakeholders (as a table: Role | Contact | Expectations)?\n"
            "- What are the key functional requirements derived from the interfaces and components?\n"
            "Derive stakeholders from the architecture: API consumers, administrators, developers, "
            "end users, operations team. Be specific about THIS system, not generic."
        ),
    ),
    ChapterRecipe(
        id="arc42-ch02",
        title="Architecture Constraints",
        output_file="arc42/02-constraints.md",
        facts=[("all", {}), ("containers", {})],
        rag_queries=[
            "naming convention package structure configuration",
            "Oracle datasource database connection jdbc",
            "Spring Boot version framework dependency",
            "Java version JDK compiler source target",
        ],
        sections=["## 2.1 Technical Constraints", "## 2.2 Organizational Constraints", "## 2.3 Convention Constraints"],
        min_length=6000,
        context_hint=(
            "Derive constraints from evidence in the code:\n"
            "- Technical: programming language version, framework versions, database technology, build tool\n"
            "- Organizational: team structure (from module structure), deployment model\n"
            "- Conventions: naming patterns, package structure, coding standards\n"
            "Present each constraint as a table: Constraint | Description | Rationale.\n"
            "Every constraint MUST be backed by evidence from the code (file path, config value, dependency version)."
        ),
    ),
    ChapterRecipe(
        id="arc42-ch03",
        title="System Scope and Context",
        output_file="arc42/03-context.md",
        facts=[("containers", {}), ("interfaces", {}), ("relations", {})],
        rag_queries=[
            "external system integration API client",
            "authentication authorization SSO token",
            "database connection datasource JDBC",
            "message queue event kafka rabbit",
        ],
        sections=["## 3.1 Business Context", "## 3.2 Technical Context"],
        min_length=8000,
        context_hint=(
            "Identify ALL external actors and systems from the interfaces and relations data:\n"
            "- Business Context: table with Actor | Channel | Data Exchanged | Purpose\n"
            "- Technical Context: Mermaid diagram showing system boundary, all external interfaces\n"
            "- For each external system: explain the integration pattern (REST, JDBC, message queue, file)\n"
            "- Analyze: What are the risks of the current integration architecture? Single points of failure?"
        ),
    ),
    ChapterRecipe(
        id="arc42-ch04",
        title="Solution Strategy",
        output_file="arc42/04-solution-strategy.md",
        facts=[("all", {}), ("containers", {})],
        components=["configuration"],
        rag_queries=[
            "architecture pattern repository service framework",
            "Spring Security configuration authentication",
            "caching strategy cache configuration",
            "error handling exception strategy ControllerAdvice",
        ],
        sections=["## 4.1 Technology Decisions", "## 4.2 Architecture Patterns", "## 4.3 Achieving Quality Goals"],
        min_length=8000,
        context_hint=(
            "Explain the fundamental architecture decisions and their rationale:\n"
            "- Technology Decisions: table with Technology | Purpose | Alternatives Considered | Rationale\n"
            "- Architecture Patterns: which patterns are used (Layered, MVC, Repository, etc.) and WHY\n"
            "- Quality Goals: how does each technology/pattern decision contribute to quality goals?\n"
            "- Trade-offs: what was sacrificed for each decision? (e.g., monolith = simpler deployment but harder scaling)\n"
            "Be analytical, not just descriptive. Explain the WHY behind every choice."
        ),
    ),
    # Chapter 5: Building Blocks (4 parts → merged)
    ChapterRecipe(
        id="arc42-ch05-p1",
        title="Building Block View — Overview",
        output_file="arc42/05-part1-overview.md",
        facts=[("all", {}), ("containers", {})],
        components=["controller", "service", "repository"],
        rag_queries=["package structure module organization layer"],
        sections=["## 5.1 Overview", "## 5.2 Whitebox Overall System"],
        min_length=6000,
        merge_into="arc42/05-building-blocks.md",
        context_hint=(
            "Show the system decomposition at the highest level:\n"
            "- Mermaid diagram showing the layered architecture with component counts per layer\n"
            "- Table: Layer | Purpose | Component Count | Key Technologies\n"
            "- Explain the responsibility of each layer and the dependency rules between them\n"
            "- Identify any layer violations visible in the relations data"
        ),
    ),
    ChapterRecipe(
        id="arc42-ch05-p2a",
        title="Building Block View — Controller Layer",
        output_file="arc42/05-part2a-controllers.md",
        facts=[("interfaces", {})],
        components=["controller"],
        rag_queries=[
            "REST controller patterns RequestMapping validation security",
            "@RestController @GetMapping @PostMapping endpoint",
            "request response DTO validation @Valid",
        ],
        sections=["## 5.3 Presentation Layer", "### 5.3.1 Layer Overview", "### 5.3.2 Key Controllers"],
        min_length=8000,
        merge_into="arc42/05-building-blocks.md",
        context_hint=(
            "Deep-dive the presentation layer:\n"
            "- Layer overview: total controllers, total endpoints, HTTP method distribution\n"
            "- Top 5 most important controllers: for each show Name | Endpoints | Methods | Responsibility\n"
            "- For each top controller: list all endpoints as table (Method | Path | Description)\n"
            "- API patterns: how is validation done? Error responses? Authentication?\n"
            "- Analysis: are there any REST anti-patterns? Oversized controllers? Missing versioning?"
        ),
    ),
    ChapterRecipe(
        id="arc42-ch05-p2b",
        title="Building Block View — Controller Inventory",
        output_file="arc42/05-part2b-inventory.md",
        facts=[("all", {}), ("interfaces", {})],
        components=["controller"],
        sections=["### 5.3.3 Controller Inventory"],
        min_length=3000,
        merge_into="arc42/05-building-blocks.md",
        context_hint=(
            "Create a complete inventory table of ALL controllers:\n"
            "Name | Module | Endpoints Count | HTTP Methods | Primary Responsibility\n"
            "Sort by number of endpoints (most complex first).\n"
            "Add a summary: total controllers, total endpoints, average endpoints per controller."
        ),
    ),
    ChapterRecipe(
        id="arc42-ch05-p3",
        title="Building Block View — Service Layer",
        output_file="arc42/05-part3-services.md",
        facts=[("containers", {}), ("relations", {})],
        components=["service"],
        rag_queries=[
            "service implementation transaction @Transactional",
            "business logic workflow process",
            "service dependency injection @Autowired",
        ],
        sections=["## 5.4 Business Layer", "### 5.4.1 Layer Overview", "### 5.4.2 Service Inventory"],
        min_length=8000,
        merge_into="arc42/05-building-blocks.md",
        context_hint=(
            "Deep-dive the business layer:\n"
            "- Layer overview: total services, transaction patterns, dependency patterns\n"
            "- Top 5 most important services: for each show Name | Dependencies | Responsibility | Patterns\n"
            "- Service inventory: table with Name | Module | Dependencies Count | Uses Transactions?\n"
            "- Service interaction Mermaid diagram showing the top 10 services and their dependencies\n"
            "- Analysis: are there God services? Circular dependencies? Missing abstractions?"
        ),
    ),
    ChapterRecipe(
        id="arc42-ch05-p4",
        title="Building Block View — Domain and Persistence",
        output_file="arc42/05-part4-domain.md",
        facts=[("relations", {}), ("data_model", {})],
        components=["entity", "repository"],
        rag_queries=[
            "Oracle datasource database connection spring",
            "@Entity JPA column table mapping",
            "repository pattern JpaRepository CrudRepository",
        ],
        sections=["## 5.5 Domain Layer", "## 5.6 Persistence Layer", "## 5.7 Component Dependencies"],
        min_length=8000,
        merge_into="arc42/05-building-blocks.md",
        context_hint=(
            "Deep-dive domain and persistence:\n"
            "- Domain model: Mermaid class diagram of top 10 entities and their relationships\n"
            "- Entity inventory: table with Name | Table | Key Fields | Relationships\n"
            "- Repository inventory: table with Name | Entity | Custom Queries? | Pattern\n"
            "- Database technology: which DB? Connection pooling? Migration strategy?\n"
            "- Analysis: is the domain model anemic or rich? Are there aggregate roots? DDD patterns?"
        ),
    ),
    # Chapter 6: Runtime View (2 parts → merged)
    ChapterRecipe(
        id="arc42-ch06-p1",
        title="Runtime View — API Flows",
        output_file="arc42/06-part1-api-flows.md",
        facts=[("interfaces", {}), ("containers", {}), ("relations", {})],
        components=["controller"],
        rag_queries=[
            "request flow authentication security filter",
            "CRUD create read update delete endpoint",
            "error handling exception response status code",
        ],
        sections=["## 6.1 Runtime View Overview", "## 6.2 Authentication Flow", "## 6.3 CRUD Operation Flows"],
        min_length=8000,
        merge_into="arc42/06-runtime-view.md",
        context_hint=(
            "Show how the system behaves at runtime:\n"
            "- Authentication flow: Mermaid sequence diagram Client → Filter → Auth → Controller\n"
            "- CRUD flow: Mermaid sequence diagram for a typical create operation through all layers\n"
            "- Error flow: what happens when validation fails? When the DB is down?\n"
            "- For each flow: list the components involved and their responsibilities\n"
            "Use at least 3 Mermaid sequence diagrams."
        ),
    ),
    ChapterRecipe(
        id="arc42-ch06-p2",
        title="Runtime View — Business Flows",
        output_file="arc42/06-part2-business-flows.md",
        facts=[("containers", {}), ("relations", {})],
        components=["service"],
        rag_queries=[
            "workflow state transition scheduled task batch",
            "exception error handling recovery retry",
            "event notification trigger async",
        ],
        sections=["## 6.4 Core Business Workflows", "## 6.5 Error and Recovery Scenarios"],
        min_length=6000,
        merge_into="arc42/06-runtime-view.md",
        context_hint=(
            "Show complex business processes:\n"
            "- Identify the most important business workflows from the service layer\n"
            "- Mermaid flowchart or sequence diagram for each core workflow\n"
            "- Error and recovery: what happens on failure? Retry? Compensation? Rollback?\n"
            "- Scheduled tasks: what runs periodically? At what intervals? Why?"
        ),
    ),
    ChapterRecipe(
        id="arc42-ch07",
        title="Deployment View",
        output_file="arc42/07-deployment.md",
        facts=[("all", {}), ("containers", {})],
        rag_queries=[
            "docker dockerfile kubernetes deployment",
            "application properties profile environment",
            "server port host configuration",
            "CI CD pipeline build deploy",
        ],
        sections=["## 7.1 Infrastructure Overview", "## 7.2 Infrastructure Nodes", "## 7.3 Container Deployment"],
        min_length=6000,
        context_hint=(
            "Derive deployment topology from code evidence:\n"
            "- Infrastructure: Mermaid diagram showing deployment nodes (app server, DB, load balancer)\n"
            "- Container mapping: which software container runs on which infrastructure node?\n"
            "- Environment config: what environment-specific settings exist? (profiles, property files)\n"
            "- If no explicit deployment config found: state this clearly and derive likely setup from the tech stack\n"
            "- Analysis: is the deployment cloud-ready? Container-ready? What's missing?"
        ),
    ),
    # Chapter 8: Crosscutting Concepts (3 parts → merged)
    ChapterRecipe(
        id="arc42-ch08-p1a",
        title="Crosscutting Concepts — Domain and Security",
        output_file="arc42/08-part1a-domain-security.md",
        facts=[],
        components=["entity"],
        rag_queries=[
            "security authentication authorization JWT token",
            "@Entity JPA domain model aggregate",
            "Spring Security configuration WebSecurityConfig",
            "role permission access control RBAC",
        ],
        sections=["## 8.1 Domain Model", "## 8.2 Security Concept"],
        min_length=8000,
        merge_into="arc42/08-crosscutting.md",
        context_hint=(
            "Two critical crosscutting concerns:\n"
            "Domain Model:\n"
            "- Mermaid class diagram of the core domain entities and their relationships\n"
            "- Explain the domain model: is it anemic or rich? Aggregate roots? Value objects?\n"
            "- Table: Entity | Purpose | Key Attributes | Relationships\n\n"
            "Security Concept:\n"
            "- Authentication: how are users authenticated? (JWT, session, SSO, token?)\n"
            "- Authorization: how is access controlled? (@PreAuthorize, roles, permissions?)\n"
            "- Mermaid sequence diagram of the authentication flow\n"
            "- Analysis: are there security gaps? Missing CSRF protection? Weak token handling?"
        ),
    ),
    ChapterRecipe(
        id="arc42-ch08-p1b",
        title="Crosscutting Concepts — Persistence and Operations",
        output_file="arc42/08-part1b-persistence-ops.md",
        facts=[],
        components=["repository"],
        rag_queries=[
            "Transactional JPA persistence EntityManager",
            "ControllerAdvice exception error handling ResponseEntity",
            "slf4j logback logging MDC structured",
            "health check actuator monitoring metrics",
        ],
        sections=["## 8.3 Persistence", "## 8.4 Error Handling", "## 8.5 Logging"],
        min_length=8000,
        merge_into="arc42/08-crosscutting.md",
        context_hint=(
            "Three operational crosscutting concerns:\n"
            "Persistence:\n"
            "- Transaction management: @Transactional patterns, propagation, isolation\n"
            "- JPA configuration: entity scanning, naming strategy, DDL auto\n\n"
            "Error Handling:\n"
            "- Global strategy: @ControllerAdvice, exception hierarchy\n"
            "- Error response format: status codes, error DTOs\n"
            "- Analysis: is error handling consistent? Are there catch-all handlers?\n\n"
            "Logging:\n"
            "- Framework: SLF4J, Logback? Structured logging?\n"
            "- Log levels, correlation IDs, audit logging patterns"
        ),
    ),
    ChapterRecipe(
        id="arc42-ch08-p2",
        title="Crosscutting Concepts — Patterns and Conventions",
        output_file="arc42/08-part2-patterns.md",
        facts=[("all", {}), ("containers", {})],
        rag_queries=[
            "configuration properties profile cache @Value",
            "validation Bean JSR @Valid @NotNull constraint",
            "test junit mockito SpringBootTest integration",
            "dependency injection @Autowired @Component @Service",
        ],
        sections=["## 8.6 Dependency Injection", "## 8.7 Validation", "## 8.8 Testing Concept"],
        min_length=8000,
        merge_into="arc42/08-crosscutting.md",
        context_hint=(
            "Architecture-wide patterns and conventions:\n"
            "Dependency Injection:\n"
            "- How is DI used? Constructor injection vs field injection?\n"
            "- Configuration management: @ConfigurationProperties, profiles, externalized config\n\n"
            "Validation:\n"
            "- Input validation: Bean Validation, custom validators, validation groups\n"
            "- Where is validation enforced? Controller level? Service level? Both?\n\n"
            "Testing Concept:\n"
            "- Test types: unit, integration, E2E — with counts from the test data\n"
            "- Test frameworks: JUnit, Mockito, Spring Test, Playwright\n"
            "- Test coverage analysis: which layers are well-tested, which are not?"
        ),
    ),
    ChapterRecipe(
        id="arc42-ch09",
        title="Architecture Decisions",
        output_file="arc42/09-decisions.md",
        facts=[("containers", {}), ("all", {}), ("interfaces", {})],
        rag_queries=[
            "architecture decision spring framework database",
            "technology choice migration upgrade version",
            "design pattern strategy implementation approach",
        ],
        sections=["## 9.1 Decision Log Overview", "## 9.2 Architecture Decision Records"],
        min_length=10000,
        context_hint=(
            "Create 10+ Architecture Decision Records (ADRs) derived from the code:\n"
            "Each ADR must follow this format:\n"
            "### ADR-{N}: {Title}\n"
            "- **Status**: Accepted\n"
            "- **Context**: What problem needed to be solved?\n"
            "- **Decision**: What was decided?\n"
            "- **Consequences**: What are the positive and negative effects?\n"
            "- **Evidence**: Which files/configs prove this decision? (file paths!)\n\n"
            "Derive ADRs from real evidence: Spring Boot choice, database technology, "
            "authentication mechanism, API design style, build tool, test framework, "
            "module structure, error handling strategy, caching approach, logging framework."
        ),
    ),
    ChapterRecipe(
        id="arc42-ch10",
        title="Quality Requirements",
        output_file="arc42/10-quality.md",
        facts=[("containers", {}), ("all", {}), ("relations", {})],
        rag_queries=[
            "quality performance test benchmark",
            "security vulnerability scan audit",
            "maintainability complexity coupling cohesion",
        ],
        sections=["## 10.1 Quality Tree", "## 10.2 Quality Scenarios"],
        min_length=8000,
        context_hint=(
            "Define quality requirements based on architecture evidence:\n"
            "Quality Tree:\n"
            "- Mermaid mindmap showing: Maintainability, Performance, Security, Reliability, Testability\n"
            "- For each: 3-4 sub-attributes derived from the actual architecture\n\n"
            "Quality Scenarios (15+ scenarios):\n"
            "Table: ID | Quality Attribute | Scenario | Expected Response | Priority\n"
            "Derive scenarios from REAL architecture evidence:\n"
            "- Maintainability: 'A developer changes service X — how many files are affected?'\n"
            "- Performance: 'API endpoint Y receives 100 concurrent requests — response time?'\n"
            "- Security: 'An unauthenticated user accesses endpoint Z — system rejects with 401'\n"
            "Every scenario must reference a real component or endpoint from the data."
        ),
    ),
    ChapterRecipe(
        id="arc42-ch11",
        title="Risks and Technical Debt",
        output_file="arc42/11-risks.md",
        facts=[("containers", {}), ("all", {}), ("relations", {})],
        rag_queries=[
            "deprecated legacy TODO FIXME coupling circular",
            "complexity god class large method long parameter",
            "missing test untested coverage gap",
            "security vulnerability hardcoded password secret",
        ],
        sections=["## 11.1 Risk Overview", "## 11.2 Architecture Risks", "## 11.3 Technical Debt Inventory"],
        min_length=8000,
        context_hint=(
            "Identify risks and technical debt from architecture evidence:\n"
            "Architecture Risks (8+ risks):\n"
            "Table: ID | Risk | Probability | Impact | Mitigation\n"
            "Derive from: coupling metrics, missing abstractions, security gaps, scalability limits\n\n"
            "Technical Debt (10+ items):\n"
            "Table: ID | Debt Item | Severity | Effort to Fix | Evidence (file/code)\n"
            "Derive from: TODO/FIXME in code, deprecated APIs, layer violations, "
            "missing tests, hardcoded values, God classes\n\n"
            "Mitigation Roadmap: prioritize the top 5 items with concrete actions."
        ),
    ),
    ChapterRecipe(
        id="arc42-ch12",
        title="Glossary",
        output_file="arc42/12-glossary.md",
        facts=[("all", {}), ("containers", {})],
        components=["entity", "service"],
        rag_queries=[
            "domain model business terminology",
            "acronym abbreviation definition constant",
        ],
        sections=["## 12.1 Business Terms", "## 12.2 Technical Terms"],
        min_length=4000,
        context_hint=(
            "Extract ALL domain-specific terms from the codebase:\n"
            "Business Terms: table with Term | Definition | Used In (component/module)\n"
            "Technical Terms: table with Term | Definition | Context\n"
            "Abbreviations: table with Abbreviation | Full Form | Domain\n\n"
            "Sources: entity names, service names, API path segments, enum values, "
            "package names, configuration keys. Include German terms if the codebase uses them."
        ),
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
        rag_queries=[
            "external system integration client adapter",
            "authentication SSO identity provider",
        ],
        sections=["## 1.1 Overview", "## 1.2 The System", "## 1.3 Actors", "## 1.4 External Systems"],
        min_length=6000,
        max_length=20000,
        diagram_file="c4/c4-context.drawio",
        context_hint=(
            "C4 Level 1 — the highest abstraction level:\n"
            "- Overview: what does the system do? One paragraph.\n"
            "- The System: name, type, technology summary\n"
            "- Actors: table with Actor | Type (person/system) | Interaction | Protocol\n"
            "- External Systems: table with System | Purpose | Integration Type | Data Flow\n"
            "- Mermaid C4 context diagram showing the system, actors, and external systems\n"
            "- Analysis: are there too many external dependencies? Missing system boundaries?"
        ),
    ),
    ChapterRecipe(
        id="c4-container",
        title="C4 Level 2 — Container Diagram",
        output_file="c4/c4-container.md",
        facts=[("containers", {}), ("relations", {}), ("interfaces", {})],
        rag_queries=["docker container deployment microservice monolith"],
        sections=["## 2.1 Overview", "## 2.2 Container Inventory", "## 2.3 Container Interactions"],
        min_length=6000,
        max_length=20000,
        diagram_file="c4/c4-container.drawio",
        context_hint=(
            "C4 Level 2 — containers within the system:\n"
            "- Container Inventory: table with Container | Type | Technology | Responsibility | Ports\n"
            "- Container Interactions: table with Source | Target | Protocol | Data | Purpose\n"
            "- Mermaid C4 container diagram with system boundary, all containers, external actors\n"
            "- Technology stack summary per container\n"
            "- Analysis: is the container architecture well-decomposed? Monolith risks?"
        ),
    ),
    ChapterRecipe(
        id="c4-component",
        title="C4 Level 3 — Component Diagram",
        output_file="c4/c4-component.md",
        facts=[("relations", {})],
        components=["controller", "service", "repository", "entity"],
        rag_queries=["layer architecture dependency injection component"],
        sections=["## 3.1 Overview", "## 3.2 Backend Components", "## 3.3 Component Dependencies"],
        min_length=6000,
        max_length=20000,
        diagram_file="c4/c4-component.drawio",
        context_hint=(
            "C4 Level 3 — components within the main container:\n"
            "- Show LAYERS, not individual components (too many for a diagram)\n"
            "- Layer summary: table with Layer | Stereotype | Count | Key Responsibility\n"
            "- Dependency rules: which layer may depend on which? Are there violations?\n"
            "- Mermaid diagram showing layers as boxes with dependency arrows and counts\n"
            "- Top 5 most connected components (highest dependency count)\n"
            "- Analysis: coupling metrics, layer violation count, circular dependencies"
        ),
    ),
    ChapterRecipe(
        id="c4-deployment",
        title="C4 Level 4 — Deployment",
        output_file="c4/c4-deployment.md",
        facts=[("containers", {}), ("relations", {})],
        rag_queries=[
            "docker dockerfile kubernetes deployment infrastructure",
            "server port configuration environment profile",
        ],
        sections=["## 4.1 Overview", "## 4.2 Infrastructure Nodes", "## 4.3 Container Mapping"],
        min_length=5000,
        max_length=20000,
        diagram_file="c4/c4-deployment.drawio",
        context_hint=(
            "C4 Level 4 — deployment topology:\n"
            "- Infrastructure nodes: table with Node | Type | Purpose | Hosted Containers\n"
            "- Container mapping: which container runs where?\n"
            "- Mermaid deployment diagram with network zones (DMZ, app zone, data zone)\n"
            "- Environment configuration: what varies between environments?\n"
            "- If deployment info is limited in the code: state clearly what is inferred vs confirmed\n"
            "- Analysis: scaling strategy, HA setup, disaster recovery readiness"
        ),
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
