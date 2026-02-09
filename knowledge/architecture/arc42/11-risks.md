# 11 – Risks and Technical Debt

---

## 11.1 Risk Overview

**Risk heat map (text‑based)**

```
| Severity \ Probability | Low   | Medium | High |
|------------------------|-------|--------|------|
| **Low**                |   –   |   –    |  R1  |
| **Medium**             |   –   |  R2,R3 | R4,R5 |
| **High**               |  R6   | R7,R8  |  –   |
```

*Legend*: **R1‑R8** refer to the detailed risk entries in the next section.

**Summary table**

| ID | Risk | Category | Severity | Probability | Impact | Mitigation |
|----|------|----------|----------|-------------|--------|------------|
| R1 | Single point of failure in *configuration* component (only 1 instance) | Technology | Low | High | System outage if configuration fails | Introduce redundant configuration service and health‑check monitoring |
| R2 | High coupling between controllers and repositories (direct `@Autowired` usage) | Structural | Medium | Medium | Difficult to evolve domain model | Refactor to service layer mediation, enforce clean architecture rules |
| R3 | Large number of REST endpoints (196) increases surface for security flaws | Operational | Medium | Medium | Potential data breach | Conduct regular OWASP API Security testing, apply API gateway policies |
| R4 | Outdated Spring Boot version (major version lag) | Technology | Medium | High | Compatibility and security risks | Plan upgrade to latest LTS, allocate migration sprint |
| R5 | Insufficient automated test coverage (estimated < 40 %) | Organizational | Medium | Medium | Regression defects in releases | Introduce test‑coverage targets, add unit/integration test budget |
| R6 | Manual deployment process for *container.backend* (no CI/CD) | Operational | Low | High | Deployment errors, downtime | Implement CI/CD pipeline with automated roll‑back |
| R7 | High number of adapters (50) indicates possible duplication of integration code | Structural | Medium | Medium | Maintenance overhead | Consolidate adapters, define shared integration library |
| R8 | Lack of runtime monitoring for background jobs (e.g., `JobServiceImpl`) | Operational | Low | Medium | Undetected job failures | Add centralized logging and health‑checks for scheduled jobs |

---

## 11.2 Architecture Risks

| ID | Risk | Category | Severity | Probability | Impact | Mitigation |
|----|------|----------|----------|-------------|--------|------------|
| A1 | **Monolithic controller layer** – 32 controllers directly expose 196 endpoints, leading to tangled request handling. | Structural | Medium | High | Hard to maintain, high change‑impact. | Group controllers by bounded context, introduce API‑gateway routing, enforce thin‑controller pattern. |
| A2 | **Service layer bloat** – 184 services, many with overlapping responsibilities (e.g., `ActionServiceImpl`, `ArchiveManagerServiceImpl`). | Structural | Medium | Medium | Cognitive overload, duplicated logic. | Conduct service inventory, merge similar services, apply domain‑driven design boundaries. |
| A3 | **Entity explosion** – 360 domain entities, many with limited usage, risk of anemic model. | Structural | Low | Medium | Increased schema complexity, migration pain. | Review entity relevance, archive obsolete entities, adopt aggregate roots. |
| A4 | **Repository‑direct controller access** – Several controllers reference repository beans directly (observed in code base). | Structural | High | Medium | Violates separation of concerns, testing difficulty. | Enforce service‑mediated data access, add static analysis rule. |
| A5 | **Technology lock‑in** – Predominant use of Spring Boot and Angular without abstraction layers. | Technology | Medium | Low | Future migration cost. | Introduce façade modules, evaluate alternative frameworks for new features. |
| A6 | **Insufficient security annotations** – Few `@PreAuthorize` or method‑level checks found. | Operational | High | Medium | Unauthorized access risk. | Apply security‑by‑design, add comprehensive security annotations, integrate security scans. |
| A7 | **Lack of version control for dependencies** – No automated dependency‑update bot. | Technology | Medium | High | Vulnerable libraries remain unpatched. | Integrate Dependabot or Renovate, schedule quarterly dependency review. |
| A8 | **Operational monitoring gaps** – Background jobs (`JobServiceImpl`, `ReencryptionJobRestServiceImpl`) lack health endpoints. | Operational | Low | Medium | Silent failures, SLA breach. | Add Prometheus metrics, expose job status via actuator. |

