# SDLC Pilot

**AI-Powered Development Lifecycle Automation**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![CrewAI](https://img.shields.io/badge/framework-CrewAI-orange.svg)](https://crewai.com/)
[![Angular 21](https://img.shields.io/badge/dashboard-Angular%2021-red.svg)](#sdlc-dashboard)
[![On-Premises](https://img.shields.io/badge/deployment-on--premises-purple.svg)](#why-on-premises)

SDLC Pilot automates the full Software Development Lifecycle, from architecture extraction to code generation. Point it at any repository, operate everything through the **SDLC Dashboard**, and get:

- Architecture facts, C4 models, arc42 documentation
- Development plans from JIRA/DOCX/Excel tasks
- Generated code on isolated git branches
- Live pipeline monitoring with real-time log streaming

Runs entirely on your infrastructure. No data leaves your network.

---

## Quick Start

### 1. Install

```bash
git clone <repo-url> aicodegencrew && cd aicodegencrew
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -e ".[dev,parsers]"
cp .env.example .env                              # edit with your settings
ollama pull all-minilm:latest && ollama serve     # embeddings
```

### 2. Launch the Dashboard

```bash
npm install          # one-time: installs concurrently
npm run dev          # starts backend :8001 + frontend :4200 together
```

Open **http://localhost:4200** — the SDLC Dashboard is ready.

To stop both servers: `Ctrl+C` or from another terminal:
```bash
npm run stop
```

> **Manual start** (if needed): `npm run dev:backend` and `npm run dev:frontend` in separate terminals.

### 3. Upload Input Files

Go to **Input Files** in the sidebar and drag-and-drop your JIRA XML, DOCX, or Excel files into the matching category card. The `.env` is auto-configured.

Or set paths manually in `.env`:
```env
TASK_INPUT_DIR=C:\work\my-project\tasks
```

### 4. Run a Pipeline

From the Dashboard:
1. Go to **Run Pipeline** — the input file summary shows what's uploaded
2. Select a preset (e.g. `plan`) or pick individual phases
3. Optionally adjust environment variables
4. Click **Run Pipeline** and watch live log output

Or via CLI:
```bash
aicodegencrew plan                                  # Development planning
aicodegencrew run --preset document                 # C4 + arc42 docs
aicodegencrew codegen                               # Code generation
```

---

## SDLC Dashboard

The Dashboard is the primary interface for SDLC Pilot. Built with **Angular 21** + **FastAPI**.

| Page | Purpose |
|------|---------|
| **Dashboard** | System health, pipeline status with phase cards, active run banner, quick links |
| **Run Pipeline** | Execute presets or custom phases, edit env vars, live SSE log streaming, input file summary, run history with type column (Run/Reset) |
| **Input Files** | Drag-and-drop upload for tasks, requirements, logs, reference materials. Auto-configures `.env` |
| **Phases** | Phase configuration, dependencies, run/reset individual phases, Reset All button |
| **Knowledge** | Multi-tab file browser with rendered previews (JSON, Markdown, AsciiDoc, HTML, Confluence, DrawIO) |
| **Reports** | 3-tab view: structured plan viewer (overview metrics, migration sequence, component chips), code diff viewer (colored diffs), git branch management |
| **Metrics** | Explore `metrics.jsonl` events with filters |
| **Logs** | Tail application logs with color-coded levels |
| **Collectors** | Manage and configure data collectors for pipeline input |
| **History** | Run history with stats (success rate, avg duration, token usage), phase frequency, KPI cards |

**Key capabilities:**
- **File upload** with drag-and-drop, extension validation, 4 input categories
- **Structured plan viewer** — overview card with complexity/effort/risk metrics, implementation steps, parsed component chips, full upgrade migration sequence with severity badges and per-step affected files, test strategy, collapsible security/validation/error handling details, rendered JIRA context
- **Code diff viewer** — per-file expandable diffs with green/red line coloring, action chips (created/modified/deleted), language badges
- **Git branch management** — list `codegen/*` branches with file count, report links, and delete action
- **Pipeline reset** — per-phase and full pipeline reset with cascade propagation, confirm dialog with cascade preview
- **Persistent run history** — append-only JSONL (`logs/run_history.jsonl`) with Run/Reset type tracking
- **Document rendering** — JSON syntax highlighting, Markdown, AsciiDoc, HTML, Confluence wiki
- Real-time log streaming via Server-Sent Events (SSE)
- Environment configuration editing before each run
- Phase-level progress timeline with durations
- Run history with Run/Reset type column, status tracking
- Pipeline cancellation (SIGTERM with SIGKILL fallback)
- Subprocess isolation — pipeline crash won't crash the Dashboard

### Docker Deployment

```bash
docker-compose -f ui/docker-compose.ui.yml up --build
# Open http://localhost
```

---

## Architecture

3-layer pipeline with 8 phases:

```
KNOWLEDGE (no LLM)          REASONING (hybrid)           EXECUTION (hybrid)
Discover                ->  Analyze                  ->  Implement
Extract                 ->  Document (C4 + arc42)    ->  Verify (planned)
                             Plan                     ->  Deliver (planned)
```

| Name | LLM | Description |
|------|:---:|-------------|
| Discover | No | Vector-index repository into ChromaDB |
| Extract | No | Deterministic extraction: components, relations, interfaces |
| Analyze | Yes | Multi-agent analysis (domain, workflow, quality) |
| Document | Yes | C4 diagrams + arc42 chapters + DrawIO |
| Plan | Hybrid | 4 deterministic stages + 1 LLM call (18-40s) |
| Implement | Hybrid | Strategy pattern per task type, cascade multi-task on single branch |
| Verify | - | Planned |
| Deliver | - | Planned |

> Full specification: [AI SDLC Architecture](docs/AI_SDLC_ARCHITECTURE.md)

### Data Flow

```
Repository ─► Discover   ─► knowledge/discover/    (ChromaDB)
             Extract    ─► knowledge/extract/     (architecture_facts.json)
             Analyze    ─► knowledge/analyze/     (analyzed_architecture.json)
             Document   ─► knowledge/document/    (C4 + arc42 + DrawIO)
             Plan       ─► knowledge/plan/        (task_plan.json)
             Implement  ─► Git branch codegen/batch-*  + knowledge/implement/
```

---

## Why On-Premises?

Enterprise code contains sensitive IP and customer data. SDLC Pilot runs **entirely on your infrastructure**:

- **Local models** via [Ollama](https://ollama.com/) (e.g. `qwen2.5-coder`, `llama3`)
- **On-prem API endpoints** (OpenAI-compatible: vLLM, TGI)
- **Local embeddings** via Ollama (`all-minilm`)

No data ever leaves your network.

---

## Configuration

Copy `.env.example` to `.env` and configure. Key variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `PROJECT_PATH` | Repository to analyze | `C:\repos\my-project` |
| `TASK_INPUT_DIR` | Folder with JIRA/DOCX/Excel tasks (outside repo) | `C:\projects\inputs` |
| `LLM_PROVIDER` | `local` (Ollama) or `onprem` (API endpoint) | `onprem` |
| `MODEL` | LLM model identifier | `gpt-oss-120b` |
| `API_BASE` | LLM API endpoint URL | `http://localhost:11434/v1` |
| `INDEX_MODE` | `off` / `auto` / `smart` / `force` | `auto` |

> Full variable reference: [.env.example](.env.example)

### Presets

| Preset | Phases | Use Case |
|--------|--------|----------|
| `index` | Discover | Repository indexing only |
| `scan` | Discover + Extract | Deterministic facts (no LLM) |
| `analyze` | Discover → Analyze | AI analysis |
| `document` | Discover → Document | C4 + arc42 documentation |
| `plan` | Discover → Plan | Development planning (most common) |
| `develop` | Discover → Implement | Planning + code generation |
| `architect` | Discover → Plan (no code) | Architecture + planning |
| `full` | All phases | End-to-end |

---

## CLI Reference

```bash
aicodegencrew [--env <path>] <command> [options]
```

| Command | Description |
|---------|-------------|
| `plan` | Development planning (Discover → Plan) |
| `codegen` | Code generation (Discover → Implement) |
| `run --preset <name>` | Run a preset |
| `run --phases <p1> <p2>` | Run specific phases |
| `index` | Index repository only |
| `list` | Show phases and presets |

Common options: `--repo-path`, `--index-mode`, `--git-url`, `--branch`, `--config`, `--clean`

> Full CLI reference: [User Guide](docs/USER_GUIDE.md)

---

## Task Inputs (Plan phase)

Two ways to provide input files:

| Mode | How |
|------|-----|
| **Dashboard** | Go to **Input Files**, drag-and-drop into category cards. `.env` auto-configured. |
| **Manual** | Set `TASK_INPUT_DIR`, `REQUIREMENTS_DIR`, `LOGS_DIR`, `REFERENCE_DIR` in `.env` |

| Category | Extensions | Purpose |
|----------|-----------|---------|
| **Tasks** | `.xml` `.docx` `.pdf` `.txt` `.json` | JIRA exports, tickets |
| **Requirements** | `.xlsx` `.docx` `.pdf` `.txt` `.csv` | Requirement docs, specs |
| **Logs** | `.log` `.txt` `.xlsx` `.csv` | Application logs |
| **Reference** | `.png` `.jpg` `.svg` `.pdf` `.drawio` `.md` | Mockups, diagrams |

Output: `knowledge/plan/{task_id}_plan.json` with affected components, implementation steps, test/security/validation strategies.

---

## Output Artifacts

```
./
├── knowledge/
│   ├── discover/            # Discover: ChromaDB vector store
│   ├── extract/             # Extract: architecture_facts.json, evidence_map.json
│   ├── analyze/             # Analyze: analyzed_architecture.json
│   ├── document/            # Document: c4/, arc42/ (C4 diagrams + arc42 chapters)
│   ├── plan/                # Plan: {task_id}_plan.json
│   └── implement/           # Implement: {task_id}_report.json
├── architecture-docs/       # Document export (Markdown + Confluence + AsciiDoc + HTML)
└── logs/
    ├── current.log
    ├── metrics.jsonl        # Structured metrics
    └── run_history.jsonl    # Persistent run history (append-only)
```

---

## Deployment

SDLC Pilot is **Capgemini proprietary** software. Three delivery modes:

| Mode | Command | Source Visible |
|------|---------|:--------------:|
| **Wheel** | `pip install aicodegencrew-X.Y.Z.whl` | No |
| **Docker** | `docker-compose run aicodegencrew plan` | No |
| **Dev** | `pip install -e .` | Yes (internal) |

```bash
# Build release (wheel + Docker + changelog)
python scripts/build_release.py --bump patch --tag --docker
```

> Details: [Delivery Guide](docs/DELIVERY_GUIDE.md)

---

## Testing

780+ tests, no LLM or network required (except `tests/e2e/`).

```bash
pip install -e ".[dev]"
pytest tests/ -v                    # Full suite (~17s)
pytest tests/ --ignore=tests/e2e    # Unit + integration only
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [AI SDLC Architecture](docs/AI_SDLC_ARCHITECTURE.md) | Full architecture specification |
| [User Guide](docs/USER_GUIDE.md) | Installation, configuration, CLI, troubleshooting |
| [Delivery Guide](docs/DELIVERY_GUIDE.md) | Release process and deployment |
| [Phase Configuration](config/phases_config.yaml) | Phase definitions and presets |
| [Environment Template](.env.example) | All configurable variables |

---

## Project Structure

```
aicodegencrew/
├── ui/                          # SDLC Dashboard (primary interface)
│   ├── frontend/                #   Angular 21 SPA (10 pages, Material + Tailwind)
│   ├── backend/                 #   FastAPI (11 routers, SSE streaming, file upload, reset)
│   └── docker-compose.ui.yml
├── src/aicodegencrew/
│   ├── cli.py                   # CLI entry point
│   ├── orchestrator.py          # Phase orchestration
│   ├── crews/                   # AI Agent Workflows (Analyze + Document)
│   ├── pipelines/               # Deterministic Pipelines (Discover, Extract, Plan, Implement)
│   ├── shared/                  # Validation, models, utilities
│   └── mcp/                     # Model Context Protocol server
├── config/phases_config.yaml
├── tests/                       # 780+ tests
├── docs/                        # Architecture docs + diagrams
├── Dockerfile                   # Multi-stage (no source in final image)
└── docker-compose.yml
```

---

## License

**Copyright 2024-2026 Capgemini** — Proprietary and confidential.

---

<p align="center">
  <strong>SDLC Pilot</strong> &mdash; Built with <a href="https://crewai.com/">CrewAI</a> &middot; Powered by local LLMs &middot; Made for enterprise<br>
  <sub>&copy; Capgemini. All rights reserved</sub>
</p>
