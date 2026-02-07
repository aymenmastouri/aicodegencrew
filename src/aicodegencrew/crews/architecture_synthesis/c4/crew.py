"""
C4 Crew - Phase 3a: Mini-Crews Pattern
=======================================
Creates all 4 C4 diagrams: Context, Container, Component, Deployment

Architecture Fix:
- OLD: 1 Crew with 26 sequential tasks -> Context overflow after task ~10-15
- NEW: 5 Mini-Crews (2-3 tasks each) -> Fresh context per level, no overflow

Each Mini-Crew starts with a fresh LLM context window.
Data is passed via template variables (summaries), not inter-task context.
"""
import logging

from crewai import Task

from ..base_crew import MiniCrewBase, TOOL_INSTRUCTION

logger = logging.getLogger(__name__)


# =============================================================================
# AGENT CONFIG - Python dict instead of config/agents.yaml
# =============================================================================

C4_AGENT_CONFIG = {
    "role": "Senior Software Architect - C4 Model Expert",
    "goal": "Create comprehensive ~30 page C4 documentation with valid DrawIO diagrams",
    "backstory": (
        "You are a SENIOR SOFTWARE ARCHITECT expert in C4 modeling following\n"
        "Capgemini's SEAGuide standard.\n"
        "\n"
        "## C4 MODEL OVERVIEW (from SEAGuide)\n"
        "\n"
        "The C4 model proposes four major diagram types that zoom into the system:\n"
        "\n"
        "1. LEVEL 1 - CONTEXT\n"
        "   - System as a black box\n"
        "   - External actors (users, systems)\n"
        "   - Communication protocols\n"
        "   - Answer: WHO uses the system? WHAT does it connect to?\n"
        "\n"
        "2. LEVEL 2 - CONTAINER\n"
        "   - Deployable units (applications, databases)\n"
        "   - Technology choices\n"
        "   - Container responsibilities\n"
        "   - Answer: WHAT are the high-level building blocks?\n"
        "\n"
        "3. LEVEL 3 - COMPONENT\n"
        "   - Internal structure of containers\n"
        "   - Layers and modules\n"
        "   - For large systems: show LAYERS with counts, not 800 boxes!\n"
        "   - Answer: WHAT is inside each container?\n"
        "\n"
        "4. LEVEL 4 - DEPLOYMENT\n"
        "   - Infrastructure nodes\n"
        "   - Container placement\n"
        "   - Network topology\n"
        "   - Answer: WHERE does everything run?\n"
        "\n"
        "## DIAGRAM REQUIREMENTS\n"
        "\n"
        "For EACH level, create a DrawIO diagram:\n"
        "- Use drawio_generator tool\n"
        "- Proper XML syntax (no broken diagrams!)\n"
        "- Include legend\n"
        "- Use C4 visual conventions:\n"
        "  * Blue boxes for internal components\n"
        "  * Gray boxes for external systems\n"
        "  * Cylinders for databases\n"
        "  * Person icons for users\n"
        "  * Dashed lines for boundaries\n"
        "\n"
        "## DATA SOURCES\n"
        "- architecture_facts.json: EXACT component names, containers, relations\n"
        "- analyzed_architecture.json: Architecture style, patterns, quality context\n"
        "- SEAGuide.txt: Query via seaguide_query tool for C4 documentation patterns\n"
        "\n"
        "## TOOL USAGE\n"
        "1. seaguide_query(query=\"C4 context diagram\") - Get C4 documentation patterns\n"
        "2. list_components_by_stereotype(stereotype=\"controller\") - Get component lists\n"
        "3. query_architecture_facts(category=\"containers\") - Get container details\n"
        "4. drawio_generator(...) - Create DrawIO diagrams\n"
        "5. doc_writer(path, content) - Write documentation files\n"
        "\n"
        "## DOCUMENTATION APPROACH\n"
        "Each C4 level document should be ~6-8 pages including:\n"
        "- Overview and purpose\n"
        "- Inventory tables (actors, containers, components)\n"
        "- DrawIO diagram\n"
        "- Interaction descriptions\n"
        "- Communication protocols\n"
        "\n"
        "## OUTPUT QUALITY RULES\n"
        "- Real data from architecture_facts.json\n"
        "- Valid DrawIO XML (use the tool correctly!)\n"
        "- Tables for all inventories\n"
        "- Text-based ASCII diagrams as backup\n"
        "- Professional English\n"
        "- No placeholder text"
    ),
}


