# SDLC Pilot — Architecture Overview

> **Status**: v0.7.2 | **Author**: Aymen Mastouri | **Updated**: 2026-03-06

---

## 1. Purpose

**SDLC Pilot** is a fully local, on-premises AI-powered blueprint for a complete, end-to-end Software Development Lifecycle. It analyzes an existing repository, generates evidence-based architecture documentation, and supports the full development workflow — planning, implementing, testing, and delivering changes.

**Why On-Premises?** Enterprise software often contains sensitive IP and security-critical code. SDLC Pilot runs entirely on your infrastructure with your own LLMs — no data ever leaves your network.

## 2. 4-Layer Architecture

> **Diagrams:** [sdlc-overview.drawio](diagrams/sdlc-overview.drawio) · [layer-architecture.drawio](diagrams/layer-architecture.drawio) · [pipeline-flow.drawio](diagrams/pipeline-flow.drawio) · [cross-architecture.drawio](cross-architecture.drawio)

| Layer | Phases | Purpose | LLM Required |
|-------|--------|---------|--------------|
| **KNOWLEDGE** | 0–1 | Deterministic facts extraction | No |
| **REASONING** | 2–5 | AI-powered analysis, synthesis, triage, and planning | Hybrid |
| **EXECUTION** | 6–8 | Code generation, testing, and delivery | Yes |
| **FEEDBACK** | — | Continuous learning and quality | Yes |

## 3. Phase Overview

| Phase | Name | Layer | Type | Status | Docs |
|-------|------|-------|------|--------|------|
| 0 | Discover | Knowledge | Pipeline | IMPLEMENTED | [Phase 0](phases/phase-0-discover/README.md) |
| 1 | Extract | Knowledge | Pipeline | IMPLEMENTED | [Phase 1](phases/phase-1-extract/README.md) |
| 2 | Analyze | Reasoning | Crew | IMPLEMENTED | [Phase 2](phases/phase-2-analyze/README.md) |
| 3 | Document | Reasoning | Crew | IMPLEMENTED | [Phase 3](phases/phase-3-document/README.md) |
| 4 | Triage | Reasoning | Crew | IMPLEMENTED | [Phase 4](phases/phase-4-triage/README.md) |
| 5 | Plan | Reasoning | Hybrid | IMPLEMENTED | [Phase 5](phases/phase-5-plan/README.md) |
| 6 | Implement | Execution | Hybrid | IMPLEMENTED | [Phase 6](phases/phase-6-implement/README.md) |
| 7 | Verify | Execution | Crew | IMPLEMENTED | [Phase 7](phases/phase-7-verify/README.md) |
| 8 | Deliver | Execution | Crew | IMPLEMENTED | [Phase 8](phases/phase-8-deliver/README.md) |

## 4. Core Principles

| Principle | Description |
|-----------|-------------|
| Evidence-First | Every statement backed by code/config evidence — LLMs synthesize, they don't discover |
| Deterministic Discovery | Facts come from code analysis (Extract), not LLM guesswork |
| Phase Isolation | Clear inputs/outputs per phase, no cross-phase dependencies |
| Incremental Adoption | Phases can be executed independently |
| Mini-Crews | Fresh crew per task, preventing context overflow |

## 5. Core Modules

| Module | Location | Responsibility |
|--------|----------|----------------|
| **Orchestrator** | `orchestrator.py` | Phase coordination (register → run), dependency validation |
| CLI | `cli.py` | Command-line interface, repo resolution, preset validation |
| GitRepoManager | `shared/utils/git_repo_manager.py` | Clone/pull remote Git repos |
| DependencyChecker | `shared/dependency_checker.py` | Phase dependency resolution (tier 1: session, tier 2: disk) |
| PhaseGitHandler | `shared/phase_git_handler.py` | Post-phase git auto-commit of `knowledge/` |
| SchemaVersion | `shared/schema_version.py` | `_schema_version` injection + reader-side mismatch warnings |
| Pipelines | `pipelines/` | Deterministic processes (Discover, Extract) |
| Crews | `crews/` | AI agent workflows (Analyze, Document, Verify) |
| Hybrid | `hybrid/` | Pipeline + CrewAI (Plan, Implement) |
| Shared | `shared/` | Common utilities, models, tools |

