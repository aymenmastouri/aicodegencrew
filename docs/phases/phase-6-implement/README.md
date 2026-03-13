# Phase 6 — Implement (Code Generation)

> **Status**: IMPLEMENTED | **Type**: Hierarchical CrewAI | **Layer**: Execution

---

## 1. Overview

| Attribute | Value |
|-----------|-------|
| Phase ID | `implement` |
| Display Name | Code Generation |
| Type | Hierarchical CrewAI (4 Agents, Dual-Model Routing) |
| Entry Point | `hybrid/code_generation/crew.py` → `ImplementCrew` |
| LLM Requirement | Yes (Developer + Tester: Coder-14B, Manager + Builder: 120B) |
| Output | Git branch + `knowledge/implement/{task_id}_report.json` |
| Dependency | Plan |
| Status | **IMPLEMENTED** |

> **Diagrams:** [phase-6-implement-architecture.drawio](phase-6-implement-architecture.drawio) · [code-generation-pipeline.drawio](code-generation-pipeline.drawio) · [task-type-strategy.drawio](task-type-strategy.drawio)

**Why CrewAI?** The previous pipeline approach (1 LLM call per file) was too rigid — no cross-file reasoning, no iterative improvement, no self-healing with architectural context. The new approach treats the LLM as a *developer with tools*, not a code template engine.

## 2. Goals

- Generate code changes that compile and follow existing patterns
- Self-heal build errors via Manager → Developer heal loop (max 3x)
- Generate unit tests matching repository conventions
- Deterministic pre/post-processing to reduce LLM token waste
- Task-type-specific behavior via Strategy pattern (no hardcoded if/else)

## 3. Inputs & Outputs

| Direction | Artifact | Format | Path |
|-----------|----------|--------|------|
| **Input** | Implementation plan | JSON | `knowledge/plan/{task_id}_plan.json` |
| **Input** | Architecture facts | JSON | `knowledge/extract/architecture_facts.json` |
| **Input** | Target repository | File system | `PROJECT_PATH` |
| **Input** | ChromaDB index | Vector DB | `knowledge/discover/` |
| **Output** | Code changes | Git branch | `codegen/{task_id}` or `codegen/batch-{timestamp}` |
| **Output** | Generation report | JSON | `knowledge/implement/{task_id}_report.json` |

## 4. Architecture

### 4-Phase Flow

```
PREFLIGHT (Deterministic, 0 LLM tokens, 5-15s)
  PlanReader → ImportIndexBuilder → DependencyGraphBuilder → PreflightValidator
  │
  │ GATE: fail → abort before LLM tokens burn
  ▼
STRATEGY: pre_execute() (Deterministic, task-type-specific)
  Upgrade: schematics, config changes, version bumps
  Default: no-op
  │
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
STRATEGY: enrich_verification() (Deterministic, task-type-specific)
  All: error clustering
  Upgrade: deprecation warnings, migration completeness
  │
  ▼
OUTPUT WRITER (Git + File I/O)
  Branch creation → File writes → Git commit → Report JSON
```

### Agent Architecture

| Agent | LLM | Role | Tools | Delegation |
|-------|-----|------|-------|------------|
| **Manager** | MODEL (120B) | Technical Project Lead | PlanReader, CodeReader, ImportIndex, DependencyLookup, FactsQuery, RAGQuery, MCP | `True` |
| **Developer** | CODEGEN_MODEL (Coder-14B) | Senior Full-Stack Dev | CodeReader, CodeWriter, ImportIndex, DependencyLookup, FactsQuery, RAGQuery, MCP | `False` |
| **Builder** | MODEL (120B) | DevOps & Build Engineer | BuildRunner, BuildErrorParser, FactsQuery | `False` |
| **Tester** | CODEGEN_MODEL (Coder-14B) | Senior Test Engineer | TestPattern, TestWriter, CodeReader, RAGQuery, MCP | `False` |

### Dual-Model Routing

```
create_llm()         → MODEL (gpt-oss-120B)       → Manager, Builder
create_codegen_llm() → CODEGEN_MODEL (Coder-14B)  → Developer, Tester

Fallback: If CODEGEN_MODEL unavailable → falls back to MODEL
```

**Why dual-model?** Coder-14B writes better code at fewer tokens. 120B better at understanding complex tasks and analyzing build output.

### Preflight Modules

All deterministic, 0 LLM tokens, run BEFORE the crew:

