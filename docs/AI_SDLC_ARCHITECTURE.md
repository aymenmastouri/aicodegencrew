# AI-Powered Software Development Lifecycle Architecture

## 1. Introduction

### 1.1 Purpose and Goal

**SDLC Pilot** is a fully local, on-premises AI-powered blueprint for a complete, end-to-end Software Development Lifecycle (SDLC).

**Use Case:** Provide a fully local / on-prem AI SDLC blueprint (using only on-prem LLMs, no external data transfer) that analyzes an existing repository, generates evidence-based architecture documentation, and supports the full development workflow by creating and then working through backlog items (issues/CRs/tasks): planning, implementing changes, generating tests, running build/CI validations, and finally preparing and merging the delivery end-to-end.

**Why On-Premises?** Enterprise software often contains sensitive intellectual property, customer data, or security-critical code. Sending this data to external AI services (like OpenAI, Anthropic, etc.) may violate compliance requirements, data protection regulations, or internal security policies. SDLC Pilot is designed to run entirely on your infrastructure with your own LLMs - no data ever leaves your network.

### Detailed Architecture Documentation

- [Phase Registry](architecture/phase-registry.md) — Single source of truth for phase metadata
- [Orchestration & State](architecture/orchestration.md) — Phase execution, dependencies, crash recovery
- [Pipeline Pattern](architecture/pipeline-pattern.md) — Stage-based execution, self-healing builds
- [Crew Pattern](architecture/crew-pattern.md) — Multi-agent AI collaboration, MapReduce
- [Knowledge Lifecycle](architecture/knowledge-lifecycle.md) — 16 dimensions, data flow, archive/reset
- [Dashboard Architecture](architecture/dashboard.md) — Angular + FastAPI, SSE, 11 routers

### 1.2 4-Layer Architecture Model

> **Reference Diagrams:**
> - [sdlc-overview.drawio](diagrams/sdlc-overview.drawio) - Full SDLC Pipeline Overview
> - [layer-architecture.drawio](diagrams/layer-architecture.drawio) - Detailed 4-Layer Architecture
> - [pipeline-flow.drawio](diagrams/pipeline-flow.drawio) - Phase Flow with Layer Context

The system is organized into 4 distinct layers, each with clear responsibilities:

| Layer | Phases | Purpose | LLM Required |
|-------|--------|---------|--------------|
| **KNOWLEDGE** | 0-1 | Deterministic facts extraction | No |
| **REASONING** | 2-4 | AI-powered analysis, synthesis, and planning | Hybrid |
| **EXECUTION** | 5-7 | Code generation and deployment | Yes |
| **FEEDBACK** | - | Continuous learning and quality | Yes |

### 1.3 Implementation Status

| Phase | Name | Layer | Type | Status |
|-------|------|-------|------|--------|
| 0 | Discover | Knowledge | Pipeline | IMPLEMENTED |
| 1 | Extract | Knowledge | Pipeline | IMPLEMENTED |
| 2 | Analyze | Reasoning | Crew | IMPLEMENTED |
| 3 | Document | Reasoning | Crew | IMPLEMENTED |
| 4 | Plan | Reasoning | Hybrid | IMPLEMENTED |
| 5 | Implement | Execution | Hybrid | IMPLEMENTED |
| 6 | Verify | Execution | Crew | PLANNED |
| 7 | Deliver | Execution | Pipeline | PLANNED |

### 1.4 Key Benefits

**Fully Automated:** No more manual diagram drawing. Point the tool at your repository and receive complete documentation. The AI agents handle everything from component discovery to diagram generation.

**Evidence-Based:** Every statement in the generated documentation is backed by actual code or configuration evidence. No hallucinations, no guesswork. If it is not in your code, it will not appear in the documentation.

**Reproducible:** Run the same analysis twice and get the same results. The deterministic code analysis phase ensures consistency, while the AI synthesis phase is guided by structured schemas.

**Scalable:** Whether your project has 50 components or 100,000, the Map-Reduce architecture handles it. Large repositories are automatically split by container for parallel analysis.

**Standards-Compliant:** The output follows industry-standard formats - C4 model for architectural diagrams and arc42 for comprehensive documentation. These formats are widely recognized and understood by architects worldwide.

### 1.5 What You Get

When you run SDLC Pilot on your repository, you receive:

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
| Discover | Knowledge | Repository analysis, vector storage | Pipeline (ChromaDB) |
| Extract | Knowledge | Deterministic code analysis | Pipeline (31 Collectors) |
| Analyze | Reasoning | Multi-agent architecture analysis | Crew (MapReduce) |
| Document | Reasoning | C4 + arc42 documentation | Crew (Mini-Crews) |
| Plan | Reasoning | Parse tasks + create implementation plans | Hybrid Pipeline (IMPLEMENTED) |
| Implement | Execution | Feature implementation | Hybrid Pipeline (IMPLEMENTED) |
| Verify | Execution | Test creation | Crew (Planned) |
| Deliver | Execution | CI/CD integration | Pipeline (Planned) |

### 2.2 Core Principles

| Principle | Description |
|-----------|-------------|
| Evidence-First | Every statement must be backed by code/config evidence |
| Deterministic Discovery | LLMs synthesize, they do not discover - facts come from code analysis |
| Mini-Crews | Fresh crew per chapter/level, 1 task per crew |
| Phase Isolation | Each phase has clear inputs/outputs, no cross-phase dependencies |
| Incremental Adoption | Phases can be executed independently |
| Clean Output | No evidence IDs in final documentation |

### 2.3 Current Focus: Knowledge + Reasoning + Execution Layers (Discover through Implement)

The implementation covers deterministic facts extraction through code generation:

| Area | Implementation | Status |
|------|----------------|--------|
| **Discover** | ChromaDB vector storage | IMPLEMENTED |
| **Extract** | 31 Collectors | IMPLEMENTED |
| **Analyze** | MapReduce multi-agent analysis | IMPLEMENTED |
| **Document** | C4 + arc42 Crews (Mini-Crews pattern) | IMPLEMENTED |
| **Plan** | Hybrid pipeline (4 deterministic + 1 LLM stage) | IMPLEMENTED |
| **Implement** | Hybrid pipeline (6 stages: 4 deterministic + LLM gen + build verify with self-heal) | IMPLEMENTED |
| **SDLC Dashboard** | Angular 21 + FastAPI web UI with SSE streaming, file upload, doc rendering | IMPLEMENTED |
| **Evidence Traceability** | evidence_map.json | IMPLEMENTED |

### 2.4 Knowledge Layer Capabilities

Extract extracts comprehensive architecture facts from any codebase:

| Capability | Description |
|------------|-------------|
| **Component Discovery** | Detects components (services, controllers, entities, modules, etc.) across all technology stacks |
| **Interface Extraction** | REST endpoints, Angular routes, OpenAPI specs, database schemas |
| **Relation Mapping** | 7-tier resolver resolves dependencies across layers (see 4.2.1) |
| **Endpoint Flow Tracing** | Traces request flows through layers (e.g., Controller→Service→Repository) (see 4.2.2) |
| **Evidence Collection** | Every fact is linked to source file + line number for traceability |
| **Pattern Detection** | Security, validation, error handling, and test patterns |

---

## 3. Architecture Overview

> **Reference Diagrams:**
> - [sdlc-overview.drawio](diagrams/sdlc-overview.drawio) - Full SDLC Pipeline Overview
> - [layer-architecture.drawio](diagrams/layer-architecture.drawio) - Detailed 4-Layer Architecture
> - [pipeline-flow.drawio](diagrams/pipeline-flow.drawio) - Pipeline Flow (Phases 0-7)
> - [evidence-flow.drawio](diagrams/evidence-flow.drawio) - Evidence Data Flow
> - [knowledge-structure.drawio](diagrams/knowledge-structure.drawio) - Knowledge Base Structure
> - [facts-collectors.drawio](diagrams/facts-collectors.drawio) - Deterministic Collectors
> - [analysis-crew.drawio](diagrams/analysis-crew.drawio) - Multi-Agent Analysis Crew
> - [synthesis-crew.drawio](diagrams/synthesis-crew.drawio) - C4 + Arc42 Synthesis Crews
> - [development-planning-pipeline.drawio](diagrams/development-planning-pipeline.drawio) - Hybrid Development Planning Pipeline
> - [analysis-crew-schema.drawio](diagrams/analysis-crew-schema.drawio) - Analysis Schema Validation

### 3.1 Core Principle: Evidence-First Architecture

> See [pipeline-flow.drawio](diagrams/pipeline-flow.drawio) for the full 4-layer pipeline diagram.

**Why Evidence-First?** LLMs hallucinate. If you ask an LLM "what components does this system have?", it will guess based on naming conventions. By extracting facts deterministically first (Extract, no LLM), then feeding only verified facts to the LLM (Analyze+), every statement in the output is traceable to real code. This is critical for enterprise documentation that auditors and architects rely on.

**Key Rules:**
- Extract produces facts and evidence (deterministic, no LLM)
- Analyze synthesizes documentation from facts only
- If it is not in `architecture_facts.json`, it must NOT appear in output
- Evidence IDs are for internal processing only, NOT in final documentation
- Feedback loop updates knowledge base continuously

### 3.2 Component Classification

| Classification | Layer | LLM Requirement | Phases |
|----------------|-------|-----------------|--------|
| Pipeline | Knowledge | None (Embeddings for Discover) | Discover, Extract, Verify, Deliver |
| Crew | Reasoning/Execution | Full LLM | Analyze, Document, Plan, Implement |

### 3.3 Core Modules

| Module | Location | Responsibility |
|--------|----------|----------------|
| **Orchestrator** | `orchestrator.py` | Phase coordination (register - run) |
| CLI | `cli.py` | Command-line interface, repo resolution |
| GitRepoManager | `shared/utils/git_repo_manager.py` | Clone/pull remote Git repos |
| Pipelines | `pipelines/` | Deterministic processes (Discover, Extract) |
| Crews | `crews/` | AI agent workflows (Analyze+) |
| Shared | `shared/` | Common utilities, models, tools |