## 6. Cross-Cutting Architecture

| Document | Description |
|----------|-------------|
| [Pipeline Pattern](architecture/pipeline-pattern.md) | Stage-based execution, self-healing builds |
| [Crew Pattern](architecture/crew-pattern.md) | Multi-agent AI collaboration, MapReduce |
| [Knowledge Lifecycle](architecture/knowledge-lifecycle.md) | 16 dimensions, data flow, archive/reset |
| [Orchestration & State](architecture/orchestration.md) | Phase execution, dependencies, crash recovery |
| [Phase Registry](architecture/phase-registry.md) | Single source of truth for phase metadata |
| [Pipeline Contract](architecture/pipeline-contract.md) | Inter-phase data contracts |
| [Multi-Project Isolation](architecture/multi-project-isolation.md) | Per-project discover subfolders, slug derivation |
| [Dashboard](architecture/dashboard.md) | Angular + FastAPI web UI, SSE streaming |
| [Logging & Observability](architecture/logging-observability.md) | Structured metrics, run correlation |

## 7. Data Flow

```
Source Repository
  │
  ▼
Phase 0: Discover ─── knowledge/discover/{slug}/ (ChromaDB + symbols + evidence + manifest)
  │
  ▼
Phase 1: Extract ──── architecture_facts.json + evidence_map.json
  │
  ▼
Phase 2: Analyze ──── analyzed_architecture.json
  │
  ▼
Phase 3: Document ─── C4 diagrams + Arc42 docs + quality reports
  │
  ▼
Phase 4: Triage ───── knowledge/triage/ (findings + customer + developer briefs)
  │
  ▼
Phase 5: Plan ─────── {task_id}_plan.json
  │
  ▼
Phase 6: Implement ── Git branch + {task_id}_report.json
  │
  ▼
Phase 7: Verify ───── knowledge/verify/ ({task_id}_verify.json + summary.json)
  │
  ▼
Phase 8: Deliver ──── knowledge/deliver/ (consistency + quality + synthesis report)
```

See [Knowledge Lifecycle](architecture/knowledge-lifecycle.md) for the full data flow matrix.

## 8. Execution Presets

Presets are defined in `config/phases_config.yaml` and validated by the CLI.

| Preset | Phases | Description |
|--------|--------|-------------|
| `index` | 0 | Repository indexing only |
| `scan` | 0, 1 | Indexing + Architecture Facts (no LLM) |
| `analyze` | 0, 1, 2 | Indexing + Facts + Analysis |
| `document` | 0, 1, 2, 3 | C4 + arc42 documentation |
| `triage` | 0, 1, 2, 4 | Issue triage |
| `plan` | 0, 1, 2, 5 | Development planning |
| `develop` | 0, 1, 2, 5, 6 | Planning + code generation |
| `architect` | 0, 1, 2, 3, 5 | Architecture docs + planning |
| `full` | 0–8 | Complete SDLC pipeline |

## 9. Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PROJECT_PATH` | Target repository path | Required |
| `GIT_REPO_URL` | Git HTTPS URL (overrides `PROJECT_PATH`) | — |
| `GIT_BRANCH` | Branch to checkout | Auto-detect |
| `MODEL` | LLM model identifier | `gpt-oss-120b` |
| `EMBED_MODEL` | Embedding model | `all-minilm:latest` |
| `INDEX_MODE` | Indexing behavior: off/auto/smart/force | `auto` |
| `LLM_PROVIDER` | LLM provider: local/onprem | `local` |
| `CODEGEN_MODEL` | Code generation LLM | Falls back to `MODEL` |

### Git Repository Support

