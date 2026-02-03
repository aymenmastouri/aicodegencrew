# AI Code Generation Crew

AI-powered SDLC automation using CrewAI. Automatically generates C4 diagrams and arc42 documentation from your codebase.

---

## Quick Install (From Scratch)

### Step 1: Install uv (Package Manager)

```powershell
# Windows PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Step 2: Install Ollama (for Embeddings)

Download from: https://ollama.com/download

```bash
# Pull embedding model
ollama pull all-minilm:latest
```

### Step 3: Clone & Setup

```powershell
git clone <repo-url> aicodegencrew
cd aicodegencrew
```

### Step 4: Configure

```powershell
copy .env.example .env
```

Edit `.env`:

```env
# Your repository to analyze
PROJECT_PATH=C:\path\to\your\repo

# LLM Provider: "local" (Ollama) or "onprem" (Capgemini)
LLM_PROVIDER=onprem

# On-Prem Capgemini
MODEL=gpt-oss-120b
API_BASE=http://sov-ai-platform.nue.local.vm:4000/v1
OPENAI_API_KEY=your-api-key-here

# First run: auto, subsequent: off
INDEX_MODE=auto
```

### Step 5: Run

```powershell
crewai run
```

That's it! The crew will:
1. Index your codebase (first run only)
2. Extract architecture facts (components, relations, integrations)
3. Generate C4 diagrams + arc42 documentation

Output: `./knowledge/architecture/`

---

## Documentation

- [Architecture Details](docs/AI_SDLC_ARCHITECTURE.md)
- [Diagrams](docs/diagrams/)

---

## Table of Contents

1. [Quick Install](#quick-install-from-scratch)
2. [Running Phases](#2-running-phases)
3. [Configuration](#3-configuration)
4. [Project Structure](#4-project-structure)
5. [CLI Reference](#5-cli-reference)
6. [Knowledge Management](#6-knowledge-management)
7. [Troubleshooting](#7-troubleshooting)
8. [Development](#8-development)
9. [License](#9-license)

---

## 2. Running Phases

The SDLC pipeline consists of 8 phases (0-7). Use the unified CLI to run phases.

### 2.1 Available Phases

| Phase | Name | Type | Description |
|-------|------|------|-------------|
| 0 | Indexing | Pipeline | Index codebase into ChromaDB (embeddings only, no LLM) |
| 1 | Facts | Pipeline | Extract architecture facts (deterministic, no LLM) |
| 2 | Synthesis | Crew | AI generates C4 + arc42 documentation from facts |
| 3 | Review | Crew | Consistency check and quality review (planned) |
| 4 | Development | Crew | Backlog generation and planning (planned) |
| 5 | Codegen | Crew | Code generation from specs (planned) |
| 6 | Testing | Crew | Test generation (planned) |
| 7 | Deployment | Pipeline | CI/CD and deployment configs (planned) |

### 2.2 Presets (Recommended)

```bash
# List all phases and presets
python -m aicodegencrew list

# Index repository only (Phase 0)
python -m aicodegencrew run --preset indexing_only

# Index + extract facts (Phase 0+1, no LLM required)
python -m aicodegencrew run --preset facts_only

# Full architecture documentation (Phase 0+1+2)
python -m aicodegencrew run --preset architecture_workflow

# Skip re-indexing if already indexed
python -m aicodegencrew run --preset architecture_workflow --index-mode off

# Force clean re-index
python -m aicodegencrew run --preset architecture_workflow --index-mode force --clean
```

### 2.3 Running Individual Phases

```bash
# Run specific phases by name
python -m aicodegencrew run --phases phase0_indexing
python -m aicodegencrew run --phases phase1_architecture_facts
python -m aicodegencrew run --phases phase2_architecture_synthesis

# Run multiple phases
python -m aicodegencrew run --phases phase0_indexing phase1_architecture_facts

