# SDLC Pilot

**AI-Powered Software Development Lifecycle Automation**

[![Version](https://img.shields.io/badge/version-0.8.0-blue.svg)](#changelog)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Angular 21](https://img.shields.io/badge/dashboard-Angular%2021-red.svg)](#dashboard)
[![Tests](https://img.shields.io/badge/tests-745%20passed-brightgreen.svg)](#testing)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![On-Premises](https://img.shields.io/badge/deployment-on--premises-purple.svg)](#deployment)

SDLC Pilot analyzes existing codebases, generates evidence-based architecture documentation, and automates the full development lifecycle — from repository indexing to delivery review. Runs entirely on your infrastructure. **No data leaves your network.**

---

## The Problem

Development teams waste weeks manually analyzing codebases, writing architecture documentation, and planning work. Existing AI tools either send your source code to external APIs or generate hallucinated documentation not grounded in actual code.

## The Solution

SDLC Pilot uses a **9-phase pipeline architecture** that:

1. **Indexes your entire codebase** into a vector store (Qdrant) with full evidence tracking
2. **Extracts architecture facts deterministically** — 45 collectors, 16 dimensions, zero LLM involvement
3. **Generates documentation grounded in code** — every claim backed by file path and line number
4. **Runs 100% on-premises** — your code never leaves your network

> **Key Insight:** LLMs don't guess about your code. They analyze verified facts that were extracted deterministically from your codebase.

---

## Architecture

```
KNOWLEDGE (no LLM)          REASONING (Pipeline + LLM)       EXECUTION
━━━━━━━━━━━━━━━━━━          ━━━━━━━━━━━━━━━━━━━━━━━━━━       ━━━━━━━━━
Phase 0: Discover    --->   Phase 2: Analyze          --->   Phase 6: Implement *
Phase 1: Extract     --->   Phase 3: Document         --->   Phase 7: Verify *
                            Phase 4: Triage           --->   Phase 8: Deliver
                            Phase 5: Plan

* Phases 6-7 are not yet implemented
```

| Phase | LLM | What it does |
|-------|:---:|-------------|
| **0 Discover** | No | Index codebase into Qdrant vector store, extract symbols and evidence |
| **1 Extract** | No | Deterministically extract 16 architecture dimensions via 45 collectors |
| **2 Analyze** | Yes | 16 parallel LLM calls + cross-section review + synthesis |
| **3 Document** | Hybrid | Template-first: deterministic skeleton + LLM enrichment (C4 + Arc42) |
| **4 Triage** | Hybrid | Deterministic scan (<5s) + single LLM synthesis (~30s) |
| **5 Plan** | Hybrid | 4 deterministic stages + 1 LLM call + 2 validators |
| **8 Deliver** | Yes | Consistency review + quality synthesis report |

### Data Flow

```
Source Repository
  |
  v
Discover --> Qdrant vectors + symbols.jsonl + evidence.jsonl
Extract  --> architecture_facts.json (16 dimensions, ground truth)
Analyze  --> analyzed_architecture.json
Document --> C4 diagrams + Arc42 chapters + DrawIO
Triage   --> Issue findings + developer briefs
Plan     --> Implementation plans per task
Deliver  --> Consistency report + quality synthesis
```

---

## Key Features

### Evidence-First AI
Every LLM claim is backed by code evidence. Phase 0+1 extract facts deterministically (zero LLM). Phase 2+ synthesize only what's been proven.

### Anti-Hallucination
- **Fact Grounding**: Detects hallucinated component names by matching against known entities
- **Template-First**: Deterministic markdown skeleton with fact tables — LLM fills only placeholders
- **Quality Gates**: Auto-retry below threshold with escalating feedback and decreasing temperature

### Pipeline Quality Score
Weighted aggregate across phases: Extract (10%) + Analyze (25%) + Document (35%) + Triage (15%) + Deliver (15%). Tracked in MLflow, displayed in dashboard.

### Dual Interface
- **Web Dashboard** — Angular 21 + Material Design. Start pipelines, upload tasks, browse results, view metrics.
- **CLI** — Full pipeline control from the terminal. Presets, phase selection, Git integration.

### On-Premises Ready
- LLM via Ollama or any OpenAI-compatible API (self-hosted)
- Vector store: Qdrant (self-hosted)
- Observability: Langfuse + MLflow + Prometheus (all self-hosted)
- SSL: Corporate CA support via `truststore`

---

## Quick Start

### Step 1: Prerequisites

Install [Ollama](https://ollama.com) (local LLM) and [Docker](https://docs.docker.com/get-docker/) (or [Colima](https://github.com/abiosoft/colima) for Mac):

```bash
# Pull LLM models
ollama pull qwen3.5              # 9.7B coding model
ollama pull nomic-embed-text     # Embedding model for RAG
```

### Step 2: Start Platform Services

```bash
git clone https://github.com/aymenmastouri/aicodegencrew.git
cd aicodegencrew

# Start all services (Qdrant, Langfuse, MLflow, Prometheus, Grafana)
docker-compose -f docker-compose.local.yml up -d
```

**Active services** (included in `docker-compose.local.yml`):

| Service | URL | Login | Purpose |
|---------|-----|-------|---------|
| **Qdrant** | http://localhost:6333/dashboard | — | Vector store (semantic code search) |
| **Langfuse** | http://localhost:3000 | Sign up on first visit | LLM observability (prompt tracing) |
| **MLflow** | http://localhost:5001 | admin / password1234 | Experiment tracking (pipeline metrics) |
| **Prometheus** | http://localhost:9090 | — | Runtime metrics |
| **Grafana** | http://localhost:3001 | admin / admin | Monitoring dashboards |
| **Ollama** | http://localhost:11434 | — | Local LLM (runs natively, not Docker) |

**Disabled services** (planned, configure via `.env` if available):

| Service | Purpose | Status |
|---------|---------|--------|
| Neo4J | Knowledge graph (architecture as nodes/edges) | Code ready, no local container |
| Authentik | OIDC authentication for dashboard | Not implemented |
| MCPO | MCP HTTP proxy | Using stdio transport |
| Docling | PDF/DOCX to Markdown conversion | Not tested |

> See [Platform Services Guide](docs/platform-services.md) for full configuration details.

> **Langfuse first-time setup:**
> 1. Open http://localhost:3000
> 2. Click **"Sign Up"** — create an account (email + password)
> 3. Click **"New Project"** — name it "SDLC Pilot"
> 4. Langfuse shows you two API keys: **Public Key** (`pk-lf-...`) and **Secret Key** (`sk-lf-...`)
> 5. Copy both keys into your `.env`:
> ```
> LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxx
> LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxx
> LANGFUSE_HOST=http://localhost:3000
> ```
> Without these keys, everything still works — Langfuse tracing is simply skipped.

### Platform Management

```bash
# Start all services
docker-compose -f docker-compose.local.yml up -d

# Stop all services (data is preserved in Docker volumes)
docker-compose -f docker-compose.local.yml down

# Restart a single service
docker-compose -f docker-compose.local.yml restart qdrant

# View logs
docker-compose -f docker-compose.local.yml logs -f          # all services
docker-compose -f docker-compose.local.yml logs -f mlflow   # single service

# Check status
docker-compose -f docker-compose.local.yml ps

# Reset everything (WARNING: deletes all data!)
docker-compose -f docker-compose.local.yml down -v
```

> **Note:** `down` preserves all data (Qdrant collections, MLflow experiments, Langfuse traces).
> Only `down -v` deletes the Docker volumes and resets everything.

### Step 3: Start Dashboard

```bash
cp .env.example .env             # Pre-configured for local Ollama + Docker services
# Edit .env: set PROJECT_PATH to the repo you want to analyze

python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,parsers]"

cd ui/frontend && npm install && cd ../..
npm install && npm run dev
```

Dashboard: **http://localhost:4200** | API: **http://localhost:8001/api/health**

### Step 4: Analyze a Repository

```bash
# Edit .env: PROJECT_PATH=/path/to/your/repo

aicodegencrew run --preset plan          # Discover -> Plan
aicodegencrew run --preset document      # Discover -> Document (C4 + Arc42)
aicodegencrew run --preset full          # All phases
aicodegencrew index --force              # Re-index repository
```

### Alternative: OpenAI API (no local GPU needed)

Edit `.env`:
```env
LLM_PROVIDER=onprem
API_BASE=https://api.openai.com/v1
OPENAI_API_KEY=sk-your-key-here
MODEL=gpt-4o
```

---

## Tech Stack

| Category | Technology |
|----------|-----------|
| **LLM Routing** | LiteLLM (OpenAI, Ollama, Azure, Anthropic) |
| **Vector Store** | Qdrant (semantic code search) |
| **Backend** | FastAPI (async, SSE streaming) |
| **Frontend** | Angular 21 + Material Design + Tailwind |
| **Validation** | Pydantic (schema enforcement on LLM output) |
| **Observability** | Langfuse (LLM tracing) + MLflow (experiments) + Prometheus |
| **Tool Protocol** | MCP (Model Context Protocol) |
| **Build** | Hatchling (Python wheel) + Docker |
| **Testing** | pytest (745+ tests) + Playwright (E2E) |

---

## Configuration

Copy `.env.example` to `.env` and configure:

| Variable | Description | Example |
|----------|------------|---------|
| `PROJECT_PATH` | Repository to analyze | `/path/to/your/repo` |
| `MODEL` | Main LLM model | `openai/gpt-4o` |
| `API_BASE` | LLM API endpoint | `http://localhost:11434/v1` |
| `OPENAI_API_KEY` | API key | `sk-...` |
| `EMBED_MODEL` | Embedding model | `nomic-embed-text` |

See [.env.example](.env.example) for all options and [LLM Selection Guide](docs/guides/LLM_SELECTION_GUIDE.md) for model recommendations.

---

## Testing

```bash
pytest tests/ -q --ignore=tests/test_delivery.py   # All tests (745+)
pytest tests/ --ignore=tests/e2e                    # Unit + integration only
ruff check src/ tests/ ui/backend                   # Linting
```

---

## Documentation

| Document | Description |
|----------|------------|
| [SDLC Architecture](docs/SDLC_ARCHITECTURE.md) | Full system architecture with phase specs |
| [AI Expertise Reference](docs/AI_EXPERTISE_REFERENCE.md) | AI patterns and decisions in this project |
| [LLM Selection Guide](docs/guides/LLM_SELECTION_GUIDE.md) | Which model for which phase |
| [Corporate SSL Guide](docs/guides/CORPORATE_SSL_GUIDE.md) | On-prem certificate setup |
| [MCP Knowledge Server](docs/guides/MCP_KNOWLEDGE_SERVER.md) | MCP server for LLM tools |

---

## Architecture Decisions

| Decision | Why |
|----------|-----|
| **Pipeline+LLM over Multi-Agent** | CrewAI agents had 30% loop rate, 3x token overhead, unpredictable latency. Single LLM calls are faster, cheaper, reproducible. |
| **Evidence-First** | LLMs hallucinate when guessing about code. Deterministic extraction (Phase 0+1) provides ground truth. |
| **Template-First Documents** | Deterministic skeleton + LLM enrichment = guaranteed structure, no hallucinated facts. |
| **Qdrant over ChromaDB** | Production-grade vector store with payload indexes, quantization, and hybrid search support. |
| **On-Premises** | Enterprise source code must not leave the network. Zero external API calls. |

---

## License

[MIT](LICENSE) — Aymen Mastouri

---

<p align="center">
  <strong>SDLC Pilot</strong> — Evidence-First AI Architecture Analysis<br>
  <sub>&copy; 2025-2026 Aymen Mastouri</sub>
</p>
