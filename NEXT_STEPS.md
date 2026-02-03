# AI CodeGen Crew - Next Steps Plan

## Current Status (2026-02-03)

| Phase | Status | Details |
|-------|--------|---------|
| Phase 0: Indexing | DONE | ChromaDB working, 2700+ files indexed |
| Phase 1: Facts | DONE | 826 components, 108 interfaces, 120 relations extracted |
| Phase 2: Synthesis | READY | gpt-oss-120B model configured! |

## Model Status: RESOLVED ✓

Now using `gpt-oss-120b` from sov-ai-platform! This is a 120B model - much better than the 14B.

**Current .env settings:**
```dotenv
MODEL=gpt-oss-120b
API_BASE=http://sov-ai-platform.nue.local.vm:4000/v1
```

---

## Optimizations Applied (2026-02-03)

### 🔧 Fixed: Building Blocks Task
The `arc42_building_blocks` task was trying to document 826 components in one LLM call.

**Solution:** Updated task description to use explicit chunked approach:
1. Create skeleton with `chunked_writer(mode="create")`
2. Query `stereotype_list_tool(stereotype="controller")` → append section
3. Query `stereotype_list_tool(stereotype="service")` → append section
4. Query `stereotype_list_tool(stereotype="entity")` → append section
5. Query `stereotype_list_tool(stereotype="repository")` → append section
6. Finalize with `chunked_writer(mode="finalize")`

### 🔧 Fixed: C4 Component Task
Added `StereotypeListTool` to C4 Crew and updated task to show layer structure (not 800 boxes).

---

## Next Action: Run Phase 2 with 120B Model

### Quick Start

```powershell
# Test the model first
python -m aicodegencrew run --phases phase2_synthesis

# Or run full pipeline
python -m aicodegencrew run --preset architecture_workflow
```

### Component Chunking Strategy (Already Implemented!)

The codebase already has tools for chunking by component/stereotype:

| Tool | Purpose | Location |
|------|---------|----------|
| `ChunkedWriterTool` | Write large docs in sections | [chunked_writer_tool.py](src/aicodegencrew/crews/architecture_synthesis/tools/chunked_writer_tool.py) |
| `StereotypeListTool` | Get components by type (controller/service/etc) | Same file |
| `FactsQueryTool` | RAG-based facts retrieval | [facts_query_tool.py](src/aicodegencrew/crews/architecture_synthesis/tools/facts_query_tool.py) |

**How it works:**
1. `StereotypeListTool` - Query only controllers, then services, then repos
2. `ChunkedWriterTool` - Write each section separately (create → append → append → finalize)
3. No token overflow - each LLM call gets focused context

### Batch Processing for Morning Run

If you want to run everything overnight/morning, use:

```powershell
# Run Phase 2 (C4 + Arc42) - takes ~30-60 min
python -m aicodegencrew run --phases phase2_synthesis

# Or specific sub-phases
python -m aicodegencrew run --phases phase2_c4      # Just C4 diagrams
python -m aicodegencrew run --phases phase2_arc42   # Just arc42 docs
```

---

## Options for Next Work Session

### Option A: Run Phase 2 Now (Priority HIGH) ✓ READY

Model is configured! Just run:

```powershell
python -m aicodegencrew run --phases phase2_synthesis
```

**Expected output:**
- 4 C4 diagrams: Context, Container, Component, Deployment
- 12 arc42 chapters (50+ pages total)
- DrawIO diagram files

**Deliverable:** Complete architecture documentation

---

### Option B: Design Phases 3-7 (Priority MEDIUM)

Currently only Phases 0-2 are implemented. Design and plan:

| Phase | Name | Type | Purpose |
|-------|------|------|---------|
| 3 | Review & Consistency | Crew | Validate outputs, check consistency |
| 4 | Development Planning | Crew | Generate backlog items from architecture |
| 5 | Code Generation | Crew | Implement features, refactoring |
| 6 | Test Generation | Crew | Create unit/integration tests |
| 7 | Deployment | Pipeline | CI/CD configs, release notes |

**Deliverable:** Architecture docs for Phases 3-7, task definitions

---

### Option C: Improve Phase 0-1 (Priority LOW)

Enhance existing collectors:

1. **EndpointFlowBuilder** - Build runtime workflows (already started, empty file)
2. **Better Angular support** - Current collector is basic
3. **More integration patterns** - gRPC, GraphQL, WebSocket
4. **Database schema extraction** - Entity relationships from JPA/Hibernate

**Deliverable:** More detailed architecture_facts.json

---

### Option D: Analyze Different Repository (Priority LOW)

Test the system on a different codebase to validate:
- Generalization (not just UVZ-specific)
- Performance on larger/smaller repos
- Different tech stacks (Python, Node.js, etc.)

**Deliverable:** Validation report, potential improvements

---

## Recommended Order

1. **First:** Option A - Fix Phase 2 (core functionality)
2. **Then:** Option C - Improve collectors (better facts = better docs)
3. **Later:** Option B - Design future phases
4. **Optional:** Option D - Test on other repos

---

## Quick Commands

```bash
# Run full pipeline (Phase 0-1-2)
python -m aicodegencrew run --preset architecture_workflow

# Run only indexing
python -m aicodegencrew index

# Run only facts extraction
python -m aicodegencrew run --phases phase1_architecture_facts

# List available phases
python -m aicodegencrew list
```

---

## Files to Check

- `.env` - LLM configuration (MODEL, OLLAMA_BASE_URL)
- `knowledge/architecture/architecture_facts.json` - Phase 1 output
- `knowledge/architecture/evidence_map.json` - Evidence links
- `logs/current.log` - Latest run log

---

## Contact / Notes

Last working session: 2026-02-03
- Consolidated CLI (4 scripts -> 1)
- New logging system with StepTracker
- Fresh git init with clean commit