Set `GIT_REPO_URL` to clone a remote repository automatically. Auto-detects default branch, handles submodules, caches in `.cache/repos/`. See [User Guide](guides/USER_GUIDE.md).

## 10. Command Reference

```bash
# Presets
aicodegencrew run --preset plan        # Discover + Extract + Analyze + Plan
aicodegencrew run --preset architect    # Full architecture documentation

# Shortcuts
aicodegencrew plan                      # Same as --preset plan
aicodegencrew codegen                   # Code generation (cascade mode)
aicodegencrew codegen --dry-run         # Preview (no file writes)

# Single phases
aicodegencrew run --phases extract
aicodegencrew run --phases analyze

# Options
aicodegencrew --env /path/to/.env plan
aicodegencrew plan --index-mode off
aicodegencrew run --git-url https://gitlab.example.com/team/project.git
```

## 11. SDLC Dashboard

The web UI wraps the CLI pipeline in a visual interface. See [Dashboard Architecture](architecture/dashboard.md).

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI (Python) — 10 routers, SSE streaming |
| Frontend | Angular 21 + Material Design |
| Proxy | Nginx (SSE buffering) |
| Deployment | Docker Compose |

## 12. Deployment

| Mode | Source Visible | Use Case |
|------|---------------|----------|
| Development (`pip install -e .`) | Yes | Development |
| Wheel (`pip install *.whl`) | No | Internal distribution |
| Docker (`docker run`) | No | Production |

See [Delivery Guide](guides/DELIVERY_GUIDE.md) for release process.

## 13. Diagrams

### Cross-Cutting (in `diagrams/`)

| Diagram | Description |
|---------|-------------|
| [sdlc-overview.drawio](diagrams/sdlc-overview.drawio) | Full SDLC pipeline overview |
| [layer-architecture.drawio](diagrams/layer-architecture.drawio) | 4-layer architecture |
| [pipeline-flow.drawio](diagrams/pipeline-flow.drawio) | Phase flow with layer context |
| [knowledge-structure.drawio](diagrams/knowledge-structure.drawio) | Knowledge base organization |
| [orchestration-state.drawio](diagrams/orchestration-state.drawio) | Orchestration state machine |
| [dashboard-architecture.drawio](diagrams/dashboard-architecture.drawio) | Dashboard architecture |
| [reset-cascade.drawio](diagrams/reset-cascade.drawio) | Reset cascade & archive flow |

### Per-Phase (in `phases/`)

| Phase | Primary Diagram | Additional |
|-------|----------------|------------|
| 0 — Discover | [phase-0-discover-architecture.drawio](phases/phase-0-discover/phase-0-discover-architecture.drawio) | [evidence-flow.drawio](phases/phase-0-discover/evidence-flow.drawio) |
| 1 — Extract | [phase-1-extract-architecture.drawio](phases/phase-1-extract/phase-1-extract-architecture.drawio) | — |
| 2 — Analyze | [phase-2-analyze-architecture.drawio](phases/phase-2-analyze/phase-2-analyze-architecture.drawio) | [analysis-crew-schema.drawio](phases/phase-2-analyze/analysis-crew-schema.drawio) |
| 3 — Document | [phase-3-document-architecture.drawio](phases/phase-3-document/phase-3-document-architecture.drawio) | — |
| 4 — Triage | *(README only — no .drawio yet)* | — |
| 5 — Plan | [phase-5-plan-architecture.drawio](phases/phase-5-plan/phase-5-plan-architecture.drawio) | [upgrade-rules-engine.drawio](phases/phase-5-plan/upgrade-rules-engine.drawio) |
| 6 — Implement | [phase-6-implement-architecture.drawio](phases/phase-6-implement/phase-6-implement-architecture.drawio) | [code-generation-pipeline.drawio](phases/phase-6-implement/code-generation-pipeline.drawio) · [task-type-strategy.drawio](phases/phase-6-implement/task-type-strategy.drawio) |

---

© 2026 Aymen Mastouri. All rights reserved. Proprietary — see [LICENSE](../LICENSE).
