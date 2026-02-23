"""
Arc42 Crew - Task Descriptions
================================
Task descriptions for all 12 arc42 chapters + quality gate.

Chapters 5, 6, and 8 are split into sub-crews for maximum output quality:
- Chapter 5: 4 sub-crews (overview, controllers, services, domain)
- Chapter 6: 2 sub-crews (API flows, business flows)
- Chapter 8: 2 sub-crews (technical concepts, patterns)

Each task uses {template_variables} for facts data injection.
"""

from ..base_crew import TOOL_INSTRUCTION

# =============================================================================
# Chapter 1: Introduction and Goals
# =============================================================================

CH01_INTRODUCTION = (
    TOOL_INSTRUCTION
    + """
Create the COMPLETE arc42 Chapter 1: Introduction and Goals.
Document generation date: {current_date}

## REQUIRED SECTIONS (do NOT skip any):
### 1.1 Requirements Overview
- Full system description with business domain classification
- Primary business value and target users
- Feature inventory table with ALL business capabilities (derive from controller/service names)
- System statistics table (components, controllers, services, repos, entities, endpoints)
### 1.2 Quality Goals
- Quality goal table with measurable targets for each attribute
- At least 5 goals: Maintainability, Testability, Security, Performance, Scalability
- For EACH: Priority, Rationale, How Achieved (which patterns), Measurement
### 1.3 Stakeholders
- Stakeholder table with at least 8 roles
- For EACH: Role, Concern, Expectations, Key Interactions

## EXECUTION EXAMPLE (follow this pattern):
1. get_statistics() -> get component counts
2. get_architecture_summary() -> get architecture style, patterns
3. list_components_by_stereotype(stereotype="controller") -> get ALL controllers
4. list_components_by_stereotype(stereotype="service") -> get ALL services
5. list_components_by_stereotype(stereotype="repository") -> get ALL repositories
6. list_components_by_stereotype(stereotype="entity") -> get ALL entities
7. get_endpoints() -> get REST API endpoints
8. doc_writer(file_path="arc42/01-introduction.md", content="# 01 - Introduction and Goals\\n\\n## 1.1 Requirements Overview\\n...")
9. Respond: "File arc42/01-introduction.md written successfully."

Summary data:
{system_summary}

Write to file: arc42/01-introduction.md using doc_writer tool.
Write 8-12 pages with REAL data from tools. No placeholders.
"""
)

# =============================================================================
# Chapter 2: Architecture Constraints
# =============================================================================

CH02_CONSTRAINTS = (
    TOOL_INSTRUCTION
    + """
Create the COMPLETE arc42 Chapter 2: Architecture Constraints.

## REQUIRED SECTIONS (do NOT skip any):
### 2.1 Technical Constraints
- Constraint table for: Programming Language, Framework, Database, Infrastructure, Security
- For EACH: Constraint name, Background, Impact on architecture, Consequences
### 2.2 Organizational Constraints
- Team structure, development process, deployment frequency
- Compliance and regulatory requirements
### 2.3 Convention Constraints
- Naming conventions (packages, classes, methods, REST endpoints)
- Code style and formatting rules
- API design conventions (REST, versioning)

## EXECUTION EXAMPLE (follow this pattern):
1. get_statistics() -> get system overview
2. get_architecture_summary() -> get architecture decisions and patterns
3. query_architecture_facts(category="containers") -> get container technologies
4. rag_query(query="naming convention package structure") -> naming patterns
5. rag_query(query="configuration properties spring") -> framework constraints
6. rag_query(query="Oracle datasource database connection jdbc") -> database technology
7. doc_writer(file_path="arc42/02-constraints.md", content="# 02 - Architecture Constraints\\n...")
8. Respond: "File arc42/02-constraints.md written successfully."

Summary data:
{system_summary}
{containers_summary}

Write to file: arc42/02-constraints.md using doc_writer tool.
Write 8-10 pages with REAL data from tools. No placeholders.
"""
)

# =============================================================================
# Chapter 3: System Scope and Context
# =============================================================================