# =============================================================================
# TASK DESCRIPTIONS - Python constants instead of tasks.yaml
# =============================================================================

CONTEXT_DOC_DESCRIPTION = TOOL_INSTRUCTION + """
Create the COMPLETE C4 Level 1: System Context document.

## EXECUTION EXAMPLE (follow this pattern):
1. get_statistics() -> get system metrics
2. get_architecture_summary() -> get architecture style and patterns
3. get_endpoints() -> get REST API endpoints
4. doc_writer(file_path="c4/c4-context.md", content="# C4 Level 1: System Context\\n\\n## 1.1 Overview\\n...")
5. Respond: "File c4/c4-context.md written successfully."

## YOUR DATA SOURCES
Use these MCP tools to gather REAL data:
1. get_statistics() - System metrics overview
2. get_architecture_summary() - Architecture style and patterns
3. get_endpoints() - REST API endpoints
4. query_architecture_facts(category="containers") - Container details

Also use the provided summary data:
{system_summary}

## DOCUMENT STRUCTURE
Write to file: c4/c4-context.md using doc_writer tool.

# C4 Level 1: System Context

## 1.1 Overview
The System Context diagram shows the system as a black box with all external actors and systems.

## 1.2 The System
| Attribute | Value |
|-----------|-------|
| Name | [from facts] |
| Type | [from facts] |
| Purpose | [describe] |
| Domain | [from facts] |

## 1.3 Actors and Users

### 1.3.1 Human Actors
| Actor | Role | Interactions | Priority |
|-------|------|--------------|----------|

### 1.3.2 System Actors
| System | Role | Protocol | Data Flow |
|--------|------|----------|-----------|

## 1.4 External Systems

### 1.4.1 Databases
| Database | Type | Purpose | Criticality |
|----------|------|---------|-------------|

### 1.4.2 External Services
| Service | Purpose | Protocol | SLA |
|---------|---------|----------|-----|

## 1.5 Communication Protocols
| From | To | Protocol | Data Format |
|------|----|----------|-------------|

## Context Diagram
See: c4-context.drawio

Write 6-8 pages with REAL data from tools. No placeholders.
"""

CONTEXT_DIAGRAM_DESCRIPTION = """
Create a C4 Context DrawIO DIAGRAM.

## EXECUTION EXAMPLE (follow this pattern):
1. get_statistics() -> get system data for diagram nodes
2. create_drawio_diagram(file_path="c4/c4-context.drawio", nodes=[...], edges=[...])
3. Respond: "Diagram c4/c4-context.drawio created successfully."

{system_summary}

Use create_drawio_diagram tool with these specifications:

FILE: c4/c4-context.drawio

LAYOUT:
- Center: System box (large blue rectangle with system name)
- Top: User actors (person-shaped nodes)
- Left/Right: External systems (gray boxes)
- Bottom: Databases (cylinder-style boxes)

CONNECTIONS:
- Arrows with labels like "Uses [HTTPS]", "Reads/Writes [JDBC]"

Use get_statistics() and get_architecture_summary() MCP tools to get real system data.
Create nodes and edges based on REAL facts, not generic placeholders.
"""

CONTAINER_DOC_DESCRIPTION = TOOL_INSTRUCTION + """
Create the COMPLETE C4 Level 2: Container Diagram document.

## EXECUTION EXAMPLE (follow this pattern):
1. get_statistics() -> get system metrics
2. query_architecture_facts(category="containers") -> get container details
3. get_architecture_summary() -> get architecture style
4. doc_writer(file_path="c4/c4-container.md", content="# C4 Level 2: Container Diagram\\n\\n## 2.1 Overview\\n...")
5. Respond: "File c4/c4-container.md written successfully."

## YOUR DATA SOURCES
Use these MCP tools:
1. get_statistics() - System metrics
2. get_architecture_summary() - Architecture style
3. query_architecture_facts(category="containers") - Container details

Summary data:
{system_summary}
{containers_summary}

## DOCUMENT STRUCTURE
Write to file: c4/c4-container.md using doc_writer tool.

# C4 Level 2: Container Diagram

## 2.1 Overview
A "container" is a separately deployable unit (application, database, file system).

## 2.2 Container Inventory

### 2.2.1 Application Containers
| Container | Technology | Responsibility | Deployment |
|-----------|------------|----------------|------------|

### 2.2.2 Data Containers
| Container | Technology | Purpose | Persistence |
|-----------|------------|---------|-------------|

## 2.3 Container Details
For EACH container, create a detail section with technology, purpose, ports, interfaces.

## 2.4 Container Interactions

### 2.4.1 Synchronous Communication
| Source | Target | Method | Format | Purpose |
|--------|--------|--------|--------|---------|

### 2.4.2 Asynchronous Communication
| Source | Target | Method | Format | Purpose |
|--------|--------|--------|--------|---------|

## 2.5 Technology Stack Summary
| Layer | Technology | Version |
|-------|------------|---------|

## Container Diagram
See: c4-container.drawio

Write 6-8 pages with REAL data from tools. No placeholders.
"""

