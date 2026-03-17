# Phase 0 — Discover (Repository Indexing)

> **Status**: IMPLEMENTED | **Type**: Pipeline | **Layer**: Knowledge

---

## 1. Overview

| Attribute | Value |
|-----------|-------|
| Phase ID | `discover` |
| Display Name | Repository Indexing |
| Type | Pipeline (deterministic) |
| LLM Requirement | None (embeddings only — local Ollama model) |
| Entry Point | `pipelines/indexing/indexing_pipeline.py` → `IndexingPipeline` |
| Output | `knowledge/discover/{slug}/` |
| Status | **IMPLEMENTED** |

> **Diagrams:** [phase-0-discover-architecture.drawio](phase-0-discover-architecture.drawio) · [evidence-flow.drawio](evidence-flow.drawio)

The Discover phase is the foundation that every subsequent phase builds on. It transforms a raw repository into a structured, queryable knowledge base — **10 steps, 0 LLM calls, 100% deterministic** (the only AI call is a local embedding model).

## 2. Goals

- Index repository files into a vector store (ChromaDB) for semantic search
- Extract symbols (classes, methods, endpoints) for deterministic lookups
- Build evidence traceability from chunks back to source code
- Create a repository manifest (frameworks, modules, file stats)
- Prioritize high-value files via budget-based reordering

## 3. Inputs & Outputs

| Direction | Artifact | Format | Path |
|-----------|----------|--------|------|
| **Input** | Target repository | File system | `PROJECT_PATH` or `GIT_REPO_URL` |
| **Output** | Vector embeddings | ChromaDB | `knowledge/discover/{slug}/chroma.sqlite3` |
| **Output** | Symbol index | JSONL | `knowledge/discover/{slug}/symbols.jsonl` |
| **Output** | Evidence store | JSONL | `knowledge/discover/{slug}/evidence.jsonl` |
| **Output** | Repository manifest | JSON | `knowledge/discover/{slug}/repo_manifest.json` (includes `ecosystems` field) |
| **Output** | Indexing state | JSON | `knowledge/discover/{slug}/.indexing_state.json` |
| **Output** | Active project marker | JSON | `knowledge/discover/.active_project` |

> `{slug}` is derived from the repository folder name (e.g. `C:\uvz` → `uvz`). See [Multi-Project Isolation](../../architecture/multi-project-isolation.md).

## 4. Architecture

### The Problem

Enterprise repositories contain thousands of files across multiple languages. Downstream phases need to **find the right code** fast and precise. Loading entire repos into LLM context is impossible (token limits), and naive file-path matching misses semantic relationships.

### The Solution: 4 Complementary Artifacts

| Artifact | Retrieval Type | Problem Solved |
|----------|---------------|----------------|
| **ChromaDB** | Semantic (vector similarity) | "Find code related to authentication" |
| **symbols.jsonl** | Deterministic (exact lookup) | "Where is class `AuthController`?" |
| **evidence.jsonl** | Structural (chunk-to-source) | "Which lines does this result come from?" |
| **repo_manifest.json** | Structural (repo overview) | "What frameworks and modules exist?" |

### Pipeline Flow

```
Step 1:  Discover files              (RepoDiscoveryTool)
Step 1b: Build repo manifest         (ManifestBuilder → repo_manifest.json)
Step 2:  Read files                  (RepoReaderTool)
Step 2b: Extract symbols per file    (SymbolExtractor)
Step 2c: Apply budget prioritization (BudgetEngine, A/B/C tiers)
Step 3:  Chunk                       (ChunkerTool + content_type)
Step 4:  Embed                       (OllamaEmbeddingsTool)
Step 5:  Store in ChromaDB           (ChromaIndexTool)
Step 6:  Write artifacts             (symbols.jsonl, evidence.jsonl)
```

### Fingerprinting & Change Detection

Two-level fingerprinting decides whether re-indexing is needed:

| Strategy | Method | Speed |
|----------|--------|-------|
| **Git** (preferred) | SHA-256 of HEAD + `git status --porcelain` | ~100ms |
| **Filesystem** (fallback) | SHA-256 of size+mtime for first/last N files | ~1s |

### Indexing Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| `off` | Skip entirely | Index already exists |
| `auto` | Skip if ChromaDB exists and fingerprint matches | Default |
| `smart` | Incremental — only re-index changed files (SHA-256) | After small code changes |
| `force` | Delete and rebuild everything | After major changes |

Smart mode: 2934 files → ~90 min (force), 12 changed → ~30 sec (smart).

## 5. Patterns & Decisions

### Ecosystem Strategy Pattern

Language/framework detection and symbol extraction are driven by **ecosystem modules** (`shared/ecosystems/`). Each ecosystem defines its own file extensions, marker files, regex patterns, and skip directories.