### 3.4 SDLCOrchestrator Design

The orchestrator follows clean architecture principles:

```python
# Simple, explicit API
orchestrator = SDLCOrchestrator()
orchestrator.register("discover", IndexingPipeline(...))
orchestrator.register("extract", ArchFactsPipeline(...))
orchestrator.register("analyze", AnalysisCrew(...))
orchestrator.register("document", SynthesisCrew(...))
orchestrator.register("plan", PlanningPipeline(...))

result = orchestrator.run(preset="architect")
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

### 3.5 Mini-Crews Pattern (Document)

**Why Mini-Crews?** CrewAI's default pattern — one Crew with many sequential tasks — fails for large documents. After ~10-15 tasks, the accumulated conversation history exceeds the LLM context window (120K tokens), producing `max_tokens must be at least 1` errors. Mini-Crews solve this by giving each sub-task a fresh agent with a fresh context window, passing data via template variables instead of conversation history.

Document uses the **Mini-Crews Pattern** instead of a single large Crew:

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
| **Structured Metrics** | `log_metric()` writes to `metrics.jsonl` with `run_id` |
| **Tool Guardrails** | Blocks identical (>3x) / runaway (>25) tool calls via CrewAI hooks |
| **Retry with Backoff** | Retries on `ConnectionError/TimeoutError/OSError` |
| **Output Recovery** | Generates stub docs from facts on crew failure |

#### 3.6.1 LLM Optimization Features (Phase 0.5 + 1 + 1.5)

> **Status**: Fully implemented across Analyze and Document crews.
> Implemented across Analyze and Document crews (tool guardrails, budget limits, output gates).

**Phase 0.5: Guardrails & Stop Conditions**

| Guardrail | Implementation | Impact |
|-----------|----------------|--------|
| **Tool-call budget** | Max 25 tool calls per task, then force finish | Prevents infinite loops |
| **Identical-call limit** | Max 3 identical calls (same tool + args) | Stops MCP spam (e.g., 30x `get_statistics`) |
| **Output-gate validation** | Raises `RuntimeError` if files missing after crew completes | Fails fast instead of silent success |
| **Response sanitizer** | Extracts content from raw `ChatCompletionMessageToolCall` objects | Prevents cryptic errors on `max_iter` |

**Phase 1: Few-Shot Prompting**

| Feature | Location | Purpose |
|---------|----------|---------|
| **TOOL_INSTRUCTION** | `base_crew.py`, prepended to all task descriptions | 4 mandatory rules + concrete tool-use example (WRONG/RIGHT patterns) |
| **EXECUTION EXAMPLE blocks** | Per-task descriptions in `c4/crew.py` and `arc42/crew.py` | Shows exact tool sequence for each chapter (e.g., Step 1: `get_statistics()`, Step 2: `doc_writer(...)`) |

**Phase 1.5: Output Quality Maximization**

| Optimization | Before | After | Impact |
|--------------|--------|-------|--------|
| **Input token limit** | 32K | 100K | Agents can process more facts/context |
| **Output token limit** | 4K | 16K | Longer chapters (20-25 pages vs. 6-8) |
| **Context window** | 32K | 120K | Handles full conversation history |
| **Tool-call budget** | 10 | 25 | More data gathering before synthesis |
| **Identical-call limit** | 2 | 3 | Allows necessary re-queries |
| **Chapter splitting** | Ch05 only | Ch05 + Ch06 + Ch08 | 4 sub-crews each → merge in Python |

**Expected improvements (combined):**
- Tool-Use Compliance: ~60% → ~85%
- Files written / expected: ~70% → ~90%
- Tool loops per crew: 1-2 → 0
- Average chapter length: 6-8 pages → 12-20 pages

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

        architecture_analysis/         # Analyze: Architecture Analysis
            __init__.py
            crew.py                    # ArchitectureAnalysisCrew (5 mini-crews, all Python)
            mapreduce_crew.py          # MapReduceAnalysisCrew (large repos)
            container_crew.py          # ContainerAnalysisCrew (per-container)
            tools/
                __init__.py
                rag_query_tool.py      # ChromaDB semantic search

        architecture_synthesis/        # Document: Architecture Synthesis
            __init__.py
            crew.py                    # ArchitectureSynthesisCrew (orchestrator)
            base_crew.py               # MiniCrewBase ABC (shared infrastructure)

            c4/                        # C4 Mini-Crews (5 crews)
                __init__.py
                crew.py                # C4Crew(MiniCrewBase) - all Python, no YAML

            arc42/                     # Arc42 Mini-Crews (18 crews)
                __init__.py
                crew.py                # Arc42Crew(MiniCrewBase) - all Python, no YAML

            tools/                     # Crew tools
                __init__.py
                file_read_tool.py      # Read JSON/text files
                doc_writer_tool.py     # Write markdown (with path-stripping)
                drawio_tool.py         # Create DrawIO diagrams (with path-stripping)
                facts_query_tool.py    # Query architecture facts
                chunked_writer_tool.py # ChunkedWriterTool + StereotypeListTool

        codegen/                       # Implement: Code Generation (IMPLEMENTED)
            (deleted — moved to pipelines/code_generation/)

        testing/                       # Verify: Test Generation (PLANNED)
            __init__.py
            agents.py                  # Test generation agents
            crew.py                    # TestGenerationCrew
            tasks.py                   # Test generation tasks

        review/                        # Deliver: Review + Deploy (PLANNED)
            __init__.py
            agents.py                  # Review agents
            crew.py                    # ReviewCrew
            tasks.py                   # Review tasks

    pipelines/
        __init__.py
        indexing.py                    # Backward compat

        indexing/                      # Discover: Repository Indexing
            __init__.py
            indexing_pipeline.py       # IndexingPipeline + IndexingState + ensure_repo_indexed
            ...

        architecture_facts/            # Extract: Architecture Facts
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

        development_planning/          # Plan: Development Planning (HYBRID)
            __init__.py
            pipeline.py                # DevelopmentPlanningPipeline (5 stages)
            schemas.py                 # Pydantic schemas for plans

            stages/                    # 5-stage hybrid architecture
                __init__.py
                input_parser.py        # Stage 1: Parse JIRA/DOCX/Excel (deterministic)
                component_discovery.py # Stage 2: RAG + scoring (2-5s)
                pattern_matcher.py     # Stage 3: TF-IDF + rules (1-3s)
                plan_generator.py      # Stage 4: LLM call (15-30s) <- ONLY LLM
                validator.py           # Stage 5: Pydantic validation (<1s)

            parsers/                   # Input file parsers
                __init__.py
                jira_parser.py         # Parse JIRA XML exports
                docx_parser.py         # Parse Word documents
                excel_parser.py        # Parse Excel sheets
                log_parser.py          # Parse application logs

            upgrade_rules/             # Framework upgrade rules
                __init__.py
                angular_upgrades.py    # Angular version upgrades
                spring_upgrades.py     # Spring Boot upgrades
                java_upgrades.py       # Java version upgrades
                node_upgrades.py       # Node.js upgrades
                dependency_upgrades.py # Dependency updates
                breaking_changes.py    # Breaking change detection
                migration_steps.py     # Migration step generation

        code_generation/                # Implement: Code Generation (HYBRID)
            __init__.py
            pipeline.py                # CodeGenerationPipeline (6 stages)
            schemas.py                 # Pydantic schemas (10 models)

            stages/                    # 6-stage hybrid architecture
                __init__.py
                stage1_plan_reader.py      # Read Plan output + resolve file paths
                stage2_context_collector.py # Collect source code from target repo
                stage3_code_generator.py   # LLM call per file (primary LLM stage)
                stage4_code_validator.py   # Syntax, security, pattern validation
                stage4b_build_verifier.py  # Build verification + self-healing (LLM)
                stage5_output_writer.py    # Git branch + file writes + report

            strategies/                # Task-type-specific strategies
                __init__.py
                base.py                # BaseStrategy ABC
                feature_strategy.py    # New feature implementation
                bugfix_strategy.py     # Targeted bug fixes
                upgrade_strategy.py    # Framework migration (Angular, Spring)
                refactoring_strategy.py # Code restructuring

        merge/                         # Pipeline merge utilities
            __init__.py
            ...

        tools/                         # Pipeline tools
            __init__.py
            ...

    shared/
        __init__.py
        validation.py                  # PhaseOutputValidator (inter-phase contracts)

        utils/
            logger.py                  # Logger + RUN_ID + JsonFormatter + log_metric()
            tool_guardrails.py         # ToolCallTracker + install/uninstall hooks
            crew_callbacks.py          # step_callback + task_callback (logger-based)
            git_repo_manager.py        # GitRepoManager (clone/pull remote repos)
            token_budget.py            # Token budget configuration
            file_filters.py
            ollama_client.py

        models/
            __init__.py
            architecture_facts_schema.py  # Pydantic schema for Extract
            analysis_schema.py            # Pydantic schema for Analyze
            development_plan_schema.py    # Pydantic schema for Plan

        tools/                         # Shared tool base classes
            __init__.py
            base_tool.py               # BaseTool abstract class
            quality_gate_tool.py       # Quality gate validation

    mcp/
        server.py                      # MCP knowledge server (STDIO)
        knowledge_tools.py             # MCP tool implementations
```

---

## 4. Phase Specifications

### 4.1 Discover Phase

| Attribute | Specification |
|-----------|---------------|
| Type | Pipeline (deterministic) |
| Module | `pipelines/indexing/indexing_pipeline.py` |
| LLM Requirement | None (embeddings only) |
| Output | `knowledge/discover/` (ChromaDB) + `knowledge/discover/.indexing_state.json` |
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

### 4.2 Extract Phase (CRITICAL!)

| Attribute | Specification |
|-----------|---------------|
| Type | Pipeline (deterministic, **NO LLM!**) |
| Module | `pipelines/architecture_facts/` |
| LLM Requirement | **NONE** |
| Output | `knowledge/extract/architecture_facts.json` |
|        | `knowledge/extract/evidence_map.json` |
| Dependency | Discover |

