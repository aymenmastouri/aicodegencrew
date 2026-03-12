# SDLC Pilot

> **Proprietary Software**
> This repository contains software created by Aymen Mastouri (Capgemini).
> No internal or external usage is permitted without explicit written agreement.

**AI-Powered Development Lifecycle Automation**

[![Version](https://img.shields.io/badge/version-0.7.2-blue.svg)](#changelog)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![CrewAI](https://img.shields.io/badge/CrewAI-1.9.3-orange.svg)](https://crewai.com/)
[![Angular 21](https://img.shields.io/badge/dashboard-Angular%2021-red.svg)](#sdlc-dashboard)
[![Tests](https://img.shields.io/badge/tests-781%20passed-brightgreen.svg)](#testing)
[![On-Premises](https://img.shields.io/badge/deployment-on--premises-purple.svg)](#why-on-premises)

SDLC Pilot automates the full Software Development Lifecycle, from architecture extraction to code generation. It consists of two parts:

1. **SDLC Dashboard** (Web UI) — the primary interface for running pipelines, uploading tasks, browsing results
2. **Core Pipeline** (CLI) — can run independently without the Dashboard

Runs entirely on your infrastructure. No data leaves your network.

---

## 1. Quick Start (Docker — empfohlen)

Du brauchst nur **2 Programme** auf deinem Rechner:

1. **Git** — [Download](https://git-scm.com/downloads) (bei Capgemini meist vorinstalliert)
2. **Docker Desktop** — [Download](https://www.docker.com/products/docker-desktop)

### Schritt 1: Repository herunterladen

Öffne ein Terminal (Windows: PowerShell oder CMD) und tippe:

```
git clone https://bnotkca.pl.s2-eu.capgemini.com/gitlab/ai-group/aicodegencrew.git
cd aicodegencrew
```

### Schritt 2: Konfiguration

```
copy .env.example .env
```

Öffne die Datei `.env` mit einem Texteditor (Rechtsklick → "Öffnen mit" → Notepad).
Suche die Zeile:
```
OPENAI_API_KEY=sk-your-api-key-here
```
Ersetze `sk-your-api-key-here` mit dem echten API-Key (bekommst du vom Team-Lead).
Speichern und schließen.

### Schritt 3: Starten

Stelle sicher, dass **Docker Desktop gestartet** ist (blaues Wal-Icon im System-Tray).

Dann im Terminal:

| Windows CMD / PowerShell | Git Bash / Linux / macOS |
|--------------------------|--------------------------|
| `start.bat` | `./start.sh` |

Beim ersten Mal dauert es **2-3 Minuten** (Downloads). Danach startet es in Sekunden.

### Schritt 4: Dashboard öffnen

Öffne im Browser: **http://localhost**

Fertig!

### Stoppen / Logs

| Aktion | Windows | Git Bash |
|--------|---------|----------|
| Stoppen | `start.bat stop` | `./start.sh stop` |
| Logs anzeigen | `start.bat logs` | `./start.sh logs` |

---

## 2. Installation für Entwickler (Python + Node)

> Nur nötig wenn du am Code mitarbeiten willst. Für die Demo reicht Docker (siehe oben).

### Quick Start for Developers (Python + Node)

#### Prerequisites

| Service | Purpose | How to check | Required? |
|---------|---------|--------------|-----------|
| **Python 3.10-3.12** | Core pipeline | `python --version` | Yes |
| **Node.js 18+** | Dashboard frontend | `node --version` | Yes |
| **Ollama** | Embeddings (Phase 0) | `curl http://127.0.0.1:11434/api/tags` | Only for pipeline |
| **LLM API** | AI phases (2-8) | `curl $API_BASE/v1/models` | Only for pipeline |

> Ollama and LLM API are **not needed** to start the Dashboard UI.
> They are only required when running actual pipeline phases.

#### Setup (copy-paste)

```bash
# 1. Clone & enter
git clone <repo-url> aicodegencrew && cd aicodegencrew

# 2. Python environment
python -m venv .venv
.venv\Scripts\activate                            # Windows
# source .venv/bin/activate                       # Linux/macOS
pip install -e ".[dev,parsers]"

# 3. Configuration
cp .env.example .env
# Edit .env: set PROJECT_PATH, OPENAI_API_KEY, and verify API_BASE

# 4. Frontend dependencies (one-time)
cd ui/frontend && npm install && cd ../..
npm install                                       # root: installs concurrently

# 5. Start Dashboard
npm run dev                                       # opens http://localhost:4200

# 6. (Optional) Embeddings for pipeline
# ollama pull nomic-embed-text:latest
```

### Verify Setup

After `npm run dev`, check:
- Dashboard: http://localhost:4200
- Backend health: http://localhost:8001/api/health
- Setup status: http://localhost:8001/api/health/setup-status

---

## 3. SDLC Dashboard (Web UI)

The Dashboard is the primary interface. It runs a **FastAPI backend** (port 8001) and an **Angular frontend** (port 4200).

### Starting the Dashboard

**Option A: npm scripts** (from project root)
```bash
npm run dev              # starts backend + frontend together
```

**Option B: dev.sh script** (recommended for Git Bash)
```bash
./scripts/dev.sh         # restart (stop + start)
./scripts/dev.sh start   # start only
./scripts/dev.sh status  # check if running
```

**Option C: manual** (two terminals)
```bash
# Terminal 1: Backend
cd ui/backend && python main.py

# Terminal 2: Frontend (MUST use npm start for proxy!)
cd ui/frontend && npm start
```

> **IMPORTANT**: Always use `npm start` for the frontend, never `ng serve` directly.
> `npm start` includes `--proxy-config proxy.conf.json` which routes `/api/*` to the backend.
> Without it, API calls return Angular HTML instead of JSON.

Open **http://localhost:4200** — the Dashboard is ready.

### Stopping the Dashboard

| Method | Command |
|--------|---------|
| **Ctrl+C** | If started with `npm run dev` |
| **npm** | `npm run stop` |
| **dev.sh** | `./scripts/dev.sh stop` |
| **stop-dev.js** | `node scripts/stop-dev.js` |

`dev.sh stop` and `stop-dev.js` also kill orphan uvicorn worker processes that can survive a normal stop.

### Troubleshooting: Port Already in Use

If a server didn't shut down cleanly:

```bash
# Find what's using the port
netstat -ano | grep ":8001"      # backend
netstat -ano | grep ":4200"      # frontend

# Kill by PID
taskkill //F //PID <pid>

# Or kill all at once
./scripts/dev.sh stop            # safest — kills ports + orphans
node scripts/stop-dev.js         # alternative (Node.js)
```

### Troubleshooting: API Returns HTML

If the Dashboard shows errors or API calls return HTML:
- The frontend proxy is not active
- Stop the frontend and restart with `npm start` (not `ng serve`)

### Dashboard Pages

| Page | Purpose |
|------|---------|
| **Dashboard** | System health, phase status cards, active run banner |
| **Run Pipeline** | Execute presets or custom phases, live SSE log streaming |
| **Input Files** | Drag-and-drop upload for tasks, requirements, logs, reference |
| **Phases** | Phase configuration, dependencies, run/reset individual phases |
| **Knowledge** | Browse extracted facts (JSON, Markdown, AsciiDoc, HTML, Confluence, DrawIO) |
| **Reports** | Plan viewer, code diff viewer, git branch management |
| **Metrics** | LLM usage, token counts, event explorer |
| **Logs** | Real-time pipeline logs with color-coded levels |
| **Collectors** | Architecture fact collector configuration |
| **History** | Run history with stats, KPI cards, phase frequency |

### Docker Deployment (Dashboard)

```bash
docker-compose -f ui/docker-compose.ui.yml up --build
# Open http://localhost
```

---

## 4. Core Pipeline (CLI)

The pipeline can run **independently** without the Dashboard, directly from the command line.

### Quick Examples

```bash
# Index a repository
aicodegencrew index --force

# Generate development plans from JIRA tasks
aicodegencrew plan

# Full pipeline: index + extract + analyze + plan + implement
aicodegencrew codegen

# Run specific phases (skip indexing)
aicodegencrew run --phases plan implement --index-mode off --no-clean
```

### Commands

```bash
aicodegencrew [--env <path>] <command> [options]
```

| Command | Description |
|---------|-------------|
| `index` | Index repository into ChromaDB |
| `plan` | Development planning (Discover → Plan) |
| `codegen` | Code generation (Discover → Implement) |
| `run --preset <name>` | Run a preset combination of phases |
| `run --phases <p1> <p2>` | Run specific phases |
| `list` | Show available phases and presets |

### Index Modes

| Mode | Description |
|------|-------------|
| `auto` | Index only if repo changed (default) |
| `off` | Skip indexing, use existing index |
| `force` | Delete and re-index from scratch |
| `smart` | Incremental — only re-index changed files |

```bash
aicodegencrew index --force           # force re-index
aicodegencrew run --index-mode off    # skip indexing for this run
```

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

### Run Options

```bash
aicodegencrew run --preset plan \
  --repo-path C:\other\repo \         # override target repo
  --index-mode off \                  # skip indexing
  --no-clean \                        # keep existing knowledge
  --config custom_phases.yaml \       # custom phase config
  --git-url https://... \             # clone from URL
  --branch feature/xyz               # specific branch
```

### Reusing Previous Phase Outputs

To skip expensive phases (e.g. extract, analyze), copy results from a previous run:

```bash
# List archived runs
ls knowledge/archive/

# Copy extract results from archive
cp knowledge/archive/reset_YYYYMMDD_HHMMSS/extract/extract/* knowledge/extract/

# Run only later phases
aicodegencrew run --phases plan implement --index-mode off --no-clean
```

### Pipeline Reset

```bash
# Via Dashboard: Phases page → Reset All
# Via API: curl -X POST http://localhost:8001/api/reset
# Archives current knowledge/ to knowledge/archive/reset_YYYYMMDD_HHMMSS/
```

---

## 5. Configuration

Copy `.env.example` to `.env` and configure:

| Variable | Description | Example |
|----------|-------------|---------|
| `PROJECT_PATH` | Target repository to analyze | `C:\repos\my-project` |
| `TASK_INPUT_DIR` | JIRA/DOCX/Excel task files | `C:\projects\inputs\tasks` |
| `LLM_PROVIDER` | `local` (Ollama) or `onprem` (API) | `onprem` |
| `MODEL` | LLM model identifier | `gpt-oss-120b` |
| `API_BASE` | LLM API endpoint URL | `http://localhost:4000/v1` |
| `OPENAI_API_KEY` | API key for LLM | `sk-...` |
| `OLLAMA_BASE_URL` | Ollama endpoint | `http://127.0.0.1:11434` |
| `EMBED_MODEL` | Embedding model | `nomic-embed-text:latest` |
| `INDEX_MODE` | `off` / `auto` / `smart` / `force` | `auto` |
| `CODEGEN_USE_CREW` | Use CrewAI agents for code gen | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Task Inputs

| Mode | How |
|------|-----|
| **Dashboard** | Drag-and-drop on **Input Files** page. `.env` auto-configured. |
| **Manual** | Set `TASK_INPUT_DIR`, `REQUIREMENTS_DIR`, `LOGS_DIR`, `REFERENCE_DIR` in `.env` |

| Category | Extensions |
|----------|-----------|
| Tasks | `.xml` `.docx` `.pdf` `.txt` `.json` |
| Requirements | `.xlsx` `.docx` `.pdf` `.txt` `.csv` |
| Logs | `.log` `.txt` `.xlsx` `.csv` |
| Reference | `.png` `.jpg` `.svg` `.pdf` `.drawio` `.md` |

> Full variable reference: [.env.example](.env.example)

---

## 6. Architecture

### SDLC Phases

```
KNOWLEDGE (no LLM)          REASONING (hybrid)           EXECUTION (hybrid)
Discover                ->  Analyze                  ->  Implement
Extract                 ->  Document (C4 + arc42)    ->  Verify
                             Plan                     ->  Deliver (planned)
```

| # | Phase | LLM | Description |
|---|-------|:---:|-------------|
| 0 | Discover | No | Index codebase into ChromaDB, extract symbols, evidence traceability |
| 1 | Extract | No | Deterministic extraction of 16 architecture dimensions |
| 2 | Analyze | Yes | Multi-agent analysis (domain, workflow, quality) |
| 3 | Document | Yes | C4 diagrams + arc42 chapters + DrawIO |
| 4 | Plan | Hybrid | 4 deterministic stages + 1 LLM call |
| 5 | Implement | Hybrid | Team-based CrewAI: code generation + build verification with self-healing |
| 6 | Verify | Yes | Single-agent test generation per file (JUnit 5 / Angular TestBed + Jasmine) |
| 7 | Deliver | - | Planned |

### Data Flow

```
Repository --> Discover   --> knowledge/discover/    (ChromaDB + symbols + evidence)
               Extract    --> knowledge/extract/     (architecture_facts.json)
               Analyze    --> knowledge/analyze/     (analyzed_architecture.json)
               Document   --> knowledge/document/    (C4 + arc42 + DrawIO)
               Plan       --> knowledge/plan/        ({task_id}_plan.json)
               Implement  --> Git branch codegen/*   + knowledge/implement/
               Verify     --> knowledge/verify/      ({task_id}_verify.json + summary.json)
```

> Full specification: [SDLC Architecture](docs/SDLC_ARCHITECTURE.md)

---

## 7. Troubleshooting

| Problem | Solution |
|---------|----------|
| Port 8001/4200 in use | `./scripts/dev.sh stop` or `node scripts/stop-dev.js` |
| API returns HTML not JSON | Restart frontend with `npm start` (not `ng serve`) |
| LLM Connection error | Check VPN: `curl $API_BASE/v1/models` (401 = OK, refused = no VPN) |
| Ollama not running | `ollama serve` then `curl http://127.0.0.1:11434/api/tags` |
| Indexing hangs | Remove stale lock: `rm knowledge/discover/.index.lock` |
| Build fails with VPN | Known issue: VPN can break Gradle/npm builds. Run LLM phases with VPN, build without. |
| Orphan uvicorn workers | `./scripts/dev.sh stop` kills them automatically |
| Pipeline crash | Dashboard stays alive (subprocess isolation). Check `logs/current.log` |

---

## 8. Scripts Reference

| Script | Description |
|--------|-------------|
| `scripts/dev.sh` | Start/stop/restart/status of Dashboard dev servers |
| `scripts/stop-dev.js` | Stop Dashboard servers + kill orphan processes |
| `scripts/build_release.py` | Build release package (wheel + changelog + Docker) |
| `dist/release/install.sh` | Install from wheel (end-user) |
| `dist/release/uninstall.sh` | Uninstall package |

### dev.sh usage

```bash
./scripts/dev.sh              # restart (stop + start)
./scripts/dev.sh start        # start backend + frontend
./scripts/dev.sh stop         # stop all + kill orphans
./scripts/dev.sh status       # check if running
```

### build_release.py usage

```bash
python scripts/build_release.py                         # build current version
python scripts/build_release.py --bump patch            # 0.5.0 -> 0.5.1
python scripts/build_release.py --bump minor --tag      # 0.5.0 -> 0.6.0 + git tag
python scripts/build_release.py --bump patch --docker   # + Docker image
```

---

## 9. Deployment

SDLC Pilot is **proprietary** software. Three delivery modes:

| Mode | Command | Source Visible |
|------|---------|:--------------:|
| **Wheel** | `pip install aicodegencrew-X.Y.Z.whl` | No |
| **Docker** | `docker-compose run aicodegencrew plan` | No |
| **Dev** | `pip install -e .` | Yes (internal) |

> Details: [Delivery Guide](docs/guides/DELIVERY_GUIDE.md)

---

## 10. Testing

815+ tests, no LLM or network required (except `tests/e2e/`).

```bash
pip install -e ".[dev]"

# Full suite (exkl. bekannter Langläufer)
pytest tests/ -q --ignore=tests/test_delivery.py

# Nur unit + integration
pytest tests/ --ignore=tests/e2e

# Nur Collector-Unit-Tests (~5s)
pytest tests/unit/collectors/ -v

# Linting (Python + Backend)
ruff check src/ tests/ ui/backend
```

---

## 11. Documentation

| Document | Description |
|----------|-------------|
| [SDLC Architecture](docs/SDLC_ARCHITECTURE.md) | Cross-architecture parent + links to all phase docs |
| [Phase 5 — Implement](docs/phases/phase-5-implement/README.md) | Code generation + build verify architecture |
| [User Guide](docs/guides/USER_GUIDE.md) | Installation, configuration, CLI, troubleshooting |
| [Delivery Guide](docs/guides/DELIVERY_GUIDE.md) | Release process and deployment |
| [MCP Knowledge Server](docs/guides/MCP_KNOWLEDGE_SERVER.md) | MCP server for CrewAI tools |
| [Phase Configuration](config/phases_config.yaml) | Phase definitions and presets |
| [Environment Template](.env.example) | All configurable variables |

---

## Project Structure

```
aicodegencrew/
├── ui/                          # SDLC Dashboard
│   ├── frontend/                #   Angular 21 (port 4200)
│   ├── backend/                 #   FastAPI (port 8001)
│   └── docker-compose.ui.yml
├── src/aicodegencrew/           # Core Pipeline
│   ├── cli.py                   #   CLI entry point
│   ├── orchestrator.py          #   Phase orchestration
│   ├── pipelines/               #   Discover, Extract
│   ├── crews/                   #   Analyze, Document, Verify
│   ├── hybrid/                  #   Plan, Implement (pipeline + CrewAI)
│   ├── shared/                  #   Utilities, tools, validation
│   │   ├── dependency_checker.py  #   Phase dependency resolution (extracted)
│   │   ├── phase_git_handler.py   #   Post-phase git auto-commit (extracted)
│   │   ├── schema_version.py      #   Phase JSON schema versioning
│   │   └── tools/               #   CrewAI tool implementations
│   └── mcp/                     #   MCP knowledge server
├── scripts/                     # Dev scripts (dev.sh, stop-dev.js, build_release.py)
├── config/phases_config.yaml    # Phase definitions
├── knowledge/                   # Phase outputs (auto-generated)
├── tests/                       # 815+ tests
│   ├── unit/collectors/         #   Collector unit tests (no LLM)
│   ├── integration/             #   Phase integration tests
│   └── e2e/                     #   End-to-end tests (requires LLM)
├── docs/                        # Architecture docs + guides
└── .env                         # Configuration
```

---

## License

**Copyright 2026 Aymen Mastouri** — Proprietary and confidential.

---

<p align="center">
  <strong>SDLC Pilot</strong> &mdash; Built with <a href="https://crewai.com/">CrewAI</a> &middot; Powered by local LLMs &middot; Made for enterprise<br>
  <sub>&copy; 2026 Aymen Mastouri. All rights reserved</sub>
</p>
