# AICodeGenCrew

**AI-Powered Software Development Lifecycle Automation**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![CrewAI](https://img.shields.io/badge/framework-CrewAI-orange.svg)](https://crewai.com/)
[![Angular 21](https://img.shields.io/badge/dashboard-Angular%2021-red.svg)](#sdlc-dashboard)
[![On-Premises](https://img.shields.io/badge/deployment-on--premises-purple.svg)](#why-on-premises)

AICodeGenCrew automates the full Software Development Lifecycle, from architecture extraction to code generation. Point it at any repository, operate everything through the **SDLC Dashboard**, and get:

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

Open **two terminals** in the project root:

```bash
# Terminal 1 — Backend (FastAPI)
uvicorn ui.backend.main:app --reload --port 8001

# Terminal 2 — Frontend (Angular, includes proxy to backend)
cd ui/frontend && npm install && npm start
```

Open **http://localhost:4200** — the SDLC Dashboard is ready.

### 3. Upload Input Files

Go to **Input Files** in the sidebar and drag-and-drop your JIRA XML, DOCX, or Excel files into the matching category card. The `.env` is auto-configured.

Or set paths manually in `.env`:
```env
TASK_INPUT_DIR=C:\work\my-project\tasks
```

### 4. Run a Pipeline

From the Dashboard:
1. Go to **Run Pipeline** — the input file summary shows what's uploaded
2. Select a preset (e.g. `planning_only`) or pick individual phases
3. Optionally adjust environment variables
4. Click **Run Pipeline** and watch live log output

Or via CLI:
```bash
aicodegencrew plan                                  # Development planning
aicodegencrew run --preset architecture_workflow    # C4 + arc42 docs
aicodegencrew codegen                               # Code generation
```

---

## SDLC Dashboard

The Dashboard is the primary interface for AICodeGenCrew. Built with **Angular 21** + **FastAPI**.

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

**Key capabilities:**
- **File upload** with drag-and-drop, extension validation, 4 input categories
- **Structured plan viewer** — overview card with complexity/effort/risk metrics, implementation steps, parsed component chips, full upgrade migration sequence with severity badges and per-step affected files, test strategy, collapsible security/validation/error handling details, rendered JIRA context
- **Code diff viewer** — per-file expandable diffs with green/red line coloring, action chips (created/modified/deleted), language badges
- **Git branch management** — list `codegen/*` branches with file count, report links, and delete action
- **Pipeline reset** — per-phase and full pipeline reset with cascade propagation, confirm dialog with cascade preview
- **Persistent run history** — append-only JSONL (`logs/run_history.jsonl`) with Run/Reset type tracking, legacy `run_report.json` fallback
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

4-layer pipeline with 8 phases:

```
KNOWLEDGE (no LLM)          REASONING (hybrid)           EXECUTION (hybrid)
Phase 0: Indexing        ->  Phase 2: Analysis        ->  Phase 5: Code Generation
Phase 1: Facts           ->  Phase 3: Synthesis (C4)  ->  Phase 6: Test Gen (planned)
                             Phase 4: Planning         ->  Phase 7: Deploy (planned)
```

| Phase | Name | LLM | Description |
|:-----:|------|:---:|-------------|
| 0 | Indexing | No | Vector-index repository into ChromaDB |
| 1 | Facts | No | Deterministic extraction: components, relations, interfaces |
| 2 | Analysis | Yes | Multi-agent analysis (domain, workflow, quality) |
| 3 | Synthesis | Yes | C4 diagrams + arc42 chapters + DrawIO |
| 4 | Planning | Hybrid | 4 deterministic stages + 1 LLM call (18-40s) |
| 5 | Code Gen | Hybrid | Strategy pattern per task type, git branch isolation |
| 6 | Test Gen | - | Planned |
| 7 | Deploy | - | Planned |

> Full specification: [AI SDLC Architecture](docs/AI_SDLC_ARCHITECTURE.md)

### Data Flow

```
Repository ─► Phase 0 ─► knowledge/phase0_indexing/  (ChromaDB)
             Phase 1 ─► knowledge/phase1_facts/      (architecture_facts.json)
             Phase 2 ─► knowledge/phase2_analysis/    (analyzed_architecture.json)
             Phase 3 ─► knowledge/phase3_synthesis/   (C4 + arc42 + DrawIO)
             Phase 4 ─► knowledge/phase4_planning/    (task_plan.json)
             Phase 5 ─► Git branch codegen/{task_id}  + knowledge/phase5_codegen/
```

---

## Why On-Premises?

Enterprise code contains sensitive IP and customer data. AICodeGenCrew runs **entirely on your infrastructure**:

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
| `OUTPUT_BASE_DIR` | Base for all outputs | `.` |

> Full variable reference: [.env.example](.env.example)

### Presets

| Preset | Phases | Use Case |
|--------|--------|----------|
| `planning_only` | 0, 1, 2, 4 | Development planning (most common) |
| `architecture_workflow` | 0 – 3 | C4 + arc42 documentation |
| `architecture_full` | 0 – 4 | Architecture + planning |
| `codegen_only` | 0, 1, 2, 4, 5 | Planning + code generation |
| `facts_only` | 0, 1 | Deterministic facts (no LLM) |
| `full_pipeline` | 0 – 7 | All phases end-to-end |

---

## CLI Reference

```bash
aicodegencrew [--env <path>] <command> [options]
```

| Command | Description |
|---------|-------------|
| `plan` | Development planning (Phases 0+1+2+4) |
| `codegen` | Code generation (Phases 0+1+2+4+5) |
| `run --preset <name>` | Run a preset |
| `run --phases <p1> <p2>` | Run specific phases |
| `index` | Index repository only |
| `list` | Show phases and presets |

Common options: `--repo-path`, `--index-mode`, `--git-url`, `--branch`, `--config`, `--clean`

> Full CLI reference: [User Guide](docs/USER_GUIDE.md)

---

## Task Inputs (Phase 4)

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

Output: `knowledge/phase4_planning/{task_id}_plan.json` with affected components, implementation steps, test/security/validation strategies.

---

## Output Artifacts

```
<OUTPUT_BASE_DIR>/
├── knowledge/
│   ├── phase0_indexing/     # Phase 0: ChromaDB vector store
│   ├── phase1_facts/        # Phase 1: architecture_facts.json, evidence_map.json
│   ├── phase2_analysis/     # Phase 2: analyzed_architecture.json
│   ├── phase3_synthesis/    # Phase 3: c4/, arc42/ (C4 diagrams + arc42 chapters)
│   ├── phase4_planning/     # Phase 4: {task_id}_plan.json
│   ├── phase5_codegen/      # Phase 5: {task_id}_report.json
│   └── run_report.json      # Pipeline run summary
├── architecture-docs/       # Phase 3 export (Markdown + Confluence + AsciiDoc + HTML)
└── logs/
    ├── current.log
    ├── metrics.jsonl        # Structured metrics
    └── run_history.jsonl    # Persistent run history (append-only)
```

---

## Deployment

AICodeGenCrew is **Capgemini proprietary** software. Three delivery modes:

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

600+ tests, no LLM or network required (except `tests/e2e/`).

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
│   ├── frontend/                #   Angular 21 SPA (9 pages, Material + Tailwind)
│   ├── backend/                 #   FastAPI (11 routers, SSE streaming, file upload, reset)
│   └── docker-compose.ui.yml
├── src/aicodegencrew/
│   ├── cli.py                   # CLI entry point
│   ├── orchestrator.py          # Phase orchestration
│   ├── crews/                   # AI Agent Workflows (Phases 2-3)
│   ├── pipelines/               # Deterministic Pipelines (Phases 0, 1, 4, 5)
│   ├── shared/                  # Validation, models, utilities
│   └── mcp/                     # Model Context Protocol server
├── config/phases_config.yaml
├── tests/                       # 600+ tests
├── docs/                        # Architecture docs + diagrams
├── Dockerfile                   # Multi-stage (no source in final image)
└── docker-compose.yml
```

---

## License

**Copyright 2024-2026 Capgemini** — Proprietary and confidential.

---

<p align="center">
  Built with <a href="https://crewai.com/">CrewAI</a> &middot; Powered by local LLMs &middot; Made for enterprise<br>
  <sub>&copy; Capgemini. All rights reserved</sub>
</p>