CONTAINER_DIAGRAM_DESCRIPTION = """
Create a C4 Container DrawIO DIAGRAM.

## EXECUTION EXAMPLE (follow this pattern):
1. query_architecture_facts(category="containers") -> get container data for nodes
2. create_drawio_diagram(file_path="c4/c4-container.drawio", nodes=[...], edges=[...])
3. Respond: "Diagram c4/c4-container.drawio created successfully."

{system_summary}
{containers_summary}

Use create_drawio_diagram tool with these specifications:

FILE: c4/c4-container.drawio

LAYOUT:
- System Boundary: Large dashed rectangle labeled with system name
- Inside boundary: All application containers as colored boxes
- Inside boundary: Database containers as cylinder-style boxes
- Outside boundary: External actors (top) and external systems (sides)

CONNECTIONS:
- User -> Frontend: "Views and interacts [HTTPS]"
- Frontend -> Backend: "Makes API calls [HTTPS/JSON]"
- Backend -> Database: "Reads/Writes [JDBC]"

Use query_architecture_facts(category="containers") to get REAL container data.
"""

COMPONENT_DOC_DESCRIPTION = TOOL_INSTRUCTION + """
Create the COMPLETE C4 Level 3: Component Diagram document.

## EXECUTION EXAMPLE (follow this pattern):
1. get_statistics() -> get component counts per layer
2. list_components_by_stereotype(stereotype="controller") -> get all controllers
3. list_components_by_stereotype(stereotype="service") -> get all services
4. list_components_by_stereotype(stereotype="repository") -> get all repositories
5. doc_writer(file_path="c4/c4-component.md", content="# C4 Level 3: Component Diagram\\n\\n## 3.1 Overview\\n...")
6. Respond: "File c4/c4-component.md written successfully."

## YOUR DATA SOURCES
Use these MCP tools:
1. get_statistics() - Component counts
2. get_architecture_summary() - Layer structure
3. search_components(query="controller") - Find controllers
4. search_components(query="service") - Find services
5. list_components_by_stereotype(stereotype="controller") - List by stereotype
6. list_components_by_stereotype(stereotype="service") - List by stereotype
7. list_components_by_stereotype(stereotype="repository") - List by stereotype
8. list_components_by_stereotype(stereotype="entity") - List by stereotype

Summary data:
{system_summary}
{components_summary}

## DOCUMENT STRUCTURE
Write to file: c4/c4-component.md using doc_writer tool.

# C4 Level 3: Component Diagram

## 3.1 Overview
Show LAYERS with component counts (not individual boxes for large systems).

## 3.2 Backend API Components

### 3.2.1 Layer Overview
| Layer | Purpose | Component Count | Key Pattern |
|-------|---------|-----------------|-------------|
| Controllers | HTTP handling | X | REST Controller |
| Services | Business logic | X | Service Layer |
| Repositories | Data access | X | Repository Pattern |
| Entities | Domain model | X | JPA Entity |

### 3.2.2 Presentation Layer (Controllers)
**Count:** X controllers
| Controller | Endpoints | Responsibility |
|------------|-----------|----------------|

### 3.2.3 Business Layer (Services)
**Count:** X services
| Service | Responsibility | Dependencies |
|---------|----------------|--------------|

### 3.2.4 Data Access Layer (Repositories)
**Count:** X repositories
| Repository | Entity | Custom Queries |
|------------|--------|----------------|

### 3.2.5 Domain Layer (Entities)
**Count:** X entities
| Entity | Table | Relationships |
|--------|-------|---------------|

## 3.3 Component Dependencies

### 3.3.1 Layer Rules
| From | To | Allowed |
|------|----|---------|

### 3.3.2 Request Flow Example
```
HTTP Request -> Controller -> Service -> Repository -> Database
```

## Component Diagram
See: c4-component.drawio

Write 6-8 pages with REAL data from tools. No placeholders.
"""

