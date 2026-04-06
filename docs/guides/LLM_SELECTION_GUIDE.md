# LLM Selection Guide — AICodeGenCrew

> **Platform**: On-Prem AI
> All models run on-premises. No data leaves the network.

---

## 1. Available Models

| Alias | Modell | Architektur | Parameter | Aktiv | Kontext | Lizenz | Herkunft |
|-------|--------|------------|-----------|-------|---------|--------|---------|
| `complex_tasks` | **Kimi-K2.5** | MoE | 1T total | 32B | 196 608 | MIT | Moonshot / CN |
| `chat` | **GPT-OSS-120B** | MoE | 120B total | 5.1B | 131 072 | Apache 2 | OpenAI / US |
| `code` | **Qwen3-Coder-Next** | MoE (Hybrid) | 80B total | 3B | 262 144 | Apache 2 | Alibaba / CN |
| `vision` | **Mistral-Small-3.1-24B** | Dense | 24B | 24B | 131 071 | Apache 2 | Mistral / EU |
| `embed` | Platform Embedding | — | — | — | — | — | — |

**API-Endpunkt:** `https://your-litellm.example.com/v1`
**API-Key:** shared for all models (in `.env` als `OPENAI_API_KEY`)

---

## 2. Model Routing

| Env-Variable | Alias | Modell | Verwendet von |
|---|---|---|---|
| `MODEL` | `openai/code` | Qwen3-Coder-Next | Alle Standard-Crews (Analyse, Triage, Docs, Deliver) |
| `FAST_MODEL` | `openai/code` | Qwen3-Coder-Next | Schnelle / einfache Tasks (Klassifizierung, Formatting) |
| `CODEGEN_MODEL` | `openai/code` | Qwen3-Coder-Next | Code-Generierung + Test-Generierung |
| `VISION_MODEL` | `openai/vision` | Mistral-Small-3.1-24B | OCR, Diagramm-Analyse, Screenshot-Verarbeitung |
| `EMBED_MODEL` | `embed` | Platform Embed | Vektorsuche (ChromaDB, RAG) |

> **Simplification:** MODEL, FAST_MODEL und CODEGEN_MODEL verwenden alle dasselbe Modell
> (Qwen3-Coder-Next). Die Trennung bleibt als Env-Variablen erhalten, so that if needed
> individual phases can be switched to different models.

---

## 3. Model per Phase

### Phase 0 — Discover (Repository-Indexierung)
- **LLM:** none
- **Typ:** deterministic
- **Was:** Codebase → ChromaDB-Vektorindex, `repo_manifest.json`, `symbols.jsonl`
- **Output:** `knowledge/discover/`

---

### Phase 1 — Extract (Architektur-Fakten)
- **LLM:** none
- **Typ:** deterministic
- **Was:** Statische Code-Analyse → 17 Dimensions-Dateien (`components.json`, `relations.json`, `interfaces.json`, …)
- **Output:** `knowledge/extract/architecture_facts.json`

---

### Phase 2 — Analyze (Architektur-Analyse)
- **LLM:** `MODEL` → **Qwen3-Coder-Next** (`openai/code`)
- **Funktion:** `create_llm()`
- **Kontext:** 262 144 Tokens
- **Why Qwen3-Coder-Next:** 5 parallele Mini-Crews, tiefes Reasoning über Architekturmuster, Domain-Modelle, Qualitätsanalyse; langer Kontext für große Codebasen
- **Agents:** `tech_architect`, `func_analyst`, `quality_analyst`, `synthesis_lead`
- **Mini-Crews (parallel):**
  1. `tech_analysis` — Architekturstil, Design Patterns, Tech-Stack
  2. `domain_analysis` — Domain-Modell, Bounded Contexts, Business Capabilities
  3. `workflow_analysis` — Workflows, State Machines
  4. `quality_analysis` — Technical Debt, Security, Operability
  5. `synthesis` — Zusammenführung aller 16 Analysen
- **Output:** `knowledge/analyze/analyzed_architecture.json`

---