| Module | Purpose |
|--------|---------|
| `PlanReader` | Read plan JSON, resolve file paths from facts |
| `ImportIndexBuilder` | Scan repo → 2266 symbols, 1984 files (language-filtered) |
| `DependencyGraphBuilder` | Topological sort (Kahn's algorithm) → tier-based generation order |
| `PreflightValidator` | Plan valid? Files exist? Build system? Index >0 symbols? |

### Post-Crew Processing

| Module | Purpose |
|--------|---------|
| `ImportFixer` | Deterministic import correction (language-filtered, TS↔Java separation) |
| Build Verification | Compile per container (backup → build → restore pattern) |
| Safety Gate | >50% files failed → no commit; build failed → no commit |

### Task-Type Strategy Pattern

The Strategy pattern injects task-specific behavior at 3 pipeline hooks without `if task_type == "upgrade"` in core code.

```python
class TaskTypeStrategy(ABC):
    def enrich_plan(self, plan_data, facts) -> PlanEnrichment: ...
    def pre_execute(self, plan, staging, repo_path, dry_run) -> PreExecutionResult: ...
    def enrich_verification(self, build_result, staging, plan, ...) -> VerificationEnrichment: ...
```

| Hook | Phase | Purpose |
|------|-------|---------|
| `enrich_plan()` | Planning (Stage 3) | Validate feasibility, add compatibility checks |
| `pre_execute()` | Implement (before Crew) | Deterministic steps before LLM |
| `enrich_verification()` | Implement (after Build) | Rich reporting: error clusters, deprecations |

**Registered Strategies:**

| Task Type | Strategy | Behavior |
|-----------|----------|----------|
| `upgrade` | `UpgradeStrategy` | Schematics, dependency compat, migration tracking |
| `feature`/`bugfix` | `DefaultStrategy` | No-op for hooks 1 & 2, error clustering for hook 3 |

Strategies auto-register via `@register_strategy("upgrade")` decorator. Unknown types fall back to `DefaultStrategy`.

### UpgradeStrategy Details

- **`enrich_plan()`**: Validates `required_dependencies` against repo versions (semver)
- **`pre_execute()`**: Runs whitelisted schematics (`ng`, `npx`, `npm`, `openrewrite`), applies config changes, bumps versions
- **`enrich_verification()`**: Error clustering + deprecation parsing + migration completeness

### Tools

| Tool | Used By | Description |
|------|---------|-------------|
| `CodeReaderTool` | Developer, Tester, Manager | Read source files (max 12K chars) |
| `CodeWriterTool` | Developer | Write code to staging dict |
| `BuildRunnerTool` | Builder | Execute builds per container |
| `BuildErrorParserTool` | Builder | Parse javac/tsc errors |
| `TestPatternTool` | Tester | Query test patterns from facts |
| `TestWriterTool` | Tester | Write test files with validation |
| `ImportIndexTool` | Developer, Manager | Language-filtered import lookup |
| `DependencyLookupTool` | Developer, Manager | Dependency graph queries |
| `PlanReaderTool` | Manager | Read plan JSON |
| `FactsQueryTool` | All | Query architecture facts |
| `RAGQueryTool` | Developer, Tester, Manager | Semantic search in ChromaDB |

## 5. Patterns & Decisions

| Decision | Rationale |
|----------|-----------|
| Hierarchical crew | Manager coordinates — workers execute single tasks |
| Dual-model routing | Code-writing LLM (14B) vs analysis LLM (120B) |
| Preflight gate | Validates before spending LLM tokens |
| Language-filtered imports | Prevents Java/TypeScript cross-contamination |
| Strategy pattern | Task-type behavior without if/else in core pipeline |
| Staging dict | All writes in memory until commit — enables rollback |

## 6. Dependencies

- **Upstream**: Phase 4 (Plan) — `{task_id}_plan.json`; Phase 1 (Extract) — facts for file resolution; Phase 0 (Discover) — ChromaDB + symbols
- **Downstream**: Phase 6 (Verify) — code changes to test; Phase 7 (Deliver) — branch for PR

## 7. Quality Gates & Validation

| Gate | Description |
|------|-------------|
| Preflight | Plan, files, build system validated before LLM |
| Dirty tree check | Aborts if uncommitted changes exist |
| Tool guardrails | Max 50 total calls, max 3 identical |
| Safety gate | >50% failure → no commit |
| Build verification | Post-crew compile per container |
| Import fixer | Deterministic correction after crew |

## 8. Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL` | (required) | Analysis LLM (Manager, Builder) |
| `CODEGEN_MODEL` | `$MODEL` | Code generation LLM (Developer, Tester) |
| `CODEGEN_API_BASE` | `$API_BASE` | Code gen LLM endpoint |
| `CODEGEN_API_KEY` | `$OPENAI_API_KEY` | Code gen LLM key |
| `CODEGEN_BUILD_VERIFY` | `true` | Enable post-crew build verification |
| `CODEGEN_BUILD_TIMEOUT` | `600` | Build timeout (seconds) |
| `PROJECT_PATH` | (required) | Target repository path |
| `TASK_INPUT_DIR` | `knowledge/plan/` | Directory with plan JSON files |

## 9. File Structure

```
hybrid/code_generation/
├── crew.py              # ImplementCrew (hierarchical crew orchestrator)
├── agents.py            # 4 agents with dual-model routing
├── tasks.py             # 3 CrewAI tasks (implement, build, test)
├── schemas.py           # Pydantic schemas (10+ models)
├── output_writer.py     # Git branch + file writes + report
├── strategies/          # Task-type strategy pattern
│   ├── __init__.py      # Registry exports + auto-register
│   ├── base.py          # ABC + DefaultStrategy + registry
│   └── upgrade_strategy.py
├── preflight/           # Deterministic pre/post-crew modules
│   ├── plan_reader.py
│   ├── import_index.py
│   ├── dependency_graph.py
│   ├── import_fixer.py
│   └── validator.py
└── tools/               # 11 CrewAI tool wrappers
```

## 10. Risks & Open Points

- **Build verification**: Gradle builds may fail if build tools are unavailable. Solution: `CODEGEN_BUILD_VERIFY=false` or `-x test` in Gradle command.
- **LLM connection stability**: Network interruptions cause connection errors → >50% failure → safety gate rejects
- **Self-healing**: Works (proven on Angular build), but depends on LLM understanding error messages
- **CrewAI + on-prem LLM**: Don't use `output_pydantic` — parse raw text with `_repair_truncated_json` instead

---

© 2026 Aymen Mastouri. All rights reserved.