CH03_CONTEXT = (
    TOOL_INSTRUCTION
    + """
Create the COMPLETE arc42 Chapter 3: System Scope and Context.

## REQUIRED SECTIONS (do NOT skip any):
### 3.1 Business Context
- Context diagram (text-based ASCII showing system + external actors)
- External actors table: | Actor | Role | Interactions | Volume |
- External systems table: | System | Purpose | Protocol | Data Exchanged |
### 3.2 Technical Context
- Technical interfaces: REST API surface, database connections, message channels
- Protocols and formats table
- Complete API endpoint inventory (summarized by domain)
### 3.3 External Dependencies
- Runtime dependencies table: | Dependency | Version | Purpose | Criticality |
- Build dependencies table
- Infrastructure dependencies

## EXECUTION EXAMPLE (follow this pattern):
1. get_statistics() -> get system overview
2. get_architecture_summary() -> get architecture style
3. get_endpoints() -> get ALL REST API endpoints
4. query_architecture_facts(category="containers") -> get container details
5. query_architecture_facts(category="interfaces") -> get API interfaces
6. rag_query(query="external system integration database") -> external deps
7. doc_writer(file_path="arc42/03-context.md", content="# 03 - System Scope and Context\\n...")
8. Respond: "File arc42/03-context.md written successfully."

Summary data:
{system_summary}

Write to file: arc42/03-context.md using doc_writer tool.
Write 8-12 pages with REAL data from tools. No placeholders.
"""
)

# =============================================================================
# Chapter 4: Solution Strategy
# =============================================================================

CH04_SOLUTION_STRATEGY = (
    TOOL_INSTRUCTION
    + """
Create the COMPLETE arc42 Chapter 4: Solution Strategy.

## REQUIRED SECTIONS (do NOT skip any):
### 4.1 Technology Decisions
- ADR-lite table for EACH major technology: Backend Framework, Database, Frontend, Build Tool,
  Container Technology, Security Framework, API Design
- For EACH: Context, Decision, Rationale, Alternatives, Consequences
### 4.2 Architecture Patterns
- Macro architecture: pattern name, layer responsibilities, dependency rules
- Applied patterns table: | Pattern | Purpose | Where Applied | Benefit |
- At least 8 patterns from the codebase
### 4.3 Achieving Quality Goals
- Table: | Quality Goal | Solution Approach | Implemented By |
- Map quality goals to concrete architectural decisions

## EXECUTION EXAMPLE (follow this pattern):
1. get_architecture_summary() -> get architecture style, patterns, layers
2. get_statistics() -> get system metrics
3. query_architecture_facts(category="containers") -> get container technologies
4. list_components_by_stereotype(stereotype="configuration") -> get config components
5. rag_query(query="architecture pattern repository service") -> pattern details
6. rag_query(query="framework spring boot version") -> framework info
7. doc_writer(file_path="arc42/04-solution-strategy.md", content="# 04 - Solution Strategy\\n...")
8. Respond: "File arc42/04-solution-strategy.md written successfully."

Summary data:
{system_summary}

Write to file: arc42/04-solution-strategy.md using doc_writer tool.
Write 8-12 pages with REAL data from tools. No placeholders.
"""
)

# =============================================================================
# Chapter 5: Building Block View (split into 4 sub-crews)
# =============================================================================

CH05_PART1_OVERVIEW = (
    TOOL_INSTRUCTION
    + """
Create arc42 Chapter 5 PART 1: Overview and System Whitebox.

## REQUIRED SECTIONS (do NOT skip any):
### 5.1 Overview
- A-Architecture (Functional view): business capabilities mapped to layers
- T-Architecture (Technical view): containers hosting building blocks
- Building Block Hierarchy with total counts per stereotype
### 5.2 Whitebox Overall System (Level 1)
- Container overview diagram (text-based ASCII)
- Container responsibilities table: | Container | Technology | Purpose | Component Count |
- Layer dependency rules diagram
- Component distribution across containers

## EXECUTION EXAMPLE (follow this pattern):
1. get_statistics() -> get component counts per layer
2. get_architecture_summary() -> get layer structure and patterns
3. query_architecture_facts(category="containers") -> get container details
4. list_components_by_stereotype(stereotype="controller") -> count controllers
5. list_components_by_stereotype(stereotype="service") -> count services
6. list_components_by_stereotype(stereotype="repository") -> count repos
7. list_components_by_stereotype(stereotype="entity") -> count entities
8. doc_writer(file_path="arc42/05-part1-overview.md", content="# 05 - Building Block View\\n...")
9. Respond: "File arc42/05-part1-overview.md written successfully."

Summary data:
{system_summary}
{containers_summary}

Write to file: arc42/05-part1-overview.md using doc_writer tool.
Write 6-8 pages with REAL data from tools. No placeholders.
"""
)

