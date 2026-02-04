# AI-Powered Software Development Lifecycle Architecture

## 1. Introduction

### 1.1 Purpose & Goal

**AICodeGenCrew** is a fully local, on-premises AI-powered blueprint for a complete, end-to-end Software Development Lifecycle (SDLC).

**Use Case:** Provide a fully local / on-prem AI SDLC blueprint (using only on-prem LLMs, no external data transfer) that analyzes an existing repository, generates evidence-based architecture documentation, and supports the full development workflow by creating and then working through backlog items (issues/CRs/tasks): planning, implementing changes, generating tests, running build/CI validations, and finally preparing and merging the delivery end-to-end.

**Why On-Premises?** Enterprise software often contains sensitive intellectual property, customer data, or security-critical code. Sending this data to external AI services (like OpenAI, Anthropic, etc.) may violate compliance requirements, data protection regulations, or internal security policies. AICodeGenCrew is designed to run entirely on your infrastructure with your own LLMs - no data ever leaves your network.

**The Complete Vision:**

> **Reference Diagram:** [sdlc-overview.drawio](diagrams/sdlc-overview.drawio) - Full SDLC Pipeline Overview

**Phase 0-3: Understand (Current Focus - Implemented)**
The tool analyzes your existing codebase. It extracts architectural facts, identifies patterns, and generates comprehensive documentation (C4 diagrams, arc42). This is the foundation - you cannot improve what you do not understand.

**Phase 4-5: Plan (Designed - Not Yet Implemented)**
Based on the architecture analysis, AI agents generate development backlogs, user stories, issues, change requests, and work items. The system understands the codebase structure and can suggest improvements, identify technical debt, and prioritize refactoring tasks.

**Phase 6-7: Build (Designed - Not Yet Implemented)**
AI agents implement changes based on backlog items, generate code following existing patterns and conventions, and create comprehensive tests. Each change is validated against the architecture constraints discovered during analysis.

**Phase 8: Deploy (Designed - Not Yet Implemented)**
The pipeline integrates with CI/CD systems to run builds, execute tests, validate changes, and prepare merge requests. The goal is fully automated delivery from backlog item to merged code.

**Current Status:** Documentation and reverse engineering phases (0-3) are implemented and working. The planning, code generation, testing, and deployment phases are designed but not yet implemented.

### 1.2 Key Benefits

**Fully Automated:** No more manual diagram drawing. Point the tool at your repository and receive complete documentation. The AI agents handle everything from component discovery to diagram generation.

**Evidence-Based:** Every statement in the generated documentation is backed by actual code or configuration evidence. No hallucinations, no guesswork. If it's not in your code, it won't appear in the documentation.

**Reproducible:** Run the same analysis twice and get the same results. The deterministic code analysis phase ensures consistency, while the AI synthesis phase is guided by structured schemas.

**Scalable:** Whether your project has 50 components or 100,000, the Map-Reduce architecture handles it. Large repositories are automatically split by container for parallel analysis.

**Standards-Compliant:** The output follows industry-standard formats - C4 model for architectural diagrams and arc42 for comprehensive documentation. These formats are widely recognized and understood by architects worldwide.

### 1.3 What You Get

When you run AICodeGenCrew on your repository, you receive:

- **C4 Diagrams:** Context, Container, Component, and Deployment views as editable DrawIO files
- **arc42 Documentation:** All 12 chapters including introduction, constraints, context, solution strategy, building blocks, runtime scenarios, deployment, and quality requirements
- **Architecture Analysis:** Detected patterns, technology stack, quality assessment, technical debt indicators, and security posture
- **Evidence Map:** Internal traceability from documentation back to source code (for validation)

The entire process takes minutes for typical repositories and produces documentation that would normally require days of manual effort.

---

## 2. Executive Summary

This document defines the architecture for a complete **End-to-End AI-Powered Software Development Lifecycle (SDLC) Blueprint**. The system utilizes CrewAI multi-agent workflows with configurable LLM backends on-premise models to automate the entire software development process.

### 2.1 Vision

Establish a fully automated SDLC pipeline that covers:

| Phase | Capability | Implementation |
|-------|------------|----------------|
| Phase 0: Indexing | Repository analysis, vector storage | Pipeline (ChromaDB) |
| Phase 1: Architecture Facts | Deterministic code analysis, facts extraction | Pipeline (7 Collectors) |
| Phase 2: Architecture Analysis | Multi-agent analysis (Technical, Functional, Quality) | Crew (4 Agents) |
| Phase 3: Architecture Synthesis | C4 + arc42 documentation generation | Crew (Think First) |
| Phase 4: Review | Consistency checks, quality validation | Crew (Planned) |
| Phase 5: Development | Backlog generation, work items | Crew (Planned) |
| Phase 6: Code Generation | Feature implementation, refactoring | Crew (Planned) |
| Phase 7: Testing | Test generation, coverage | Crew (Planned) |
| Phase 8: Deployment | CI/CD integration, releases | Pipeline (Planned) |

### 2.2 Core Principles

| Principle | Description |
|-----------|-------------|
| Evidence-First | Every statement must be backed by code/config evidence |
| Deterministic Discovery | LLMs synthesize, they do not discover - facts come from code analysis |
| Think First | Agents analyze before documenting (analyze_system task) |
| Phase Isolation | Each phase has clear inputs/outputs, no cross-phase dependencies |
| Incremental Adoption | Phases can be executed independently |
| Clean Output | No evidence IDs in final documentation |

### 1.3 Current Focus: Architecture Phases (0-2)

The initial implementation focuses on architecture reverse engineering:

| Area | Implementation | Status |
|------|----------------|--------|
| **C4 Model** | 5 tasks (1 analyze + 4 diagrams) | Implemented |
| **arc42 Documentation** | 14 tasks (1 analyze + 12 chapters + quality gate) | Implemented |
| **Evidence Traceability** | evidence_map.json (internal use only) | Implemented |
| **Think First Pattern** | analyze_system task before all documentation | Implemented |

### 1.4 Implementation Status

| Phase | Name | Type | Components | Output | Status |
|-------|------|------|------------|--------|--------|
| 0 | Indexing | Pipeline | 5 tools | `.cache/.chroma` | Implemented |
| 1 | Architecture Facts | Pipeline | 7 collectors | `architecture_facts.json` + `evidence_map.json` | Implemented |
| 2 | Architecture Analysis | Crew | 4 agents | `analyzed_architecture.json` | In Progress |
| 3 | Architecture Synthesis | Crew | 2 sub-crews | `c4/*`, `arc42/*`, `quality/*` | Implemented |
| 4 | Review | Crew | - | Quality reports | Planned |
| 5 | Development | Crew | - | Backlog items | Planned |
| 6 | Code Generation | Crew | - | Feature code | Planned |
| 7 | Testing | Crew | - | Unit/integration tests | Planned |
| 8 | Deployment | Pipeline | - | CI/CD configs | Planned |

---

## 2. Architecture Overview

> **Reference Diagrams:**
> - [phase-flow.drawio](diagrams/phase-flow.drawio) - Pipeline Flow (Phases 0-5)
> - [evidence-flow.drawio](diagrams/evidence-flow.drawio) - Evidence Data Flow
> - [knowledge-structure.drawio](diagrams/knowledge-structure.drawio) - Knowledge Base Structure
> - [collectors.drawio](diagrams/collectors.drawio) - Phase 1 Collectors
> - [analysis-crew.drawio](diagrams/analysis-crew.drawio) - Phase 2 Analysis Crew
> - [synthesis-crew.drawio](diagrams/synthesis-crew.drawio) - Phase 3 Synthesis Crew

### 2.1 Core Principle: Evidence-First Architecture

```
Repository → Phase 0 (Indexing) → Phase 1 (Facts) → Phase 2 (Analysis) → Phase 3 (Synthesis) → C4 + arc42 Output
                 ↓                     ↓                   ↓                    ↓
            ChromaDB              NO LLM!           LLM (4 Agents)        LLM (2 Sub-Crews)
```

**Key Rules:**
- Phase 1 produces facts and evidence (deterministic, no LLM)
- Phase 2 analyzes facts with 4 specialized agents, produces `analyzed_architecture.json`
- Phase 3 may only synthesize from Phase 2 output
- If it is not in `architecture_facts.json`, it must NOT appear in output
- Evidence IDs are for internal processing only, NOT in final documentation

### 2.2 Component Classification

