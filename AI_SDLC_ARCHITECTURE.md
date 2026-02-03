# AI-Powered Software Development Lifecycle Architecture

## 1. Executive Summary

This document defines the architecture for a complete **End-to-End AI-Powered Software Development Lifecycle (SDLC) Blueprint**. The system utilizes CrewAI multi-agent workflows with configurable LLM backends on-premise models to automate the entire software development process.

### 1.1 Vision

Establish a fully automated SDLC pipeline that covers:

| Phase | Capability |
|-------|------------|
| Architecture Discovery | Reverse engineering of existing codebases |
| Architecture Documentation | C4 Model, arc42 chapters, evidence-based |
| Code Quality Review | Consistency checks, pattern validation |
| Development Planning | Backlog generation, work item creation |
| Code Generation | Feature implementation, refactoring |
| Testing | Test generation, coverage analysis |
| Deployment | CI/CD integration, release management |

### 1.2 Core Principles

| Principle | Description |
|-----------|-------------|
| Evidence-First | Every statement must be backed by code/config evidence |
| Deterministic Discovery | LLMs synthesize, they do not discover - facts come from code analysis |
| Phase Isolation | Each phase has clear inputs/outputs, no cross-phase dependencies |
| Incremental Adoption | Phases can be executed independently |

### 1.3 Current Focus: Architecture Phases (0-2)

The initial implementation focuses on architecture reverse engineering:

- **C4 Model** (Context / Container / Components)
- **arc42 Documentation** (Chapters with runtime/deployment views)
- **Evidence Traceability** (Every diagram element references source code)

### 1.4 Implementation Status

| Phase | Name | Type | Output | Status |
|-------|------|------|--------|--------|
| 0 | Indexing | Pipeline | `.cache/.chroma` | Implemented |
| 1 | Architecture Facts | Pipeline (deterministic, no LLM) | `architecture_facts.json` + `evidence_map.json` | Implemented |
| 2 | Architecture Analysis | Crew (LLM, 4 agents) | `analyzed_architecture.json` | Implemented |
| 2b | Architecture Synthesis | Crew (LLM, evidence-first) | `c4/*`, `arc42/*`, `quality/*` | Implemented |
| 3 | Review and Consistency Guard | Crew | Quality reports, consistency checks | Planned |
| 4 | Development Planning | Crew | Backlog items, work packages | Planned |
| 5 | Code Generation | Crew | Feature code, refactoring PRs | Planned |
| 6 | Test Generation | Crew | Unit tests, integration tests | Planned |
| 7 | Deployment Automation | Pipeline | CI/CD configs, release notes | Planned |

### 1.5 Enterprise-Scale Support

The system supports repositories from small (100 components) to enterprise (100,000+ components):

| Scale | Components | Query Strategy |
|-------|------------|----------------|
| Small | < 500 | Standard queries |
| Medium | 500-5,000 | Stereotype filtering |
| Large | 5,000-50,000 | Stereotype + Container filtering |
| Enterprise | 50,000+ | Paginated queries (500/batch) |

---

## 2. Architecture Overview

> **Reference Diagrams:**
> - [docs/diagrams/phase-flow.drawio](docs/diagrams/phase-flow.drawio) - Pipeline Flow
> - [docs/diagrams/evidence-flow.drawio](docs/diagrams/evidence-flow.drawio) - Evidence Data Flow
> - [docs/diagrams/knowledge-structure.drawio](docs/diagrams/knowledge-structure.drawio) - Knowledge Base

### 2.1 Core Principle: Evidence-First Architecture

Repository -> Phase 0 Indexing -> Phase 1 Architecture Facts -> Phase 2 Architecture Synthesis -> C4 + arc42 Output.
Phase 1 produces facts and evidence; Phase 2 may only synthesize from those facts. If it is not in facts, it must not appear in output.

### 2.2 Component Classification

| Classification | Description | LLM Requirement | Examples |
|----------------|-------------|-----------------|----------|
| Pipeline | Deterministic automated process | Embeddings only | Indexing, Architecture Facts |
| Crew | CrewAI multi-agent workflow | Full LLM | Synthesis, Review |

### 2.3 Core Modules

| Module | Location | Responsibility |
|--------|----------|----------------|
| Orchestrator | `orchestrator.py` | Phase coordination and execution |
| CLI | `cli.py` | Command-line interface |
| Pipelines | `pipelines/` | Deterministic processes (Phase 0, 1) |
| Crews | `crews/` | AI agent workflows (Phase 2+) |
| Shared | `shared/` | Common utilities, models, tools |

