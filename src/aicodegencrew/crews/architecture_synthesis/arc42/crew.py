"""
Arc42 Crew - Phase 3b: Mini-Crews Pattern
==========================================
Creates all 12 arc42 chapters + Quality Gate

Architecture Fix:
- OLD: 1 Crew with 44 sequential tasks -> Context overflow after ~10 tasks
- NEW: 18 Mini-Crews (1 task each) -> Fresh context per chapter/sub-chapter

Chapters 5, 6, and 8 are split into sub-crews for maximum output quality:
- Chapter 5: 4 sub-crews (overview, controllers, services, domain)
- Chapter 6: 2 sub-crews (API flows, business flows)
- Chapter 8: 2 sub-crews (technical concepts, patterns)

Each Mini-Crew starts with a fresh LLM context window.
Data is passed via template variables (summaries), not inter-task context.
"""

import logging
from pathlib import Path

from crewai import Task

from ..base_crew import TOOL_INSTRUCTION, MiniCrewBase
from ..tools import ChunkedWriterTool

logger = logging.getLogger(__name__)


# =============================================================================
# AGENT CONFIG - Python dict instead of config/agents.yaml
# =============================================================================

ARC42_AGENT_CONFIG = {
    "role": "Senior Software Architect - SEAGuide Documentation Expert",
    "goal": "Create comprehensive 100-120 page arc42 documentation following SEAGuide standards",
    "backstory": (
        "You are a SENIOR SOFTWARE ARCHITECT with expertise in creating professional\n"
        "architecture documentation following Capgemini's SEAGuide standard.\n"
        "\n"
        "## SEAGuide QUALITY STANDARDS\n"
        "You MUST follow these principles from SEAGuide:\n"
        "\n"
        "1. GRAPHICS FIRST\n"
        "   - Use diagrams as primary communication\n"
        "   - Don't repeat in text what's visible on diagrams\n"
        "   - Clean diagrams with legends\n"
        "   - Understandability over completeness\n"
        "\n"
        "2. COMPREHENSIVE COVERAGE\n"
        "   - Each chapter should be 8-12 pages\n"
        "   - Total documentation 100-120 pages\n"
        "   - Include tables, examples, diagrams\n"
        "   - Real data from facts, not generic text\n"
        "\n"
        "3. ARCHITECTURAL DECOMPOSITION\n"
        "   - A-Architecture (Functional view): Business building blocks\n"
        "   - T-Architecture (Technical view): Technical components\n"
        "   - Apply DDD concepts (Bounded Contexts, Subdomains)\n"
        "\n"
        "4. PATTERN-BASED DOCUMENTATION\n"
        "   - Building Block patterns for structure\n"
        "   - Runtime patterns for behavior\n"
        "   - Deployment patterns for infrastructure\n"
        "\n"
        "## DATA SOURCES\n"
        "- architecture_facts.json: EXACT component names, counts, relations\n"
        "- analyzed_architecture.json: Architecture style, patterns, quality, risks\n"
        "- SEAGuide.txt: Query via seaguide_query tool for documentation standards\n"
        "\n"
        "## TOOL USAGE (use these tools actively!)\n"
        '1. seaguide_query(query="arc42 building block view") - Get Arc42 patterns from SEAGuide\n'
        '2. seaguide_query(query="runtime view sequence") - Get runtime documentation patterns\n'
        '3. list_components_by_stereotype(stereotype="controller") - Get component lists\n'
        '4. query_architecture_facts(category="containers") - Get container details\n'
        "5. doc_writer(path, content) - Write documentation files\n"
        "\n"
        "IMPORTANT: Before writing each chapter, query SEAGuide for the relevant pattern!\n"
        "Example: Before writing Chapter 5 (Building Blocks), run:\n"
        '  seaguide_query(query="building block view patterns")\n'
        "\n"
        "## YOUR APPROACH\n"
        "1. seaguide_query for relevant documentation patterns FIRST\n"
        "2. Read analyzed_architecture.json for high-level context\n"
        "3. Query architecture_facts.json for specific details\n"
        "4. Write comprehensive chapters with tables, diagrams, examples\n"
        "\n"
        "## OUTPUT QUALITY RULES\n"
        "- Each chapter 8-12 pages minimum\n"
        "- Use tables for structured data (components, decisions, risks)\n"
        "- Include text-based diagrams where appropriate\n"
        "- Reference specific component names from facts\n"
        '- Never use placeholder text like "[to be determined]"\n'
        "- Document rationale (WHY decisions were made)\n"
        "- Include quality scenarios with measurable targets\n"
        "- Write in professional English\n"
        "\n"
        "## FORMATTING RULES\n"
        "- Use Markdown with proper headers (##, ###)\n"
        "- Use tables for inventories (| Column | Column |)\n"
        "- Use code blocks for diagrams (```)\n"
        "- Use bold for emphasis, not ALL CAPS"
    ),
}


