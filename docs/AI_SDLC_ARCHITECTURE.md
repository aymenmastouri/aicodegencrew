# AI-Powered Software Development Lifecycle Architecture

## 1. Introduction

### 1.1 Purpose and Goal

**AICodeGenCrew** is a fully local, on-premises AI-powered blueprint for a complete, end-to-end Software Development Lifecycle (SDLC).

**Use Case:** Provide a fully local / on-prem AI SDLC blueprint (using only on-prem LLMs, no external data transfer) that analyzes an existing repository, generates evidence-based architecture documentation, and supports the full development workflow by creating and then working through backlog items (issues/CRs/tasks): planning, implementing changes, generating tests, running build/CI validations, and finally preparing and merging the delivery end-to-end.

**Why On-Premises?** Enterprise software often contains sensitive intellectual property, customer data, or security-critical code. Sending this data to external AI services (like OpenAI, Anthropic, etc.) may violate compliance requirements, data protection regulations, or internal security policies. AICodeGenCrew is designed to run entirely on your infrastructure with your own LLMs - no data ever leaves your network.

### 1.2 4-Layer Architecture Model

> **Reference Diagrams:**
> - [sdlc-overview.drawio](diagrams/sdlc-overview.drawio) - Full SDLC Pipeline Overview
> - [layer-architecture.drawio](diagrams/layer-architecture.drawio) - Detailed 4-Layer Architecture
> - [phase-flow.drawio](diagrams/phase-flow.drawio) - Phase Flow with Layer Context

The system is organized into 4 distinct layers, each with clear responsibilities:

| Layer | Phases | Purpose | LLM Required |
|-------|--------|---------|--------------|
| **KNOWLEDGE** | 0-1 | Deterministic facts extraction | No |
| **REASONING** | 2-3 | LLM-powered analysis and synthesis | Yes |
| **EXECUTION** | 4-7 | Code generation and deployment | Yes |
| **FEEDBACK** | - | Continuous learning and quality | Yes |

### 1.3 Implementation Status

| Phase | Name | Layer | Type | Status |
|-------|------|-------|------|--------|
| 0 | Indexing | Knowledge | Pipeline | IMPLEMENTED |
| 1 | Architecture Facts | Knowledge | Pipeline | IMPLEMENTED |
| 2 | Architecture Analysis | Reasoning | Crew | IMPLEMENTED |
| 3 | Architecture Synthesis | Reasoning | Crew | IMPLEMENTED |
| 4 | Task Understanding | Reasoning | Crew | PLANNED |
| 5 | Code Generation | Execution | Crew | PLANNED |
| 6 | Test Generation | Execution | Crew | PLANNED |
| 7 | Review + Deploy | Execution | Pipeline | PLANNED |

### 1.4 Key Benefits

**Fully Automated:** No more manual diagram drawing. Point the tool at your repository and receive complete documentation. The AI agents handle everything from component discovery to diagram generation.

**Evidence-Based:** Every statement in the generated documentation is backed by actual code or configuration evidence. No hallucinations, no guesswork. If it is not in your code, it will not appear in the documentation.

**Reproducible:** Run the same analysis twice and get the same results. The deterministic code analysis phase ensures consistency, while the AI synthesis phase is guided by structured schemas.

**Scalable:** Whether your project has 50 components or 100,000, the Map-Reduce architecture handles it. Large repositories are automatically split by container for parallel analysis.

**Standards-Compliant:** The output follows industry-standard formats - C4 model for architectural diagrams and arc42 for comprehensive documentation. These formats are widely recognized and understood by architects worldwide.

### 1.5 What You Get

When you run AICodeGenCrew on your repository, you receive:

- **C4 Diagrams:** Context, Container, Component, and Deployment views as editable DrawIO files
- **arc42 Documentation:** All 12 chapters including introduction, constraints, context, solution strategy, building blocks, runtime scenarios, deployment, and quality requirements
- **Architecture Analysis:** Detected patterns, technology stack, quality assessment, technical debt indicators, and security posture
- **Evidence Map:** Internal traceability from documentation back to source code (for validation)

---

## 2. Executive Summary

This document defines the architecture for a complete **End-to-End AI-Powered Software Development Lifecycle (SDLC) Blueprint**. The system utilizes CrewAI multi-agent workflows with configurable LLM backends on-premise models to automate the entire software development process.

### 2.1 Vision

Establish a fully automated SDLC pipeline that covers:

| Phase | Layer | Capability | Implementation |
|-------|-------|------------|----------------|
| Phase 0: Indexing | Knowledge | Repository analysis, vector storage | Pipeline (ChromaDB) |
| Phase 1: Architecture Facts | Knowledge | Deterministic code analysis | Pipeline (7 Collectors) |
| Phase 2: Architecture Analysis | Reasoning | Multi-agent architecture analysis | Crew (MapReduce) |
| Phase 3: Architecture Synthesis | Reasoning | C4 + arc42 documentation | Crew (Think First) |
| Phase 4: Task Understanding | Reasoning | RAG-enhanced planning | Crew (Planned) |
| Phase 5: Code Generation | Execution | Feature implementation | Crew (Planned) |
| Phase 6: Test Generation | Execution | Test creation | Crew (Planned) |
| Phase 7: Review + Deploy | Execution | CI/CD integration | Pipeline (Planned) |

### 2.2 Core Principles

| Principle | Description |
|-----------|-------------|
| Evidence-First | Every statement must be backed by code/config evidence |
| Deterministic Discovery | LLMs synthesize, they do not discover - facts come from code analysis |
| Think First | Agents analyze before documenting (analyze_system task) |
| Phase Isolation | Each phase has clear inputs/outputs, no cross-phase dependencies |
| Incremental Adoption | Phases can be executed independently |
| Clean Output | No evidence IDs in final documentation |

### 2.3 Current Focus: Knowledge Layer (Phases 0-1)

The initial implementation focuses on architecture facts extraction:

| Area | Implementation | Status |
|------|----------------|--------|
| **Phase 0 Indexing** | ChromaDB vector storage | IMPLEMENTED |
| **Phase 1 Facts** | 7 Collectors | IMPLEMENTED |
| **Phase 2 Analysis** | MapReduce multi-agent analysis | IMPLEMENTED |
| **Phase 3 Synthesis** | C4 + arc42 Crews | IMPLEMENTED |
| **Evidence Traceability** | evidence_map.json | IMPLEMENTED |

### 2.4 Phase 1 Results (Current)

| Metric | Value |
|--------|-------|
| Components | 738 |
| Interfaces | 125 |
| Relations | 169 (raw), target 85%+ resolved |
| Evidence Items | 1005 |
| Relation Resolution | 7-tier resolver (see 4.2.1) |
| Endpoint Flows | Controller-Service-Repository chains (see 4.2.2) |

---

## 3. Architecture Overview

> **Reference Diagrams:**
> - [sdlc-overview.drawio](diagrams/sdlc-overview.drawio) - Full 4-Layer SDLC Overview
> - [layer-architecture.drawio](diagrams/layer-architecture.drawio) - Detailed Layer Architecture
> - [phase-flow.drawio](diagrams/phase-flow.drawio) - Pipeline Flow (Phases 0-7)
> - [evidence-flow.drawio](diagrams/evidence-flow.drawio) - Evidence Data Flow
> - [knowledge-structure.drawio](diagrams/knowledge-structure.drawio) - Knowledge Base Structure
> - [collectors.drawio](diagrams/collectors.drawio) - Phase 1 Collectors
> - [synthesis-crew.drawio](diagrams/synthesis-crew.drawio) - Phase 2 Synthesis Crew

### 3.1 Core Principle: Evidence-First Architecture

> See [phase-flow.drawio](diagrams/phase-flow.drawio) for the full 4-layer pipeline diagram.

**Key Rules:**
- Phase 1 produces facts and evidence (deterministic, no LLM)
- Phase 2 synthesizes documentation from facts only
- If it is not in `architecture_facts.json`, it must NOT appear in output
- Evidence IDs are for internal processing only, NOT in final documentation
- Feedback loop updates knowledge base continuously

### 3.2 Component Classification

| Classification | Layer | LLM Requirement | Phases |
|----------------|-------|-----------------|--------|
| Pipeline | Knowledge | None (Embeddings for Phase 0) | 0, 1, 6, 7 |
| Crew | Reasoning/Execution | Full LLM | 2, 3, 4, 5 |

### 3.3 Core Modules

| Module | Location | Responsibility |
|--------|----------|----------------|
| **Orchestrator** | `orchestrator.py` | Phase coordination (register - run) |
| CLI | `cli.py` | Command-line interface |
| Pipelines | `pipelines/` | Deterministic processes (Phase 0, 1) |
| Crews | `crews/` | AI agent workflows (Phase 2+) |
| Shared | `shared/` | Common utilities, models, tools |

### 3.4 SDLCOrchestrator Design

The orchestrator follows clean architecture principles:

```python
# Simple, explicit API
orchestrator = SDLCOrchestrator()
orchestrator.register("phase0_indexing", IndexingPipeline(...))
orchestrator.register("phase1_architecture_facts", ArchFactsPipeline(...))
orchestrator.register("phase2_architecture_analysis", AnalysisCrew(...))
orchestrator.register("phase3_architecture_synthesis", SynthesisCrew(...))

result = orchestrator.run(preset="architecture_workflow")
```

| Principle | Implementation |
|-----------|----------------|
| **Single Responsibility** | Only orchestrates, no business logic |
| **Dependency Injection** | Phases are registered, not hardcoded |
| **Fail Fast** | Stops on first error by default |
| **Protocol-based** | Any class with `kickoff()` or `run()` works |
| **Data Classes** | `PhaseResult`, `PipelineResult` for clarity |
| **Phase Validation** | `PhaseOutputValidator` checks outputs between phases |
| **Strict CLI** | Preset/phase names validated against `phases_config.yaml` |

### 3.5 Mini-Crews Pattern (Phase 3)

Phase 3 uses the **Mini-Crews Pattern** instead of a single large Crew:

```
OLD: 1 Crew with 26 sequential tasks → Context overflow after task ~10-15
NEW: 5 Mini-Crews (2-3 tasks each) → Fresh context per level, no overflow
```

Each Mini-Crew:
- Gets a **fresh agent** with a **fresh LLM context window**
- Receives data via **template variables** (summaries), not inter-task context
- Is **checkpointed** after completion for resume-on-failure

```
C4Crew.run():
  Mini-Crew 1: Context   (doc + diagram) → checkpoint
  Mini-Crew 2: Container (doc + diagram) → checkpoint
  Mini-Crew 3: Component (doc + diagram) → checkpoint
  Mini-Crew 4: Deployment (doc + diagram) → checkpoint
  Mini-Crew 5: Quality Gate              → checkpoint
```

This prevents the context overflow that occurs when CrewAI accumulates
internal conversation history across many sequential tasks.

### 3.6 MiniCrewBase Architecture

Both C4Crew and Arc42Crew inherit from `MiniCrewBase` (ABC):

```python
class MiniCrewBase(ABC):
    # Shared infrastructure:
    _create_llm()           # LLM factory from env vars
    _create_agent()         # Agent with MCP + tools
    _run_mini_crew()        # Execute crew with fresh context
    _save_checkpoint()      # Persist progress for resume
    _extract_token_usage()  # Track token consumption

    # Subclasses implement:
    crew_name: str          # "C4" or "Arc42"
    agent_config: dict      # {"role": ..., "goal": ..., "backstory": ...}
    _summarize_facts()      # Create template variables
    run()                   # Execute all mini-crews
```

| Feature | Description |
|---------|-------------|
| **Checkpoint Resume** | `.checkpoint_c4.json` / `.checkpoint_arc42.json` |
| **Token Tracking** | Per mini-crew token usage with summary |
| **MCP Singleton** | MCP server path resolved once, reused |
| **Structured Metrics** | `log_metric()` writes to `metrics.jsonl` |

---