### Phase 3 — Document (C4 + Arc42)
- **LLM:** `MODEL` → **Qwen3-Coder-Next** (`openai/code`)
- **Funktion:** `create_llm()` (mit `FAST_MODEL`-Unterstützung für einfache Agents via `use_fast_model=True`)
- **Kontext:** 262 144 Tokens
- **Why Qwen3-Coder-Next:** Arc42-Kapitel = 6–12 Seiten langer strukturierter Output; C4-Diagramme brauchen exaktes Schema-Following; 262K-Kontext für große Codebasen
- **Sub-Crews (sequenziell):**
  1. **C4 Crew** — L1 System Context, L2 Container, L3 Component Diagramme (DrawIO)
  2. **Arc42 Crew** — 12 Arc42-Kapitel (~50 Seiten)
- **Output:** `knowledge/document/c4/` + `knowledge/document/arc42/`

---

### Phase 4 — Triage (Issue-Klassifizierung)
- **LLM:** `MODEL` → **Qwen3-Coder-Next** (`openai/code`)
- **Funktion:** `create_llm(temperature=0.2)`
- **Typ:** Hybrid (deterministic + LLM-Synthese)
- **Deterministische Phase (kein LLM, <5 s):**
  - Issue-Klassifizierung, Blast-Radius (BFS), Entry-Points, Duplikat-Erkennung (ChromaDB)
- **LLM-Phase:**
  - Agent 1: `Issue Context Analyst` — Synthese aus deterministicen Findings → `customer_summary` + `developer_context`
  - Agent 2: `Triage Quality Reviewer` — Qualitäts-Review (kein Tool-Use)
- **Output:** `knowledge/triage/` (findings.json, customer.md, developer.md, triage.json)

---

### Phase 5 — Plan (Implementierungsplanung)
- **LLM:** `MODEL` → **Qwen3-Coder-Next** (`openai/code`) für Planner, `FAST_MODEL` → **Qwen3-Coder-Next** für Reviewer
- **Funktion:** `create_llm()` (Planner) + `create_fast_llm()` (Reviewer)
- **Typ:** Hybrid (5-Stufen-Pipeline, nur Stufe 4 = LLM)
- **Why Qwen3-Coder-Next:** JSON-Schema-Compliance kritisch (Pydantic-Validierung); komplexes Reasoning über Abhängigkeitsgraphen; langer strukturierter Output
- **Pipeline:**
  1. Input Parser (deterministic, <1 s) — JIRA XML, DOCX, Excel
  2. Component Discovery (RAG + Scoring, 2–5 s)
  3. Pattern Matcher (TF-IDF + Rules, 1–3 s)
  4. **Plan Generator (LLM, 15–30 s)** — erzeugt `ImplementationPlan`-JSON
  5. Validator (Pydantic, <1 s)
- **Output:** `knowledge/plan/{task_id}_plan.json`

---

### Phase 6 — Implement (Code-Generierung)
- **LLM:** `CODEGEN_MODEL` → **Qwen3-Coder-Next** (`openai/code`)
- **Funktion:** `create_codegen_llm()`
- **Kontext:** 262 144 Tokens
- **Why Qwen3-Coder-Next:** Speziell für agentic Coding trainiert; Hybrid Gated DeltaNet + Attention für langen Kontext; exzellentes Tool-Use und Build-Error-Recovery; 10–20× effizienter als vergleichbare Dense-Modelle
- **Typ:** Hybrid (Build-Fix-Loop, max. 3 Versuche)
- **Agent:** `Developer` — liest Plan, schreibt Code, repariert Build-Fehler
- **Tools:** CodeReader, CodeWriter, FactsQuery, RAG, Symbol, ImportIndex, DependencyLookup, BuildRunner, BuildErrorParser
- **Output:** Git-Branch `codegen/{task_id}` + `knowledge/implement/{task_id}_report.json`

---

### Phase 7 — Verify (Test-Generierung)
- **LLM:** `CODEGEN_MODEL` → **Qwen3-Coder-Next** (`openai/code`)
- **Funktion:** `create_codegen_llm()`
- **Kontext:** 262 144 Tokens
- **Why Qwen3-Coder-Next:** Test-Code ist Code; Framework-spezifische Syntax (JUnit 5 + Mockito, Angular TestBed + Jasmine); gleiche Stärken wie Phase 6
- **Agent pro Datei:** `Test Generator` — liest Quell-Datei, schreibt Test-Datei
- **Sprachen:** Java (JUnit 5 + Mockito), TypeScript (Angular TestBed + Jasmine)
- **Output:** `knowledge/verify/{task_id}_verify.json` + Test-Dateien im Repo

