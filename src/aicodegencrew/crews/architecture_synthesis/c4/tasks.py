"""
C4 Crew - Task Descriptions
=============================
Task descriptions for 4 C4 diagram levels + quality gate.

Each mini-crew creates a doc + diagram pair for one C4 level.
Task descriptions use {template_variables} for facts data injection.
"""

from ..base_crew import TOOL_INSTRUCTION

# =============================================================================
# C4 Level 1: Context
# =============================================================================

CONTEXT_DOC_DESCRIPTION = (
    TOOL_INSTRUCTION
    + """
Create the COMPLETE C4 Level 1: System Context document.

## EXECUTION STEPS (call each tool exactly ONCE, never as array):
Step 1: query_facts(category="containers") -> container overview
Step 2: query_facts(category="interfaces") -> REST API endpoints
Step 3: query_facts(category="relations") -> system interactions
Step 4: doc_writer(file_path="c4/c4-context.md", content="# C4 Level 1: System Context\n...")
Step 5: Respond ONLY: "Chapter completed."

## YOUR DATA SOURCES
Use these tools to gather REAL data (call each tool ONCE with a SINGLE set of parameters):
1. query_facts(category="containers") - Container/system overview
2. query_facts(category="interfaces") - REST API endpoints
3. query_facts(category="relations") - System interactions
4. list_components_by_stereotype(stereotype="controller") - Controllers

Also use the provided summary data:
{system_summary}

## DOCUMENT STRUCTURE

# C4 Level 1: System Context

## 1.1 Overview
The System Context diagram shows the system as a black box with all external actors and systems.

## 1.2 The System
| Attribute | Value |
|-----------|-------|
| Name | (from query_facts) |
| Type | (from query_facts) |
| Purpose | (derive from components) |
| Domain | (from query_facts) |

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
"""
)

CONTEXT_DIAGRAM_DESCRIPTION = """
Create a C4 Context DrawIO DIAGRAM.

## EXECUTION STEPS (call each tool exactly ONCE, never as array):
1. query_facts(category="containers") -> get system data for diagram nodes
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

Use query_facts(category="containers") to get real system data.
Create nodes and edges based on REAL facts, not generic placeholders.
"""

# =============================================================================
# C4 Level 2: Container
# =============================================================================

CONTAINER_DOC_DESCRIPTION = (
    TOOL_INSTRUCTION
    + """
Create the COMPLETE C4 Level 2: Container Diagram document.

## EXECUTION STEPS (call each tool exactly ONCE, never as array):
1. query_facts(category="containers") -> get container details
2. query_facts(category="relations") -> get container interactions
3. doc_writer(file_path="c4/c4-container.md", content="# C4 Level 2: Container Diagram\\n\\n## 2.1 Overview\\n...")
4. Respond: "File c4/c4-container.md written successfully."

## YOUR DATA SOURCES
Use these tools (call each ONCE with a SINGLE set of parameters):
1. query_facts(category="containers") - Container details
2. query_facts(category="relations") - Container interactions
3. query_facts(category="interfaces") - API endpoints

Summary data:
{system_summary}
{containers_summary}

## DOCUMENT STRUCTURE

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
"""
)

CONTAINER_DIAGRAM_DESCRIPTION = """
Create a C4 Container DrawIO DIAGRAM.

## EXECUTION STEPS (call each tool exactly ONCE, never as array):
1. query_facts(category="containers") -> get container data for nodes
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

Use query_facts(category="containers") to get REAL container data.
"""

# =============================================================================
# C4 Level 3: Component
# =============================================================================