## 4. Project Structure

```
src/aicodegencrew/
    __init__.py
    __main__.py
    cli.py                             # Strict preset validation from config
    orchestrator.py                    # Phase coordination + dependency validation

    crews/
        __init__.py

        architecture_analysis/         # Phase 2: Architecture Analysis
            __init__.py
            crew.py                    # ArchitectureAnalysisCrew (5 mini-crews, all Python)
            mapreduce_crew.py          # MapReduceAnalysisCrew (large repos)
            container_crew.py          # ContainerAnalysisCrew (per-container)
            tools/
                __init__.py
                rag_query_tool.py      # ChromaDB semantic search

        architecture_synthesis/        # Phase 3: Architecture Synthesis
            __init__.py
            crew.py                    # ArchitectureSynthesisCrew (orchestrator)
            base_crew.py               # MiniCrewBase ABC (shared infrastructure)

            c4/                        # C4 Mini-Crews (5 crews)
                __init__.py
                crew.py                # C4Crew(MiniCrewBase) - all Python, no YAML

            arc42/                     # Arc42 Mini-Crews (15 crews)
                __init__.py
                crew.py                # Arc42Crew(MiniCrewBase) - all Python, no YAML

            tools/                     # Crew tools
                __init__.py
                file_read_tool.py      # Read JSON/text files
                doc_writer_tool.py     # Write markdown (with path-stripping)
                drawio_tool.py         # Create DrawIO diagrams (with path-stripping)
                facts_query_tool.py    # Query architecture facts
                chunked_writer_tool.py # ChunkedWriterTool + StereotypeListTool

    pipelines/
        __init__.py
        indexing.py                    # Backward compat

        indexing/                      # Phase 0: Repository Indexing
            __init__.py
            pipeline.py               # IndexingPipeline
            indexing_pipeline.py       # ensure_repo_indexed
            ...

        architecture_facts/            # Phase 1: Architecture Facts
            __init__.py
            pipeline.py               # ArchitectureFactsPipeline
            collectors/                # Dimension + Specialist collectors
                orchestrator.py        # CollectorOrchestrator
                spring/                # Spring Boot specialists
                angular/               # Angular specialists
                database/              # Database specialists
            model_builder.py           # Canonical ID generation + 7-tier resolver
            endpoint_flow_builder.py   # Controller→Service→Repository chains
            dimension_writers.py
            collectors/
                fact_adapter.py        # RawFact→CollectedComponent/Interface/Relation

    shared/
        __init__.py
        validation.py                  # PhaseOutputValidator (inter-phase contracts)
        utils/
            logger.py                  # Logger + JsonFormatter + log_metric()
            token_budget.py            # Token budget configuration
            file_filters.py
            crew_callbacks.py
            ollama_client.py
        models/
            __init__.py
            architecture_facts_schema.py  # Pydantic schema for Phase 1
            analysis_schema.py            # Pydantic schema for Phase 2

    mcp/
        server.py                      # MCP knowledge server (STDIO)
        knowledge_tools.py             # MCP tool implementations
```

---

## 4. Phase Specifications

### 4.1 Phase 0: Repository Indexing

| Attribute | Specification |
|-----------|---------------|
| Type | Pipeline (deterministic) |
| Module | `pipelines/indexing/pipeline.py` |
| LLM Requirement | None (embeddings only) |
| Output | `.cache/.chroma` (ChromaDB) |
| Dependency | None |
| Status | Implemented |

#### Processing Steps

| Step | Component | Function |
|------|-----------|----------|
| 1 | RepoDiscoveryTool | Filesystem traversal with filtering |
| 2 | RepoReaderTool | Content extraction |
| 3 | ChunkerTool | Semantic segmentation |
| 4 | OllamaEmbeddingsTool | Vector generation (Ollama) |
| 5 | ChromaIndexTool | Vector persistence |

---

### 4.2 Phase 1: Architecture Facts (CRITICAL!)

| Attribute | Specification |
|-----------|---------------|
| Type | Pipeline (deterministic, **NO LLM!**) |
| Module | `pipelines/architecture_facts/` |
| LLM Requirement | **NONE** |
| Output | `knowledge/architecture/architecture_facts.json` |
|        | `knowledge/architecture/evidence_map.json` |
| Dependency | Phase 0 |

#### Purpose

**Phase 1 creates the SINGLE SOURCE OF TRUTH for architecture.**
- No interpretation
- No LLM
- No documentation
- Only Facts + Evidence

**Everything not in Phase 1 output must NOT be written by Phase 2!**

#### What Gets Extracted

| Category | Items | Evidence Required |
|----------|-------|-------------------|
| System | Repository name, domain | Yes |
| Containers | Backend, Frontend, DB, Infra | Yes |
| Components | @RestController, @Service, @Repository, @Component | Yes |
| Interfaces | REST endpoints, Routes | Yes |
| Relations | Constructor injection, imports | Yes |

#### Collector Architecture (Modular)

> **Reference Diagram:** [collectors.drawio](diagrams/collectors.drawio)

The collector system uses a modular architecture with an **Orchestrator** that coordinates **Dimension Collectors** and **Specialist Collectors**.

**Orchestrator** (`collectors/orchestrator.py`):
- `CollectorOrchestrator`: Runs all collectors in sequence, returns `DimensionResults`
- 8-step flow: System → Container → Component → Interface → DataModel → Runtime → Infrastructure → Evidence

**Dimension Collectors**:
| Collector | Output | Description |
|-----------|--------|-------------|
| `SystemCollector` | system.json | System metadata from root files |
| `ContainerCollector` | containers.json | Deployable units (pom.xml, package.json, Dockerfile) |
| `ComponentCollector` | components.json | Aggregates Spring + Angular specialists |
| `InterfaceCollector` | interfaces.json | REST endpoints, routes, schedulers |
| `DataModelCollector` | data_model.json | JPA entities, SQL tables, migrations |
| `RuntimeCollector` | runtime.json | Schedulers, async, events |
| `InfrastructureCollector` | infrastructure.json | Docker, K8s, CI/CD |
| `EvidenceCollector` | evidence_map.json | Aggregates all evidence |

