# AI Masterclass — From Developer to AI Solution Architect

> **Author:** Aymen Mastouri | **Date:** 2026-04-06
> **Purpose:** Complete AI knowledge for interview preparation and expert-level understanding
> **Method:** Every concept explained using AICodeGenCrew (SDLC Pilot) as reference

---

## 1. What is an LLM?

A Large Language Model predicts the next token. It read billions of texts and learned which word likely comes next.

```
Input:  "The capital of France is"
Output: "Paris" (highest probability)
```

**Transformer Architecture** (2017, Google): Text is split into tokens, each represented as a vector. The model calculates attention — "which other tokens matter for this one?" — then outputs a probability distribution over all possible next tokens.

**In your project (Phase 2 Analyze):** You give the LLM facts from `architecture_facts.json` and it generates a human-readable analysis. The LLM never guesses — it synthesizes verified facts.

### Parameter Sizes

| Model | Parameters | GPU RAM | Strength |
|-------|-----------|---------|----------|
| 7B | 7 billion | ~14 GB | Simple tasks, fast |
| 14B | 14 billion | ~28 GB | Code generation |
| 70B | 70 billion | ~140 GB | Deep analysis |
| 120B+ | 120+ billion | ~240 GB | Best quality |

Your project uses **dual-model routing**: large model for analysis/reasoning, smaller model for code generation — because a 14B model responds 8x faster than 120B.

### What an LLM is NOT

- Not a database (it learned patterns, not exact knowledge)
- Not a reasoner (it simulates reasoning through pattern matching)
- Not deterministic (same input can produce different outputs)

This is why your project uses **Evidence-First**: the LLM never guesses about code structure. Deterministic facts first, LLM synthesis second.

---

## 2. Tokens and Context Window

### Tokens

A token is a piece of text — typically a word or word-part.

```
"UserService" = 3 tokens: ["User", "Serv", "ice"]
"REST API"    = 2 tokens: ["REST", " API"]
```

**Rule of thumb:** 1 token = ~4 characters (English), ~3 characters (code)

### Context Window

Maximum tokens the LLM can process at once (input + output combined).

| Model | Context Window | ~Characters |
|-------|---------------|-------------|
| GPT-4 | 128K tokens | ~500K |
| Qwen3-Coder | 262K tokens | ~1M |
| Claude Opus | 1M tokens | ~4M |

**Your project:** Configured for 262K tokens (`LLM_CONTEXT_WINDOW=262144`).

**The problem:** Your project analyzes repos with 100K+ lines. Solution: **Decomposition** — Phase 2 runs 16 parallel LLM calls, each with ~10K tokens input, instead of one massive call.

### Token Costs

| Provider | Input | Output |
|----------|-------|--------|
| GPT-4o | $2.50/1M tokens | $10.00/1M tokens |
| On-Prem (Ollama) | $0 | $0 |

Your project is on-prem — zero token costs. But you still track usage (MLflow, Langfuse) for optimization.

---

## 3. Temperature, Top-P and Sampling

### Temperature

Controls randomness of LLM output.

```
Temperature = 0.0  ->  Always the most probable word (deterministic)
Temperature = 0.5  ->  Mostly probable, sometimes surprising
Temperature = 1.0  ->  Natural distribution (creative)
```

**Technically:** The LLM computes probabilities for all possible next tokens. Temperature scales this distribution — low temperature sharpens it (more deterministic), high temperature flattens it (more random).

### Your Phase Temperatures

```python
_PHASE_TEMPERATURE_DEFAULTS = {
    "analyze": 0.5,   # Balance: consistent but analytically deep
    "document": 0.5,  # Consistent documentation
    "triage": 0.7,    # Higher: broader issue detection
    "plan": 0.6,      # Moderate creativity for solution proposals
    "retry": 0.3,     # Low: conservative corrections
}
```

**Why decreasing temperature on retry?** Each retry attempt forces the model to be more conservative — it deviates less from the template. Like telling an employee: "Don't be creative, stick to the template."

### Top-P (Nucleus Sampling)

Top-P selects from the most probable tokens that together make up P% of the probability mass.

```python
_DEFAULT_TOP_P = 0.95  # Qwen3-Coder-Next manufacturer recommendation
```

---

## 4. Prompt Engineering

### The 4 Techniques You Use

#### 1. System Prompt
Defines the role and rules for the LLM. Each PromptBuilder sets a specific system prompt per phase.

#### 2. Few-Shot Prompting
Give the LLM examples of desired output. Your `pipelines/document/prompt_builder.py` uses few-shot examples for each Arc42 chapter. The LLM learns format, depth, and style from examples.

