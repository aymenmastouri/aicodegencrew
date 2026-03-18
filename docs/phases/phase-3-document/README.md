# Phase 3 — Document (Architecture Synthesis)

> **Status**: IMPLEMENTED | **Type**: Pipeline | **Layer**: Reasoning

---

## 1. Overview

| Attribute | Value |
|-----------|-------|
| Phase ID | `document` |
| Display Name | Architecture Synthesis |
| Type | Pipeline (template-first: deterministic skeleton + LLM enrichment + multi-level validation) |
| Entry Point | `pipelines/document/pipeline.py` → `DocumentPipeline` |
| Base Class | `shared/base_pipeline.py` → `BasePipeline` (ABC) |
| LLM Requirement | Yes (2 calls per chapter: generate + content review) |
| Output | `knowledge/document/` (c4/, arc42/, quality/) |
| Checkpoint | `knowledge/document/.checkpoint_pipeline.json` |
| Dependency | Extract + Analyze |
| Status | **IMPLEMENTED** |

> **Diagram:** [phase-3-document-architecture.drawio](phase-3-document-architecture.drawio)

The Document phase generates C4 diagrams and Arc42 documentation from architecture facts and analysis results. No agents, no tool loops — each chapter follows a deterministic pipeline:

```
DataCollector → PromptBuilder → LLMGenerator → ChapterValidator → DocumentReviewer → Write
```

## 2. Goals

- Generate 4 C4 diagram documents (Context, Container, Component, Deployment)
- Generate 12-chapter Arc42 documentation (with large chapters split and merged)
- Validate every chapter structurally (length, sections, banned phrases, fact grounding)
- Review every chapter for content quality (missing topics, unsupported claims, contradictions)
- All output evidence-based — no hallucinated containers, components, or relationships

## 3. Inputs & Outputs

| Direction | Artifact | Format | Path |
|-----------|----------|--------|------|
| **Input** | Architecture facts | JSON | `knowledge/extract/architecture_facts.json` |
| **Input** | Analyzed architecture | JSON | `knowledge/analyze/analyzed_architecture.json` |
| **Input** | ChromaDB index (optional) | Vector DB | `knowledge/discover/` |
| **Output** | C4 documents | Markdown | `knowledge/document/c4/` |
| **Output** | Arc42 documents | Markdown | `knowledge/document/arc42/` |
| **Output** | Quality report | Markdown | `knowledge/document/quality/pipeline-report.md` |

## 4. Architecture

### Pipeline Flow (per chapter)

| Step | Component | Description |
|------|-----------|-------------|
| 1. Collect | `DataCollector.collect(recipe)` | Gather facts, RAG results, components per recipe |
| 1b. Template | `TemplateBuilder.build_chapter_template()` | Deterministic markdown skeleton with fact tables + `<!-- LLM_ENRICH -->` placeholders |
| 2. Build | `PromptBuilder.build(data + recipe + template)` | Structured prompt with template context for enrichment |
| 3. Generate | `LLMGenerator.generate_text(messages)` | Single streaming LLM call with phase temperature 0.5 |
| 4a. Validate | `ChapterValidator.validate()` | 7 structural checks + template integrity (placeholders filled, fact tables preserved) |
| 4b. Retry | `retry_with_feedback_text(attempt=N)` | Max 2 retries with escalating severity + decreasing temperature |
| 4c. Review | `DocumentReviewer.review()` | Content review LLM call against source data |
| 4d. Rewrite | `retry_with_feedback_text()` | Rewrite if review score < 65 |
| 5. Write | `output_path.write_text()` | Write to disk + checkpoint |

### Content Review (New)

After structural validation passes, the `DocumentReviewer` runs a second LLM call that receives the generated chapter + the original source data. It checks:

- **Missing topics** — important data in the source that the chapter doesn't cover
- **Unsupported claims** — statements not backed by the source data
- **Contradictions** — statements that conflict with the architecture facts
- **Weak sections** — paragraphs with vague language instead of concrete evidence

The reviewer produces a `ReviewResult` with `quality_score` (0–100) and `rewrite_needed` flag. If `rewrite_needed=true` (score < 65), the chapter is rewritten with the reviewer's specific feedback. The review is **non-fatal** — if the review LLM call fails, the chapter proceeds normally.

### Chapter Recipes

Each chapter has a `ChapterRecipe` that defines exactly what data to collect and what to expect:

```python
ChapterRecipe(
    id="arc42-ch05-p1",
    title="Building Block Overview",
    output_file="arc42/05-part1-overview.md",
    facts=[("components", {}), ("containers", {})],
    rag_queries=["building block structure", "module organization"],
    components=["controller", "service", "repository"],
    sections=["## 5.1 Overview", "## 5.2 Level 1"],
    min_length=6000,
    max_length=30000,
    context_hint="Focus on layer decomposition...",
)
```

### C4 Documents (4 recipes)

| Recipe | Output |
|--------|--------|
| `c4-context` | `c4/c4-context.md` |
| `c4-container` | `c4/c4-container.md` |
| `c4-component` | `c4/c4-component.md` |
| `c4-deployment` | `c4/c4-deployment.md` |

### Arc42 Documents (18 recipes, 12 chapters)

Large chapters are split into parts and merged post-generation:

| Chapter | Parts | Output |
|---------|-------|--------|
| 1 — Introduction | 1 | `01-introduction.md` |
| 2 — Constraints | 1 | `02-constraints.md` |
| 3 — Context | 1 | `03-context.md` |
| 4 — Solution Strategy | 1 | `04-solution-strategy.md` |
| 5 — Building Blocks | 5 (split) | `05-building-blocks.md` (merged) |
| 6 — Runtime View | 2 (split) | `06-runtime-view.md` (merged) |
| 7 — Deployment | 1 | `07-deployment.md` |
| 8 — Crosscutting | 3 (split) | `08-crosscutting.md` (merged) |
| 9 — Decisions | 1 | `09-decisions.md` |
| 10 — Quality | 1 | `10-quality.md` |
| 11 — Risks | 1 | `11-risks.md` |
| 12 — Glossary | 1 | `12-glossary.md` |

### Modules

| Module | File | Responsibility |
|--------|------|----------------|
| **DocumentPipeline** | `pipeline.py` | Orchestrates all chapters, checkpoint/resume, merge, quality report |
| **DataCollector** | `data_collector.py` | Gathers facts, RAG results, components per recipe |
| **DataRecipes** | `data_recipes.py` | 22 chapter recipes (4 C4 + 18 Arc42) with per-chapter data requirements |
| **PromptBuilder** | `prompt_builder.py` | XML-tagged structured prompts with Chain-of-Thought instructions |
| **ChapterValidator** | `validator.py` | 7 structural validation checks |
| **TemplateBuilder** | `template_builder.py` | Deterministic markdown skeletons with fact tables and LLM enrichment placeholders |
| **FactGrounder** | `shared/utils/fact_grounding.py` | Shared fact-grounding validation against known architecture components |
| **DocumentReviewer** | `reviewer.py` | Content review LLM call against source data |
| **LLMGenerator** | `shared/llm_generator.py` | Single streaming LLM call + retry with feedback |

## 5. Patterns & Decisions

| Decision | Rationale |
|----------|-----------|
| No agents or tool loops | Deterministic data collection + single LLM call = 0% agent loops, 2× faster |
| Per-chapter data recipes | Each chapter gets exactly the data it needs — no over-fetching, no context overflow |
| Two-phase quality: validate then review | Structural validation catches format issues cheaply; content review catches semantic issues |
| Non-fatal review | Review failure doesn't block chapter generation — partial output is better than none |
| Split + merge for large chapters | Chapters 5, 6, 8 split into 2–5 parts to stay within output limits |
| Checkpoint/resume | Skip completed chapters on retry — saves tokens on partial failures |
| XML-tagged prompts | `<architecture_facts>`, `<code_evidence>`, `<component_inventory>` for clear data separation |

## 6. Dependencies

- **Upstream**: Phase 1 (Extract) — `architecture_facts.json`; Phase 2 (Analyze) — `analyzed_architecture.json`
- **Downstream**: Phase 4 (Review) — validates consistency; Phase 5 (Plan) — documentation context (optional)

## 7. Quality Gates & Validation

### Structural Validation (ChapterValidator — 7 checks)

| Check | What it validates |
|-------|-------------------|
| `not_empty` | Content exists |
| `length` | Within `min_length` / `max_length` bounds per recipe |
| `heading` | Starts with `#` heading |
| `sections` | All required section numbers present |
| `banned_phrases` | No "placeholder", "TODO:", "TBD", "as an AI", etc. |
| `fact_grounding` | References ≥3 real names from architecture data (case-insensitive) |
| `code_fence` | Not wrapped in ``` fences |
| `template_integrity` | LLM_ENRICH placeholders filled, fact tables from template preserved |

### Content Review (DocumentReviewer)

| Check | What it identifies |
|-------|-------------------|
| Missing topics | Source data present but chapter ignores |
| Unsupported claims | Chapter statements not backed by source data |
| Contradictions | Statements conflicting with architecture facts |
| Weak sections | Vague language instead of concrete evidence |

### Flow

```
Template → Generate → Structural Validate + Template Integrity → Retry (max 2×, escalating) → Content Review → Rewrite (if score < 65) → Write → quality_score
```

## 8. Configuration

LLM settings via environment variables, all centralized in `shared/llm_generator.py`:

| Variable | Default | Purpose |
|----------|---------|---------|
| `MODEL` | `openai/code` | LLM model identifier |
| `API_BASE` | — | LiteLLM API base URL |
| `MAX_LLM_OUTPUT_TOKENS` | `65536` | Max output tokens per call |
| `LLM_TEMPERATURE_DOCUMENT` | `0.5` | Phase-specific temperature (lower = more consistent documentation) |
| `LLM_TEMPERATURE_RETRY` | `0.3` | Retry temperature (decreases further per attempt for focused fixes) |
| `LLM_TOP_P` | `0.95` | Nucleus sampling |
| `LLM_TOP_K` | `40` | Top-k sampling |
| `LLM_CHUNK_TIMEOUT` | `60` | Seconds between stream chunks |

## 9. Risks & Open Points

- Content review adds ~30-50% more LLM tokens per chapter — acceptable for quality improvement
- Very large repositories may hit context limits in the review prompt (source data truncated to 8K chars)
- RAG query quality depends on Discover phase embedding model consistency

---

© 2026 Aymen Mastouri. All rights reserved.