**Specialist Collectors** (`collectors/spring/`, `collectors/angular/`, `collectors/database/`):
| Specialist | Package | Extracts |
|------------|---------|----------|
| `SpringRestCollector` | spring/ | @RestController, @RequestMapping |
| `SpringServiceCollector` | spring/ | @Service, interface+impl mappings |
| `SpringRepositoryCollector` | spring/ | JpaRepository, custom queries |
| `SpringConfigCollector` | spring/ | @Configuration, application.yml |
| `SpringSecurityCollector` | spring/ | Security configs |
| `AngularModuleCollector` | angular/ | @NgModule |
| `AngularComponentCollector` | angular/ | @Component |
| `AngularServiceCollector` | angular/ | @Injectable services |
| `AngularRoutingCollector` | angular/ | RouterModule, routes |
| `OracleTableCollector` | database/ | CREATE TABLE (multi-dialect) |
| `MigrationCollector` | database/ | Flyway, Liquibase |

#### Additional Components

| Component | Purpose |
|-----------|---------|
| `FactAdapter` | Converts RawFact types to CollectedComponent/Interface/Relation (see 4.2.3) |
| `ModelBuilder` | Deduplication, canonical ID generation, 7-tier relation resolution (see 4.2.1) |
| `EndpointFlowBuilder` | Builds request flow chains Controller→Service→Repository (see 4.2.2) |
| `QualityValidator` | Validates extracted facts for completeness |
| `FactsWriter` | Writes architecture_facts.json and evidence_map.json |

#### Output Schema

```json
{
  "system": {
    "id": "system",
    "name": "Repository Name",
    "domain": "UNKNOWN"
  },
  "containers": [
    {"id": "backend", "name": "backend", "type": "application", 
     "technology": "Spring Boot", "evidence": ["ev_0001"]}
  ],
  "components": [
    {"id": "workflow_service", "container": "backend", 
     "name": "WorkflowServiceImpl", "stereotype": "service",
     "evidence": ["ev_0002"]}
  ],
  "interfaces": [
    {"id": "workflow_api", "container": "backend", "type": "REST",
     "path": "/workflow/**", "implemented_by": "WorkflowController",
     "evidence": ["ev_0003"]}
  ],
  "relations": [
    {"from": "workflow_service", "to": "workflow_repository",
     "type": "uses", "evidence": ["ev_0004"]}
  ]
}
```

#### Evidence Map

```json
{
  "ev_0001": {
    "path": "backend/pom.xml",
    "lines": "1-20",
    "reason": "Spring Boot dependency detected"
  },
  "ev_0002": {
    "path": "backend/src/.../WorkflowServiceImpl.java",
    "lines": "12-85",
    "reason": "@Service annotated class"
  }
}
```

#### Rules (MUST FOLLOW!)

| DO | DO NOT |
|-------|-----------|
| Extract only detectable facts | Use LLM |
| Reference evidence for every fact | Describe responsibilities |
| Mark UNKNOWN if no evidence | Make architecture decisions |
| Use exact class/file names | Define flows or sequences |
|  | Summarize or interpret |

#### 4.2.1 Relation Resolution Pipeline

Relations are collected as `RelationHint` objects by specialist collectors (e.g., constructor injection in `SpringServiceCollector`). These carry **disambiguation hints** to improve resolution accuracy:

| Field | Purpose | Example |
|-------|---------|---------|
| `from_name` / `to_name` | Raw component names | `"ActionRestServiceImpl"` → `"ActionService"` |
| `from_stereotype_hint` | Source stereotype | `"service"` |
| `to_stereotype_hint` | Target stereotype | `"repository"` |
| `from_file_hint` | Source file path | `"backend/src/.../ActionRestServiceImpl.java"` |
| `to_file_hint` | Target file path | (optional) |

**FactAdapter** (`collectors/fact_adapter.py`) converts `RelationHint` → `CollectedRelation`, preserving all hints. The `DimensionResultsAdapter` also extracts hints from serialized dict format.

**ModelBuilder** (`model_builder.py`) resolves raw names to canonical IDs using a **7-tier fallback**:

| Tier | Strategy | Example |
|------|----------|---------|
| 1 | Direct old-ID mapping | `"comp_1_ActionService"` → canonical |
| 2 | Already canonical | `"component.backend.service.action_service"` |
| 3 | Exact name match (unambiguous) | `"ActionService"` → 1 candidate |
| 4 | Disambiguate by stereotype hint | `"service:ActionService"` → unique |
| 5 | Interface-to-implementation | `"OrderService"` → `"OrderServiceImpl"` |
| 6 | Fuzzy suffix match | `"UserService"` ↔ `"UserServiceImpl"` |
| 7 | File path match | `from_file_hint` → component owning that file |

Enhanced indices built during `_normalize_components()`:
- `_name_to_component_ids`: Multi-value (name → list of canonical IDs)
- `_stereotype_name_to_id`: `"stereotype:name"` → canonical ID
- `_file_to_component_id`: File path → canonical ID
- `_interface_to_impl_name`: `"OrderService"` → `"OrderServiceImpl"`

#### 4.2.2 Endpoint Flow Builder

`EndpointFlowBuilder` (`endpoint_flow_builder.py`) constructs evidence-based request chains from REST interfaces:

```
Interface: POST /workflow/create
  → Controller: WorkflowController (via implemented_by)
    → Service: WorkflowServiceImpl (via relation: uses)
      → Repository: WorkflowRepository (via relation: uses)
```

**Key implementation details:**
- `implemented_by` field on `CollectedInterface` links REST endpoints to controllers
- Relations use raw component **names** (not adapter IDs), so chain following uses `_id_to_name` reverse lookup
- Chain depth limited to 5 levels to prevent explosion
- Stereotype-based priority sorting: controller(0) → service(1) → repository(2) → entity(3)
- Only flows with 2+ chain elements are included in output

#### 4.2.3 FactAdapter Pipeline

