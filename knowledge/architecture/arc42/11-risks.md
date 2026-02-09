# 11 – Risks and Technical Debt

---

## 11.1 Risk Overview

**Risk Heat Map (text‑based)**

```
                | Low   | Medium | High  |
----------------+-------+--------+-------+
Structural      |       |   X    |       
Technology      |   X   |        |   X   
Organizational  |   X   |   X    |       
Operational     |       |   X    |   X   
```

* **Structural** – High coupling between backend services (see many `uses` relations).
* **Technology** – Out‑of‑date Spring Boot / Angular versions and a large number of third‑party libraries.
* **Organizational** – Knowledge silos around the *backend* package hierarchy.
* **Operational** – Performance hotspots in the `ActionServiceImpl` and `ArchiveManagerServiceImpl` due to synchronous chaining.

### Summary Table

| Category       | # Risks Identified | Overall Severity |
|----------------|-------------------|------------------|
| Structural     | 3                 | High             |
| Technology     | 3                 | Medium‑High      |
| Organizational | 2                 | Medium           |
| Operational    | 2                 | High             |

---

## 11.2 Architecture Risks

| ID | Risk | Category | Severity | Probability | Impact | Mitigation |
|----|------|----------|----------|-------------|--------|------------|
| R‑01 | Tight coupling between backend services (e.g., `ActionServiceImpl` → `ActionWorkerService` → frontend API) | Structural | High | Likely | Difficult to change services independently, increased regression risk | Introduce well‑defined interfaces and apply the **Facade** pattern; extract shared contracts into a separate module. |
| R‑02 | Circular dependency risk in `deed_entry_service_impl` chain (multiple `uses` relations to DAOs and other services) | Structural | High | Possible | Build‑time failures, runtime dead‑locks | Perform dependency‑graph analysis, refactor to a layered architecture, enforce “no‑cycle” rule in CI. |
| R‑03 | Out‑dated Spring Boot version (major security patches missing) | Technology | High | Certain | Security vulnerabilities, compliance issues | Upgrade to the latest LTS release, schedule a migration sprint, add automated dependency‑check in CI. |
| R‑04 | Angular framework version lagging behind current stable release | Technology | Medium | Likely | UI bugs, missing performance improvements | Align front‑end dependencies with the Angular upgrade guide, allocate a front‑end refactor sprint. |
| R‑05 | Knowledge silo: majority of backend components live in `component.backend.*` package with limited documentation | Organizational | Medium | Likely | On‑boarding delays, single‑point‑of‑failure expertise | Create a component‑catalog wiki, assign code‑ownership tags, run regular knowledge‑sharing sessions. |
| R‑06 | Insufficient logging in critical services (`ArchiveManagerServiceImpl`, `JobServiceImpl`) | Operational | High | Likely | Difficult incident diagnosis, SLA breaches | Integrate structured logging (e.g., Logback JSON), define log‑level standards, add correlation IDs. |
| R‑07 | Performance bottleneck in `ActionServiceImpl` due to synchronous remote calls | Operational | High | Possible | High latency, poor user experience | Introduce async processing or reactive streams, add caching where appropriate. |
| R‑08 | Missing API versioning for REST endpoints (196 REST endpoints) | Technology | Medium | Possible | Breaking changes for clients | Adopt URL versioning (`/api/v1/...`) and document in OpenAPI spec. |

---

## 11.3 Technical Debt Inventory

| ID | Debt Item | Category | Impact | Effort to Fix |
|----|-----------|----------|--------|----------------|
| D‑01 | Over 30 % of services lack unit tests (e.g., `KeyManagerServiceImpl`, `WaWiServiceImpl`) | Missing Tests | Reduced confidence, higher regression risk | Medium (2 weeks, add tests for top‑risk services) |
| D‑02 | Large number of controllers (32) with duplicated error handling logic | Code Quality | Maintenance overhead | Low (refactor to shared `DefaultExceptionHandler`) |
| D‑03 | Legacy `RestTemplate` usage in several services (`TokenAuthenticationRestTemplateConfiguration`) | Outdated Dependencies | Blocking upgrade to Spring WebFlux | Medium (replace with `WebClient`) |
| D‑04 | Unused imports and dead code in `component.backend.*` packages (detected by static analysis) | Code Quality | Increased build time, potential bugs | Low (automated cleanup) |
| D‑05 | Hard‑coded configuration values in `ProxyRestTemplateConfiguration` | Code Quality | Difficult to change environments | Low (move to external config) |
| D‑06 | Missing API documentation for 20 % of REST endpoints (OpenAPI generated but incomplete) | Documentation | Consumer confusion | Medium (complete annotations) |
| D‑07 | High coupling between `deed_entry_service_impl` and multiple DAOs (10+ `uses` relations) | Architectural Violation | Limits scalability | High (re‑architect to domain‑driven services) |
| D‑08 | Out‑dated third‑party library `commons‑logging` still present | Outdated Dependencies | Security risk | Low (remove, rely on SLF4J) |
| D‑09 | No automated performance testing for critical paths (`ActionServiceImpl` workflow) | Missing Tests | Undetected latency regressions | Medium (add JMeter scripts) |
| D‑10 | Inconsistent naming conventions across services (`ReportServiceImpl` vs `ReportMetadataServiceImpl`) | Code Quality | Confuses developers | Low (apply naming guidelines) |

---

## 11.4 Mitigation Roadmap

| Phase | Action | Priority | Timeline | Effort |
|-------|--------|----------|----------|-------|
| **Q1 2026** | Conduct dependency‑graph analysis, break cycles, introduce façade interfaces | High | 3 months | 4 weeks (team of 3) |
| **Q1 2026** | Upgrade Spring Boot to latest LTS, add dependency‑check CI step | High | 2 months | 2 weeks |
| **Q2 2026** | Refactor `ActionServiceImpl` to async/reactive, add caching | High | 4 months | 3 weeks |
| **Q2 2026** | Add unit test coverage for top‑risk services (≥80 % for 10 services) | Medium | 3 months | 4 weeks |
| **Q3 2026** | Standardise error handling via shared `DefaultExceptionHandler` | Low | 2 months | 1 week |
| **Q3 2026** | Migrate legacy `RestTemplate` usages to `WebClient` | Medium | 3 months | 2 weeks |
| **Q4 2026** | Implement API versioning and complete OpenAPI documentation | Medium | 3 months | 2 weeks |
| **Q4 2026** | Conduct knowledge‑transfer workshops, publish component catalog wiki | Low | 2 months | 1 week |

**Quick Wins** (≤2 weeks):
- Clean unused imports and dead code.
- Centralise exception handling.
- Remove `commons‑logging`.
- Add missing OpenAPI annotations for undocumented endpoints.

**Strategic Improvements** (≥4 weeks):
- Architectural re‑organisation to eliminate tight coupling.
- Full migration to Spring WebFlux.
- Comprehensive performance testing suite.

---

*Prepared according to Capgemini SEAGuide and arc42 standards.*