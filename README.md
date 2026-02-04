# AI Code Generation Crew

AI Code Generation Crew is an on‑premises toolkit that automates evidence‑based architecture discovery and documentation for software repositories. It extracts deterministic architecture facts from a codebase, then synthesizes C4 diagrams and arc42 documentation using configurable local LLMs.

This repository focuses on a secure, reproducible, and auditable SDLC workflow where every claim in generated documentation is traceable to source code evidence.

Key principles:
- Evidence‑first: every generated item must reference code/config evidence.
- Deterministic discovery: facts are extracted by deterministic collectors (no LLM).
- Phase isolation: clear inputs/outputs per pipeline phase.
- On‑prem operation: designed for local LLMs and no external data leakage.

Contents
- [Quick Start](#quick-start)
- [Concepts & Phases](#concepts--phases)
- [Configuration](#configuration)
- [CLI & Usage](#cli--usage)
- [Outputs](#outputs)
- [Contributing](#contributing)
- [License](#license)
- [Further Documentation](#further-documentation)

## Quick Start

Prerequisites
- Python 3.10+ (recommended)
- Local embedding/LLM runtime (e.g. Ollama) if running synthesis phases

Clone and prepare

```powershell
git clone <repo-url> aicodegencrew
cd aicodegencrew
copy .env.example .env
```

Configure `.env` (example values)

```env
# Path to repository you want to analyze
PROJECT_PATH=C:\path\to\your\repo

# Choose LLM provider: "local" (Ollama) or "onprem" (enterprise endpoint)
LLM_PROVIDER=local
MODEL=all-minilm:latest
INDEX_MODE=auto
```

Install and prepare embedding/model runtimes as required by your environment (e.g. install Ollama and pull an embedding model).

Run the full architecture workflow

```powershell
python -m aicodegencrew run --preset architecture_workflow
```

Run only indexing and facts extraction (no LLM required)

```powershell
python -m aicodegencrew run --preset facts_only
```

## Concepts & Phases

The pipeline is organized into phased steps. Phases 0–2 are implemented and stable; later phases are planned.

- Phase 0 — Indexing (pipeline): create vector index (Chroma) for repository content.
- Phase 1 — Architecture Facts (pipeline): deterministic collectors extract components, containers, interfaces, relations and build `architecture_facts.json` + `evidence_map.json` (NO LLM).
- Phase 2 — Architecture Synthesis (crew): AI agents synthesize C4 diagrams and arc42 documentation from facts and analysis (uses local LLMs).
- Phases 3–7 — Review, Development, Codegen, Testing, Deployment: designed, planned for future work.

Important rule: Phase 2 may only synthesize items that are present (or marked UNKNOWN) in Phase 1 outputs. The system enforces evidence traceability; generated documentation must reference evidence IDs internally.

## Configuration

Key environment variables (set in `.env`)

- `PROJECT_PATH`: repository to analyze
- `LLM_PROVIDER`: `local` or `onprem`
- `MODEL`: LLM/embedding model identifier
- `INDEX_MODE`: `off`, `auto`, `force`, `smart`

Indexing limits and chunking settings are configurable in `shared` utilities and `phases_config.yaml`.

## CLI & Usage

Top‑level commands

```powershell
python -m aicodegencrew <command> [options]
```

Common commands
- `run` — execute phases or presets (`--preset architecture_workflow`, `--phases`)
- `index` — run indexing only (`--mode force|smart`)
- `list` — show phases and presets

Examples

```powershell
# Full architecture workflow (index + facts + synthesis)
python -m aicodegencrew run --preset architecture_workflow

# Index only
python -m aicodegencrew run --preset indexing_only

# Run specific phases
python -m aicodegencrew run --phases phase0_indexing phase1_architecture_facts
```

## Outputs

Primary outputs are written to `knowledge/architecture/`:

- `architecture_facts.json` — canonical facts (phase 1)
- `evidence_map.json` — mapping from evidence IDs to file paths and line ranges
- `c4/` — generated C4 markdown + Draw.io files
- `arc42/` — generated arc42 chapter markdown files

Use these artifacts to review, validate, and iterate on architecture decisions. Evidence IDs are internal and ensure traceability from docs back to source code.

## Contributing

We welcome contributions. Suggested workflow:

1. Fork the repository and create a feature branch.
2. Run unit tests and linters.
3. Open a pull request describing the change and rationale.

See `tests/` for the current test suite and `config/phases_config.yaml` for configurable phase behavior.

## License

This project is provided under the terms in the `LICENSE` file.

## Further Documentation

See the detailed SDLC architecture and design notes:

- [AI SDLC Architecture](docs/AI_SDLC_ARCHITECTURE.md)
- Architecture analysis and diagrams: `docs/diagrams/`

If you want, I can stage and commit this change and provide the exact git commands to push it.

---

## Implementation notes for maintainers

- Phase 1 collectors are deterministic and must not use LLMs; Phase 2 performs synthesis with LLMs using the analyze→synthesize pattern.
- Keep evidence-first rules in mind when modifying synthesis code paths.


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