The `FactAdapter` bridges new collector outputs (Raw types) to legacy types consumed by `ModelBuilder`:

```
Collectors (RawComponent, RawInterface, RelationHint)
    │
    ▼
FactAdapter.to_collected_component()   → CollectedComponent
FactAdapter.to_collected_interface()   → CollectedInterface  (with implemented_by)
FactAdapter.to_collected_relation()    → CollectedRelation   (with disambiguation hints)
    │
    ▼
DimensionResultsAdapter.convert()      → Dict consumed by ModelBuilder
    │
    ▼
ModelBuilder.build()                   → CanonicalModel (normalized, deduplicated)
```

**Key transformations:**
- `RawInterface.implemented_by_hint` → `CollectedInterface.implemented_by`
- `RelationHint.evidence` (list) → iterated individually for evidence IDs
- `RelationHint.type` → `CollectedRelation.relation_type`
- Disambiguation hints (`from_stereotype_hint`, `to_stereotype_hint`, `from_file_hint`, `to_file_hint`) propagated through the full pipeline

---

### 4.3 Phase 2: Architecture Analysis (Mini-Crews Pattern)

> **Reference Diagram:** [docs/diagrams/analysis-crew.drawio](diagrams/analysis-crew.drawio)

| Attribute | Specification |
|-----------|---------------|
| Type | Crew (AI Agents) - Mini-Crews Pattern |
| Module | `crews/architecture_analysis/crew.py` |
| Config | Python constants (no YAML) |
| LLM Requirement | Yes |
| Input | `architecture_facts.json` + ChromaDB Index |
| Output | `knowledge/architecture/analyzed_architecture.json` |
| Checkpoint | `.checkpoint_analysis.json` (resume on failure) |
| Dependency | Phase 0 (Index) + Phase 1 (Facts) |
| Status | Implemented |

#### Mini-Crew Architecture

The Analysis Crew uses **5 mini-crews** with **4 specialized agent types**,
each mini-crew getting a fresh agent and fresh LLM context window.
See the detailed diagram: [analysis-crew.drawio](diagrams/analysis-crew.drawio)

| Mini-Crew | Agent | Tasks | Output Files |
|-----------|-------|-------|-------------|
| `tech_analysis` | tech_architect | 4: macro, backend, frontend, quality | `01-04_*.json` |
| `domain_analysis` | func_analyst | 4: domain, capabilities, contexts, states | `05-08_*.json` |
| `workflow_analysis` | func_analyst | 4: workflows, sagas, runtime, api | `09-12_*.json` |
| `quality_analysis` | quality_analyst | 4: complexity, debt, security, ops | `13-16_*.json` |
| `synthesis` | synthesis_lead | 1: merge all 16 results | `analyzed_architecture.json` |

#### Agents and Responsibilities

| Agent | Focus | Uses Facts For | Uses RAG For |
|-------|-------|---------------|--------------|
| **Technical Architect** | Technical structure | `architecture_style`, `design_pattern` | Implementation patterns in code |
| **Functional Analyst** | Business domain | `entity`, `service` | Business logic, Javadoc, comments |
| **Quality Analyst** | Quality attributes | All stereotypes | Error handling, logging, tests |
| **Synthesis Lead** | Integration | All outputs | Conflict resolution |

#### Output: analyzed_architecture.json

```json
{
  "system": {
    "name": "uvz",
    "domain": "Deed Management Platform",
    "description": "Notary deed registration and workflow system"
  },
  "architecture": {
    "primary_style": "layered_architecture",
    "secondary_styles": ["modular_monolith"],
    "evidence_ids": ["ev_arch_0049", "ev_arch_0061"]
  },
  "patterns": [
    {"name": "repository_pattern", "evidence_count": 4},
    {"name": "factory_pattern", "evidence_count": 6}
  ],
  "capabilities": [
    {"name": "Deed Management", "key_components": ["DeedEntryService", "DeedRegistryService"]},
    {"name": "Workflow Processing", "key_components": ["WorkflowService", "ActionService"]}
  ],
  "quality_attributes": {
    "maintainability": {"level": "high", "reason": "Layered + Repository pattern"},
    "scalability": {"level": "medium", "reason": "Monolith, not distributed"}
  },
  "risks": [
    {"name": "Large monolith", "severity": "medium", "mitigation": "Consider modularization"}
  ]
}
```

#### Benefits of Multi-Agent Analysis

| Benefit | Description |
|---------|-------------|
| **Specialization** | Each agent focuses on their expertise area |
| **Less Hallucination** | Specific tasks = better accuracy |
| **Reusable Output** | JSON can be used by multiple downstream crews |
| **Traceable** | Separate analyses can be reviewed individually |

#### Deep Analysis Mode and Token Management

LLM token limits are always present. Deep Analysis does NOT mean unlimited tokens.
Instead, it uses strategies to analyze MORE data within the same context window:

| Aspect | Standard Mode | Deep Analysis Mode |
|--------|---------------|-------------------|
| Tool calls per agent | 5-10 | 20-50 |
| Runtime | 2-5 minutes | 30-40 minutes |
| max_iter (CrewAI) | 25 | 50 |
| Query limit | 50 items | 500 items |

**Token Management Strategies:**

1. **Chunked Queries**: Instead of 1 query returning 10,000 items (token overflow), 
   use 20 queries returning 500 items each. Agent processes incrementally.

2. **Truncation**: Long descriptions are cut to 80-100 characters in tool output.
   Full text remains in ChromaDB for RAG queries when needed.

3. **Temp Output Files**: Each agent writes results to a file, not kept in context.
   Synthesis agent reads files, not entire conversation history.

4. **Forgetting Old Results**: CrewAI naturally "forgets" older tool results as
   conversation grows. New queries replace old data in working memory.

> See [synthesis-crew.drawio](diagrams/synthesis-crew.drawio) for the agent context window layout.

**Configuration (Python constants in crew.py):**