#### 3. Chain-of-Thought (CoT)
Ask the LLM to think step by step. This improves quality because when it writes "Step 1", it has that context when generating "Step 2".

#### 4. Structured Output (Pydantic Schema)
Define the exact output format as a schema. The LLM must produce JSON matching the schema. Invalid output triggers retry with validation error as feedback.

### Template-First Pattern (Your Innovation)

**Problem:** Give LLM a blank page, it hallucinate structure and facts.

**Solution:**

```
Step 1: TemplateBuilder (100% deterministic)
  - Chapter headings from data recipe
  - Fact tables (containers, interfaces, relations)
  - <!-- LLM_ENRICH: section_id --> placeholders

Step 2: LLM fills ONLY the placeholders
  - Less output = less hallucination
  - Structure is guaranteed
  - Fact tables are deterministically correct

Step 3: Validator checks
  - All placeholders filled?
  - Fact tables preserved?
  - Structural checks (length, sections, banned phrases)
```

---

## 5. Embeddings — Text as Numbers

Computers can't compute with text. **Embeddings** convert text into number lists (vectors) so that **similar texts get similar numbers**.

```
"UserService"    -> [0.82, 0.15, -0.43, 0.91, ...]  (768 numbers)
"BenutzerDienst" -> [0.80, 0.17, -0.41, 0.89, ...]  (similar!)
"Database"       -> [0.12, 0.88, 0.33, -0.21, ...]  (very different)
```

**Embedding search** finds semantically similar code, not just keyword matches. "authentication" also finds `SecurityConfig.java`, `JwtFilter.java`, `LoginController.java` — because the model understands meaning, not just characters.

**In your project (Phase 0):** Source code is chunked (1800 chars), embedded via Ollama, and stored in Qdrant.

---

## 6. Vector Stores and Similarity Search

### Qdrant (Your Vector Store)

```python
collection_name = f"repo_docs_{project_slug}_{branch}"

# Each vector has payload (metadata)
{
    "vector": [0.82, 0.15, -0.43, ...],    # 768 dimensions
    "payload": {
        "file_path": "src/main/java/UserService.java",
        "line_number": 42,
        "content_type": "java_class",
        "content": "public class UserService { ... }"
    }
}
```

### Cosine Similarity

Measures the angle between two vectors: 1.0 = identical, 0.0 = unrelated, -1.0 = opposite.

### Top-K Retrieval

"Give me the K most similar chunks" — this is the foundation for RAG.

---

## 7. RAG — Retrieval-Augmented Generation

### The Core Concept

**Problem:** An LLM knows nothing about your specific code.
**Solution:** Before asking the LLM, search for relevant information and include it as context.

### Your RAG Pipeline

```
INDEXING (Phase 0, one-time, zero LLM)
  Source Code -> File Filter -> Chunking (1800 chars) -> Embedding -> Qdrant
                             -> Symbol Extraction -> symbols.jsonl
                             -> Evidence Metadata -> evidence.jsonl

EXTRACTION (Phase 1, zero LLM)
  45 Collectors -> 16 Architecture Dimensions -> architecture_facts.json

RETRIEVAL (Phases 2-8, per question)
  Question -> Embed query -> Qdrant similarity search -> Top-K chunks
  -> LLM prompt: System + Facts + RAG results + Question -> Answer
```

### Why RAG over Fine-Tuning?

| | RAG | Fine-Tuning |
|--|-----|-------------|
| Update data | Easy: re-index (5 min) | Hard: retrain model (hours) |
| Source transparency | Yes: "Source: UserService.java:42" | No |
| Cost | Only indexing | GPU training |
| Accuracy | High: exact snippets | Medium: can hallucinate |

---

## 8. Chunking Strategies

### Fixed-Size (Your Current Approach)

1800 characters per chunk. Problem: can cut methods in half, breaking semantic context.

### AST-based (Planned Improvement)

Code-aware chunking: each chunk is one complete method or class. Parent context (class signature) included as metadata.

### Overlap Strategy

10-20% overlap between chunks ensures information at boundaries isn't lost.

---

## 9. Hybrid Search and Reranking

### The Problem

Dense embedding search understands semantics but fails on exact keywords:
- Query: `"@PreAuthorize"` — dense search finds SecurityConfig (semantic), but misses the files that literally contain the annotation.

### Hybrid Search (Planned)

Combine dense (semantic) + sparse (BM25/keywords) vectors via Reciprocal Rank Fusion (RRF).