CH05_PART2A_CONTROLLERS_OVERVIEW = (
    TOOL_INSTRUCTION
    + """
Create arc42 Chapter 5 Part 2A: Controller Layer Overview and Top 5 Deep Dive.

## REQUIRED SECTIONS (do NOT skip any):
### 5.3.1 Layer Overview
- Controller layer responsibilities and patterns
- Request lifecycle (HTTP → Controller → Service → Repository)
### 5.3.2 API Patterns
- REST conventions, URL naming, HTTP methods, response formats
- Common annotations used (@RestController, @RequestMapping, etc.)
### 5.3.3 Key Controllers Deep Dive — TOP 5 most important
- For EACH of the 5: endpoints listed, delegation to services, validation, security

## EXECUTION EXAMPLE (follow this pattern):
1. list_components_by_stereotype(stereotype="controller") -> get controller names (use first 5 for deep dive)
2. get_endpoints() -> get REST API endpoints
3. rag_query(query="REST controller endpoint mapping RequestMapping") -> API patterns
4. rag_query(query="controller validation security authentication") -> security details
5. doc_writer(file_path="arc42/05-part2a-controllers-overview.md", content="## 5.3 Presentation Layer\\n...")
6. Respond: "File arc42/05-part2a-controllers-overview.md written successfully."

Summary data:
{system_summary}

Write to file: arc42/05-part2a-controllers-overview.md using doc_writer tool.
Write 4-5 pages with REAL data from tools. No placeholders.
"""
)

CH05_PART2B_CONTROLLERS_INVENTORY = (
    TOOL_INSTRUCTION
    + """
Create arc42 Chapter 5 Part 2B: Controller Inventory Table.

## REQUIRED SECTIONS (do NOT skip any):
### 5.3.4 Controller Inventory (representative sample)
- Full table: | # | Controller | Package | Primary Responsibility |
- List the TOP 30 most important controllers (do NOT paginate for more — 30 is enough)
- State total count (e.g. "230 controllers total; representative sample below")
### 5.3.5 Endpoint Summary
- Total endpoint count by HTTP method (GET/POST/PUT/DELETE/PATCH)
- Most frequently used URL patterns

## EXECUTION — EXACTLY 4 TOOL CALLS (no more!):
1. list_components_by_stereotype(stereotype="controller") — ONE call, first page only
2. get_statistics() — total counts
3. get_endpoints() — count by HTTP method
4. doc_writer(file_path="arc42/05-part2b-controllers-inventory.md", content="...")

STRICT LIMIT: 4 tool calls total. Do NOT call list_components_by_stereotype for other stereotypes.
Do NOT paginate. Do NOT call get_architecture_summary. The summary data below has everything you need.

Summary data:
{system_summary}

Write to file: arc42/05-part2b-controllers-inventory.md using doc_writer tool.
Write 3-4 pages — focused on the inventory table only. No placeholders.
"""
)