| Classification | Description | LLM Requirement | Implemented |
|----------------|-------------|-----------------|-------------|
| Pipeline | Deterministic automated process | None (Embeddings for Phase 0) | Phase 0, Phase 1 |
| Crew | CrewAI multi-agent workflow | Full LLM | Phase 2, Phase 3 |

### 2.3 Core Modules

| Module | Location | Responsibility |
|--------|----------|----------------|
| **Orchestrator** | `orchestrator.py` | Phase coordination (register → run) |
| CLI | `cli.py` | Command-line interface |
| Pipelines | `pipelines/` | Deterministic processes (Phase 0, 1) |
| Crews | `crews/` | AI agent workflows (Phase 2+) |
| Shared | `shared/` | Common utilities, models, tools |

### 2.4 SDLCOrchestrator Design

The orchestrator follows clean architecture principles:

```python
# Simple, explicit API
orchestrator = SDLCOrchestrator()
orchestrator.register("phase0_indexing", IndexingPipeline(...))
orchestrator.register("phase1_architecture_facts", ArchFactsPipeline(...))
orchestrator.register("phase2_architecture_synthesis", SynthesisCrew(...))

result = orchestrator.run(preset="architecture_workflow")
```

| Principle | Implementation |
|-----------|----------------|
| **Single Responsibility** | Only orchestrates, no business logic |
| **Dependency Injection** | Phases are registered, not hardcoded |
| **Fail Fast** | Stops on first error by default |
| **Protocol-based** | Any class with `kickoff()` or `run()` works |
| **Data Classes** | `PhaseResult`, `PipelineResult` for clarity |

### 2.5 Phase 2 Think First Pattern

Each crew in Phase 2 starts with an `analyze_system` task:

```
analyze_system  →  document_1  →  document_2  →  ...  →  quality_gate
     ↓
  (Query all facts first, understand system, then document)
```

This ensures the agent "thinks" before writing any documentation.

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
        
        architecture_analysis/         # Phase 2: Architecture Analysis (NEW)
            __init__.py
            crew.py                    # ArchitectureAnalysisCrew
            config/
                agents.yaml            # 4 agents: tech_architect, func_analyst, quality_analyst, synthesis_lead
                tasks.yaml             # analyze tasks per agent + merge task
            tools/
                __init__.py
                rag_query_tool.py      # ChromaDB semantic search
        
        architecture_synthesis/        # Phase 3: Architecture Synthesis
            __init__.py
            crew.py                    # ArchitectureSynthesisCrew
            agents.py
            
            c4/                        # C4 Sub-Crew
                __init__.py
                crew.py
                config/
                    agents.yaml        # architect agent
                    tasks.yaml         # analyze + 4 diagram tasks
            
            arc42/                     # Arc42 Sub-Crew
                __init__.py
                crew.py
                config/
                    agents.yaml        # architect agent
                    tasks.yaml         # analyze + 12 chapter tasks
            
            tools/                     # Crew tools
                __init__.py
                file_read_tool.py
                doc_writer_tool.py
                drawio_tool.py
                facts_query_tool.py
                chunked_writer_tool.py     # includes StereotypeListTool
                doc_quality_gate_tool.py
        
        development/                   # Phase 5: Planned
            __init__.py
    
    pipelines/
        __init__.py
        indexing.py                    # Backward compat → indexing/
        
        indexing/                      # Phase 0: Repository Indexing
            __init__.py
            pipeline.py                # IndexingPipeline
            indexing_pipeline.py       # ensure_repo_indexed
            repo_discovery_tool.py
            repo_reader_tool.py
            chunker_tool.py
            embeddings_tool.py
            chroma_index_tool.py
        
        architecture_facts/            # Phase 1: Architecture Facts
            __init__.py
            pipeline.py                # ArchitectureFactsPipeline
            base_collector.py
            container_detector.py
            spring_collector.py
            angular_collector.py
            infra_collector.py
            database_collector.py
            integration_collector.py
            architecture_style_collector.py
            endpoint_flow_builder.py
            quality_validator.py
            writer.py
        
        tools/                         # Backward compat → indexing/
        deployment/                    # Phase 7: Planned
        cicd/                          # Planned
        git_ops/                       # Planned
        merge/                         # Planned
    
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
            architecture_facts_schema.py
        tools/
            __init__.py
            base_tool.py
            quality_gate_tool.py
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

