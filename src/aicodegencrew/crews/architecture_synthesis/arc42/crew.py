"""
Arc42 Crew - Phase 3b: Mini-Crews Pattern
==========================================
Creates all 12 arc42 chapters + Quality Gate

Architecture Fix:
- OLD: 1 Crew with 44 sequential tasks -> Context overflow after ~10 tasks
- NEW: 6 Mini-Crews (2-3 tasks each) -> Fresh context per chapter group

Each Mini-Crew starts with a fresh LLM context window.
Data is passed via template variables (summaries), not inter-task context.
"""
import logging
from pathlib import Path

from crewai import Task

from ..base_crew import MiniCrewBase, TOOL_INSTRUCTION
from ..tools import ChunkedWriterTool

logger = logging.getLogger(__name__)


# =============================================================================
# TASK DESCRIPTIONS - Python constants instead of tasks.yaml
# =============================================================================

CH01_INTRODUCTION = TOOL_INSTRUCTION + """
Create the COMPLETE arc42 Chapter 1: Introduction and Goals (8-10 pages).

## YOUR DATA SOURCES
Use these MCP tools to gather REAL data:
1. get_statistics() - System metrics overview
2. get_architecture_summary() - Architecture style and patterns
3. get_endpoints() - REST API endpoints
4. list_components_by_stereotype(stereotype="controller") - Controllers
5. list_components_by_stereotype(stereotype="service") - Services
6. list_components_by_stereotype(stereotype="repository") - Repositories
7. list_components_by_stereotype(stereotype="entity") - Entities

Summary data:
{system_summary}

## DOCUMENT STRUCTURE
Write to file: arc42/01-introduction.md using doc_writer tool.

# 01 - Introduction and Goals

## 1.1 Requirements Overview

### 1.1.1 What is this System?
- Full system description (not just one sentence!)
- Business domain and subdomain classification
- Primary business value delivered

### 1.1.2 Essential Features
Document the TOP 10 business capabilities with feature name, business value, and components involved.

### 1.1.3 System Statistics
| Metric | Count |
|--------|-------|
| Total Components | X |
| Controllers | X |
| Services | X |
| Repositories | X |
| Entities | X |
| REST Endpoints | X |

## 1.2 Quality Goals

For EACH quality goal:
| Attribute | Description |
|-----------|-------------|
| Goal | e.g., Maintainability |
| Priority | 1-3 |
| Rationale | Why? |
| How Achieved | Which patterns? |

Document at least 5 quality goals: Maintainability, Testability, Security, Performance, Scalability.

## 1.3 Stakeholders
| Role | Concern | Expectations | Contact |
|------|---------|--------------|---------|

Include at least 8 stakeholder roles.

Write 8-10 pages with REAL data from tools. No placeholders.
"""

CH02_CONSTRAINTS = TOOL_INSTRUCTION + """
Create the COMPLETE arc42 Chapter 2: Architecture Constraints (6-8 pages).

## YOUR DATA SOURCES
Use these MCP tools:
1. get_statistics() - System overview
2. get_architecture_summary() - Architecture decisions
3. query_architecture_facts(category="containers") - Container technologies

Summary data:
{system_summary}
{containers_summary}

## DOCUMENT STRUCTURE
Write to file: arc42/02-constraints.md using doc_writer tool.

# 02 - Architecture Constraints

## 2.1 Technical Constraints
For EACH constraint:
| Aspect | Description |
|--------|-------------|
| Constraint | Name |
| Background | Why? |
| Impact | How it affects architecture |
| Consequence | Resulting decisions |

Categories: Programming Language, Framework, Database, Infrastructure, Security.

## 2.2 Organizational Constraints
| Constraint | Background | Consequence |
|------------|------------|-------------|
| Team structure | ... | Component ownership |
| Development process | ... | Sprint-based delivery |
| Deployment frequency | ... | Release automation |

## 2.3 Convention Constraints
| Convention | Description | Enforcement |
|------------|-------------|-------------|
| Naming conventions | Package, class, method naming | ... |
| Code style | Formatting rules | ... |
| API design | REST conventions | ... |

Write 6-8 pages with REAL data from tools. No placeholders.
"""