CH05_PART3_SERVICES = (
    TOOL_INSTRUCTION
    + """
Create arc42 Chapter 5 PART 3: Business Layer / Services.

## REQUIRED SECTIONS (do NOT skip any):
### 5.4.1 Layer Overview
- Service layer responsibilities, bounded contexts, business rules
### 5.4.2 Service Inventory (representative sample)
- Table of TOP 30 services: | # | Service | Package | Interface? | Description |
  State total count. Do NOT paginate — one call is enough.
### 5.4.3 Service Patterns
- Interface/Implementation pattern, transaction boundaries, service composition
### 5.4.4 Key Services Deep Dive — TOP 5
- For EACH: Core responsibilities, transaction management, dependencies, events
### 5.4.5 Service Interactions
- Key service-to-service dependencies with direction

## EXECUTION EXAMPLE (follow this pattern):
1. list_components_by_stereotype(stereotype="service") -> get first page (do NOT paginate)
2. get_architecture_summary() -> get architecture patterns
3. get_statistics() -> get component counts
4. query_architecture_facts(category="relations") -> get service dependencies
5. rag_query(query="service implementation transaction") -> service patterns
6. doc_writer(file_path="arc42/05-part3-services.md", content="## 5.4 Business Layer\\n...")
7. Respond: "File arc42/05-part3-services.md written successfully."

Summary data:
{system_summary}

Write to file: arc42/05-part3-services.md using doc_writer tool.
Write 6-8 pages with REAL data. No placeholders. Do NOT paginate tool results.
"""
)

CH05_PART4_DOMAIN = (
    TOOL_INSTRUCTION
    + """
Create arc42 Chapter 5 PART 4: Domain Layer, Persistence Layer, Dependencies.

## REQUIRED SECTIONS (do NOT skip any):
### 5.5 Domain Layer — Entities
- Layer overview: JPA entities, aggregate roots, value objects
- Entity inventory (TOP 30): | # | Entity | Package | Key Attributes | Description |
  IMPORTANT: Include ONLY JPA @Entity classes (names ending in "Entity" or "Eto").
  EXCLUDE: Flyway migration scripts, SQL files, and any non-Java class items.
  State total count (e.g. "120 entities total; representative sample below").
- Key entities deep dive (TOP 5): attributes, relationships, lifecycle, validation
### 5.6 Persistence Layer — Repositories
- Layer overview: data access patterns
- Repository inventory (TOP 30): | # | Repository | Entity | Custom Queries | Description |
  Include DAO interfaces, JpaRepository extensions, and custom implementations.
  State total count. Do NOT paginate — one call is enough.
- Data access patterns (Spring Data JPA, custom queries, specifications)
### 5.7 Component Dependencies
- Layer dependency rules with direction
- Dependency matrix: | From/To | Controller | Service | Repository | Entity |
- Dependency statistics and coupling analysis

## EXECUTION EXAMPLE (follow this pattern):
1. list_components_by_stereotype(stereotype="entity") -> get first page (do NOT call again with offset)
2. list_components_by_stereotype(stereotype="repository") -> get first page (do NOT paginate)
3. query_architecture_facts(category="relations") -> get dependency data
4. get_statistics() -> get component counts
5. rag_query(query="Oracle datasource database connection spring") -> database technology
6. doc_writer(file_path="arc42/05-part4-domain.md", content="## 5.5 Domain Layer\\n...")
7. Respond: "File arc42/05-part4-domain.md written successfully."

IMPORTANT NOTES:
- Entity inventory: ONLY classes annotated with @Entity (JPA). Skip migration files.
- Repository inventory: Include all DAO/Repository classes (JPA + custom implementations).
- Use rag_query to confirm the actual production database (Oracle/H2/PostgreSQL — don't assume).
- Do NOT paginate tool results — use total_count for summary, one page is enough.
- Limit tool calls to 5-6 maximum to stay within token budget.

Summary data:
{system_summary}

Write to file: arc42/05-part4-domain.md using doc_writer tool.
Write 6-8 pages with REAL data. No placeholders.
"""
)

# =============================================================================
# Chapter 6: Runtime View (split into 2 sub-crews)
# =============================================================================

