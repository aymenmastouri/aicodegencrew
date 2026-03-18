# Phase 2 — Analyze (Architecture Analysis)

> **Status**: IMPLEMENTED | **Type**: Pipeline | **Layer**: Reasoning

---

## 1. Overview

| Attribute | Value |
|-----------|-------|
| Phase ID | `analyze` |
| Display Name | Architecture Analysis |
| Type | Pipeline (16 parallel LLM calls + synthesis) |
| Entry Point | `pipelines/analysis/pipeline.py` → `AnalysisPipeline` |
| LLM Requirement | Yes (19 calls max: 16 sections + 1 review + N redo + 1 synthesis) |
| Output | `knowledge/analyze/analyzed_architecture.json` |
| Checkpoint | `knowledge/analyze/.checkpoint_analysis.json` |
| Dependency | Discover + Extract |
| Status | **IMPLEMENTED** |

> **Diagrams:** [phase-2-analyze-architecture.drawio](phase-2-analyze-architecture.drawio) · [analysis-crew-schema.drawio](analysis-crew-schema.drawio)

The Analyze phase uses `AnalysisPipeline(BasePipeline)` to run **16 parallel LLM calls** (one per analysis section) via `ThreadPoolExecutor(max_workers=8)`, followed by a **review LLM call** that cross-checks all sections for gaps, contradictions, and weak analysis. Sections flagged by the reviewer are **selectively re-generated** with specific feedback. Finally, a **synthesis call** merges all section files into `analyzed_architecture.json`. Checkpoint/resume: completed sections are persisted in `.checkpoint_analysis.json`.

## 2. Goals

- Analyze architecture patterns, styles, and quality attributes
- Identify business capabilities, domain contexts, and workflows
- Assess technical debt, security posture, and operational readiness
- Synthesize individual analyses into a unified output

## 3. Inputs & Outputs

| Direction | Artifact | Format | Path |
|-----------|----------|--------|------|
| **Input** | Architecture facts | JSON | `knowledge/extract/architecture_facts.json` |
| **Input** | ChromaDB index | Vector DB | `knowledge/discover/` |
| **Output** | Analyzed architecture | JSON | `knowledge/analyze/analyzed_architecture.json` |
| **Output** | Review report | JSON | `knowledge/analyze/analysis/_review_report.json` |
| **Output** | Checkpoint | JSON | `knowledge/analyze/.checkpoint_analysis.json` |

## 4. Architecture

### Pipeline Architecture

| Step | Mechanism | Output |
|------|-----------|--------|
| Section calls (×16) | `ThreadPoolExecutor(max_workers=8)` — `SectionPromptBuilder.build({"section_id": id})` | `analysis/01_*.json` … `16_*.json` |
| Review call (×1) | `AnalysisReviewer.review(section_outputs)` — cross-checks all 16 sections | `analysis/_review_report.json` |
| Selective redo (×0–N) | `retry_with_feedback()` for sections flagged by reviewer | Updated section `.json` files |
| Synthesis call (×1) | `SynthesisPromptBuilder.build({"sections": {filename: content}})` | `analyzed_architecture.json` |

### Review Call (New)

After all 16 sections complete, the `AnalysisReviewer` runs a single LLM call that receives all section outputs plus a source data summary. It identifies:

- **Gaps** — topics present in the source data but missing from the analysis
- **Contradictions** — conflicting statements between sections (e.g., section 01 says "Monolith" but section 04 implies microservices coupling patterns)
- **Weak sections** — vague reasoning without evidence from the facts
- **Number inconsistencies** — component counts or relation counts that differ between sections

The reviewer produces a `ReviewResult` with a `quality_score` (0–100) and a `sections_to_redo` mapping. Flagged sections are re-generated using `retry_with_feedback()` with the reviewer's specific issues injected into the prompt. This ensures the synthesis call receives consistent, well-grounded input.

The review is **non-fatal** — if the review LLM call fails, the pipeline continues normally.

**Section IDs and topics:**