```
shared/ecosystems/
    base.py                      # EcosystemDefinition abstract base class
    registry.py                  # EcosystemRegistry — detection + aggregation
    _utils.py                    # Shared helpers (find_block_end, etc.)
    java_jvm.py                  # Java/JVM (Spring, Maven, Gradle, Kotlin)
    javascript_typescript.py     # JavaScript/TypeScript (Angular, React, Vue, Node)
    python_ecosystem.py          # Python (pip, poetry, setuptools)
    c_cpp.py                     # C/C++ (CMake, Make, Autotools, Meson, Conan, vcpkg)
```

The `ManifestBuilder` runs `EcosystemRegistry.detect(repo_path)` during Step 1b and stores the active ecosystem IDs in `repo_manifest.json` (field: `ecosystems`). Downstream phases can use this list to skip irrelevant processing.

### Symbol Extractor

`SymbolExtractor` dispatches to the active ecosystem's `extract_symbols()` method. Regex-based, per-language extraction — deterministic, no LLM.

| Ecosystem | Languages | Detected Symbols |
|-----------|-----------|-----------------|
| **Java/JVM** | Java | Classes, methods, annotations (`@RestController`, `@Service`), Spring endpoints |
| **JavaScript/TypeScript** | TypeScript, JavaScript | Classes, interfaces, functions, Angular decorators (`@Component`, `@Injectable`) |
| **Python** | Python | Classes, functions/methods, decorators |
| **C/C++** | C, C++ | Structs, unions, enums, functions, macros, typedefs, namespaces, classes (C++) |

### Evidence Store

Each chunk gets traceability: file path, line range, content type (`code`/`doc`/`config`), and linked symbols (overlap-based).

### Budget Engine

Classifies files into 3 priority tiers — high-value files indexed first:

| Tier | Allocation | Contents |
|------|-----------|----------|
| **A** (high) | 40% | READMEs, controllers, root configs, Angular modules |
| **B** (medium) | 40% | Services, repositories, entities, files with 3+ symbols |
| **C** (low) | 20% | Tests, utilities, generated code |

### Multi-Project Isolation

Multiple target repositories can be indexed **side by side** without overwriting each other. Each project gets its own subfolder:

```
knowledge/discover/
├── .active_project           ← JSON: {"slug": "uvz", "repo_path": "C:\\uvz"}
├── uvz/                      ← All artifacts for C:\uvz
│   ├── chroma.sqlite3
│   ├── symbols.jsonl
│   ├── evidence.jsonl
│   ├── repo_manifest.json
│   └── .indexing_state.json
└── myapp/                    ← All artifacts for C:\projects\myapp
    ├── chroma.sqlite3
    └── ...
```

| Concept | Details |
|---------|---------|
| **Slug derivation** | `Path(repo_path).resolve().name`, lowercased, sanitized |
| **Active project** | `.active_project` marker tracks which project downstream tools should query |
| **Legacy migration** | First index after upgrade automatically moves flat artifacts into `{slug}/` |
| **Fallback chain** | Active project → single subfolder → legacy flat layout |

Central module: `shared/project_context.py`. See [Multi-Project Isolation](../../architecture/multi-project-isolation.md) for full architecture.

## 6. Dependencies

- **Upstream**: None (first phase)
- **Downstream**: All phases consume Discover outputs:
  - Phase 1 (Extract): `repo_manifest.json` for framework context
  - Phase 2 (Analyze): ChromaDB via `RAGQueryTool`
  - Phase 3 (Document): ChromaDB via `RAGQueryTool`
  - Phase 4 (Plan): ChromaDB + `symbols.jsonl` (5-signal scoring)
  - Phase 5 (Implement): ChromaDB + `symbols.jsonl` (targeted extraction)

## 7. Quality Gates & Validation

- Fingerprint-based skip logic prevents unnecessary re-indexing
- Stale lock recovery (checks if PID is still alive)
- State file persists across runs — warns on missing ChromaDB instead of silently re-indexing

## 8. Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `INDEX_MODE` | `auto` | off/auto/smart/force |
| `INDEX_CHUNK_SIZE` | `1500` | Characters per chunk |
| `INDEX_CHUNK_OVERLAP` | `200` | Overlap between chunks |
| `INDEX_BATCH_SIZE` | `50` | Files per processing batch |
| `INDEX_ENABLE_BUDGET` | `true` | Enable A/B/C priority reordering |
| `INDEX_PRIORITY_A_PCT` | `40` | Tier A allocation |
| `INDEX_PRIORITY_B_PCT` | `40` | Tier B allocation |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Ollama embedding model |
| `EMBEDDING_BASE_URL` | `http://localhost:11434` | Ollama server URL |

All settings are optional — built-in defaults work without any env vars.

## 9. Risks & Open Points

- Embedding model consistency: all consumers must use the same model as indexing (`EMBEDDING_MODEL`)
- Graceful degradation: every artifact is optional — missing `symbols.jsonl` falls back to 4-signal scoring in Plan, missing `evidence.jsonl` returns results without enrichment

---

© 2026 Aymen Mastouri. All rights reserved.