CH06_PART1_API_FLOWS = (
    TOOL_INSTRUCTION
    + """
Create arc42 Chapter 6 Part 1: API Runtime Flows.

## REQUIRED SECTIONS (do NOT skip any):
### 6.1 Runtime View Overview
- Purpose of runtime documentation
- How to read sequence diagrams
### 6.2 Authentication Flow
- Login sequence with ALL components involved
- Token refresh / session management
### 6.3 CRUD Operation Flows
- CREATE: Full request flow from client to database and back
- READ: Single item + list with pagination
- UPDATE: Optimistic locking / versioning
- DELETE: Cascade behavior
### 6.4 REST API Request Lifecycle
- Request validation, serialization, error mapping
- HTTP status code strategy
- Content negotiation

## EXECUTION EXAMPLE (follow this pattern):
1. get_endpoints() -> get ALL REST API endpoints
2. get_architecture_summary() -> get architecture patterns
3. list_components_by_stereotype(stereotype="controller") -> get controllers
4. list_components_by_stereotype(stereotype="service") -> get services
5. list_components_by_stereotype(stereotype="repository") -> get repositories
6. query_architecture_facts(category="relations") -> get component dependencies
7. rag_query(query="request flow authentication") -> get auth flow details
8. doc_writer(file_path="arc42/06-part1-api-flows.md", content="# 06 - Runtime View\\n\\n## 6.1 Overview\\n...")
9. Respond: "File arc42/06-part1-api-flows.md written successfully."

Summary data:
{system_summary}

Write to file: arc42/06-part1-api-flows.md using doc_writer tool.
Write 8-10 pages with REAL data from tools. No placeholders.
Include text-based sequence diagrams for EACH flow showing exact component names.
"""
)

CH06_PART2_BUSINESS_FLOWS = (
    TOOL_INSTRUCTION
    + """
Create arc42 Chapter 6 Part 2: Business Process Flows.

## REQUIRED SECTIONS (do NOT skip any):
### 6.5 Core Business Workflows
- Primary business process end-to-end (e.g., deed entry creation workflow)
- State transitions with component responsibilities
- Workflow orchestration pattern
### 6.6 Complex Business Scenarios
- Multi-step approval/validation flows
- Cross-service transactions
- Batch processing flows
### 6.7 Error and Recovery Scenarios
- Exception propagation through layers
- Compensation/rollback patterns
- Retry strategies
### 6.8 Asynchronous Patterns
- Scheduled tasks and cron jobs
- Event-driven interactions (if any)
- Background processing

## EXECUTION EXAMPLE (follow this pattern):
1. get_statistics() -> get system overview
2. get_architecture_summary() -> get architecture patterns
3. list_components_by_stereotype(stereotype="service") -> get ALL services
4. query_architecture_facts(category="relations") -> get dependencies
5. rag_query(query="workflow state transition") -> get workflow details
6. rag_query(query="scheduled task batch") -> get async patterns
7. rag_query(query="exception error handling") -> get error handling
8. doc_writer(file_path="arc42/06-part2-business-flows.md", content="## 6.5 Core Business Workflows\\n...")
9. Respond: "File arc42/06-part2-business-flows.md written successfully."

Summary data:
{system_summary}

Write to file: arc42/06-part2-business-flows.md using doc_writer tool.
Write 8-10 pages with REAL data from tools. No placeholders.
Include text-based sequence diagrams showing exact component names from facts.
"""
)

# =============================================================================
# Chapter 7: Deployment View
# =============================================================================

CH07_DEPLOYMENT = (
    TOOL_INSTRUCTION
    + """
Create the COMPLETE arc42 Chapter 7: Deployment View.

## REQUIRED SECTIONS (do NOT skip any):
### 7.1 Infrastructure Overview
- Deployment diagram (text-based ASCII)
- Infrastructure summary
### 7.2 Infrastructure Nodes
- Node table: | Node | Type | Specification | Purpose |
- Container-to-node mapping
### 7.3 Container Deployment
- Docker configuration details
- Container orchestration (Kubernetes/Docker Compose)
- Build pipeline (Maven/Gradle -> Docker image)
### 7.4 Environment Configuration
- Development, Test, Staging, Production environments
- Environment-specific settings
### 7.5 Network Topology
- Network zones and firewall rules
- Load balancing strategy
### 7.6 Scaling Strategy
- Scaling table: | Container | Scaling Type | Trigger | Min | Max |

## EXECUTION EXAMPLE (follow this pattern):
1. get_statistics() -> get system overview
2. query_architecture_facts(category="containers") -> get container details
3. get_architecture_summary() -> get infrastructure hints
4. rag_query(query="docker dockerfile kubernetes deployment") -> deployment config
5. rag_query(query="application properties profile environment") -> env config
6. doc_writer(file_path="arc42/07-deployment.md", content="# 07 - Deployment View\\n...")
7. Respond: "File arc42/07-deployment.md written successfully."

Summary data:
{system_summary}
{containers_summary}

Write to file: arc42/07-deployment.md using doc_writer tool.
Write 8-10 pages with REAL data from tools. No placeholders.
"""
)

