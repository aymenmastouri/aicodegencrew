# Phase 1 — Extract (Architecture Facts Extraction)

> **Status**: IMPLEMENTED | **Type**: Pipeline | **Layer**: Knowledge

---

## 1. Overview

| Attribute | Value |
|-----------|-------|
| Phase ID | `extract` |
| Display Name | Architecture Facts Extraction |
| Type | Pipeline (deterministic, **NO LLM**) |
| Entry Point | `pipelines/architecture_facts/pipeline.py` → `ArchitectureFactsPipeline` |
| Output | `knowledge/extract/` |
| Dependency | Discover |
| Status | **IMPLEMENTED** |

> **Diagram:** [phase-1-extract-architecture.drawio](phase-1-extract-architecture.drawio)

Extract creates the **single source of truth for architecture**. No interpretation, no LLM, no documentation — only facts and evidence. Everything not in Extract output must NOT appear in downstream phases.

## 2. Goals

- Deterministically extract 16 architecture dimensions from source code
- Build a canonical model with normalized component IDs
- Map all relations via a 7-tier resolution pipeline
- Trace request flows (Controller → Service → Repository chains)
- Produce evidence for every extracted fact (file path, line number)

## 3. Inputs & Outputs

| Direction | Artifact | Format | Path |
|-----------|----------|--------|------|
| **Input** | Target repository | File system | `PROJECT_PATH` |
| **Input** | Repo manifest (optional) | JSON | `knowledge/discover/repo_manifest.json` |
| **Output** | Architecture facts | JSON | `knowledge/extract/architecture_facts.json` |
| **Output** | Evidence map | JSON | `knowledge/extract/evidence_map.json` |

## 4. Architecture

### Collector System

The collector system uses a modular architecture with an **Orchestrator** that coordinates **Dimension Collectors** and **Specialist Collectors**.

**Orchestrator** (`collectors/orchestrator.py`):
8-step flow: System → Container → Component → Interface → DataModel → Runtime → Infrastructure → Evidence

**Dimension Collectors:**

| Collector | Output | Description |
|-----------|--------|-------------|
| `SystemCollector` | system metadata | System name from root files |
| `ContainerCollector` | containers | Deployable units (pom.xml, package.json, Dockerfile) |
| `ComponentCollector` | components | Aggregates Spring + Angular specialists |
| `InterfaceCollector` | interfaces | REST endpoints, routes, schedulers |
| `DataModelCollector` | data model | JPA entities, SQL tables, migrations |
| `RuntimeCollector` | runtime | Schedulers, async, events |
| `InfrastructureCollector` | infrastructure | Docker, K8s, CI/CD |
| `EvidenceCollector` | evidence map | Aggregates all evidence |

**Specialist Collectors:**

| Specialist | Package | Extracts |
|------------|---------|----------|
| `SpringRestCollector` | `spring/` | @RestController, @RequestMapping |
| `SpringServiceCollector` | `spring/` | @Service, interface+impl mappings |
| `SpringRepositoryCollector` | `spring/` | JpaRepository, custom queries |
| `SpringConfigCollector` | `spring/` | @Configuration, application.yml |
| `SpringSecurityCollector` | `spring/` | Security configs |
| `AngularModuleCollector` | `angular/` | @NgModule |
| `AngularComponentCollector` | `angular/` | @Component |
| `AngularServiceCollector` | `angular/` | @Injectable services |
| `AngularRoutingCollector` | `angular/` | RouterModule, routes |
| `OracleTableCollector` | `database/` | CREATE TABLE (multi-dialect) |
| `MigrationCollector` | `database/` | Flyway, Liquibase |

### 7-Tier Relation Resolution

`ModelBuilder` resolves raw component names to canonical IDs:

| Tier | Strategy | Example |
|------|----------|---------|
| 1 | Direct old-ID mapping | `"comp_1_ActionService"` → canonical |
| 2 | Already canonical | `"component.backend.service.action_service"` |
| 3 | Exact name match (unambiguous) | `"ActionService"` → 1 candidate |
| 4 | Disambiguate by stereotype hint | `"service:ActionService"` → unique |
| 5 | Interface-to-implementation | `"OrderService"` → `"OrderServiceImpl"` |
| 6 | Fuzzy suffix match | `"UserService"` ↔ `"UserServiceImpl"` |
| 7 | File path match | `from_file_hint` → component owning that file |

### Endpoint Flow Builder

Constructs evidence-based request chains from REST interfaces:

```
Interface: POST /workflow/create
  → Controller: WorkflowController (via implemented_by)
    → Service: WorkflowServiceImpl (via relation: uses)
      → Repository: WorkflowRepository (via relation: uses)
```

Chain depth limited to 5 levels. Only flows with 2+ elements included.

### FactAdapter Pipeline

Bridges collector outputs (Raw types) to legacy types consumed by ModelBuilder:

```
Collectors (RawComponent, RawInterface, RelationHint)
  → FactAdapter.to_collected_*()
  → DimensionResultsAdapter.convert()
  → ModelBuilder.build() → CanonicalModel (normalized, deduplicated)
```

## 5. Patterns & Decisions

| Decision | Rationale |
|----------|-----------|
| No LLM | Facts must be deterministic and reproducible |
| Specialist collectors | Modular — add new frameworks without touching existing code |
| 7-tier resolution | Handles ambiguous references (same class name in different packages) |
| Evidence-first | Every fact traceable to file + line number |

### Rules (MUST FOLLOW)

| DO | DO NOT |
|-------|-----------|
| Extract only detectable facts | Use LLM |
| Reference evidence for every fact | Describe responsibilities |
| Mark UNKNOWN if no evidence | Make architecture decisions |
| Use exact class/file names | Summarize or interpret |

## 6. Dependencies

- **Upstream**: Phase 0 (Discover) — `repo_manifest.json` for framework hints (optional)
- **Downstream**:
  - Phase 2 (Analyze): `architecture_facts.json` as primary input
  - Phase 3 (Document): `architecture_facts.json` + `evidence_map.json`
  - Phase 4 (Plan): All 17 keys of `architecture_facts.json`
  - Phase 5 (Implement): File path resolution + facts queries

## 7. Quality Gates & Validation

- `QualityValidator`: checks extracted facts for completeness
- `PhaseOutputValidator`: verifies `architecture_facts.json` exists and has required keys before downstream phases run

## 8. Configuration

No phase-specific configuration — Extract uses `PROJECT_PATH` and runs deterministically.

## 9. Risks & Open Points

- New frameworks require new specialist collectors
- Specialist collectors are regex-based — may miss unusual code patterns
- `ComponentCollector` handles Java, TypeScript, Node.js; other languages need extension

---

© 2026 Aymen Mastouri. All rights reserved.