#### Purpose

**Extract creates the SINGLE SOURCE OF TRUTH for architecture.**
- No interpretation
- No LLM
- No documentation
- Only Facts + Evidence

**Everything not in Extract output must NOT be written by Analyze!**

#### What Gets Extracted

| Category | Items | Evidence Required |
|----------|-------|-------------------|
| System | Repository name, domain | Yes |
| Containers | Backend, Frontend, DB, Infra | Yes |
| Components | @RestController, @Service, @Repository, @Component | Yes |
| Interfaces | REST endpoints, Routes | Yes |
| Relations | Constructor injection, imports | Yes |

#### Collector Architecture (Modular)

> **Reference Diagram:** [facts-collectors.drawio](diagrams/facts-collectors.drawio)

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

**ComponentCollector** also handles:
| Technology | Detection | Container Match |
|------------|-----------|-----------------|
| Spring Boot / Java/Gradle / Java/Maven | Spring specialist collectors | `_get_containers_by_technologies()` |
| Angular | Angular specialist collectors | `_get_containers_by_technology()` |
| Node.js / Node.js/TypeScript | `export class/function/const` scan | `_get_containers_by_technologies()` |

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

### 4.3 Analyze Phase (Mini-Crews Pattern)

> **Reference Diagram:** [docs/diagrams/analysis-crew.drawio](diagrams/analysis-crew.drawio)

| Attribute | Specification |
|-----------|---------------|
| Type | Crew (AI Agents) - Mini-Crews Pattern |
| Module | `crews/architecture_analysis/crew.py` |
| Config | Python constants (no YAML) |
| LLM Requirement | Yes |
| Input | `architecture_facts.json` + ChromaDB Index |
| Output | `knowledge/analyze/analyzed_architecture.json` |
| Checkpoint | `.checkpoint_analysis.json` (resume on failure) |
| Dependency | Discover + Extract |
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
    "name": "my-app",
    "domain": "Business Platform",
    "description": "Enterprise application system"
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
    {"name": "Order Management", "key_components": ["OrderService", "InventoryService"]},
    {"name": "User Management", "key_components": ["UserService", "AuthService"]}
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

| Aspect | Standard Mode | Deep Analysis Mode (Current) |
|--------|---------------|------------------------------|
| Tool calls per agent | 5-15 | 15-25 (max budget) |
| Runtime | 2-5 minutes | 30-40 minutes |
| max_iter (CrewAI) | 15 | 30 |
| Query limit | 50 items | 500 items |
| **Input token limit** | 32K | **100K** (Phase 1.5) |
| **Output token limit** | 4K | **16K** (Phase 1.5) |
| **Context window** | 32K | **120K** (Phase 1.5) |

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

### 4.4 Document Phase (Mini-Crews Pattern)

| Attribute | Specification |
|-----------|---------------|
| Type | Crew (AI Agents) - Mini-Crews Pattern |
| Module | `crews/architecture_synthesis/` |
| Base Class | `base_crew.py` → `MiniCrewBase` (ABC) |
| LLM Requirement | Yes |
| Input | `architecture_facts.json` (Extract) + `analyzed_architecture.json` (Analyze) |
| Input (optional) | ChromaDB Index (via MCP server) |
| Output | `knowledge/document/c4/` (DrawIO + Markdown) |
|        | `knowledge/document/arc42/` (Markdown) |
|        | `knowledge/document/quality/` (Reports) |
| Dependency | Extract + Analyze (validated by `PhaseOutputValidator`) |
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
    Arc42Crew.run()  → 18 Mini-Crews (18 tasks total, 1 task per crew)
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

#### Arc42Crew: 18 Mini-Crews (1 task each)

| Mini-Crew | Chapter | Output |
|-----------|---------|--------|
| `introduction` | 1 | `01-introduction.md` |
| `constraints` | 2 | `02-constraints.md` |
| `context` | 3 | `03-context.md` |
| `solution-strategy` | 4 | `04-solution-strategy.md` |
| `building-blocks-overview` | 5.1-5.2 | `05-part1-overview.md` |
| `building-blocks-controllers` | 5.3 | `05-part2-controllers.md` |
| `building-blocks-services` | 5.4 | `05-part3-services.md` |
| `building-blocks-domain` | 5.5-5.7 | `05-part4-domain.md` |
| `runtime-view-api-flows` | 6.1-6.4 | `06-part1-api-flows.md` |
| `runtime-view-business-flows` | 6.5-6.8 | `06-part2-business-flows.md` |
| `deployment` | 7 | `07-deployment.md` |
| `crosscutting-technical` | 8.1-8.5 | `08-part1-technical.md` |
| `crosscutting-patterns` | 8.6-8.11 | `08-part2-patterns.md` |
| `decisions` | 9 | `09-decisions.md` |
| `quality` | 10 | `10-quality.md` |
| `risks` | 11 | `11-risks.md` |
| `glossary` | 12 | `12-glossary.md` |
| `quality-gate` | validation | `quality/arc42-report.md` |

Chapters 5, 6, and 8 are split into sub-crews. After all sub-crews complete,
merge functions combine part files into the final chapter files (e.g.,
`05-part1...4` → `05-building-blocks.md`).

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
knowledge/
├── discover/                      # ChromaDB vector store
│   ├── chroma.sqlite3             # ChromaDB database
│   └── .indexing_state.json       # Persistent indexing state
├── extract/                       # Architecture facts (Extract)
│   ├── architecture_facts.json
│   └── evidence_map.json
├── analyze/                       # Architecture analysis (Analyze)
│   └── analyzed_architecture.json
├── document/                      # Documentation synthesis (Document)
│   ├── .checkpoint_c4.json        # Resume checkpoint (temporary)
│   ├── .checkpoint_arc42.json     # Resume checkpoint (temporary)
│   ├── c4/
│   │   ├── c4-context.md          # Level 1 (6-8 pages)
│   │   ├── c4-context.drawio
│   │   ├── c4-container.md        # Level 2 (6-8 pages)
│   │   ├── c4-container.drawio
│   │   ├── c4-component.md        # Level 3 (6-8 pages)
│   │   ├── c4-component.drawio
│   │   ├── c4-deployment.md       # Level 4 (4-6 pages)
│   │   └── c4-deployment.drawio
│   ├── arc42/
│   │   ├── 01-introduction.md     # Chapter 1 (8-10 pages)
│   │   ├── 02-constraints.md      # Chapter 2 (6-8 pages)
│   │   ├── 03-context.md          # Chapter 3 (8-10 pages)
│   │   ├── 04-solution-strategy.md # Chapter 4 (8-10 pages)
│   │   ├── 05-building-blocks.md  # Chapter 5 (20-25 pages, largest)
│   │   ├── 06-runtime-view.md     # Chapter 6 (8-10 pages)
│   │   ├── 07-deployment.md       # Chapter 7 (6-8 pages)
│   │   ├── 08-crosscutting.md     # Chapter 8 (8-10 pages)
│   │   ├── 09-decisions.md        # Chapter 9 (8 pages)
│   │   ├── 10-quality.md          # Chapter 10 (6 pages)
│   │   ├── 11-risks.md            # Chapter 11 (6 pages)
│   │   └── 12-glossary.md         # Chapter 12 (4 pages)
│   └── quality/
│       ├── c4-report.md           # C4 quality gate report
│       └── arc42-report.md        # Arc42 quality gate report
├── plan/                          # Development plans (Plan)
│   └── {task_id}_plan.json        # 1 per task
├── implement/                     # Code generation reports (Implement)
│   └── {task_id}_report.json      # 1 per task
├── verify/                        # (planned)
└── deliver/                       # (planned)
```

#### Rules (MUST FOLLOW!)

| DO | DO NOT |
|-------|-----------|
| Use ONLY data from facts.json | Invent containers |
| Query MCP tools for real data | Invent components |
| Use doc_writer tool for output | Write content in response text |
| Use exact names from facts | Add business context |
| Write readable documentation | Clutter output with evidence IDs |
| Use DrawIO for diagrams (XML) | Use Mermaid, PlantUML, or ASCII diagrams |

---

### 4.5 Plan Phase (HYBRID PIPELINE - IMPLEMENTED)

> **Reference Diagram:** [development-planning-pipeline.drawio](diagrams/development-planning-pipeline.drawio) - Hybrid Pipeline Flow

| Attribute | Specification |
|-----------|---------------|
| Type | Pipeline (Hybrid: Deterministic + 1 LLM Call per task) |
| Module | `pipelines/development_planning/` |
| LLM Requirement | Yes (Stage 4 only, 1 call per task) |
| Multi-File | 1 file = single run; N files (same epic) = parse all, sort, process each |
| Input | `inputs/tasks/` (`.txt`, `.log`, `.xml`, `.docx`, `.xlsx`) — primary task files |
| | `inputs/requirements/` (Specs, documentation) — supplementary context for richer plans |
| | `inputs/logs/` (Error logs, traces) — supplementary context for debugging tasks |
| | `inputs/reference/` (Examples, patterns) — supplementary context for design guidance |
| | `architecture_facts.json` (Extract, all 17 keys) |
| | `analyzed_architecture.json` (Analyze) |
| | ChromaDB (Discover, semantic search) |
| Output | `knowledge/plan/{task_id}_plan.json` (1 per task) |
| Dependency | Discover, Extract, Analyze |
| Status | **IMPLEMENTED** |

#### Architecture: Hybrid Pipeline

**Why Hybrid?** Development planning is 80% pattern matching and 20% creative synthesis. Multi-agent workflows (CrewAI) use LLMs for everything — including deterministic tasks like "find components matching keyword X" — which is slow (5-7 min), expensive (5 LLM calls), and unreliable (70-80% success). The hybrid approach uses algorithms for what algorithms do best (TF-IDF similarity, regex matching, rule-based lookup) and the LLM only for the creative step (synthesizing a coherent implementation plan from structured inputs). Result: 10-20x faster, 95%+ success rate, and fully debuggable.

**5-Stage Pipeline:**

```
Stage 1: Input Parser (Deterministic, <1s) - IMPLEMENTED
  └─ Parse XML/DOCX/Excel/Text → TaskInput JSON
  └─ JIRA XML: Extracts ALL content (description, 15+ comments,
                metadata, assignee, reporter, dates, fix version)

