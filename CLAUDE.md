# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AICodeGenCrew is an AI-powered SDLC automation platform. It analyzes existing repositories and generates architecture documentation, development plans, and code. Runs entirely on-premises with local LLMs (gpt-oss-120b via OpenAI-compatible API, embeddings via Ollama).

**Stack**: Python 3.12, CrewAI, FastAPI (port 8001), Angular 21 (port 4200), ChromaDB

## Common Commands

```bash
# Development servers (backend + frontend)
npm run dev                           # or: ./scripts/dev.sh start
./scripts/dev.sh stop                 # clean stop + kill orphan processes

# Backend only
cd ui/backend && python main.py       # port 8001

# Frontend only
cd ui/frontend && npm start           # port 4200 (proxy → 8001)
# NEVER use "ng serve" directly — requires proxy.conf.json from "npm start"

# Tests (786+, ~42s)
pytest tests/ -q --ignore=tests/test_delivery.py   # standard run
pytest tests/test_development_planning.py -v        # single file
pytest tests/ -m phase0                             # by marker (phase0-phase5, e2e, slow)

# Lint & format
ruff check src/ tests/ ui/backend
ruff format src/ tests/ ui/backend
cd ui/frontend && npm run lint

# Pipeline CLI
python -m aicodegencrew run --preset plan           # full planning pipeline
python -m aicodegencrew run --phases triage plan     # specific phases
python -m aicodegencrew run --phases triage --task-id TASK-123  # single task
python -m aicodegencrew index --force               # re-index target repo
python -m aicodegencrew list                        # list phases/presets
```

## Architecture

### 9 SDLC Phases

```
KNOWLEDGE (deterministic)        REASONING (hybrid AI)             EXECUTION
discover → extract               analyze → document → triage → plan   implement → verify → deliver
  Phase 0    Phase 1              Phase 2   Phase 3    Phase 4  Phase 5  Phase 6    Phase 7  Phase 8
```

### Phase Types
- **Pipeline** (deterministic): discover, extract — stages run sequentially, no LLM
- **Crew** (multi-agent AI): analyze, document, verify — CrewAI agents collaborate
- **Hybrid** (pipeline + 1 LLM call): triage, plan, implement, deliver — deterministic stages + single LLM synthesis

### Key Source Directories

| Directory | Purpose |
|-----------|---------|
| `src/aicodegencrew/cli.py` | CLI entry point, subcommand parsing |
| `src/aicodegencrew/orchestrator.py` | Phase execution engine, dependency resolution |
| `src/aicodegencrew/phase_registry.py` | Single source of truth for phase metadata (PHASES dict) |
| `src/aicodegencrew/pipelines/` | Deterministic pipelines (discover, extract) |
| `src/aicodegencrew/crews/` | CrewAI crews (analyze, document, triage, verify, deliver) |
| `src/aicodegencrew/hybrid/` | Hybrid pipelines (plan, implement) |
| `src/aicodegencrew/shared/utils/phase_state.py` | Persistent execution state with file locking |
| `ui/backend/` | FastAPI server — routers/, services/ |
| `ui/frontend/src/app/pages/` | Angular pages (dashboard, run-pipeline, tasks, history, etc.) |
| `config/phases_config.yaml` | Phase enable/disable, preset definitions |

### Data Flow

```
inputs/tasks/           → triage → plan → implement → verify → deliver
knowledge/discover/     → extract → analyze → document
knowledge/{phase}/      ← output per phase (JSON, Markdown)
logs/phase_state.json   ← execution state (written by orchestrator, read by dashboard)
```

### Parallel Task Execution

Each task can run as its own subprocess for triage + plan phases:
- CLI: `--task-id TASK-123` filters to one task per subprocess
- Backend: `PipelineExecutor.start_parallel_tasks()` spawns N subprocesses via ThreadPoolExecutor
- Frontend: Task selection UI + per-task progress chips
- State: `_task_states` dict with per-task status, guarded by `_task_states_lock`

### Dashboard Communication

- **REST API**: `/api/pipeline/run`, `/api/pipeline/status`, `/api/pipeline/history`
- **SSE**: `/api/pipeline/stream` for real-time log lines + status updates
- **Polling**: Dashboard polls `/api/pipeline/status` for live metrics
- **Proxy**: Frontend `proxy.conf.json` routes `/api/*` to backend port 8001

## Important Patterns

### Phase Registration (adding a new phase)
1. Register in `phase_registry.py` with `PhaseDescriptor`
2. Create module in `{pipelines,crews,hybrid}/`
3. Implement `kickoff(inputs: dict) -> dict` protocol
4. Add to `config/phases_config.yaml` + presets
5. Register in `cli.py` for CLI execution

### Dependency Resolution (2-tier)
1. Did dependency succeed **in this session**? (in-memory)
2. Do output artifacts exist **on disk**? (fallback)

### Checkpoint Resume
Long-running phases (plan, implement) save `.checkpoint_*.json` after each task. On resume, completed tasks are skipped if output file still exists on disk.

### File Locking
`phase_state.py` uses `filelock.FileLock` for cross-process safety when parallel subprocesses write to `phase_state.json`.

## Known Gotchas

- `ng serve` without proxy → API calls return Angular HTML (use `npm start`)
- Port conflicts: `./scripts/dev.sh stop` handles orphan processes on Windows
- `phases_config.yaml` `enabled: false` silently filters phases from pipeline
- CrewAI `output_pydantic` doesn't work with on-prem LLM — avoid it
- LLM invents tool parameters — always add `**kwargs` to tool `_run()` methods
- Prompts must use generic tech references (FrameworkX, not Angular) — agent works on any codebase
- `discover` phase is `resettable=False` — never delete its output
- Windows: use `.\gradlew.bat` with `shell=True` for Gradle builds
- Ghost sockets on Windows (PID dead, port LISTENING) — `scripts/dev.sh restart` handles it