---

## 3. Project Structure

```
src/aicodegencrew/
    __init__.py
    __main__.py
    cli.py
    orchestrator.py
    
    crews/
        __init__.py
        
        architecture_synthesis/        # Phase 2: Architecture Synthesis
            __init__.py
            crew.py                    # ArchitectureSynthesisCrew (orchestrates sub-crews)
            agents.py                  # Senior Software Architect agents
            
            c4/                        # C4 Sub-Crew
                __init__.py
                crew.py                # C4Crew (4 tasks)
                config/
                    agents.yaml        # C4 modeling expert
                    tasks.yaml         # Context, Container, Component, Deployment
            
            arc42/                     # Arc42 Sub-Crew
                __init__.py
                crew.py                # Arc42Crew (16 tasks)
                config/
                    agents.yaml        # Arc42 documentation expert
                    tasks.yaml         # 12 chapters + 4 building block sub-tasks
            
            tools/
                __init__.py
                file_read_tool.py      # Read architecture_facts.json
                doc_writer_tool.py     # Write output files
                drawio_tool.py         # Create valid Draw.io diagrams
                facts_query_tool.py    # RAG-based architecture facts query
                chunked_writer_tool.py # Chunked document generation + StereotypeListTool
        
        development/                   # Phase 4: Planned
            __init__.py
    
    pipelines/
        __init__.py
        indexing.py                    # Phase 0: Indexing
        
        architecture_facts/            # Phase 1: Architecture Facts
            __init__.py
            pipeline.py                # ArchitectureFactsPipeline
            base_collector.py          # BaseCollector
            container_detector.py      # ContainerDetector
            spring_collector.py        # SpringCollector
            angular_collector.py       # AngularCollector
            infra_collector.py         # InfraCollector
            database_collector.py      # DatabaseCollector (Liquibase, Flyway)
            integration_collector.py   # IntegrationCollector (Kafka, REST clients)
            architecture_style_collector.py  # Design patterns detection
            quality_validator.py       # Deterministic validation
            writer.py                  # FactsWriter
        
        tools/
        git_ops/
        cicd/
        merge/
    
    shared/
        __init__.py
        utils/
            logger.py
            file_filters.py
            crew_callbacks.py
            ollama_client.py
            smart_index_config.py
        models/
            __init__.py
            analysis_schema.py         # Legacy schema
            architecture_facts_schema.py  # Phase 1 output schema
        tools/
            __init__.py
            base_tool.py
            quality_gate_tool.py
        archscan/
            templates/
```

---

## 4. Phase Specifications

### 4.1 Phase 0: Repository Indexing

| Attribute | Specification |
|-----------|---------------|
| Type | Pipeline (deterministic) |
| Module | `pipelines/indexing.py` |
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
| 4 | EmbeddingsTool | Vector generation (Ollama) |
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

#### Collectors

> **Reference Diagram:** [docs/diagrams/collectors.drawio](docs/diagrams/collectors.drawio)

| Collector | Technology | Extracts |
|-----------|------------|----------|
| `ContainerDetector` | All | Containers from build files |
| `SpringCollector` | Java/Spring | Controllers, Services, Repos, Relations |
| `AngularCollector` | Angular/TS | Components, Modules, Routes |
| `InfraCollector` | Docker/K8s | Deployment configs |
| `DatabaseCollector` | SQL | Liquibase, Flyway, SQL scripts |
| `ArchitectureStyleCollector` | All | Design patterns, arch styles |
| `IntegrationCollector` | All | REST clients, Kafka, RabbitMQ |

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

---

### 4.3 Phase 2: Architecture Synthesis

| Attribute | Specification |
|-----------|---------------|
| Type | Crew (AI Agents) |
| Module | `crews/architecture_synthesis/crew.py` |
| LLM Requirement | Yes |
| Input | `architecture_facts.json` + `evidence_map.json` |
| Output | `knowledge/architecture/c4/` (Draw.io XML + Markdown) |
|        | `knowledge/architecture/arc42/` (Markdown) |
|        | `knowledge/architecture/quality/` (Reports) |
| Dependency | Phase 1 |
| Status | Implemented |

#### CrewAI Best Practices Applied