COMPONENT_DOC_DESCRIPTION = (
    TOOL_INSTRUCTION
    + """
Create the COMPLETE C4 Level 3: Component Diagram document.

## EXECUTION STEPS (call each tool exactly ONCE, never as array):
1. list_components_by_stereotype(stereotype="controller") -> get all controllers
2. list_components_by_stereotype(stereotype="service") -> get all services
3. list_components_by_stereotype(stereotype="repository") -> get all repositories
4. doc_writer(file_path="c4/c4-component.md", content="# C4 Level 3: Component Diagram\\n\\n## 3.1 Overview\\n...")
5. Respond: "File c4/c4-component.md written successfully."

## YOUR DATA SOURCES
Use these tools (call each ONCE with a SINGLE set of parameters):
1. list_components_by_stereotype(stereotype="controller") - List controllers
2. list_components_by_stereotype(stereotype="service") - List services
3. list_components_by_stereotype(stereotype="repository") - List repositories
4. list_components_by_stereotype(stereotype="entity") - List entities
5. query_facts(category="relations") - Component dependencies

Summary data:
{system_summary}
{components_summary}

## DOCUMENT STRUCTURE

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
"""
)

COMPONENT_DIAGRAM_DESCRIPTION = """
Create a C4 Component DrawIO DIAGRAM.

## EXECUTION STEPS (call each tool exactly ONCE, never as array):
1. query_facts(category="components", stereotype="controller") -> get component counts
2. create_drawio_diagram(file_path="c4/c4-component.drawio", nodes=[...], edges=[...])
3. Respond: "Diagram c4/c4-component.drawio created successfully."

{system_summary}
{components_summary}

Use create_drawio_diagram tool with these specifications:

FILE: c4/c4-component.drawio

LAYOUT (show LAYERS as swimlanes, not individual components):
- Container Boundary: "<Container Name> [<Technology>]"
- Presentation Layer box: Controllers (X components)
- Business Layer box: Services (X components)
- Data Access Layer box: Repositories (X components)
- Domain Layer box: Entities (X components)

CONNECTIONS:
- Arrows between layers showing dependency direction
- Each layer box shows component count

Use query_facts and list_components_by_stereotype to get REAL component counts.
"""

# =============================================================================
# C4 Level 4: Deployment
# =============================================================================

DEPLOYMENT_DOC_DESCRIPTION = (
    TOOL_INSTRUCTION
    + """
Create the COMPLETE C4 Level 4: Deployment Diagram document.

## EXECUTION STEPS (call each tool exactly ONCE, never as array):
1. query_facts(category="containers") -> get container details
2. query_facts(category="relations") -> get deployment dependencies
3. doc_writer(file_path="c4/c4-deployment.md", content="# C4 Level 4: Deployment Diagram\\n\\n## 4.1 Overview\\n...")
4. Respond: "File c4/c4-deployment.md written successfully."

## YOUR DATA SOURCES
Use these tools (call each ONCE with a SINGLE set of parameters):
1. query_facts(category="containers") - Container details
2. query_facts(category="relations") - Deployment dependencies

Summary data:
{system_summary}
{containers_summary}

## DOCUMENT STRUCTURE

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
"""
)

DEPLOYMENT_DIAGRAM_DESCRIPTION = """
Create a C4 Deployment DrawIO DIAGRAM.

## EXECUTION STEPS (call each tool exactly ONCE, never as array):
1. query_facts(category="containers") -> get container data for nodes
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

Use query_facts(category="containers") to get REAL container names.
"""

# =============================================================================
# Quality Gate
# =============================================================================

QUALITY_GATE_DESCRIPTION = """
Quality review of all C4 documents.

READ all C4 files using safe_file_read tool and validate:
1. knowledge/document/c4/c4-context.md
2. knowledge/document/c4/c4-container.md
3. knowledge/document/c4/c4-component.md
4. knowledge/document/c4/c4-deployment.md

Validate:
- All 4 levels complete
- Each level has DrawIO diagram reference
- Content based on REAL facts (component names, counts, relations)
- No placeholder text like "[to be determined]"

Write quality report to: quality/c4-report.md using doc_writer tool.

# C4 Quality Report

| Level | Diagram | Status |
|-------|---------|--------|
| Context | c4-context.drawio | ? |
| Container | c4-container.drawio | ? |
| Component | c4-component.drawio | ? |
| Deployment | c4-deployment.drawio | ? |
"""