CH03_CONTEXT = TOOL_INSTRUCTION + """
Create the COMPLETE arc42 Chapter 3: System Scope and Context (8-10 pages).

## YOUR DATA SOURCES
Use these MCP tools:
1. get_statistics() - System overview
2. get_architecture_summary() - Architecture style
3. get_endpoints() - REST API endpoints
4. query_architecture_facts(category="containers") - Container details
5. query_architecture_facts(category="interfaces") - API interfaces

Summary data:
{system_summary}

## DOCUMENT STRUCTURE
Write to file: arc42/03-context.md using doc_writer tool.

# 03 - System Scope and Context

## 3.1 Business Context

### 3.1.1 Context Diagram (text-based ASCII)
### 3.1.2 External Actors
| Actor | Role | Interactions | Volume |
|-------|------|--------------|--------|
### 3.1.3 External Systems
| System | Purpose | Protocol | Data Exchanged |
|--------|---------|----------|----------------|

## 3.2 Technical Context

### 3.2.1 Technical Interfaces
- REST API Surface
- Database Connections
- Message Channels

### 3.2.2 Protocols and Formats
- REST API: JSON over HTTPS
- Database: JDBC
- Caching: Redis (if applicable)

## 3.3 External Dependencies
### 3.3.1 Runtime Dependencies
| Dependency | Version | Purpose | Criticality |
|------------|---------|---------|-------------|
### 3.3.2 Build Dependencies
| Dependency | Version | Purpose |
|------------|---------|---------|

Write 8-10 pages with REAL data from tools. No placeholders.
"""

CH04_SOLUTION_STRATEGY = TOOL_INSTRUCTION + """
Create the COMPLETE arc42 Chapter 4: Solution Strategy (8-10 pages).

## YOUR DATA SOURCES
Use these MCP tools:
1. get_architecture_summary() - Architecture style and patterns
2. get_statistics() - System metrics
3. query_architecture_facts(category="containers") - Container details

Summary data:
{system_summary}

## DOCUMENT STRUCTURE
Write to file: arc42/04-solution-strategy.md using doc_writer tool.

# 04 - Solution Strategy

## 4.1 Technology Decisions
For EACH major technology choice (ADR-lite format):
| Aspect | Description |
|--------|-------------|
| Context | What problem? |
| Decision | What was chosen? |
| Rationale | Why this option? |
| Alternatives | What else? |
| Consequences | What follows? |

Document decisions for: Backend Framework, Database Technology, Frontend Framework, Build Tool, Container Technology, Security Framework, API Design.

## 4.2 Architecture Patterns

### 4.2.1 Macro Architecture
- Pattern name (e.g., Layered Architecture)
- Key principles and layer responsibilities
- Dependency rules

### 4.2.2 Applied Patterns
| Pattern | Purpose | Where Applied | Benefit |
|---------|---------|---------------|---------|

## 4.3 Achieving Quality Goals
| Quality Goal | Solution Approach | Implemented By |
|--------------|-------------------|----------------|

Write 8-10 pages with REAL data from tools. No placeholders.
"""

CH05_BUILDING_BLOCKS = TOOL_INSTRUCTION + """
Create the COMPLETE arc42 Chapter 5: Building Block View (20-25 pages).

THIS IS THE LARGEST CHAPTER. Use ALL available tools to get COMPLETE component lists.

## YOUR DATA SOURCES
Use these MCP tools:
1. get_statistics() - Component counts
2. get_architecture_summary() - Layer structure
3. list_components_by_stereotype(stereotype="controller") - ALL controllers
4. list_components_by_stereotype(stereotype="service") - ALL services
5. list_components_by_stereotype(stereotype="repository") - ALL repositories
6. list_components_by_stereotype(stereotype="entity") - ALL entities
7. search_components(query="config") - Configuration components
8. query_architecture_facts(category="relations") - Dependencies

Summary data:
{system_summary}
{containers_summary}

## DOCUMENT STRUCTURE
Write to file: arc42/05-building-blocks.md using doc_writer tool.

# 05 - Building Block View

## 5.1 Overview
- A-Architecture (Functional view)
- T-Architecture (Technical view)
- Building Block Hierarchy

## 5.2 Whitebox Overall System (Level 1)
- Container Overview with diagram (text-based)
- Container Responsibilities

## 5.3 Presentation Layer (Controllers)
### 5.3.1 Layer Overview
### 5.3.2 Controller Inventory (COMPLETE list in table)
### 5.3.3 API Patterns
### 5.3.4 Key Controllers Deep Dive (TOP 5)

## 5.4 Business Layer (Services)
### 5.4.1 Layer Overview
### 5.4.2 Service Inventory (COMPLETE list in table)
### 5.4.3 Service Patterns
### 5.4.4 Key Services Deep Dive (TOP 5)
### 5.4.5 Service Interactions

## 5.5 Domain Layer (Entities)
### 5.5.1 Layer Overview
### 5.5.2 Entity Inventory (COMPLETE list in table)
### 5.5.3 Domain Model Diagram (text-based)
### 5.5.4 Key Entities Deep Dive (TOP 5)

## 5.6 Persistence Layer (Repositories)
### 5.6.1 Layer Overview
### 5.6.2 Repository Inventory (COMPLETE list in table)
### 5.6.3 Data Access Patterns

## 5.7 Component Dependencies
- Layer Dependency Rules
- Dependency Matrix

Write 20-25 pages with REAL data from tools. COMPLETE component inventories. No placeholders.
"""

