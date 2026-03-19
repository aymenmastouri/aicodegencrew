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

- Index repository files into Qdrant vector store for semantic search (RAG)
- Extract symbols (classes, methods, endpoints) for deterministic lookups
- Store evidence metadata (line numbers, symbols) directly in Qdrant payload
- Create a repository manifest (frameworks, modules, ecosystems)
- Prioritize high-value files via budget-based reordering

## 3. How It All Works Together

The Discover phase transforms a raw repository into a **queryable knowledge base**. Every subsequent phase uses this knowledge in different ways. Here is the complete picture:

```
Source Repository (2800+ files)
    │
    ├── Step 1: Discover files ──── Which files exist? (filtering, prioritization)
    │
    ├── Step 2: Read + Extract ──── Code content + Symbols (classes, methods, endpoints)
    │
    ├── Step 3: Chunk ───────────── Split files into meaningful pieces (~1500 chars each)
    │
    ├── Step 4: Embed ───────────── Convert each chunk to a vector (embedding model)
    │
    └── Step 5: Store in Qdrant ─── Vector + Text + Metadata (ALL in one place)
                    │
                    │  Each point in Qdrant contains:
                    │  ┌─────────────────────────────────────────┐
                    │  │ id:         "chunk_abc123"               │
                    │  │ vector:     [0.12, -0.34, 0.56, ...]    │  ← for semantic search
                    │  │ text:       "public class AuthContr..."  │  ← the actual code
                    │  │ file_path:  "src/auth/AuthController.java"│
                    │  │ start_line: 45                           │  ← evidence
                    │  │ end_line:   92                           │  ← evidence
                    │  │ symbols:    "AuthController,login,logout" │  ← evidence
                    │  │ content_type: "code"                     │
                    │  │ language:   "java"                       │
                    │  │ file_hash:  "a1b2c3..."                  │  ← for SMART mode
                    │  └─────────────────────────────────────────┘
                    │
    How downstream phases USE this:
    │
    ├── Analyze (Phase 2) ─── RAG Query: "authentication patterns" → finds AuthController
    │                         Result includes: code + file path + line 45-92 + symbols
    │
    ├── Document (Phase 3) ── RAG Query: "REST endpoints" → finds all controllers
    │                         Uses evidence to cite exact source locations in docs
    │
    ├── Triage (Phase 4) ──── RAG Query: "error handling in OrderService"
    │                         + Symbol lookup: find_entry_points() matches component names
    │                         + Duplicate detection: semantic similarity search
    │
    ├── Plan (Phase 5) ────── 5-signal scoring:
    │                         • Semantic (30%): Qdrant vector similarity
    │                         • Name (25%): fuzzy match against component names
    │                         • Symbol (20%): exact match in symbols.jsonl
    │                         • Package (15%): label-based filtering
    │                         • Stereotype (10%): keyword detection
    │
    └── Implement (Phase 6) ─ Targeted code extraction: find exact files to modify
                              Symbol index → precise file:line locations
```

### Single Source of Truth: Qdrant

All evidence metadata (line numbers, symbols, content type, language) is stored **directly in the Qdrant payload** — not in a separate local file. This means:

- **No sync problems**: one place for everything, no local files that can get deleted or go stale
- **No "Loaded 0 evidence records"**: evidence comes from the same query that finds the code
- **Reset-safe**: `Reset All` clears downstream phases but Qdrant data survives (remote server)
- **One query, full context**: RAG query returns code + file path + line numbers + symbols in a single call

### What is a RAG Query?

RAG = **Retrieval-Augmented Generation**. Instead of asking the LLM to guess, we **find the relevant code first** and inject it into the prompt:

```
Without RAG:  "How does authentication work?" → LLM guesses (hallucination risk)

With RAG:     "How does authentication work?"
                → Qdrant finds: AuthController.java (lines 45-92), SecurityConfig.java (lines 10-35)
                → LLM receives actual code as context → accurate, evidence-based answer
```

Every phase that calls `RAGQueryTool` gets this benefit automatically.

### What are Symbols?

Symbols are **named code elements** extracted deterministically (regex, no LLM):

| Symbol Type | Example | Used By |
|-------------|---------|---------|
| Class | `AuthController` | Plan (component discovery), Triage (entry points) |
| Method | `login()`, `handleRequest()` | Implement (targeted extraction) |
| Endpoint | `GET /api/users` | Extract (interface detection), Triage (blast radius) |
| Annotation | `@RestController`, `@Service` | Extract (stereotype classification) |
| Interface | `UserRepository` | Extract (relation mapping) |

Symbols enable **deterministic lookups** — no embedding needed, instant exact match.

### What is Evidence?

Evidence = **traceability from a search result back to source code**:

| Field | Example | Purpose |
|-------|---------|---------|
| `start_line` | 45 | Cite exact location in generated docs |
| `end_line` | 92 | Show code range, not just file |
| `symbols` | `AuthController,login` | Know what's in the chunk without reading it |
| `content_type` | `code` / `doc` / `config` | Filter search by type |
| `language` | `java` | Language-specific processing |

Without evidence, a RAG result is just "some text from some file". With evidence, it's "lines 45-92 of AuthController.java containing the login() method".

## 4. Inputs & Outputs

| Direction | Artifact | Format | Storage |
|-----------|----------|--------|---------|
| **Input** | Target repository | File system | `PROJECT_PATH` or `GIT_REPO_URL` |
| **Output** | Vectors + text + evidence | Qdrant points | Remote Qdrant server (single source of truth) |
| **Output** | Symbol index | JSONL | `knowledge/discover/{slug}/symbols.jsonl` (local) |
| **Output** | Repository manifest | JSON | `knowledge/discover/{slug}/repo_manifest.json` |
| **Output** | Indexing state | JSON | `knowledge/discover/{slug}/.indexing_state.json` |

> `{slug}` is derived from the repository folder name (e.g. `C:\uvz` → `uvz`). See [Multi-Project Isolation](../../architecture/multi-project-isolation.md).

> **Note**: `evidence.jsonl` is a legacy local cache. New indexes store all evidence in Qdrant payload. The RAG query reads from Qdrant first, falls back to `evidence.jsonl` for old indexes.

## 5. Architecture

### Pipeline Flow

```
Step 1:  Discover files              (RepoDiscoveryTool — find all files, apply filters)
Step 1b: Build repo manifest         (ManifestBuilder → frameworks, modules, ecosystems)
Step 2:  Read files                  (RepoReaderTool — content + encoding handling)
Step 2b: Extract symbols per file    (SymbolExtractor — classes, methods, endpoints)
Step 2c: Apply budget prioritization (BudgetEngine — A/B/C tiers, high-value files first)
Step 3:  Chunk                       (ChunkerTool — split into ~1500 char pieces + content_type)
Step 4:  Embed                       (EmbeddingsTool — local embedding model → vectors)
Step 5:  Store in Qdrant             (ChromaIndexTool — vectors + text + evidence payload)
Step 6:  Write local artifacts       (symbols.jsonl, repo_manifest.json)
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

### Evidence in Qdrant Payload

Each chunk gets traceability stored **directly in Qdrant** as payload metadata:

```
Qdrant Point Payload:
{
    "file_path": "src/auth/AuthController.java",
    "file_hash": "a1b2c3...",
    "start_line": 45,          ← evidence
    "end_line": 92,            ← evidence
    "symbols": "AuthController,login,logout",  ← evidence (comma-separated)
    "content_type": "code",    ← evidence
    "language": "java",        ← evidence
    "chunk_index": 3,
    "start_char": 1200,
    "end_char": 2700,
    "repo_path": "C:/uvz"
}
```

This is the **single source of truth** — RAG queries read evidence directly from the Qdrant result, no local file needed. Legacy `evidence.jsonl` is still supported as fallback for indexes created before this change.

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

## 7. Dependencies

- **Upstream**: None (first phase)
- **Downstream**: All phases consume Discover outputs:

| Phase | What it uses | How |
|-------|-------------|-----|
| Extract (1) | `repo_manifest.json` | Framework/ecosystem detection for dimension collectors |
| Analyze (2) | Qdrant via `RAGQueryTool` | Code context for 16 analysis sections (14973 evidence records) |
| Document (3) | Qdrant via `RAGQueryTool` | Code evidence for arc42/C4 chapters (line numbers + symbols) |
| Triage (4) | Qdrant + `symbols.jsonl` | Semantic search for duplicates, symbol-based entry point finding |
| Plan (5) | Qdrant + `symbols.jsonl` | 5-signal component scoring (semantic 30%, symbol 20%, ...) |
| Implement (6) | Qdrant + `symbols.jsonl` | Targeted code extraction — find exact files and line ranges to modify |

## 8. Quality Gates & Validation

- Fingerprint-based skip logic prevents unnecessary re-indexing
- Stale lock recovery (checks if PID is still alive)
- State file persists across runs — warns on missing data instead of silently re-indexing
- `resettable=False` — Reset All does not delete Discover artifacts (expensive to rebuild, Qdrant data is remote)
- Empty `evidence.jsonl` or `symbols.jsonl` triggers a WARNING advising `INDEX_MODE=force`

## 9. Configuration

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

## 10. Risks & Open Points

- Embedding model consistency: all consumers must use the same model as indexing (`EMBED_MODEL`)
- Graceful degradation: `symbols.jsonl` missing → falls back to 4-signal scoring in Plan; old Qdrant index without payload evidence → falls back to `evidence.jsonl`
- Qdrant availability: if remote Qdrant is down, all RAG queries return empty results (deterministic fallbacks still work)

---

© 2026 Aymen Mastouri. All rights reserved.
