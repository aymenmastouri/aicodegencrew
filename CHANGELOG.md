# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [0.3.0] - 2026-02-12

### Added

**Pipeline Reset & Run History**
- Full pipeline reset with per-phase and reset-all support
- Cascade propagation: resetting a phase automatically resets all dependent phases (e.g., Phase 1 → Phase 2-5)
- Archive before delete: outputs are backed up to `knowledge/archive/reset_YYYYMMDD_HHMMSS/` before deletion
- Persistent run history via append-only JSONL (`logs/run_history.jsonl`) — replaces overwritten `run_report.json`
- Legacy fallback: history endpoint reads from `run_report.json` + archive when JSONL is empty
- Reset preview endpoint (dry-run) shows affected phases and files before execution
- Safety: reset blocked (409) while pipeline is running
- Backend: `reset` router with 3 endpoints (`/api/reset/preview`, `/api/reset/execute`, `/api/reset/all`)
- Backend: `history_service` (JSONL append/read) and `reset_service` (cascade/archive/delete)
- Frontend: Reset buttons on Phases page (per-phase + "Reset All" in header) with confirm dialog showing cascade preview
- Frontend: Run/Reset type column in Run History table with colored chips (blue=Run, red=Reset)
- 31 backend unit tests covering history, reset, cascade, schemas, and router endpoints
- Updated Playwright e2e specs for phases and run-pipeline pages

**Developer Experience: Reports Page Rewrite**
- Structured plan viewer with affected components table, implementation steps, test strategy, collapsible security/validation/error/architecture sections
- Code diff viewer with per-file expandable unified diffs (green/red/blue line coloring), action chips (created/modified/deleted), language badges
- Git branch management tab — list `codegen/*` branches, file count, report indicator, delete with confirmation
- "Show Raw JSON" toggle per plan/report for debugging
- Backend: `GET /api/reports/branches`, `DELETE /api/reports/branches/{task_id}` endpoints
- Backend: Branch list via `git branch --list codegen/*`, file count via `git diff --name-only`

**Input Files Management**
- New Input Files page (`/inputs`) with drag-and-drop upload
- 4 categories: tasks (JIRA exports), requirements (specs), logs (traces), reference (mockups)
- Extension validation per category, 20 MB size limit, filename sanitization
- Auto-configuration of `TASK_INPUT_DIR`, `REQUIREMENTS_DIR`, `LOGS_DIR`, `REFERENCE_DIR` in `.env`
- Backend: `inputs` router with 6 endpoints (list, summary, categories, upload, delete)
- Supplementary files support in Phase 4 — requirements, logs, and reference files injected into LLM prompt

**Dashboard Redesign**
- Hero section with gradient background, app title with colored accents, status pills
- Phase status cards with color-coded left border, phase number indicator, output badges
- Active pipeline banner with animated progress
- Reduced quick links from 7 to 3 focused action cards
- OnPush change detection for better performance

**Knowledge Explorer Rewrite**
- Multi-tab interface: Arc42 Docs, C4 Model, Knowledge Base, Containers, Dev Plans, Other
- Document rendering: Markdown (via marked), JSON (syntax-highlighted), HTML (sanitized), AsciiDoc, Confluence wiki, DrawIO metadata
- File grid view with stats bar showing file type counters
- Source/rendered mode toggle per document

**Frontend Infrastructure**
- Upgraded Angular 19 → 21 (zoneless change detection)
- Added Tailwind CSS with Capgemini custom theme
- Grouped sidebar navigation (Operations, Explore, Monitor)
- Sidenav footer with version badge

**Backend Improvements**
- Preset metadata format: `display_name`, `description`, `icon` per preset in `phases_config.yaml`
- Backward-compatible preset parsing in orchestrator
- Phase status logic: completed/ready/planned (was completed/idle)

---

## [0.2.0] - 2026-02-11

### Added

**Code Generation (Phase 5)**
- Hybrid 5-stage pipeline (4 deterministic + 1 LLM call per file)
- Strategy pattern: FeatureStrategy, BugfixStrategy, UpgradeStrategy, RefactoringStrategy
- Plan reader with automatic file path resolution from architecture_facts.json
- Context collector: reads source files, detects language, finds sibling files, extracts patterns
- Code validator: syntax checks (balanced braces), security scan (hardcoded secrets, SQL injection, XSS, eval), pattern compliance
- Output writer with git branch isolation (`codegen/{task_id}`), explicit staging, and failure threshold (>50% abort)
- Safety features: dry-run mode (`--dry-run`), dirty tree check, never pushes to remote, never touches main
- Unified diff generation for modified files
- JSON report per task in `knowledge/codegen/{task_id}_report.json`
- CLI `codegen` command with `--task-id` and `--dry-run` options
- Configurable: `CODEGEN_CALL_DELAY`, `CODEGEN_MAX_RETRIES` environment variables
- `codegen_only` preset (Phases 0+1+2+4+5)