# =============================================================================
# Chapter 8: Crosscutting Concepts (split into 3 sub-crews)
# =============================================================================

CH08_PART1A_DOMAIN_SECURITY = (
    TOOL_INSTRUCTION
    + """
Create arc42 Chapter 8 Part 1A: Domain Model and Security.

REQUIRED SECTIONS:
8.1 Domain Model: entity relationship diagram, entity inventory table (Entity|Attributes|Relationships), aggregate boundaries.
8.2 Security Concept: authentication mechanism, authorization model (roles/permissions), security annotations, CSRF/XSS prevention.

EXECUTION EXAMPLE:
1. list_components_by_stereotype(stereotype="entity") -> entities
2. search_components(query="security") -> security components
3. rag_query(query="security authentication authorization JWT") -> auth details
4. rag_query(query="@Entity JPA domain model") -> domain details
5. doc_writer(file_path="arc42/08-part1a-domain-security.md", content="# 08 - Part 1A\\n...")
6. Respond: "File arc42/08-part1a-domain-security.md written successfully."

{system_summary}

Write to: arc42/08-part1a-domain-security.md. 6-8 pages. REAL data. No placeholders.
"""
)

CH08_PART1B_PERSISTENCE_OPS = (
    TOOL_INSTRUCTION
    + """
Create arc42 Chapter 8 Part 1B: Persistence, Error Handling, Logging.

REQUIRED SECTIONS:
8.3 Persistence: JPA/ORM config, @Transactional, pooling, Flyway migrations.
8.4 Error Handling: exception hierarchy, @ControllerAdvice, error response, HTTP codes.
8.5 Logging: framework config, log levels, structured format, health endpoints.

EXECUTION EXAMPLE:
1. list_components_by_stereotype(stereotype="repository") -> repos
2. rag_query(query="Transactional JPA") -> persistence details
3. rag_query(query="ControllerAdvice exception") -> error handling
4. rag_query(query="slf4j logback logging") -> logging
5. doc_writer(file_path="arc42/08-part1b-persistence-ops.md", content="## 8.3\\n...")
6. Respond: "File arc42/08-part1b-persistence-ops.md written successfully."

{system_summary}

Write to: arc42/08-part1b-persistence-ops.md. 6-8 pages. REAL data. No placeholders.
"""
)

CH08_PART2_PATTERNS = (
    TOOL_INSTRUCTION
    + """
Create arc42 Chapter 8 Part 2: Architecture Patterns and Conventions.

## REQUIRED SECTIONS (do NOT skip any):
### 8.6 Dependency Injection Patterns
- Constructor injection conventions
- Bean lifecycle management
- Component scanning strategy
- Profile-based configuration
### 8.7 Caching Strategy
- Cache levels (application, HTTP, database)
- Cache invalidation patterns
- Cacheable operations
### 8.8 Validation Concept
- Bean validation (JSR-380)
- Custom validators
- Validation at each layer (controller, service, entity)
### 8.9 Configuration Management
- Property sources and profiles (application.yml, application-PROFILE.yml)
- Environment-specific configuration
- Externalized configuration
- Feature toggles
### 8.10 Testing Concept
- Test pyramid strategy
- Unit test patterns (Mockito, JUnit)
- Integration test setup (@SpringBootTest)
- Test data management
### 8.11 Internationalization
- i18n support (if detected)
- Message bundles, locale handling

## EXECUTION EXAMPLE (follow this pattern):
1. get_statistics() -> get system overview
2. get_architecture_summary() -> get patterns
3. search_components(query="config") -> find configuration components
4. search_components(query="cache") -> find caching components
5. rag_query(query="configuration properties profile") -> config details
6. rag_query(query="validation Bean JSR") -> validation patterns
7. rag_query(query="test junit mockito SpringBootTest") -> testing patterns
8. rag_query(query="dependency injection constructor autowired") -> DI patterns
9. doc_writer(file_path="arc42/08-part2-patterns.md", content="## 8.6 Dependency Injection Patterns\\n...")
10. Respond: "File arc42/08-part2-patterns.md written successfully."

Summary data:
{system_summary}

Write to file: arc42/08-part2-patterns.md using doc_writer tool.
Write 8-10 pages with REAL data from tools. No placeholders.
"""
)