```python
AGENT_CONFIGS = {
    "tech_architect": {"role": "Senior Technical Architect", ...},
    "func_analyst":   {"role": "Senior Functional Analyst", ...},
    "quality_analyst": {"role": "Senior Quality Architect", ...},
    "synthesis_lead":  {"role": "Lead Architect - Synthesis", ...},
}
```
| **RAG Integration** | Semantic code search adds context beyond structure |

---

### 4.4 Phase 3: Architecture Synthesis (Mini-Crews Pattern)

| Attribute | Specification |
|-----------|---------------|
| Type | Crew (AI Agents) - Mini-Crews Pattern |
| Module | `crews/architecture_synthesis/` |
| Base Class | `base_crew.py` → `MiniCrewBase` (ABC) |
| LLM Requirement | Yes |
| Input | `architecture_facts.json` (Phase 1) + `analyzed_architecture.json` (Phase 2) |
| Input (optional) | ChromaDB Index (via MCP server) |
| Output | `knowledge/architecture/c4/` (DrawIO + Markdown) |
|        | `knowledge/architecture/arc42/` (Markdown) |
|        | `knowledge/architecture/quality/` (Reports) |
| Dependency | Phase 1 + Phase 2 (validated by `PhaseOutputValidator`) |
| Status | Implemented |

#### Why Mini-Crews?

**Problem:** CrewAI accumulates internal conversation history across sequential tasks.
With 26+ tasks in one Crew, the prompt exceeds the model's context window (~120k tokens)
after ~10-15 tasks, causing `max_tokens must be at least 1, got -8424` errors.

**Solution:** Split into multiple small Crews (2-3 tasks each), each with a **fresh agent
and fresh LLM context**. Data is passed via template variables, not inter-task context.

#### Orchestration

```
ArchitectureSynthesisCrew.run():
    C4Crew.run()     → 5 Mini-Crews (9 tasks total)
    Arc42Crew.run()  → 7 Mini-Crews (14 tasks total)
```

Both inherit from `MiniCrewBase` which provides shared infrastructure.

#### C4Crew: 5 Mini-Crews (9 tasks)

| Mini-Crew | Tasks | Output |
|-----------|-------|--------|
| `context` | doc + diagram | `c4/c4-context.md` + `.drawio` |
| `container` | doc + diagram | `c4/c4-container.md` + `.drawio` |
| `component` | doc + diagram | `c4/c4-component.md` + `.drawio` |
| `deployment` | doc + diagram | `c4/c4-deployment.md` + `.drawio` |
| `quality` | validation | `quality/c4-report.md` |

#### Arc42Crew: 7 Mini-Crews (14 tasks)

| Mini-Crew | Chapters | Output |
|-----------|----------|--------|
| `intro-constraints` | 1-2 | `01-introduction.md`, `02-constraints.md` |
| `context-strategy` | 3-4 | `03-context.md`, `04-solution-strategy.md` |
| `building-blocks` | 5 | `05-building-blocks.md` (largest chapter) |
| `runtime-deployment` | 6-7 | `06-runtime-view.md`, `07-deployment.md` |
| `crosscutting-decisions` | 8-9 | `08-crosscutting.md`, `09-decisions.md` |
| `quality-risks-glossary` | 10-12 | `10-quality.md`, `11-risks.md`, `12-glossary.md` |
| `quality-gate` | validation | `quality/arc42-report.md` |

#### Task Descriptions as Python Constants

Task descriptions are defined as Python multiline strings (not YAML), prefixed with
`TOOL_INSTRUCTION` that forces the agent to use the `doc_writer` tool:

```python
TOOL_INSTRUCTION = """
CRITICAL INSTRUCTION: You MUST use the doc_writer tool to write the output file.
STEP 1: Use MCP tools to gather data.
STEP 2: Use doc_writer(file_path="...", content="...") to write the complete document.
STEP 3: Respond with a brief confirmation that the file was written.
"""

CONTEXT_DOC_DESCRIPTION = TOOL_INSTRUCTION + """
Create the COMPLETE C4 Level 1: System Context document.
...
"""
```

This solved the problem of agents writing document content in their response text
instead of calling the tool.

#### Checkpoint Resume

Each mini-crew is checkpointed after completion. If a run fails at mini-crew 4,
re-running skips mini-crews 1-3 automatically:

```json
// .checkpoint_c4.json
{
  "completed_crews": ["context", "container", "component"],
  "checkpoints": [
    {"crew": "context", "status": "completed", "duration_seconds": 180.5},
    ...
  ]
}
```

#### Tools

| Tool | Purpose |
|------|---------|
| `FileReadTool` | Read JSON/text files |
| `DocWriterTool` | Write markdown (with path-stripping for double-nesting bug) |
| `DrawioDiagramTool` | Create DrawIO diagrams (with path-stripping) |
| `FactsQueryTool` | Query architecture facts by category |
| `StereotypeListTool` | List components by stereotype |
| `ChunkedWriterTool` | Write large documents in sections (Arc42 only) |
| `RAGQueryTool` | ChromaDB semantic search |
| **MCP Tools** | `get_statistics()`, `get_architecture_summary()`, `get_endpoints()`, etc. |

#### MCP Server Integration

Each agent connects to an MCP knowledge server (`mcp_server.py`) via STDIO,
providing token-efficient access to architecture facts without loading full JSON:

| MCP Tool | Purpose | Tokens Saved |
|----------|---------|--------------|
| `get_statistics()` | Component counts, metrics | ~90% vs full JSON |
| `get_architecture_summary()` | Patterns, styles | ~95% vs full JSON |
| `search_components(query)` | Find specific components | ~98% vs full JSON |
| `list_components_by_stereotype(stereo)` | Layer-specific lists | ~95% vs full JSON |

#### Output Structure