### Two-Stage Reranking (Planned)

1. **Bi-Encoder** (fast, 20ms): Get top-50 candidates from Qdrant
2. **Cross-Encoder** (precise, 200ms): Re-rank to top-10

---

## 10. Hallucination and Fact Grounding

### What is Hallucination?

The LLM invents things that sound plausible but are false: "The project has a PaymentService..." — when no PaymentService exists.

### Your Fact Grounding

```python
grounder = FactGrounder(architecture_facts)
result = grounder.check(llm_output_text)
# result.score = 67  (67% of named entities exist)
# result.found = {"UserService", "OrderService"}
# result.hallucinated = {"PaymentService"}
# result.passed = False -> Retry!
```

**How it works:**
1. Extract proper nouns from LLM output (CamelCase, PascalCase, kebab-case)
2. Match against known entities from `architecture_facts.json`
3. Score = found / (found + hallucinated) * 100

### Evidence-First Pattern

Your core principle: LLMs don't guess. Phase 0+1 extract facts deterministically (45 collectors, zero LLM). Phase 2+ synthesizes only verified data.

---

## 11. Multi-Agent vs Pipeline+LLM

### Why CrewAI Was Removed (March 2026)

| Problem | Impact | Frequency |
|---------|--------|-----------|
| Agent-Loop | Agent calls tool repeatedly with identical input | ~30% of runs |
| Context Overflow | Multi-agent chat exceeds token limit | Large repos |
| Stubs | Agent writes "TODO" instead of real content | ~10% |
| Unpredictable runtime | Same input: 5-45 min variance | Always |
| Token waste | Agent turns, tool calls, retries | 3x overhead |

### Pipeline+LLM Pattern (Your Solution)

```
DataCollector (deterministic)
  -> PromptBuilder (deterministic)
    -> litellm.completion() (single call, no loops)
      -> Validator (deterministic)
        -> Retry with escalating feedback (max 2-3x)
```

### Results

| Metric | With CrewAI | Pipeline+LLM |
|--------|------------|--------------|
| Agent-Loop rate | ~30% | 0% |
| Stub rate | ~10% | 0% |
| Phase 3 duration | 25-40 min | 10-15 min |
| Tokens per phase | ~150K | ~50K |
| Reproducibility | Low | High |

### When to Use What

Multi-agent: iterative tool-calling (code write, build, fix). Pipeline+LLM: analysis, documentation, planning — everything predictable.

---

## 12. Quality Gates and LLM Output Validation

### 3-Level Quality System

**Level 1: Structural Validation (deterministic)**
- Triage: 9 checks (big_picture length >= 80 chars, scope boundaries, no action steps, etc.)
- Plan: 6 checks (has steps, no phantom components, triage components addressed)
- Document: 7 structural + template integrity + fact grounding

**Level 2: Semantic Validation**
- Fact Grounding: hallucinated component detection
- Plan Content Validator: triage coverage, risk awareness

**Level 3: Cross-Phase Quality Gates**
```
quality_score >= 70? -> SUCCESS
  < 70 -> Auto-Retry (1x, lower temperature)
  < 50 after retry -> PARTIAL (pipeline continues)
```

### Pipeline Quality Score

Weighted aggregate: Extract (10%) + Analyze (25%) + Document (35%) + Triage (15%) + Deliver (15%).

### Adaptive Retry

| Attempt | Severity | Temperature | Prompt |
|---------|----------|-------------|--------|
| 1 | Normal | 0.30 | "Issues found, please fix" |
| 2 | Critical | 0.25 | "CRITICAL: Still problems, fix ONLY these" |
| 3 | Final | 0.20 | "FINAL ATTEMPT: Focus exclusively on these" |

---

## 13. LLM Observability and Costs

### Your Observability Stack

- **Langfuse** (localhost:3000): Traces every LLM call — prompts, responses, latency, tokens
- **MLflow** (localhost:5000): Pipeline Quality Score, phase metrics, artifacts
- **Prometheus** (localhost:9090) + **Grafana** (localhost:3001): Runtime dashboards
- **Structured Logging**: JSON events with RUN_ID correlation

### Cost Estimation

```
Phase 2 (Analyze): 16 parallel calls
  Input:  ~8K tokens x 16 = 128K input tokens
  Output: ~3K tokens x 16 =  48K output tokens

Total per run: ~400K tokens
  GPT-4o: ~$5/run
  On-Prem (Ollama): $0 (only electricity)
```

---

## 14. Model Selection

### When Fine-Tuning, When RAG, When Prompt Engineering?