Stage 2: Component Discovery (RAG + Scoring, 2-5s) - IMPLEMENTED
  └─ ChromaDB semantic search + multi-signal scoring
  └─ 4 signals: semantic (40%), name (30%), package (20%), stereotype (10%)

Stage 3: Pattern Matcher (TF-IDF + Rules, 1-3s) - IMPLEMENTED
  └─ Test patterns (TF-IDF on 925 tests)
  └─ Security/Validation/Error (rule-based on 143+149+23 patterns)

Stage 4: Plan Generator (LLM, 15-30s) - IMPLEMENTED ← ONLY LLM CALL
  └─ Synthesize all previous stages → Implementation plan

Stage 5: Validator (Pydantic, <1s) - IMPLEMENTED
  └─ Schema validation, completeness checks, layer compliance

Total: 18-40 seconds (vs 5-7 minutes with CrewAI)
All Parsers: XML, DOCX, Excel, Text - FULLY IMPLEMENTED
```

#### Performance Metrics

| Metric | CrewAI (Multi-Agent) | Hybrid Pipeline | Improvement |
|--------|---------------------|-----------------|-------------|
| Duration | 5-7 minutes | 18-40 seconds | **10-20x faster** |
| LLM Calls | 5 | 1 | **5x fewer** |
| Success Rate | 70-80% | 95%+ | **+15-25%** |
| Data Utilization | 20% (components only) | 100% (all 17 keys) | **5x more** |
| Debuggability | Hard (agent black box) | Easy (pipeline steps) | Much better |

#### Multi-File Processing (IMPLEMENTED)

The pipeline supports processing multiple task files from the same epic in a single run.

**Modes:**

| Mode | Input | Behavior |
|------|-------|----------|
| Single file | 1 file in `inputs/tasks/` | Stages 1→5 sequentially (default) |
| Multi-file | N files in `inputs/tasks/` | Parse all → Sort → Process each (Stages 2-5) |

**Content-Based Sorting Algorithm** (`_sort_tasks()`):

Tasks are sorted by a composite key `(is_child, priority, task_type, task_id)`:

| Sort Key | Order | Purpose |
|----------|-------|---------|
| `is_child` | 0 (parent) → 1 (child) | Parent tickets before subtasks |
| JIRA Priority | Blocker(1) → Critical(2) → Major(3) → Minor(4) → Trivial(5) | Higher priority first |
| Task Type | upgrade(1) → bugfix(2) → feature(3) → refactoring(4) | Upgrades before features |
| Task ID | Alphabetical | Deterministic tiebreaker |

**Child Detection:** A task is a "child" if any of its `linked_tasks` IDs match another task in the current batch. This handles:
- Explicit JIRA links (`<issuelinks>`, `<subtasks>`, `<parent>`)
- Cross-references in description text (e.g., "als Teil von PROJ-123")

**Error Isolation:** Failed tasks do not block processing of remaining tasks. The pipeline returns `status: "partial"` when some tasks fail.

**Example** (2 files in `inputs/tasks/`):
```
Input:
  PROJ-456.xml  (SASS Migration, Major, links to PROJ-123)
  PROJ-123.xml  (Framework Upgrade, Major, no links in batch)

Sorted:
  1. PROJ-123 [Major] type=upgrade is_child=0  ← parent first
  2. PROJ-456 [Major] type=upgrade is_child=1  ← child second

Output:
  knowledge/plan/PROJ-123_plan.json
  knowledge/plan/PROJ-456_plan.json
```

#### Stage 1: Input Parsers (IMPLEMENTED)

All 4 parsers fully implemented in `pipelines/development_planning/parsers/`:

**1. XML Parser** (`xml_parser.py`) - **Complete JIRA Extraction**
- JIRA RSS format, generic XML, custom formats
- Extracts from JIRA XML:
  - Basic: Task ID, Summary, Description, Priority, Type, Status
  - Metadata: Assignee, Reporter, Created/Updated dates, Fix Version, Resolution
  - **All Comments**: Author, timestamp, full text (example: 15 comments = 7,066 chars)
  - Labels, Components, Custom fields, Attachments, Links, Subtasks
  - **Linked Tasks** (`linked_tasks`): Extracted from 4 sources:
    1. `<issuelinks>` — JIRA issue links (Causes, Blocks, etc.)
    2. `<subtasks>` — Sub-task references
    3. `<parent>` — Parent ticket reference
    4. Description text — Regex `[A-Z][A-Z0-9]+-\d+` (cross-references)
  - **JIRA Type** (`jira_type`): Task, Sub-Task, Epic, Story, Bug
- Example: 133KB JIRA file → Complete task context with all discussions

**2. DOCX Parser** (`docx_parser.py`)
- Extracts: Title, sections (with headings), tables
- Dependency: `python-docx`

**3. Excel Parser** (`excel_parser.py`)
- Parses all sheets, detects headers, extracts data rows
- Dependency: `openpyxl`

**4. Text Parser** (`text_parser.py`)
- Plain text and log files
- Extracts error patterns with context, parses log entries

**Installation:** `pip install -e ".[parsers]"` for DOCX/Excel support

#### Stage 2: Component Discovery (Multi-Signal Scoring)

**Algorithm:** Combines 4 signals to find affected components:

1. **Semantic Similarity** (40% weight) - ChromaDB vector distance
   ```python
   similarity = 1 - min(chromadb_distance, 1.0)
   ```

2. **Name Matching** (30% weight) - Fuzzy string match
   ```python
   score = fuzz.partial_ratio(task_description, component_name) / 100.0
   ```

3. **Package Matching** (20% weight) - Label-based filtering
   ```python
   if task_label in component.package: score += 0.5
   ```

4. **Stereotype Matching** (10% weight) - Keyword detection
   ```python
   if "service" in task and component.stereotype == "service": score = 1.0
   ```

**Output:** Top 10 components ranked by weighted score

#### Stage 3: Pattern Matcher (TF-IDF + Rules)

**Test Pattern Matching (TF-IDF):**
```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Build corpus: task description + all test names/scenarios
corpus = [task_description] + [test.name + " ".join(test.scenarios) for test in tests]

# TF-IDF vectorization
vectorizer = TfidfVectorizer(stop_words='english', max_features=100)
tfidf_matrix = vectorizer.fit_transform(corpus)

# Cosine similarity
similarities = cosine_similarity(tfidf_matrix[0], tfidf_matrix[1:]).flatten()

