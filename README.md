# AICodeGenCrew

**AI-Powered Software Development Lifecycle Automation**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![CrewAI](https://img.shields.io/badge/framework-CrewAI-orange.svg)](https://crewai.com/)
[![Capgemini](https://img.shields.io/badge/license-Capgemini-green.svg)](LICENSE)
[![On-Premises](https://img.shields.io/badge/deployment-on--premises-purple.svg)](#why-on-premises)

AICodeGenCrew is a fully local, on-premises AI-powered toolkit for end-to-end Software Development Lifecycle (SDLC) automation. Point it at any repository and it will:

1. **Extract architecture facts** — deterministic code analysis, no LLM needed (components, relations, interfaces, endpoints)
2. **Analyze architecture patterns** — AI-powered domain, workflow, and quality analysis (Map-Reduce for scale)
3. **Generate C4 model + arc42 documentation** — complete C4 diagrams + all 12 arc42 chapters with DrawIO diagrams
4. **Create development plans** — hybrid pipeline (4 deterministic stages + 1 LLM call, 18-40s) for JIRA tasks, bugfixes, upgrades
5. **Export to multiple formats** — Markdown, Confluence Wiki Markup, AsciiDoc, HTML — ready for your documentation toolchain

All backed by real code evidence, running entirely on your infrastructure. No data leaves your network.

---

## Table of Contents

- [Key Features](#key-features)
- [Why On-Premises?](#why-on-premises)
- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Deployment](#deployment)
- [Configuration](#configuration)
- [CLI Reference](#cli-reference)
- [Pipeline Phases](#pipeline-phases)
- [Output Artifacts](#output-artifacts)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Evidence-Based Documentation** | Every claim in generated docs is traceable to source code evidence. No hallucinations. |
| **C4 Model + arc42** | Generates complete C4 diagrams (Context, Container, Component, Deployment) and all 12 arc42 chapters. |
| **Development Planning** | Hybrid pipeline (4 deterministic + 1 LLM stage, 18-40s) generates implementation plans from JIRA/DOCX/Excel tasks. Finds affected components via RAG, matches test/security/validation patterns. |
| **Multi-Format Export** | Automatic conversion to Confluence Wiki Markup, AsciiDoc, and HTML alongside Markdown. Arc42 ToC in EN/DE. |
| **Deterministic Fact Extraction** | Phase 1 extracts architecture facts without any LLM — pure code analysis. |
| **Multi-Agent AI Crews** | Specialized AI agents (architects, analysts) collaborate via CrewAI for analysis and synthesis. |
| **Map-Reduce for Scale** | Large repositories (500+ components) are split by container and analyzed in parallel. |
| **Mini-Crews Pattern** | Each documentation section gets a fresh LLM context window — no context overflow. |
| **Checkpoint & Resume** | If a crew fails, re-running automatically skips completed work. |
| **Run Reports** | Every pipeline run exports `knowledge/run_report.json` with phase status, durations, output files. |
| **MCP Integration** | Model Context Protocol server provides live architecture queries to agents. |
| **DrawIO Diagrams** | Generates machine-readable `.drawio` diagrams alongside Markdown documentation. |
| **Configurable Output** | `OUTPUT_BASE_DIR` redirects all outputs (`knowledge/`, `logs/`, docs) to any directory. |
| **Fully On-Premises** | Runs with local LLMs (Ollama) or on-prem endpoints. No data leaves your network. |

---

## Why On-Premises?

Enterprise software often contains sensitive intellectual property, customer data, or security-critical code. Sending this data to external AI services may violate compliance requirements, data protection regulations, or internal security policies.

AICodeGenCrew is designed to run **entirely on your infrastructure** with your own LLMs — no data ever leaves your network. It supports:

- **Local models** via [Ollama](https://ollama.com/) (e.g., `qwen2.5-coder`, `llama3`)
- **On-prem API endpoints** compatible with the OpenAI API format (e.g., vLLM, TGI)
- **Local embeddings** via Ollama (`all-minilm`) for vector indexing

---

## Architecture Overview

The system follows a **4-Layer Architecture** with 8 pipeline phases (0-7):

| Layer | Phases | Purpose | LLM Required |
|-------|--------|---------|:------------:|
| **Knowledge** | 0 – 1 | Deterministic facts extraction | No |
| **Reasoning** | 2 – 4 | AI-powered analysis, synthesis, and planning | Hybrid |
| **Execution** | 5 – 7 | Code generation, testing, and deployment | Yes |

> For the full architecture specification, see [AI SDLC Architecture](docs/AI_SDLC_ARCHITECTURE.md).
> DrawIO diagrams are in [docs/diagrams/](docs/diagrams/).

### Data Flow

```
Repository
  │
  ├─ Phase 0: Indexing ──────────────► ChromaDB (vector store)
  │
  ├─ Phase 1: Facts Extraction ─────► architecture_facts.json + evidence_map.json
  │
  ├─ Phase 2: Analysis (AI) ────────► analyzed_architecture.json
  │
  ├─ Phase 3: Synthesis (AI) ───────► C4 docs + arc42 chapters + DrawIO diagrams
  │
  └─ Phase 4: Planning (Hybrid) ────► task_plan.json (18-40s, 100% data usage)
```

---

## Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| **Python** | 3.10 – 3.12 | Runtime |
| **Ollama** | latest | Local embeddings (`all-minilm`) and optional local LLMs |
| **Git** | any | Repository access |

**Optional:**
- On-prem LLM API endpoint (OpenAI-compatible) for analysis/synthesis phases
- 16 GB+ RAM recommended for large repositories

---

## Installation

### 1. Clone the Repository

```bash
git clone <repo-url> aicodegencrew
cd aicodegencrew
```

### 2. Create Virtual Environment

```bash
python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Core dependencies
pip install -e .

# With development tools
pip install -e ".[dev]"

# With parser support (DOCX, Excel)
pip install -e ".[parsers]"

# Or install everything
pip install -e ".[dev,parsers]"
```

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your settings (see [Configuration](#configuration) below).

### 5. Start Ollama (for embeddings)

```bash
ollama pull all-minilm:latest
ollama serve
```

### 6. Verify Installation

```bash
python -m aicodegencrew list
```

---

## Quick Start

```bash
# Option A: Local repository — set PROJECT_PATH in .env
#   PROJECT_PATH=/path/to/your/repo

# Option B: Git URL — clones automatically into .cache/repos/
#   GIT_REPO_URL=https://gitlab.example.com/team/project.git
#   GIT_BRANCH=         # empty = auto-detect main/master

# Development Planning (Phases 0+1+2+4) — most common
aicodegencrew plan

# With custom .env file (e.g. Docker, wheel distribution)
aicodegencrew --env /path/to/project.env plan

# Full architecture documentation - C4 + arc42 (Phases 0-3, excludes planning)
aicodegencrew run --preset architecture_workflow

# Architecture + development planning (Phases 0-4, includes planning)
aicodegencrew run --preset architecture_full

# Or specify the Git URL directly via CLI
aicodegencrew run --preset architecture_workflow --git-url https://gitlab.example.com/team/project.git
```

---

## Deployment

AICodeGenCrew is **Capgemini proprietary** software. Source code must not be distributed to end users. Three deployment modes are available:

### Option 1: Wheel Distribution (No Source Code)

```bash
# Build wheel (dev team only)
pip install build
python -m build --wheel
# -> dist/aicodegencrew-0.1.0-py3-none-any.whl

# Distribute to developers — they install with:
pip install aicodegencrew-0.1.0-py3-none-any.whl[parsers]

# Developer runs with their own .env config:
aicodegencrew --env /path/to/project.env plan
```

### Option 2: Docker (Recommended for Production)

Multi-stage Dockerfile ensures **no source code** in the final image — only the compiled wheel.

```bash
# Build image (dev team only)
docker build -t aicodegencrew:latest .

# Run with docker-compose (developer)
docker-compose run aicodegencrew plan

# Or run directly
docker run --network host \
  -v /path/to/.env:/app/.env:ro \
  -v /path/to/repo:/repo:ro \
  -v /path/to/inputs:/app/inputs/tasks:ro \
  -v ./knowledge:/app/knowledge \
  -v ./architecture-docs:/app/architecture-docs \
  -v ./.cache:/app/.cache \
  -e PROJECT_PATH=/repo \
  -e TASK_INPUT_DIR=/app/inputs/tasks \
  -e DOCS_OUTPUT_DIR=/app/architecture-docs \
  aicodegencrew:latest plan
```

### Volume Mounts (Docker)

| Mount (from `.env`) | Container Path | Mode | Purpose |
|---------------------|---------------|------|---------|
| `.env` | `/app/.env` | read-only | Configuration |
| `PROJECT_PATH` | `/repo` | read-only | Repository to analyze |
| `TASK_INPUT_DIR` | `/app/inputs/tasks` | read-only | JIRA XML, DOCX, Excel files |
| `knowledge/` | `/app/knowledge` | read-write | Internal output: facts, analysis, plans |
| `DOCS_OUTPUT_DIR` | `/app/architecture-docs` | read-write | Phase 3 export: C4 + Arc42 docs for architect |
| `.cache/` | `/app/.cache` | read-write | ChromaDB vector store |

docker-compose reads `PROJECT_PATH` and `TASK_INPUT_DIR` from your `.env` file and mounts them automatically.

### Option 3: Development Install (Internal Only)

```bash
pip install -e ".[dev,parsers]"
```

### Release Build (`scripts/build_release.py`)

Automated release builder that creates a distribution-ready package.

```bash
# Build current version (no version change)
python scripts/build_release.py

# Bump version and build
python scripts/build_release.py --bump patch          # 0.1.0 -> 0.1.1
python scripts/build_release.py --bump minor          # 0.1.0 -> 0.2.0
python scripts/build_release.py --bump major          # 0.1.0 -> 1.0.0

# Bump + git tag (commit + annotated tag vX.Y.Z)
python scripts/build_release.py --bump patch --tag

# Full release: bump + tag + Docker image
python scripts/build_release.py --bump patch --tag --docker

# Push Docker image to registry
python scripts/build_release.py --bump patch --tag --docker --push --registry registry.example.com
```

**What `--bump` does automatically:**

| Step | File | Action |
|------|------|--------|
| 1 | `pyproject.toml` | Updates `version = "X.Y.Z"` |
| 2 | `CHANGELOG.md` | Adds new version header with git commit messages since last tag |
| 3 | `docs/DELIVERY_GUIDE.md` | Updates all version references |
| 4 | `docs/USER_GUIDE.md` | Updates all version references |
| 5 | `dist/release/` | Builds wheel + assembles 8 release files |

**What `--tag` does additionally:**

| Step | Action |
|------|--------|
| 1 | `git add` all version-related files |
| 2 | `git commit -m "release: vX.Y.Z"` |
| 3 | `git tag -a vX.Y.Z -m "Release X.Y.Z"` |

**Release package output (`dist/release/`):**

```
dist/release/
├── aicodegencrew-X.Y.Z-py3-none-any.whl   # Installable wheel (no source code)
├── .env.example                             # Configuration template
├── docker-compose.yml                       # Docker setup
├── config/phases_config.yaml                # Phase configuration
├── USER_GUIDE.md                            # End-user documentation
├── CHANGELOG.md                             # Version history (auto-generated from git)
├── install.bat                              # Windows installer script
└── install.sh                               # Linux/macOS installer script
```

---

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

#### Repository & Input

| Variable | Description | Example |
|----------|-------------|---------|
| `PROJECT_PATH` | Local path to the repository to analyze | `C:\repos\my-project` |
| `TASK_INPUT_DIR` | Folder with JIRA XML / task files (outside repo!) | `C:\projects\inputs` |
| `GIT_REPO_URL` | Git HTTPS URL (optional, overrides `PROJECT_PATH`) | `https://gitlab.example.com/team/project.git` |
| `GIT_BRANCH` | Branch to checkout (empty = auto-detect main/master) | `develop` |

**Important:** `TASK_INPUT_DIR` should point to a folder **outside** the code repository. This is where you place your JIRA XML exports, DOCX requirements, Excel files, etc.

When `GIT_REPO_URL` is set, the repo is cloned into `.cache/repos/<name>/` and updated on each run.
Credentials are prompted interactively on first clone and cached in-memory only (never written to disk or logs).

#### LLM

| Variable | Description | Example |
|----------|-------------|---------|
| `LLM_PROVIDER` | LLM provider type | `local` or `onprem` |
| `MODEL` | LLM model identifier | `qwen2.5-coder:7b` or `gpt-oss-120b` |
| `API_BASE` | LLM API endpoint URL | `http://localhost:11434/v1` |

#### Embeddings (Ollama)

| Variable | Default | Description |
|----------|---------|-------------|
| `EMBED_MODEL` | `all-minilm:latest` | Ollama embedding model |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama server URL |
| `OLLAMA_TIMEOUT_S` | `300` | Ollama request timeout (seconds) |

#### Indexing

| Variable | Default | Description |
|----------|---------|-------------|
| `INDEX_MODE` | `auto` | `off` / `auto` / `force` / `smart` |
| `CHROMA_DIR` | `.cache/.chroma` | ChromaDB storage directory |
| `INDEX_EXTENSIONS` | `.java,.ts,...` | File extensions to index |
| `INDEX_EXTRA_SKIP_DIRS` | `dist,out,...` | Directories to skip during indexing |

#### Token Budget

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_LLM_INPUT_TOKENS` | `100000` | Max input tokens per LLM call |
| `MAX_LLM_OUTPUT_TOKENS` | `16000` | Max output tokens per LLM call (~12 pages per crew) |
| `LLM_CONTEXT_WINDOW` | `120000` | Total LLM context window size (gpt-oss-120b) |

#### Output & Logging

| Variable | Default | Description |
|----------|---------|-------------|
| `OUTPUT_BASE_DIR` | `.` | Base directory for ALL outputs: `knowledge/`, `logs/`, `run_report.json`, `architecture-docs/` |
| `DOCS_OUTPUT_DIR` | `<OUTPUT_BASE_DIR>/architecture-docs` | Export dir for Phase 3 docs. Auto-converts to Confluence/AsciiDoc/HTML. |
| `ARC42_LANGUAGE` | `en` | Arc42 ToC language: `en` (English) or `de` (Deutsch) |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

### Presets

Presets are predefined phase combinations defined in [`config/phases_config.yaml`](config/phases_config.yaml):

| Preset | Phases | Description |
|--------|--------|-------------|
| `indexing_only` | 0 | Index repository only |
| `facts_only` | 0 – 1 | Deterministic facts extraction (no LLM) |
| `analysis_only` | 0 – 2 | Facts + AI analysis |
| `planning_only` | 0 – 2, 4 | Development planning (skips Phase 3 synthesis) |
| `architecture_workflow` | 0 – 3 | C4 Model + arc42 documentation |
| `architecture_full` | 0 – 4 | Architecture documentation + Development Planning |
| `full_pipeline` | 0 – 7 | All phases (end-to-end SDLC) |

---

## CLI Reference

```
aicodegencrew [--env <path>] <command> [options]
```

### Global Options

| Option | Description |
|--------|-------------|
| `--env <path>` | Path to `.env` configuration file (default: `.env` in current directory) |

### Commands

| Command | Description |
|---------|-------------|
| `run` | Execute pipeline phases (presets or explicit phase list) |
| `plan` | Run development planning (shortcut for `run --preset planning_only`) |
| `index` | Run indexing only (shortcut for Phase 0) |
| `list` | List available phases and presets |

### `run` Options

| Option | Description |
|--------|-------------|
| `--preset <name>` | Run a predefined preset (see table below) |
| `--phases <p1> [p2] ...` | Run specific phases by name |
| `--index-mode <mode>` | Override `INDEX_MODE` (`off` / `auto` / `force` / `smart`) |
| `--repo-path <path>` | Override `PROJECT_PATH` from `.env` |
| `--git-url <url>` | Git HTTPS URL (overrides `GIT_REPO_URL` in `.env`) |
| `--branch <name>` | Git branch (overrides `GIT_BRANCH` in `.env`) |
| `--clean` | Clean knowledge directories before running |
| `--no-clean` | Skip auto-cleaning of knowledge directories |
| `--config <path>` | Custom path to `phases_config.yaml` |

### `plan` Options

| Option | Description |
|--------|-------------|
| `--repo-path <path>` | Override `PROJECT_PATH` from `.env` |
| `--index-mode <mode>` | Override `INDEX_MODE` (`off` / `auto` / `force` / `smart`) |
| `--config <path>` | Custom path to `phases_config.yaml` |

### `index` Options

| Option | Description |
|--------|-------------|
| `--mode <mode>`, `-m` | Indexing mode (`off` / `auto` / `force` / `smart`) |
| `--force`, `-f` | Force re-index (shortcut for `--mode force`) |
| `--smart`, `-s` | Smart incremental (shortcut for `--mode smart`) |
| `--repo <path>` | Repository path (overrides `PROJECT_PATH`) |
| `--git-url <url>` | Git HTTPS URL (overrides `GIT_REPO_URL` in `.env`) |
| `--branch <name>` | Git branch (overrides `GIT_BRANCH` in `.env`) |

### `list` Options

| Option | Description |
|--------|-------------|
| `--config <path>` | Custom path to `phases_config.yaml` |

### Index Modes

| Mode | Behavior |
|------|----------|
| `off` | Skip indexing entirely, use existing ChromaDB index |
| `auto` | Index only if repo changed (fingerprint check). Persistent state survives ChromaDB deletion |
| `smart` | Always run, but only re-embed files whose content hash changed |
| `force` | Delete ChromaDB and re-index everything from scratch |

### Examples

#### Presets (recommended)

```bash
# Development planning (Phases 0+1+2+4) — most common
aicodegencrew plan
# equivalent to: aicodegencrew run --preset planning_only

# With custom .env file
aicodegencrew --env /path/to/project.env plan

# Full architecture documentation - C4 + arc42 (Phases 0-3, excludes planning)
aicodegencrew run --preset architecture_workflow

# Architecture + development planning (Phases 0-4, includes planning)
aicodegencrew run --preset architecture_full

# Facts only — no LLM needed (Phases 0-1)
aicodegencrew run --preset facts_only

# Facts + AI analysis, no synthesis (Phases 0-2)
aicodegencrew run --preset analysis_only

# Index repository only (Phase 0)
aicodegencrew run --preset indexing_only

# Architecture + development planning (Phases 0-4)
aicodegencrew run --preset architecture_full

# All phases end-to-end (Phases 0-7)
aicodegencrew run --preset full_pipeline
```

#### Running Individual Phases

```bash
# Phase 0: Index repository into ChromaDB
python -m aicodegencrew run --phases phase0_indexing

# Phase 1: Extract architecture facts (deterministic, no LLM)
python -m aicodegencrew run --phases phase1_architecture_facts

# Phase 2: AI analysis of architecture patterns
python -m aicodegencrew run --phases phase2_architecture_analysis

# Phase 3: Generate C4 + arc42 documentation
python -m aicodegencrew run --phases phase3_architecture_synthesis
```

#### Combining Phases

```bash
# Run Phase 0 + Phase 1 together
python -m aicodegencrew run --phases phase0_indexing phase1_architecture_facts

# Run Phase 2 + Phase 3 (skip indexing/facts if already done)
python -m aicodegencrew run --phases phase2_architecture_analysis phase3_architecture_synthesis --index-mode off

# Re-run synthesis only (skip earlier phases)
python -m aicodegencrew run --phases phase3_architecture_synthesis --index-mode off
```

#### Indexing Control

```bash
# Auto-index (skip if unchanged, default)
python -m aicodegencrew run --preset architecture_workflow --index-mode auto

# Force full re-index + run all phases
python -m aicodegencrew run --preset architecture_workflow --index-mode force

# Skip indexing entirely (use existing ChromaDB)
python -m aicodegencrew run --preset architecture_workflow --index-mode off

# Smart incremental index (only changed files)
python -m aicodegencrew run --preset facts_only --index-mode smart
```

#### Index Command (Shortcut)

```bash
# Auto-index (default)
python -m aicodegencrew index

# Force re-index
python -m aicodegencrew index --force
python -m aicodegencrew index -f

# Smart incremental
python -m aicodegencrew index --smart
python -m aicodegencrew index -s

# Explicit mode
python -m aicodegencrew index --mode force

# Index a different repository
python -m aicodegencrew index --repo C:\repos\my-project
```

#### Clean Runs

```bash
# Clean knowledge directory + run full workflow
python -m aicodegencrew run --preset architecture_workflow --clean

# Force re-index + clean + full workflow (completely fresh start)
python -m aicodegencrew run --preset architecture_workflow --index-mode force --clean

# Run facts without auto-cleaning previous outputs
python -m aicodegencrew run --preset facts_only --no-clean
```

#### Other Repository

```bash
# Analyze a different local repository
python -m aicodegencrew run --preset architecture_workflow --repo-path C:\repos\other-project

# Analyze a remote Git repository (clones automatically)
python -m aicodegencrew run --preset architecture_workflow --git-url https://gitlab.example.com/team/project.git

# Specify a branch
python -m aicodegencrew run --preset architecture_workflow --git-url https://gitlab.example.com/team/project.git --branch develop

# List available phases and presets
python -m aicodegencrew list
```

---

## Pipeline Phases

| Phase | Name | Type | LLM | Status | Description |
|:-----:|------|:----:|:---:|:------:|-------------|
| 0 | **Indexing** | Pipeline | No | Implemented | Vector-indexes repository into ChromaDB |
| 1 | **Architecture Facts** | Pipeline | No | Implemented | Deterministic extraction of components, relations, interfaces, endpoint flows |
| 2 | **Architecture Analysis** | Crew | Yes | Implemented | Multi-agent analysis (4 analysts + Map-Reduce) |
| 3 | **Architecture Synthesis** | Crew | Yes | Implemented | C4 + arc42 document generation (Mini-Crews pattern) |
| 4 | **Development Planning** | Pipeline | Hybrid | Implemented | Hybrid pipeline (5 stages: 4 deterministic + 1 LLM). Parses tasks, discovers components (RAG), matches patterns (TF-IDF), generates plans (LLM), validates. 18-40s, 100% data usage. |
| 5 | **Code Generation** | Crew | Yes | Planned | Feature implementation and refactoring |
| 6 | **Test Generation** | Crew | Yes | Planned | Unit and integration test generation |
| 7 | **Review + Deploy** | Pipeline | No | Planned | CI/CD configuration and release management |

### Phase Dependencies

Each phase declares its dependencies. The orchestrator validates that all required inputs exist before starting a phase. If a dependency fails validation, the phase will not run.

```
Phase 0 ──► Phase 1 ──► Phase 2 ──► Phase 3 ──► Phase 4 ──► ...
(Index)     (Facts)     (Analysis)  (Synthesis)  (Planning)
```

---

## Input Files for Development Planning (Phase 4)

Phase 4 (Development Planning) requires task inputs to generate implementation plans. Input files are stored **outside** the tool — configure the paths in your `.env`:

```env
TASK_INPUT_DIR=C:\projects\inputs          # JIRA XML, DOCX, Excel, text files
REQUIREMENTS_DIR=C:\projects\requirements  # Specs and documentation (optional)
LOGS_DIR=C:\projects\logs                  # Error logs for bugfix tasks (optional)
REFERENCE_DIR=C:\projects\reference        # Reference code examples (optional)
```

### Input Folder Structure

```
C:\projects\inputs\          # = TASK_INPUT_DIR
├── PROJ-123.xml                # JIRA XML export
├── task-001.txt                # Plain text task description
├── bug-fix.log                 # Error log to analyze/fix
├── requirement.docx            # Word requirement doc
└── backlog.xlsx                # Excel task spreadsheet
```

### Supported File Formats

All formats are fully implemented and ready to use:

| Format | Extension | Description | What Gets Extracted | Dependencies |
|--------|-----------|-------------|---------------------|--------------|
| **Plain Text** | `.txt`, `.log` | Task descriptions, error logs | Full text content, error patterns | None (built-in) |
| **XML** | `.xml` | JIRA exports, structured data | **Complete extraction:** task details, description, comments (all with authors/dates), assignee, reporter, fix version, labels, metadata | None (built-in) |
| **Word** | `.docx` | Requirements, specifications | Title, sections (headings), tables | `pip install python-docx` |
| **Excel** | `.xlsx`, `.xls` | Task lists, backlogs | All sheets, data rows with headers | `pip install openpyxl` |

**Note:** Install optional parsers with `pip install -e ".[parsers]"` to enable DOCX and Excel support.

### How to Use

1. **Set `TASK_INPUT_DIR`** in your `.env` file:
   ```env
   TASK_INPUT_DIR=C:\projects\inputs
   ```

2. **Add your task files** to that folder:
   - Export JIRA tickets as XML
   - Or create plain text task descriptions

3. **Run development planning**:
   ```bash
   # Shortcut (recommended)
   aicodegencrew plan

   # Or explicitly
   aicodegencrew run --preset planning_only
   ```

### Example Task Input (Plain Text)

```text
Task: Add pagination to user list endpoint

Requirements:
- GET /api/users should support page and size parameters
- Default page size: 20 items
- Return total count in response headers
- Use Spring Data JPA Pageable

Acceptance Criteria:
- Existing tests still pass
- New endpoint supports ?page=0&size=10
- Response includes X-Total-Count header
```

### Output

Phase 4 generates implementation plans in `knowledge/development/`:

```
knowledge/development/
├── PROJ-123_plan.json     # Full implementation plan
├── TASK-456_plan.json     # Another task plan
└── ...
```

Each plan includes:
- Affected components (from RAG + semantic search)
- Implementation steps
- Test strategy (matched from 925 existing test patterns)
- Security considerations (from 143 security configs)
- Validation strategy (from 149 validation patterns)
- Error handling patterns (from 23 error handlers)
- Complete task context (all JIRA comments, metadata, history)

---

## Output Artifacts

All outputs are saved under `OUTPUT_BASE_DIR` (default: current working directory). Set `OUTPUT_BASE_DIR` in `.env` to redirect all outputs to a specific folder.

```
<OUTPUT_BASE_DIR>/
├── knowledge/                  # All generated artifacts
│   ├── architecture/           # Phase 1-3 outputs
│   ├── development/            # Phase 4 plans
│   └── run_report.json         # Pipeline run report (always generated)
├── logs/                       # Runtime logs
│   ├── current.log             # Session log (overwritten each run)
│   ├── errors.log              # Persistent error log (rotating)
│   └── metrics.jsonl           # Structured metrics (JSON lines)
└── architecture-docs/          # Phase 3 export (C4 + Arc42 only)
```

After Phase 3, the tool automatically **exports** the architect-relevant documents (C4 + Arc42 only, no JSON) to an export folder. Default: `<OUTPUT_BASE_DIR>/architecture-docs`. Override with `DOCS_OUTPUT_DIR` in `.env`.

Each `.md` file is automatically converted to **3 additional formats**:

| Format | Extension | Usage |
|--------|-----------|-------|
| **Markdown** | `.md` | Original, readable in any editor |
| **Confluence** | `.confluence` | Paste into Confluence Wiki Markup editor |
| **AsciiDoc** | `.adoc` | Compatible with docToolchain / asciidoc2confluence |
| **HTML** | `.html` | Open in browser, standalone with embedded CSS |

Arc42 chapters follow the **official arc42 template** structure. Set `ARC42_LANGUAGE=de` for German titles.

### Phase 1: Facts

| File | Description |
|------|-------------|
| `architecture_facts.json` | Canonical architecture facts (components, relations, interfaces, containers) |
| `evidence_map.json` | Source code evidence linked to each fact |

### Phase 2: Analysis

| File | Description |
|------|-------------|
| `analyzed_architecture.json` | Unified analysis (styles, patterns, domain model, quality, risks) |

### Phase 3: Synthesis

**C4 Model** (`c4/`):

| File | Description |
|------|-------------|
| `c4-context.md` | Level 1: System Context (actors, external systems) |
| `c4-context.drawio` | System Context diagram (DrawIO) |
| `c4-container.md` | Level 2: Container view (services, databases) |
| `c4-container.drawio` | Container diagram (DrawIO) |
| `c4-component.md` | Level 3: Component view (modules, layers) |
| `c4-component.drawio` | Component diagram (DrawIO) |
| `c4-deployment.md` | Level 4: Deployment view (infrastructure) |
| `c4-deployment.drawio` | Deployment diagram (DrawIO) |

**arc42** (`arc42/`):

| File | Description |
|------|-------------|
| `01-introduction.md` | Business context and stakeholders |
| `02-constraints.md` | Technical and organizational constraints |
| `03-context.md` | System scope and context |
| `04-solution-strategy.md` | Fundamental architecture decisions |
| `05-building-blocks.md` | Static decomposition (largest chapter) |
| `06-runtime-view.md` | Runtime scenarios and flows |
| `07-deployment.md` | Infrastructure and deployment topology |
| `08-crosscutting.md` | Cross-cutting concerns (security, logging, etc.) |
| `09-decisions.md` | Architecture Decision Records (ADRs) |
| `10-quality.md` | Quality requirements and measures |
| `11-risks.md` | Known risks and technical debt |
| `12-glossary.md` | Domain and technical glossary |

**Quality Reports** (`quality/`):

| File | Description |
|------|-------------|
| `c4-report.md` | C4 documentation quality assessment |
| `arc42-report.md` | arc42 documentation quality assessment |

---

## Project Structure

```
aicodegencrew/
├── config/
│   └── phases_config.yaml          # Phase definitions and presets
├── docs/
│   ├── AI_SDLC_ARCHITECTURE.md     # Full architecture specification
│   └── diagrams/                   # DrawIO architecture diagrams
│       ├── sdlc-overview.drawio
│       ├── layer-architecture.drawio
│       ├── pipeline-flow.drawio
│       ├── facts-collectors.drawio
│       ├── evidence-flow.drawio
│       ├── knowledge-structure.drawio
│       ├── analysis-crew.drawio
│       ├── synthesis-crew.drawio
│       ├── analysis-crew-schema.drawio
│       └── development-planning-pipeline.drawio
├── src/aicodegencrew/
│   ├── cli.py                      # CLI entry point (argparse)
│   ├── orchestrator.py             # Phase orchestration and dependency resolution
│   ├── main.py                     # Application entry point
│   │
│   ├── crews/                      # AI Agent Workflows (LLM required)
│   │   ├── architecture_analysis/  # Phase 2: Multi-agent analysis (Mini-Crews)
│   │   │   ├── crew.py             #   5 mini-crews, 17 tasks (all Python, no YAML)
│   │   │   ├── mapreduce_crew.py   #   Map-Reduce for large repos
│   │   │   ├── container_crew.py   #   Per-container analysis crew
│   │   │   └── tools/              #   Facts query, RAG, statistics tools
│   │   │
│   │   └── architecture_synthesis/ # Phase 3: Document generation
│   │       ├── base_crew.py        #   MiniCrewBase ABC (shared infrastructure)
│   │       ├── crew.py             #   Top-level synthesis coordinator
│   │       ├── c4/crew.py          #   C4 Mini-Crews (5 crews, all Python)
│   │       ├── arc42/crew.py       #   Arc42 Mini-Crews (18 crews, all Python)
│   │       └── tools/              #   DocWriter, DrawIO, chunked writer
│   │
│   ├── pipelines/                  # Deterministic Pipelines (no LLM)
│   │   ├── indexing/               # Phase 0: ChromaDB vector indexing
│   │   │   ├── indexing_pipeline.py #  IndexingPipeline + IndexingState + ensure_repo_indexed
│   │   │   ├── chroma_index_tool.py
│   │   │   ├── chunker_tool.py
│   │   │   └── embeddings_tool.py
│   │   │
│   │   ├── architecture_facts/     # Phase 1: Facts extraction
│   │   │   ├── pipeline.py
│   │   │   ├── model_builder.py    #   Canonical model + 7-tier relation resolver
│   │   │   ├── endpoint_flow_builder.py  # Controller→Service→Repository chains
│   │   │   ├── dimension_writers.py
│   │   │   └── collectors/         #   20+ specialized collectors
│   │   │       ├── fact_adapter.py  #   RawFact→Collected* adapter
│   │   │       ├── spring/         #     Spring Boot (REST, services, repos, config)
│   │   │       ├── angular/        #     Angular (components, modules, routing, services)
│   │   │       └── database/       #     Database (migrations, tables, procedures)
│   │   │
│   │   └── development_planning/   # Phase 4: Hybrid development planning
│   │       ├── pipeline.py         #   DevelopmentPlanningPipeline (orchestrator)
│   │       ├── schemas.py          #   Pydantic models for all stages
│   │       └── stages/             #   5-stage hybrid architecture
│   │           ├── stage1_input_parser.py     # JIRA XML, DOCX, Excel, logs
│   │           ├── stage2_component_discovery.py  # RAG + multi-signal scoring
│   │           ├── stage3_pattern_matcher.py      # TF-IDF + rule-based matching
│   │           ├── stage4_plan_generator.py       # LLM synthesis (only LLM stage)
│   │           └── stage5_validator.py            # Pydantic + completeness checks
│   │
│   ├── shared/                     # Shared utilities
│   │   ├── validation.py           # Phase output validation
│   │   ├── models/                 # Pydantic schemas (facts, analysis, outputs)
│   │   └── utils/                  # Logger, token budget, file filters, Ollama client
│   │       ├── git_repo_manager.py # Git clone/pull for remote repos
│   │       └── tool_guardrails.py  # Phase 0.5: Loop prevention + tool budgets
│   │
│   └── mcp/                        # Model Context Protocol
│       ├── server.py               # MCP server (architecture knowledge queries)
│       └── knowledge_tools.py      # get_statistics, get_endpoints, query_facts, ...
│
├── tests/
│   ├── test_*.py                   # Unit tests
│   └── e2e/                        # End-to-end tests (full workflow)
│
├── knowledge/architecture/         # Generated output (gitignored)
├── logs/                           # Runtime logs + metrics.jsonl
├── .env.example                    # Environment template
├── pyproject.toml                  # Project metadata and dependencies
├── Dockerfile                      # Multi-stage build (no source in final image)
├── docker-compose.yml              # Developer-friendly Docker setup
├── .dockerignore                   # Excludes source from Docker context
└── mcp_server.py                   # MCP server entry point
```

---

## Testing

The project has a comprehensive test suite with **600+ tests** covering unit, integration, scenario, and delivery validation.

### Prerequisites

```bash
pip install -e ".[dev]"
```

### Run All Tests

```bash
# Full suite (all 600+ tests, ~17s)
pytest tests/ -v

# With coverage report
pytest tests/ --cov=aicodegencrew --cov-report=term-missing
```

### Test Categories

#### Unit Tests

| Test File | Module | Tests |
|-----------|--------|:-----:|
| `test_cli_orchestrator.py` | CLI argument parsing, Config, presets, orchestrator lifecycle | ~50 |
| `test_logger_guardrails.py` | Logger, StepTracker, token budget, tool guardrails | ~30 |
| `test_parsers_upgrade.py` | XML/text parsers, Angular/Spring/Java upgrade rules | ~40 |
| `test_validation_model.py` | Phase validation, model builder, ID generation, layer classification | ~50 |
| `test_confluence_converter.py` | Markdown to Confluence/AsciiDoc/HTML conversion | ~50 |
| `test_development_planning.py` | Phase 4 pipeline stages, schemas, pattern matching | ~33 |
| `test_chunker.py` | Text chunking for indexing | 6 |
| `test_chroma_index.py` | ChromaDB upsert/query operations | 7 |
| `test_repo_discovery.py` | Git repo detection, submodules | 6 |
| `test_file_filters.py` | Include/exclude file filtering | 10 |
| `test_quality_gate.py` | Quality gate checks | 6 |
| `test_quality_validator.py` | Facts JSON schema validation | 8 |
| `test_summarize_facts.py` | Facts summarization | 2 |

```bash
# Run all unit tests (excludes e2e/)
pytest tests/ --ignore=tests/e2e -v

# Run a single test file
pytest tests/test_cli_orchestrator.py -v

# Run a specific test class
pytest tests/test_confluence_converter.py::TestConfluence -v

# Run a specific test
pytest tests/test_validation_model.py::TestLayerClassifier::test_controller_returns_presentation -v
```

#### Integration Tests

| Test File | Coverage |
|-----------|----------|
| `test_integration.py` | Phase 0→1 data flow, indexing state, fingerprinting, facts schema, collector orchestration |

```bash
pytest tests/test_integration.py -v
```

#### Scenario / E2E Tests

| Test File | Scenarios |
|-----------|-----------|
| `test_scenarios.py` | Fresh first run, preset resolution, error recovery, phase output validation, multi-format export, run report, orchestrator data flow, collector base classes |
| `e2e/test_full_workflow.py` | Full pipeline workflow, idempotency, evidence chain |
| `e2e/test_phase1_facts_extraction.py` | Phase 1 facts extraction against real repo |
| `e2e/test_phase2_synthesis.py` | Phase 2 synthesis quality checks |

```bash
# Scenario tests (no LLM/network required)
pytest tests/test_scenarios.py -v

# E2E tests (requires PROJECT_PATH set + Ollama running)
pytest tests/e2e/ -v
```

#### Delivery / Packaging Tests

| Test File | Coverage |
|-----------|----------|
| `test_delivery.py` | pyproject.toml structure, version bumping, .env.example, Docker/Compose files, phases_config.yaml, documentation completeness, code quality (no print/secrets/syntax errors), .gitignore rules |

```bash
pytest tests/test_delivery.py -v
```

### Test Patterns

Tests run **without LLM or network access** (except `tests/e2e/`). They use:

- `tmp_path` fixtures for isolated file system operations
- `monkeypatch` for environment variable mocking
- `unittest.mock.patch` for dependency injection
- Real `phases_config.yaml` for preset validation tests

### Continuous Integration

```bash
# Quick check: syntax + all tests
python -m py_compile src/aicodegencrew/cli.py && pytest tests/ -v --tb=short
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [AI SDLC Architecture](docs/AI_SDLC_ARCHITECTURE.md) | Full architecture specification (4-layer model, phases, patterns, Mini-Crews) |
| [DrawIO Diagrams](docs/diagrams/) | Visual architecture diagrams (open with [draw.io](https://app.diagrams.net/)) |
| [Phase Configuration](config/phases_config.yaml) | Phase definitions, dependencies, and preset configurations |
| [Environment Template](.env.example) | All configurable environment variables with descriptions |

### Key Architecture Concepts

- **Evidence-First**: All outputs must reference real code evidence. If it's not in `architecture_facts.json`, it must not appear in documentation.
- **Mini-Crews Pattern**: Each document section is generated by a separate AI crew with fresh LLM context, preventing context window overflow.
- **MiniCrewBase**: Abstract base class providing shared infrastructure (LLM factory, tool setup, MCP config, checkpointing) for all synthesis crews.
- **Map-Reduce Analysis**: Large repositories are split by container for parallel analysis, then merged into a unified result.
- **Checkpoint & Resume**: Failed runs can be resumed — completed mini-crews are skipped automatically.

---

## Contributing

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/my-feature`)
3. **Install** dev dependencies (`pip install -e ".[dev]"`)
4. **Make** your changes
5. **Run** tests (`pytest tests/ -v`)
6. **Lint** your code (`ruff check src/`)
7. **Submit** a pull request

### Development Guidelines

- Follow existing code patterns and naming conventions
- Add tests for new collectors or tools
- Update `phases_config.yaml` when adding new phases
- Keep the evidence-first principle: no invented data in outputs
- Use Pydantic models for data contracts between phases

---

## License

Proprietary — Capgemini. See [LICENSE](LICENSE) for details.

---

<p align="center">
  Built with <a href="https://crewai.com/">CrewAI</a> · Powered by local LLMs · Made for enterprise
</p>