CH06_RUNTIME = TOOL_INSTRUCTION + """
Create the COMPLETE arc42 Chapter 6: Runtime View (8-10 pages).

## YOUR DATA SOURCES
Use these MCP tools:
1. get_statistics() - System overview
2. get_endpoints() - REST API endpoints
3. get_architecture_summary() - Architecture patterns
4. search_components(query="controller") - Find key controllers
5. query_architecture_facts(category="relations") - Dependencies

Summary data:
{system_summary}

## DOCUMENT STRUCTURE
Write to file: arc42/06-runtime-view.md using doc_writer tool.

# 06 - Runtime View

## 6.1 Overview

## 6.2 Key Scenarios
Document at least 5 runtime scenarios with sequence diagrams (text-based):

### Scenario 1: User Authentication
```
Client -> AuthController -> AuthService -> UserRepository -> Database
```

### Scenario 2: CRUD Create Operation
### Scenario 3: CRUD Read with Pagination
### Scenario 4: Business Process (most complex flow)
### Scenario 5: Error Handling Scenario

## 6.3 Interaction Patterns
- Synchronous Interactions
- Asynchronous Interactions (if any)

## 6.4 Transaction Boundaries
- Service layer demarcation
- Rollback scenarios

Write 8-10 pages with REAL data from tools. No placeholders.
"""

CH07_DEPLOYMENT = TOOL_INSTRUCTION + """
Create the COMPLETE arc42 Chapter 7: Deployment View (6-8 pages).

## YOUR DATA SOURCES
Use these MCP tools:
1. get_statistics() - System overview
2. get_architecture_summary() - Infrastructure hints
3. query_architecture_facts(category="containers") - Container details

Summary data:
{system_summary}
{containers_summary}

## DOCUMENT STRUCTURE
Write to file: arc42/07-deployment.md using doc_writer tool.

# 07 - Deployment View

## 7.1 Infrastructure Overview
- Deployment Diagram (text-based)

## 7.2 Infrastructure Nodes
| Node | Type | Specification | Purpose |
|------|------|---------------|---------|

## 7.3 Container Deployment
- Docker Configuration
- Container Orchestration

## 7.4 Environment Configuration
- Development, Test, Production

## 7.5 Network Topology
- Network Zones and Firewall Rules

## 7.6 Scaling Strategy
| Container | Scaling Type | Trigger | Min | Max |
|-----------|--------------|---------|-----|-----|

Write 6-8 pages with REAL data from tools. No placeholders.
"""

CH08_CROSSCUTTING = TOOL_INSTRUCTION + """
Create the COMPLETE arc42 Chapter 8: Cross-cutting Concepts (8-10 pages).

## YOUR DATA SOURCES
Use these MCP tools:
1. get_statistics() - System overview
2. get_architecture_summary() - Architecture patterns
3. search_components(query="security") - Security components
4. search_components(query="config") - Configuration components
5. list_components_by_stereotype(stereotype="entity") - Domain model

Summary data:
{system_summary}

## DOCUMENT STRUCTURE
Write to file: arc42/08-crosscutting.md using doc_writer tool.

# 08 - Cross-cutting Concepts

## 8.1 Domain Model
- Core Domain Concepts
- Entity Relationships

## 8.2 Security Concept
- Authentication mechanism
- Authorization mechanism
- Security Patterns

## 8.3 Persistence Concept
- ORM Strategy
- Transaction Management
- Database Migrations

## 8.4 Error Handling
- Exception hierarchy
- Error response format

## 8.5 Logging and Monitoring
- Logging framework
- Log levels and strategy

## 8.6 Testing Concept
- Test pyramid
- Test patterns

## 8.7 Configuration Management
- Property sources
- Profile management

Write 8-10 pages with REAL data from tools. No placeholders.
"""