Phase 2 implements several strategies to optimize token usage and prevent context overflow:

| Strategy | Implementation | Benefit |
|----------|----------------|---------|
| **Task Splitting** | Building Blocks split into 4 sub-tasks (Controllers, Services, Entities, Repositories) | Focused context per task |
| **Hierarchical Dependencies** | Tasks inherit only relevant context from predecessors | Reduced token usage |
| **RAG-based Facts Query** | `FactsQueryTool` queries only needed facts | 80-90% token reduction |
| **Chunked Generation** | `ChunkedWriterTool` writes large docs in sections | Prevents overflow |

#### Sub-Crews Architecture

Phase 2 is split into two specialized crews:

| Crew | Module | Tasks | Output |
|------|--------|-------|--------|
| **C4Crew** | `c4/crew.py` | 4 tasks (Context, Container, Component, Deployment) | `c4/*.md` + `*.drawio` |
| **Arc42Crew** | `arc42/crew.py` | 16 tasks (12 chapters + 4 building block sub-tasks + quality gate) | `arc42/*.md` |

#### Tools

| Tool | Module | Purpose |
|------|--------|---------|
| `FileReadTool` | `tools/file_read_tool.py` | Read JSON/text files |
| `DocWriterTool` | `tools/doc_writer_tool.py` | Write markdown documents |
| `DrawioDiagramTool` | `tools/drawio_tool.py` | Create Draw.io XML diagrams |
| `FactsQueryTool` | `tools/facts_query_tool.py` | RAG-based architecture facts query |
| `ChunkedWriterTool` | `tools/chunked_writer_tool.py` | Chunked document generation |
| `StereotypeListTool` | `tools/chunked_writer_tool.py` | Get components by stereotype |

#### C4 Crew Tasks (4 Total)

| Task | Context Dependency | Output |
|------|-------------------|--------|
| `c4_context` | None | `c4/c4-context.md` + `c4-context.drawio` |
| `c4_container` | c4_context | `c4/c4-container.md` + `c4-container.drawio` |
| `c4_component` | c4_container | `c4/c4-component.md` + `c4-component.drawio` |
| `c4_deployment` | c4_component | `c4/c4-deployment.md` + `c4-deployment.drawio` |

#### Arc42 Crew Tasks (16 Total)

| Task | Context Dependency | Output |
|------|-------------------|--------|
| `arc42_introduction` | None | `arc42/01-introduction.md` |
| `arc42_constraints` | introduction | `arc42/02-constraints.md` |
| `arc42_context` | constraints | `arc42/03-context.md` |
| `arc42_solution_strategy` | context | `arc42/04-solution-strategy.md` |
| `arc42_building_blocks_overview` | solution_strategy | `arc42/05-building-blocks.md` (init) |
| `arc42_building_blocks_controllers` | overview | `arc42/05-building-blocks.md` (append) |
| `arc42_building_blocks_services` | controllers | `arc42/05-building-blocks.md` (append) |
| `arc42_building_blocks_entities` | services | `arc42/05-building-blocks.md` (append) |
| `arc42_building_blocks_repositories` | entities | `arc42/05-building-blocks.md` (finalize) |
| `arc42_runtime_view` | repositories | `arc42/06-runtime-view.md` |
| `arc42_deployment` | runtime_view | `arc42/07-deployment.md` |
| `arc42_crosscutting` | runtime_view | `arc42/08-crosscutting.md` |
| `arc42_decisions` | crosscutting | `arc42/09-decisions.md` |
| `arc42_quality` | crosscutting | `arc42/10-quality.md` |
| `arc42_risks` | quality | `arc42/11-risks.md` |
| `arc42_glossary` | introduction | `arc42/12-glossary.md` |
| `quality_gate` | glossary | `quality/arc42-report.md` |

#### Output Structure

```
knowledge/architecture/
    architecture_facts.json     # From Phase 1
    evidence_map.json           # From Phase 1
    c4/
        c4-context.md           # System context
        c4-context.drawio
        c4-container.md         # Container diagram
        c4-container.drawio
        c4-component.md         # Component diagram
        c4-component.drawio
        c4-deployment.md        # Deployment diagram
        c4-deployment.drawio
    arc42/
        01-introduction.md
        02-constraints.md
        03-context.md
        04-solution-strategy.md
        05-building-blocks.md   # Chunked generation (4 sub-tasks)
        06-runtime-view.md
        07-deployment.md
        08-crosscutting.md
        09-decisions.md
        10-quality.md
        11-risks.md
        12-glossary.md
    quality/
        arc42-report.md
```

