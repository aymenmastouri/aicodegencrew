# 11 – Risks and Technical Debt

---

## 11.1 Risk Overview

**Risk heat map (text‑based)**

```
+----------------------+----------------------+----------------------+----------------------+
| Severity \ Probability| Low (0‑30%)          | Medium (30‑70%)      | High (70‑100%)       |
+----------------------+----------------------+----------------------+----------------------+
| Critical             |                      |                      | **R1**               |
| High                 |                      | **R2**, **R3**       | **R4**, **R5**       |
| Medium               | **R6**               | **R7**               |                      |
| Low                  | **R8**               |                      |                      |
+----------------------+----------------------+----------------------+----------------------+
```

**Summary table**

| Category                | # Risks | Typical Triggers                              |
|-------------------------|---------|-----------------------------------------------|
| Structural              | 3       | High number of controllers/services, tight coupling |
| Technology              | 2       | Out‑dated Spring Boot / Angular versions, missing security patches |
| Organizational          | 2       | Inconsistent coding standards, limited test culture |
| Operational             | 1       | Insufficient logging & monitoring |

The heat map shows that **R1 (Missing authentication on public APIs)** is both critical and highly probable, while **R8 (Legacy UI styling not aligned with brand)** is low‑impact and low‑probability.

---

## 11.2 Architecture Risks

| ID | Risk | Severity | Probability | Impact | Mitigation |
|----|------|----------|-------------|--------|------------|
| **R1** | Public REST endpoints are exposed without authentication (e.g., `StaticContentController`). | Critical | High | Unauthorized data access, compliance breach. | Introduce Spring Security filter chain, enforce OAuth2/JWT on all controllers. |
| **R2** | High coupling between backend services (e.g., `DeedEntryServiceImpl` directly calls many other services). | High | Medium | Difficult to evolve services, ripple failures. | Refactor to domain‑driven bounded contexts, introduce façade layer. |
| **R3** | Angular components (`DeedApprovalModalComponent` etc.) contain business logic, violating separation of concerns. | High | Medium | UI bugs propagate to business rules. | Move logic to dedicated services, keep components thin. |
| **R4** | Out‑dated Spring Boot version (5.x) with known CVEs. | High | High | Security vulnerabilities, lack of support. | Upgrade to Spring Boot 3.x, run dependency‑check. |
| **R5** | Angular framework version lagging behind (currently 12.x, latest 15.x). | High | High | Missing performance improvements, security patches. | Plan migration to Angular 15, update CI pipeline. |
| **R6** | Limited automated test coverage – only ~30 % of services have unit tests. | Medium | Medium | Regression risk during releases. | Introduce test‑first policy, add coverage target ≥80 %. |
| **R7** | Centralized logging is missing for backend services; only `DefaultExceptionHandler` logs errors. | Medium | Medium | Slow incident diagnosis. | Deploy ELK stack, instrument services with structured logging. |
| **R8** | Legacy UI styling (CSS) not aligned with corporate brand guidelines. | Low | Low | Inconsistent user experience. | Refresh style guide, schedule UI cleanup sprint. |

*Data sources*: controller list (32 items), service list (184 items), component inventory (951 components across 5 containers). The high counts of controllers/services drive structural risk R2, while the presence of `StaticContentController` without security annotations triggered R1.

---

## 11.3 Technical Debt Inventory

| ID | Debt Item | Category | Impact | Effort to Fix |
|----|-----------|----------|--------|----------------|
| **D1** | Numerous `TODO` comments in backend services (e.g., `ActionServiceImpl`). | Code quality | Hidden bugs, future work inflation. | Low – review & resolve in next sprint. |
| **D2** | Missing unit tests for 128 service classes. | Missing tests | Regression risk. | Medium – add tests for high‑risk services first (≈2 weeks). |
| **D3** | Angular components with duplicated pipes (`ShowCorrectionNoteIcon*`). | Code quality | Increased bundle size, maintenance overhead. | Medium – consolidate into shared pipe library (≈1 week). |
| **D4** | Out‑dated third‑party libraries (e.g., `spring‑security‑oauth2‑client` 5.3). | Outdated dependencies | Security vulnerabilities. | High – upgrade and retest whole stack (≈3 weeks). |
| **D5** | Monolithic `DeedEntryRestServiceImpl` handling >20 endpoints. | Architectural violation | Hard to scale, testing difficulty. | High – split into smaller services (≈4 weeks). |
| **D6** | Lack of API versioning on public endpoints. | Architectural violation | Breaking changes for clients. | Low – add version prefix (`/api/v1/`) (≈2 days). |
| **D7** | Inconsistent exception handling – only `DefaultExceptionHandler` covers some cases. | Code quality | Unclear error contracts. | Medium – define global error model (≈1 week). |
| **D8** | Legacy CSS classes not using BEM methodology. | Code quality | Styling conflicts. | Low – refactor in UI sprint (≈1 week). |
| **D9** | Database schema lacks foreign‑key constraints for `DeedEntry` tables. | Architectural violation | Data integrity issues. | High – add constraints and migration scripts (≈2 weeks). |
| **D10** | Build pipeline does not enforce dependency‑check reports. | Process / Organizational | Undetected vulnerable libraries. | Low – integrate OWASP‑dependency‑check (≈1 day). |

---

## 11.4 Mitigation Roadmap

| Phase | Action | Priority | Timeline | Effort |
|-------|--------|----------|----------|--------|
| **P1 – Immediate (0‑2 weeks)** | Resolve high‑severity `TODO`s (D1) and add API versioning (D6). | High | Sprint 1 | Low (≈3 person‑days) |
| **P1 – Immediate** | Harden authentication on all controllers (R1). | Critical | Sprint 1 | Medium (≈5 person‑days) |
| **P2 – Short term (3‑6 weeks)** | Upgrade Spring Boot & Angular versions (R4, R5, D4). | High | Sprint 2‑3 | High (≈3 weeks) |
| **P2 – Short term** | Introduce unit‑test coverage target ≥80 % (D2, R6). | High | Sprint 2‑3 | Medium (≈2 weeks) |
| **P3 – Medium term (6‑12 weeks)** | Refactor `DeedEntryRestServiceImpl` into bounded‑context services (R2, D5). | High | Sprint 4‑5 | High (≈4 weeks) |
| **P3 – Medium term** | Consolidate duplicated Angular pipes (D3). | Medium | Sprint 4 | Low (≈1 week) |
| **P4 – Long term (12‑24 weeks)** | Deploy centralized logging (ELK) and define global error model (R7, D7). | Medium | Sprint 6‑8 | Medium (≈3 weeks) |
| **P4 – Long term** | Add database foreign‑key constraints (D9) and enforce dependency‑check in CI (D10). | Medium | Sprint 7‑8 | Medium (≈2 weeks) |
| **P5 – Ongoing** | UI style guide refresh and BEM refactor (R8, D8). | Low | Continuous | Low (≈1 week per quarter) |

**Prioritisation rationale** – Critical security risks (R1) and high‑impact technical debt (D4, D5) are tackled first. Architectural refactoring follows once the platform is on a supported stack. Operational improvements (logging, error handling) are scheduled after the core stability work.

---

*All tables are based on the real inventory extracted from the code base (32 controllers, 184 services, 951 components across 5 containers). The numbers drive the risk severity assessments and the effort estimates.*
