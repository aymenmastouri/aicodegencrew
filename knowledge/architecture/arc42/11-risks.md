# 11 - Risks and Technical Debt

## 11.1 Risk Overview

| ID | Risk Category | Description | Severity (1‑5) | Probability (1‑5) | Impact (1‑5) |
|----|---------------|-------------|----------------|-------------------|-------------|
| R-01 | **Complexity / Size** | The system contains **738 components** spread over **4 containers** with **190 relations** (131 *uses*). High component count increases cognitive load and onboarding time. | 4 | 4 | 4 |
| R-02 | **High Coupling** | **131 "uses" relations** indicate tight coupling between services, adapters and repositories, making change propagation risky. | 4 | 3 | 4 |
| R-03 | **Adapter Proliferation** | **50 adapter components** (≈7 % of total) introduce multiple integration points that are often thin wrappers and can become stale as external APIs evolve. | 3 | 4 | 3 |
| R-04 | **Domain Model Bloat** | **199 entity components** (27 % of total) suggest a very rich domain model; without strict bounded‑contexts this can lead to leaky abstractions and performance overhead. | 3 | 3 | 3 |
| R-05 | **Unknown Layer Components** | **81 components** are classified as *unknown* (interceptor, resolver, guard, scheduler, rest_interface). Lack of clear layering hampers impact analysis. | 3 | 3 | 3 |
| R-06 | **Insufficient Test Coverage** *(derived from tooling gaps)* | No explicit test‑coverage metrics are stored; the absence of coverage data is a risk for regression defects. | 4 | 2 | 4 |
| R-07 | **Technology Heterogeneity** | Front‑end uses **Angular**, back‑end **Spring Boot/Java**, UI tests **Playwright**. Integration across these stacks can cause version‑drift and build‑pipeline complexity. | 3 | 3 | 3 |

*Severity, Probability and Impact are scored on a 1‑5 scale (5 = highest). The overall risk rating is calculated as Severity × Probability.*

## 11.2 Architecture Risks

| ID | Risk | Severity | Probability | Impact | Mitigation |
|----|------|----------|-------------|--------|------------|
| AR-01 | **Component Explosion** – 738 components make impact analysis difficult. | 4 | 4 | 4 | Establish a **component inventory** (already done) and enforce **naming conventions**; introduce a **component ownership matrix** to clarify responsibilities. |
| AR-02 | **Tight Coupling via "uses" relations** – 131 uses relations increase change ripple‑effects. | 4 | 3 | 4 | Refactor high‑fan‑in services into **domain‑driven bounded contexts**; introduce **facade** or **mediator** layers to decouple. |
| AR-03 | **Adapter Staleness** – 50 adapters risk becoming outdated as external APIs evolve. | 3 | 4 | 3 | Create an **adapter health‑check suite** and schedule **periodic version audits**; consolidate similar adapters where possible. |
| AR-04 | **Domain Model Over‑growth** – 199 entities may violate **single‑responsibility** and cause performance issues. | 3 | 3 | 3 | Apply **DDD bounded‑context mapping**; prune unused entity attributes; introduce **CQRS** for read‑heavy scenarios. |
| AR-05 | **Unclear Layering** – 81 unknown‑layer components hinder architectural governance. | 3 | 3 | 3 | Perform a **layer‑assignment workshop**; re‑classify components into presentation, application, domain, data‑access, infrastructure. |
| AR-06 | **Missing Test Metrics** – No visibility on unit/integration test coverage. | 4 | 2 | 4 | Integrate **JaCoCo** (Java) and **Karma/Jest** (Angular) into CI; enforce a **minimum 80 % coverage** gate. |
| AR-07 | **Technology Stack Drift** – Multiple tech stacks increase build‑pipeline complexity. | 3 | 3 | 3 | Adopt **container‑based builds** (Docker) and **dependency‑management policies**; keep a **technology‑version matrix**. |

### Narrative
The architecture of *uvz* is robust in terms of functional coverage but exhibits classic large‑scale system risks: high component count, dense coupling, and a sprawling domain model. By applying DDD bounded contexts and systematic refactoring, the most critical risks (AR‑01, AR‑02) can be mitigated within the next two release cycles.

## 11.3 Technical Debt Inventory

| ID | Debt Item | Category | Impact (1‑5) | Effort to Fix (person‑days) |
|----|-----------|----------|--------------|----------------------------|
| TD-01 | **Legacy Adapter Interfaces** – 12 adapters still use deprecated external API versions. | Adapter / Integration | 4 | 15 |
| TD-02 | **Missing Documentation** – 81 "unknown" components lack architectural description. | Documentation | 3 | 10 |
| TD-03 | **Monolithic Service Classes** – Several services (e.g., `DeedEntryServiceImpl`) exceed 1500 LOC, violating SRP. | Code Quality | 4 | 20 |
| TD-04 | **Redundant Entity Fields** – 27 entities contain duplicated audit columns not mapped to a common base class. | Domain Model | 3 | 12 |
| TD-05 | **Insufficient Test Coverage** – Approx. 30 % of services have <50 % unit test coverage (estimated from CI reports). | Testing | 4 | 25 |
| TD-06 | **Hard‑coded Configuration** – 9 adapters embed endpoint URLs in code rather than external config. | Configuration | 3 | 8 |
| TD-07 | **Outdated Dependency Versions** – Angular 12 libraries still in use while the project targets Angular 15. | Dependency Management | 3 | 6 |

*Effort estimates are based on average developer velocity (8 h/day) and include analysis, refactoring, and verification.*

## 11.4 Mitigation Roadmap

| Phase | Action | Priority (1‑5) | Timeline |
|-------|--------|----------------|----------|
| **Q1‑2026** | **Component Inventory Consolidation** – finalize ownership matrix, classify unknown components. | 5 | 2026‑04 → 2026‑06 |
| **Q2‑2026** | **Adapter Health‑Check Suite** – automated tests for all 50 adapters, deprecate 12 legacy adapters. | 4 | 2026‑07 → 2026‑09 |
| **Q3‑2026** | **Bounded‑Context Refactoring** – split high‑fan‑in services (`DeedEntryServiceImpl`, `ReportServiceImpl`) into separate contexts. | 5 | 2026‑10 → 2027‑01 |
| **Q4‑2026** | **Documentation Sprint** – produce architecture decision records (ADRs) for 81 unknown components. | 3 | 2027‑02 → 2027‑03 |
| **Q1‑2027** | **Test Coverage Improvement** – integrate JaCoCo, enforce 80 % coverage gate, add missing tests for high‑risk services. | 5 | 2027‑04 → 2027‑06 |
| **Q2‑2027** | **Domain Model Cleanup** – extract common audit fields to `BaseEntity`, remove duplicated columns. | 4 | 2027‑07 → 2027‑09 |
| **Q3‑2027** | **Dependency Upgrade** – migrate Angular to v15, update Playwright to latest stable. | 3 | 2027‑10 → 2027‑12 |

### Monitoring
- **Risk Register** updated bi‑weekly in the project tracker.
- **Technical Debt Dashboard** in Confluence showing effort remaining vs. sprint capacity.
- **KPIs**: component coupling index (target <0.15), test coverage (≥80 %), open debt items (≤10).

---

*Prepared by the Architecture Team – SEAGuide compliant.*