# AICodeGenCrew - User Guide

**Version 0.1.0 | Capgemini Proprietary**

---

## Table of Contents

**Getting Started**

1. [Overview](#1-overview)
2. [What You Received](#2-what-you-received)
3. [Prerequisites & System Requirements](#3-prerequisites--system-requirements)
4. [Before You Begin: Setup Checklist](#4-before-you-begin-setup-checklist)
5. [Choose Your Installation Method](#5-choose-your-installation-method)
6. [Installation](#6-installation)
7. [Configuration](#7-configuration)
8. [Your Folder Structure](#8-your-folder-structure)

**Using the Tool**

9. [Common Use Cases: Which Preset Should I Use?](#9-common-use-cases-which-preset-should-i-use)
10. [Quick Start](#10-quick-start)
11. [Commands](#11-commands)
12. [Understanding Indexing Modes](#12-understanding-indexing-modes)
13. [Input Files](#13-input-files)
14. [Output Files](#14-output-files)
15. [Presets](#15-presets)
16. [Environment Variables](#16-environment-variables)

**Advanced & Troubleshooting**

17. [Docker Usage](#17-docker-usage)
18. [Network Connectivity Diagnostics](#18-network-connectivity-diagnostics)
19. [Troubleshooting](#19-troubleshooting)
20. [FAQ](#20-faq)

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

## 2. What You Received

When you unpack the delivery package, you'll find:

```
aicodegencrew-v0.1.0/
├── aicodegencrew-0.1.0-py3-none-any.whl   ← The tool (install this)
├── .env.example                            ← Configuration template
├── install.bat / install.sh                ← Quick installer (Windows/Linux/Mac)
├── docker-compose.yml                      ← Docker setup (alternative)
├── config/
│   └── phases_config.yaml                  ← Phase definitions (reference)
├── USER_GUIDE.md                           ← Documentation (Markdown)
├── USER_GUIDE.pdf                          ← Documentation (PDF)
└── CHANGELOG.md                            ← Version history
```

**What each file does:**
- `.whl` file: The Python package you'll install via `pip`
- `.env.example`: Copy this to `.env` and edit with YOUR project paths
- `install.bat/.sh`: Run this for automated setup (easier than manual pip)
- `docker-compose.yml`: For Docker users (isolated environment)
- `phases_config.yaml`: Defines which phases run in each preset (read-only)
- `USER_GUIDE.md` / `.pdf`: This documentation in Markdown and PDF format

**Your data stays separate!** This tool doesn't include your repository or inputs.
You'll configure paths to YOUR files in the `.env` file (see Section 7).

---

## 3. Prerequisites & System Requirements

Before installing, ensure you have:

### Required Software

| Requirement | Version | Check Command | Install |
|-------------|---------|---------------|---------|
| Python | 3.10, 3.11, or 3.12 | `python --version` | https://python.org |
| Ollama | Latest | `ollama --version` | https://ollama.com |

### System Resources

- **RAM:** 4 GB minimum, 8 GB recommended
- **Disk Space:** 50 GB free (for large repositories)
- **Network:** Access to your on-prem LLM endpoint

### Ports

These ports must be available on your network:
- `:11434` - Ollama embeddings service (localhost)
- `:4000` - Your on-prem LLM endpoint (configurable)

### Supported Operating Systems

- Windows 10+
- Linux (Ubuntu 20.04+, RHEL 8+)
- macOS 10.15+

### Network Requirements

**On-premises only** - No data leaves your network
- All AI calls: Your configured LLM server
- All embeddings: Local Ollama instance

---

## 4. Before You Begin: Setup Checklist

Complete this checklist BEFORE installation:

**Software Installed:**
- Python 3.10+ installed: `python --version` works
- Ollama installed: `ollama --version` works
- Ollama running: `ollama serve` (in separate terminal)
- Embedding model pulled: `ollama pull nomic-embed-text:latest`

**Access & Credentials:**
- Your project repository path ready (e.g., `C:\repos\my-project`)
- On-prem LLM endpoint URL (e.g., `http://server:4000/v1`)
- API key for LLM endpoint

**Optional (for Phase 4 only):**
- JIRA export folder with XML files (if running development planning)
- Input folder path ready (e.g., `C:\work\inputs\tasks`)

**System Check:**
- 4+ GB free RAM available
- 50+ GB free disk space
- Ports 11434 and 4000 are not blocked by firewall

**All checked?** Proceed to Section 5 (Choose Installation Method)

**Missing something?** See Prerequisites (Section 3)

---

## 5. Choose Your Installation Method

**Which method should I use?**

```
START HERE
│
├─ Do you have Python 3.10+ installed?
│  ├─ YES: Go to Option A (Wheel Package) - Simpler, 5 min
│  └─ NO: Go to Option B (Docker) - No Python needed
│
├─ Does your team use Docker?
│  ├─ YES: Go to Option B (Docker) - Team standard
│  └─ NO: Go to Option A (Wheel Package)
│
└─ Want quickest setup?
   Use install.bat/install.sh (Windows/Linux/Mac) - Automated
```

**Comparison:**

| Method | Time | Prerequisites | Isolation | Team Use |
|--------|------|---------------|-----------|----------|
| **Wheel (pip)** | 5 min | Python 3.10+ | Medium | Individual |
| **Quick Install** | 2 min | Python 3.10+ | Medium | Individual |
| **Docker** | 10 min | Docker 20+ | High | Team |

Continue to Section 6 (Installation) with your chosen method

---

## 6. Installation

Choose your method from Section 5. Jump to:
- **Quick Setup:** Section 6.1 (install.bat/install.sh)
- **Wheel Package:** Section 6.2 (pip install)
- **Docker:** Section 6.3 (docker-compose)

### 6.1 Quick Setup (Recommended for First-Time)

**Windows:**
```bat
install.bat
```

**Linux/macOS:**
```bash
chmod +x install.sh
./install.sh
```

**What it does:**
1. Checks Python version
2. Installs wheel with pip
3. Pulls Ollama embedding model
4. Verifies installation

Skip to Section 7 (Configuration)

### 6.2 Manual: Wheel Package

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

### 6.3 Manual: Docker

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

### 6.4 Uninstall

To completely remove AICodeGenCrew from your system:

**Wheel installation (Windows/Linux/Mac):**
```bash
# Uninstall the package
pip uninstall aicodegencrew -y

# Remove data and cache (optional, choose one)
# Windows:
rmdir /s /q .cache knowledge logs

# Linux/Mac:
rm -rf .cache knowledge logs
```

**Docker installation:**
```bash
# Remove container
docker rm -f aicodegencrew

# Remove image
docker rmi aicodegencrew:latest

# Remove volumes (optional - deletes all data)
docker volume rm aicodegencrew_data
```

**What gets removed:**
- Python package: `pip uninstall` removes the tool
- Data folders: `.cache`, `knowledge`, `logs` must be deleted manually
- Configuration: `.env` file stays (delete manually if needed)
- Your repository: NEVER touched (stays safe)

**What stays:**
- Your `.env` file (in case you reinstall)
- Your input folders (`TASK_INPUT_DIR`, etc.)
- Your source code repository (`PROJECT_PATH`)

---

## 7. Configuration

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

# Phase 4 only: Input folders (for development planning)
# Leave these OUT if you only want architecture docs (Phases 0-3)
TASK_INPUT_DIR=C:\work\my-project\tasks             # JIRA XML, DOCX, PDF, TXT
REQUIREMENTS_DIR=C:\work\my-project\requirements    # Requirements (Excel, DOCX, PDF)
LOGS_DIR=C:\work\my-project\logs                    # Log files (.log, .txt, .xlsx)
REFERENCE_DIR=C:\work\my-project\reference          # Mockups, diagrams

# REQUIRED: LLM endpoint
LLM_PROVIDER=onprem
MODEL=gpt-oss-120b
API_BASE=http://sov-ai-platform.nue.local.vm:4000/v1
OPENAI_API_KEY=your-api-key-here

# REQUIRED: Ollama for embeddings
OLLAMA_BASE_URL=http://127.0.0.1:11434
EMBED_MODEL=nomic-embed-text:latest
```

**What are these input folders?**

| Variable | Used by | Contents | Required? |
|----------|---------|----------|-----------|
| `PROJECT_PATH` | All phases | Your source code repository | YES |
| `TASK_INPUT_DIR` | Phase 4 only | JIRA exports (.xml), tickets (.docx), bug reports (.txt) | Only for `plan` command |
| `REQUIREMENTS_DIR` | Phase 4 only | Requirements docs (.xlsx, .docx, .pdf) | Optional |
| `LOGS_DIR` | Phase 4 only | Application logs (.log, .txt, .xlsx) | Optional |
| `REFERENCE_DIR` | Phase 4 only | UI mockups, architecture diagrams | Optional |

**Important:** Input folders must be OUTSIDE your code repository!

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

## 8. Your Folder Structure

After first run, your working directory will look like this:

### What Gets Created

```
your-workspace/              ← Your chosen directory
├── .env                     ← Your configuration (YOU created this)
├── knowledge/               ← Tool outputs (auto-created)
│   ├── run_report.json      ← Status of last run
│   ├── architecture/
│   │   ├── architecture_facts.json    ← Phase 1 output
│   │   ├── analyzed_architecture.json ← Phase 2 output
│   │   ├── c4/              ← Phase 3 C4 diagrams
│   │   └── arc42/           ← Phase 3 arc42 chapters
│   └── development/
│       └── ${TASK_ID}_plan.json ← Phase 4 development plan (one per task)
├── architecture-docs/       ← Multi-format exports (if Phase 3 run)
│   ├── c4/
│   │   ├── c4-context.confluence
│   │   ├── c4-context.adoc
│   │   └── c4-context.html
│   └── arc42/               ← (similar structure)
├── logs/                    ← Execution logs (auto-created)
│   ├── current.log          ← Latest run
│   ├── errors.log           ← Error messages only
│   └── metrics.jsonl        ← Metrics for analysis
└── .cache/                  ← ChromaDB index (auto-created)
    └── .chroma/             ← Vector database
```

### What Stays SEPARATE

Your INPUT files are NOT in the tool's folder:

**Windows example:**
```
C:\repos\my-project\                    ← Your repository (PROJECT_PATH)
C:\work\my-project\
├── tasks\                              ← JIRA exports (TASK_INPUT_DIR)
│   ├── PROJ-123.xml                    ← JIRA XML export
│   ├── BUG-456.docx                    ← Bug report document
│   └── FEATURE-789.txt                 ← Feature request text
├── requirements\                       ← Requirements (REQUIREMENTS_DIR)
│   ├── business-requirements.xlsx
│   └── technical-spec.docx
├── logs\                               ← Application logs (LOGS_DIR)
│   ├── application.log
│   └── error-analysis.xlsx
└── reference\                          ← Reference materials (REFERENCE_DIR)
    ├── ui-mockup.pdf
    └── architecture-diagram.drawio
```

**Linux/Mac example:**
```
/home/user/repos/my-project/            ← Your repository (PROJECT_PATH)
/home/user/work/my-project/
├── tasks/                              ← TASK_INPUT_DIR
├── requirements/                       ← REQUIREMENTS_DIR
├── logs/                               ← LOGS_DIR
└── reference/                          ← REFERENCE_DIR
```

**Why separate?**
- Keeps tool outputs isolated from your source code
- Prevents accidental deletion of your source code
- Allows multiple projects with same tool installation
- Input folders can be shared across team (e.g., network drive)

---

## 9. Common Use Cases: Which Preset Should I Use?

**"What do I run for my goal?"**

| Your Goal | Preset to Use | Time | LLM? |
|-----------|---------------|------|------|
| Generate development plan from JIRA ticket | `planning_only` | 30-40 sec | Hybrid |
| Get quick architecture facts (no AI analysis) | `facts_only` | 3-5 min | No |
| Full architecture documentation (C4 + arc42) | `architecture_workflow` | 45-60 min | Yes |
| Architecture docs + development plan | `architecture_full` | 60-90 min | Yes |
| Just update the vector index | Use `index` command | 5-10 min | No |

### Examples

**Use Case 1: "I have a JIRA ticket, need a development plan"**
```bash
aicodegencrew plan
```
Output: `knowledge/development/{TASK_ID}_plan.json`

**Use Case 2: "I need C4 diagrams for architecture review"**
```bash
aicodegencrew run --preset architecture_workflow
```
Output: `knowledge/architecture/c4/*.md` + `*.drawio`

**Use Case 3: "I want component list without waiting for LLM"**
```bash
aicodegencrew run --preset facts_only
```
Output: `knowledge/architecture/architecture_facts.json` (3 min, no LLM)

See Section 11 (Quick Start) for detailed command examples

---

## 10. Quick Start

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

## 11. Commands

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

## 12. Understanding Indexing Modes

Phase 0 (Indexing) takes 2-10 minutes on first run. Subsequent runs can be faster.

### Modes Explained

| Mode | When to Use | Duration | What It Does |
|------|-------------|----------|--------------|
| `auto` | **Default** (most common) | Smart | Checks fingerprint; skips if unchanged |
| `off` | Ran yesterday, no code changes | <1 sec | Skips indexing (uses existing) |
| `smart` | Committed code changes today | 1-3 min | Re-indexes only changed files |
| `force` | Index seems corrupted/stale | Full time | Deletes cache, re-indexes everything |

### Decision Tree

```
Did you already run the tool on this repository?
├─ NO (first time)
│  └─ Use default (auto mode) - will index fully
│
├─ YES, and code changed since last run
│  └─ Use --index-mode smart
│
├─ YES, and code DIDN'T change
│  └─ Use --index-mode off (or auto, will skip automatically)
│
└─ Something seems wrong (stale data, weird results)
   └─ Use --index-mode force
```

### Examples

```bash
# First run (will index fully, 5-10 min)
aicodegencrew plan

# Second run same day, no code changes (will skip indexing, <1 sec)
aicodegencrew plan --index-mode auto

# After committing new code (will re-index changed files only, 1-3 min)
aicodegencrew plan --index-mode smart

# If results seem wrong (will wipe cache and re-index, 5-10 min)
aicodegencrew plan --index-mode force
```

**Pro Tip:** Check `.cache/.indexing_state.json` to see last index date.

---

## 13. Input Files

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

## 14. Output Files

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

#### Understanding the JSON Structure

After running `aicodegencrew plan`, you'll find development plans in `knowledge/development/`:

```
knowledge/development/
├── ${TASK_ID}_plan.json    ← One file per task (e.g., PROJ-123_plan.json)
├── ${TASK_ID}_plan.json    ← Multiple tasks = multiple files
└── ...
```

**File naming:** The `${TASK_ID}` is extracted from:
- JIRA XML exports: `<key>PROJ-123</key>`
- DOCX filename: `PROJ-123_feature_request.docx` → extracts `PROJ-123`
- TXT filename: `bug_ISSUE-456.txt` → extracts `ISSUE-456`

**Example JSON structure:**

```json
{
  "task_id": "PROJ-123",                              ← Matches filename
  "title": "Implement user authentication",           ← From JIRA summary or doc title
  "affected_components": [...]  ← Which code files/classes to modify
  "implementation_steps": [...]  ← Step-by-step coding instructions
  "test_strategy": {
    "similar_patterns": [...]    ← Existing tests to follow as examples
  },
  "security_considerations": [...] ← Security patterns to apply
  "validation_strategy": [...]   ← Input validation rules
  "error_handling": [...]        ← Error handling patterns
  "upgrade_plan": {              ← If upgrade task (e.g., Angular 18→19)
    "framework": "Angular",
    "from_version": "18",
    "to_version": "19",
    "migration_sequence": [...]  ← Step-by-step upgrade rules with affected_files
  },
  "risks": [...],
  "complexity_estimate": "..."
}
```

**Which section should I read first?**
- For coding: `implementation_steps`
- For testing: `test_strategy.similar_patterns`
- For security review: `security_considerations`
- For framework upgrades: `upgrade_plan.migration_sequence`

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

## 15. Presets

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

## 16. Environment Variables

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

## 17. Docker Usage

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

## 18. Network Connectivity Diagnostics

Before running the tool, verify all connections work.

### Test 1: Ollama is Reachable

```bash
curl http://127.0.0.1:11434/api/tags
```

**Expected:** JSON response with installed models
```json
{"models":[{"name":"nomic-embed-text:latest",...}]}
```

**If error:**
- `Connection refused`: Ollama not running. Run: `ollama serve`
- `Timeout`: Port 11434 blocked. Check firewall.

### Test 2: LLM Endpoint is Reachable

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     http://your-llm-server:4000/v1/models
```

**Expected:** JSON list of available models

**If error:**
- `Timeout`: LLM server down or network blocked. Check VPN/proxy.
- `Connection refused`: Wrong port. Verify API_BASE in .env.

### Test 3: API Key is Valid

```bash
curl -X POST http://your-llm-server:4000/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-oss-120b", "messages": [{"role": "user", "content": "test"}]}'
```

**Expected:** Response starts (even if incomplete)

**If "invalid key":**
- Update `OPENAI_API_KEY` in .env
- Verify key with your IT admin

**All tests passed?** Proceed to Quick Start (Section 11)

**Tests failed?** See Troubleshooting (Section 19)

---

## 19. Troubleshooting

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

## 20. FAQ

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
