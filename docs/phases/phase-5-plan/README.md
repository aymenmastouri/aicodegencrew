# Phase 5 — Plan (Development Planning)

> **Status**: IMPLEMENTED | **Type**: Pipeline | **Layer**: Reasoning

---

## 1. Overview

| Attribute | Value |
|-----------|-------|
| Phase ID | `plan` |
| Display Name | Development Planning |
| Type | Pipeline (5 stages: 4 deterministic + 1 LLM call) |
| Entry Point | `pipelines/plan/pipeline.py` → `PlanPipeline` |
| LLM Requirement | Yes (Stage 4 only — 1 call per task) |
| Output | `knowledge/plan/{task_id}_plan.json` |
| Dependency | Discover + Extract + Analyze |
| Status | **IMPLEMENTED** |

> **Diagrams:** [phase-5-plan-architecture.drawio](phase-5-plan-architecture.drawio) · [upgrade-rules-engine.drawio](upgrade-rules-engine.drawio)

**Why Hybrid?** Development planning is 80% pattern matching and 20% creative synthesis. Multi-agent workflows use LLMs for everything — including deterministic tasks like name matching — which is slow (5–7 min), expensive (5 LLM calls), and unreliable (70–80% success). The hybrid approach uses algorithms for what they do best and the LLM only for synthesis. **Result: 10–20x faster, 95%+ success rate.**

## 2. Goals

- Parse task descriptions from JIRA XML, DOCX, Excel, or plain text
- Discover affected components using multi-signal scoring
- Match test, security, validation, and error-handling patterns
- Generate evidence-based implementation plans via a single LLM call
- Support upgrade tasks with framework-specific rules engine

## 3. Inputs & Outputs

| Direction | Artifact | Format | Path |
|-----------|----------|--------|------|
| **Input** | Task files | XML/DOCX/XLSX/TXT | `inputs/tasks/` |
| **Input** | Supplementary context | Various | `inputs/requirements/`, `inputs/logs/`, `inputs/reference/` |
| **Input** | Architecture facts | JSON | `knowledge/extract/architecture_facts.json` (all 17 keys) |
| **Input** | Analyzed architecture | JSON | `knowledge/analyze/analyzed_architecture.json` |
| **Input** | ChromaDB index | Vector DB | `knowledge/discover/` |
| **Input** | Symbol index | JSONL | `knowledge/discover/symbols.jsonl` |
| **Output** | Implementation plan | JSON | `knowledge/plan/{task_id}_plan.json` |

## 4. Architecture

### 5-Stage Pipeline

```
Stage 1: Input Parser      (Deterministic, <1s)
  └─ Parse XML/DOCX/Excel/Text → TaskInput JSON
  └─ Detect task_type (upgrade/bugfix/feature/refactoring)

Stage 2: Component Discovery (RAG + Scoring, 2-5s)
  └─ 5-signal scoring: semantic 30%, name 25%, symbol 20%, package 15%, stereotype 10%
  └─ Upgrades: return ALL components in affected container

Stage 3: Pattern Matcher    (TF-IDF + Rules, 1-3s)
  └─ Test patterns (TF-IDF on 925 tests)
  └─ Security/Validation/Error (rule-based)
  └─ Upgrades: UpgradeRulesEngine scan + assess

Stage 4: Plan Generator     (LLM, 15-30s) ← ONLY LLM CALL
  └─ Synthesize all context → implementation plan

Stage 5: Validator          (Pydantic, <1s)
  └─ Schema validation, completeness checks

Total: 18-40 seconds
```

### Performance

| Metric | CrewAI (Multi-Agent) | Hybrid Pipeline | Improvement |
|--------|---------------------|-----------------|-------------|
| Duration | 5–7 min | 18–40 sec | **10–20x faster** |
| LLM Calls | 5 | 1 | **5x fewer** |
| Success Rate | 70–80% | 95%+ | **+15–25%** |
| Data Utilization | 20% | 100% (all 17 keys) | **5x more** |

### Multi-File Processing

| Mode | Input | Behavior |
|------|-------|----------|
| Single file | 1 file in `inputs/tasks/` | Stages 1→5 sequentially |
| Multi-file | N files in `inputs/tasks/` | Parse all → Sort → Process each |

Tasks sorted by `(is_child, priority, task_type, task_id)` — parents before children, blockers before trivial, upgrades before features.

### Component Discovery (5-Signal Scoring)

| Signal | Weight | Method |
|--------|--------|--------|
| Semantic | 30% | ChromaDB vector similarity |
| Name | 25% | Fuzzy string match |
| Symbol | 20% | Deterministic symbol index match |
| Package | 15% | Label-based filtering |
| Stereotype | 10% | Keyword detection |

Falls back to 4-signal (40/30/20/10) when `symbols.jsonl` missing.

### Upgrade Rules Engine

Framework-agnostic rules engine for upgrade task planning. Gated behind `task_type == "upgrade"`.

**Architecture**: `upgrade_rules/` — Rule Types, Scanner, Engine, per-framework Rules.

**Framework Rules (40 total):**

| Framework | Rules | Key Changes |
|-----------|-------|-------------|
| Angular | 17 | Standalone default, control flow, Karma→Vitest, Sass compiler |
| Spring | 12 | Jakarta migration, SecurityFilterChain, RestClient |
| Java | 5 | SecurityManager removed, finalize deprecated |
| Playwright | 6 | Locator API, waitForURL, ElementHandle |

Severities: `BREAKING` · `DEPRECATED` · `RECOMMENDED` · `OPTIONAL`

### Input Parsers

| Parser | File | Capabilities |
|--------|------|-------------|
| XML | `xml_parser.py` | JIRA RSS (all comments, links, metadata), generic XML |
| DOCX | `docx_parser.py` | Title, sections, tables |
| Excel | `excel_parser.py` | All sheets, header detection |
| Text | `text_parser.py` | Plain text, log files, error patterns |

## 5. Patterns & Decisions

| Decision | Rationale |
|----------|-----------|
| Hybrid (4 deterministic + 1 LLM) | 10–20x faster than full CrewAI |
| TF-IDF for test matching | Deterministic, reproducible, works on 925 tests |
| Score-based task type detection | Avoids hardcoded keyword matching |
| Multi-file sort by composite key | Deterministic order, parents before children |

## 6. Dependencies

- **Upstream**: Phase 0 (Discover) — ChromaDB + symbols.jsonl; Phase 1 (Extract) — all 17 keys; Phase 2 (Analyze) — architecture context
- **Downstream**: Phase 5 (Implement) — `{task_id}_plan.json`

## 7. Quality Gates & Validation

- Stage 5: Pydantic schema validation + completeness checks
- Upgrade plans: migration_sequence, verification_commands, effort estimates validated
- Layer compliance checks
- Failed tasks don't block others — pipeline returns `status: "partial"`

## 8. Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `TASK_INPUT_DIR` | `inputs/tasks/` | Directory with task files |
| `REQUIREMENTS_DIR` | `inputs/requirements/` | Supplementary specs |
| `LOGS_DIR` | `inputs/logs/` | Error logs |
| `REFERENCE_DIR` | `inputs/reference/` | Reference materials |

Task file parsers require: `pip install -e ".[parsers]"` for DOCX/Excel support.

## 9. Risks & Open Points

- LLM plan quality depends on context completeness — all 17 fact dimensions needed
- Upgrade rules are declarative — new framework versions need rule updates
- Multi-file processing: child detection relies on JIRA links and regex cross-references

---

© 2026 Aymen Mastouri. All rights reserved.
