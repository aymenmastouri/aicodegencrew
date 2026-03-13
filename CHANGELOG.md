# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [0.7.4] - 2026-03-13

### Security

- Remove real API keys from `.env.run` (file deleted from distribution)
- Add XXE protection to XML parser (file size limit + defusedxml support)
- Add DOMPurify HTML sanitization in Knowledge and Reports components (XSS fix)
- Add symlink rejection to all path traversal checks (backend)
- Sanitize backend error messages — no longer leak internal details to clients
- Validate `env_overrides` in pipeline RunRequest (block system variable injection)
- URL-encode Git credentials to prevent special character leaks
- Harden nginx CSP: add `object-src 'none'; base-uri 'self'; form-action 'self'`

### Fixed

- **Pipeline LLM failure**: Add `litellm` as required dependency (`crewai[tools,litellm]>=1.10.1`) — fixes "Unable to initialize LLM with model 'openai/...'" error
- Upgrade `crewai` 1.9.3 → 1.10.1, `openai` 1.83.0 → 1.109.1
- `LOG_LEVEL` validation crash: invalid values now fall back to INFO instead of AttributeError
- `start.bat`: Add Docker Compose v1/v2 detection (matching `start.sh` behavior)
- `docker-compose.yml`: Add default for `TASK_INPUT_DIR` to prevent startup failure
- `build_release.py`: Add file existence checks before copy, fix `install.sh` missing chmod
- Fix 3 pre-existing test failures caused by environment variable pollution

### Changed

- Make corporate CA certificate optional in Dockerfiles (build no longer fails without cert)
- Make timezone configurable via `TZ` env var in all docker-compose files
- Replace hardcoded Capgemini LLM URLs in `.env.example` with generic examples
- Fix misleading "Production" comment in `Dockerfile.dev`
- Remove internal domain reference from `docker-compose.yml` comment

## [0.7.2] - 2026-03-06

### Changed

- Version is now single-sourced from `pyproject.toml` — no more hardcoded versions
- Frontend footer version loaded dynamically from `/api/health` endpoint
- Updated README badge, docs, and e2e tests to use dynamic version

### Fixed

- Demo fixes: parallel phase status, Run Pipeline wait, faster completion detection

## [0.7.1] - 2026-02-21

Deep audit of all pipeline phases — 64 bugs fixed across Phases 2-5. Demo rewritten for managers.

### Fixed

**Phase 2 — Architecture Facts Extraction (32 bugs in 21 collector files)**

*Critical (5 broken exported collectors — complete rewrites):*
- `SpringSecurityCollector`: wrong field names, missing dimension, bypassed file cache
- `AngularStateCollector`: same pattern, `rglob` without SKIP_DIRS pruning
- `OracleSchemaCollector`: `.upper()` corrupting extracted names, wrong field names
- `OracleProcedureCollector`: `RelationHint(relation_type=)` → `type=`
- `OracleViewCollector`: `columns=list[str]` → `list[dict]`

*High (13 pipeline bugs):*
- `system_collector`: pom.xml extracted parent version instead of project version
- `container_collector`: substring test-directory matching (e.g. "contest" matched "test")
- `component_collector` + `interface_collector`: `rglob` without SKIP_DIRS (10-20x slowdown on network drives)
- `component_collector`: `relative_to` crash on edge paths
- `interface_collector`: only detected "Spring Boot", missed Java/Gradle and Java/Maven projects
- `workflow_collector`: substring `_should_skip`, Python `def` pattern on Java codebase, `rglob` without SKIP_DIRS
- `techstack_version_collector`: version comparison by string length instead of segment count; npm versions truncated to major-only
- `security_detail_collector`: `@Secured`/`@RolesAllowed` captured only first and last role
- `dependency_collector`: pyproject.toml parsed `[tool.X.dependencies]` instead of `[project]`

*Medium (14 fixes):*
- `dependency_collector`: Gradle dependencies now parse `group:artifact:version` (version was always empty)
- `oracle_table_collector`: UNIQUE index detection looked outside regex match
- `evidence_collector`: substring path matching replaced with normalized comparison
- `config_collector`: `rglob` replaced with `_find_files`; `_should_skip_path` fixed to path-component matching
- `data_model_collector`: `line_start` clamped to `max(1, ...)`; only collection types skipped (not all generics)
- `_should_skip` fixed in 6 collectors: workflow, techstack, security_detail, test, validation, error_handling
- `infrastructure_collector`: Kubernetes `rglob` replaced with `_find_files`
- `requirements.txt` parser handles extras brackets and dots in package names

