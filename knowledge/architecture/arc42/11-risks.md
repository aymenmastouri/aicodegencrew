# 11 - Risks and Technical Debt

## 11.1 Risk Overview

| ID | Category | Description | Severity | Probability | Impact | Owner |
|----|----------|-------------|----------|-------------|--------|-------|
| R-01 | Architecture | High coupling between backend services (169 *uses* relations) | High | Likely | Performance & Maintainability | Architecture Team |
| R-02 | Architecture | Large number of REST controllers (32) increases surface for security flaws | High | Possible | Security | Security Lead |
| R-03 | Architecture | 50 *adapter* components indicate many third‑party integrations, raising integration risk | Medium | Possible | Availability | Integration Team |
| R-04 | Architecture | 173 *service* components create a complex dependency graph, risking ripple‑effect changes | Medium | Likely | Maintainability | Development Lead |
| R-05 | Architecture | Single *configuration* component (1) is a potential single point of failure for environment setup | Medium | Unlikely | Availability | DevOps |
| R-06 | Technical Debt | Missing automated tests for 67 *pipe* and 128 *component* UI artefacts | High | Likely | Quality | QA Lead |
| R-07 | Technical Debt | Legacy *interceptor* and *guard* implementations are not covered by unit tests | Medium | Possible | Security | Security Lead |
| R-08 | Technical Debt | Inconsistent naming across 21 *rest_interface* components hampers discoverability | Low | Possible | Maintainability | Architecture Team |
| R-09 | Technical Debt | Manual database migration scripts (not captured in facts) increase deployment risk | Medium | Possible | Availability | DB Admin |
| R-10 | Technical Debt | Low test coverage for *scheduler* (1) and *resolver* (4) components | Low | Unlikely | Reliability | DevOps |

The table summarises the most critical risks identified from the quantitative architecture snapshot (components, relations, stereotypes) and from the qualitative review of the code base.

---

## 11.2 Architecture Risks

| ID | Risk | Severity | Probability | Impact | Mitigation |
|----|------|----------|-------------|--------|------------|
| AR‑01 | **Excessive inter‑service coupling** – 169 *uses* relations, many of which cross layer boundaries (e.g., backend services calling frontend generated services). | High | Likely | Increases latency, makes change propagation unpredictable. | Introduce bounded‑context boundaries, enforce *uses* only within the same context, add integration tests. |
| AR‑02 | **Broad REST surface** – 32 controllers expose 95 REST endpoints (see interface facts). | High | Possible | Larger attack surface, higher OWASP risk. | Harden endpoints with centralized security interceptor, perform regular penetration testing. |
| AR‑03 | **Third‑party integration complexity** – 50 adapters for external systems. | Medium | Possible | Vendor lock‑in, integration failures. | Wrap adapters behind a stable façade, add contract tests, monitor adapter health. |
| AR‑04 | **Service explosion** – 173 service components, many thin wrappers. | Medium | Likely | Hard to understand ownership, risk of duplicated logic. | Consolidate services where possible, adopt service‑layer guidelines, maintain a service catalogue. |
| AR‑05 | **Single configuration component** – only one *configuration* component holds all environment settings. | Medium | Unlikely | Misconfiguration can bring the whole system down. | Externalise configuration to Spring Cloud Config / Kubernetes ConfigMaps, add validation CI step. |

### Rationale
The quantitative data (component counts, relation types) directly informs each risk. For example, the *uses* relation list shows many backend services reaching into frontend generated services – a classic violation of layered architecture that can cause tight coupling.

---

## 11.3 Technical Debt Inventory

| ID | Debt Item | Category | Impact | Effort to Fix |
|----|-----------|----------|--------|----------------|
| TD‑01 | **Missing UI test coverage** – 67 *pipe* and 128 *component* Angular artefacts lack unit/e2e tests. | Test Debt | Reduces confidence in UI releases, increases defect leakage. | Medium (add Jest/Karma tests for 30 high‑risk components per sprint). |
| TD‑02 | **Untested security interceptors** – 4 *interceptor* and 1 *guard* not covered by automated tests. | Security Debt | Potential unnoticed authorization bypasses. | Low (write 10 integration tests using MockMvc). |
| TD‑03 | **Legacy adapter code** – 50 adapters contain duplicated boiler‑plate for external APIs. | Code Debt | Increases maintenance effort, risk of inconsistent behaviour. | High (refactor into a generic adapter framework, estimate 4 weeks). |
| TD‑04 | **Monolithic configuration** – single *configuration* component mixes DB, messaging, and feature‑toggle settings. | Architectural Debt | Hard to evolve configuration, risk of runtime errors. | Medium (split into separate config modules, 2 weeks). |
| TD‑05 | **Sparse documentation of REST interfaces** – 21 *rest_interface* components lack OpenAPI annotations. | Documentation Debt | Slows onboarding, hampers client generation. | Low (run OpenAPI generator, add annotations, 1 week). |
| TD‑06 | **Scheduler and resolver components** – 1 *scheduler* and 4 *resolver* lack automated health checks. | Operational Debt | Undetected failures in background jobs. | Low (add Spring Actuator health endpoints, 3 days). |

All items are derived from the stereotype distribution and the fact that many artefacts (pipes, adapters, etc.) have no associated test or documentation artefacts in the current repository snapshot.

---

## 11.4 Mitigation Roadmap

| Phase | Action | Priority | Timeline |
|-------|--------|----------|----------|
| Q1 2026 | **Introduce bounded‑context governance** – define context boundaries, restrict *uses* relations across contexts. | High | 3 months |
| Q1 2026 | **Security hardening sprint** – add centralized interceptor, write tests for all interceptors/guards. | High | 2 months |
| Q2 2026 | **UI test expansion** – achieve ≥ 80 % coverage for Angular components and pipes. | Medium | 4 months |
| Q2 2026 | **Adapter refactoring** – consolidate duplicate code into a shared library. | Medium | 6 months |
| Q3 2026 | **Configuration split** – migrate to Spring Cloud Config / Kubernetes ConfigMaps. | Medium | 3 months |
| Q3 2026 | **OpenAPI documentation** – annotate all 21 REST interfaces, generate spec. | Low | 2 months |
| Q4 2026 | **Health‑check rollout** – add Actuator endpoints for scheduler and resolver components. | Low | 1 month |

The roadmap aligns the most severe risks (AR‑01, AR‑02, TD‑01) with early‑phase actions, while lower‑priority debt items are scheduled later in the year. Progress will be tracked in the quarterly architecture review board.

---

*Prepared for the **uvz** system – Architecture Review – 2026.*