# =============================================================================
# Chapter 9: Architecture Decisions
# =============================================================================

CH09_DECISIONS = (
    TOOL_INSTRUCTION
    + """
Create the COMPLETE arc42 Chapter 9: Architecture Decisions.

## REQUIRED SECTIONS (do NOT skip any):
### 9.1 Decision Log Overview
- Summary table of ALL ADRs with status and date
### 9.2 Architecture Decision Records
- Write at least 10 ADRs, each with: Status, Context, Decision, Rationale, Alternatives, Consequences
- Cover: Architecture Style, Backend Framework, Database, Frontend, API Design, Authentication,
  Deployment Strategy, Caching, Logging Framework, Testing Strategy

## EXECUTION EXAMPLE (follow this pattern):
1. get_architecture_summary() -> get architecture style, patterns
2. query_architecture_facts(category="containers") -> get technology choices
3. get_statistics() -> get system metrics
4. get_endpoints() -> get API design decisions
5. rag_query(query="architecture decision spring framework") -> framework decisions
6. rag_query(query="database configuration persistence") -> DB decisions
7. doc_writer(file_path="arc42/09-decisions.md", content="# 09 - Architecture Decisions\\n...")
8. Respond: "File arc42/09-decisions.md written successfully."

Summary data:
{system_summary}

Write to file: arc42/09-decisions.md using doc_writer tool.
Write 8-12 pages with REAL data from tools. No placeholders.
"""
)

# =============================================================================
# Chapter 10: Quality Requirements
# =============================================================================

CH10_QUALITY = (
    TOOL_INSTRUCTION
    + """
Create the COMPLETE arc42 Chapter 10: Quality Requirements.

## REQUIRED SECTIONS (do NOT skip any):
### 10.1 Quality Tree
- Quality attribute hierarchy (text-based tree diagram)
- ISO 25010 mapping for each quality attribute
### 10.2 Quality Scenarios
- At least 15 quality scenarios in table format
- Cover: Performance, Security, Maintainability, Reliability, Usability, Portability
- For EACH: | ID | Attribute | Stimulus | Response | Measure | Priority |
### 10.3 Quality Metrics
- Metrics table: | Metric | Target | Measurement Method | Current |
- Code quality metrics, performance targets, security requirements

## EXECUTION EXAMPLE (follow this pattern):
1. get_architecture_summary() -> get quality attributes, patterns
2. get_statistics() -> get system metrics (component counts, relations)
3. list_components_by_stereotype(stereotype="controller") -> count for metrics
4. query_architecture_facts(category="relations") -> coupling metrics
5. rag_query(query="quality performance test") -> quality indicators
6. doc_writer(file_path="arc42/10-quality.md", content="# 10 - Quality Requirements\\n...")
7. Respond: "File arc42/10-quality.md written successfully."

Summary data:
{system_summary}

Write to file: arc42/10-quality.md using doc_writer tool.
Write 8-10 pages with REAL data from tools. No placeholders.
"""
)

# =============================================================================
# Chapter 11: Risks and Technical Debt
# =============================================================================