```
knowledge/architecture/
    architecture_facts.json     # From Phase 1
    evidence_map.json           # From Phase 1
    analyzed_architecture.json  # From Phase 2
    .checkpoint_c4.json         # Resume checkpoint (temporary)
    .checkpoint_arc42.json      # Resume checkpoint (temporary)
    c4/
        c4-context.md           # Level 1 (6-8 pages)
        c4-context.drawio
        c4-container.md         # Level 2 (6-8 pages)
        c4-container.drawio
        c4-component.md         # Level 3 (6-8 pages)
        c4-component.drawio
        c4-deployment.md        # Level 4 (4-6 pages)
        c4-deployment.drawio
    arc42/
        01-introduction.md      # Chapter 1 (8-10 pages)
        02-constraints.md       # Chapter 2 (6-8 pages)
        03-context.md           # Chapter 3 (8-10 pages)
        04-solution-strategy.md # Chapter 4 (8-10 pages)
        05-building-blocks.md   # Chapter 5 (20-25 pages, largest)
        06-runtime-view.md      # Chapter 6 (8-10 pages)
        07-deployment.md        # Chapter 7 (6-8 pages)
        08-crosscutting.md      # Chapter 8 (8-10 pages)
        09-decisions.md         # Chapter 9 (8 pages)
        10-quality.md           # Chapter 10 (6 pages)
        11-risks.md             # Chapter 11 (6 pages)
        12-glossary.md          # Chapter 12 (4 pages)
    quality/
        c4-report.md            # C4 quality gate report
        arc42-report.md         # Arc42 quality gate report
```

#### Rules (MUST FOLLOW!)

| DO | DO NOT |
|-------|-----------|
| Use ONLY data from facts.json | Invent containers |
| Query MCP tools for real data | Invent components |
| Use doc_writer tool for output | Write content in response text |
| Use exact names from facts | Add business context |
| Write readable documentation | Clutter output with evidence IDs |
| Use DrawIO for diagrams (XML) | Use Mermaid or ASCII diagrams |

---

### 4.5 Phase 4: Task Understanding (PLANNED)

| Attribute | Specification |
|-----------|---------------|
| Type | Crew or Rules-based |
| Purpose | Ensure consistency across outputs |
| Status | Planned |

#### Tasks

- Facts <-> C4 <-> arc42 consistency check
- Missing evidence detection
- Naming/term unification
- Report generation

---

### 4.6 Phase 5: Code Generation (PLANNED)

| Attribute | Specification |
|-----------|---------------|
| Type | Crew |
| Purpose | Derive work items from architecture |
| Status | Planned |

#### Tasks

- Architecture debt/risk -> JIRA items
- Refactoring/Test/Observability spikes
- Optional: Code changes/PR proposals

---

## 5. Knowledge Management

> **Reference Diagrams:**
> - [docs/diagrams/knowledge-structure.drawio](docs/diagrams/knowledge-structure.drawio)
> - [docs/diagrams/evidence-flow.drawio](docs/diagrams/evidence-flow.drawio)

### 5.1 Data Flow Matrix

| Source Phase | Output Artifact | Consumer Phase |
|--------------|-----------------|----------------|
| Phase 0 | ChromaDB Vector Index | Phase 1, Phase 2, Phase 3 (optional) |
| Phase 1 | `architecture_facts.json` | Phase 2, Phase 3 |
| Phase 1 | `evidence_map.json` | Phase 2, Phase 3 |
| Phase 2 | `analyzed_architecture.json` | Phase 3 |
| Phase 3 | `c4/*.md`, `c4/*.drawio` | Phase 4 |
| Phase 3 | `arc42/*.md` | Phase 4 |
| Phase 4 | Quality Reports | Phase 5 |

### 5.2 Knowledge Directory Structure

```
knowledge/
    README.md
    user_preference.txt
    
    architecture/
        architecture_facts.json     # From Phase 1 (truth)
        evidence_map.json           # From Phase 1 (evidence)
        
        c4/                         # From Phase 3 (C4Crew)
            c4-context.md
            c4-context.drawio
            c4-container.md
            c4-container.drawio
            c4-component.md
            c4-component.drawio
            c4-deployment.md
            c4-deployment.drawio

        arc42/                      # From Phase 3 (Arc42Crew)
            01-introduction.md
            02-constraints.md
            03-context.md
            04-solution-strategy.md
            05-building-blocks.md   # Chunked: Controllers, Services, Entities, Repositories
            06-runtime-view.md
            07-deployment.md
            08-crosscutting.md
            09-decisions.md
            10-quality.md
            11-risks.md
            12-glossary.md
            
        quality/                    # From Phase 3
            arc42-report.md
            
        html/                       # Generated reports
        confluence/                 # Export formats
        adr/                        # Architecture decisions
        
    analysis/
    development/
```

### 5.3 Evidence Traceability

Evidence traceability is maintained through `architecture_facts.json` and `evidence_map.json`.
The agent uses evidence during processing to ensure accuracy, but the final documentation
is written in clean, readable form:

```markdown
## Backend Container

The **backend** container uses Spring Boot 3.2.

### Components

- **WorkflowServiceImpl** - Business logic for workflow management
  - Uses: WorkflowRepository for data persistence
```

For audit/validation, the Quality Gate can verify that all documented components
exist in `architecture_facts.json`.

---

## 6. Configuration

### 6.1 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PROJECT_PATH` | Target repository path | Required |
| `OLLAMA_BASE_URL` | Ollama server endpoint | `http://127.0.0.1:11434` |
| `MODEL` | LLM model identifier | `gpt-oss-120b` |
| `EMBED_MODEL` | Embedding model identifier | `all-minilm:latest` |
| `INDEX_MODE` | Indexing behavior | `auto` |
| `LLM_PROVIDER` | LLM provider selection | `local` |

### 6.2 LLM Provider Configuration

| Provider | Configuration | Notes |
|----------|---------------|-------|
| Local | `LLM_PROVIDER=local` | Ollama local instance |
| On-Premise | `LLM_PROVIDER=onprem` | Requires `API_BASE_URL` |

Embeddings utilize local Ollama exclusively, independent of LLM provider configuration.

### 6.3 INDEX_MODE Configuration

| Mode | Description |
|------|-------------|
| `off` | Skip indexing; utilize existing index |
| `auto` | Conditional indexing based on change detection (default) |
| `force` | Clear cache and perform complete re-indexing |
| `smart` | Incremental update for modified files only |

---

## 7. Execution Presets

