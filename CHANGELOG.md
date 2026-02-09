# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
