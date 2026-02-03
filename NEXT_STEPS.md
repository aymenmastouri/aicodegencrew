# AI CodeGen Crew - Next Steps Plan

## Current Status (2026-02-03)

| Phase | Status | Details |
|-------|--------|---------|
| Phase 0: Indexing | DONE | ChromaDB working, 2700+ files indexed |
| Phase 1: Facts | DONE | 826 components, 108 interfaces, 120 relations extracted |
| Phase 2: Synthesis | BLOCKED | LLM 14B unreliable, needs 32B model |

## Blocker: Phase 2 LLM Issue

The current 14B model (`qwen2.5-coder:14b`) is not reliable enough for architecture synthesis.
It produces incomplete or inconsistent documentation.

**Solution needed:** Deploy 32B model on bmf-ai server.

```powershell
# Check available models
Invoke-RestMethod -Uri "http://bmf-ai.apps.ce.capgemini.com/code/v1/models"

# If 32B available, update .env:
MODEL=openai/Qwen/Qwen2.5-Coder-32B-Instruct
```

---

## Options for Next Work Session

### Option A: Fix Phase 2 (Priority HIGH)

1. Check if 32B model is now available on bmf-ai
2. If yes: Update `.env` and test synthesis
3. If no: Consider hybrid approach:
   - Use Python for deterministic parts
   - Use small LLM only for text generation (summaries, descriptions)

**Deliverable:** Working C4 + arc42 documentation generation

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