Presets are defined in `config/phases_config.yaml` and validated strictly by the CLI.
Unknown presets raise an error instead of silently falling back.

| Preset | Phases | Description |
|--------|--------|-------------|
| `indexing_only` | 0 | Repository indexing only |
| `facts_only` | 0, 1 | Indexing + Architecture Facts (no LLM) |
| `analysis_only` | 0, 1, 2 | Indexing + Facts + Analysis |
| `architecture_workflow` | 0, 1, 2, 3 | Full architecture documentation |
| `architecture_full` | 0, 1, 2, 3, 4 | Architecture + Review (with consistency checks) |
| `full_pipeline` | 0-8 | Complete automated SDLC pipeline (future) |

---

## 8. Command Reference

### 8.1 Phase Listing

```bash
python -m aicodegencrew list
```

### 8.2 Preset Execution

```bash
# Only extract facts (no LLM)
python -m aicodegencrew run --preset facts_only

# Full architecture documentation (C4 + arc42)
python -m aicodegencrew run --preset architecture_workflow

# Analysis only (no synthesis)
python -m aicodegencrew run --preset analysis_only
```

### 8.3 Single Phase Execution

```bash
# Phase 1: Architecture Facts
python -m aicodegencrew run --phases phase1_architecture_facts

# Phase 2: Architecture Analysis
python -m aicodegencrew run --phases phase2_architecture_analysis

# Phase 3: Architecture Synthesis (C4 + arc42)
python -m aicodegencrew run --phases phase3_architecture_synthesis
```

### 8.4 Options

| Option | Description |
|--------|-------------|
| `--preset NAME` | Run a named preset (validated against config) |
| `--phases P1 P2` | Run specific phases by ID |
| `--repo-path PATH` | Target repository path |
| `--index-mode MODE` | Override INDEX_MODE (`off`, `auto`, `force`, `smart`) |
| `--clean` | Clean knowledge directories before running |
| `--no-clean` | Skip auto-cleaning |
| `--config PATH` | Custom phases_config.yaml path |

---

## 9. Logging System

### 9.1 Log Structure

```
logs/
├── current.log          # Active session (overwritten each run)
├── metrics.jsonl         # Structured JSON metrics (append-only)
├── archive/             # Archived sessions (max 20)
│   ├── 2026-02-03_11-30-00_session.log
│   └── ...
└── errors.log           # Persistent errors (rotating, 5MB x 3)
```

### 9.2 Step Logging API

```python
from .shared.utils.logger import (
    step_start,     # [STEP] ══════ Name ══════
    step_done,      # [DONE] ══════ Name ══════ (12.3s)
    step_fail,      # [FAIL] ══════ Name ══════
    step_info,      #        Info message
    step_warn,      #        Warning message
    step_progress,  #        [██████░░░░] 5/10 - items
    log_metric,     # Structured JSON event → metrics.jsonl
)

# Step tracking example
step_start("Phase 1: Indexing")
step_info("Scanning repository...")
step_progress(5, 10, "files")
step_done()  # Auto-timing

# Structured metric example
log_metric("mini_crew_complete", crew="context", duration=180.5, tokens=1500)
```

### 9.3 Structured Metrics (metrics.jsonl)

Each line in `metrics.jsonl` is a JSON object:

```json
{"ts": "2026-02-07T14:30:00", "level": "INFO", "logger": "aicodegencrew", "msg": "mini_crew_complete", "data": {"event": "mini_crew_complete", "crew_type": "C4", "crew_name": "context", "duration_seconds": 180.5, "total_tokens": 1500}}
```

Events logged:
- `mini_crew_complete` — per mini-crew with timing and token usage
- `phase_complete` — per phase with total duration

### 9.4 Features

| Feature | Description |
|---------|-------------|
| Session Archive | Auto-archives `current.log` to `archive/` on startup |
| Step Tracking | Automatic timing per step |
| Progress Bar | Visual progress with `step_progress()` |
| Structured Metrics | JSON events in `metrics.jsonl` via `log_metric()` |
| Unbuffered | Real-time log viewing |
| Singleton | Logger initialized once |
| MCP-Safe | Console logging disabled when `MCP_STDIO_MODE` is set |

---

## 10. Diagrams Overview

> All diagrams located in `docs/diagrams/`

| Diagram | File | Description |
|---------|------|-------------|
| **SDLC Overview** | `sdlc-overview.drawio` | Full SDLC pipeline (UNDERSTAND → PLAN → BUILD → DEPLOY) |
| Phase Flow | `phase-flow.drawio` | Main pipeline flow |
| Evidence Flow | `evidence-flow.drawio` | Evidence data flow |
| Knowledge Structure | `knowledge-structure.drawio` | Knowledge base organization |
| Collectors | `collectors.drawio` | Phase 1 collector details |
| Analysis Crew | `analysis-crew.drawio` | Phase 2 analysis crew details |
| Synthesis Crew | `synthesis-crew.drawio` | Phase 3 synthesis crew details |

---

## 11. System Requirements

### 11.1 Software Dependencies

| Component | Requirement |
|-----------|-------------|
| Python | 3.10 - 3.13 |
| Ollama | Latest stable release |

### 11.2 Required Models

| Model | Purpose |
|-------|---------|
| `all-minilm:latest` | Embedding generation |
| `qwen2.5-coder:7b` | Code analysis and generation |

---

## 12. Installation Procedure

### 12.1 Model Installation

```
ollama pull all-minilm:latest
ollama pull qwen2.5-coder:7b
```

### 12.2 Environment Setup

```
python -m venv .venv
.\.venv\Scripts\activate
pip install -e .
```

### 12.3 Configuration

```
copy .env.example .env
```

Edit `.env` to configure `PROJECT_PATH` and other parameters as required.

---

## 13. Testing

### 13.1 Full Test Suite

```
pytest tests/
```

### 13.2 Component Tests

```
pytest tests/test_indexing.py -v
pytest tests/test_quality_gate.py -v
```

---

## 14. License

Proprietary — Capgemini. See [LICENSE](../LICENSE) for details.
