# Implement Phase Architecture: CrewAI Redesign

> **Status**: Concept — pending approval before code implementation
> **Author**: Aymen Mastouri
> **Date**: 2026-02-14
> **Version**: 0.6.0 (planned)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Agents](#3-agents)
4. [Tools](#4-tools)
5. [Knowledge Sources](#5-knowledge-sources)
6. [Mini-Crew Pattern](#6-mini-crew-pattern)
7. [Data Flow](#7-data-flow)
8. [Schema Extensions](#8-schema-extensions)
9. [Comparison: Current vs Proposed](#9-comparison-current-vs-proposed)
10. [Environment Variables](#10-environment-variables)
11. [Implementation Roadmap](#11-implementation-roadmap)

---

## 1. Overview

### Why Redesign?

The current implement phase uses a **pure pipeline** with direct OpenAI API calls. While functional, it has fundamental limitations:

| Limitation | Impact |
|------------|--------|
| 1 LLM call per file | No cross-file reasoning, no iterative improvement |
| Rigid retry loop | Stage 4b heal is a simple "fix errors" prompt — no architectural context |
| No test generation | Tests are not part of the code generation pipeline |
| No agent memory | Each file is generated in isolation — no learning from prior files |
| Monolithic Stage 3 | Code generation, build fixing, and test writing are conflated |

### Proposed Solution

Replace the monolithic Stage 3 + Stage 4b with a **CrewAI crew of 3 specialized agents**, while keeping the deterministic pre/post-processing stages unchanged.

**Key benefits:**
- **Separation of concerns** — each agent owns one responsibility
- **Iterative self-healing** — DevOps agent builds, Senior Dev fixes, in a loop with context
- **Test generation** — dedicated Tester agent creates tests matching existing patterns
- **Cross-file awareness** — agents share context through CrewAI's task chaining
- **Reusable tools** — `FactsQueryTool` and `RAGQueryTool` already proven in the analyze crew

---

## 2. Architecture

### Pipeline Shell (Unchanged)

The outer pipeline remains a linear sequence of deterministic stages:

```
Stage 1          Stage 2           Stage 3 (NEW)        Stage 4          Stage 5
Plan Reader  →  Context       →   CREW               →  Code         →  Output
                Collector         (3 Agents)            Validator        Writer
```

**What stays the same:**
- Stage 1: Reads and validates the development plan JSON
- Stage 2: Collects source code + sibling files for targeted components
- Stage 4: Syntax, security, and pattern validation (deterministic)
- Stage 5: Git branch creation, file writes, commit, report generation

**What changes:**
- Stage 3: Replaced by a CrewAI crew with 3 agents and 8 tools
- Stage 4b: **Absorbed** into the crew (DevOps agent + BuildRunnerTool)

### New Stage 3: Implement Crew

```
┌──────────────────────────────────────────────────────────────────┐
│  Stage 3: Implement Crew                                         │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────┐        │
│  │ Senior Dev  │  │   Tester    │  │  DevOps Engineer │        │
│  │             │  │             │  │                  │        │
│  │ • Generate  │  │ • Find test │  │ • Run builds     │        │
│  │   code      │  │   patterns  │  │ • Parse errors   │        │
│  │ • Fix build │  │ • Write     │  │ • Verify CI      │        │
│  │   errors    │  │   tests     │  │   readiness      │        │
│  └──────┬──────┘  └──────┬──────┘  └────────┬─────────┘        │
│         │                │                   │                   │
│  ┌──────┴────────────────┴───────────────────┴──────────┐       │
│  │  Tools: CodeReader, CodeWriter, BuildRunner,         │       │
│  │  BuildErrorParser, TestPattern, TestWriter,          │       │
│  │  FactsQuery, RAGQuery                                │       │
│  └──────────────────────────────────────────────────────┘       │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Agents

All agents follow the proven pattern from the architecture analysis crew:
- Python-only configuration (no YAML)
- Fresh LLM instance per agent
- `allow_delegation=False` (agents don't hand off to each other)
- `max_iter=25`, `max_retry_limit=3`
- MCP server connection for extended tool access

### 3.1 Senior Developer

```python
{
    "role": "Senior Software Developer",
    "goal": (
        "Generate high-quality code changes for the given development task. "
        "Write code that compiles, follows existing patterns, and integrates "
        "with the target codebase architecture. Fix any build errors reported "
        "by the DevOps Engineer."
    ),
    "backstory": (
        "You are a senior full-stack developer with deep expertise in Spring Boot "
        "and Angular. You always read existing code before writing new code. You "
        "match the style, naming conventions, and patterns of the target codebase. "
        "You never invent imports or APIs — you verify them via FactsQuery and "
        "RAGQuery first. When fixing build errors, you make minimal surgical changes."
    ),
}
```

**Tools**: `CodeReaderTool`, `CodeWriterTool`, `FactsQueryTool`, `RAGQueryTool`

**Responsibilities:**
- Generate code changes file-by-file using the development plan
- Use `RAGQueryTool` to find similar implementations in the codebase
- Use `FactsQueryTool` to verify component APIs, interfaces, and relations
- Fix compilation errors reported by the DevOps agent (self-healing loop)

### 3.2 Tester

```python
{
    "role": "Senior Test Engineer",
    "goal": (
        "Create comprehensive tests for all code changes. Match the existing "
        "test patterns and frameworks used in the target repository. Ensure "
        "every public method and API endpoint has test coverage."
    ),
    "backstory": (
        "You are a test automation expert who writes tests that actually catch bugs. "
        "You always analyze existing test files first to match the exact testing "
        "framework, assertion style, mock patterns, and directory conventions. "
        "For Spring Boot you use JUnit 5 + Mockito. For Angular you use Jasmine + "
        "TestBed. You never write tests without first checking TestPatternTool for "
        "the repository's established patterns."
    ),
}
```

**Tools**: `TestPatternTool`, `TestWriterTool`, `CodeReaderTool`, `RAGQueryTool`

**Responsibilities:**
- Query existing test patterns via `TestPatternTool` (925 test files in target repo)
- Generate unit tests matching the repository's exact testing conventions
- Write tests via `TestWriterTool` (validates test structure before writing)
- Ensure test file placement matches existing directory conventions

### 3.3 DevOps Engineer

```python
{
    "role": "DevOps & Build Engineer",
    "goal": (
        "Verify that all code changes compile and build successfully. Run the "
        "build for each affected container. Parse build errors and report them "
        "to the Senior Developer for fixing. Ensure CI readiness."
    ),
    "backstory": (
        "You are a build and CI/CD specialist. You know Gradle, Maven, npm, and "
        "Angular CLI build systems. You detect build tools from the repository "
        "structure. You run baseline builds first to distinguish pre-existing "
        "errors from new ones. You parse javac, TypeScript, and Angular compiler "
        "errors into structured reports. You never skip the baseline check."
    ),
}
```

**Tools**: `BuildRunnerTool`, `BuildErrorParserTool`, `FactsQueryTool`

**Responsibilities:**
- Run builds per container using auto-detected build commands
- Baseline builds to isolate pre-existing errors
- Parse compilation errors into structured error objects
- Report errors back to the Senior Developer with file paths and line numbers

---

## 4. Tools

### 4.1 CodeReaderTool

Reads source files from the target repository with context.

```python
class CodeReaderInput(BaseModel):
    file_path: str = Field(..., description="Absolute path to the source file")
    include_siblings: bool = Field(default=False, description="Also return nearby files")

class CodeReaderTool(BaseTool):
    name = "read_code"
    description = "Read source code from the target repository. Use before writing to understand existing patterns."
    # Returns: file content + optional sibling file contents
```

**Source**: Reuses logic from Stage 2 `ContextCollector` but as a CrewAI tool.

### 4.2 CodeWriterTool

Writes generated code to a staging area (not directly to disk).

```python
class CodeWriterInput(BaseModel):
    file_path: str = Field(..., description="Target file path in the repository")
    content: str = Field(..., description="Complete file content to write")
    action: Literal["modify", "create"] = Field(default="modify")

class CodeWriterTool(BaseTool):
    name = "write_code"
    description = "Write generated code to the staging area. Stage 5 handles actual disk writes."
    # Writes to in-memory staging dict, not to disk
    # Returns: confirmation with diff preview
```

**Key design**: Writes to an in-memory `dict[str, GeneratedFile]` staging area. Stage 5 handles the actual file writes, git branch, and commit. This prevents partial writes on failure.

### 4.3 BuildRunnerTool

Executes build commands per container (absorbs Stage 4b logic).

```python
class BuildRunnerInput(BaseModel):
    container_id: str = Field(..., description="Container to build (e.g. 'container.backend')")
    baseline: bool = Field(default=False, description="Run baseline build (before applying changes)")

class BuildRunnerTool(BaseTool):
    name = "run_build"
    description = "Run the build command for a container. Use baseline=True first to check pre-existing errors."
    # Auto-detects: gradle → .\gradlew.bat / ./gradlew
    #               maven  → .\mvnw.cmd / ./mvnw
    #               npm    → npm run build (from package.json)
    # Returns: exit_code, stdout, stderr, duration
```

**Absorbs**: All build execution logic from `stage4b_build_verifier.py` including:
- Windows/Unix build command derivation
- `shell=True` with `bytes.decode('utf-8', errors='replace')`
- ANSI escape code stripping
- Configurable timeout (`CODEGEN_BUILD_TIMEOUT`)

### 4.4 BuildErrorParserTool

Parses build output into structured error objects.

```python
class BuildErrorParserInput(BaseModel):
    build_output: str = Field(..., description="Raw build output (stdout + stderr)")
    container_type: str = Field(default="auto", description="'java', 'typescript', or 'auto'")

class BuildErrorParserTool(BaseTool):
    name = "parse_build_errors"
    description = "Parse build output into structured errors with file paths and line numbers."
    # Returns: list of {file, line, column, code, message}
```

**Absorbs**: Error parsing logic from Stage 4b including:
- `javac` pattern: `.+?\.java:\d+:\s*error:` (Windows-safe)
- `tsc` pattern: `[^\s:]+\.ts:\d+:\d+\s*-\s*error\s+TS\d+:`
- ANSI escape code stripping (`_strip_ansi()`)
- Error deduplication and grouping by file

### 4.5 TestPatternTool

Queries existing test patterns from architecture facts.

```python
class TestPatternInput(BaseModel):
    container: str = Field(default="", description="Filter by container (e.g. 'backend', 'frontend')")
    stereotype: str = Field(default="", description="Filter by component stereotype being tested")
    limit: int = Field(default=20)

class TestPatternTool(BaseTool):
    name = "find_test_patterns"
    description = "Find existing test files and patterns in the target repository to match their conventions."
    # Reads from architecture_facts.json "tests" dimension (925 test files)
    # Returns: test frameworks, assertion styles, directory structure, mock patterns
```

**Data source**: The `tests` dimension in `architecture_facts.json` contains 925 test file entries with framework, assertion style, and structural metadata.

### 4.6 TestWriterTool

Writes test files to the staging area with validation.

```python
class TestWriterInput(BaseModel):
    file_path: str = Field(..., description="Test file path (e.g. 'src/test/java/.../FooServiceTest.java')")
    content: str = Field(..., description="Complete test file content")
    tested_component: str = Field(..., description="Component being tested")

class TestWriterTool(BaseTool):
    name = "write_test"
    description = "Write a test file to the staging area. Validates test structure before accepting."
    # Validates: imports present, at least 1 test method, correct directory
    # Writes to staging dict alongside generated code files
```

### 4.7 FactsQueryTool (Reused)

**Reused from**: `src/aicodegencrew/crews/architecture_analysis/tools/facts_query_tool.py`

Queries architecture facts by category (components, relations, interfaces, containers, data_model) with filtering by stereotype, container, and text search. Supports pagination.

### 4.8 RAGQueryTool (Reused)

**Reused from**: `src/aicodegencrew/crews/architecture_analysis/tools/rag_query_tool.py`

Semantic search in the ChromaDB index. Finds relevant code snippets by natural language query. Essential for the Senior Developer to find similar implementations before writing code.

---

## 5. Knowledge Sources

The crew receives rich context from all prior SDLC phases:

### 5.1 Development Plan (from Plan phase)

```
knowledge/plan/{task_id}_plan.json
```

Contains:
- `task_id`, `task_type` (upgrade/feature/bugfix/refactoring)
- `summary`, `description`
- `affected_components[]` — component IDs with file paths, stereotypes, change types
- `implementation_steps[]` — ordered steps for the developer
- `upgrade_plan` — migration rules (for upgrade tasks only)
- `patterns` — test/security/validation patterns from Phase 4
- `test_strategy` — what tests to write, which frameworks

### 5.2 Collected Source Code (from Stage 2)

```python
CollectedContext(
    file_contexts=[
        FileContext(
            file_path="/abs/path/to/File.java",
            content="...current file content...",
            language="java",
            sibling_files=["../SiblingService.java", "../SiblingDTO.java"],
            related_patterns=["@Test with Mockito", "@PreAuthorize RBAC"],
            component=ComponentTarget(...)
        ),
        ...
    ]
)
```

Stage 2 reads actual files from disk and collects sibling files for pattern reference. This is passed directly to the crew as initial context.

### 5.3 Architecture Facts (from Extract phase)

```
knowledge/extract/architecture_facts.json (+ dimension files)
```

16 dimensions available via `FactsQueryTool`:

| Dimension | Description | Used By |
|-----------|------------|---------|
| `system` | System overview | All agents — overview |
| `containers` | Deployable units | DevOps — build targets |
| `components` | All components | Senior Dev — API verification |
| `interfaces` | REST endpoints | Senior Dev — REST endpoint design |
| `relations` | Dependencies | Senior Dev — dependency awareness |
| `data_model` | Entities & tables | Senior Dev — entity structure |
| `dependencies` | 170 | DevOps — library compatibility |
| `tech_versions` | 8 | DevOps — version awareness |
| `tests` | 925 | Tester — pattern matching |
| `security_details` | 143 | Senior Dev — security patterns |
| `validation` | 149 | Senior Dev — validation rules |
| `error_handling` | 23 | Senior Dev — error patterns |
| `workflows` | 42 | Senior Dev — business logic |
| `build_system` | 8 | DevOps — build configuration |
| `runtime` | 1 | DevOps — runtime config |
| `infrastructure` | 1 | DevOps — infra awareness |

### 5.4 ChromaDB RAG Index (from Discover phase)

```
knowledge/discover/ (ChromaDB persistent storage)
```

Semantic search via `RAGQueryTool`. The Senior Developer uses this to:
- Find similar implementations before writing code
- Verify import paths and API usage
- Discover patterns not captured in architecture facts

---

## 6. Mini-Crew Pattern

Following the proven pattern from the architecture analysis crew (5 mini-crews), the implement crew uses **3 mini-crews per container**, each with fresh LLM context.

### Why Mini-Crews?

- **Context freshness** — each mini-crew starts with a clean LLM context window
- **Isolation** — a failure in Mini-Crew B (build) doesn't corrupt Mini-Crew A's (code) output
- **Checkpoint/resume** — if the pipeline crashes, completed mini-crews don't need re-running
- **Parallelism** — Mini-Crew C (tests) can run in parallel with Mini-Crew B (build)

### Per-Container Execution

For each container (e.g., backend, frontend):

```
Mini-Crew A: Code Generation
├── Agent: Senior Developer
├── Task: Generate code for all affected files in this container
├── Tools: CodeReader, CodeWriter, FactsQuery, RAGQuery
├── Input: plan + collected context + facts
├── Output: staged files (in-memory dict)
└── Checkpoint: staged_files_{container_id}.json

        ↓ (staged files)

Mini-Crew B: Build & Heal (max 3 iterations)
├── Agents: DevOps Engineer + Senior Developer
├── Task 1 (DevOps): Run baseline build, then build with staged files
├── Task 2 (Senior Dev): Fix any compilation errors
├── Tools: BuildRunner, BuildErrorParser, CodeWriter, CodeReader
├── Input: staged files + build output
├── Output: healed staged files
├── Loop: build → parse errors → fix → rebuild (max 3x)
└── Checkpoint: healed_files_{container_id}.json

        ↓ (healed files)

Mini-Crew C: Test Generation
├── Agent: Tester
├── Task: Generate tests for all changed files in this container
├── Tools: TestPattern, TestWriter, CodeReader, RAGQuery
├── Input: healed files + test patterns from facts
├── Output: test files added to staging
└── Checkpoint: test_files_{container_id}.json
```

### Checkpoint/Resume

Each mini-crew saves its output to a checkpoint file. If the pipeline crashes:
- Completed mini-crews are skipped (checkpoint exists)
- The failed mini-crew is retried from scratch
- Env var `CODEGEN_CREW_RESUME=true` enables this behavior

### Container Ordering

Containers are processed sequentially (not in parallel) to:
- Prevent LLM rate limiting (one crew at a time)
- Allow backend changes to inform frontend changes
- Keep build isolation clean

---

## 7. Data Flow

### Complete Flow Diagram

```
                    ┌─────────────────┐
                    │  Plan Phase     │
                    │  (Phase 4)      │
                    └────────┬────────┘
                             │
                    {task_id}_plan.json
                             │
                    ┌────────▼────────┐
                    │  Stage 1        │
                    │  Plan Reader    │──── Validates plan, selects strategy
                    └────────┬────────┘
                             │
                    CodegenPlanInput
                             │
                    ┌────────▼────────┐
                    │  Stage 2        │     knowledge/extract/
                    │  Context        │◄─── architecture_facts.json
                    │  Collector      │◄─── knowledge/discover/ (ChromaDB)
                    └────────┬────────┘
                             │
                    CollectedContext
                             │
              ┌──────────────▼──────────────┐
              │  Stage 3: IMPLEMENT CREW     │
              │                              │
              │  For each container:         │
              │  ┌────────────────────────┐  │
              │  │ Mini-Crew A: Code Gen  │  │
              │  │ (Senior Developer)     │  │
              │  └───────────┬────────────┘  │
              │              │               │
              │  ┌───────────▼────────────┐  │
              │  │ Mini-Crew B: Build     │  │
              │  │ (DevOps + Senior Dev)  │  │
              │  │ (max 3 heal loops)     │  │
              │  └───────────┬────────────┘  │
              │              │               │
              │  ┌───────────▼────────────┐  │
              │  │ Mini-Crew C: Tests     │  │
              │  │ (Tester)              │  │
              │  └───────────┬────────────┘  │
              │              │               │
              └──────────────┼───────────────┘
                             │
                    list[GeneratedFile]  (code + tests)
                             │
                    ┌────────▼────────┐
                    │  Stage 4        │
                    │  Code Validator  │──── Syntax, security, pattern checks
                    └────────┬────────┘
                             │
                    ValidationResult
                             │
                    ┌────────▼────────┐
                    │  Stage 5        │
                    │  Output Writer  │──── Git branch, file writes, commit
                    └────────┬────────┘
                             │
                    CodegenReport
                             │
                    knowledge/implement/{task_id}_report.json
```

### Tool ↔ Agent Mapping

| Tool | Senior Dev | Tester | DevOps |
|------|:----------:|:------:|:------:|
| `CodeReaderTool` | x | x | |
| `CodeWriterTool` | x | | |
| `BuildRunnerTool` | | | x |
| `BuildErrorParserTool` | | | x |
| `TestPatternTool` | | x | |
| `TestWriterTool` | | x | |
| `FactsQueryTool` | x | | x |
| `RAGQueryTool` | x | x | |

---

## 8. Schema Extensions

### New Fields in CodegenReport

```python
class CodegenReport(BaseModel):
    # ... existing fields unchanged ...

    # NEW: Test generation results
    test_files_generated: int = 0
    test_files_failed: int = 0
    generated_tests: list[GeneratedFile] = Field(default_factory=list)

    # NEW: Per-agent metrics
    agent_metrics: dict[str, AgentMetrics] = Field(default_factory=dict)

class AgentMetrics(BaseModel):
    """Metrics for a single agent's execution."""
    agent_role: str
    tasks_completed: int = 0
    llm_calls: int = 0
    tokens_used: int = 0
    tools_invoked: int = 0
    duration_seconds: float = 0.0
    errors: list[str] = Field(default_factory=list)
```

### New Fields in ContainerBuildResult

```python
class ContainerBuildResult(BaseModel):
    # ... existing fields unchanged ...

    # NEW: Detailed error tracking
    errors_found: int = 0
    errors_fixed: int = 0
    error_details: list[BuildError] = Field(default_factory=list)

class BuildError(BaseModel):
    """A single build error with location."""
    file_path: str
    line: int = 0
    column: int = 0
    code: str = ""          # e.g. "TS2345" or "javac"
    message: str = ""
    fixed: bool = False
```

---

## 9. Comparison: Current vs Proposed

| Aspect | Current (v0.5.0) | Proposed (v0.6.0) |
|--------|-------------------|-------------------|
| **Architecture** | Pure pipeline (6 stages) | Pipeline shell + CrewAI crew (5 stages) |
| **Stage 3** | Direct OpenAI API, 1 call/file | CrewAI Senior Developer agent |
| **Stage 4b** | Separate build verifier stage | Absorbed into Mini-Crew B (DevOps agent) |
| **Self-healing** | Simple prompt: "fix these errors" | Contextual: agent reads code, facts, and error details |
| **Test generation** | Not supported | Mini-Crew C: dedicated Tester agent |
| **Cross-file reasoning** | None (each file isolated) | Agent has full task context + RAG search |
| **Tools** | None (raw API calls) | 8 specialized tools with guardrails |
| **Knowledge access** | Plan + source code only | Plan + source + facts (16 dim) + RAG |
| **Error parsing** | Regex in Stage 4b | `BuildErrorParserTool` (reusable, tested) |
| **Retry strategy** | Fixed 3x loop | Agent-driven: up to 3 iterations with context |
| **Token tracking** | Basic (total only) | Per-agent metrics |
| **Checkpoint/resume** | None | Per-mini-crew checkpoint files |
| **Configuration** | 5 env vars | 10 env vars (more granular control) |
| **Existing code reuse** | — | `FactsQueryTool`, `RAGQueryTool` from analyze crew |

### What Gets Deleted

- `stage4b_build_verifier.py` — logic moves into `BuildRunnerTool` + `BuildErrorParserTool`
- `stage3_code_generator.py` — replaced by `stage3_implement_crew.py`
- Strategy classes (`BaseStrategy`, `UpgradeStrategy`, etc.) — prompt logic moves into agent backstories + task descriptions

### What Stays Unchanged

- `stage1_plan_reader.py` — deterministic, fast, no LLM
- `stage2_context_collector.py` — deterministic, fast, no LLM; now uses symbol index for targeted content extraction (reads class/method body instead of truncating entire files)
- `stage4_code_validator.py` — deterministic validation
- `stage5_output_writer.py` — git operations, file writes, report generation
- `schemas.py` — extended, not replaced

---

## 10. Environment Variables

### Existing (Unchanged)

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `onprem` | LLM provider type |
| `MODEL` | `gpt-oss-120b` | Model name |
| `API_BASE` | (platform URL) | OpenAI-compatible API endpoint |
| `OPENAI_API_KEY` | `dummy-key` | API authentication |
| `PROJECT_PATH` | — | Target repository absolute path |

### New (Crew-Specific)

| Variable | Default | Description |
|----------|---------|-------------|
| `CODEGEN_CREW_ENABLED` | `true` | Use crew (true) or legacy pipeline (false) |
| `CODEGEN_CREW_RESUME` | `false` | Resume from checkpoint files |
| `CODEGEN_CREW_VERBOSE` | `true` | Verbose CrewAI logging |
| `CODEGEN_BUILD_VERIFY` | `true` | Enable build verification in Mini-Crew B |
| `CODEGEN_BUILD_MAX_RETRIES` | `3` | Max heal iterations in Mini-Crew B |
| `CODEGEN_BUILD_TIMEOUT` | `600` | Build timeout in seconds |
| `CODEGEN_TEST_ENABLED` | `true` | Enable test generation (Mini-Crew C) |
| `CODEGEN_MAX_RPM` | `30` | Max LLM requests per minute |
| `CODEGEN_CALL_DELAY` | `2` | Seconds between LLM calls |
| `MAX_LLM_OUTPUT_TOKENS` | `8000` | Max output tokens per LLM call |
| `LLM_CONTEXT_WINDOW` | `120000` | Context window size |

### Feature Flags

- `CODEGEN_CREW_ENABLED=false` — falls back to the legacy pipeline (Stage 3 + 4b)
- `CODEGEN_TEST_ENABLED=false` — skips Mini-Crew C (test generation)
- `CODEGEN_BUILD_VERIFY=false` — skips Mini-Crew B (build verification)

---

## 11. Implementation Roadmap

### Phase 1: Tool Layer (Foundation)

Create the 6 new tools that agents will use. Reuse 2 existing tools.

| # | File | Action | Description |
|---|------|--------|-------------|
| 1 | `src/aicodegencrew/crews/implement/tools/__init__.py` | CREATE | Tool exports |
| 2 | `src/aicodegencrew/crews/implement/tools/code_reader_tool.py` | CREATE | Read source files from target repo |
| 3 | `src/aicodegencrew/crews/implement/tools/code_writer_tool.py` | CREATE | Write to in-memory staging area |
| 4 | `src/aicodegencrew/crews/implement/tools/build_runner_tool.py` | CREATE | Run builds per container (from Stage 4b) |
| 5 | `src/aicodegencrew/crews/implement/tools/build_error_parser_tool.py` | CREATE | Parse javac/tsc errors (from Stage 4b) |
| 6 | `src/aicodegencrew/crews/implement/tools/test_pattern_tool.py` | CREATE | Query test patterns from facts |
| 7 | `src/aicodegencrew/crews/implement/tools/test_writer_tool.py` | CREATE | Write test files to staging |

**Reused (symlink or import)**:
- `FactsQueryTool` from `crews/architecture_analysis/tools/`
- `RAGQueryTool` from `crews/architecture_analysis/tools/`

**Dependency**: None — tools are standalone.

### Phase 2: Agent & Crew Definition

Define the 3 agents and the mini-crew orchestration.

| # | File | Action | Description |
|---|------|--------|-------------|
| 8 | `src/aicodegencrew/crews/implement/__init__.py` | CREATE | Package init |
| 9 | `src/aicodegencrew/crews/implement/crew.py` | CREATE | Crew class with 3 agents, 3 mini-crews, checkpoint logic |
| 10 | `src/aicodegencrew/crews/implement/agents.py` | CREATE | Agent configs (role, goal, backstory) |
| 11 | `src/aicodegencrew/crews/implement/tasks.py` | CREATE | Task descriptions + expected outputs |

**Dependency**: Phase 1 (tools must exist).

### Phase 3: Pipeline Integration

Wire the new crew into the existing pipeline, replacing Stage 3 + 4b.

| # | File | Action | Description |
|---|------|--------|-------------|
| 12 | `src/aicodegencrew/pipelines/code_generation/stages/stage3_implement_crew.py` | CREATE | New Stage 3 that invokes the crew |
| 13 | `src/aicodegencrew/pipelines/code_generation/pipeline.py` | MODIFY | Swap Stage 3 + 4b for new Stage 3 (feature-flagged) |
| 14 | `src/aicodegencrew/pipelines/code_generation/schemas.py` | MODIFY | Add test fields + agent metrics |

**Dependency**: Phase 2 (crew must exist).

### Phase 4: Legacy Preservation & Testing

Keep the old pipeline working behind a feature flag and add tests.

| # | File | Action | Description |
|---|------|--------|-------------|
| 15 | `src/aicodegencrew/pipelines/code_generation/stages/stage3_code_generator.py` | KEEP | Preserved as legacy fallback |
| 16 | `src/aicodegencrew/pipelines/code_generation/stages/stage4b_build_verifier.py` | KEEP | Preserved as legacy fallback |
| 17 | `tests/test_implement_crew.py` | CREATE | Unit tests for crew + tools |
| 18 | `tests/test_build_runner_tool.py` | CREATE | Unit tests for build tool (Windows + Unix) |

**Dependency**: Phase 3 (integration must work).

### Phase 5: Dashboard Integration

Update the UI to show crew-specific metrics.

| # | File | Action | Description |
|---|------|--------|-------------|
| 19 | `ui/backend/routers/reports.py` | MODIFY | Expose agent_metrics + test results |
| 20 | `ui/frontend/src/app/pages/reports/` | MODIFY | Display per-agent metrics, test file list |

**Dependency**: Phase 4 (crew must be tested).

### Execution Order

```
Phase 1: Tools          [~4 hours]  → 7 files created
Phase 2: Agents/Crew    [~3 hours]  → 4 files created
Phase 3: Integration    [~2 hours]  → 1 created, 2 modified
Phase 4: Tests          [~2 hours]  → 2 files created, 2 preserved
Phase 5: Dashboard      [~1 hour]   → 2 files modified
                        ──────────
Total:                  ~12 hours    18 file changes
```

### Migration Path

1. **v0.6.0-alpha**: Crew behind `CODEGEN_CREW_ENABLED=false` (off by default)
2. **v0.6.0-beta**: Crew enabled by default, legacy still available
3. **v0.7.0**: Legacy code removed after validation on 3+ target repos

---

## Appendix: File Tree (New)

```
src/aicodegencrew/
├── crews/
│   ├── architecture_analysis/    # Existing (Phase 2)
│   │   ├── crew.py
│   │   └── tools/
│   │       ├── facts_query_tool.py      ← REUSED
│   │       ├── rag_query_tool.py        ← REUSED
│   │       ├── facts_statistics_tool.py
│   │       ├── stereotype_list_tool.py
│   │       └── partial_results_tool.py
│   │
│   └── implement/                # NEW (Phase 5)
│       ├── __init__.py
│       ├── crew.py               # Mini-crew orchestration
│       ├── agents.py             # 3 agent definitions
│       ├── tasks.py              # Task descriptions
│       └── tools/
│           ├── __init__.py
│           ├── code_reader_tool.py
│           ├── code_writer_tool.py
│           ├── build_runner_tool.py
│           ├── build_error_parser_tool.py
│           ├── test_pattern_tool.py
│           └── test_writer_tool.py
│
├── pipelines/
│   └── code_generation/
│       ├── pipeline.py           # MODIFIED (feature flag)
│       ├── schemas.py            # MODIFIED (new fields)
│       └── stages/
│           ├── stage1_plan_reader.py       # UNCHANGED
│           ├── stage2_context_collector.py # UNCHANGED
│           ├── stage3_code_generator.py    # KEPT (legacy fallback)
│           ├── stage3_implement_crew.py    # NEW (crew wrapper)
│           ├── stage4_code_validator.py    # UNCHANGED
│           ├── stage4b_build_verifier.py   # KEPT (legacy fallback)
│           └── stage5_output_writer.py     # UNCHANGED
```