| ID | Topic | ID | Topic |
|----|-------|----|-------|
| 01 | Macro architecture | 09 | Workflow engines |
| 02 | Backend pattern | 10 | Saga patterns |
| 03 | Frontend pattern | 11 | Runtime scenarios |
| 04 | Architecture quality | 12 | API design |
| 05 | Domain model | 13 | Complexity |
| 06 | Business capabilities | 14 | Technical debt |
| 07 | Bounded contexts | 15 | Security |
| 08 | State machines | 16 | Operational readiness |

Both `SectionPromptBuilder` and `SynthesisPromptBuilder` implement `BasePromptBuilder.build(data: dict) -> list[dict]` (real `@abstractmethod` — no workarounds).

### LLM Generator

All LLM calls go through `shared/llm_generator.py` → `LLMGenerator(phase_id="analyze")`:
- `generate(messages)` — raw LLM response with phase-specific temperature (default: 0.5)
- `retry_with_feedback(messages, output, issues, attempt=N)` — adaptive retry with escalating severity and decreasing temperature
- Temperature, `top_p`, `top_k`, `max_tokens`, timeout centralized; per-phase temperature via `LLM_TEMPERATURE_ANALYZE` env var

### Data Collector

`DataCollector` (in `pipelines/analysis/data_collector.py`) loads `architecture_facts.json` and optional ChromaDB once, then serves per-section data via `collect_section_data(section_id)`.

### JSON Repair

All 16 section outputs are parsed with `_extract_and_repair_json()` which:
1. Strips markdown fences
2. Tries direct `json.loads()`
3. Reconstructs unclosed structures (handles truncated LLM output)

## 5. Patterns & Decisions

| Decision | Rationale |
|----------|-----------|
| 16 parallel LLM calls | Each section independent → full parallelism via ThreadPoolExecutor |
| Review call before synthesis | Cross-checks sections for gaps, contradictions, and number inconsistencies before merging |
| Selective redo, not full re-run | Only re-generates sections flagged by reviewer — saves tokens and time |
| Non-fatal review | Review failure doesn't block the pipeline — synthesis proceeds with original sections |
| Checkpoint/resume | Completed section IDs in `.checkpoint_analysis.json`; only failed sections re-run |
| `BasePromptBuilder` ABC | Uniform `build(data: dict)` contract — no workarounds |
| JSON repair | LLMs truncate; stack-based bracket closer recovers partial JSON |
| Single `LLMGenerator` | All LLM config centralized in `shared/llm_generator.py` |

## 6. Dependencies

- **Upstream**: Phase 0 (Discover) — ChromaDB for RAG queries; Phase 1 (Extract) — `architecture_facts.json`
- **Downstream**: Phase 3 (Document) — `analyzed_architecture.json` as input; Phase 4 (Plan) — architecture context

## 7. Quality Gates & Validation

| Gate | Mechanism | When |
|------|-----------|------|
| JSON parse + repair | `_extract_and_repair_json()` — stack-based bracket closer for truncated output | After each section call |
| Cross-section review | `AnalysisReviewer` — LLM reviews all 16 sections for gaps, contradictions, inconsistencies | After all sections complete |
| Selective redo | `retry_with_feedback()` — re-generates flagged sections with reviewer issues | After review |
| Synthesis validation | Required top-level keys check (`system`, `macro_architecture`, `overall_grade`, etc.) | After synthesis |
| Review report | `_review_report.json` — persisted for transparency and debugging | After review |

## 8. Configuration

LLM settings via environment variables, all centralized in `shared/llm_generator.py`:

| Variable | Default | Purpose |
|----------|---------|---------|
| `MODEL` | `openai/code` | LLM model identifier |
| `LLM_TEMPERATURE_ANALYZE` | `0.5` | Phase-specific temperature (lower = more deterministic analysis) |
| `MAX_LLM_OUTPUT_TOKENS` | `65536` | Max output tokens per call |

The pipeline returns `quality_score` in its output dict (from the review report's `quality_score` field), enabling orchestrator-level Quality Gate checks.

## 9. Risks & Open Points

- LLM quality impacts analysis depth — on-prem models may produce shallower insights than cloud models
- Context window overflow still possible with very large components (>500 per container)
- RAG query quality depends on Discover phase embedding model consistency

---

© 2026 Aymen Mastouri. All rights reserved.