#### Collectors

> **Reference Diagram:** [collectors.drawio](diagrams/collectors.drawio)

| Collector | Technology | Extracts | Key Patterns |
|-----------|------------|----------|--------------|
| `ContainerDetector` | All | Containers from build files | pom.xml, package.json, angular.json, Dockerfile |
| `SpringCollector` | Java/Spring | Controllers, Services, Repos, Relations | @RestController, @Service, @Repository, @Component, @Entity |
| `AngularCollector` | Angular/TS | Components, Modules, Routes | @NgModule, @Component, @Injectable, RouterModule |
| `InfraCollector` | Docker/K8s | Deployment configs | docker-compose.yml, k8s/*.yaml |
| `DatabaseCollector` | SQL | Database schemas, migrations | Liquibase XML/YAML, Flyway V*.sql |
| `ArchitectureStyleCollector` | All | Design patterns, arch styles | Repository, Factory, Builder, Singleton, Strategy |
| `IntegrationCollector` | All | External integrations | RestTemplate, WebClient, Feign, Kafka, RabbitMQ |

#### Additional Components

| Component | Purpose |
|-----------|---------|
| `EndpointFlowBuilder` | Builds request flow chains (Controller→Service→Repository) |
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

---

### 4.3 Phase 2: Architecture Analysis (NEW)

> **Reference Diagram:** [docs/diagrams/analysis-crew.drawio](diagrams/analysis-crew.drawio)

| Attribute | Specification |
|-----------|---------------|
| Type | Crew (AI Agents) |
| Module | `crews/architecture_analysis/crew.py` |
| LLM Requirement | Yes |
| Input | `architecture_facts.json` + ChromaDB Index |
| Output | `knowledge/architecture/analyzed_architecture.json` |
| Dependency | Phase 0 (Index) + Phase 1 (Facts) |
| Status | In Progress |

#### Multi-Agent Analysis Pattern

The Analysis Crew uses **4 specialized agents** with different perspectives.
See the detailed diagram: [analysis-crew.drawio](diagrams/analysis-crew.drawio)

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

```
Agent Context Window (e.g., 128K tokens)
+-- System Prompt + Task Description (~5K)
+-- Tool Result 1: 500 components (~20K)
+-- Tool Result 2: 500 relations (~15K)
+-- Tool Result 3: 200 interfaces (~10K)
+-- ... (older results fade from context)
+-- Final Output -> written to file (not in context)
```

**Configuration (agents.yaml):**

```yaml
tech_architect:
  max_iter: 50      # Allow 50 tool calls before stopping
  # Tool queries use limit=500 for comprehensive results
```
| **RAG Integration** | Semantic code search adds context beyond structure |

---

### 4.4 Phase 3: Architecture Synthesis

> **Reference Diagram:** [synthesis-crew.drawio](diagrams/synthesis-crew.drawio)

| Attribute | Specification |
|-----------|---------------|
| Type | Crew (AI Agents) |
| Module | `crews/architecture_synthesis/crew.py` |
| LLM Requirement | Yes (Ollama) |
| Input | `architecture_facts.json` (Phase 1) + `analyzed_architecture.json` (Phase 2) |
| Input (optional) | ChromaDB Index (for code snippets if needed) |
| Output | `knowledge/architecture/c4/` (Draw.io XML + Markdown) |
|        | `knowledge/architecture/arc42/` (Markdown) |
|        | `knowledge/architecture/quality/` (Reports) |
| Dependency | Phase 1 + Phase 2 |
| Status | Implemented |

#### Orchestration

The `ArchitectureSynthesisCrew` orchestrates two sub-crews sequentially:

```
Phase 3a: C4Crew → Phase 3b: Arc42Crew
```

Each sub-crew has exactly **1 agent** (`architect`) with multiple sequential tasks.

#### CrewAI Best Practices Applied

| Practice | Implementation |
|----------|----------------|
| **Think First** | `analyze_system` task runs before any documentation |
| **Hierarchical Context** | Tasks inherit context from predecessors |
| **Simple Agents** | Minimal backstory (~15 lines), 4 clear rules |
| **RAG-based Queries** | `FactsQueryTool` for category-based queries |
| **Clean Output** | No evidence IDs in final documentation |
| **Single Agent per Crew** | One `architect` agent handles all tasks |

#### Sub-Crews Architecture

Phase 2 uses a **"Think First"** pattern - each crew starts with an analysis task:

| Crew | Agent | Tasks | Output |
|------|-------|-------|--------|
| **C4Crew** | `architect` | 1 analyze + 4 diagram tasks (5 total) | `c4/*.md` + `*.drawio` |
| **Arc42Crew** | `architect` | 1 analyze + 12 chapters + 1 quality gate (14 total) | `arc42/*.md` |

#### Task Flow Pattern

```
analyze_system → document_task_1 → document_task_2 → ... → quality_gate
     ↓
  (Think!)
```

The `analyze_system` task queries all facts first, understands the system, 
identifies patterns, and provides context for all following documentation tasks.

#### Tools

| Tool | Purpose |
|------|---------|
| `FileReadTool` | Read JSON/text files |
| `DocWriterTool` | Write markdown documents |
| `DrawioDiagramTool` | Create Draw.io XML diagrams |
| `FactsQueryTool` | Query architecture facts (RAG-based) |
| `ChunkedWriterTool` | Write large documents in sections |
| `StereotypeListTool` | Get components by stereotype |
| `DocQualityGateTool` | Validate document quality |

#### C4 Crew Tasks (5 Total)

| Task | Context Dependency | Output |
|------|-------------------|--------|
| `analyze_system` | None | Internal analysis |
| `c4_context` | analyze_system | `c4/c4-context.md` + `.drawio` |
| `c4_container` | c4_context | `c4/c4-container.md` + `.drawio` |
| `c4_component` | c4_container | `c4/c4-component.md` + `.drawio` |
| `c4_deployment` | c4_component | `c4/c4-deployment.md` + `.drawio` |

#### Arc42 Crew Tasks (14 Total)

| Task | Context Dependency | Output |
|------|-------------------|--------|
| `analyze_system` | None | Internal analysis |
| `arc42_introduction` | analyze_system | `arc42/01-introduction.md` |
| `arc42_constraints` | introduction | `arc42/02-constraints.md` |
| `arc42_context` | constraints | `arc42/03-context.md` |
| `arc42_solution_strategy` | context | `arc42/04-solution-strategy.md` |
| `arc42_building_blocks` | solution_strategy | `arc42/05-building-blocks.md` |
| `arc42_runtime_view` | building_blocks | `arc42/06-runtime-view.md` |
| `arc42_deployment` | runtime_view | `arc42/07-deployment.md` |
| `arc42_crosscutting` | deployment | `arc42/08-crosscutting.md` |
| `arc42_decisions` | crosscutting | `arc42/09-decisions.md` |
| `arc42_quality` | decisions | `arc42/10-quality.md` |
| `arc42_risks` | quality | `arc42/11-risks.md` |
| `arc42_glossary` | risks | `arc42/12-glossary.md` |
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

### 4.5 Phase 4: Review & Consistency Guard (PLANNED)

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

### 4.6 Phase 5: Development / Backlog (PLANNED)

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
| Phase 1 | `evidence_map.json` | Phase 2 |
| Phase 2 | `analyzed_architecture.json` | Phase 3 |
| Phase 3 | `c4/*.md`, `c4/*.drawio` | Phase 4 |
| Phase 3 | `arc42/*.md`, `arc42/diagrams/*.drawio` | Phase 4 |
| Phase 4 | Quality Reports | Phase 5 |

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
python -m aicodegencrew run --phases phase2_architecture_synthesis
```

---

## 9. Logging System

### 9.1 Log Structure

```
logs/
├── current.log          # Active session (overwritten each run)
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
)

# Example
step_start("Phase 1: Indexing")
step_info("Scanning repository...")
step_progress(5, 10, "files")
step_done()  # Auto-timing
```

### 9.3 Features

| Feature | Description |
|---------|-------------|
| Session Archive | Auto-archives `current.log` to `archive/` on startup |
| Step Tracking | Automatic timing per step |
| Progress Bar | Visual progress with `step_progress()` |
| Unbuffered | Real-time log viewing |
| Singleton | Logger initialized once |

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

MIT License