**Phase 3 — Architecture Analysis (9 bugs)**
- Token counting crash, `PrivateAttr` missing default, `output_pydantic` blocking repairs
- Stale files on resume, quality context not forwarded, parallel mini-crews

**Phase 4 — Development Planning (12 bugs)**
- Components shown to LLM now include `file_path` (was missing → Phase 5 could not resolve files)
- Enrichment stores full component dicts instead of bare name strings
- Agent backstory includes explicit step format with file paths
- Layer pattern derived from analyzed architecture instead of hardcoded
- `output_pydantic` removed, dead code cleaned up

**Phase 5 — Code Generation (11 bugs)**
- Shared baseline cache, import index reuse, cascade checkpoints
- Per-phase timeout wrapper, phase contract validation

**UI / E2E**
- Reports Architecture tab shows only arc42/C4 documents
- Phase cards show "ready" only when all dependencies are completed
- History page auto-scrolls to detail panel

### Changed
- **Demo showcase** (`e2e/demo-showcase.spec.ts`) rewritten for manager audience (793 → 310 lines):
  removed Settings, Collectors, Phases config, MCP Servers, Logs, Metrics;
  focused on business story: Upload Task → One-Click Run → Generated Architecture Docs → Development Plans → Code → Git Branches → Audit History

---

## [0.7.0] - 2026-02-21

Phase 7 (deliver) complete. All 8 SDLC phases implemented and tested. 781 tests pass (0 failures).
Major reliability and observability improvements via CrewAI advanced features.
781 tests pass (0 failures). The pipeline runs fully on-premises without any cloud dependency.

### Added

**Phase 7 — Review & Consistency Guard (`ReviewCrew`)**
- Deterministic scan phase (no LLM): container/C4 coverage check, arc42 chapter presence, placeholder detection (TODO/FIXME/TBD/XXX), quality score 0-100
- LLM synthesis phase: single agent with `FactsQueryTool` + `RAGQueryTool` produces a Markdown quality report
- Outputs: `knowledge/deliver/consistency.json`, `quality.json`, `summary.json`, `synthesis-report.md`
- Registered in CLI (`cli.py`) and `phases_config.yaml` with correct `type: crew` and `dependencies: [implement]`

**CrewAI Advanced Features — Runtime Observability & Reliability**
- **Task Guardrails** (`shared/utils/task_guardrails.py`): `validate_json_output` (Phase 2 tasks) and `validate_plan_json` (Phase 4 planning task) — LLM gets one structured retry when output is not valid JSON or missing required keys; `guardrail_max_retries=1` on all guarded tasks
- **`inject_date=True`** on all 13 agent factories (Phases 2, 3, 4, 5, 6, 7, MCP utility) — current date injected into every agent system prompt automatically
- **`step_callback` + `task_callback`** wired into all 9 `Crew()` constructors (was dead code in `crew_callbacks.py` — never connected); every agent reasoning step and tool call now logged in real time
- **`output_log_file`** on all 9 Crew constructors — structured JSON logs written to `knowledge/{phase}/logs/{name}.json` using CrewAI's built-in `FileHandler` (JSON array format, one entry per task)
- **Embedder config** (`shared/utils/embedder_config.py`): `get_crew_embedder()` reads `OLLAMA_BASE_URL` + `EMBED_MODEL` env vars; passed to all Crew constructors, removes the OpenAI-embeddings blocker for future `memory=True` adoption
- New utility files: `shared/utils/task_guardrails.py`, `shared/utils/embedder_config.py`

**Architecture — Shared Infrastructure Extraction (Wave 3)**
- `shared/dependency_checker.py`: `DependencyChecker` class extracted from orchestrator — phase prerequisite validation with structured error messages
- `shared/phase_git_handler.py`: `PhaseGitHandler` class — git branch/commit lifecycle for phase outputs, extracted from orchestrator
- `shared/schema_version.py`: `add_schema_version()` / `check_schema_version()` — all 6 phase output JSON files now carry `_schema_version` and `_generated_at` metadata; orchestrator validates schema version on cached facts

**Unit Tests — Collectors (Wave 3)**
- `tests/unit/collectors/test_spring_collectors.py` — 11 tests for Spring Boot fact extraction
- `tests/unit/collectors/test_angular_collectors.py` — 9 tests for Angular component/service/module/pipe/directive extraction
- `tests/unit/collectors/test_generic_collectors.py` — 6 tests for Container and Dependency collectors
- **Total test count: 781 passed, 0 failed**

