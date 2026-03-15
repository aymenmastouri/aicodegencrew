# Phase 4 — Triage (Issue Triage)

> **Status**: IMPLEMENTED | **Type**: Pipeline | **Layer**: Reasoning

---

## 1. Overview

| Attribute | Value |
|-----------|-------|
| Phase ID | `triage` |
| Phase Number | 4 |
| Display Name | Issue Triage |
| Type | Pipeline (deterministic scan + LLM synthesis + validate→retry) |
| LLM Requirement | Yes — single LLM call for synthesis (optional: deterministic mode available) |
| Entry Point | `pipelines/triage/pipeline.py` → `TriagePipeline` |
| Output | `knowledge/triage/` |
| Status | **IMPLEMENTED** |

The Triage phase takes an issue (bug report, feature request, task) and produces a complete analysis: classification, affected components, blast radius, risk assessment, test coverage gaps, and dual-audience summaries (customer + developer).

## 2. Goals

- Classify issues automatically (bug, feature, refactor, investigation)
- Find entry-point components via multi-signal matching against architecture facts
- Calculate blast radius through BFS traversal of the dependency graph
- Detect duplicate/similar issues via ChromaDB semantic search
- Assess risk (security, error handling, quality debt)
- Generate customer-facing summary + developer action brief via LLM

## 3. Inputs & Outputs

| Direction | Artifact | Format | Path |
|-----------|----------|--------|------|
| **Input** | Issue title + description | Text / Task file | CLI or API |
| **Input** | Discover artifacts | ChromaDB + symbols + evidence | `knowledge/discover/{slug}/` |
| **Input** | Architecture facts | JSON | `knowledge/extract/architecture_facts.json` |
| **Input** | Analysis (optional) | JSON | `knowledge/analyze/analyzed_architecture.json` |
| **Input** | Supplementary files (optional) | Text | Logs, requirements, reference docs |
| **Output** | Deterministic findings | JSON | `knowledge/triage/{issue_id}_findings.json` |
| **Output** | Customer summary | Markdown | `knowledge/triage/{issue_id}_customer.md` |
| **Output** | Developer brief | Markdown | `knowledge/triage/{issue_id}_developer.md` |
| **Output** | Full triage result | JSON | `knowledge/triage/{issue_id}_triage.json` |
| **Output** | Run summary | JSON | `knowledge/triage/summary.json` |

## 4. Architecture

### The Pattern: Deterministic Scan + LLM Synthesis

Follows the same pattern as Phase 7 (Review): run deterministic analysis first, then let a single LLM agent synthesize a human-readable narrative from structured findings.

```
Phase 1 (deterministic, <5s):
  classify_issue() → entry_point_finder() → blast_radius() →
  find_duplicates() → test_coverage() → risk_assessment()
      ↓
  findings.json (structured data)
      ↓
Phase 2 (LLM, ~30s):
  Single CrewAI agent: FactsQueryTool + RAGQueryTool + SymbolQueryTool
      ↓
  customer_summary.md + developer_brief.md
```

### Deterministic Modules

| Module | File | Purpose |
|--------|------|---------|
| **Classifier** | `classifier.py` | Rule-based issue type detection (bug/feature/refactor/investigation) |
| **Entry Point Finder** | `entry_point_finder.py` | Multi-signal component matching (name, path, symbol, keyword) |
| **Blast Radius** | `blast_radius.py` | BFS on relation graph from entry points — finds all transitively affected components |
| **Duplicate Detector** | `duplicate_detector.py` | ChromaDB semantic search for similar issues/code |
| **Test Coverage** | `test_coverage.py` | Checks test patterns for affected components |
| **Risk Assessor** | `risk_assessor.py` | Security, error handling, quality debt scoring |
| **Context Builder** | `context_builder.py` | Loads all available phase outputs as triage context |

### LLM Synthesis

`LLMGenerator.generate()` called once with the structured findings as context.

**Validate→retry quality loop** (same pattern as Plan):
1. Parse LLM output → score quality via `_score_triage_quality()`
2. If `score < TRIAGE_QUALITY_THRESHOLD` (default: 50) and warnings exist → `retry_with_feedback()` with the warnings
3. Accept retry only if `quality2.score >= quality.score` (never regress)
4. Env var `TRIAGE_QUALITY_THRESHOLD` controls the threshold

Produces dual output:
- **Customer summary**: Impact level, ETA category, plain-language summary, workaround
- **Developer brief**: Root cause hypothesis, affected files/components, action steps, test strategy

### Quick Mode

`triage_quick(title, description)` runs deterministic analysis only (no LLM). Completes in <2 seconds. Useful for bulk triage or when LLM is unavailable.

## 5. File Structure

```
pipelines/triage/
├── pipeline.py           # TriagePipeline(BasePipeline) — orchestrates both phases
├── schemas.py            # TriageRequest input model
├── classifier.py         # Issue type classification
├── entry_point_finder.py # Multi-signal component matching
├── blast_radius.py       # BFS dependency traversal
├── duplicate_detector.py # ChromaDB similarity search
├── test_coverage.py      # Test pattern checker
├── risk_assessor.py      # Risk scoring
└── context_builder.py    # KnowledgeLoader for all phase outputs
```

## 6. Dependencies

- **Upstream**: Extract (architecture_facts), Discover (ChromaDB, symbols)
- **Optional upstream**: Analyze (analyzed_architecture), Document (arc42, c4)
- **Downstream**: Plan (can use triage findings for planning context)

## 7. Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL` | (from .env) | LLM for synthesis (via shared `LLMGenerator`) |
| `TRIAGE_QUALITY_THRESHOLD` | `50` | Minimum quality score before retry (0–100) |
| `CHROMA_DIR` | Auto-resolved | ChromaDB path (multi-project aware) |

## 8. Execution Modes

| Mode | LLM | Duration | Use Case |
|------|-----|----------|----------|
| **Full** (`run()`) | Yes | ~30s | Complete triage with narrative output |
| **Quick** (`triage_quick()`) | No | <2s | Bulk triage, CI integration, no LLM available |
| **Orchestrator** (`kickoff()`) | Yes | ~30s | Part of SDLC pipeline |

---

 2026 Aymen Mastouri. All rights reserved.
