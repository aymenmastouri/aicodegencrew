# Phase 2 — Analyze (Architecture Analysis)

> **Status**: IMPLEMENTED | **Type**: Crew | **Layer**: Reasoning

---

## 1. Overview

| Attribute | Value |
|-----------|-------|
| Phase ID | `analyze` |
| Display Name | Architecture Analysis |
| Type | Crew (AI Agents) — Mini-Crews Pattern |
| Entry Point | `crews/architecture_analysis/crew.py` → `ArchitectureAnalysisCrew` |
| LLM Requirement | Yes |
| Output | `knowledge/analyze/analyzed_architecture.json` |
| Checkpoint | `.checkpoint_analysis.json` |
| Dependency | Discover + Extract |
| Status | **IMPLEMENTED** |

> **Diagrams:** [phase-2-analyze-architecture.drawio](phase-2-analyze-architecture.drawio) · [analysis-crew-schema.drawio](analysis-crew-schema.drawio)

The Analyze phase uses **5 mini-crews** with **4 specialized agent types** to produce a unified architecture analysis. Each mini-crew gets a fresh agent with a fresh LLM context window — preventing context overflow.

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

### Mini-Crew Architecture

| Mini-Crew | Agent | Tasks | Output Files |
|-----------|-------|-------|-------------|
| `tech_analysis` | Technical Architect | 4: macro, backend, frontend, quality | `01-04_*.json` |
| `domain_analysis` | Functional Analyst | 4: domain, capabilities, contexts, states | `05-08_*.json` |
| `workflow_analysis` | Functional Analyst | 4: workflows, sagas, runtime, api | `09-12_*.json` |
| `quality_analysis` | Quality Analyst | 4: complexity, debt, security, ops | `13-16_*.json` |
| `synthesis` | Synthesis Lead | 1: merge all 16 results | `analyzed_architecture.json` |

### Agent Specialization

| Agent | Focus | Uses Facts For | Uses RAG For |
|-------|-------|---------------|--------------|
| **Technical Architect** | Technical structure | `architecture_style`, `design_pattern` | Implementation patterns |
| **Functional Analyst** | Business domain | `entity`, `service` | Business logic, Javadoc |
| **Quality Analyst** | Quality attributes | All stereotypes | Error handling, logging, tests |
| **Synthesis Lead** | Integration | All outputs | Conflict resolution |

### Deep Analysis Mode

| Aspect | Standard | Deep Analysis (Current) |
|--------|----------|------------------------|
| Tool calls per agent | 5–15 | 15–25 |
| Runtime | 2–5 min | 30–40 min |
| Input token limit | 32K | 100K |
| Output token limit | 4K | 16K |
| Context window | 32K | 120K |

**Token management strategies**: chunked queries (500 items per batch), truncation (80–100 chars), temp output files, natural forgetting of old tool results.

### Scaling: MapReduce Pattern

For large repositories (≥300 components across ≥2 containers), analysis automatically switches to MapReduce:

```
Map Phase (parallel):
  Container A Analyst → container_a_analysis.json
  Container B Analyst → container_b_analysis.json
  Container C Analyst → container_c_analysis.json

Reduce Phase:
  Synthesis Agent → merge + deduplicate → analyzed_architecture.json
```

Benefits: smaller context per agent (~200–400 components), parallel execution (3x+ speedup), failure isolation.

## 5. Patterns & Decisions

| Decision | Rationale |
|----------|-----------|
| Mini-Crews | Fresh context per crew prevents overflow (120K limit) |
| 4 agent types | Specialization improves accuracy vs single generalist |
| MapReduce for large repos | Scales to 100K+ components |
| Checkpoint/resume | Completed mini-crews saved; on retry, only failed crews re-run |
| Python constants (no YAML) | Agent configs as code for easier debugging |

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
