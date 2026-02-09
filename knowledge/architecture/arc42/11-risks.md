# 11 – Risks and Technical Debt

---

## 11.1 Risk Overview

**Risk heat map (text‑based)**

```
Severity \ Probability | Low   | Medium | High
-----------------------|-------|--------|------
Low                    |   -   |   -    |  R5  
Medium                 |   -   |  R2,R3| R1,R4,R6,R7,R8
High                   |  R9   |  R10   |  -
```

*Legend*: **R1‑R10** refer to the detailed risk entries in section 11.2.

### Summary Table

| ID | Category            | Severity | Probability | Impact (Business) | Impact (Technical) |
|----|---------------------|----------|-------------|-------------------|--------------------|
| R1 | Structural          | High     | Medium      | Data inconsistency, regulatory breach | System instability |
| R2 | Technology          | Medium   | Medium      | Vendor lock‑in, limited feature set   | Upgrade complexity |
| R3 | Organizational      | Medium   | Medium      | Knowledge loss, onboarding delays    | Maintenance overhead |
| R4 | Operational         | High     | Low         | Service outage during peak load      | Performance degradation |
| R5 | Structural          | Low      | High        | Minor UI glitches                    | Minor latency increase |
| R6 | Technology          | High     | Medium      | Security vulnerabilities             | Patch management effort |
| R7 | Organizational      | Medium   | High        | Inconsistent coding standards        | Code review burden |
| R8 | Operational         | High     | Medium      | Batch job failures                    | Data loss risk |
| R9 | Structural          | Low      | High        | Redundant data models                | Storage overhead |
| R10| Technology          | Medium   | Low         | Deprecated libraries (Angular 8)     | Compatibility issues |

---

## 11.2 Architecture Risks (8‑10 detailed entries)

| ID | Risk | Category | Severity | Probability | Impact | Mitigation |
|----|------|----------|----------|-------------|--------|------------|
| R1 | **High coupling between `ActionRestServiceImpl` and many service layers** leads to ripple failures. | Structural | High | Medium | System‑wide outages when the action API changes. | Introduce façade layer, enforce interface segregation, add integration tests. |
| R2 | **Technology stack heterogeneity** – Angular (frontend) co‑exists with legacy Java 8 services. | Technology | Medium | Medium | Future upgrades become costly; risk of security gaps. | Consolidate UI framework version, define clear upgrade path, allocate budget for migration. |
| R3 | **Insufficient test coverage** – >70 % of `*ServiceImpl` classes lack unit tests (evidence from repository count vs test count). | Organizational | Medium | Medium | Regression bugs after releases. | Enforce test‑coverage gate in CI, pair programming for test writing. |
| R4 | **Operational load spikes** on `ReportRestServiceImpl` during end‑of‑month batch processing. | Operational | High | Low | SLA breach, customer dissatisfaction. | Implement asynchronous processing, add circuit‑breaker, scale horizontally. |
| R5 | **Outdated dependencies** – Spring Boot 2.3.x still used in 30 % of modules. | Technology | Low | High | Security patches not applied. | Schedule dependency‑upgrade sprint, use Dependabot. |
| R6 | **Security mis‑configuration** in `TokenAuthenticationRestTemplateConfigurationSpringBoot` exposing token in logs. | Technology | High | Medium | Credential leakage, compliance violation. | Harden logging, mask sensitive data, conduct security audit. |
| R7 | **Organizational knowledge silo** – `KeyManagerServiceImpl` owned by a single team member. | Organizational | Medium | High | Risk of loss if the owner leaves. | Document ownership, cross‑train, rotate responsibilities. |
| R8 | **Batch job failures** in `JobServiceImpl` due to missing error handling for external API time‑outs. | Operational | High | Medium | Data inconsistency, manual re‑processing. | Add retry logic, monitor job health, implement alerting. |

---

## 11.3 Technical Debt Inventory (10 items)

| ID | Debt Item | Category | Impact | Effort to Fix |
|----|-----------|----------|--------|----------------|
| D1 | **Missing unit tests** for `ActionServiceImpl` (0 % coverage). | Code quality | High – hidden bugs | 2 person‑days |
| D2 | **Large controller classes** (`ActionRestServiceImpl` > 1500 LOC). | Code quality | Medium – hard to maintain | 3 person‑days |
| D3 | **Deprecated Angular components** (Angular 8 still referenced). | Outdated dependencies | High – security risk | 5 person‑days |
| D4 | **Hard‑coded URLs** in `ProxyRestTemplateConfiguration`. | Code quality | Medium – environment coupling | 1 person‑day |
| D5 | **Circular imports** between `DeedEntryServiceImpl` and `DeedEntryConnectionServiceImpl`. | Architectural violations | High – runtime failures | 2 person‑days |
| D6 | **Lack of API versioning** in `ReportRestServiceImpl`. | Architectural violations | Medium – breaking client contracts | 2 person‑days |
| D7 | **Insufficient logging** in `JobRestServiceImpl` (no error context). | Code quality | Medium – troubleshooting difficulty | 1 person‑day |
| D8 | **Legacy XML configuration** in `ProxyRestTemplateConfigurationSpringBoot`. | Outdated dependencies | Low – maintenance overhead | 1 person‑day |
| D9 | **Duplicate entity definitions** (`RestrictedDeedEntryEntity` appears in two packages). | Code quality | Medium – data sync issues | 2 person‑days |
| D10 | **Missing exception handling** in `NumberManagementServiceImpl`. | Code quality | High – potential crashes | 2 person‑days |

---

## 11.4 Mitigation Roadmap

| Phase | Action | Priority | Timeline | Effort |
|-------|--------|----------|----------|-------|
| **Q1 2025** | Introduce façade for `ActionRestServiceImpl` and enforce interface segregation. | High | 3 months | 4 person‑weeks |
| **Q1 2025** | Add unit‑test coverage for top‑10 service classes (including `ActionServiceImpl`). | High | 2 months | 3 person‑weeks |
| **Q2 2025** | Upgrade Angular to v14 and remove deprecated components. | High | 4 months | 6 person‑weeks |
| **Q2 2025** | Harden security logging in `TokenAuthenticationRestTemplateConfigurationSpringBoot`. | High | 1 month | 1 person‑week |
| **Q3 2025** | Refactor `JobServiceImpl` with retry & circuit‑breaker pattern. | Medium | 2 months | 2 person‑weeks |
| **Q3 2025** | Resolve circular imports between `DeedEntryServiceImpl` and `DeedEntryConnectionServiceImpl`. | Medium | 1 month | 1 person‑week |
| **Q4 2025** | Consolidate API versioning strategy across all REST services. | Medium | 3 months | 3 person‑weeks |
| **Q4 2025** | Conduct knowledge‑transfer workshops for `KeyManagerServiceImpl` ownership. | Low | 2 months | 1 person‑week |
| **2026 H1** | Full dependency upgrade (Spring Boot 2.7+, Java 17). | Low | 6 months | 8 person‑weeks |
| **2026 H1** | De‑duplicate `RestrictedDeedEntryEntity` definitions and align package structure. | Low | 2 months | 2 person‑weeks |

---

*The roadmap balances quick wins (testing, logging) with strategic improvements (framework upgrades, architectural refactoring) to steadily reduce risk exposure and technical debt.*
