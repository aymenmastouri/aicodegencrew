# Phase 8 — Deliver (Review & Deploy)

> **Status**: PLANNED | **Type**: Pipeline | **Layer**: Execution

---

## 1. Overview

| Attribute | Value |
|-----------|-------|
| Phase ID | `deliver` |
| Display Name | Review & Deploy |
| Type | Pipeline (deterministic) |
| LLM Requirement | Minimal (PR description generation) |
| Module | `pipelines/deliver/` (planned) |
| Status | **PLANNED** |

The Deliver phase will handle the final steps of the SDLC: creating pull requests, running CI/CD validations, and preparing changes for merge.

## 2. Goals

- Create pull requests with structured descriptions from codegen reports
- Run CI/CD pipeline validations
- Generate PR review summaries
- Prepare changes for merge after approval

## 3. Inputs & Outputs

| Direction | Artifact | Format | Source |
|-----------|----------|--------|--------|
| **Input** | Code generation branch | `codegen/{task_id}` (git) | Phase 5 |
| **Input** | Test results | `knowledge/verify/{task_id}_test_report.json` | Phase 6 |
| **Input** | Codegen report | `knowledge/implement/{task_id}_report.json` | Phase 5 |
| **Output** | Pull request | Git platform (GitHub/GitLab) | — |
| **Output** | Delivery report | `knowledge/deliver/{task_id}_delivery.json` | — |

## 4. Architecture

Planned as a deterministic pipeline:

```
Read codegen report → Generate PR description → Create PR
  → Run CI checks → Report status
```

## 5. Dependencies

- **Upstream**: Phase 5 (Implement) — code changes, Phase 6 (Verify) — test results
- **Downstream**: None (final phase)

## 6. Risks & Open Points

- Git platform integration (GitHub vs GitLab vs Bitbucket) needs abstraction
- CI/CD pipeline configuration varies per project
- Merge strategy (squash, rebase, merge commit) should be configurable

---

© 2026 Aymen Mastouri. All rights reserved.