#### Rules (MUST FOLLOW!)

| DO | DO NOT |
|-------|-----------|
| Use ONLY data from facts.json | Invent containers |
| Query facts before writing | Invent components |
| State clearly if no data found | Invent relations |
| Use exact names from facts | Add business context |
| Write readable documentation | Clutter output with evidence IDs |
| Use Draw.io for diagrams (XML export) | Use Mermaid or ASCII diagrams |

**Note:** Evidence IDs are for internal processing and quality validation.
The final documentation should be clean and readable without `[ev_XXX]` markers.

---

### 4.3.1 Phase 2 Analysis: Architecture Analysis Crew

| Attribute | Specification |
|-----------|---------------|
| Type | Crew (AI Agents) |
| Module | `crews/architecture_analysis/crew.py` |
| LLM Requirement | Yes |
| Input | `architecture_facts.json` + `evidence_map.json` + ChromaDB |
| Output | `knowledge/architecture/analyzed_architecture.json` |
| Dependency | Phase 1 |
| Status | Implemented |

#### Purpose

Deep analysis of architecture facts to produce quality metrics, insights, and structured analysis:

- Technical Architecture Analysis (styles, patterns, tech stack)
- Functional/Domain Analysis (entities, capabilities, bounded contexts)
- Quality Analysis (complexity, coupling, tech debt indicators)
- Synthesized JSON output for Phase 3

#### Enterprise-Scale Support (100,000+ Components)

The Architecture Analysis Crew supports repositories of any size through intelligent scaling:

| Scale | Components | Strategy |
|-------|------------|----------|
| Small | < 500 | Standard queries with limit=100 |
| Medium | 500-5,000 | Query by stereotype, limit=200 |
| Large | 5,000-50,000 | Query by stereotype AND container, pagination |
| Enterprise | 50,000+ | Paginated queries with offset/limit batches of 500 |

#### Scaling Tools

| Tool | Purpose | Usage |
|------|---------|-------|
| `get_facts_statistics()` | Overview without loading all data | ALWAYS call first |
| `query_facts(limit, offset)` | Paginated component queries | For large repos |
| `list_components_by_stereotype()` | Filter by stereotype | Max 500 per query |

#### Query Strategy for Large Repos

```
1. get_facts_statistics()
   Response: {
     "repository_scale": "enterprise (100,000 components)",
     "components_by_stereotype": {"service": 12500, "controller": 3200, ...},
     "recommendation": "Use paginated_query with offset/limit..."
   }

2. query_facts(category="components", stereotype="service", limit=500, offset=0)
   Response: {
     "pagination": {"components": {"returned": 500, "total_matching": 12500, "has_more": true}}
   }

3. query_facts(..., offset=500)  // Continue until has_more=false
```

#### Analysis Agents (4 Agents)

| Agent | Role | Focus |
|-------|------|-------|
| Tech Architect | Technical analysis | Styles, patterns, tech stack, layers |
| Functional Analyst | Domain analysis | Entities, capabilities, bounded contexts |
| Quality Analyst | Quality metrics | Complexity, coupling, debt, risks |
| Synthesis Lead | Merge results | Create analyzed_architecture.json |

#### Output Schema

```json
{
  "metadata": {
    "repository_scale": "enterprise (100,000 components)",
    "analysis_timestamp": "2026-02-03T12:00:00Z",
    "tool_calls": 85
  },
  "technical_analysis": {
    "architecture_styles": {"primary": "layered_architecture", "secondary": ["microservices"]},
    "design_patterns": [{"name": "repository", "instances": 450}],
    "technology_stack": {...},
    "layer_structure": {...}
  },
  "functional_analysis": {
    "domain_model": {...},
    "capabilities": [...],
    "bounded_contexts": [...]
  },
  "quality_analysis": {
    "complexity_assessment": {...},
    "coupling_metrics": {...},
    "tech_debt_indicators": [...]
  }
}
```

#### Auto-Archive Feature

Before each run, old outputs are archived to prevent data loss:

```
knowledge/architecture/archive/
    run_20260203_120000/
        analyzed_architecture.json
        analysis_technical.json
        analysis_functional.json
        analysis_quality.json
    run_20260202_150000/
        ...
```