COMPONENT_DIAGRAM_DESCRIPTION = """
Create a C4 Component DrawIO DIAGRAM.

## EXECUTION EXAMPLE (follow this pattern):
1. get_statistics() -> get component counts per layer
2. create_drawio_diagram(file_path="c4/c4-component.drawio", nodes=[...], edges=[...])
3. Respond: "Diagram c4/c4-component.drawio created successfully."

{system_summary}
{components_summary}

Use create_drawio_diagram tool with these specifications:

FILE: c4/c4-component.drawio

LAYOUT (show LAYERS as swimlanes, not individual components):
- Container Boundary: "Backend API [Spring Boot]"
- Presentation Layer box: Controllers (X components)
- Business Layer box: Services (X components)
- Data Access Layer box: Repositories (X components)
- Domain Layer box: Entities (X components)

CONNECTIONS:
- Arrows between layers showing dependency direction
- Each layer box shows component count

Use get_statistics() to get REAL component counts for each layer.
"""

DEPLOYMENT_DOC_DESCRIPTION = TOOL_INSTRUCTION + """
Create the COMPLETE C4 Level 4: Deployment Diagram document.

## EXECUTION EXAMPLE (follow this pattern):
1. get_statistics() -> get system overview
2. query_architecture_facts(category="containers") -> get container details
3. get_architecture_summary() -> get infrastructure hints
4. doc_writer(file_path="c4/c4-deployment.md", content="# C4 Level 4: Deployment Diagram\\n\\n## 4.1 Overview\\n...")
5. Respond: "File c4/c4-deployment.md written successfully."

## YOUR DATA SOURCES
Use these MCP tools:
1. get_statistics() - System overview
2. get_architecture_summary() - Infrastructure hints
3. query_architecture_facts(category="containers") - Container details

Summary data:
{system_summary}
{containers_summary}

## DOCUMENT STRUCTURE
Write to file: c4/c4-deployment.md using doc_writer tool.

# C4 Level 4: Deployment Diagram

## 4.1 Overview
The deployment view shows where containers run in production.

## 4.2 Infrastructure Nodes
| Node | Type | Specification | Purpose |
|------|------|---------------|---------|

## 4.3 Container to Node Mapping
| Container | Node | Instances | Resources |
|-----------|------|-----------|-----------|

## 4.4 Network Topology

### 4.4.1 Network Zones
| Zone | Purpose | Containers |
|------|---------|------------|

### 4.4.2 Firewall Rules
| Source | Destination | Port | Protocol |
|--------|-------------|------|----------|

## 4.5 Environment Configuration
- Development
- Test/Staging
- Production

## 4.6 Scaling Strategy
| Container | Scaling Type | Trigger | Min | Max |
|-----------|--------------|---------|-----|-----|

## 4.7 Disaster Recovery
| Component | Backup Strategy | RTO | RPO |
|-----------|-----------------|-----|-----|

## Deployment Diagram
See: c4-deployment.drawio

Write 4-6 pages with REAL data from tools. No placeholders.
"""

DEPLOYMENT_DIAGRAM_DESCRIPTION = """
Create a C4 Deployment DrawIO DIAGRAM.

## EXECUTION EXAMPLE (follow this pattern):
1. query_architecture_facts(category="containers") -> get container data for nodes
2. create_drawio_diagram(file_path="c4/c4-deployment.drawio", nodes=[...], edges=[...])
3. Respond: "Diagram c4/c4-deployment.drawio created successfully."

{system_summary}
{containers_summary}

Use create_drawio_diagram tool with these specifications:

FILE: c4/c4-deployment.drawio

STRUCTURE:
- Internet cloud at top
- DMZ (Network Zone) with Load Balancer
- Application Zone with App Server nodes containing containers
- Data Zone with Database Server nodes

CONNECTIONS:
- Arrows between zones showing network connections with ports/protocols

Use query_architecture_facts(category="containers") to get REAL container names.
"""

