# AI Architecture Patterns Reference -- SDLC Pilot (aicodegencrew)

**Author:** Aymen Mastouri
**Project:** SDLC Pilot -- AI-powered SDLC automation platform (9 phases)
**Last updated:** 2026-04-06

> **Key architecture decision (March 2026):** CrewAI was removed and replaced
> by the Pipeline+LLM pattern. CrewAI caused 30% agent loops and 3x token
> overhead. The new architecture uses deterministic Python pipelines with
> targeted `litellm.completion()` calls. This change reduced token cost by
> ~65%, eliminated non-deterministic agent loops, and made every LLM call
> auditable.

---

## Table of Contents

1. [LLM Integration](#1-llm-integration)
2. [RAG Architecture](#2-rag-architecture)
3. [From Multi-Agent to Pipeline+LLM](#3-from-multi-agent-to-pipelinellm)
4. [Prompt Engineering](#4-prompt-engineering)
5. [Hallucination and Fact Grounding](#5-hallucination-and-fact-grounding)
6. [Quality Gates](#6-quality-gates)
7. [Adaptive Retry](#7-adaptive-retry)
8. [LLM Observability](#8-llm-observability)
9. [Hybrid Architecture Matrix](#9-hybrid-architecture-matrix)
10. [Tech Stack](#10-tech-stack)

---

## 1. LLM Integration

All LLM calls in the platform go through a single class: `LLMGenerator`
(`src/aicodegencrew/shared/llm_generator.py`). There are no agents, no tool
loops, no autonomous iterations. One completion call per invocation.

### LLMGenerator Pattern

```python
from aicodegencrew.shared import LLMGenerator

generator = LLMGenerator(phase_id="analyze")
content = generator.generate([
    {"role": "system", "content": "You are an architecture analyst."},
    {"role": "user",   "content": prompt},
])
```

Under the hood, `generate()` calls `litellm.completion()` with streaming:

```python
stream = litellm.completion(
    model=model,
    messages=messages,
    api_base=api_base,
    api_key=api_key,
    max_tokens=max_tokens,
    temperature=temperature,
    top_p=top_p,
    extra_body={"top_k": top_k},
    timeout=chunk_timeout,
    num_retries=3,
    stream=True,
)
```

### Provider Abstraction

LiteLLM abstracts the LLM provider. The `MODEL` env var accepts any
litellm-compatible identifier (e.g., `openai/gpt-4o`, `anthropic/claude-3`,
or a custom model behind an OpenAI-compatible API). An `_ensure_provider_prefix`
function adds the `openai/` prefix for custom model names served via
OpenAI-compatible endpoints (e.g., vLLM, Ollama).

### Phase-Specific Temperatures

Each phase has a tuned temperature default. Resolution order:

1. `LLM_TEMPERATURE_{PHASE}` env var (e.g., `LLM_TEMPERATURE_ANALYZE`)
2. Phase-specific default from code
3. `LLM_TEMPERATURE` env var
4. Global default (1.0 for Qwen3-Coder-Next best practice)

Default temperature map:

| Phase    | Temperature | Rationale                              |
|----------|-------------|----------------------------------------|
| analyze  | 0.5         | Balanced precision for architecture     |
| document | 0.5         | Consistent technical writing            |
| triage   | 0.7         | Needs creative issue classification     |
| plan     | 0.6         | Structured but flexible planning        |
| retry    | 0.3         | Focused correction, minimal creativity  |

Retry attempts further decrease temperature: `max(0.2, 0.3 - (attempt-1) * 0.05)`,
yielding 0.30 -> 0.25 -> 0.20 across three attempts.

### Configuration (Environment Variables)

| Variable              | Default    | Purpose                         |
|-----------------------|------------|---------------------------------|
| `MODEL`               | openai/code| LiteLLM model identifier        |
| `API_BASE`            | (empty)    | OpenAI-compatible API URL       |
| `OPENAI_API_KEY`      | (empty)    | API key                         |
| `MAX_LLM_OUTPUT_TOKENS`| 65536    | Max response tokens             |
| `LLM_TEMPERATURE`     | 1.0        | Global temperature              |
| `LLM_TOP_P`           | 0.95       | Nucleus sampling                |
| `LLM_TOP_K`           | 40         | Top-k sampling (via extra_body) |
| `LLM_CHUNK_TIMEOUT`   | 60         | Stream chunk timeout (seconds)  |

---

## 2. RAG Architecture

### Vector Store: Qdrant

The platform uses Qdrant as its sole vector database (ChromaDB was removed).
The client is a thread-safe singleton (`src/aicodegencrew/shared/utils/qdrant_client.py`)
implementing `VectorStoreProtocol`.

```python
from aicodegencrew.shared.utils.vector_store import get_vector_store

store = get_vector_store()
store.upsert("repo_docs", ids, documents, embeddings, metadatas)
results = store.query("repo_docs", query_embeddings, n_results=10)
```

Key design choices:
- COSINE distance for similarity search
- Deterministic UUID5 point IDs from string document IDs
- ChromaDB-compatible return format for drop-in migration
- SSL/TLS support with `truststore` for corporate CA certificates
- Scroll-based pagination for bulk retrieval

### Chunking

Documents are chunked at 1800 characters (configurable via `CHUNK_CHARS` env var).
This size was chosen to balance context density with embedding quality.

### Evidence Store

Phase 0 (Discover) produces two JSONL indexes:

- `evidence.jsonl` -- source code evidence with file path, line numbers, and snippets
- `symbols.jsonl` -- symbol index (classes, functions, interfaces) for code navigation

Evidence metadata is stored directly in Qdrant payloads (single source of truth),
eliminating the need for a separate metadata database.

### Architecture Dimensions

Phase 1 (Extract) runs 21 deterministic collectors across 16 architecture
dimensions, organized by ecosystem (Java/JVM, JavaScript/TypeScript, C/C++,
Python) plus cross-cutting collectors:

| # | Dimension               | Category | Collector Type |
|---|-------------------------|----------|----------------|
| 1 | system                  | core     | structure      |
| 2 | containers              | core     | structure      |
| 3 | components              | core     | structure      |
| 4 | interfaces              | optional | interface      |
| 5 | data_model              | optional | data           |
| 6 | runtime                 | optional | runtime        |
| 7 | infrastructure          | optional | infrastructure |
| 8 | dependencies            | optional | build          |
| 9 | workflows               | optional | runtime        |
| 10| tech_versions           | optional | build          |
| 11| security_details        | optional | quality        |
| 12| validation              | optional | quality        |
| 13| tests                   | optional | quality        |
| 14| error_handling          | optional | quality        |
| 15| build_system            | optional | build          |
| 16| configuration           | optional | infrastructure |
| 17| logging_observability   | optional | quality        |
| 18| technical_debt          | optional | quality        |
| 19| api_contracts           | optional | interface      |
| 20| communication_patterns  | optional | runtime        |
| 21| evidence (aggregation)  | core     | meta           |

Each collector produces structured JSON with `RawEvidence` objects linking
every fact back to source code (file path, line range, reason, optional snippet).

The ecosystem-specific collectors (e.g., `spring/`, `angular/`, `python_eco/`,
`cpp/`) total approximately 45 collector classes across all ecosystems, feeding
into 16 consolidated architecture dimensions. Each ecosystem subfolder provides
specialized collectors that understand framework-specific patterns (e.g.,
Spring `@RestController`, Angular `NgModule`, Python `FastAPI` routers).

---

## 3. From Multi-Agent to Pipeline+LLM

### Why CrewAI Was Removed

CrewAI was the original orchestration framework (used through early 2026).
It was removed in March 2026 for three reasons:

1. **30% agent loops** -- Agents would enter tool-call loops, repeatedly
   calling the same tool without making progress. No reliable way to detect
   or break these loops.
2. **3x token overhead** -- Agent reasoning, tool selection, and
   self-correction consumed roughly 3x more tokens than the actual useful
   output.
3. **Non-determinism** -- Identical inputs produced structurally different
   outputs across runs, making quality gates unreliable.

### The Pipeline+LLM Pattern

The replacement pattern is explicit and auditable:

```
DataCollector -> PromptBuilder -> litellm.completion() -> Validator -> Retry
```

Each step is a plain Python class with no autonomous decision-making:

- **DataCollector**: Gathers facts from disk (deterministic, no LLM)
- **PromptBuilder**: Constructs system+user messages from templates and data
- **litellm.completion()**: Single LLM call via `LLMGenerator`
- **Validator**: Checks output against schema, length, fact grounding
- **Retry**: If validation fails, `retry_with_feedback()` sends issues back

Example from the Analysis Pipeline (`src/aicodegencrew/pipelines/analysis/pipeline.py`):

```
1. DataCollector.load() -- read all fact files once
2. 16 parallel LLM calls via ThreadPoolExecutor(max_workers=8)
3. Review LLM call -- cross-check sections for gaps & contradictions
4. Selective redo of flagged sections with review feedback
5. Synthesis LLM call -> analyzed_architecture.json
```

Example from the Document Pipeline (`src/aicodegencrew/pipelines/document/pipeline.py`):

```
For each chapter:
    collect data -> build prompt -> 1 LLM call -> validate -> write
```

No agents, no tool loops, no iterations beyond explicit retry-with-feedback.

---

## 4. Prompt Engineering

### Template-First Generation

The Document Pipeline uses a Template-First approach
(`src/aicodegencrew/pipelines/document/template_builder.py`) that reduces
hallucination by constraining LLM output:

1. **Deterministic skeleton** -- `TemplateBuilder` creates a markdown structure
   with verified fact tables already filled in.
2. **LLM enrichment placeholders** -- The template contains
   `<!-- LLM_ENRICH ... -->` markers. The LLM fills only these placeholders,
   not the entire document.
3. **Structure preservation** -- Even if the LLM produces poor output, the
   fact tables and section structure remain intact.

```python
builder = TemplateBuilder()
template = builder.build_chapter_template(recipe, collected_data)
# Template contains:
#   ## 1.1 Requirements Overview
#   | Requirement | Source | Evidence |
#   | ...deterministic data... |
#   <!-- LLM_ENRICH: Summarize the key quality goals -->
```

### Data Recipes

Each chapter has a `ChapterRecipe` defining exactly what data it needs:

```python
@dataclass
class ChapterRecipe:
    id: str
    title: str
    output_file: str
    facts: list[tuple[str, dict]]       # (category, params) for query_facts
    rag_queries: list[str]              # search queries for vector store
    components: list[str]               # stereotypes to include
    sections: list[str]                 # expected markdown sections
    min_length: int = 5000
    max_length: int = 30000
    context_hint: str = ""              # chapter-specific LLM guidance
```

### Few-Shot and Chain-of-Thought

- **Few-Shot**: Section prompts include example outputs showing the expected
  JSON structure and writing style.
- **Chain-of-Thought**: Analysis prompts ask the LLM to reason step-by-step
  through architecture patterns before producing the final structured output.

### Schema Validation

All LLM outputs that produce structured data are validated against Pydantic
models (e.g., `ArchitectureAnalysis`). Invalid JSON or missing required fields
trigger retry-with-feedback.

---

## 5. Hallucination and Fact Grounding

### FactGrounder

The `FactGrounder` class (`src/aicodegencrew/shared/utils/fact_grounding.py`)
checks LLM output against known architecture facts extracted in Phase 1.

```python
grounder = FactGrounder(architecture_facts)
result = grounder.check(llm_output_text)
if not result.passed:
    logger.warning("Low grounding: %s", result.found)
```

**How it works:**

1. Extracts known names from `architecture_facts.json` across three categories:
   - `containers` (deployable units)
   - `technology_stack` (frameworks, libraries)
   - `relations` (connections between components)

2. Searches for each known name in the LLM output text (case-insensitive).

3. Produces a `GroundingResult`:
   - `score`: 0-100 (50% coverage of known names = score 100)
   - `found`: set of known names found in text
   - `passed`: True if at least `min_references` known names appear
     (default 3, or 5% of total known names, whichever is lower)

### Banned Phrases

The `ChapterValidator` checks for hallucination indicator phrases:

```python
BANNED_PHRASES = [
    "placeholder text", "insert here", "fill in later",
    "TODO:", "TBD", "as an AI", "I cannot", "I don't have",
    "auto-generated as a stub", "information is not available",
    "would need to be", "could not be determined",
]
```

Any match triggers validation failure and retry.

### Multi-Layer Anti-Hallucination

1. **Template-First** -- Deterministic fact tables are never LLM-generated
2. **FactGrounder** -- Cross-reference against extracted architecture facts
3. **Banned phrases** -- Catch common LLM hedging/placeholder patterns
4. **Schema validation** -- Pydantic enforces structural correctness
5. **Evidence requirement** -- Every technology and component must have source evidence

---

## 6. Quality Gates

### Cross-Phase Quality Gate

The orchestrator (`src/aicodegencrew/orchestrator.py`) applies quality gates
after each phase:

| Score    | Action                              |
|----------|-------------------------------------|
| >= 70    | Success, proceed to next phase      |
| < 70     | Retry the phase once                |
| < 50     | Mark as partial, continue pipeline  |

Thresholds are configurable via environment variables:
- `QUALITY_GATE_THRESHOLD=70`
- `QUALITY_GATE_MINIMUM=50`

### Pipeline Quality Score

The overall pipeline quality is a weighted score across phases:

```python
_QUALITY_WEIGHTS = {
    "extract":  0.10,   # 10% -- data collection
    "analyze":  0.25,   # 25% -- architecture analysis
    "document": 0.35,   # 35% -- documentation (highest weight)
    "triage":   0.15,   # 15% -- issue classification
    "deliver":  0.15,   # 15% -- final review
}
```

Document phase carries the highest weight (35%) because the primary deliverable
is architecture documentation.

### Quality Gate Checks (Per Phase)

The `QualityGateTool` (`src/aicodegencrew/shared/tools/quality_gate_tool.py`)
runs four checks:

1. **Schema Validation** -- Pydantic model conformance
2. **Evidence Requirements** -- Minimum evidence items per technology/component
3. **Required Sections** -- `repo_name`, `summary`, `analysis_timestamp` present
4. **Technology Detection** -- At least one technology detected

### Phase Contracts

Each phase declares what it requires and provides:

```python
PHASE_CONTRACTS = {
    "discover": {"requires": [],           "provides": ["discover"]},
    "extract":  {"requires": ["discover"], "provides": ["extract"]},
    "analyze":  {"requires": ["extract"],  "provides": ["analyze"]},
    "document": {"requires": ["analyze"],  "provides": ["document"]},
    "triage":   {"requires": ["discover", "extract"], "provides": ["triage"]},
    "plan":     {"requires": ["extract"],  "provides": ["plan"]},
    ...
}
```

---

## 7. Adaptive Retry

When validation fails, `LLMGenerator.retry_with_feedback()` re-prompts the
LLM with escalating severity:

### Attempt Progression

| Attempt | Temperature | Severity Message                                          |
|---------|-------------|-----------------------------------------------------------|
| 1       | 0.30        | "Your previous output had these specific issues..."       |
| 2       | 0.25        | "CRITICAL: Your previous attempt still had problems..."   |
| 3       | 0.20        | "FINAL ATTEMPT: Focus exclusively on fixing these..."     |

### Message Structure

The retry appends the previous output and issues to the conversation:

```python
messages = [
    original_messages[0],                           # system message
    original_messages[1],                           # original user prompt
    {"role": "assistant", "content": previous_output[:15000]},
    {
        "role": "user",
        "content": (
            f"<feedback severity='{attempt}'>\n"
            f"{severity}\n"
            f"- {issue_1}\n- {issue_2}\n...\n"
            f"Output the complete corrected result.\n"
            f"</feedback>\n\n"
            f"<previous_output>\n{previous_output[:15000]}\n</previous_output>"
        ),
    },
]
```

The temperature decreases with each attempt to make the LLM more focused and
deterministic on corrections. Previous output is truncated to 15,000 characters
to stay within context limits.

The Document Pipeline caps retries at `_MAX_RETRIES = 2` per chapter.

---

## 8. LLM Observability

The platform uses three observability layers, all optional and no-op safe
when their dependencies are not configured.

### Langfuse (LLM Tracing)

Configured in `src/aicodegencrew/shared/utils/llm_factory.py`. When
`LANGFUSE_PUBLIC_KEY` is set, Langfuse callbacks are registered on litellm:

```python
litellm.success_callback = [..., "langfuse"]
litellm.failure_callback = [..., "langfuse"]
```

Every `litellm.completion()` call is automatically traced with prompt, response,
latency, and token counts. No code changes needed in pipelines.

### MLflow (Experiment Tracking)

`MLflowTracker` (`src/aicodegencrew/shared/utils/mlflow_tracker.py`) tracks
pipeline runs as MLflow experiments:

```python
tracker = MLflowTracker()
tracker.start_run(run_id="abc123")
tracker.log_phase_metrics("analyze", duration=12.3, tokens=1500, status="success")
tracker.log_artifact("knowledge/extract/architecture_facts.json")
tracker.end_run("success")
```

Metrics logged per phase: duration, token count, status. Artifacts are uploaded
via MLflow's proxy (`mlflow-artifacts://`) so no direct S3/MinIO credentials
are needed on the client.

### Prometheus (Operational Metrics)

When `PROMETHEUS_ENABLED=true`, phase metrics are pushed to Prometheus collectors
exposed at `/metrics` via FastAPI (`ui/backend/routers/prometheus.py`):

```python
sdlc_phase_duration_seconds   # Histogram with phase_id label
sdlc_phase_status_total       # Counter with phase_id, status labels
sdlc_tokens_total             # Counter with phase_id, token_type labels
```

Histogram buckets: 5s, 15s, 30s, 60s, 120s, 300s, 600s, 1800s, 3600s.

### Structured Logging

Every log event includes a `RUN_ID` (8-char UUID) for cross-event correlation:

```python
from aicodegencrew.shared.utils.logger import RUN_ID, log_metric

log_metric("phase_complete", phase="analyze", duration=12.3, tokens_prompt=1200)
```

Metrics are written to `logs/metrics.jsonl` in structured JSON format.
Phase completion events are automatically forwarded to Prometheus when enabled.

---

## 9. Hybrid Architecture Matrix

Not all phases use LLM. The platform deliberately mixes deterministic and
LLM-based processing:

| Phase | # | Name                    | Type         | LLM Usage    |
|-------|---|-------------------------|--------------|--------------|
| 0     | discover  | Repository Indexing     | pipeline     | 0% -- pure Python chunking + embedding |
| 1     | extract   | Architecture Facts      | pipeline     | 0% -- 21 deterministic collectors |
| 2     | analyze   | Architecture Analysis   | pipeline     | 100% -- 16 parallel LLM calls + synthesis |
| 3     | document  | Architecture Synthesis  | pipeline     | Hybrid -- template-first + LLM enrichment |
| 4     | triage    | Issue Triage            | pipeline     | Hybrid -- deterministic detection + LLM classification |
| 5     | plan      | Development Planning    | pipeline     | Hybrid -- component discovery + LLM plan generation |
| 6     | implement | Code Generation         | crew         | Not yet implemented |
| 7     | verify    | Test Generation         | crew         | Not yet implemented |
| 8     | deliver   | Review & Consistency    | pipeline     | LLM -- review and consistency checking |

Design principle: use LLM only where deterministic approaches cannot achieve
the goal. Phases 0-1 are fully deterministic because code parsing and fact
extraction are well-defined problems. Phase 2 is fully LLM because architecture
analysis requires reasoning across dimensions. Phases 3-5 are hybrid, using
deterministic data collection with targeted LLM calls for synthesis.

Phase dependencies form a DAG:

```
discover -> extract -> analyze -> document
                   \-> triage
                   \-> plan -> implement -> verify
                                        \-> deliver
```

---

## 10. Tech Stack

### Core AI/ML

| Technology    | Role                               | Location                              |
|---------------|------------------------------------|---------------------------------------|
| LiteLLM       | LLM routing and provider abstraction| `shared/llm_generator.py`, `shared/utils/llm_factory.py` |
| Qdrant        | Vector database (HNSW, COSINE)     | `shared/utils/qdrant_client.py`       |
| Pydantic      | Schema validation for LLM outputs  | `shared/models/`, validators          |
| truststore    | OS cert store injection for SSL    | `shared/utils/llm_factory.py`, `qdrant_client.py` |

### Observability

| Technology    | Role                               | Location                              |
|---------------|------------------------------------|---------------------------------------|
| Langfuse      | LLM call tracing                   | `shared/utils/llm_factory.py`         |
| MLflow        | Experiment tracking, artifact store| `shared/utils/mlflow_tracker.py`      |
| Prometheus    | Operational metrics                | `ui/backend/routers/prometheus.py`    |
| prometheus-client | Python Prometheus SDK          | `ui/backend/routers/prometheus.py`    |

### Integration

| Technology    | Role                               | Location                              |
|---------------|------------------------------------|---------------------------------------|
| MCP           | Model Context Protocol server      | `mcp/server.py`, `mcp/knowledge_tools.py` |
| FastAPI       | Dashboard backend API              | `ui/backend/`                         |
| Docker        | Containerized deployment           | `docker-compose.yml`                  |

### Removed

| Technology    | Removed   | Reason                                              |
|---------------|-----------|-----------------------------------------------------|
| CrewAI        | March 2026| 30% agent loops, 3x token overhead, non-determinism |
| ChromaDB      | 2026      | Replaced by Qdrant (cloud-native, better scaling)   |

---

## Summary of Key Patterns

1. **Pipeline+LLM over Multi-Agent** -- Deterministic pipelines with targeted LLM calls beat autonomous agents for reliability and cost.
2. **Evidence-First RAG** -- Every fact traces back to source code with file path and line numbers.
3. **Template-First Generation** -- Deterministic skeletons with LLM enrichment placeholders reduce hallucination.
4. **Fact Grounding** -- Cross-reference LLM output against extracted architecture facts.
5. **Adaptive Retry** -- Escalating severity with decreasing temperature for focused corrections.
6. **Phase-Specific Temperatures** -- Each phase tuned for its task (0.3 retry to 0.7 triage).
7. **Quality Weights** -- Document phase (35%) weighted highest because documentation is the primary deliverable.
8. **Three-Layer Observability** -- Langfuse (LLM traces) + MLflow (experiments) + Prometheus (operations).
9. **Hybrid Architecture** -- LLM used only where deterministic approaches are insufficient.
10. **Provider Abstraction** -- LiteLLM allows swapping between OpenAI, Anthropic, Azure, or self-hosted models with zero code changes.