# Top 5 most similar tests
top_tests = sorted(zip(tests, similarities), reverse=True)[:5]
```

**Security/Validation/Error Pattern Matching (Rule-Based):**
- Security: File path prefix matching (143 configs)
- Validation: Target class matching (149 patterns)
- Error Handling: Keyword matching (23 patterns)

#### Upgrade Rules Engine (IMPLEMENTED)

> **Reference Diagram:** [upgrade-rules-engine.drawio](diagrams/upgrade-rules-engine.drawio) - Upgrade Detection & Assessment Flow

A generic, framework-agnostic rules engine for upgrade task planning. All upgrade logic is gated behind `task_type == "upgrade"` — feature and bugfix tasks are completely unchanged.

**Task Type Detection (Stage 1):** Score-based classification with threshold >= 3:

| Signal Strength | Weight | Examples |
|-----------------|--------|----------|
| Strong | 3 | "angular upgrade", "spring boot upgrade", "java upgrade", "playwright update" |
| Medium | 2 | "version bump", "breaking changes", "migration guide", "ng update" |
| Weak | 1-2 | Generic "upgrade"/"migrate" combined with framework name |

**Architecture:** 4 components in `pipelines/development_planning/upgrade_rules/`:

| Component | File | Purpose |
|-----------|------|---------|
| Rule Types | `base.py` | Pure dataclasses: `UpgradeRule`, `UpgradeRuleSet`, `CodePattern`, `UpgradeImpact` |
| Scanner | `scanner.py` | Regex-based file scanning (2-5s, skips node_modules/.git/dist) |
| Engine | `engine.py` | Orchestrator: detect framework → select rules → scan → assess |
| Rules | `angular.py`, `spring.py`, `java.py`, `playwright.py` | Declarative rule definitions per framework |

**Framework Rules (40 total):**

| Framework | Rule Sets | Rules | Version Range | Key Changes |
|-----------|-----------|-------|---------------|-------------|
| Angular | 4 | 17 | 18→19, 19→20, Signals, Third-party | Standalone default, control flow, Karma→Vitest, Sass compiler |
| Spring | 4 | 12 | 2→3, 3.1→3.2, 3.2→3.3, 3.3→3.4 | Jakarta migration, SecurityFilterChain, RestClient, virtual threads |
| Java | 1 | 5 | 17→21 | SecurityManager removed, finalize deprecated, Gradle/Maven compat |
| Playwright | 1 | 6 | 1→2 | Locator API, waitForURL, ElementHandle, Cucumber compat |

**Severity Levels:** `BREAKING` | `DEPRECATED` | `RECOMMENDED` | `OPTIONAL`

**Categories:** `API_CHANGE` | `MIGRATION` | `DEPENDENCY` | `BUILD_CONFIG` | `TEST_RUNNER` | `SYNTAX`

**Pipeline Integration:**
1. Stage 1 detects `task_type="upgrade"` via score-based analysis
2. Stage 2 returns ALL components in the affected container (not top-K scoring)
3. Stage 3 invokes `UpgradeRulesEngine`: detect framework → select applicable rules → scan target repo → produce impact assessment
4. Stage 4 receives upgrade assessment with migration_sequence, effort estimates, and schematics alongside normal context
5. Stage 5 validates upgrade plan completeness (migration_sequence, verification_commands, effort)

**Extensibility:** To add a new framework, create `{framework}.py` with `UpgradeRuleSet` list and register it in `engine.py:_auto_register_rules()`.

#### Output Schema

```json
{
  "task_id": "PROJ-123",
  "source_files": ["inputs/tasks/PROJ-123.xml"],
  "understanding": {
    "summary": "Add email notification on user registration",
    "requirements": ["Send welcome email", "Include activation link"],
    "acceptance_criteria": ["Email sent within 1 minute"],
    "technical_notes": "Use existing EmailService, async processing"
  },
  "development_plan": {
    "affected_components": [
      {
        "id": "component.backend.service.user_service_impl",
        "name": "UserServiceImpl",
        "stereotype": "service",
        "layer": "application",
        "relevance_score": 0.95,
        "change_type": "modify",
        "source": "chromadb"
      }
    ],
    "interfaces": [{"path": "/api/users/register", "method": "POST", ...}],
    "dependencies": [{"from": "UserServiceImpl", "to": "EmailService", ...}],

    "implementation_steps": [
      "1. Add EmailService dependency to UserServiceImpl (constructor injection)",
      "2. Create sendWelcomeEmail(User user) private method",
      "3. Call sendWelcomeEmail() from registerUser() after user creation",
      "4. Add @Async annotation for non-blocking email sending"
    ],

    "test_strategy": {
      "unit_tests": ["UserServiceImplTest.testSendEmail()"],
      "integration_tests": ["UserRegistrationIT.testEmailSent()"],
      "similar_patterns": [
        {
          "name": "OrderServiceImplTest",
          "framework": "junit",
          "relevance_score": 0.87,
          "pattern_description": "Similar unit test with @MockBean injection"
        }
      ],
      "recommended_framework": "junit"
    },

    "security_considerations": [
      {
        "security_type": "authentication",
        "recommendation": "Verify user is authenticated before sending email"
      }
    ],

    "validation_strategy": [
      {
        "field": "email",
        "validation_type": "not_null",
        "recommendation": "Use @NotNull @Email on User.email field"
      }
    ],

    "error_handling": [
      {
        "exception_class": "EmailSendException",
        "handling_type": "exception_handler",
        "recommendation": "Add @ExceptionHandler in DefaultExceptionHandler"
      }
    ],

    "architecture_context": {
      "style": "Modular Monolith",
      "layer_pattern": "Controller → Service → Repository",
      "quality_grade": "C",
      "layer_compliance": ["UserService -> EmailService (valid)"]
    },

    "estimated_complexity": "Low",
    "complexity_reasoning": "Simple service call addition, existing infrastructure",
    "estimated_files_changed": 3,
    "risks": ["Email failure should not block registration"],

    "evidence_sources": {
      "components": "architecture_facts.json (951 components)",
      "test_patterns": "architecture_facts.json (925 tests, TF-IDF similarity)",
      "security": "architecture_facts.json (143 security details, rule-based)",
      "validation": "architecture_facts.json (149 validation patterns, regex)",
      "error_handling": "architecture_facts.json (23 error patterns, keyword)",
      "architecture": "analyzed_architecture.json",
      "semantic_search": "ChromaDB (Discover)"
    }
  }
}
```

**Upgrade Plan Output (when `task_type == "upgrade"`):**

The plan JSON includes an additional `upgrade_plan` section:

```json
{
  "development_plan": {
    "...": "normal plan fields...",

    "upgrade_plan": {
      "framework": "Angular",
      "current_version": "18",
      "target_version": "20",
      "migration_sequence": [
        {
          "step": 1,
          "rule_id": "ng19-standalone-default",
          "title": "Standalone components are now default",
          "severity": "breaking",
          "occurrences": 16,
          "effort_minutes": 160,
          "migration_steps": [
            "1. Run: ng generate @angular/core:standalone-migration",
            "2. Review generated changes per module",
            "3. Remove empty NgModules after migration"
          ],
          "schematic": "ng generate @angular/core:standalone-migration"
        }
      ],
      "summary": {
        "total_rules_triggered": 12,
        "total_occurrences": 489,
        "total_affected_files": 89,
        "estimated_effort_minutes": 852,
        "estimated_effort_hours": 14.2,
        "breaking_changes": 4,
        "deprecated_apis": 5
      },
      "verification_commands": ["ng build", "ng test"]
    }
  }
}
```

#### Data Utilization (100% of Discover through Analyze)

Plan Hybrid Pipeline uses **ALL** outputs from previous phases:

**From Discover:**
- ChromaDB vector store (semantic search in Stage 2)

**From Extract (architecture_facts.json - ALL 17 keys):**
- `components` [951] → Component discovery (Stage 2)
- `interfaces` [226] → API endpoint lookup (Stage 2)
- `relations` [190] → Dependency graph (Stage 2)
- `endpoint_flows` [206] → Request flow analysis (Stage 2)
- `tests` [925] → **TF-IDF test pattern matching** (Stage 3)
- `security_details` [143] → **Rule-based security lookup** (Stage 3)
- `validation` [149] → **Regex validation matching** (Stage 3)
- `error_handling` [23] → **Keyword error matching** (Stage 3)
- `workflows` [42] → Business context (Stage 3)
- `dependencies` [170] → Dependency impact (Stage 2)
- `tech_versions` [8] → Tech stack info (Stage 4)
- `evidence` [2508] → Traceability (Stage 5)

**From Analyze:**
- `analyzed_architecture.json` → Architecture style, patterns, quality (Stage 4+5)

**From Upgrade Rules Engine (when task_type="upgrade"):**
- Target repository → Live code scanning for deprecated APIs, breaking changes (Stage 3)
- `containers` from `architecture_facts.json` → Framework and version detection (Stage 3)
- Declarative rules (40 rules across 4 frameworks) → Pattern matching + migration steps (Stage 3)

**Comparison with CrewAI approach:** The Hybrid Pipeline uses the same input data but processes it algorithmically (TF-IDF, fuzzy matching, rule-based lookup) instead of through LLM agents, resulting in 10-20x speedup and 95%+ success rate.

---

### 4.6 Implement Phase (HYBRID PIPELINE - IMPLEMENTED)

| Attribute | Specification |
|-----------|---------------|
| Type | Pipeline (Hybrid: Deterministic + LLM per file + Build Verification) |
| Module | `pipelines/code_generation/` |
| LLM Requirement | Yes (Stage 3: generation, Stage 4b: optional self-healing) |
| Input | `knowledge/plan/{task_id}_plan.json` (Plan) |
| | Target repository source code (`PROJECT_PATH`) |
| | `architecture_facts.json` (Extract, for file path resolution) |
| Output | Git branch `codegen/batch-{timestamp}` (multi-task) or `codegen/{task_id}` (single) |
| | `knowledge/implement/{task_id}_report.json` |
| Dependency | Plan |
| Status | **IMPLEMENTED** |

#### Architecture: Hybrid Pipeline

**Why Hybrid?** Code generation needs precision, not creativity. Each modified file has a clear context (existing code + plan + patterns), and the LLM's job is to produce valid code that fits. Multi-agent crews waste tokens on inter-agent coordination and produce inconsistent style across files. One LLM call per file with a strategy-specific prompt (feature/bugfix/upgrade/refactoring) gives predictable, reviewable output that developers trust.

**6-Stage Pipeline:**

```
Stage 1: Plan Reader (Deterministic, <1s) - IMPLEMENTED
  └─ Read Plan output JSON → CodegenPlanInput
  └─ Resolve missing file paths from architecture_facts.json
  └─ Select strategy (feature/bugfix/upgrade/refactoring)

Stage 2: Context Collector (File I/O, 2-5s) - IMPLEMENTED
  └─ Read current source files from target repo
  └─ Detect language, find sibling files, extract related patterns
  └─ Truncate large files (>12K chars) to fit LLM context

Stage 3: Code Generator (LLM, 10-30s per file) - IMPLEMENTED ← PRIMARY LLM CALLS
  └─ Strategy-specific prompt per file (feature/bugfix/upgrade/refactoring)
  └─ Retry with backoff on failure (configurable CODEGEN_MAX_RETRIES)
  └─ Rate limiting between calls (configurable CODEGEN_CALL_DELAY)

Stage 4: Code Validator (Deterministic, 1-3s) - IMPLEMENTED
  └─ Syntax validation (balanced braces/parens, class declarations)
  └─ Security scan (hardcoded secrets, SQL injection, XSS, eval)
  └─ Pattern compliance (class name matches file, exports present)
  └─ Unified diff generation for modified files

Stage 4b: Build Verifier (Subprocess + LLM heal, 30s-5min) - IMPLEMENTED
  └─ Group generated files by target container (backend/frontend/import_schema)
  └─ Backup-and-restore: write files to disk, build, always restore
  └─ Per-container build: gradlew compileJava (backend), ng build (frontend)
  └─ Self-healing loop: parse errors → LLM fix → re-validate → retry (max 3x)
  └─ Error parsers: javac (File.java:42: error:) and tsc (file.ts:42:10 - error TS2345:)
  └─ Configurable: CODEGEN_BUILD_VERIFY (on/off), CODEGEN_BUILD_MAX_RETRIES
  └─ Works identically in dry_run and normal mode (Stage 5 does final writes)

Stage 5: Output Writer (Git + File I/O, 2-5s) - IMPLEMENTED
  └─ Safety: abort if working tree dirty, never push, never touch main
  └─ Single task: branch codegen/{task_id}, write files, commit, switch back
  └─ Multi-task cascade: single branch codegen/batch-{timestamp}, sequential commits
  └─ >50% failure threshold → abort entire task
  └─ Write JSON report to knowledge/implement/ (includes build_verification results)

Total: 30s-10min depending on file count and build times

