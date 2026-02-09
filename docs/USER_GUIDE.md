# AICodeGenCrew - User Guide

**Version 0.1.0 | Capgemini Proprietary**

---

## Table of Contents

1. [Overview](#1-overview)
2. [Installation](#2-installation)
3. [Configuration](#3-configuration)
4. [Quick Start](#4-quick-start)
5. [Commands](#5-commands)
6. [Input Files](#6-input-files)
7. [Output Files](#7-output-files)
8. [Presets](#8-presets)
9. [Environment Variables](#9-environment-variables)
10. [Docker Usage](#10-docker-usage)
11. [Troubleshooting](#11-troubleshooting)
12. [FAQ](#12-faq)

---

## 1. Overview

AICodeGenCrew is an AI-powered tool for Software Development Lifecycle automation. It analyzes your codebase and generates:

- **Architecture documentation** (C4 Model + arc42)
- **Development plans** from JIRA tickets, requirements, and logs
- **Code analysis** including components, relations, patterns, and quality metrics

The tool runs **entirely on-premises** — no data leaves your network.

### What You Get

| Phase | What It Does | LLM Required | Duration |
|:-----:|-------------|:------------:|----------|
| 0 | Index repository into vector database | No | 2-10 min |
| 1 | Extract architecture facts (components, relations) | No | 1-3 min |
| 2 | AI analysis of architecture patterns | Yes | 5-15 min |
| 3 | Generate C4 + arc42 documentation | Yes | 15-45 min |
| 4 | Generate development plans from JIRA tickets | Hybrid | 18-40 sec |

---

## 2. Installation

### Option A: Wheel Package (Recommended)

You received a `.whl` file from the development team.

```bash
# Install (with DOCX/Excel parser support)
pip install aicodegencrew-0.1.0-py3-none-any.whl[parsers]

# Verify installation
aicodegencrew --help
```

**Requirements:**
- Python 3.10 - 3.12
- Ollama (for embeddings): https://ollama.com/

### Option B: Docker

You received a Docker image (`.tar.gz` file or access to a registry).

```bash
# Load from file
docker load -i aicodegencrew-0.1.0.tar.gz

# Or pull from registry
docker pull <registry>/aicodegencrew:0.1.0

# Verify
docker run aicodegencrew:latest --help
```

**Requirements:**
- Docker 20+

---

## 3. Configuration

### Step 1: Create `.env` File

Copy the provided `.env.example` to your working directory and edit it:

```bash
cp .env.example .env
```

### Step 2: Configure Required Settings

Edit `.env` with your project-specific values:

```env
# REQUIRED: Path to the repository you want to analyze
PROJECT_PATH=C:\repos\my-project

# REQUIRED: LLM endpoint
LLM_PROVIDER=onprem
MODEL=gpt-oss-120b
API_BASE=http://sov-ai-platform.nue.local.vm:4000/v1
OPENAI_API_KEY=your-api-key-here

# REQUIRED: Ollama for embeddings
OLLAMA_BASE_URL=http://127.0.0.1:11434
EMBED_MODEL=nomic-embed-text:latest
```

### Step 3: Start Ollama

```bash
# Pull embedding model (first time only)
ollama pull nomic-embed-text:latest

# Start Ollama server
ollama serve
```

### Step 4: Verify

```bash
aicodegencrew list
```

You should see all available phases and presets.

---

## 4. Quick Start

### Development Planning (Most Common)

1. Set `TASK_INPUT_DIR` in your `.env` to the folder containing your JIRA XML files:
   ```env
   TASK_INPUT_DIR=C:\work\my-project\tasks
   ```

2. Run:
   ```bash
   aicodegencrew plan
   ```

This runs Phases 0+1+2+4 and generates a development plan in `knowledge/development/`.

### With Custom `.env` Location

```bash
aicodegencrew --env C:\configs\my-project.env plan
```

### Full Architecture Documentation

```bash
aicodegencrew run --preset architecture_workflow
```

---

## 5. Commands

### General Syntax

```
aicodegencrew [--env <path>] <command> [options]
```

### Available Commands

| Command | Description |
|---------|-------------|
| `plan` | Development planning (Phases 0+1+2+4) |
| `run` | Execute pipeline with preset or explicit phases |
| `index` | Index repository only (Phase 0) |
| `list` | Show available phases and presets |

### `plan` Command

```bash
# Basic usage
aicodegencrew plan

# Override repository path
aicodegencrew plan --repo-path C:\repos\other-project

# Skip re-indexing (use existing index)
aicodegencrew plan --index-mode off
```

### `run` Command

```bash
# Run a preset
aicodegencrew run --preset architecture_workflow

# Run specific phases
aicodegencrew run --phases phase0_indexing phase1_architecture_facts

# Force re-index + clean output
aicodegencrew run --preset architecture_workflow --index-mode force --clean
```

### `index` Command

```bash
# Auto-index (skip if unchanged)
aicodegencrew index

# Force re-index
aicodegencrew index --force

# Smart incremental (only changed files)
aicodegencrew index --smart
```

---

## 6. Input Files

### For Development Planning (Phase 4)

Input files are stored **outside** the tool installation — on your local machine or a shared drive.
Configure the paths in your `.env` file:

```env
# REQUIRED: Folder with JIRA XMLs, DOCX, Excel, or text files
TASK_INPUT_DIR=C:\work\my-project\tasks

# OPTIONAL: Additional input folders
REQUIREMENTS_DIR=C:\work\my-project\requirements
LOGS_DIR=C:\work\my-project\logs
REFERENCE_DIR=C:\work\my-project\reference
```

Example folder structure on your machine:

```
C:\work\my-project\
├── tasks/              # REQUIRED: Task descriptions
│   ├── PROJ-123.xml       # JIRA XML export
│   ├── requirement.docx   # Word requirement doc
│   ├── backlog.xlsx       # Excel spreadsheet
│   └── task.txt           # Plain text description
│
├── requirements/       # OPTIONAL: Additional specs
├── logs/               # OPTIONAL: Error logs for bugfix tasks
└── reference/          # OPTIONAL: Reference code examples
```

### Supported Formats

| Format | Extension | What Gets Extracted |
|--------|-----------|---------------------|
| **JIRA XML** | `.xml` | Task ID, description, comments, labels, priority, linked tickets |
| **Word** | `.docx` | Title, sections, tables |
| **Excel** | `.xlsx`, `.xls` | All sheets, data rows |
| **Text/Log** | `.txt`, `.log` | Full text, error patterns |

### JIRA XML Export

To export from JIRA:
1. Open the JIRA issue
2. Click **Export** > **XML**
3. Save to your `TASK_INPUT_DIR` folder (configured in `.env`)

### Multiple Tasks

Place multiple XML files in your `TASK_INPUT_DIR` folder. The tool processes them in priority order:
1. Blocker > Critical > Major > Minor > Trivial
2. Upgrades > Bugfixes > Features > Refactoring
3. Parent tickets before child/subtask tickets

---

## 7. Output Files

### Development Plans (Phase 4)

Output: `knowledge/development/{TASK_ID}_plan.json`

Each plan contains:
- **affected_components**: Components impacted by the change
- **upgrade_plan** (for framework upgrades only):
  - `framework`, `from_version`, `to_version` (e.g., "Angular 18 → 19")
  - `migration_sequence`: 15+ upgrade rules with severity (breaking/deprecated/recommended)
  - `affected_files`: Real file paths matched by each rule (e.g., 142 files for standalone components)
  - `migration_steps`: Step-by-step migration guide per rule
  - `estimated_effort_minutes`: Effort per rule
  - `verification_commands`: Commands to verify upgrade (e.g., `ng build`, `ng test`)
- **implementation_steps**: Ordered steps to implement the task
- **test_strategy**: Recommended tests based on existing patterns
- **security_considerations**: Security-relevant patterns found
- **validation_strategy**: Validation rules from the codebase
- **error_handling**: Error handling patterns to follow
- **architecture_context**: Relevant architecture information
- **risks**: Identified risks and mitigation strategies
- **complexity**: Estimated complexity and effort

### Run Report

After every pipeline run, `knowledge/run_report.json` is generated with:
- **run_id**: Unique identifier for this run
- **status**: `success` or `failed`
- **phases**: Per-phase status, duration, and output files
- **environment**: Repo path, index mode, output base directory
- **output_summary**: Paths to log file and metrics file

This file is always written — even on failure — so you have a persistent record of what happened.

### Architecture Documentation (Phase 3)

Internal output (always): `knowledge/architecture/`

```
knowledge/architecture/
├── architecture_facts.json       # Phase 1: Raw facts (internal)
├── analyzed_architecture.json    # Phase 2: AI analysis (internal)
├── c4/                           # C4 Model (for architect)
│   ├── c4-context.md + .drawio
│   ├── c4-container.md + .drawio
│   ├── c4-component.md + .drawio
│   └── c4-deployment.md + .drawio
└── arc42/                        # arc42 Chapters (for architect)
    ├── 01-introduction.md
    ├── 02-constraints.md
    ├── ... (12 chapters total)
    └── 12-glossary.md
```

### Exporting Architecture Docs

After Phase 3, the tool automatically copies the **architect-relevant** documents (C4 + Arc42) to an export folder. Default: `./architecture-docs` in your working directory.

To change the export location, set `DOCS_OUTPUT_DIR` in your `.env`:

```env
DOCS_OUTPUT_DIR=C:\work\my-project\architecture-docs
```

The export folder contains **only** the deliverable documents — no intermediate JSON files. Each `.md` file is automatically converted to 3 additional formats:

```
C:\work\my-project\architecture-docs\
├── c4/
│   ├── c4-context.md                # Markdown (original)
│   ├── c4-context.confluence        # Confluence Wiki Markup
│   ├── c4-context.adoc              # AsciiDoc (for docToolchain)
│   ├── c4-context.html              # Standalone HTML
│   ├── c4-context.drawio            # DrawIO diagram
│   └── ... (4 C4 levels x 4 formats + drawio)
└── arc42/
    ├── 00-arc42-toc.confluence      # Table of Contents (arc42 template)
    ├── 00-arc42-toc.adoc
    ├── 00-arc42-toc.html
    ├── 01-introduction.md
    ├── 01-introduction.confluence
    ├── 01-introduction.adoc
    ├── 01-introduction.html
    ├── ... (12 chapters x 4 formats)
    └── 12-glossary.html
```

### Export Formats

| Format | Extension | Usage |
|--------|-----------|-------|
| **Markdown** | `.md` | Original format, readable in any editor |
| **Confluence** | `.confluence` | Paste into Confluence Wiki Markup editor |
| **AsciiDoc** | `.adoc` | Compatible with docToolchain / asciidoc2confluence |
| **HTML** | `.html` | Open in browser, standalone with embedded CSS |

Arc42 chapters follow the **official arc42 template** structure (arc42.org). Set `ARC42_LANGUAGE=de` in `.env` for German chapter titles in the Table of Contents.

---

## 8. Presets

| Preset | Phases | Use Case |
|--------|--------|----------|
| `planning_only` | 0, 1, 2, 4 | Development planning from JIRA tickets |
| `facts_only` | 0, 1 | Quick architecture facts (no LLM needed) |
| `analysis_only` | 0, 1, 2 | Facts + AI analysis |
| `architecture_workflow` | 0, 1, 2, 3 | Full C4 + arc42 documentation |
| `architecture_full` | 0, 1, 2, 3, 4 | Architecture docs + development planning |

Usage:
```bash
aicodegencrew run --preset <preset_name>
```

---

## 9. Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `PROJECT_PATH` | Path to repository to analyze | `C:\repos\my-project` |
| `TASK_INPUT_DIR` | Folder with JIRA XML / task files | `C:\work\my-project\tasks` |
| `LLM_PROVIDER` | LLM provider (`onprem` or `local`) | `onprem` |
| `MODEL` | LLM model name | `gpt-oss-120b` |
| `API_BASE` | LLM API endpoint | `http://server:4000/v1` |
| `OPENAI_API_KEY` | API key for LLM | `your-key` |
| `OLLAMA_BASE_URL` | Ollama server URL | `http://127.0.0.1:11434` |
| `EMBED_MODEL` | Ollama embedding model | `nomic-embed-text:latest` |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `INDEX_MODE` | `auto` | Indexing mode (`off`/`auto`/`force`/`smart`) |
| `SKIP_SYNTHESIS` | `false` | Skip Phase 3 (C4/arc42 generation) |
| `LOG_LEVEL` | `INFO` | Logging level |
| `OUTPUT_BASE_DIR` | `.` | Base directory for ALL outputs (`knowledge/`, `logs/`, `run_report.json`) |
| `DOCS_OUTPUT_DIR` | `<OUTPUT_BASE_DIR>/architecture-docs` | Export folder for Phase 3 docs (C4 + Arc42 only) |
| `ARC42_LANGUAGE` | `en` | Arc42 ToC language (`en` or `de`) |
| `MAX_LLM_INPUT_TOKENS` | `100000` | Max input tokens per LLM call |
| `MAX_LLM_OUTPUT_TOKENS` | `16000` | Max output tokens per LLM call |

### Git Repository (Alternative to PROJECT_PATH)

| Variable | Description |
|----------|-------------|
| `GIT_REPO_URL` | Git HTTPS URL (clones automatically) |
| `GIT_BRANCH` | Branch to checkout (empty = auto-detect) |

---

## 10. Docker Usage

### docker-compose (Recommended)

Create a working directory with this structure:

```
my-workspace/
├── .env                  # Your configuration (set TASK_INPUT_DIR, PROJECT_PATH)
├── docker-compose.yml    # Provided with the tool
├── knowledge/            # Internal output (auto-created)
├── architecture-docs/    # Phase 3 export for architect (auto-created)
└── .cache/               # ChromaDB cache (auto-created)
```

Your `.env` points to your **external** folders:
```env
PROJECT_PATH=C:\repos\my-project
TASK_INPUT_DIR=C:\projects\inputs
DOCS_OUTPUT_DIR=./architecture-docs
```

Run:
```bash
docker-compose run aicodegencrew plan
```

The docker-compose reads `TASK_INPUT_DIR` and `PROJECT_PATH` from your `.env` and mounts them automatically.

### docker run

```bash
docker run --network host \
  -v C:\configs\my-project.env:/app/.env:ro \
  -v C:\repos\my-project:/repo:ro \
  -v C:\projects\inputs:/app/inputs/tasks:ro \
  -v .\knowledge:/app/knowledge \
  -v .\architecture-docs:/app/architecture-docs \
  -v .\.cache:/app/.cache \
  -e PROJECT_PATH=/repo \
  -e TASK_INPUT_DIR=/app/inputs/tasks \
  -e DOCS_OUTPUT_DIR=/app/architecture-docs \
  aicodegencrew:latest plan
```

### Network Requirements

The Docker container needs access to:
- **Ollama** at `localhost:11434` (or your configured URL)
- **On-prem LLM** at the configured `API_BASE` URL

Use `--network host` to enable access to host services.

---

## 11. Troubleshooting

### "Input file not found"

Ensure `TASK_INPUT_DIR` in your `.env` points to the correct folder containing your JIRA XML files. This must be an **absolute path** to a folder **outside** the code repository.

### "Ollama connection refused"

```bash
# Check if Ollama is running
curl http://127.0.0.1:11434/api/tags

# Start Ollama
ollama serve

# Pull embedding model
ollama pull nomic-embed-text:latest
```

### "LLM connection timeout"

- Verify `API_BASE` in `.env` is reachable
- Check VPN/proxy settings (`NO_PROXY=localhost,127.0.0.1`)
- Increase timeout: `LLM_NUM_RETRIES=10`, `LLM_RETRY_DELAY=5`

### "ChromaDB index missing"

```bash
# Force re-index
aicodegencrew index --force
```

### "Phase X failed, but Phase Y needs it"

Each phase depends on the previous. Run all phases in order:
```bash
aicodegencrew run --preset planning_only
```

### Docker: "Permission denied" on volumes

Ensure the mounted directories exist and have correct permissions:
```bash
mkdir -p knowledge .cache architecture-docs
```

### Slow indexing (>30 min)

- Large repositories may take time on first index
- Subsequent runs use `auto` mode (skips if unchanged)
- Use `--index-mode smart` to only re-index changed files

---

## 12. FAQ

**Q: Does my data leave the network?**
A: No. Everything runs on-premises. Embeddings use local Ollama, LLM calls go to your on-prem endpoint.

**Q: Can I analyze multiple repositories?**
A: Yes. Use different `.env` files for each project:
```bash
aicodegencrew --env project-a.env plan
aicodegencrew --env project-b.env plan
```

**Q: Can I skip the indexing step?**
A: Yes, if already indexed: `aicodegencrew plan --index-mode off`

**Q: What languages are supported?**
A: Java (Spring Boot), TypeScript/JavaScript (Angular), Kotlin, Groovy. The tool extracts architecture from these frameworks.

**Q: How long does it take?**
A: Development planning (Phase 4): 18-40 seconds. Full architecture docs (Phases 0-3): 20-60 minutes depending on repository size.

**Q: Can I process multiple JIRA tickets at once?**
A: Yes. Place all XML files in your `TASK_INPUT_DIR` folder (configured in `.env`). They are sorted by priority and processed sequentially.

---

*Capgemini Proprietary - Internal Use Only*