---

### 4.4 Phase 3: Review & Consistency Guard (PLANNED)

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

### 4.5 Phase 4: Development / Backlog (PLANNED)

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
| Phase 0 | ChromaDB Vector Index | Phase 1 |
| Phase 1 | `architecture_facts.json` | Phase 2 |
| Phase 1 | `evidence_map.json` | Phase 2 |
| Phase 2 | `c4/*.md`, `c4/*.drawio` | Phase 3 |
| Phase 2 | `arc42/*.md`, `arc42/diagrams/*.drawio` | Phase 3 |
| Phase 3 | Quality Reports | Phase 4 |

### 5.2 Knowledge Directory Structure

```
knowledge/
    README.md
    user_preference.txt
    
    architecture/
        architecture_facts.json     # From Phase 1 (truth)
        evidence_map.json           # From Phase 1 (evidence)
        
        c4/                         # From Phase 2 (C4Crew)
            c4-context.md
            c4-context.drawio
            c4-container.md
            c4-container.drawio
            c4-component.md
            c4-component.drawio
            c4-deployment.md
            c4-deployment.drawio
            
        arc42/                      # From Phase 2 (Arc42Crew)
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
            
        quality/                    # From Phase 2/3
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
| `MODEL` | LLM model identifier | `ollama/qwen2.5-coder:7b` |
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

| Preset | Phases | Description |
|--------|--------|-------------|
| `indexing_only` | 0 | Repository indexing only |
| `facts_only` | 0, 1 | Indexing + Architecture Facts (no LLM) |
| `architecture_workflow` | 0, 1, 2 | Full architecture pipeline |
| `architecture_full` | 0, 1, 2 | Complete C4 + arc42 generation |
| `full_pipeline` | 0, 1, 2, 3, 4 | Complete automated pipeline (future) |

---

## 8. Command Reference

### 8.1 Phase Listing

```bash
python run_phase.py --list
```

### 8.2 Preset Execution

```bash
# Only extract facts (no LLM)
python run_phase.py --preset facts_only

# Full architecture documentation
python run_phase.py --preset architecture_workflow
```

### 8.3 Single Phase Execution

```bash
# Phase 0: Indexing
python run_phase.py --phases phase0_indexing

# Phase 1: Architecture Facts
python run_phase.py --phases phase1_architecture_facts

# Phase 2: Architecture Synthesis
python run_phase.py --phases phase2_architecture_synthesis
```

---

## 9. Diagrams Overview

> All diagrams located in `docs/diagrams/`

| Diagram | File | Description |
|---------|------|-------------|
| Phase Flow | `phase-flow.drawio` | Main pipeline flow |
| Evidence Flow | `evidence-flow.drawio` | Evidence data flow |
| Knowledge Structure | `knowledge-structure.drawio` | Knowledge base organization |
| Collectors | `collectors.drawio` | Phase 1 collector details |
| Synthesis | `synthesis-crew.drawio` | Phase 2 crew details |

### 8.3 Index Mode Override

```
python run_phase.py --preset planning_workflow --index-mode force
```

### 8.4 Explicit Phase Selection

```
python run_phase.py --phases phase0_indexing phase1_architecture
```

### 8.5 Knowledge Cleanup

```
python run_phase.py --preset planning_workflow --clean
```

---

## 9. System Requirements

### 9.1 Software Dependencies

| Component | Requirement |
|-----------|-------------|
| Python | 3.10 - 3.13 |
| Ollama | Latest stable release |

### 9.2 Required Models

| Model | Purpose |
|-------|---------|
| `all-minilm:latest` | Embedding generation |
| `qwen2.5-coder:7b` | Code analysis and generation |

---

## 10. Installation Procedure

### 10.1 Model Installation

```
ollama pull all-minilm:latest
ollama pull qwen2.5-coder:7b
```

### 10.2 Environment Setup

```
python -m venv .venv
.\.venv\Scripts\activate
pip install -e .
```

### 10.3 Configuration

```
copy .env.example .env
```

Edit `.env` to configure `PROJECT_PATH` and other parameters as required.

---

## 11. Testing

### 11.1 Full Test Suite

```
pytest tests/
```

### 11.2 Component Tests

```
pytest tests/test_indexing.py -v
pytest tests/test_quality_gate.py -v
```

---

## 12. License

MIT License
