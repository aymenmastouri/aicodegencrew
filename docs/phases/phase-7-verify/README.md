# Phase 7 — Verify (Test Generation)

> **Status**: PLANNED | **Type**: Crew | **Layer**: Execution

---

## 1. Overview

| Attribute | Value |
|-----------|-------|
| Phase ID | `verify` |
| Display Name | Test Generation |
| Type | Crew (AI Agents) |
| LLM Requirement | Yes |
| Module | `crews/testing/` |
| Status | **PLANNED** |

The Verify phase will generate comprehensive test suites for code changes produced by Phase 6 (Implement). Tests will match existing repository conventions (JUnit 5 + Mockito for Spring Boot, Jasmine + TestBed for Angular).

## 2. Goals

- Generate unit tests for all code changes from Phase 6
- Match existing test patterns and frameworks in the target repository
- Achieve meaningful coverage of modified code paths
- Produce tests that compile and run against the target codebase

## 3. Inputs & Outputs

| Direction | Artifact | Format | Source |
|-----------|----------|--------|--------|
| **Input** | Code generation report | `knowledge/implement/{task_id}_report.json` | Phase 5 |
| **Input** | Generated code branch | `codegen/{task_id}` (git) | Phase 5 |
| **Input** | Architecture facts | `knowledge/extract/architecture_facts.json` | Phase 1 |
| **Input** | Test patterns | `architecture_facts.json` → `tests` dimension | Phase 1 |
| **Output** | Generated test files | On git branch | — |
| **Output** | Test generation report | `knowledge/verify/{task_id}_test_report.json` | — |

## 4. Architecture

Planned as a CrewAI crew with specialized test generation agents:

```
Read codegen report → Identify changed files → Query test patterns
  → Generate unit tests → Run tests → Report coverage
```

## 5. Dependencies

- **Upstream**: Phase 5 (Implement) — code changes to test
- **Downstream**: Phase 7 (Deliver) — test results for PR readiness

## 6. Risks & Open Points

- Test execution requires build environment (same build-tool dependency as Phase 5)
- Test quality depends on LLM understanding of business logic
- May need fallback to template-based test generation for simpler cases

---

© 2026 Aymen Mastouri. All rights reserved.