Cascade Mode (Multi-Task):
  When multiple plan files exist, tasks are processed sequentially on ONE branch.
  Each task sees cumulative file changes from all prior tasks.
  └─ setup_cascade_branch() → codegen/batch-YYYYMMDD-HHMMSS
  └─ cascade_write_and_commit() per task (no branch switching)
  └─ teardown_cascade() → switch back to original branch
```

#### Build Verification Flow

```
For each container (backend, frontend, import_schema):
  1. backup.apply()   — write ALL generated files to disk, save originals
  2. Run build command (subprocess, with timeout)
  3. If success → done
  4. If fail → parse errors (javac/tsc patterns)
     └─ Match errors to generated files
     └─ For each failing file: LLM heal prompt → fix code → re-validate syntax
     └─ Retry build (up to CODEGEN_BUILD_MAX_RETRIES times)
  5. backup.restore() — ALWAYS restore originals (Stage 5 handles final writes)
```

| Container | Build Command | Timeout |
|-----------|--------------|---------|
| `container.backend` | `gradlew.bat compileJava -q` | 120s |
| `container.frontend` | `npx ng build --configuration=development` | 180s |
| `container.import_schema` | `gradlew.bat compileJava -q` | 120s |

#### Strategy Pattern

| Strategy | Task Type | Key Behavior |
|----------|-----------|-------------|
| `FeatureStrategy` | feature | Add new code following existing patterns |
| `BugfixStrategy` | bugfix | Minimal targeted changes only |
| `UpgradeStrategy` | upgrade | Apply migration rules per file |
| `RefactoringStrategy` | refactoring | Restructure while preserving behavior |

#### Safety Features

| Feature | Description |
|---------|-------------|
| **Dry-run mode** | `--dry-run` runs Stages 1-4b but skips file writes and git (Stage 4b still builds to verify) |
| **Dirty tree check** | Aborts if target repo has uncommitted changes |
| **Branch isolation** | Single: `codegen/{task_id}`, Multi: `codegen/batch-{timestamp}`, never touches main/develop |
| **No push** | Never pushes to remote — user reviews and pushes manually |
| **Failure threshold** | Aborts if >50% of files fail generation/validation |
| **Security scan** | Blocks hardcoded secrets, SQL injection, XSS, eval/exec |
| **Explicit git add** | Only stages files explicitly written (no `git add -A`) |
| **Build verification** | Compiles generated code per container before committing (Stage 4b) |
| **Self-healing** | On build failure, parses errors and uses LLM to fix (max 3 retries) |
| **Backup-restore** | Stage 4b always restores files after build verification (even on crash) |

#### CLI: `codegen` Command

```bash
# Generate code for all pending plans
aicodegencrew codegen

# Single task
aicodegencrew codegen --task-id PROJ-123

# Preview mode (no file writes)
aicodegencrew codegen --dry-run

