# Phase 3 — Document (Architecture Synthesis)

> **Status**: IMPLEMENTED | **Type**: Crew | **Layer**: Reasoning

---

## 1. Overview

| Attribute | Value |
|-----------|-------|
| Phase ID | `document` |
| Display Name | Architecture Synthesis |
| Type | Pipeline (LLM generation + quality validation) |
| Entry Point | `pipelines/document/pipeline.py` → `DocumentPipeline` |
| Base Class | `shared/base_pipeline.py` → `BasePipeline` (ABC) |
| LLM Requirement | Yes |
| Output | `knowledge/document/` (c4/, arc42/, quality/) |
| Dependency | Extract + Analyze |
| Status | **IMPLEMENTED** |

> **Diagram:** [phase-3-document-architecture.drawio](phase-3-document-architecture.drawio)

The Document phase generates C4 architectural diagrams and Arc42 documentation from architecture facts and analysis. `DocumentPipeline(BasePipeline)` uses `LLMGenerator.generate_text()` for the main generation pass and `retry_with_feedback_text()` when the quality gate detects missing sections.

## 2. Goals

- Generate 4-level C4 diagrams (Context, Container, Component, Deployment) as editable DrawIO files
- Generate complete 12-chapter Arc42 documentation
- Produce quality gate reports for both C4 and Arc42
- All output evidence-based — no hallucinated containers, components, or relationships

## 3. Inputs & Outputs

| Direction | Artifact | Format | Path |
|-----------|----------|--------|------|
| **Input** | Architecture facts | JSON | `knowledge/extract/architecture_facts.json` |
| **Input** | Analyzed architecture | JSON | `knowledge/analyze/analyzed_architecture.json` |
| **Input** | ChromaDB index (optional) | Vector DB | `knowledge/discover/` |
| **Output** | C4 diagrams | Markdown + DrawIO | `knowledge/document/c4/` |
| **Output** | Arc42 docs | Markdown | `knowledge/document/arc42/` |
| **Output** | Quality reports | Markdown | `knowledge/document/quality/` |

## 4. Architecture

### Why Mini-Crews?

CrewAI accumulates conversation history across sequential tasks. With 26+ tasks, the prompt exceeds the context window (~120K tokens) after ~10–15 tasks. Mini-Crews solve this: each gets a fresh agent with fresh context, passing data via template variables.

### Orchestration

```
ArchitectureSynthesisCrew.run():
  C4Crew.run()     → 5 mini-crews (9 tasks)
  Arc42Crew.run()  → 18 mini-crews (18 tasks, 1 per crew)
```

Both inherit from `MiniCrewBase` which provides shared infrastructure.

### C4Crew: 5 Mini-Crews

| Mini-Crew | Tasks | Output |
|-----------|-------|--------|
| `context` | doc + diagram | `c4/c4-context.md` + `.drawio` |
| `container` | doc + diagram | `c4/c4-container.md` + `.drawio` |
| `component` | doc + diagram | `c4/c4-component.md` + `.drawio` |
| `deployment` | doc + diagram | `c4/c4-deployment.md` + `.drawio` |
| `quality` | validation | `quality/c4-report.md` |

### Arc42Crew: 18 Mini-Crews

Chapters 1–12, with large chapters (5, 6, 8) split into sub-crews then merged:

| Chapter | Mini-Crews | Output |
|---------|-----------|--------|
| 1 — Introduction | 1 | `01-introduction.md` |
| 2 — Constraints | 1 | `02-constraints.md` |
| 3 — Context | 1 | `03-context.md` |
| 4 — Solution Strategy | 1 | `04-solution-strategy.md` |
| 5 — Building Blocks | 4 (split) | `05-building-blocks.md` (merged) |
| 6 — Runtime View | 2 (split) | `06-runtime-view.md` (merged) |
| 7 — Deployment | 1 | `07-deployment.md` |
| 8 — Crosscutting | 2 (split) | `08-crosscutting.md` (merged) |
| 9 — Decisions | 1 | `09-decisions.md` |
| 10 — Quality | 1 | `10-quality.md` |
| 11 — Risks | 1 | `11-risks.md` |
| 12 — Glossary | 1 | `12-glossary.md` |

### MiniCrewBase Infrastructure

| Feature | Description |
|---------|-------------|
| `_create_llm()` | LLM factory from env vars |
| `_create_agent()` | Agent with MCP + tools |
| `_run_mini_crew()` | Execute crew with fresh context |
| `_save_checkpoint()` | Persist progress for resume |
| `_extract_token_usage()` | Track token consumption |
| Retry with backoff | On `ConnectionError`/`TimeoutError`/`OSError` |
| Output recovery | Generates stub docs from facts on crew failure |

### Tools

| Tool | Purpose |
|------|---------|
| `DocWriterTool` | Write markdown (with path-stripping) |
| `DrawioDiagramTool` | Create DrawIO diagrams (XML) |
| `FactsQueryTool` | Query architecture facts by category |
| `StereotypeListTool` | List components by stereotype |
| `ChunkedWriterTool` | Write large documents in sections |
| `RAGQueryTool` | ChromaDB semantic search |
| MCP Tools | `get_statistics()`, `get_architecture_summary()`, etc. |

## 5. Patterns & Decisions

| Decision | Rationale |
|----------|-----------|
| Mini-Crews | Prevents context overflow (120K limit) |
| `TOOL_INSTRUCTION` prefix | Forces agents to use tools instead of writing in response text |
| Few-shot examples | Per-task tool-use sequences (WRONG/RIGHT patterns) |
| Output token limit = 16K | Enables 12–20 page chapters vs 6–8 |
| Checkpoint/resume | Skip completed mini-crews on retry |

### Rules (MUST FOLLOW)

| DO | DO NOT |
|-------|-----------|
| Use ONLY data from facts.json | Invent containers or components |
| Query MCP tools for real data | Add business context not in facts |
| Use `doc_writer` tool for output | Write content in response text |
| Use DrawIO for diagrams (XML) | Use Mermaid, PlantUML, or ASCII |

## 6. Dependencies

- **Upstream**: Phase 1 (Extract) — `architecture_facts.json`; Phase 2 (Analyze) — `analyzed_architecture.json`
- **Downstream**: Phase 4 (Plan) — documentation context (optional)

## 7. Quality Gates & Validation

- `PhaseOutputValidator` checks required outputs between phases
- Output-gate: `RuntimeError` if expected files missing
- Tool guardrails: max 25 tool calls per task, max 3 identical calls
- Quality mini-crew validates C4 and Arc42 output

## 8. Configuration

LLM settings via environment variables. Tool-call budgets and LLM optimization as Python constants:

| Setting | Value | Purpose |
|---------|-------|---------|
| Input token limit | 100K | Process more facts |
| Output token limit | 16K | Longer chapters |
| Context window | 120K | Full conversation |
| Tool-call budget | 25 | More data gathering |
| Identical-call limit | 3 | Allow necessary re-queries |

## 9. Risks & Open Points

- Agent compliance: agents may write in response text instead of using tools (~85% compliance after few-shot)
- Large repositories need chapter splitting (ch05, ch06, ch08) to stay within output limits
- MCP server must be running for token-efficient fact access

---

© 2026 Aymen Mastouri. All rights reserved.