---

## 11.3 Technical Debt Inventory

| ID | Debt Item | Category | Impact | Effort to Fix |
|----|-----------|----------|--------|----------------|
| D1 | Missing unit tests for 45 % of services (e.g., `KeyManagerServiceImpl`) | Missing Tests | High – regression risk | Medium (2 sprints) |
| D2 | Legacy `@Autowired` field injection still used in many controllers | Code Quality | Medium – harder to mock | Low (1 sprint) |
| D3 | Outdated Spring Boot 2.3.x (current LTS 3.x) | Outdated Dependencies | High – security & support | High (3 sprints) |
| D4 | Duplicate adapter implementations (≈12 similar adapters) | Architectural Violations | Medium – maintenance overhead | Medium (2 sprints) |
| D5 | Hard‑coded URLs in `StaticContentController` | Code Quality | Low – brittle configuration | Low (1 sprint) |
| D6 | No centralized error handling for REST layer (multiple `@ExceptionHandler` scattered) | Architectural Violations | Medium – inconsistent responses | Low (1 sprint) |
| D7 | Large controller classes (>1500 LOC) – e.g., `ReportRestServiceImpl` | Code Quality | High – readability & testability | Medium (2 sprints) |
| D8 | Absence of API versioning strategy (all endpoints under same base path) | Architectural Violations | Medium – breaking changes | Low (1 sprint) |
| D9 | Inconsistent logging format across services | Code Quality | Low – log aggregation difficulty | Low (1 sprint) |
| D10 | Missing integration tests for external system adapters | Missing Tests | High – integration failures undetected | High (2 sprints) |

---

## 11.4 Mitigation Roadmap

| Phase | Action | Priority | Timeline | Effort |
|-------|--------|----------|----------|-------|
| **Phase 1 – Quick Wins (0‑3 months)** | Introduce CI/CD pipeline for `container.backend` | High | Q1 2026 | 2 weeks |
|  | Replace field injection with constructor injection in controllers | High | Q1 2026 | 1 sprint |
|  | Add centralized `@ControllerAdvice` for error handling | Medium | Q1 2026 | 1 sprint |
|  | Enable Dependabot for dependency updates | High | Q1 2026 | 1 week |
| **Phase 2 – Stabilisation (3‑9 months)** | Refactor direct repository access to service layer | High | Q2‑Q3 2026 | 3 sprints |
|  | Consolidate duplicate adapters into shared library | Medium | Q2‑Q3 2026 | 2 sprints |
|  | Implement API versioning and gateway routing | Medium | Q3 2026 | 2 sprints |
|  | Increase unit test coverage to 70 % for services | High | Q3‑Q4 2026 | 4 sprints |
| **Phase 3 – Strategic Improvements (9‑18 months)** | Upgrade Spring Boot to 3.x LTS | High | Q4 2026‑Q1 2027 | 3 sprints |
|  | Introduce domain‑driven design boundaries (aggregate roots) | Medium | Q1‑Q2 2027 | 4 sprints |
|  | Deploy centralized monitoring (Prometheus + Grafana) for background jobs | Medium | Q2 2027 | 2 sprints |
|  | Conduct security hardening (method‑level `@PreAuthorize`, OWASP scans) | High | Q2‑Q3 2027 | 3 sprints |

---

*The roadmap aligns with the organization’s risk appetite and capacity. Priorities are driven by severity and probability from the risk overview, ensuring that the most critical issues are addressed first.*