CH09_DECISIONS = TOOL_INSTRUCTION + """
Create the COMPLETE arc42 Chapter 9: Architecture Decisions (8 pages).

## YOUR DATA SOURCES
Use these MCP tools:
1. get_architecture_summary() - Architecture style and patterns
2. get_statistics() - System overview
3. query_architecture_facts(category="containers") - Technology choices

Summary data:
{system_summary}

## DOCUMENT STRUCTURE
Write to file: arc42/09-decisions.md using doc_writer tool.

# 09 - Architecture Decisions

## 9.1 Decision Log Overview
Summary of all ADRs.

## 9.2 Architecture Decision Records
Write at least 8 ADRs in this format:

### ADR-001: [Title]
| Aspect | Description |
|--------|-------------|
| Status | Accepted |
| Context | What problem? |
| Decision | What was decided? |
| Rationale | Why? |
| Consequences | What follows? |

Cover decisions for: Architecture Style, Backend Framework, Database, Frontend, API Design, Authentication, Deployment, Caching.

Write 8 pages with REAL data from tools. No placeholders.
"""

CH10_QUALITY = TOOL_INSTRUCTION + """
Create the COMPLETE arc42 Chapter 10: Quality Requirements (6 pages).

## YOUR DATA SOURCES
Use these MCP tools:
1. get_architecture_summary() - Quality attributes
2. get_statistics() - System metrics

Summary data:
{system_summary}

## DOCUMENT STRUCTURE
Write to file: arc42/10-quality.md using doc_writer tool.

# 10 - Quality Requirements

## 10.1 Quality Tree
Show quality attribute hierarchy (text-based tree diagram).

## 10.2 Quality Scenarios
Document at least 10 quality scenarios:
| ID | Quality Attribute | Scenario | Expected Response | Priority |
|----|-------------------|----------|-------------------|----------|

## 10.3 Quality Metrics
| Metric | Target | Measurement Method |
|--------|--------|--------------------|

Write 6 pages with REAL data from tools. No placeholders.
"""

CH11_RISKS = TOOL_INSTRUCTION + """
Create the COMPLETE arc42 Chapter 11: Risks and Technical Debt (6 pages).

## YOUR DATA SOURCES
Use these MCP tools:
1. get_architecture_summary() - Architecture assessment
2. get_statistics() - System complexity metrics
3. query_architecture_facts(category="relations") - Dependency risks

Summary data:
{system_summary}

## DOCUMENT STRUCTURE
Write to file: arc42/11-risks.md using doc_writer tool.

# 11 - Risks and Technical Debt

## 11.1 Risk Overview
Summary table of all risks.

## 11.2 Architecture Risks
Document at least 5 risks:
| ID | Risk | Severity | Probability | Impact | Mitigation |
|----|------|----------|-------------|--------|------------|

## 11.3 Technical Debt Inventory
| ID | Debt Item | Category | Impact | Effort to Fix |
|----|-----------|----------|--------|---------------|

## 11.4 Mitigation Roadmap
| Phase | Action | Priority | Timeline |
|-------|--------|----------|----------|

Write 6 pages with REAL data from tools. No placeholders.
"""

CH12_GLOSSARY = TOOL_INSTRUCTION + """
Create the COMPLETE arc42 Chapter 12: Glossary (4 pages).

## YOUR DATA SOURCES
Use these MCP tools:
1. get_statistics() - System terminology
2. get_architecture_summary() - Architecture terms
3. list_components_by_stereotype(stereotype="entity") - Domain terms

Summary data:
{system_summary}

## DOCUMENT STRUCTURE
Write to file: arc42/12-glossary.md using doc_writer tool.

# 12 - Glossary

## 12.1 Business Terms
| Term | Definition |
|------|-----------|

## 12.2 Technical Terms
| Term | Definition |
|------|-----------|

## 12.3 Abbreviations
| Abbreviation | Full Form |
|--------------|-----------|

## 12.4 Architecture Patterns
| Pattern | Definition | Where Used |
|---------|-----------|------------|

Write 4 pages. Include ALL domain-specific terms from the system.
"""

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

    Mini-Crews:
    1. Intro+Constraints (chapters 1-2)
    2. Context+Strategy (chapters 3-4)
    3. Building Blocks (chapter 5 - largest chapter, own crew)
    4. Runtime+Deployment (chapters 6-7)
    5. Crosscutting+Decisions (chapters 8-9)
    6. Quality+Risks+Glossary (chapters 10-12)
    7. Quality Gate (validation)
    """

    @property
    def crew_name(self) -> str:
        return "Arc42"

    @property
    def agent_config_key(self) -> str:
        return "arc42_architect"

    def _get_agents_yaml_dir(self) -> str:
        return str(Path(__file__).parent)

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

        tech_stack = sorted(
            {c.get("technology", "Unknown") for c in containers if c.get("technology")}
        )

        by_stereotype: dict[str, int] = {}
        for comp in components:
            stereo = comp.get("stereotype", "unknown")
            by_stereotype[stereo] = by_stereotype.get(stereo, 0) + 1

        arch_style = arch_info.get("primary_style", "UNKNOWN - use tools to discover")

        system_summary = f"""SYSTEM: {system_name}