# Clean output before running (deletes previous results)
python -m aicodegencrew run --phases phase2_architecture_synthesis --clean
```

### 2.4 Phase Dependencies

Phases have dependencies that must be satisfied:

- Phase 1 requires Phase 0 (needs index)
- Phase 2 requires Phase 1 (needs `architecture_facts.json`)
- Phase 3+ require Phase 2 (needs synthesized docs)

If a dependency is not met, you'll see:
```
[WARN] Dependency not met: phase2_architecture_synthesis requires phase1_architecture_facts
```

Use a preset like `architecture_workflow` to run all required phases automatically.

### 2.5 Output Locations

| Phase | Output |
|-------|--------|
| 0 | `.cache/.chroma/` (ChromaDB vector store) |
| 1 | `knowledge/architecture/architecture_facts.json`, `evidence_map.json` |
| 2 | `knowledge/architecture/c4/*.md`, `*.drawio`, `arc42/*.md` |
| 3+ | `knowledge/` subdirectories (planned) |

### 2.6 Example Workflow

```bash
# First time setup: full workflow
python -m aicodegencrew run --preset architecture_workflow

# After code changes: re-run facts + synthesis
python -m aicodegencrew run --preset architecture_workflow --index-mode smart

# Just regenerate docs (facts already exist)
python -m aicodegencrew run --phases phase2_architecture_synthesis --clean

# Standalone indexing
python -m aicodegencrew index --force

# Convert Draw.io files after Phase 2
python -m aicodegencrew.shared.utils.drawio_converter knowledge/architecture
```

---

## 3. Configuration

### 2.1 INDEX_MODE

| Mode | Description | Use Case |
|------|-------------|----------|
| `off` | Skip indexing, use existing index | CI/CD, quick iterations |
| `auto` | Index only if needed | Normal development |
| `force` | Clear cache, complete re-index | After model changes |
| `smart` | Update changed files only | Large codebases |

### 2.2 Embedding Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `EMBED_MODEL` | Embedding model | `all-minilm:latest` |
| `EMBED_BATCH_SIZE` | Batch processing size | `50` |
| `EMBED_MAX_BATCH_SIZE` | Maximum batch size | `100` |
| `EMBED_PAUSE_S` | Pause between batches | `1.0` |

### 2.3 LLM Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `MODEL` | LLM model identifier | `gpt-oss-120b` |
| `API_BASE` | API endpoint | `http://sov-ai-platform.nue.local.vm:4000/v1` |
| `MAX_LLM_OUTPUT_TOKENS` | Output token limit | `800` |

### 2.4 Model Context Windows

Different models have different context limits. The new architecture avoids token limits entirely.

**New Architecture (v2.0):**

| Phase | Method | Token Usage | Duration |
|-------|--------|-------------|----------|
| A: RAG Analysis | Direct Python | None (no LLM) | 5-30 min |
| B: Documentation | LLM Agent | ~8K tokens | 2-5 min |
| C: Quality Gate | LLM Agent | ~5K tokens | 1-2 min |

**Phase A: Comprehensive RAG Analysis**
- Runs 55+ semantic queries against ChromaDB
- Collects 200-500 evidence items
- No token limits - runs in pure Python
- Creates `analyze.json` with full analysis

**Phase B+C: Agent Documentation**
- Agents receive pre-computed `analyze.json`
- Only need to format and validate
- Minimal token usage

**RAG Query Categories (55 queries total):**

| Category | Queries | Purpose |
|----------|---------|---------|
| Backend (Java/Spring) | 10 | Controllers, Services, Repositories |
| Backend (Node/Python/.NET) | 8 | Express, FastAPI, Django, .NET |
| Frontend | 7 | Angular, React, Vue, Next.js |
| Database | 4 | Entities, Migrations, ORM |
| Messaging | 4 | Kafka, RabbitMQ, Events |
| Infrastructure | 6 | Docker, K8s, CI/CD |
| Configuration | 4 | Properties, Dependencies |
| Security | 3 | Auth, JWT, CORS |
| Cross-Cutting | 5 | Logging, Tests, Docs |

**Legacy Mode (for debugging):**

Use `run_legacy()` to let the LLM agent do RAG queries directly.
Note: May hit token limits with large repos.

```python
# In crew.py
crew = ArchitectureCrew()
result = crew.run_legacy(inputs)  # Agent-controlled RAG
```

### 2.5 Indexing Limits

| Variable | Description | Default |
|----------|-------------|---------|
| `INDEX_MAX_TOTAL_FILES` | Maximum files to index | `10000` |
| `INDEX_MAX_TOTAL_CHUNKS` | Maximum chunks to store | `100000` |
| `CHUNK_CHARS` | Chunk size (characters) | `1200` |
| `CHUNK_OVERLAP` | Chunk overlap (characters) | `150` |

---

## 4. Project Structure

```
aicodegencrew/
    .env
    pyproject.toml
    
    config/
        phases_config.yaml
    
    docs/diagrams/
        phase-flow.drawio
        evidence-flow.drawio
        knowledge-structure.drawio
        collectors.drawio
        synthesis-crew.drawio
    
    logs/
        current.log            # Active session
        errors.log             # Persistent errors (rotating)
        archive/               # Archived sessions
    
    src/aicodegencrew/
        __init__.py
        __main__.py            # Entry point: python -m aicodegencrew
        cli.py                 # Unified CLI (run, index, list)
        orchestrator.py
        
        crews/
            architecture/              # Legacy (deprecated)
            architecture_synthesis/    # Phase 2: Architecture Synthesis
            development/               # Phase 4: Planned
        
        pipelines/
            indexing.py                # Phase 0: Indexing
            architecture_facts/        # Phase 1: Architecture Facts
            tools/
        
        shared/
            utils/
            models/
            tools/
    
    knowledge/
        architecture/
            architecture_facts.json    # Phase 1 output
            evidence_map.json          # Phase 1 output
            c4/                        # Phase 2 output
            arc42/                     # Phase 2 output
        development/
    
    .cache/.chroma/
```

---

## 5. CLI Reference

Unified CLI with subcommands:

```bash
python -m aicodegencrew <command> [options]
```

### 5.1 run - Execute Pipeline

```bash
python -m aicodegencrew run [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--preset NAME` | Run preset (indexing_only, facts_only, architecture_workflow) |
| `--phases PHASE...` | Run specific phases |
| `--repo-path PATH` | Override PROJECT_PATH |
| `--index-mode MODE` | Override INDEX_MODE (off, auto, force, smart) |
| `--clean` | Clean knowledge directories before running |
| `--no-clean` | Skip auto-cleaning |
| `--config PATH` | Custom phases_config.yaml |

### 5.2 index - Repository Indexing

```bash
python -m aicodegencrew index [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--mode, -m MODE` | Indexing mode (off, auto, force, smart) |
| `-f, --force` | Force re-index (clears cache) |
| `-s, --smart` | Smart incremental update |
| `--repo PATH` | Override PROJECT_PATH |

### 5.3 list - Show Phases

```bash
python -m aicodegencrew list
```

Shows all available phases and presets.

### 5.4 Presets

| Preset | Phases | Description |
|--------|--------|-------------|
| `indexing_only` | 0 | Repository indexing only |
| `facts_only` | 0, 1 | Indexing + Architecture Facts (no LLM) |
| `architecture_workflow` | 0, 1, 2 | Full architecture documentation |
| `planning_workflow` | 0, 1, 2 | Alias for architecture_workflow |

---

## 6. Knowledge Management

### 5.1 Directory Structure

```
knowledge/
    README.md
    user_preference.txt
    architecture/
        architecture_facts.json    # Phase 1 (truth)
        evidence_map.json          # Phase 1 (evidence)
        c4/                        # Phase 2
        arc42/                     # Phase 2
        runtime/                   # Phase 2
        evidence/                  # Phase 2
        quality/                   # Phase 2/3
    analysis/
    development/
```

### 5.2 Phase Outputs

| Phase | Output Location | Content |
|-------|-----------------|---------|
| 0 | `.cache/.chroma/` | ChromaDB vector index |
| 1 | `knowledge/architecture/` | architecture_facts.json, evidence_map.json |
| 2 | `knowledge/architecture/c4/`, `arc42/` | C4 diagrams, arc42 documentation |

### 5.3 Custom Knowledge Sources

Place files in the `knowledge/` directory to provide additional context:

| File | Purpose |
|------|---------|
| `project-guidelines.txt` | Coding standards |
| `architecture-decisions.txt` | Architecture Decision Records |
| `api-documentation.txt` | API specifications |

---

## 7. Troubleshooting

### 6.1 Ollama Connection

```bash
curl http://127.0.0.1:11434/api/tags
ollama serve
ollama list
```

### 6.2 Embedding Errors

Reduce batch size in `.env`:

```env
EMBED_BATCH_SIZE=10
EMBED_MAX_BATCH_SIZE=20
```

### 6.3 ChromaDB Dimension Mismatch

Clear cache after changing embedding models:

```bash
rmdir /s /q .cache\.chroma
python -m aicodegencrew index --force
```

### 6.4 Memory Issues

Reduce indexing limits:

```env
INDEX_MAX_TOTAL_FILES=2000
INDEX_MAX_TOTAL_CHUNKS=20000
EMBED_BATCH_SIZE=20
```

---

## 8. Development

### 7.1 Installation

```bash
pip install -e ".[dev]"
```

### 7.2 Testing

```bash
pytest
pytest tests/test_indexing.py -v
```

### 7.3 Code Quality

```bash
black src/ tests/
ruff check src/ tests/
```

### 7.4 Logging Standards

**No emojis in log messages.** Use text prefixes for consistency across terminals:

| Status | Prefix | Example |
|--------|--------|---------|
| Success | `[OK]` | `logger.info("[OK] Phase 1 complete")` |
| Error | `[ERROR]` | `logger.error("[ERROR] File not found")` |
| Warning | `[WARN]` | `logger.warning("[WARN] Skipping...")` |
| Info | `[Phase1]` | `logger.info("[Phase1] Processing...")` |
| Missing | `[MISSING]` | `logger.error("[MISSING] facts.json")` |
| Hint | `[HINT]` | `logger.info("[HINT] Try running...")` |

---

## 9. License

Proprietary and confidential. For Capgemini internal use only.

See [LICENSE](LICENSE) for details.

### 8.1 Third-Party Components

This project depends on third-party open-source components. License information is available via:

- Dependency manifests (`pyproject.toml`, `uv.lock`)
- Component documentation and repositories
- Installed package metadata