---

### Phase 8 — Deliver (Review & Konsistenzprüfung)
- **LLM:** `MODEL` → **Qwen3-Coder-Next** (`openai/code`)
- **Funktion:** `create_llm(temperature=0.2)`
- **Typ:** Hybrid (deterministic + LLM-Synthese)
- **Deterministische Phase (kein LLM):**
  - C4-Container-Coverage-Check, Arc42-Kapitel-Vollständigkeit, Placeholder-Erkennung (TODO/FIXME/TBD), Quality-Score (0–100)
- **LLM-Phase:**
  - Agent: `Architecture Quality Reviewer` — synthetisiert Qualitätsbericht (Markdown)
- **Output:** `knowledge/deliver/` (consistency.json, quality.json, synthesis-report.md)

---

## 4. Overview: Phase to Model

| Phase | Name | LLM-Funktion | Modell | Kontext |
|-------|------|-------------|--------|---------|
| 0 | Discover | — | none | — |
| 1 | Extract | — | none | — |
| 2 | Analyze | `create_llm()` | Qwen3-Coder-Next | 262 144 |
| 3 | Document | `create_llm()` | Qwen3-Coder-Next | 262 144 |
| 4 | Triage | `create_llm()` | Qwen3-Coder-Next | 262 144 |
| 5 | Plan | `create_llm()` + `create_fast_llm()` | Qwen3-Coder-Next | 262 144 |
| 6 | Implement | `create_codegen_llm()` | Qwen3-Coder-Next | 262 144 |
| 7 | Verify | `create_codegen_llm()` | Qwen3-Coder-Next | 262 144 |
| 8 | Deliver | `create_llm()` | Qwen3-Coder-Next | 262 144 |

> **Currently** verwenden alle Phasen dasselbe Modell (Qwen3-Coder-Next via `openai/code`).
> Die Env-Variablen `MODEL`, `FAST_MODEL`, `CODEGEN_MODEL` bleiben getrennt,
> so that if needed individual phases can be switched to different models.
> `FAST_MODEL` wird automatisch in `architecture_synthesis` (Phase 3)
> für einfache/formulaische Agents verwendet (`use_fast_model=True` in `base_crew.py`).

---

## 5. Pipeline Requirements

| Anforderung | Phasen | Modell |
|---|---|---|
| Tiefes Reasoning, lange Analyse | 2, 3, 5 | Qwen3-Coder-Next (`code`) |
| JSON-Schema-Compliance | 5 (Plan) | Qwen3-Coder-Next (`code`) |
| Langer strukturierter Output | 3 (Arc42) | Qwen3-Coder-Next (`code`) |
| Code schreiben + Build-Error-Recovery | 6, 7 | Qwen3-Coder-Next (`code`) |
| Tool-Use + agentic Loops | 6 | Qwen3-Coder-Next (`code`) |
| Schnelle Klassifizierung | 3, 5 (Reviewer) | Qwen3-Coder-Next (`code`) |
| OCR / Diagramme / Bilder | zukünftig | Mistral-Small-3.1-24B (`vision`) |
| Vektorsuche (RAG) | alle | Platform `embed` |

---

## 6. Configuration (`.env`)

```env
# On-Prem AI Platform — single endpoint, single API key for all models
API_BASE=https://your-litellm.example.com/v1
OPENAI_API_KEY=sk-your-api-key-here

# Qwen3-Coder-Next (80B MoE, 3B active, 262K ctx) — all crews
MODEL=openai/code

# Same model (can be overridden for lighter tasks)
FAST_MODEL=openai/code

# Qwen3-Coder-Next (80B MoE, 3B active, 262K ctx) — code generation
CODEGEN_MODEL=openai/code

# Mistral-Small-3.1-24B-Instruct (24B, 131K ctx, EU) — vision
VISION_MODEL=openai/vision

# Embeddings
EMBED_MODEL=embed

# Context limit (Qwen3-Coder-Next native)
LLM_CONTEXT_WINDOW=262144
MAX_LLM_OUTPUT_TOKENS=65536
```