ARCHITECTURE (from Phase 2 analysis):
- Primary Style: {arch_style}
- Patterns: {', '.join([p.get('name', str(p)) if isinstance(p, dict) else str(p) for p in patterns]) if patterns else 'Use tools to discover'}

STATISTICS (from Phase 1 facts):
- Containers: {len(containers)}
- Components: {len(components)}
- Interfaces: {len(interfaces)}
- Relations: {len(relations)}

TECHNOLOGIES:
{chr(10).join([f'- {t}' for t in tech_stack]) if tech_stack else '- Use tools to discover'}

COMPONENT COUNTS BY STEREOTYPE:
{chr(10).join([f'- {k}: {v}' for k, v in sorted(by_stereotype.items())]) if by_stereotype else '- Use tools to discover'}

IMPORTANT: Use MCP tools (get_statistics, get_architecture_summary, list_components_by_stereotype) to get REAL data!"""

        container_lines = [
            f"- {c.get('name', '?')}: {c.get('technology', '?')}"
            for c in containers
        ]

        containers_summary = f"""CONTAINERS:
{chr(10).join(container_lines) if container_lines else '- Use query_architecture_facts to discover'}"""

        components_summary = (
            "Use list_components_by_stereotype tool to query components by type."
        )
        interfaces_summary = f"Total interfaces: {len(interfaces)}. Use query_architecture_facts with category='interfaces' for details."
        relations_summary = f"Total relations: {len(relations)}. Use query_architecture_facts with category='relations' for details."
        building_blocks_data = "Use list_components_by_stereotype for each layer (controller, service, repository, entity)."

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
    # PUBLIC API
    # -------------------------------------------------------------------------

    def run(self) -> str:
        """
        Execute all 7 Mini-Crews sequentially with resume support.

        On failure, completed mini-crews are checkpointed. Re-running
        skips already-completed mini-crews automatically.
        """
        completed = self._load_checkpoint()
        results = []

        # Define mini-crews as (name, [(description, expected_output), ...])
        mini_crews: list[tuple[str, list[tuple[str, str]]]] = [
            ("intro-constraints", [
                (CH01_INTRODUCTION, "Complete arc42 Introduction chapter (8-10 pages)"),
                (CH02_CONSTRAINTS, "Complete arc42 Constraints chapter (6-8 pages)"),
            ]),
            ("context-strategy", [
                (CH03_CONTEXT, "Complete arc42 Context chapter (8-10 pages)"),
                (CH04_SOLUTION_STRATEGY, "Complete arc42 Solution Strategy chapter (8-10 pages)"),
            ]),
            ("building-blocks", [
                (CH05_BUILDING_BLOCKS, "Complete arc42 Building Blocks chapter (20-25 pages)"),
            ]),
            ("runtime-deployment", [
                (CH06_RUNTIME, "Complete arc42 Runtime View chapter (8-10 pages)"),
                (CH07_DEPLOYMENT, "Complete arc42 Deployment View chapter (6-8 pages)"),
            ]),
            ("crosscutting-decisions", [
                (CH08_CROSSCUTTING, "Complete arc42 Crosscutting chapter (8-10 pages)"),
                (CH09_DECISIONS, "Complete arc42 Decisions chapter (8 pages)"),
            ]),
            ("quality-risks-glossary", [
                (CH10_QUALITY, "Complete arc42 Quality chapter (6 pages)"),
                (CH11_RISKS, "Complete arc42 Risks chapter (6 pages)"),
                (CH12_GLOSSARY, "Complete arc42 Glossary (4 pages)"),
            ]),
        ]

        for name, task_specs in mini_crews:
            if not self.should_skip(name, completed):
                agent = self._create_agent()
                tasks = [
                    Task(description=desc, expected_output=output, agent=agent)
                    for desc, output in task_specs
                ]
                self._run_mini_crew(name, tasks)
            results.append(f"{name}: Done")

        # Quality Gate
        if not self.should_skip("quality-gate", completed):
            agent = self._create_agent()
            self._run_mini_crew("quality-gate", [
                Task(
                    description=QUALITY_GATE_DESCRIPTION,
                    expected_output="Arc42 Quality report written to quality/arc42-report.md",
                    agent=agent,
                ),
            ])
        results.append("Quality Gate: Done")

        self._clear_checkpoint()
        summary = "\n".join(results)
        logger.info(f"[Arc42] All Mini-Crews completed:\n{summary}")
        return summary