# Skip re-indexing
aicodegencrew codegen --index-mode off
```

---

## 5. Knowledge Management

> **Reference Diagrams:**
> - [docs/diagrams/knowledge-structure.drawio](docs/diagrams/knowledge-structure.drawio)
> - [docs/diagrams/evidence-flow.drawio](docs/diagrams/evidence-flow.drawio)

### 5.1 Data Flow Matrix

| Source Phase | Output Artifact | Consumer Phase |
|--------------|-----------------|----------------|
| Discover | ChromaDB Vector Index | Extract, Analyze, Document (optional), Plan |
| Extract | `architecture_facts.json` | Analyze, Document, Plan |
| Extract | `evidence_map.json` | Analyze, Document, Plan |
| Analyze | `analyzed_architecture.json` | Document, Plan |
| Document | `c4/*.md`, `c4/*.drawio` | Plan |
| Document | `arc42/*.md` | Plan |
| Plan | Development Plans | Implement |
| Implement | Git branch + codegen report | Verify, Deliver |

### 5.2 Knowledge Directory Structure

```
knowledge/
    README.md
    user_preference.txt
    
    architecture/
        architecture_facts.json     # From Extract (truth)
        evidence_map.json           # From Extract (evidence)

        c4/                         # From Document (C4Crew)
            c4-context.md
            c4-context.drawio
            c4-container.md
            c4-container.drawio
            c4-component.md
            c4-component.drawio
            c4-deployment.md
            c4-deployment.drawio

        arc42/                      # From Document (Arc42Crew)
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
            
        quality/                    # From Document
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
| `PROJECT_PATH` | Target repository path (local) | Required (unless `GIT_REPO_URL` set) |
| `GIT_REPO_URL` | Git HTTPS URL to clone (optional, overrides `PROJECT_PATH`) | Empty (disabled) |
| `GIT_BRANCH` | Git branch to checkout (empty = auto-detect main/master) | Empty |
| `OLLAMA_BASE_URL` | Ollama server endpoint | `http://127.0.0.1:11434` |
| `MODEL` | LLM model identifier | `gpt-oss-120b` |
| `EMBED_MODEL` | Embedding model identifier | `all-minilm:latest` |
| `INDEX_MODE` | Indexing behavior | `auto` |
| `LLM_PROVIDER` | LLM provider selection | `local` |

### 6.2 Git Repository Support

Instead of pointing to a local directory via `PROJECT_PATH`, you can specify a Git HTTPS URL.
The system clones the repository into `.cache/repos/<repo_name>/` and keeps it up-to-date on subsequent runs.

| Setting | Description |
|---------|-------------|
| **Priority** | `GIT_REPO_URL` > `PROJECT_PATH` (backward-compatible) |
| **Default Branch** | Auto-detected via `git ls-remote --symref` (main/master), fallback: `main` |
| **Credentials** | Prompted interactively via `getpass` on first clone, cached in-memory only |
| **Submodules** | Always cloned/updated (`--recurse-submodules`) |
| **Clone Location** | `.cache/repos/<repo_name>/` |
| **Update** | `git fetch --all --prune` + `checkout` + `pull --ff-only` |
| **Security** | `GIT_TERMINAL_PROMPT=0` (no hanging), credentials never logged |

**Usage via .env:**
```env
GIT_REPO_URL=https://gitlab.example.com/team/project.git
GIT_BRANCH=           # empty = auto-detect
```

**Usage via CLI (overrides .env):**
```bash
python -m aicodegencrew run --preset architect --git-url https://gitlab.example.com/team/project.git --branch develop
python -m aicodegencrew index --git-url https://gitlab.example.com/team/project.git
```

**Module:** `shared/utils/git_repo_manager.py` (`GitRepoManager` class)

### 6.3 LLM Provider Configuration

| Provider | Configuration | Notes |
|----------|---------------|-------|
| Local | `LLM_PROVIDER=local` | Ollama local instance |
| On-Premise | `LLM_PROVIDER=onprem` | Requires `API_BASE_URL` |

Embeddings utilize local Ollama exclusively, independent of LLM provider configuration.

### 6.4 INDEX_MODE Configuration

| Mode | Description |
|------|-------------|
| `off` | Skip indexing; utilize existing index |
| `auto` | Conditional indexing based on change detection (default). Persistent state (`knowledge/discover/.indexing_state.json`) survives ChromaDB deletion — warns instead of silently re-indexing |
| `force` | Clear ChromaDB directory and perform complete re-indexing |
| `smart` | Incremental update — per-file hash check against ChromaDB, only re-embeds changed files |

---

## 7. Execution Presets

Presets are defined in `config/phases_config.yaml` and validated strictly by the CLI.
Unknown presets raise an error instead of silently falling back.

| Preset | Phases | Description |
|--------|--------|-------------|
| `index` | 0 | Repository indexing only |
| `scan` | 0, 1 | Indexing + Architecture Facts (no LLM) |
| `analyze` | 0, 1, 2 | Indexing + Facts + Analysis |
| `document` | 0, 1, 2, 3 | C4 Model + arc42 documentation (excludes Plan) |
| `plan` | 0, 1, 2, 4 | Development planning (most common preset) |
| `develop` | 0, 1, 2, 4, 5 | Planning + code generation |
| `architect` | 0, 1, 2, 3, 4 | Architecture documentation + Development Planning |
| `full` | 0-7 | Complete automated SDLC pipeline |

---

## 8. Command Reference

### 8.1 Phase Listing

```bash
python -m aicodegencrew list
```

### 8.2 Development Planning (Shortcut)

```bash
# Quick: Development planning (Discover+Extract+Analyze+Plan)
aicodegencrew plan

# With custom .env file
aicodegencrew --env /path/to/project.env plan

# Override index mode
aicodegencrew plan --index-mode off
```

### 8.3 Preset Execution

```bash
# Only extract facts (no LLM)
python -m aicodegencrew run --preset scan

# Full architecture documentation (C4 + arc42)
python -m aicodegencrew run --preset document

# Analysis only (no synthesis)
python -m aicodegencrew run --preset analyze
```

### 8.4 Single Phase Execution

```bash
# Extract: Architecture Facts
python -m aicodegencrew run --phases extract

# Analyze: Architecture Analysis
python -m aicodegencrew run --phases analyze

# Document: Architecture Synthesis (C4 + arc42)
python -m aicodegencrew run --phases document
```

### 8.5 Options

| Option | Scope | Description |
|--------|-------|-------------|
| `--env PATH` | Global | Path to `.env` configuration file (default: `.env` in CWD) |
| `--preset NAME` | `run` | Run a named preset (validated against config) |
| `--phases P1 P2` | `run` | Run specific phases by ID |
| `--repo-path PATH` | `run`, `plan` | Target repository path |
| `--index-mode MODE` | `run`, `plan`, `index` | Override INDEX_MODE (`off`, `auto`, `force`, `smart`) |
| `--git-url URL` | `run`, `index` | Git HTTPS URL (overrides `GIT_REPO_URL` in .env) |
| `--branch NAME` | `run`, `index` | Git branch (overrides `GIT_BRANCH` in .env) |
| `--clean` | `run` | Clean knowledge directories before running |
| `--no-clean` | `run` | Skip auto-cleaning |
| `--config PATH` | `run`, `plan`, `list` | Custom phases_config.yaml path |

---

## 9. Logging & Observability

### 9.1 Design Principles

1. **Single output path**: Everything through `logger`, zero `print()` in production code
2. **Structured metrics for every measurable event**: phases, crews, guardrails, tools
3. **Run correlation**: `RUN_ID` (UUID) on every metric event for cross-event joining
4. **Dead code removal**: No unused callback classes or alias wrappers

### 9.2 Log Structure

```
logs/
├── current.log          # Active session (overwritten each run)
├── metrics.jsonl         # Structured JSON metrics (append-only)
├── run_history.jsonl     # Pipeline run history (append-only)
└── errors.log           # Persistent errors (rotating, 5MB x 3)
```

### 9.3 Run Correlation

Every process generates a `RUN_ID` (e.g. `a3f8b2c1`) — a short UUID injected into:
- Every `log_metric()` event in `metrics.jsonl`
- The session banner in `current.log`

```
============================================================
SESSION START: 2026-02-07T23:40:28 | run_id=a3f8b2c1
Log Level: INFO
============================================================
```

This enables querying all events from a single pipeline run:
```bash
# Show all events from run a3f8b2c1
python -c "import json; [print(json.loads(l)['data']) for l in open('logs/metrics.jsonl') if 'a3f8b2c1' in l]"
```

### 9.4 Step Logging API

```python
from .shared.utils.logger import (
    step_start,     # [STEP] ══════ Name ══════
    step_done,      # [DONE] ══════ Name ══════ (12.3s)
    step_fail,      # [FAIL] ══════ Name ══════
    step_info,      #        Info message
    step_warn,      #        Warning message
    step_progress,  #        [██████░░░░] 5/10 - items
    log_metric,     # Structured JSON event → metrics.jsonl
    RUN_ID,         # Short UUID for this process
)
```

### 9.5 Structured Metrics (metrics.jsonl)

Each line in `metrics.jsonl` is a JSON object with `run_id` for correlation:

```json
{"ts": "2026-02-07T14:30:00", "level": "INFO", "logger": "aicodegencrew", "msg": "mini_crew_complete", "data": {"event": "mini_crew_complete", "run_id": "a3f8b2c1", "crew_type": "C4", "crew_name": "context", "duration_seconds": 180.5, "total_tokens": 1500, "estimated": false}}
```

#### Event Catalog

| Event | Source | Key Fields |
|-------|--------|------------|
| `phase_start` | orchestrator | `phase_id` |
| `phase_complete` | orchestrator | `phase_id`, `duration_seconds`, `status` |
| `phase_failed` | orchestrator | `phase_id`, `duration_seconds`, `error` |
| `pipeline_complete` | orchestrator | `status`, `total_duration`, `phases_run`, `phases_succeeded` |
| `mini_crew_complete` | base_crew / crew.py | `crew_type`, `crew_name`, `duration_seconds`, `tasks`, `attempts`, `total_tokens`, `estimated` |
| `mini_crew_failed` | base_crew / crew.py | `crew_type`, `crew_name`, `duration_seconds`, `error_type`, `error` |
| `guardrail_blocked` | tool_guardrails | `tool_name`, `reason` (`identical_call` or `budget_exhausted`) |
| `guardrail_summary` | base_crew / crew.py | `crew_name`, `total_calls`, `unique_calls`, `blocked` |

All events share `run_id` for correlation.

### 9.6 CrewAI Callbacks

Agent step and task callbacks (`crew_callbacks.py`) route through `logger`:

| Event | Log Level | Destination | Example |
|-------|-----------|-------------|---------|
| Agent thinking | `DEBUG` | File only | `[THINK] Architect: Analyzing macro...` |
| Tool call | `INFO` | File + console | `[TOOL] get_statistics: {}` |
| Tool result | `DEBUG` | File only | `[TOOL_RESULT] {"components": 951...}` |
| Task completion | `INFO` | File + console | `[TASK] Completed: Analyze macro arch...` |

### 9.7 Features

| Feature | Description |
|---------|-------------|
| **Run Correlation** | `RUN_ID` (uuid4[:8]) on every metric event |
| **Run History** | Append-only `run_history.jsonl` tracking all pipeline runs and resets |
| **Step Tracking** | Automatic timing per step |
| **Progress Bar** | Visual progress with `step_progress()` |
| **Structured Metrics** | JSON events in `metrics.jsonl` via `log_metric()` |
| **Guardrail Metrics** | Blocked tool calls + summary stats per crew |
| **Token Tracking** | Real token counts when available, `estimated=true` as fallback |
| **Unbuffered** | Real-time log viewing |
| **Singleton** | Logger initialized once |
| **MCP-Safe** | Console logging disabled when `MCP_STDIO_MODE` is set |

---

## 10. Diagrams Overview

> All diagrams located in `docs/diagrams/`

| Diagram | File | Description |
|---------|------|-------------|
| Pipeline Flow | `pipeline-flow.drawio` | Full pipeline flow across all layers |
| Layer Architecture | `layer-architecture.drawio` | Detailed 4-Layer Architecture |
| Evidence Flow | `evidence-flow.drawio` | Evidence data flow |
| Knowledge Structure | `knowledge-structure.drawio` | Knowledge base organization |
| Facts Collectors | `facts-collectors.drawio` | Deterministic collectors in 4 groups |
| Analysis Crew | `analysis-crew.drawio` | Multi-agent analysis crew |
| Synthesis Crew | `synthesis-crew.drawio` | C4 + Arc42 synthesis crews |
| Dev Planning Pipeline | `development-planning-pipeline.drawio` | Hybrid pipeline (5 stages) |
| Analysis Crew Schema | `analysis-crew-schema.drawio` | Schema validation flow |

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

Edit `.env` to configure repository access and other parameters:

**Option A: Local repository**
```env
PROJECT_PATH=C:\path\to\your\repo
```

**Option B: Git URL (clones automatically)**
```env
GIT_REPO_URL=https://gitlab.example.com/team/project.git
GIT_BRANCH=          # empty = auto-detect default branch
```

Both can be set simultaneously. `GIT_REPO_URL` takes priority when set.

---

## 13. Deployment

### 13.1 Deployment Modes

| Mode | Source Visible | Use Case |
|------|---------------|----------|
| **Development** (`pip install -e .`) | Yes | Development only |
| **Wheel Distribution** (`pip install *.whl`) | No (`.pyc` only) | Internal distribution |
| **Docker** (`docker run`) | No (compiled in image) | Production deployment |

### 13.2 Wheel Distribution (No Source Code)

Build a wheel package that contains only compiled Python bytecode:

```bash
pip install build
python -m build --wheel
# Output: dist/aicodegencrew-0.1.0-py3-none-any.whl
```

Distribute the `.whl` file to developers. They install it with:

```bash
pip install aicodegencrew-0.1.0-py3-none-any.whl[parsers]
aicodegencrew --env /path/to/my.env plan
```

### 13.3 Docker Deployment (Recommended)

Multi-stage Dockerfile ensures source code is only present in the build stage.
The final image contains only the installed wheel and config files.

```bash
# Build image
docker build -t aicodegencrew:latest .

# Run with docker-compose (preferred)
docker-compose run aicodegencrew plan

# Run directly
docker run --network host \
  -v /path/to/.env:/app/.env:ro \
  -v /path/to/repo:/repo:ro \
  -v ./inputs:/app/inputs:ro \
  -v ./knowledge:/app/knowledge \
  -v ./.cache:/app/.cache \
  -e PROJECT_PATH=/repo \
  aicodegencrew:latest plan
```

### 13.4 Volume Mounts

| Mount | Container Path | Mode | Purpose |
|-------|---------------|------|---------|
| `.env` | `/app/.env` | ro | Configuration |
| Target repo | `/repo` | ro | Repository to analyze |
| `inputs/` | `/app/inputs` | ro | JIRA XML, DOCX, Excel files |
| `knowledge/` | `/app/knowledge` | rw | Output: plans, architecture docs |
| `.cache/` | `/app/.cache` | rw | ChromaDB vector store |

### 13.5 Network Requirements

The container needs access to:
- **Ollama** (`localhost:11434`): Embedding generation
- **On-prem LLM** (e.g. `sov-ai-platform.nue.local.vm:4000`): Plan generation

Use `network_mode: host` in docker-compose or `--network host` with docker run.

### 13.6 Release Process

Build and assemble a release package using the release script:

```bash
# Wheel only (no Docker)
python scripts/build_release.py

# Wheel + Docker image
python scripts/build_release.py --docker

# Wheel + Docker + push to registry
python scripts/build_release.py --docker --push --registry your-registry.example.com
```

Output: `dist/release/` containing:

| File | Purpose |
|------|---------|
| `aicodegencrew-{version}-py3-none-any.whl` | Installable package (no source code) |
| `aicodegencrew-{version}.tar.gz` | Docker image (optional, with `--docker`) |
| `.env.example` | Configuration template |
| `docker-compose.yml` | Docker Compose file |
| `config/phases_config.yaml` | Phase configuration |
| `USER_GUIDE.md` | End-user documentation |
| `install.bat` / `install.sh` | Installation scripts |

### 13.7 Delivery to End Users

The `dist/release/` folder is the complete delivery package. Send it via:
- **Fileshare** (simplest): ZIP and share via Teams/SharePoint
- **Nexus/Artifactory**: Upload `.whl` as Python package
- **Docker Registry**: Push image with `--push --registry` flag

End user workflow:
1. Unzip release package
2. Run `install.bat` (Windows) or `install.sh` (Linux)
3. Copy `.env.example` to `.env`, configure settings
4. Start Ollama: `ollama serve`
5. Run: `aicodegencrew --env .env plan`

### 13.8 Version Management

- Version is defined in `pyproject.toml` (`version = "X.Y.Z"`)
- Changes documented in `CHANGELOG.md`
- Release script reads version automatically from `pyproject.toml`
- Docker images tagged with version + `latest`

---

## 14. Testing

### 14.1 Full Test Suite

```
pytest tests/
```

### 14.2 Component Tests

```
pytest tests/test_indexing.py -v
pytest tests/test_quality_gate.py -v
```

---

## 15. SDLC Dashboard (Web UI)

### Why a Dashboard?

CLI tools are powerful for automation but create friction for daily developer workflows. Developers want to:
- **See results visually** — structured plan views instead of raw JSON dumps
- **Upload files without touching `.env`** — drag-and-drop JIRA exports instead of editing paths
- **Monitor pipelines in real-time** — live log streaming instead of `tail -f`
- **Browse artifacts without an IDE** — rendered Markdown, syntax-highlighted JSON, colored diffs
- **Manage git branches** — see what codegen produced without switching to terminal

The Dashboard wraps the same CLI pipeline in a visual interface. It does NOT replace the CLI — both share the same backend logic.

### 15.1 Architecture

| Component | Technology | Why This Choice |
|-----------|-----------|-----------------|
| **Backend** | FastAPI (Python) | Same language as pipeline — can import directly, no serialization overhead |
| **Frontend** | Angular 21 + Material Design | Enterprise-standard, standalone components, zoneless change detection for performance |
| **Proxy** | Nginx | Required for SSE buffering (browsers limit concurrent SSE connections per domain) |
| **Deployment** | Docker Compose | One command to start everything; volumes for persistent data |

### 15.2 Backend API

10 routers registered in `ui/backend/main.py`:

| Router | Prefix | Key Endpoints | Purpose |
|--------|--------|---------------|---------|
| **pipeline** | `/api/pipeline` | `POST /run`, `POST /cancel`, `GET /stream`, `GET /history` | Pipeline execution + SSE streaming |
| **env** | `/api/env` | `GET /`, `PUT /`, `GET /schema` | .env read/write with variable metadata |
| **phases** | `/api/phases` | `GET /`, `GET /presets`, `GET /status` | Phase config from `phases_config.yaml` |
| **knowledge** | `/api/knowledge` | `GET /`, `GET /file` | Knowledge base file browsing + content |
| **metrics** | `/api/metrics` | `GET /` | `metrics.jsonl` event viewing |
| **reports** | `/api/reports` | `GET /`, `GET /branches`, `DELETE /branches/{id}` | Plans, codegen reports, git branches |
| **logs** | `/api/logs` | `GET /files`, `GET /` | Log file tailing |
| **diagrams** | `/api/diagrams` | `GET /`, `GET /file/{path}` | DrawIO + Mermaid diagrams |
| **inputs** | `/api/inputs` | `GET /`, `POST /{cat}/upload`, `DELETE /{cat}/{file}` | File upload, 4 categories, auto `.env` config |

### 15.3 Pipeline Execution Service

**Why Subprocess Isolation?** The pipeline uses CrewAI agents, ChromaDB, and LLM connections that can crash or hang. Running the pipeline as a subprocess means the Dashboard stays responsive even if the pipeline fails.

```
Dashboard (FastAPI)
  └─ PipelineExecutor (singleton)
      └─ subprocess.Popen("python -m aicodegencrew run --preset X --env path")
          ├─ stdout → _log_lines[] buffer (thread-safe)
          └─ exit code → state transition (completed/failed)
```

**Key Design Decisions:**

| Decision | Rationale |
|----------|-----------|
| Subprocess isolation | Pipeline crash won't crash the dashboard |
| Singleton executor | Only one pipeline at a time (409 on concurrent attempt) |
| Background monitor thread | Non-blocking stdout capture |
| SSE streaming | Real-time log lines + phase status (500ms poll) |
| Temp `.env.run` file | Override env vars without modifying original `.env` |
| `metrics.jsonl` parsing | Extract phase progress from `phase_start/phase_complete/phase_failed` events |

**State Machine:**
```
idle ──[POST /run]──► running ──[completion]──► completed
                         │                      failed
                         └──[POST /cancel]──► cancelled
```

### 15.4 Environment Configuration Service

Reads `.env.example` for variable descriptions, groups variables by category:

| Group | Key Prefixes |
|-------|-------------|
| Repository | `PROJECT_PATH`, `INCLUDE_SUBMODULES` |
| LLM | `LLM_*`, `MODEL`, `API_BASE`, `OPENAI_API_KEY`, `MAX_LLM_*` |
| Embeddings | `OLLAMA_*`, `EMBED_*`, `NO_PROXY` |
| Indexing | `INDEX_*`, `CHROMA_*`, `CHUNK_*`, `MAX_FILE_*`, `MAX_RAG_*` |
| Phase Control | `SKIP_*`, `TASK_INPUT_DIR`, `REQUIREMENTS_DIR`, `LOGS_DIR`, `REFERENCE_DIR` |
| Output | `DOCS_OUTPUT_DIR`, `ARC42_LANGUAGE` |
| Logging | `LOG_LEVEL`, `CREWAI_TRACING` |

### 15.5 Frontend Pages

**Why 9 pages?** Each page maps to one developer concern. Mixing concerns (e.g., logs + metrics on one page) creates cognitive overload. Separate pages with lazy loading keep the UI fast.

| Page | Route | What It Does | Why It Exists |
|------|-------|-------------|---------------|
| **Dashboard** | `/dashboard` | Hero section, phase status cards with color-coded borders, active run banner, quick links | First thing you see — answers "what's the state of my project?" |
| **Run Pipeline** | `/run` | Preset selector, phase checkboxes, env editor, live SSE log viewer, phase timeline, cancel | Central control panel for executing pipelines |
| **Input Files** | `/inputs` | Drag-and-drop upload for 4 categories (tasks, requirements, logs, reference), extension validation, auto `.env` config | Eliminates manual file path configuration in `.env` |
| **Phases** | `/phases` | Phase table with "Run" buttons, preset accordion with "Run Preset" buttons | Fine-grained control for re-running individual phases |
| **Knowledge** | `/knowledge` | Multi-tab browser (Arc42, C4, Knowledge Base, Containers, Dev Plans), rendered previews for JSON/Markdown/AsciiDoc/HTML/Confluence/DrawIO | Browse generated artifacts without leaving the browser |
| **Reports** | `/reports` | **Tab 1:** Structured plan viewer (components table, steps, test strategy, security/validation sections). **Tab 2:** Codegen reports with per-file expandable diff viewer (colored lines). **Tab 3:** Git branch list with delete action | Developer-friendly view of plans and generated code — replaces raw JSON dumps |
| **Metrics** | `/metrics` | Event table with type filtering, run ID tracking | Operational monitoring — which phases took how long, what failed |
| **Logs** | `/logs` | Log file selector, color-coded terminal viewer (ERROR=red, WARNING=yellow) | Debugging — tail logs without SSH |

#### Reports Page: 3-Tab Architecture

**Why structured views?** Raw JSON dumps are unreadable for plans with 20+ affected components. Developers need:

| Tab | Replaces | Key Features |
|-----|----------|-------------|
| **Development Plans** | `<pre>{{ plan \| json }}</pre>` | Summary card, affected components Material table (Name/Stereotype/Layer/Change/Relevance), numbered implementation steps, test strategy with similar patterns, collapsible security/validation/error sections, upgrade plan with migration table |
| **Codegen Reports** | `<pre>{{ report \| json }}</pre>` | File list with action chips (created/modified/deleted), language badges, per-file expandable unified diff with green (+) / red (-) / blue (@@) line coloring |
| **Git Branches** | Nothing (new) | Lists `codegen/*` branches with file count, report indicator, delete button with confirmation dialog |

Each tab has a "Show Raw JSON" toggle for debugging.

#### Input Files: 4-Category Upload System

**Why categories?** Different pipeline stages consume different file types. Categorization enables:
- Extension validation per category (`.xml` for tasks, `.xlsx` for requirements, etc.)
- Auto-configuration of `TASK_INPUT_DIR`, `REQUIREMENTS_DIR`, `LOGS_DIR`, `REFERENCE_DIR` in `.env`
- Supplementary context injection into Plan LLM prompts

| Category | Extensions | Pipeline Consumer |
|----------|-----------|-------------------|
| **Tasks** | `.xml` `.docx` `.pdf` `.txt` `.json` | Stage 1: Input Parser (Plan) |
| **Requirements** | `.xlsx` `.docx` `.pdf` `.txt` `.csv` | Stage 4: Plan Generator (supplementary context) |
| **Logs** | `.log` `.txt` `.xlsx` `.csv` | Stage 4: Plan Generator (supplementary context) |
| **Reference** | `.png` `.jpg` `.svg` `.pdf` `.drawio` `.md` | Stage 4: Plan Generator (supplementary context) |

### 15.6 SSE Streaming

The `/api/pipeline/stream` endpoint sends Server-Sent Events during execution:

| Event Type | Payload | Frequency |
|------------|---------|-----------|
| `log_line` | stdout line from subprocess | As produced |
| `status` | `ExecutionStatus` (state, phases, elapsed) | Every 500ms |
| `pipeline_complete` | Final `ExecutionStatus` | Once, then stream closes |

**Nginx SSE Configuration:**
```nginx
location /api/pipeline/stream {
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 3600s;
    chunked_transfer_encoding off;
}
```

### 15.7 Docker Deployment

```bash
# Start dashboard (backend + frontend)
docker-compose -f ui/docker-compose.ui.yml up --build

# Access: http://localhost (nginx) → proxies /api/* to http://backend:8001
```

**Volume Mounts:**

| Volume | Mode | Purpose |
|--------|------|---------|
| `knowledge/` | read-write | Generated plans, reports, diagrams |
| `logs/` | read-write | Application logs, metrics.jsonl |
| `inputs/` | read-write | Uploaded task files (from Input Files page) |
| `.env` | read-write | User configuration (editable from UI) |
| `.env.example` | read-only | Variable descriptions and defaults |
| `src/` | read-only | Source code for `aicodegencrew` CLI |
| `.cache/` | read-write | ChromaDB vector store |

---

## 16. License

Proprietary — Aymen Mastouri. See [LICENSE](../LICENSE) for details.

© 2026 Aymen Mastouri. All rights reserved