```
Does data change frequently?
  Yes -> RAG (your approach: code changes constantly)
  No  -> Is it a specialized domain?
           Yes -> Fine-Tuning (medicine, law)
           No  -> Prompt Engineering (90% of cases)
```

---

## 15. On-Prem vs Cloud

| Criterion | On-Prem | Cloud |
|-----------|---------|-------|
| Data privacy | Code never leaves network | Code sent to US servers |
| Compliance | BSI/GDPR compliant | Problematic |
| Cost (volume) | Fixed (GPU hardware) | Variable (per token) |
| Latency | Network-internal (~5ms) | Internet (~100ms) |
| Model choice | Free (Ollama, vLLM) | Provider-specific |

Your project is 100% on-prem: LLM via Ollama, Qdrant local, Langfuse/MLflow local.

---

## 16. ML Fundamentals for Solution Architects

### Machine Learning in 60 Seconds

```
Traditional software:  Input -> Rules -> Output
Machine learning:      Input + Output -> Model (learns the rules)
```

### How Your LLM Was Trained

1. **Pre-Training** (Unsupervised): Read billions of texts, predict next word
2. **Instruction Fine-Tuning** (Supervised): (Question, Answer) pairs
3. **RLHF**: Humans rate responses, model learns preferences

### What You Must Know (as SA)

- Difference between pre-training, fine-tuning, and RAG
- When to use RAG vs fine-tuning
- Token costs and latency estimates
- Model sizes and their implications

### What You Don't Need to Know

- Transformer math (attention mechanism details)
- Backpropagation / gradient descent
- PyTorch / TensorFlow code

You're a Solution Architect, not a Data Scientist.

---

## 17. MCP — Model Context Protocol

Standard protocol for communication between LLM applications and external tools/data sources. Instead of every app having its own tool format, MCP provides a universal interface.

Your MCP server (`aicodegencrew-mcp`) exposes project knowledge as standardized tools: `rag_search`, `facts_query`, `symbol_lookup`.

---

## 18. Interview Questions and Answers

### "What is RAG and why do you use it?"

> "RAG means we retrieve relevant information from a knowledge base before asking the LLM. Phase 0 indexes the entire source code into Qdrant. When Phase 2 does architecture analysis, RAGQueryTool finds the 10 most relevant code snippets via cosine similarity and gives them to the LLM as context. We use RAG instead of fine-tuning because the code changes constantly — re-indexing takes 5 minutes, re-training would take hours."

### "How do you prevent hallucination?"

> "Three mechanisms: Evidence-First — Phase 0+1 extract all facts deterministically. Template-First — TemplateBuilder creates a deterministic skeleton with fact tables, LLM fills only placeholders. Fact Grounding — FactGrounder matches proper nouns in LLM output against known entities from architecture_facts.json."

### "Why did you replace CrewAI with pipelines?"

> "CrewAI agents had 30% loop rate, 3x token overhead, unpredictable runtime. Our Pipeline+LLM pattern uses deterministic data collection plus a single litellm.completion() call per step. Result: 0% loops, 2x faster, 3x fewer tokens, 100% reproducible."

### "How do you ensure LLM quality?"

> "Three-level system: structural validation (9 checks for triage, 6 for plan), semantic validation (fact grounding detects hallucinated components), and cross-phase quality gates (auto-retry below score 70 with escalating feedback and decreasing temperature)."

### "How would you scale the system?"

> "Three levels: Embedding-level with Qdrant payload indexes and INT8 quantization for 10x faster queries. Analysis-level with 16 parallel LLM calls via ThreadPoolExecutor. For very large repos, automatic MapReduce: parallel container analysis, then synthesis."

### "On-prem vs cloud — why?"

> "Enterprise source code must not leave the network — BSI/GDPR compliance. At 400K tokens per run, GPT-4o costs ~$5/run, on-prem only electricity. Plus full model independence — we can switch models anytime."

### "Explain temperature and why different values per phase?"

> "Temperature controls output randomness. We use 0.5 for analysis/documentation (consistency), 0.7 for triage (broader detection), 0.3 decreasing for retries (forces conservative corrections)."

### "What's the difference between embedding and LLM?"

> "Embedding model converts text to a fixed-size vector — it understands similarity. LLM generates new text token by token. We use embeddings for Qdrant search and LLMs for analysis — two different models for two different tasks."

---

*This document is your study material. Read it, understand the concepts, translate them back to your project. Every interview answer is based on real experience from SDLC Pilot.*

---

(c) 2025-2026 Aymen Mastouri. All rights reserved.
