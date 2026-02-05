# SDLC Automation with CrewAI (On-Prem) – Enterprise Blueprint

> **Also available in:** [German (Deutsch)](SDLC_BLUEPRINT_DE.md)

## Vision

Automate a significant portion of the **Software Development Lifecycle (SDLC)** using **CrewAI** – including ticket/spec, design/ADR, implementation, tests, review, documentation, and release notes – **with human gates** for quality and accountability.

> Realistic expectation: **Not 100% "autonomous to production"**, but **80/20** is achievable when combining LLM + deterministic tools + policies.

---

## Core Principle: CrewAI Orchestrates, Tools Ensure Facts

**CrewAI** serves as the orchestration layer (roles/agents + pipeline/tasks).  
For reliability, you need **deterministic tools** (build, tests, lint, repo-scan, security-scan, git diff, Jira/Confluence APIs).  
The LLM (e.g., **gpt-oss-120b**, GPT-4, Claude) is primarily used for **synthesis and text/code drafts**.

---

## 4-Layer Architecture Model

> **Reference:** [AI_SDLC_ARCHITECTURE.md](AI_SDLC_ARCHITECTURE.md) | [Diagrams](diagrams/)

| Layer | Phases | Purpose | LLM Required | Status |
|-------|--------|---------|--------------|--------|
| **KNOWLEDGE** | 0-1 | Deterministic facts extraction | No | IMPLEMENTED |
| **REASONING** | 2-3 | LLM-powered analysis and synthesis | Yes | PARTIAL |
| **EXECUTION** | 4-6 | Code generation and deployment | Yes | PLANNED |
| **FEEDBACK** | 7 | Continuous learning and quality | Yes | PLANNED |

---

## What Is Highly Automatable (80/20)

### 1) Intake → Ticket/Spec
- From texts (Jira/Teams/Slack/Email): Problem, Scope, Out-of-scope
- **Acceptance Criteria (ACs)** + DoD proposal
- Risk and dependency list

### 2) Design & Architecture Artifacts
- ADR draft (options, decision, consequences)
- C4 descriptions (Context/Container/Component)
- API contract draft (OpenAPI)
- Data model draft (tables/relationships)

### 3) Implementation
- Code scaffolds, feature implementation in small increments
- Refactoring suggestions
- Standardized commit and PR descriptions

### 4) Testing
- Unit tests, contract tests, test data
- Identification of missing edge cases

### 5) Code Review & Quality
- Review comments, risks, "smells"
- Security/performance checklists (hints, not approvals)

### 6) Documentation
- README, Confluence pages, architecture notes
- Release notes/changelog drafts

### 7) DevOps/CI
- Pipeline YAML suggestions
- Helm/K8s manifests (with rules/policies)
- Observability snippets (health, metrics, logs)

---

## What Only Partially Works (and Needs Gates)

### Debugging with Real Runtime
AI helps significantly **with logs/traces/metrics**, but needs real observability data and repro steps.

### Security & Compliance
AI can check/flag – **approval remains human** (governance, audit).

### Business Logic & Prioritization
Requirements interpretation, prioritization, and risk decisions remain team/PO responsibility.

### Autonomous Merging Without Review
Not recommended. Use policies/gates (tests green, security scan, review).

---