**SDLC Dashboard (Web UI)**
- Full web-based dashboard: Angular 19 (frontend) + FastAPI (backend)
- Pipeline execution from UI: trigger presets or custom phase combinations
- Real-time log streaming via Server-Sent Events (SSE)
- Environment configuration panel: edit .env variables grouped by category (Repository, LLM, Embeddings, Indexing, Phase Control, Output, Logging)
- Phase progress timeline with status indicators and durations
- Knowledge base browser with file preview (JSON, Markdown, DrawIO)
- Metrics viewer with event filtering
- Log viewer with color-coded levels (ERROR/WARNING/INFO)
- Development plans and codegen reports viewer
- Run history from run_report.json
- Subprocess isolation: pipeline runs as child process (crash-safe)
- Singleton guard: only one pipeline at a time (409 Conflict)
- Cancel running pipeline (SIGTERM → SIGKILL fallback)
- Docker Compose deployment with nginx reverse proxy
- SSE-specific nginx config (proxy_buffering off, 1h timeout)
- 8 REST API routers: phases, knowledge, metrics, reports, logs, diagrams, pipeline, env (expanded to 11 in 0.3.0)

---

## [0.1.0] - 2026-02-09

### Added

**Architecture Pipeline (Phases 0-3)**
- Phase 0: Repository indexing into ChromaDB with 4 modes (off/auto/smart/force)
- Phase 1: Deterministic architecture facts extraction (951 components, 226 interfaces, 190 relations)
- Phase 2: Multi-agent AI analysis (4 specialists + Map-Reduce for large repos)
- Phase 3: C4 Model + arc42 document synthesis (Mini-Crews pattern, 18+ crews)
- MCP server for live architecture queries
- DrawIO diagram generation alongside Markdown docs

**Development Planning (Phase 4)**
- Hybrid 5-stage pipeline (4 deterministic + 1 LLM call)
- JIRA XML, DOCX, Excel, text/log input parsing
- Component discovery via RAG + multi-signal scoring
- Pattern matching: TF-IDF on 925 test patterns, 143 security, 149 validation, 23 error patterns
- Upgrade Rules Engine: 40 rules for Angular, Spring, Java, Playwright
- Multi-file processing with content-based sorting (priority, type, dependencies)
- Linked task extraction from JIRA issue links, subtasks, and description references

**CLI & Deployment**
- Unified CLI with `run`, `plan`, `index`, `list` commands
- Global `--env` flag for custom .env file path
- `plan` shortcut command (Phases 0+1+2+4)
- 7 execution presets (indexing_only through full_pipeline)
- Multi-stage Dockerfile (no source code in final image)
- docker-compose.yml with volume mounts for easy deployment
- Build release script (`scripts/build_release.py`)

**Reliability & Observability**
- Checkpoint & resume for all crews
- Retry with exponential backoff on LLM connection failures
- Tool guardrails (loop prevention, call budgets)
- Structured metrics logging (`logs/metrics.jsonl`)
- Session correlation via run_id
- Run reports exported to `knowledge/run_report.json` after each pipeline execution
- Configurable output directory via `OUTPUT_BASE_DIR` environment variable

**Multi-Format Export**
- Automatic conversion of architecture docs to Confluence, AsciiDoc, and HTML formats
- Export to `architecture-docs/` directory with all formats included

**Testing**
- Comprehensive test suite: 603 tests across 16 test files
- Unit tests (13 files), integration tests, scenario tests, delivery tests
- Test categories: CLI, orchestrator, parsers, validation, logger, guardrails, converters

### Fixed

**Phase 3 (Architecture Synthesis)**
- Fixed template variable injection: `{system_summary}` placeholders now properly filled with real architecture statistics
- Arc42 Chapter 01 (Introduction) now generates complete content (137 lines) instead of minimal stub
- C4 and Arc42 crews now call `_summarize_facts()` and format task descriptions correctly

**Phase 4 (Development Planning)**
- Added `UpgradePlan` and `UpgradeRule` Pydantic models to `DevelopmentPlan` schema
- Fixed upgrade plan schema to include `framework`, `from_version`, `to_version` fields
- Fixed `affected_files` population in migration_sequence from UpgradeRulesEngine
- Enhanced LLM prompt to explicitly copy `affected_files` from migration sequence
- Added affected file paths to prompt formatting (shows first 10 files per rule)
- Upgrade plans now include:
  - Clear version information (e.g., "Angular 18 → 19")
  - 15+ migration rules with severity levels (breaking/deprecated/recommended)
  - Real file paths for affected files (142+ files for standalone components, 88 files for control flow, etc.)
  - Accurate effort estimation per rule
  - Migration steps and schematics per rule