**Settings UI Improvements**
- `INDEX_MODE`: dropdown with `Auto` / `Force` / `Off` options (removed undocumented `smart` alias from UI)
- `LOG_LEVEL`: dropdown with `INFO / DEBUG / WARNING / ERROR / CRITICAL`
- `CODEGEN_API_KEY` added to masked secret keys
- `mat-hint` descriptions under every settings field (sourced from `.env.example`)
- Phase toggles: Save button calls `PUT /api/phases/{id}/toggle` → writes `phases_config.yaml`
- Required phases shown as disabled toggle with tooltip
- Progress counter: skipped phases counted as done alongside completed

**E2E & CI**
- Comprehensive Playwright demo showcase covering all 8 phases
- CI E2E: `webServer` config aligned with dev server startup; collectors count assertions corrected

### Fixed

**Phase 4 — Development Planning**
- `W7`: `file_path` was missing from every component line shown to the LLM → Phase 5 could not resolve files; added `file: {file_path}` and raised component limit 10 → 15 (`stage4_plan_generator.py`)
- `W1`: `_enrich_plan()` stored bare component name strings instead of full `ComponentMatch` objects → Phase 5 `plan_reader` missing `id`/`stereotype`/`file_path`; fixed in `pipeline.py`
- `W4`: agent backstory was too vague → implementation steps had no file paths; added GOLDEN RULES with explicit step format `"N. Verb ComponentName (path) — what"`
- `W13`: JSON template step example had no file path; full `affected_components` object now shown in template
- `W10`: `layer_pattern` was hardcoded; now derived from `analyzed_architecture.macro_architecture.layer_pattern`

**Phase 3 — Architecture Synthesis (Arc42, Wave 3)**
- Non-existent `seaguide_query` tool referenced in `arc42/agents.py` and `c4/agents.py` → LLM wasted all `max_iter` attempts → stub fallback; replaced with `rag_query`
- `$(date)` shell literal appearing verbatim in output; replaced with `current_date` template variable (`date.today().isoformat()`)
- JPA `@Entity` classes mixed with Flyway migration stubs in arc42 ch05; added explicit stereotype filter
- Database technology guessed incorrectly; added `rag_query(query="Oracle datasource database")` to relevant task prompts
- Wrong stats path in stub fallback (`facts["statistics"]["total_components"]` → `len(facts["components"])`)

**Deep Review Fixes — Waves 1 & 2**
- `BUG-C1`: Token counting crash — `UsageMetrics` is not a dict; switched to `getattr()` (`architecture_analysis/crew.py`)
- `BUG-C2`: `PrivateAttr` missing `default_factory=dict` on `FactsQueryTool._dimension_cache` → Pydantic crash on first instantiation
- `BUG-C3`: `output_pydantic` on Phase 2 tasks caused CrewAI to raise `ValidationError` before repair code ran; removed; added `_repair_task_output_files()` post-processing
- `BUG-C5`: Git auto-commit in knowledge dir was running unconditionally; guarded by `CODEGEN_COMMIT_KNOWLEDGE=false` env check
- `BUG-Y1`: On resume, stale output files from failed mini-crews corrupted synthesis; now deleted before restart
- `BUG-Y2`: Phase 4 `output_pydantic` + dead `_extract_json_from_validation_error()` removed
- `BUG-Y3/Y4`: `quality_context` / `quality_hints` from Phase 2 not forwarded to Phase 3/4; fixed in crew `kickoff()` methods
- `BUG-Y5`: Shared baseline build cache not passed through `_run_cascade()` → N redundant baseline builds per session; fixed
- `BUG-Y6`: `ImportIndex` rebuilt N times per cascade; now built once and shared across all cascade tasks
- `ARCH-4/5/6/7`: `TASK_TYPE_RULES` dict, `PHASE_CONTRACTS` dict, per-phase timeout wrapper, local `FactsQueryTool` duplicate removed
- `PERF-2/3`: `facts.json` cached after extract phase; `FactsQueryTool` preloads 3 heaviest dimensions once at startup

**Phase Config**
- `verify` and `deliver` phases had `enabled: false` → silently excluded from pipeline; set to `true`
- `deliver` had `type: pipeline` (should be `type: crew`); corrected
- `deliver.dependencies` was `[verify]` (too strict); corrected to `[implement]`
- `ReviewCrew` not registered in `cli.py` → phase never executed even when enabled; registration added

**Dashboard / UI**
- Knowledge and Reports pages no longer expose raw internal pipeline data (`.checkpoint_*.json`, `evidence.jsonl`, `symbols.jsonl`) — filtered at API level
- Reports page crash on missing `generated_files` field fixed
- Arc42 document rendering improvements in Knowledge Explorer

### Changed

