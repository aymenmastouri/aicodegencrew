# Phase 2 — Analyze (Architecture Analysis)

> **Status**: IMPLEMENTED | **Type**: Crew | **Layer**: Reasoning

---

## 1. Overview

| Attribute | Value |
|-----------|-------|
| Phase ID | `analyze` |
| Display Name | Architecture Analysis |
| Type | Pipeline (16 parallel LLM calls + synthesis) |
| Entry Point | `pipelines/analysis/pipeline.py` → `AnalysisPipeline` |
| LLM Requirement | Yes (17 calls: 16 sections parallel + 1 synthesis) |
| Output | `knowledge/analyze/analyzed_architecture.json` |
| Checkpoint | `knowledge/analyze/.checkpoint_analysis.json` |
| Dependency | Discover + Extract |
| Status | **IMPLEMENTED** |

> **Diagrams:** [phase-2-analyze-architecture.drawio](phase-2-analyze-architecture.drawio) · [analysis-crew-schema.drawio](analysis-crew-schema.drawio)

The Analyze phase uses `AnalysisPipeline(BasePipeline)` to run **16 parallel LLM calls** (one per analysis section) via `ThreadPoolExecutor(max_workers=8)`, followed by a **synthesis call** that merges all 16 section files into `analyzed_architecture.json`. Checkpoint/resume: completed sections are persisted in `.checkpoint_analysis.json`.

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
| **Output** | Checkpoint | JSON | `knowledge/analyze/.checkpoint_analysis.json` |

## 4. Architecture

### Pipeline Architecture

| Phase | Mechanism | Output |
|-------|-----------|--------|
| Section calls (×16) | `ThreadPoolExecutor(max_workers=8)` — `SectionPromptBuilder.build({"section_id": id})` | `analysis/01_*.json` … `16_*.json` |
| Synthesis call (×1) | `SynthesisPromptBuilder.build({"sections": {filename: content}})` | `analyzed_architecture.json` |

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

All LLM calls go through `shared/llm_generator.py` → `LLMGenerator`:
- `generate(messages)` — raw LLM response
- Temperature, `top_p`, `top_k`, `max_tokens`, timeout all configured in one place via env vars

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
| Checkpoint/resume | Completed section IDs in `.checkpoint_analysis.json`; only failed sections re-run |
| `BasePromptBuilder` ABC | Uniform `build(data: dict)` contract — no workarounds |
| JSON repair | LLMs truncate; stack-based bracket closer recovers partial JSON |
| Single `LLMGenerator` | All LLM config centralized in `shared/llm_generator.py` |

## 6. Dependencies

- **Upstream**: Phase 0 (Discover) — ChromaDB for RAG queries; Phase 1 (Extract) — `architecture_facts.json`
- **Downstream**: Phase 3 (Document) — `analyzed_architecture.json` as input; Phase 4 (Plan) — architecture context

## 7. Quality Gates & Validation

- Pydantic output validation per crew task — invalid output triggers retry with error feedback
- Output-gate validation: raises `RuntimeError` if files missing after crew completes
- Evidence-first: every claim must be backed by tool query results

## 8. Configuration

Configuration via Python constants in `crew.py`:

```python
AGENT_CONFIGS = {
    "tech_architect": {"role": "Senior Technical Architect", ...},
    "func_analyst":   {"role": "Senior Functional Analyst", ...},
    "quality_analyst": {"role": "Senior Quality Architect", ...},
    "synthesis_lead":  {"role": "Lead Architect - Synthesis", ...},
}
```

LLM settings via environment variables (`MODEL`, `API_BASE`, `LLM_PROVIDER`).

## 9. Risks & Open Points

- LLM quality impacts analysis depth — on-prem models may produce shallower insights than cloud models
- Context window overflow still possible with very large components (>500 per container)
- RAG query quality depends on Discover phase embedding model consistency

---

© 2026 Aymen Mastouri. All rights reserved.
