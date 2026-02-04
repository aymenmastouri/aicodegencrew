# Scaling Strategies for Large Repositories

> **Status**: IMPLEMENTED - MapReduceAnalysisCrew available  
> **Created**: 2026-02-03  
> **Updated**: 2026-02-04  
> **Context**: Enterprise-scale support for 100k+ components

## Current Limitation

The current Phase 2 Architecture Analysis processes **all components in a single LLM call**, which causes:
- Long wait times (5-10+ minutes for 800+ components)
- Risk of token limit overflow
- No parallelization

## Proposed Solutions

### Option 1: Map-Reduce Pattern (RECOMMENDED)

**Concept**: Split analysis by container, then merge results.

```
Phase 2a: Container-specific Analysis (parallelizable)
  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
  │ Backend Analyst │     │ Frontend Analyst│     │ Database Analyst│
  │   (~150 comp)   │     │   (~400 comp)   │     │   (~250 comp)   │
  └────────┬────────┘     └────────┬────────┘     └────────┬────────┘
           │                       │                       │
           ▼                       ▼                       ▼
  backend_analysis.json   frontend_analysis.json  database_analysis.json

Phase 2b: Synthesis
  ┌─────────────────────────────────────────────────────────────────┐
  │                    Synthesis Agent                              │
  │  Merges container analyses → analyzed_architecture.json         │
  └─────────────────────────────────────────────────────────────────┘
```

**Implementation**:
```yaml
# config/tasks.yaml additions

analyze_backend:
  agent: container_analyst
  description: "Analyze backend container components"
  tools: [query_facts, list_components_by_stereotype]
  context:
    container_filter: "backend"
  output_file: knowledge/architecture/analysis_backend.json

analyze_frontend:
  agent: container_analyst
  description: "Analyze frontend container components"
  tools: [query_facts, list_components_by_stereotype]
  context:
    container_filter: "frontend"
  output_file: knowledge/architecture/analysis_frontend.json

analyze_database:
  agent: container_analyst
  description: "Analyze database container components"
  tools: [query_facts, list_components_by_stereotype]
  context:
    container_filter: "database"
  output_file: knowledge/architecture/analysis_database.json

merge_container_analyses:
  agent: synthesis_analyst
  description: "Merge container analyses into unified architecture"
  context:
    input_files:
      - knowledge/architecture/analysis_backend.json
      - knowledge/architecture/analysis_frontend.json
      - knowledge/architecture/analysis_database.json
  output_file: knowledge/architecture/analyzed_architecture.json
```

**Advantages**:
- ✅ Smaller context per agent (~200-400 vs 826 components)
- ✅ 3x faster with parallel execution
- ✅ Scales to 100k+ components (just add more containers)
- ✅ Better failure isolation

**Effort**: Medium (2-3 days)

---

### Option 2: Hierarchical Analysis

**Concept**: Progressive deepening - overview first, details on demand.

```
Level 1: Statistics Overview (instant)
  └── get_facts_statistics → repo_overview.json

Level 2: Container Summary (fast)
  └── Per container: component counts, stereotypes, key services

Level 3: Component Details (on demand)
  └── Detailed analysis only for selected components
```

**Use Case**: Interactive exploration, large repos where full analysis isn't needed.

**Advantages**:
- ✅ Instant initial results
- ✅ Lazy loading of details
- ✅ User controls depth

**Disadvantages**:
- ❌ Requires UI/interaction model changes
- ❌ May miss cross-component patterns

**Effort**: High (5+ days)

---

### Option 3: Chunked Processing

**Concept**: Process components in batches, accumulate results.

```
Iteration 1: Components 1-200 → partial_analysis_1.json
Iteration 2: Components 201-400 → partial_analysis_2.json
Iteration 3: Components 401-600 → partial_analysis_3.json
...
Final: Merge all partials → analyzed_architecture.json
```

**Implementation**:
```python
# Pseudocode for chunked processing
CHUNK_SIZE = 200

def analyze_chunked(total_components):
    partial_results = []
    
    for offset in range(0, total_components, CHUNK_SIZE):
        chunk = query_facts(offset=offset, limit=CHUNK_SIZE)
        analysis = agent.analyze(chunk)
        partial_results.append(analysis)
    
    return merge_analyses(partial_results)
```

**Advantages**:
- ✅ Simple implementation
- ✅ Works with existing tools (offset/limit already implemented)
- ✅ Predictable memory usage

**Disadvantages**:
- ❌ Sequential (no parallelization)
- ❌ May miss cross-chunk relationships
- ❌ Requires careful merge logic

**Effort**: Low-Medium (1-2 days)

---

## Recommendation

### Short-term (Now)
Keep current approach but with enterprise-scale tools already implemented:
- ✅ `FactsStatisticsTool` for overview
- ✅ Pagination (offset/limit) in queries
- ✅ Hard cap increased to 500

### Medium-term (Next Sprint)
Implement **Option 1: Map-Reduce Pattern** because:
1. Best performance improvement (parallel execution)
2. Clean architecture (separation of concerns)
3. Scales naturally with containers

### Long-term (Backlog)
Consider **Option 2: Hierarchical Analysis** for interactive use cases.

---

## Implementation Checklist for Map-Reduce

- [ ] Create `container_analyst` agent in agents.yaml
- [ ] Add container-specific tasks in tasks.yaml
- [ ] Implement parallel task execution in crew.py
- [ ] Create merge logic for container analyses
- [ ] Update output schema for partial analyses
- [ ] Add tests for large repo simulation
- [ ] Update documentation

---

## References

- [CrewAI Parallel Task Execution](https://docs.crewai.com/concepts/tasks/#parallel-execution)
- [LangChain Map-Reduce](https://python.langchain.com/docs/modules/chains/document/map_reduce)
- Current implementation: `src/aicodegencrew/crews/architecture_analysis/`