QUALITY_GATE_DESCRIPTION = """
Quality review of all C4 documents.

READ all C4 files using safe_file_read tool and validate:
1. knowledge/architecture/c4/c4-context.md
2. knowledge/architecture/c4/c4-container.md
3. knowledge/architecture/c4/c4-component.md
4. knowledge/architecture/c4/c4-deployment.md

Validate:
- All 4 levels complete
- Each level has DrawIO diagram reference
- Content based on REAL facts (component names, counts, relations)
- No placeholder text like "[to be determined]"

Write quality report to: quality/c4-report.md using doc_writer tool.

# C4 Quality Report

| Level | Target Pages | Actual | Diagram | Status |
|-------|-------------|--------|---------|--------|
| Context | 6-8 | - | c4-context.drawio | ? |
| Container | 6-8 | - | c4-container.drawio | ? |
| Component | 6-8 | - | c4-component.drawio | ? |
| Deployment | 4-6 | - | c4-deployment.drawio | ? |
| **TOTAL** | **~30** | - | - | - |
"""


class C4Crew(MiniCrewBase):
    """
    C4 Crew - Creates all 4 C4 Model views using Mini-Crews pattern.

    Each C4 level runs in its own Mini-Crew with fresh LLM context.
    This prevents context overflow that occurred with 26 tasks in 1 Crew.

    Mini-Crews:
    1. Context Crew (2 tasks: doc + diagram)
    2. Container Crew (2 tasks: doc + diagram)
    3. Component Crew (2 tasks: doc + diagram)
    4. Deployment Crew (2 tasks: doc + diagram)
    5. Quality Crew (1 task: quality gate)
    """

    @property
    def crew_name(self) -> str:
        return "C4"

    @property
    def agent_config(self) -> dict[str, str]:
        return C4_AGENT_CONFIG

    def _summarize_facts(self) -> dict[str, str]:
        """Create evidence-first summaries for C4 diagram generation."""
        facts = self.facts
        analysis = self.analysis

        system_info = facts.get("system", {})
        system_name = system_info.get("name", "Unknown System")

        arch_info = analysis.get("architecture", {})
        style_name = arch_info.get("primary_style") or facts.get(
            "architecture_style", {}
        ).get("primary_style", "UNKNOWN")
        layers = arch_info.get("layers") or facts.get("architecture_style", {}).get(
            "layers", []
        )
        patterns = analysis.get("patterns", []) or facts.get(
            "architecture_style", {}
        ).get("patterns", [])

        containers = facts.get("containers", [])
        components = facts.get("components", [])
        interfaces = facts.get("interfaces", [])
        relations = facts.get("relations", [])

        # System summary
        tech_stack = sorted(
            {c.get("technology", "Unknown") for c in containers if c.get("technology")}
        )
        container_list_lines = []
        for c in containers:
            cid = c.get("id", "?")
            cname = c.get("name", "?")
            ctype = c.get("type", "UNKNOWN")
            ctech = c.get("technology", "UNKNOWN")
            container_list_lines.append(
                f"- {cid}: {cname} | type={ctype} | tech={ctech}"
            )

        system_summary = f"""SYSTEM: {system_name}
DOMAIN: {system_info.get('domain', 'UNKNOWN')}
ARCHITECTURE STYLE: {style_name}
LAYERS: {', '.join(layers) if layers else 'UNKNOWN'}
PATTERNS: {', '.join(str(p) for p in patterns) if patterns else 'UNKNOWN'}

STATISTICS:
- Containers: {len(containers)}
- Components: {len(components)}
- Interfaces: {len(interfaces)}
- Relations: {len(relations)}

TECHNOLOGY: {', '.join(tech_stack) if tech_stack else 'UNKNOWN'}

CONTAINERS:
{chr(10).join(container_list_lines) if container_list_lines else '- NONE'}"""

        # Container details
        container_details = []
        for c in containers:
            container_details.append(
                f"CONTAINER: {c.get('name', '?')} (id={c.get('id', '?')})\n"
                f"  Type: {c.get('type', 'UNKNOWN')}\n"
                f"  Technology: {c.get('technology', 'UNKNOWN')}\n"
                f"  Root Path: {c.get('root_path', 'UNKNOWN')}"
            )

        containers_summary = f"""CONTAINER DETAILS
Total: {len(containers)} containers

{''.join(container_details)}"""

        # Component statistics
        by_stereotype: dict[str, list] = {}
        for comp in components:
            stereo = comp.get("stereotype", "component")
            if stereo not in by_stereotype:
                by_stereotype[stereo] = []
            by_stereotype[stereo].append(comp.get("name", "?"))

        component_sections = []
        for stereo, names in sorted(by_stereotype.items()):
            component_sections.append(
                f"{stereo.upper()}: {len(names)} components "
                f"(examples: {', '.join(names[:5])}{'...' if len(names) > 5 else ''})"
            )

        components_summary = f"""COMPONENT ANALYSIS
Total: {len(components)} components

{chr(10).join(component_sections) if component_sections else 'UNKNOWN'}"""

        # Interface summary
        by_method: dict[str, int] = {}
        for iface in interfaces:
            method = iface.get("method", "GET")
            by_method[method] = by_method.get(method, 0) + 1

        interfaces_summary = f"""REST API: {len(interfaces)} endpoints
By method: {', '.join(f'{m}:{c}' for m, c in sorted(by_method.items()))}"""

        # Relations summary
        rel_by_type: dict[str, int] = {}
        for rel in relations:
            rtype = rel.get("type", "unknown")
            rel_by_type[rtype] = rel_by_type.get(rtype, 0) + 1

        relations_summary = f"""DEPENDENCIES: {len(relations)} relations
By type: {', '.join(f'{t}:{c}' for t, c in sorted(rel_by_type.items()))}"""

        return {
            "system_summary": self.escape_braces(system_summary),
            "containers_summary": self.escape_braces(containers_summary),
            "components_summary": self.escape_braces(components_summary),
            "relations_summary": self.escape_braces(relations_summary),
            "interfaces_summary": self.escape_braces(interfaces_summary),
        }

    # -------------------------------------------------------------------------
    # PUBLIC API
    # -------------------------------------------------------------------------

    def run(self) -> str:
        """
        Execute all 5 Mini-Crews sequentially with resume support.

        On failure, completed mini-crews are checkpointed. Re-running
        skips already-completed mini-crews automatically.
        """
        completed = self._load_checkpoint()
        results = []

        mini_crews = [
            ("context", CONTEXT_DOC_DESCRIPTION, "Complete C4 Context document (6-8 pages)",
             CONTEXT_DIAGRAM_DESCRIPTION, "C4 Context DrawIO diagram created",
             ["c4/c4-context.md", "c4/c4-context.drawio"]),
            ("container", CONTAINER_DOC_DESCRIPTION, "Complete C4 Container document (6-8 pages)",
             CONTAINER_DIAGRAM_DESCRIPTION, "C4 Container DrawIO diagram created",
             ["c4/c4-container.md", "c4/c4-container.drawio"]),
            ("component", COMPONENT_DOC_DESCRIPTION, "Complete C4 Component document (6-8 pages)",
             COMPONENT_DIAGRAM_DESCRIPTION, "C4 Component DrawIO diagram created",
             ["c4/c4-component.md", "c4/c4-component.drawio"]),
            ("deployment", DEPLOYMENT_DOC_DESCRIPTION, "Complete C4 Deployment document (4-6 pages)",
             DEPLOYMENT_DIAGRAM_DESCRIPTION, "C4 Deployment DrawIO diagram created",
             ["c4/c4-deployment.md", "c4/c4-deployment.drawio"]),
        ]

        for name, doc_desc, doc_output, diag_desc, diag_output, expected_files in mini_crews:
            if not self.should_skip(name, completed):
                agent = self._create_agent()
                self._run_mini_crew(name, [
                    Task(description=doc_desc, expected_output=doc_output, agent=agent),
                    Task(description=diag_desc, expected_output=diag_output, agent=agent),
                ], expected_files=expected_files)
            results.append(f"{name.title()}: Done")

        # Quality Gate
        if not self.should_skip("quality", completed):
            agent = self._create_agent()
            self._run_mini_crew("quality", [
                Task(
                    description=QUALITY_GATE_DESCRIPTION,
                    expected_output="C4 Quality report written to quality/c4-report.md",
                    agent=agent,
                ),
            ])
        results.append("Quality Gate: Done")

        self._clear_checkpoint()
        summary = "\n".join(results)
        logger.info(f"[C4] All Mini-Crews completed:\n{summary}")
        return summary