- `phases_config.yaml`: `verify` and `deliver` phases enabled by default

---

## [0.6.0] - 2026-02-15

### Added

**Enhanced Discover Phase — Symbol Index, Evidence Store, Repo Manifest, Budget Engine**

- **Symbol Extractor** (`symbol_extractor.py`): regex-based extraction of classes, methods, functions, interfaces, endpoints, and decorators for Java, TypeScript, and Python. Outputs `knowledge/discover/symbols.jsonl` (one JSONL record per symbol with name, kind, path, line range, language, module)
- **Evidence Store**: each chunk now has traceability metadata — line range, content type (code/doc/config), linked symbols. Written to `knowledge/discover/evidence.jsonl`
- **Repo Manifest** (`manifest_builder.py`): detects frameworks via marker files (pom.xml → Spring, angular.json → Angular, etc.), computes file stats by extension/module, captures git commit hash. Written to `knowledge/discover/repo_manifest.json`
- **Budget Engine** (`budget_engine.py`): classifies files into A/B/C priority tiers (docs/controllers → A, services/entities → B, tests/utils → C) and reorders indexing so high-value files are processed first. Controlled by `INDEX_ENABLE_BUDGET`, `INDEX_PRIORITY_A_PCT`, `INDEX_PRIORITY_B_PCT`
- **SymbolQueryTool** (`shared/tools/symbol_query_tool.py`): CrewAI tool for deterministic symbol lookups — exact/substring match with kind, path, and module filters. Returns empty gracefully when `symbols.jsonl` is missing
- **ChromaDB `content_type` metadata**: chunks now tagged as `code`, `doc`, or `config` in ChromaDB for filtered retrieval
- **RAG evidence enrichment**: `RAGQueryTool` now enriches search results with line numbers, content type, and linked symbols from `evidence.jsonl`. New `content_type` filter parameter
- **Data models** (`models.py`): `SymbolRecord`, `EvidenceRecord`, `RepoManifest`, `ModuleStats` dataclasses
- **Path constants**: `DISCOVER_SYMBOLS`, `DISCOVER_EVIDENCE`, `DISCOVER_MANIFEST` in `shared/paths.py`
- **Phase registry**: `DISCOVER_ARTIFACTS` dict in `phase_registry.py`
- **IndexingState**: new `symbols_count`, `evidence_count`, `manifest_generated` fields (backward-compatible)

**Downstream Phase Integration**

- **Plan (Phase 4)**: `ComponentDiscoveryStage` uses symbol index as 5th scoring signal — re-balanced weights (semantic 30%, name 25%, symbol 20%, package 15%, stereotype 10%)
- **Implement (Phase 5)**: `ContextCollectorStage` uses symbol index for targeted content extraction — reads only the relevant class/method body instead of truncating entire files at 12K chars
- **Extract (Phase 1)**: `CollectorOrchestrator` loads `repo_manifest.json` as supplementary framework/module context

---

## [0.5.0] - 2026-02-13

### Added

**Cascade Code Generation**
- Cascade mode for multi-task code generation: single integration branch (`codegen/batch-{timestamp}`), sequential processing
- Each task sees cumulative file changes from all prior tasks — dependent tasks no longer fail
- `setup_cascade_branch()`, `cascade_write_and_commit()`, `teardown_cascade()` lifecycle in OutputWriterStage
- Cascade tracking fields in CodegenReport: `cascade_branch`, `cascade_position`, `cascade_total`, `prior_task_ids`
- Single-task mode unchanged: still creates isolated `codegen/{task_id}` branches

**Plan Reader Improvements**
- String component resolution: Phase 4 plans with compact component names now resolved via architecture_facts.json
- Container root_path prepending: file paths correctly resolved as repo-relative (e.g., `frontend/src/app/...`)
- Lazy-loaded container index for O(1) path lookup

**Pipeline Executor Fix**
- Phases routing: individual phases (`--phases implement`) now passed directly to CLI instead of falling back to `--preset full`
- Dashboard can start any individual phase or combination without triggering the full pipeline

**Build System Collector**
- New collector for build system facts extraction (Maven, Gradle, npm)

### Fixed
- `_is_clean_working_tree` ignoring untracked files (added `-uno` flag) — target repos with untracked files no longer block cascade
- Pipeline executor phases fallback routing (was always defaulting to full preset)

---

## [0.4.0] - 2026-02-13

### Added

**SDLC Pilot Rebrand**
- Domain-driven phase IDs (discover, extract, analyze, document, plan, implement, verify, deliver)
- Progress bar robustness improvements
- Updated presets with display names

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
- Added Tailwind CSS with custom theme
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