CH11_RISKS = (
    TOOL_INSTRUCTION
    + """
Create the COMPLETE arc42 Chapter 11: Risks and Technical Debt.

## REQUIRED SECTIONS (do NOT skip any):
### 11.1 Risk Overview
- Risk heat map (text-based) and summary table
### 11.2 Architecture Risks
- At least 8 risks with: | ID | Risk | Severity | Probability | Impact | Mitigation |
- Categories: structural, technology, organizational, operational
### 11.3 Technical Debt Inventory
- At least 10 debt items: | ID | Debt Item | Category | Impact | Effort to Fix |
- Categories: code quality, missing tests, outdated dependencies, architectural violations
### 11.4 Mitigation Roadmap
- Prioritized action plan: | Phase | Action | Priority | Timeline | Effort |
- Quick wins vs. strategic improvements

## EXECUTION EXAMPLE (follow this pattern):
1. get_architecture_summary() -> get architecture assessment and quality
2. get_statistics() -> get system complexity metrics
3. query_architecture_facts(category="relations") -> get dependency risks
4. list_components_by_stereotype(stereotype="component") -> generic components (potential debt)
5. rag_query(query="deprecated legacy TODO FIXME") -> technical debt indicators
6. rag_query(query="coupling dependency circular") -> coupling risks
7. doc_writer(file_path="arc42/11-risks.md", content="# 11 - Risks and Technical Debt\\n...")
8. Respond: "File arc42/11-risks.md written successfully."

Summary data:
{system_summary}

Write to file: arc42/11-risks.md using doc_writer tool.
Write 8-10 pages with REAL data from tools. No placeholders.
"""
)

# =============================================================================
# Chapter 12: Glossary
# =============================================================================

CH12_GLOSSARY = (
    TOOL_INSTRUCTION
    + """
Create the COMPLETE arc42 Chapter 12: Glossary.

## REQUIRED SECTIONS (do NOT skip any):
### 12.1 Business Terms
- ALL domain-specific business terms derived from entity and service names
- Table: | Term | Definition | Related Components |
### 12.2 Technical Terms
- Framework, pattern, and technology terms
- Table: | Term | Definition | Context |
### 12.3 Abbreviations
- ALL abbreviations found in code and configuration
- Table: | Abbreviation | Full Form | Context |
### 12.4 Architecture Patterns
- All detected architecture and design patterns
- Table: | Pattern | Definition | Where Used | Benefit |

## EXECUTION EXAMPLE (follow this pattern):
1. get_statistics() -> get system terminology
2. list_components_by_stereotype(stereotype="entity") -> get domain terms
3. list_components_by_stereotype(stereotype="service") -> get business terms
4. get_architecture_summary() -> get architecture terms
5. get_endpoints() -> get API terms
6. rag_query(query="domain model business terminology") -> domain knowledge
7. doc_writer(file_path="arc42/12-glossary.md", content="# 12 - Glossary\\n...")
8. Respond: "File arc42/12-glossary.md written successfully."

Summary data:
{system_summary}

Write to file: arc42/12-glossary.md using doc_writer tool.
Write 6-8 pages. Include ALL domain-specific terms from the system. No placeholders.
"""
)

# =============================================================================
# Quality Gate
# =============================================================================

QUALITY_GATE_DESCRIPTION = """
Quality review of all arc42 chapters.
Generated on: {current_date}

READ all chapter files using safe_file_read tool and validate:
1. knowledge/document/arc42/01-introduction.md
2. knowledge/document/arc42/02-constraints.md
3. knowledge/document/arc42/03-context.md
4. knowledge/document/arc42/04-solution-strategy.md
5. knowledge/document/arc42/05-building-blocks.md
6. knowledge/document/arc42/06-runtime-view.md
7. knowledge/document/arc42/07-deployment.md
8. knowledge/document/arc42/08-crosscutting.md
9. knowledge/document/arc42/09-decisions.md
10. knowledge/document/arc42/10-quality.md
11. knowledge/document/arc42/11-risks.md
12. knowledge/document/arc42/12-glossary.md

Validate:
- All 12 chapters complete
- Each chapter has expected page count
- Content based on REAL facts
- No placeholder text

Write quality report to: quality/arc42-report.md using doc_writer tool.
"""
