# Implement Phase Architecture: Hierarchical CrewAI

> **Status**: Implemented (v0.6.0)
> **Author**: Aymen Mastouri
> **Date**: 2026-02-16
> **Module**: `src/aicodegencrew/hybrid/code_generation/`

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Agents](#3-agents)
4. [Tools](#4-tools)
5. [Preflight Modules](#5-preflight-modules)
6. [Post-Crew Processing](#6-post-crew-processing)
7. [Data Flow](#7-data-flow)
8. [Dual-Model Routing](#8-dual-model-routing)
9. [Safety & Guardrails](#9-safety--guardrails)
10. [Environment Variables](#10-environment-variables)
11. [File Structure](#11-file-structure)

---

## 1. Overview

### Architecture Decision

The Implement Phase uses a **hierarchical CrewAI crew** with 4 specialized agents instead of a deterministic pipeline. The key insight: LLMs are better used as *developers with tools* than as *code template engines*.

| Aspect | Old (Pipeline) | New (Hierarchical Crew) |
|--------|---------------|------------------------|
| **Approach** | 1 LLM call per file, rigid stages | Agents with tools, autonomous decisions |
| **Cross-file reasoning** | None | Manager coordinates, shared staging |
| **Self-healing** | Parse errors → re-prompt (1 stage) | Manager delegates fix to Developer with context |
| **Test generation** | Not included | Dedicated Tester Agent |
| **Import handling** | Deterministic fixer only | Agent uses ImportIndex + deterministic fixer |
| **Model routing** | Single model for all | Dual-model: Coder-14B for code, 120B for analysis |

### Reference Diagrams

- [code-generation-pipeline.drawio](../diagrams/code-generation-pipeline.drawio) — Full architecture overview
- [implement-phase-crew.drawio](../diagrams/implement-phase-crew.drawio) — Agent detail view

---

## 2. Architecture

### 3-Phase + Output Writer

```
PREFLIGHT (Deterministic, 0 LLM tokens)
  PlanReader → ImportIndexBuilder → DependencyGraphBuilder → PreflightValidator
  │
  │ GATE: fail → abort before LLM tokens burn
  ▼
CREW EXECUTION (CrewAI Process.hierarchical)
  Manager Agent (120B) coordinates:
    ❶ Developer (Coder 14B) → implement code changes
    ❷ Builder (120B) → verify builds
    ↻ Heal loop: Builder reports errors → Developer fixes → rebuild (max 3x)
    ❸ Tester (Coder 14B) → generate unit tests
  │
  ▼
POST-CREW (Deterministic, 0 LLM tokens)
  ImportFixer → Build Verification → Safety Gate
  │
  ▼
OUTPUT WRITER (Git + File I/O)
  Branch creation → File writes → Git commit → Report JSON
```

### Process Model

CrewAI `Process.hierarchical` — the Manager Agent has `allow_delegation=True` and decides the order of work. Worker agents (Developer, Builder, Tester) have `allow_delegation=False` and execute assigned tasks.

---

## 3. Agents

All agents follow these conventions:
- Python-only configuration (no YAML)
- Fresh LLM instance per agent via `llm_factory`
- `max_iter=25`, `max_retry_limit=3`
- MCP server connection for extended tool access
- Tool guardrails (max 50 total, max 3 identical)

### 3.1 Manager Agent

| Property | Value |
|----------|-------|
| **LLM** | `MODEL` (gpt-oss-120B) via `create_llm()` |
| **LLM Tier** | `analysis` |
| **Role** | Technical Project Lead |
| **allow_delegation** | `True` |
| **Tools** | PlanReader, CodeReader, ImportIndex, DependencyLookup, FactsQuery, RAGQuery, MCP |

**Goal**: Read the development plan, understand the scope, distribute work to specialized agents, validate results, and ensure the generated code compiles and meets acceptance criteria.

**Workflow**:
1. Read development plan (PlanReader)
2. Group affected files by container (backend/frontend)
3. Delegate code implementation to Developer (dependency order)
4. Delegate build verification to Builder
5. On build errors: delegate fix back to Developer (heal loop, max 3x)
6. After successful build: delegate test generation to Tester
7. Quality control: validate final result

**Why 120B**: Needs to understand complex task descriptions, prioritize work, coordinate agents. Does NOT write code.

### 3.2 Developer Agent

| Property | Value |
|----------|-------|
| **LLM** | `CODEGEN_MODEL` (Qwen2.5-Coder-14B) via `create_codegen_llm()` |
| **LLM Tier** | `codegen` |
| **Role** | Senior Full-Stack Developer |
| **allow_delegation** | `False` |
| **Tools** | CodeReader, CodeWriter, ImportIndex, DependencyLookup, FactsQuery, RAGQuery, MCP |

**Goal**: Generate high-quality code changes that compile, follow existing patterns, and integrate with the target codebase. Fix build errors reported by the Builder.

**Workflow per file**:
1. Read source file (CodeReader)
2. Look up correct imports (ImportIndex — language-filtered)
3. Check dependencies (DependencyLookup)
4. Query architecture context (FactsQuery, RAGQuery)
5. Generate code
6. Write to staging (CodeWriter)

**Task-type instructions** are injected into the task description:
- `upgrade`: Apply migration rules, preserve behavior, update imports
- `bugfix`: Minimal targeted changes, no refactoring
- `feature`: Follow existing patterns, add new code
- `refactoring`: Restructure while preserving public API

**Why Coder-14B**: Writes better code than 120B at significantly fewer tokens. Natively understands code patterns, imports, syntax.

### 3.3 Builder Agent

| Property | Value |
|----------|-------|
| **LLM** | `MODEL` (gpt-oss-120B) via `create_llm()` |
| **LLM Tier** | `analysis` |
| **Role** | DevOps & Build Engineer |
| **allow_delegation** | `False` |
| **Tools** | BuildRunner, BuildErrorParser, FactsQuery |

**Goal**: Verify that all code changes compile and build successfully. Parse build errors into structured reports for the Developer to fix.

**Workflow**:
1. Run build per container (BuildRunner — auto-detects gradle/maven/npm)
2. If success: report to Manager
3. If failure: parse errors (BuildErrorParser — javac + tsc patterns)
4. Report structured errors to Manager → Manager delegates fix to Developer

**Build command detection**: Reads `build_system` from `architecture_facts.json`:
- Gradle: `.\gradlew.bat compileJava -q` (Windows) / `./gradlew compileJava -q` (Unix)
- Maven: `.\mvnw.cmd compile -q` / `./mvnw compile -q`
- npm: Reads `package.json` scripts → `npm run build`

**Why 120B**: Needs to UNDERSTAND build output and explain errors, not write code. 120B better at analyzing long text outputs.

### 3.4 Tester Agent

| Property | Value |
|----------|-------|
| **LLM** | `CODEGEN_MODEL` (Qwen2.5-Coder-14B) via `create_codegen_llm()` |
| **LLM Tier** | `codegen` |
| **Role** | Senior Test Engineer |
| **allow_delegation** | `False` |
| **Tools** | TestPattern, TestWriter, CodeReader, RAGQuery, MCP |

**Goal**: Create comprehensive tests for all code changes. Match existing test patterns and frameworks: JUnit 5 + Mockito for Spring Boot, Jasmine + TestBed for Angular.

**Workflow**:
1. Query existing test patterns (TestPattern — 925 test files in target repo)
2. Read changed file (CodeReader)
3. Query similar tests via semantic search (RAGQuery)
4. Generate unit tests matching repository conventions
5. Write tests to staging (TestWriter — validates structure before accepting)

---

## 4. Tools

### 4.1 Existing Tools (unchanged)

| Tool | Used By | Description |
|------|---------|-------------|
| `CodeReaderTool` | Developer, Tester, Manager | Read source files (max 12K chars) |
| `CodeWriterTool` | Developer | Write code to staging dict (not disk) |
| `BuildRunnerTool` | Builder | Execute build per container (subprocess) |
| `BuildErrorParserTool` | Builder | Parse javac/tsc errors into structured objects |
| `TestPatternTool` | Tester | Query test patterns from architecture facts |
| `TestWriterTool` | Tester | Write test files to staging with validation |
| `FactsQueryTool` | All agents | Query architecture facts (16 dimensions) |
| `RAGQueryTool` | Developer, Tester, Manager | Semantic search in ChromaDB (25K chunks) |

### 4.2 New Tools

#### ImportIndexTool

**For**: Developer, Manager
**Purpose**: Look up exact import statements instead of letting the LLM guess.

```
Input:  symbol="CoreModule", from_file="app.module.ts", language="typescript"
Output: "import { CoreModule } from './core/core.module';"
```

**Fix for language-mixing**: The `resolve()` call filters by language — TypeScript files get ONLY TypeScript imports, Java files get ONLY Java imports.

#### DependencyLookupTool

**For**: Developer, Manager
**Purpose**: Understand file dependencies for correct generation order.

```
Input:  file_path="app.module.ts"
Output: {
  "depends_on": ["core.module.ts", "shared.module.ts"],
  "depended_by": ["main.ts"],
  "generation_tier": 1
}
```

#### PlanReaderTool

**For**: Manager
**Purpose**: Read and parse development plan JSON.

```
Input:  task_id="BNUVZ-12529"
Output: { summary, task_type, affected_components, implementation_steps, upgrade_plan }
```

### 4.3 MCP Server (7 tools, reused)

All agents can access the MCP knowledge server (STDIO protocol):
- `get_components`, `get_relations`, `get_endpoints`
- `get_containers`, `get_statistics`
- `get_component_details`, `get_data_model`

---

## 5. Preflight Modules

All preflight modules are **deterministic** (0 LLM tokens) and run BEFORE the crew starts.

### 5.1 PlanReader (`preflight/plan_reader.py`)

- Reads `knowledge/plan/{task_id}_plan.json`
- Resolves file paths from `architecture_facts.json` (ID match → name fallback)
- Handles both dict and string component formats from Phase 4
- Returns `CodegenPlanInput` directly (no strategy dependency)
- Auto-detects `task_type` from keywords if not set

### 5.2 ImportIndexBuilder (`preflight/import_index.py`)

- Scans target repository for all exported symbols
- Builds `symbol → (file_path, import_statement, language)` index
- **2266 symbols, 1984 files** on the target repo (C:\uvz, 3.1s)
- **Language filter**: `resolve(symbol, from_file, language)` filters entries by language
- Sources: `symbols.jsonl` (from Discover phase) + repo scan for Java/TS exports

### 5.3 DependencyGraphBuilder (`preflight/dependency_graph.py`)

- Builds dependency graph from architecture_facts relations + import index
- **Kahn's algorithm** for topological sort with tier tracking
- Returns generation order: files with no dependencies first (tier 0), then dependents
- Detects and handles circular dependencies

### 5.4 PreflightValidator (`preflight/validator.py`)

**Preflight Gate** — validates BEFORE LLM tokens are spent:
- Plan has `task_id` and `affected_components`?
- All affected files exist in the repository?
- Repository path exists and is accessible?
- ImportIndex has >0 symbols?
- At least one buildable container detected?

Any failure → abort with clear error message.

---

## 6. Post-Crew Processing

### 6.1 ImportFixer (`preflight/import_fixer.py`)

- Deterministic post-processor (0 LLM tokens)
- Scans all staged files for import issues
- Uses ImportIndex for missing/incorrect imports
- **Language-filtered**: TS files get TS imports, Java files get Java imports
- Handles: missing imports, wrong paths, duplicate imports, unused imports

### 6.2 Build Verification

- Post-crew deterministic build per container
- **Backup → Build → Restore** pattern (always restores, even on crash)
- Auto-detects containers from `architecture_facts.json`
- Error parsers: javac (`File.java:42: error:`) and tsc (`file.ts:42:10 - error TS2345:`)
- Configurable: `CODEGEN_BUILD_VERIFY` (on/off), `CODEGEN_BUILD_TIMEOUT`

### 6.3 Safety Gate

- `>50%` files failed → abort (no partial damage)
- Build verification failed → no commit
- Both conditions must pass for OutputWriter to proceed

---

## 7. Data Flow

```
                        Inputs
                          │
    ┌─────────────────────┼─────────────────────┐
    │                     │                     │
{task_id}_plan.json  architecture_facts.json  Target Repository
    │                     │                     │
    └─────────┬───────────┴─────────────────────┘
              │
              ▼
        PREFLIGHT
    CodegenPlanInput + ImportIndex + DependencyGraph + Validation
              │
              ▼
        CREW EXECUTION
    Manager delegates → Developer writes staging → Builder verifies → Tester tests
              │
              ▼
      staging: dict[str, GeneratedFile]
              │
              ▼
        POST-CREW
    ImportFixer → Build Verify → Safety Gate
              │
              ▼
       OUTPUT WRITER
    Git branch + file writes + commit + report JSON
              │
    ┌─────────┴──────────┐
    │                    │
codegen/{task_id}    {task_id}_report.json
 (git branch)        (knowledge/implement/)
```

---

## 8. Dual-Model Routing

```python
# In llm_factory.py

def create_llm() -> LLM:
    """LLM for analysis agents (Manager, Builder)."""
    model = os.getenv("MODEL")      # gpt-oss-120B
    api_base = os.getenv("API_BASE")
    ...

def create_codegen_llm() -> LLM:
    """LLM for code-writing agents (Developer, Tester)."""
    model = os.getenv("CODEGEN_MODEL") or os.getenv("MODEL")  # fallback
    api_base = os.getenv("CODEGEN_API_BASE") or os.getenv("API_BASE")
    api_key = os.getenv("CODEGEN_API_KEY") or os.getenv("OPENAI_API_KEY")
    ...
```

| Agent | Function | Model | Purpose |
|-------|----------|-------|---------|
| Manager | `create_llm()` | gpt-oss-120B | Understand tasks, coordinate, validate |
| Builder | `create_llm()` | gpt-oss-120B | Analyze build output, explain errors |
| Developer | `create_codegen_llm()` | Coder-14B | Write code, fix errors |
| Tester | `create_codegen_llm()` | Coder-14B | Write tests |

**Fallback**: If `CODEGEN_MODEL` is not set or unreachable, both functions fall back to `MODEL`.

---

## 9. Safety & Guardrails

### Tool Guardrails (`tool_guardrails.py`)

| Guardrail | Value | Purpose |
|-----------|-------|---------|
| `max_total` | 50 | Max tool calls per crew run |
| `max_identical` | 3 | Max identical calls (same tool + same args) |
| **Implementation** | CrewAI `step_callback` hooks | Blocks further calls when limits reached |

### Git Safety

| Feature | Implementation |
|---------|---------------|
| **Never push** | OutputWriter never calls `git push` |
| **Never touch main** | Branch names always start with `codegen/` |
| **Dirty tree check** | Abort if uncommitted changes exist |
| **Explicit staging** | Only `git add` specific files (never `-A`) |
| **Branch cleanup** | Always switches back to original branch after commit |

### Failure Handling

| Scenario | Behavior |
|----------|----------|
| Preflight validation fails | Abort with clear error, 0 LLM tokens spent |
| >50% files failed in crew | Safety gate blocks commit |
| Build verification fails | Safety gate blocks commit |
| LLM connection error | CrewAI retry with backoff |
| Agent in infinite loop | Tool guardrails kill after 50 calls |

---

## 10. Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL` | (required) | Analysis LLM model name |
| `API_BASE` | (required) | Analysis LLM API endpoint |
| `OPENAI_API_KEY` | (required) | Analysis LLM API key |
| `CODEGEN_MODEL` | `$MODEL` | Code generation LLM model name |
| `CODEGEN_API_BASE` | `$API_BASE` | Code generation LLM API endpoint |
| `CODEGEN_API_KEY` | `$OPENAI_API_KEY` | Code generation LLM API key |
| `CODEGEN_BUILD_VERIFY` | `true` | Enable/disable post-crew build verification |
| `CODEGEN_BUILD_TIMEOUT` | `600` | Build timeout in seconds |
| `PROJECT_PATH` | (required) | Target repository path |
| `TASK_INPUT_DIR` | `knowledge/plan/` | Directory with plan JSON files |

---

## 11. File Structure

```
hybrid/code_generation/
├── __init__.py                    # Exports ImplementCrew
├── crew.py                        # ImplementCrew (hierarchical crew orchestrator)
├── agents.py                      # 4 agents with dual-model routing (AGENT_CONFIGS)
├── tasks.py                       # 3 CrewAI tasks (implement, build, test)
├── schemas.py                     # Pydantic schemas (CodegenPlanInput, GeneratedFile, etc.)
├── output_writer.py               # Git branch + file writes + report (from stage5)
│
├── preflight/                     # Deterministic pre/post-crew modules
│   ├── __init__.py
│   ├── plan_reader.py             # Read plan JSON, resolve paths
│   ├── import_index.py            # ImportIndex + ImportIndexBuilder
│   ├── dependency_graph.py        # DependencyGraphBuilder (Kahn's algorithm)
│   ├── import_fixer.py            # Deterministic import correction
│   └── validator.py               # Preflight validation gate
│
└── tools/                         # CrewAI tool wrappers
    ├── __init__.py
    ├── code_reader_tool.py        # Read source files
    ├── code_writer_tool.py        # Write to staging dict
    ├── build_runner_tool.py       # Execute builds per container
    ├── build_error_parser_tool.py # Parse javac/tsc errors
    ├── test_pattern_tool.py       # Query test patterns
    ├── test_writer_tool.py        # Write test files
    ├── import_index_tool.py       # Language-filtered import lookup (NEW)
    ├── dependency_tool.py         # Dependency graph queries (NEW)
    └── plan_reader_tool.py        # Read plan JSON (NEW)
```

### What was removed (v0.5 → v0.6)

| Removed | Reason |
|---------|--------|
| `stages/` (all 8 stage files) | Replaced by preflight modules + crew agents |
| `strategies/` (4 strategy classes) | Task-type instructions embedded in task descriptions |
| `pipeline.py` | Replaced by `crew.py` (ImplementCrew) |
| `build_fixer_crew.py` | Integrated into main crew (Manager delegates heal to Developer) |