## Recommended End-to-End Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1: KNOWLEDGE (Deterministic, No LLM)                     │
├─────────────────────────────────────────────────────────────────┤
│  Phase 0: Indexing          Phase 1: Architecture Facts         │
│  - ChromaDB vector store    - 10 Collectors (Spring, Angular)   │
│  - File discovery           - 733 components extracted          │
│  - Code chunking            - 125 interfaces, 169 relations     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 2: REASONING (LLM-Powered)                               │
├─────────────────────────────────────────────────────────────────┤
│  Phase 2: Synthesis         Phase 3: Task Understanding         │
│  - C4 diagrams              - Issue analysis                    │
│  - arc42 documentation      - Scope determination               │
│  - Quality assessment       - Impact analysis                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 3: EXECUTION (LLM-Powered)                               │
├─────────────────────────────────────────────────────────────────┤
│  Phase 4: CodeGen    Phase 5: Testing    Phase 6: Deploy        │
│  - Pattern-compliant - Unit tests        - PR creation          │
│  - Small increments  - Integration       - CI validation        │
│  - Refactoring       - Edge cases        - Merge preparation    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 4: FEEDBACK (Continuous)                                 │
├─────────────────────────────────────────────────────────────────┤
│  Phase 7: Learning                                              │
│  - Quality metrics collection                                   │
│  - Pattern learning from successful changes                     │
│  - Knowledge base updates                                       │
└─────────────────────────────────────────────────────────────────┘
        │                                                    ▲
        └────────────────────────────────────────────────────┘
                         Feedback Loop
```

**Human Gate**: Review/Approval → Merge/Release

---

## Agent Structure (Minimal Setup: 5 Agents)

| Agent | Responsibility | Layer |
|-------|---------------|-------|
| **Analyst** | Issue → Spec + ACs | Reasoning |
| **Engineer** | Code/Refactor | Execution |
| **Tester** | Tests/Regression | Execution |
| **Reviewer** | Review + Checklists | Execution |
| **DocWriter** | Docs/Release Notes | Execution |

---

## Prerequisites for Good Results

### 1) Context Strategy (Repo is Too Large)
- **RAG/Indexing** or targeted code excerpts
- Split tasks into small steps (no "mega prompts")

### 2) Guardrails / Policies
- "Don't invent APIs"
- Coding standards / architecture rules
- "Only changes within defined scope"
- "If uncertain: ask questions / mark TODO"

### 3) Deterministic Quality Signals
- `lint/format` must be green
- `unit/integration` tests must be green
- Security scan results documented
- PR template + checklist mandatory

---

## Tooling Backbone

### Repo & Code
- Repo scanner (grep/AST), Git diff, Semgrep, Sonar (optional)
- Formatter/Linter (e.g., Spotless, ESLint)
- Build/Test runner (Maven/Gradle, npm, Playwright)

### ALM/Docs
- Jira API (issues/comments/status)
- Confluence API (pages/templates)
- GitLab/GitHub API (branches/PRs/MRs)

### Runtime (optional)
- Logs/Traces/Metrics (OpenTelemetry, Loki, Prometheus, etc.)
- Kubernetes API (deployments/pods/events)

---

## Quality Gates (Recommended)

| Gate | Automated | Human |
|------|-----------|-------|
| Build successful | Yes | - |
| Unit/Integration tests green | Yes | - |
| Lint/Format green | Yes | - |
| Security findings evaluated | Partial | Yes |
| Code review approval | - | Yes (min. 1) |

---

## Current Implementation Status (AICodeGenCrew)

| Component | Status | Notes |
|-----------|--------|-------|
| Phase 0: Indexing | DONE | ChromaDB, file discovery |
| Phase 1: Facts | 80% | 733 components, relation resolution at 54% |
| Phase 2: Synthesis | DONE | C4, arc42 generation |
| Phase 3-7 | PLANNED | Roadmap Q1 2026 |

### Target Stack
- **Backend:** Spring Boot (Java)
- **Frontend:** Angular (TypeScript)
- **Infrastructure:** On-Prem, GitLab, Jira/Confluence
- **LLM:** OpenAI-compatible API (local or cloud)

---

## Result

With CrewAI + LLM you can **strongly automate** the SDLC, as long as you:
- Break work into **deterministic steps**,
- Use **tools** as "source of truth",
- And maintain **human gates** for responsibility/quality.

---

## References

- [AI_SDLC_ARCHITECTURE.md](AI_SDLC_ARCHITECTURE.md) - Technical architecture details
- [SDLC_95_ARCHITECTURE.md](SDLC_95_ARCHITECTURE.md) - Full 95% automation vision
- [diagrams/](diagrams/) - Professional draw.io diagrams