# =============================================================================
# TASK DESCRIPTIONS - Python constants instead of tasks.yaml
# =============================================================================

CH01_INTRODUCTION = (
    TOOL_INSTRUCTION
    + """
Create the COMPLETE arc42 Chapter 1: Introduction and Goals (8-12 pages).

## REQUIRED SECTIONS (do NOT skip any):
### 1.1 Requirements Overview (3 pages)
- Full system description with business domain classification
- Primary business value and target users
- Feature inventory table with ALL business capabilities (derive from controller/service names)
- System statistics table (components, controllers, services, repos, entities, endpoints)
### 1.2 Quality Goals (2 pages)
- Quality goal table with measurable targets for each attribute
- At least 5 goals: Maintainability, Testability, Security, Performance, Scalability
- For EACH: Priority, Rationale, How Achieved (which patterns), Measurement
### 1.3 Stakeholders (2 pages)
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

CH02_CONSTRAINTS = (
    TOOL_INSTRUCTION
    + """
Create the COMPLETE arc42 Chapter 2: Architecture Constraints (8-10 pages).

## REQUIRED SECTIONS (do NOT skip any):
### 2.1 Technical Constraints (3 pages)
- Constraint table for: Programming Language, Framework, Database, Infrastructure, Security
- For EACH: Constraint name, Background, Impact on architecture, Consequences
### 2.2 Organizational Constraints (2 pages)
- Team structure, development process, deployment frequency
- Compliance and regulatory requirements
### 2.3 Convention Constraints (2 pages)
- Naming conventions (packages, classes, methods, REST endpoints)
- Code style and formatting rules
- API design conventions (REST, versioning)

## EXECUTION EXAMPLE (follow this pattern):
1. get_statistics() -> get system overview
2. get_architecture_summary() -> get architecture decisions and patterns
3. query_architecture_facts(category="containers") -> get container technologies
4. rag_query(query="naming convention package structure") -> naming patterns
5. rag_query(query="configuration properties spring") -> framework constraints
6. doc_writer(file_path="arc42/02-constraints.md", content="# 02 - Architecture Constraints\\n...")
7. Respond: "File arc42/02-constraints.md written successfully."

Summary data:
{system_summary}
{containers_summary}

Write to file: arc42/02-constraints.md using doc_writer tool.
Write 8-10 pages with REAL data from tools. No placeholders.
"""
)

CH03_CONTEXT = (
    TOOL_INSTRUCTION
    + """
Create the COMPLETE arc42 Chapter 3: System Scope and Context (8-12 pages).

## REQUIRED SECTIONS (do NOT skip any):
### 3.1 Business Context (3 pages)
- Context diagram (text-based ASCII showing system + external actors)
- External actors table: | Actor | Role | Interactions | Volume |
- External systems table: | System | Purpose | Protocol | Data Exchanged |
### 3.2 Technical Context (3 pages)
- Technical interfaces: REST API surface, database connections, message channels
- Protocols and formats table
- Complete API endpoint inventory (summarized by domain)
### 3.3 External Dependencies (2 pages)
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

CH04_SOLUTION_STRATEGY = (
    TOOL_INSTRUCTION
    + """
Create the COMPLETE arc42 Chapter 4: Solution Strategy (8-12 pages).

## REQUIRED SECTIONS (do NOT skip any):
### 4.1 Technology Decisions (4 pages)
- ADR-lite table for EACH major technology: Backend Framework, Database, Frontend, Build Tool,
  Container Technology, Security Framework, API Design
- For EACH: Context, Decision, Rationale, Alternatives, Consequences
### 4.2 Architecture Patterns (3 pages)
- Macro architecture: pattern name, layer responsibilities, dependency rules
- Applied patterns table: | Pattern | Purpose | Where Applied | Benefit |
- At least 8 patterns from the codebase
### 4.3 Achieving Quality Goals (2 pages)
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

# Chapter 5 is split into 4 sub-crews to avoid truncation.
# Each sub-crew writes to a separate part-file. After all complete,
# Arc42Crew.run() merges them into the final 05-building-blocks.md.

CH05_PART1_OVERVIEW = (
    TOOL_INSTRUCTION
    + """
Create arc42 Chapter 5 PART 1: Overview and System Whitebox (6-8 pages).

## REQUIRED SECTIONS (do NOT skip any):
### 5.1 Overview (2 pages)
- A-Architecture (Functional view): business capabilities mapped to layers
- T-Architecture (Technical view): containers hosting building blocks
- Building Block Hierarchy with total counts per stereotype
### 5.2 Whitebox Overall System (Level 1) (4-6 pages)
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

CH05_PART2_CONTROLLERS = (
    TOOL_INSTRUCTION
    + """
Create arc42 Chapter 5 PART 2: Presentation Layer / Controllers (8-10 pages).

## REQUIRED SECTIONS (do NOT skip any):
### 5.3.1 Layer Overview (1 page)
- Controller layer responsibilities and patterns
### 5.3.2 Controller Inventory (3-4 pages)
- COMPLETE table of ALL controllers: | # | Controller | Package | Endpoints | Description |
### 5.3.3 API Patterns (1-2 pages)
- REST conventions, URL naming, HTTP methods, response formats
### 5.3.4 Key Controllers Deep Dive — TOP 5 (3-4 pages)
- For EACH: All endpoints, operations, delegation to services, validation, security

## EXECUTION EXAMPLE (follow this pattern):
1. list_components_by_stereotype(stereotype="controller") -> get ALL controllers
2. get_endpoints() -> get ALL REST API endpoints
3. get_statistics() -> get component counts
4. query_architecture_facts(category="relations") -> get controller dependencies
5. rag_query(query="REST controller endpoint mapping") -> API patterns
6. doc_writer(file_path="arc42/05-part2-controllers.md", content="## 5.3 Presentation Layer\\n...")
7. Respond: "File arc42/05-part2-controllers.md written successfully."

Summary data:
{system_summary}

Write to file: arc42/05-part2-controllers.md using doc_writer tool.
Write 8-10 pages with REAL data. COMPLETE controller inventory. No placeholders.
"""
)

CH05_PART3_SERVICES = (
    TOOL_INSTRUCTION
    + """
Create arc42 Chapter 5 PART 3: Business Layer / Services (8-10 pages).

## REQUIRED SECTIONS (do NOT skip any):
### 5.4.1 Layer Overview (1 page)
- Service layer responsibilities, bounded contexts, business rules
### 5.4.2 Service Inventory (3-4 pages)
- COMPLETE table of ALL services: | # | Service | Package | Interface? | Description |
### 5.4.3 Service Patterns (1-2 pages)
- Interface/Implementation pattern, transaction boundaries, service composition
### 5.4.4 Key Services Deep Dive — TOP 5 (2-3 pages)
- For EACH: Core responsibilities, transaction management, dependencies, events
### 5.4.5 Service Interactions (1 page)
- Key service-to-service dependencies with direction

## EXECUTION EXAMPLE (follow this pattern):
1. list_components_by_stereotype(stereotype="service") -> get ALL services
2. get_architecture_summary() -> get architecture patterns
3. get_statistics() -> get component counts
4. query_architecture_facts(category="relations") -> get service dependencies
5. rag_query(query="service implementation transaction") -> service patterns
6. doc_writer(file_path="arc42/05-part3-services.md", content="## 5.4 Business Layer\\n...")
7. Respond: "File arc42/05-part3-services.md written successfully."

Summary data:
{system_summary}

Write to file: arc42/05-part3-services.md using doc_writer tool.
Write 8-10 pages with REAL data. COMPLETE service inventory. No placeholders.
"""
)

CH05_PART4_DOMAIN = (
    TOOL_INSTRUCTION
    + """
Create arc42 Chapter 5 PART 4: Domain Layer, Persistence Layer, Dependencies (8-10 pages).

## REQUIRED SECTIONS (do NOT skip any):
### 5.5 Domain Layer — Entities (3-4 pages)
- Layer overview: JPA entities, aggregate roots, value objects
- COMPLETE entity inventory: | # | Entity | Package | Key Attributes | Description |
- Key entities deep dive (TOP 5): attributes, relationships, lifecycle, validation
### 5.6 Persistence Layer — Repositories (2-3 pages)
- Layer overview: data access patterns
- COMPLETE repository inventory: | # | Repository | Entity | Custom Queries | Description |
- Data access patterns (Spring Data JPA, custom queries, specifications)
### 5.7 Component Dependencies (2-3 pages)
- Layer dependency rules with direction
- Dependency matrix: | From/To | Controller | Service | Repository | Entity |
- Dependency statistics and coupling analysis

## EXECUTION EXAMPLE (follow this pattern):
1. list_components_by_stereotype(stereotype="entity") -> get ALL entities
2. list_components_by_stereotype(stereotype="repository") -> get ALL repositories
3. query_architecture_facts(category="relations") -> get dependency data
4. get_statistics() -> get component counts
5. rag_query(query="entity JPA relationship mapping") -> entity details
6. rag_query(query="repository custom query specification") -> repo patterns
7. doc_writer(file_path="arc42/05-part4-domain.md", content="## 5.5 Domain Layer\\n...")
8. Respond: "File arc42/05-part4-domain.md written successfully."

Summary data:
{system_summary}

Write to file: arc42/05-part4-domain.md using doc_writer tool.
Write 8-10 pages with REAL data. COMPLETE inventories. No placeholders.
"""
)

CH06_PART1_API_FLOWS = (
    TOOL_INSTRUCTION
    + """
Create arc42 Chapter 6 Part 1: API Runtime Flows (8-10 pages).

## REQUIRED SECTIONS (do NOT skip any):
### 6.1 Runtime View Overview (1 page)
- Purpose of runtime documentation
- How to read sequence diagrams
### 6.2 Authentication Flow (2 pages)
- Login sequence with ALL components involved
- Token refresh / session management
### 6.3 CRUD Operation Flows (3 pages)
- CREATE: Full request flow from client to database and back
- READ: Single item + list with pagination
- UPDATE: Optimistic locking / versioning
- DELETE: Cascade behavior
### 6.4 REST API Request Lifecycle (2 pages)
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
Create arc42 Chapter 6 Part 2: Business Process Flows (8-10 pages).

## REQUIRED SECTIONS (do NOT skip any):
### 6.5 Core Business Workflows (3 pages)
- Primary business process end-to-end (e.g., deed entry creation workflow)
- State transitions with component responsibilities
- Workflow orchestration pattern
### 6.6 Complex Business Scenarios (3 pages)
- Multi-step approval/validation flows
- Cross-service transactions
- Batch processing flows
### 6.7 Error and Recovery Scenarios (2 pages)
- Exception propagation through layers
- Compensation/rollback patterns
- Retry strategies
### 6.8 Asynchronous Patterns (1-2 pages)
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

CH07_DEPLOYMENT = (
    TOOL_INSTRUCTION
    + """
Create the COMPLETE arc42 Chapter 7: Deployment View (8-10 pages).

## REQUIRED SECTIONS (do NOT skip any):
### 7.1 Infrastructure Overview (2 pages)
- Deployment diagram (text-based ASCII)
- Infrastructure summary
### 7.2 Infrastructure Nodes (2 pages)
- Node table: | Node | Type | Specification | Purpose |
- Container-to-node mapping
### 7.3 Container Deployment (2 pages)
- Docker configuration details
- Container orchestration (Kubernetes/Docker Compose)
- Build pipeline (Maven/Gradle -> Docker image)
### 7.4 Environment Configuration (1-2 pages)
- Development, Test, Staging, Production environments
- Environment-specific settings
### 7.5 Network Topology (1 page)
- Network zones and firewall rules
- Load balancing strategy
### 7.6 Scaling Strategy (1 page)
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

CH08_PART1_TECHNICAL = (
    TOOL_INSTRUCTION
    + """
Create arc42 Chapter 8 Part 1: Technical Crosscutting Concepts (8-10 pages).

## REQUIRED SECTIONS (do NOT skip any):
### 8.1 Domain Model (2 pages)
- Core domain concepts with entity relationship diagram (text-based)
- Entity inventory table: | Entity | Key Attributes | Relationships |
- Aggregate boundaries
### 8.2 Security Concept (2 pages)
- Authentication mechanism (Spring Security, JWT, OAuth2, etc.)
- Authorization model (roles, permissions)
- Security annotations and filters
- CSRF, XSS, injection prevention
### 8.3 Persistence Concept (2 pages)
- ORM strategy (JPA/Hibernate configuration)
- Transaction management (@Transactional boundaries)
- Connection pooling
- Database migration strategy (Flyway/Liquibase)
### 8.4 Error Handling and Exception Strategy (1-2 pages)
- Exception hierarchy (custom exceptions, base classes)
- Global exception handler (@ControllerAdvice)
- Error response format (JSON structure)
- HTTP status code mapping
### 8.5 Logging and Monitoring (1-2 pages)
- Logging framework and configuration
- Log levels strategy per layer
- Structured logging format
- Health checks and metrics endpoints

## EXECUTION EXAMPLE (follow this pattern):
1. get_architecture_summary() -> get architecture patterns
2. list_components_by_stereotype(stereotype="entity") -> get ALL entities
3. search_components(query="security") -> find security components
4. search_components(query="exception") -> find error handling
5. rag_query(query="security authentication authorization") -> security details
6. rag_query(query="logging slf4j logback") -> logging config
7. rag_query(query="exception handling ControllerAdvice") -> error handling
8. rag_query(query="transaction management Transactional") -> persistence
9. doc_writer(file_path="arc42/08-part1-technical.md", content="# 08 - Crosscutting Concepts\\n\\n## 8.1 Domain Model\\n...")
10. Respond: "File arc42/08-part1-technical.md written successfully."

Summary data:
{system_summary}

Write to file: arc42/08-part1-technical.md using doc_writer tool.
Write 8-10 pages with REAL data from tools. No placeholders.
"""
)

CH08_PART2_PATTERNS = (
    TOOL_INSTRUCTION
    + """
Create arc42 Chapter 8 Part 2: Architecture Patterns and Conventions (8-10 pages).

## REQUIRED SECTIONS (do NOT skip any):
### 8.6 Dependency Injection Patterns (2 pages)
- Constructor injection conventions
- Bean lifecycle management
- Component scanning strategy
- Profile-based configuration
### 8.7 Caching Strategy (1-2 pages)
- Cache levels (application, HTTP, database)
- Cache invalidation patterns
- Cacheable operations
### 8.8 Validation Concept (1-2 pages)
- Bean validation (JSR-380)
- Custom validators
- Validation at each layer (controller, service, entity)
### 8.9 Configuration Management (2 pages)
- Property sources and profiles (application.yml, application-{profile}.yml)
- Environment-specific configuration
- Externalized configuration
- Feature toggles
### 8.10 Testing Concept (2 pages)
- Test pyramid strategy
- Unit test patterns (Mockito, JUnit)
- Integration test setup (@SpringBootTest)
- Test data management
### 8.11 Internationalization (1 page)
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

CH09_DECISIONS = (
    TOOL_INSTRUCTION
    + """
Create the COMPLETE arc42 Chapter 9: Architecture Decisions (8-12 pages).

## REQUIRED SECTIONS (do NOT skip any):
### 9.1 Decision Log Overview (1 page)
- Summary table of ALL ADRs with status and date
### 9.2 Architecture Decision Records (7-11 pages)
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

CH10_QUALITY = (
    TOOL_INSTRUCTION
    + """
Create the COMPLETE arc42 Chapter 10: Quality Requirements (8-10 pages).

## REQUIRED SECTIONS (do NOT skip any):
### 10.1 Quality Tree (2 pages)
- Quality attribute hierarchy (text-based tree diagram)
- ISO 25010 mapping for each quality attribute
### 10.2 Quality Scenarios (4-5 pages)
- At least 15 quality scenarios in table format
- Cover: Performance, Security, Maintainability, Reliability, Usability, Portability
- For EACH: | ID | Attribute | Stimulus | Response | Measure | Priority |
### 10.3 Quality Metrics (2-3 pages)
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

CH11_RISKS = (
    TOOL_INSTRUCTION
    + """
Create the COMPLETE arc42 Chapter 11: Risks and Technical Debt (8-10 pages).

## REQUIRED SECTIONS (do NOT skip any):
### 11.1 Risk Overview (1 page)
- Risk heat map (text-based) and summary table
### 11.2 Architecture Risks (3-4 pages)
- At least 8 risks with: | ID | Risk | Severity | Probability | Impact | Mitigation |
- Categories: structural, technology, organizational, operational
### 11.3 Technical Debt Inventory (2-3 pages)
- At least 10 debt items: | ID | Debt Item | Category | Impact | Effort to Fix |
- Categories: code quality, missing tests, outdated dependencies, architectural violations
### 11.4 Mitigation Roadmap (2 pages)
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

CH12_GLOSSARY = (
    TOOL_INSTRUCTION
    + """
Create the COMPLETE arc42 Chapter 12: Glossary (6-8 pages).

## REQUIRED SECTIONS (do NOT skip any):
### 12.1 Business Terms (2-3 pages)
- ALL domain-specific business terms derived from entity and service names
- Table: | Term | Definition | Related Components |
### 12.2 Technical Terms (2 pages)
- Framework, pattern, and technology terms
- Table: | Term | Definition | Context |
### 12.3 Abbreviations (1 page)
- ALL abbreviations found in code and configuration
- Table: | Abbreviation | Full Form | Context |
### 12.4 Architecture Patterns (1-2 pages)
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

QUALITY_GATE_DESCRIPTION = """
Quality review of all arc42 chapters.

READ all chapter files using safe_file_read tool and validate:
1. knowledge/architecture/arc42/01-introduction.md
2. knowledge/architecture/arc42/02-constraints.md
3. knowledge/architecture/arc42/03-context.md
4. knowledge/architecture/arc42/04-solution-strategy.md
5. knowledge/architecture/arc42/05-building-blocks.md
6. knowledge/architecture/arc42/06-runtime-view.md
7. knowledge/architecture/arc42/07-deployment.md
8. knowledge/architecture/arc42/08-crosscutting.md
9. knowledge/architecture/arc42/09-decisions.md
10. knowledge/architecture/arc42/10-quality.md
11. knowledge/architecture/arc42/11-risks.md
12. knowledge/architecture/arc42/12-glossary.md

Validate:
- All 12 chapters complete
- Each chapter has expected page count
- Content based on REAL facts
- No placeholder text

Write quality report to: quality/arc42-report.md using doc_writer tool.
"""


class Arc42Crew(MiniCrewBase):
    """
    Arc42 Crew - Creates all 12 arc42 chapters using Mini-Crews pattern.

    Each chapter group runs in its own Mini-Crew with fresh LLM context.
    This prevents context overflow that occurred with 44 tasks in 1 Crew.

    Mini-Crews (1 task each for reliability with on-prem models):
    1-8. Chapters 1-5 (ch05 split into 4 sub-crews)
    9-10. Chapter 6 (runtime view split into 2 sub-crews)
    11. Chapter 7 (deployment)
    12-13. Chapter 8 (crosscutting split into 2 sub-crews)
    14-17. Chapters 9-12
    18. Quality Gate (validation)

    Total: 18 mini-crews (was 16 before ch06/ch08 splitting)
    """

    @property
    def crew_name(self) -> str:
        return "Arc42"

    @property
    def agent_config(self) -> dict[str, str]:
        return ARC42_AGENT_CONFIG

    def _get_extra_tools(self) -> list:
        """Arc42 needs ChunkedWriterTool for large chapters."""
        return [ChunkedWriterTool()]

    def _summarize_facts(self) -> dict[str, str]:
        """Create summaries combining Phase 1 facts and Phase 2 analysis."""
        facts = self.facts
        analysis = self.analysis

        system_info = facts.get("system", {})
        system_name = system_info.get("name", "Unknown System")

        arch_info = analysis.get("architecture", {})
        patterns = analysis.get("patterns", [])

        containers = facts.get("containers", [])
        components = facts.get("components", [])
        interfaces = facts.get("interfaces", [])
        relations = facts.get("relations", [])

        tech_stack = sorted({c.get("technology", "Unknown") for c in containers if c.get("technology")})

        by_stereotype: dict[str, int] = {}
        for comp in components:
            stereo = comp.get("stereotype", "unknown")
            by_stereotype[stereo] = by_stereotype.get(stereo, 0) + 1

        arch_style = arch_info.get("primary_style", "UNKNOWN - use tools to discover")

        system_summary = f"""SYSTEM: {system_name}

ARCHITECTURE (from Phase 2 analysis):
- Primary Style: {arch_style}
- Patterns: {", ".join([p.get("name", str(p)) if isinstance(p, dict) else str(p) for p in patterns]) if patterns else "Use tools to discover"}

STATISTICS (from Phase 1 facts):
- Containers: {len(containers)}
- Components: {len(components)}
- Interfaces: {len(interfaces)}
- Relations: {len(relations)}

TECHNOLOGIES:
{chr(10).join([f"- {t}" for t in tech_stack]) if tech_stack else "- Use tools to discover"}

COMPONENT COUNTS BY STEREOTYPE:
{chr(10).join([f"- {k}: {v}" for k, v in sorted(by_stereotype.items())]) if by_stereotype else "- Use tools to discover"}

IMPORTANT: Use MCP tools (get_statistics, get_architecture_summary, list_components_by_stereotype) to get REAL data!"""

        container_lines = [f"- {c.get('name', '?')}: {c.get('technology', '?')}" for c in containers]

        containers_summary = f"""CONTAINERS:
{chr(10).join(container_lines) if container_lines else "- Use query_architecture_facts to discover"}"""

        components_summary = "Use list_components_by_stereotype tool to query components by type."
        interfaces_summary = (
            f"Total interfaces: {len(interfaces)}. Use query_architecture_facts with category='interfaces' for details."
        )
        relations_summary = (
            f"Total relations: {len(relations)}. Use query_architecture_facts with category='relations' for details."
        )
        building_blocks_data = (
            "Use list_components_by_stereotype for each layer (controller, service, repository, entity)."
        )

        return {
            "system_name": system_name,
            "system_summary": self.escape_braces(system_summary),
            "containers_summary": self.escape_braces(containers_summary),
            "components_summary": self.escape_braces(components_summary),
            "relations_summary": self.escape_braces(relations_summary),
            "interfaces_summary": self.escape_braces(interfaces_summary),
            "building_blocks_data": self.escape_braces(building_blocks_data),
        }

    # -------------------------------------------------------------------------
    # MERGE BUILDING BLOCKS
    # -------------------------------------------------------------------------

    @staticmethod
    def _merge_building_blocks() -> None:
        """Merge 4 building-blocks part files into 05-building-blocks.md."""
        base = Path("knowledge/architecture/arc42")
        parts = [
            "05-part1-overview.md",
            "05-part2-controllers.md",
            "05-part3-services.md",
            "05-part4-domain.md",
        ]

        merged_lines: list[str] = []
        for part_file in parts:
            path = base / part_file
            if path.exists() and path.stat().st_size > 100:
                content = path.read_text(encoding="utf-8").strip()
                # Remove duplicate chapter title from parts 2-4
                if merged_lines and content.startswith("# 05"):
                    lines = content.split("\n", 1)
                    content = lines[1].strip() if len(lines) > 1 else content
                merged_lines.append(content)
                merged_lines.append("")  # blank separator
                logger.info(f"[Arc42] Merged {part_file} ({len(content)} chars)")
            else:
                logger.warning(f"[Arc42] Part file missing: {part_file}")

        if merged_lines:
            merged = "\n".join(merged_lines)
            target = base / "05-building-blocks.md"
            target.write_text(merged, encoding="utf-8")
            logger.info(f"[Arc42] Merged building-blocks: {len(merged)} chars -> {target}")

    # -------------------------------------------------------------------------
    # MERGE RUNTIME VIEW
    # -------------------------------------------------------------------------

    @staticmethod
    def _merge_runtime_view() -> None:
        """Merge 2 runtime-view part files into 06-runtime-view.md."""
        base = Path("knowledge/architecture/arc42")
        parts = [
            "06-part1-api-flows.md",
            "06-part2-business-flows.md",
        ]

        merged_lines: list[str] = []
        for part_file in parts:
            path = base / part_file
            if path.exists() and path.stat().st_size > 100:
                content = path.read_text(encoding="utf-8").strip()
                # Remove duplicate chapter title from part 2
                if merged_lines and content.startswith("# 06"):
                    lines = content.split("\n", 1)
                    content = lines[1].strip() if len(lines) > 1 else content
                merged_lines.append(content)
                merged_lines.append("")  # blank separator
                logger.info(f"[Arc42] Merged {part_file} ({len(content)} chars)")
            else:
                logger.warning(f"[Arc42] Part file missing: {part_file}")

        if merged_lines:
            merged = "\n".join(merged_lines)
            target = base / "06-runtime-view.md"
            target.write_text(merged, encoding="utf-8")
            logger.info(f"[Arc42] Merged runtime-view: {len(merged)} chars -> {target}")

    # -------------------------------------------------------------------------
    # MERGE CROSSCUTTING
    # -------------------------------------------------------------------------

    @staticmethod
    def _merge_crosscutting() -> None:
        """Merge 2 crosscutting part files into 08-crosscutting.md."""
        base = Path("knowledge/architecture/arc42")
        parts = [
            "08-part1-technical.md",
            "08-part2-patterns.md",
        ]

        merged_lines: list[str] = []
        for part_file in parts:
            path = base / part_file
            if path.exists() and path.stat().st_size > 100:
                content = path.read_text(encoding="utf-8").strip()
                # Remove duplicate chapter title from part 2
                if merged_lines and content.startswith("# 08"):
                    lines = content.split("\n", 1)
                    content = lines[1].strip() if len(lines) > 1 else content
                merged_lines.append(content)
                merged_lines.append("")  # blank separator
                logger.info(f"[Arc42] Merged {part_file} ({len(content)} chars)")
            else:
                logger.warning(f"[Arc42] Part file missing: {part_file}")

        if merged_lines:
            merged = "\n".join(merged_lines)
            target = base / "08-crosscutting.md"
            target.write_text(merged, encoding="utf-8")
            logger.info(f"[Arc42] Merged crosscutting: {len(merged)} chars -> {target}")

    # -------------------------------------------------------------------------
    # PUBLIC API
    # -------------------------------------------------------------------------

    def run(self) -> str:
        """
        Execute all 13 Mini-Crews sequentially with resume support.

        On failure, completed mini-crews are checkpointed. Re-running
        skips already-completed mini-crews automatically.

        1 task per crew for maximum reliability with on-prem models.
        """
        completed = self._load_checkpoint()
        results = []

        # Define mini-crews as (name, [(desc, expected_output)], [expected_files])
        # IMPORTANT: Max 1 task per crew — each chapter gets its own fresh
        # LLM context. The on-prem model frequently fails on the 2nd task
        # in a crew (writes ch03 but not ch04, etc.).
        mini_crews: list[tuple[str, list[tuple[str, str]], list[str]]] = [
            (
                "introduction",
                [
                    (CH01_INTRODUCTION, "Complete arc42 Introduction chapter (8-12 pages)"),
                ],
                ["arc42/01-introduction.md"],
            ),
            (
                "constraints",
                [
                    (CH02_CONSTRAINTS, "Complete arc42 Constraints chapter (8-10 pages)"),
                ],
                ["arc42/02-constraints.md"],
            ),
            (
                "context",
                [
                    (CH03_CONTEXT, "Complete arc42 Context chapter (8-12 pages)"),
                ],
                ["arc42/03-context.md"],
            ),
            (
                "solution-strategy",
                [
                    (CH04_SOLUTION_STRATEGY, "Complete arc42 Solution Strategy chapter (8-12 pages)"),
                ],
                ["arc42/04-solution-strategy.md"],
            ),
            (
                "building-blocks-overview",
                [
                    (CH05_PART1_OVERVIEW, "Building Blocks overview and system whitebox (6-8 pages)"),
                ],
                ["arc42/05-part1-overview.md"],
            ),
            (
                "building-blocks-controllers",
                [
                    (CH05_PART2_CONTROLLERS, "Building Blocks presentation layer (8-10 pages)"),
                ],
                ["arc42/05-part2-controllers.md"],
            ),
            (
                "building-blocks-services",
                [
                    (CH05_PART3_SERVICES, "Building Blocks business layer (8-10 pages)"),
                ],
                ["arc42/05-part3-services.md"],
            ),
            (
                "building-blocks-domain",
                [
                    (CH05_PART4_DOMAIN, "Building Blocks domain and persistence (8-10 pages)"),
                ],
                ["arc42/05-part4-domain.md"],
            ),
            (
                "runtime-view-api-flows",
                [
                    (CH06_PART1_API_FLOWS, "Arc42 Runtime View Part 1: API flows (8-10 pages)"),
                ],
                ["arc42/06-part1-api-flows.md"],
            ),
            (
                "runtime-view-business-flows",
                [
                    (CH06_PART2_BUSINESS_FLOWS, "Arc42 Runtime View Part 2: Business flows (8-10 pages)"),
                ],
                ["arc42/06-part2-business-flows.md"],
            ),
            (
                "deployment",
                [
                    (CH07_DEPLOYMENT, "Complete arc42 Deployment View chapter (8-10 pages)"),
                ],
                ["arc42/07-deployment.md"],
            ),
            (
                "crosscutting-technical",
                [
                    (CH08_PART1_TECHNICAL, "Arc42 Crosscutting Part 1: Technical concepts (8-10 pages)"),
                ],
                ["arc42/08-part1-technical.md"],
            ),
            (
                "crosscutting-patterns",
                [
                    (CH08_PART2_PATTERNS, "Arc42 Crosscutting Part 2: Patterns (8-10 pages)"),
                ],
                ["arc42/08-part2-patterns.md"],
            ),
            (
                "decisions",
                [
                    (CH09_DECISIONS, "Complete arc42 Decisions chapter (8-12 pages)"),
                ],
                ["arc42/09-decisions.md"],
            ),
            (
                "quality",
                [
                    (CH10_QUALITY, "Complete arc42 Quality chapter (8-10 pages)"),
                ],
                ["arc42/10-quality.md"],
            ),
            (
                "risks",
                [
                    (CH11_RISKS, "Complete arc42 Risks chapter (8-10 pages)"),
                ],
                ["arc42/11-risks.md"],
            ),
            (
                "glossary",
                [
                    (CH12_GLOSSARY, "Complete arc42 Glossary (6-8 pages)"),
                ],
                ["arc42/12-glossary.md"],
            ),
        ]

        # Get template data for filling {system_summary} placeholders
        template_data = self._summarize_facts()

        for name, task_specs, expected_files in mini_crews:
            if not self.should_skip(name, completed):
                try:
                    agent = self._create_agent()
                    tasks = [
                        Task(description=desc.format(**template_data), expected_output=output, agent=agent)
                        for desc, output in task_specs
                    ]
                    self._run_mini_crew(name, tasks, expected_files=expected_files)
                except Exception as e:
                    logger.error(f"[Arc42] Mini-crew {name} failed, continuing: {e}")
            results.append(f"{name}: Done")

        # Merge part files into final chapter files
        self._merge_building_blocks()
        self._merge_runtime_view()
        self._merge_crosscutting()

        # Quality Gate
        if not self.should_skip("quality-gate", completed):
            try:
                agent = self._create_agent()
                self._run_mini_crew(
                    "quality-gate",
                    [
                        Task(
                            description=QUALITY_GATE_DESCRIPTION,
                            expected_output="Arc42 Quality report written to quality/arc42-report.md",
                            agent=agent,
                        ),
                    ],
                )
            except Exception as e:
                logger.error(f"[Arc42] Quality gate failed, continuing: {e}")
        results.append("Quality Gate: Done")

        self._clear_checkpoint()
        summary = "\n".join(results)
        logger.info(f"[Arc42] All Mini-Crews completed:\n{summary}")
        return summary
