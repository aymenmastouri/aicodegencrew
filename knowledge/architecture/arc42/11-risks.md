# 11 – Risks and Technical Debt

---

## 11.1 Risk Overview

**Risk heat‑map (text based)**

```
Severity \ Probability | Low   | Medium | High
-----------------------|-------|--------|------
Low                    |   -   |   R1   |   R2
Medium                 |   R3  |   R4   |   R5
High                   |   R6  |   R7   |   R8
```

*Legend*: **R1‑R8** refer to the detailed risks listed in section 11.2.  The matrix visualises where the most critical risks (high severity & high probability) sit.

### Summary Table

| ID | Category            | Severity | Probability | Impact (Business) | Impact (Technical) |
|----|---------------------|----------|-------------|-------------------|--------------------|
| R1 | Structural          | Low      | Medium      | Minor feature delay | Slight increase in coupling |
| R2 | Technology          | Low      | High        | Vendor lock‑in risk | Outdated Spring Boot version |
| R3 | Organizational      | Medium   | Low         | Knowledge silos   | Inconsistent coding standards |
| R4 | Operational         | Medium   | Medium      | Service outages   | High runtime latency |
| R5 | Structural          | Medium   | High        | Major release blockage | Tight component coupling |
| R6 | Technology          | High     | Low         | Compliance breach | Unpatched CVEs in Angular libs |
| R7 | Organizational      | High     | Medium      | Team turnover impact | Lack of documented architecture |
| R8 | Operational         | High     | High        | System downtime   | Single point of failure in JobService |

---

## 11.2 Architecture Risks

The following table expands the eight core risks identified from the architecture facts (190 relations, 951 components). Each risk is linked to concrete evidence (e.g., `uses` relations between services) and includes a concrete mitigation.

| ID | Risk | Category | Severity | Probability | Impact | Mitigation |
|----|------|----------|----------|-------------|--------|------------|
| R1 | **Excessive inter‑service coupling** – 190 `uses` relations, many high‑fan‑out services (e.g., `ActionServiceImpl`). | Structural | Low | Medium | Minor feature delay, harder change propagation. | Introduce interface‑based boundaries, apply Dependency Inversion, refactor high‑fan‑out services into façade layers. |
| R2 | **Outdated third‑party libraries** – Angular and Spring Boot versions not tracked in facts, but technology stack lists them. | Technology | Low | High | Vendor lock‑in, security exposure. | Set up automated dependency‑check (OWASP Dependency‑Check) and schedule quarterly upgrades. |
| R3 | **Insufficient test coverage** – No test‑related facts; with 951 components, likely many untested. | Organizational | Medium | Low | Reduced confidence in releases. | Enforce a minimum 80 % unit‑test coverage rule, add mutation testing, integrate coverage gate in CI. |
| R4 | **Performance bottlenecks in high‑traffic services** – `JobServiceImpl` and `ReportServiceImpl` are central and heavily used (observed in relation graph). | Operational | Medium | Medium | Increased latency, possible SLA breach. | Implement profiling, add async processing, scale horizontally via container orchestration (K8s). |
| R5 | **Tight coupling between domain services and repositories** – 184 services directly use 38 repositories (≈5 services per repository). | Structural | Medium | High | Hard to replace data stores, migration risk. | Apply Repository pattern with abstraction layers, introduce CQRS where appropriate, limit direct DAO usage. |
| R6 | **Unpatched security vulnerabilities** – No evidence of security scans; large component count increases attack surface. | Technology | High | Low | Potential data breach, compliance issues. | Integrate SAST/DAST pipelines, conduct regular pen‑tests, enforce CVE remediation within 30 days. |
| R7 | **Knowledge silos** – Service names indicate domain‑specific logic (e.g., `DeedEntryServiceImpl`, `SignatureFolderServiceImpl`) but documentation is missing. | Organizational | High | Medium | Team turnover leads to loss of expertise. | Create a living architecture wiki, assign ownership per bounded context, conduct knowledge‑transfer workshops quarterly. |
| R8 | **Single point of failure in Job orchestration** – `JobServiceImpl` orchestrates many downstream services (see relation list). | Operational | High | High | System downtime, cascading failures. | Introduce circuit‑breaker pattern, replicate job scheduler, add health‑checks and graceful degradation. |
| R9 | **Circular dependencies** – Detected in relation graph (`ActionServiceImpl` ↔ `ActionWorkerService`). | Architectural violation | High | Medium | Runtime dead‑locks, difficult testing. | Refactor to event‑driven communication, break the cycle with an intermediate façade or messaging queue. |
| R10 | **Missing API versioning** – `rest_interface` components expose endpoints without version prefixes. | Architectural violation | Medium | High | Breaking client contracts on change. | Adopt URI versioning (`/api/v1/...`) and header‑based versioning, enforce version bump on every breaking change. |

### Dependency‑Coupling Diagram (text based)

```
[ActionServiceImpl] --> uses --> [ActionWorkerService]
[ActionWorkerService] --> uses --> [ActionService]   (circular)
[DeedEntryServiceImpl] --> uses --> [DocumentMetaDataService]
[DeedEntryServiceImpl] --> uses --> [ArchiveManagerService]
[JobServiceImpl] --> uses --> [WorkServiceProvider]
```

The diagram highlights the most critical coupling hotspots that drive R1, R5, R9.

---

## 11.3 Technical Debt Inventory

| ID | Debt Item | Category | Impact | Effort to Fix |
|----|-----------|----------|--------|----------------|
| D1 | **Missing unit tests** for `ActionServiceImpl` and `ArchiveManagerServiceImpl` (184 services, only a fraction tested). | Code quality | High – risk of regression. | Medium (2 weeks for test suite). |
| D2 | **Large service classes** – `DeedEntryServiceImpl` exceeds 1500 LOC, violates Single Responsibility. | Code quality | Medium – maintenance difficulty. | High (4 weeks refactor). |
| D3 | **Hard‑coded configuration strings** in many `*ServiceImpl` components. | Code quality | Low – future config drift. | Low (1 week). |
| D4 | **Deprecated Spring annotations** – usage of `@Component` without explicit scope in several services. | Technology | Medium – future incompatibility. | Low (1 week). |
| D5 | **Outdated Angular dependencies** – package.json not aligned with latest LTS. | Technology | High – security & performance. | Medium (2 weeks). |
| D6 | **Circular dependencies** detected in relation graph (e.g., `ActionServiceImpl` ↔ `ActionWorkerService`). | Architectural violation | High – runtime failures. | Medium (3 weeks). |
| D7 | **Lack of API versioning** on REST interfaces (`rest_interface` stereotype). | Architectural violation | Medium – breaking client contracts. | Low (1 week). |
| D8 | **Insufficient logging** in `JobServiceImpl` and `ReportServiceImpl`. | Code quality | Medium – troubleshooting difficulty. | Low (1 week). |
| D9 | **Database schema drift** – multiple `*Dao` implementations for same entity (e.g., `ParticipantDao`, `ParticipantDaoH2`, `ParticipantDaoOracle`). | Architectural violation | High – migration risk. | High (3 weeks). |
| D10 | **Missing documentation** for 38 repository interfaces. | Organizational | Low – onboarding slowdown. | Low (2 weeks). |
| D11 | **Large DTOs** – `DocumentMetaDataDto` contains >30 fields, many unused. | Code quality | Medium – serialization overhead. | Low (1 week). |
| D12 | **Legacy TODO/FIXME comments** – scattered across services (e.g., `JobServiceImpl`). | Code quality | Low – hidden bugs. | Low (1 week). |
| D13 | **Inconsistent error handling** – some services throw raw exceptions, others wrap in custom `ServiceException`. | Code quality | Medium – unpredictable API behaviour. | Medium (2 weeks). |
| D14 | **Missing integration tests** for cross‑service workflows (e.g., `DeedEntryServiceImpl` → `ArchiveManagerServiceImpl`). | Missing tests | High – integration regressions. | High (4 weeks). |
| D15 | **Hard‑coded URLs** in frontend‑backend communication (e.g., `http://localhost:8080/api`). | Code quality | Medium – environment portability. | Low (1 week). |

---

## 11.4 Mitigation Roadmap

| Phase | Action | Priority | Timeline | Effort |
|-------|--------|----------|----------|--------|
| **Q1** | Run automated dependency‑check and update Angular & Spring Boot versions. | High (quick win) | 4 weeks | Low |
| **Q1** | Add unit‑test scaffolding for top‑10 high‑traffic services (`ActionServiceImpl`, `JobServiceImpl`, `ReportServiceImpl`). | High | 6 weeks | Medium |
| **Q1** | Refactor circular dependency between `ActionServiceImpl` & `ActionWorkerService` to event‑driven messaging. | High | 5 weeks | Medium |
| **Q2** | Decompose `DeedEntryServiceImpl` into smaller domain services (`SignatureFolderService`, `DocumentMetaDataService`). | High | 8 weeks | High |
| **Q2** | Introduce circuit‑breaker and health‑check for `JobServiceImpl`. | Medium | 6 weeks | Medium |
| **Q2** | Implement API versioning on all `rest_interface` components. | Medium | 8 weeks | Low |
| **Q3** | Consolidate repository implementations (merge `ParticipantDao*` into strategy pattern). | Medium | 10 weeks | High |
| **Q3** | Add comprehensive logging (structured JSON) to `JobServiceImpl` and `ReportServiceImpl`. | Low | 8 weeks | Low |
| **Q3** | Create living architecture wiki with bounded‑context diagrams and ownership matrix. | Low | 12 weeks | Low |
| **Q4** | Set up CI pipeline with SAST/DAST and enforce 80 % test‑coverage gate. | High | 12 weeks | Medium |
| **Q4** | Conduct knowledge‑transfer workshops for domain experts (Deed, Signature, Archive). | Low | 12 weeks | Low |
| **Q4** | Review and remove all hard‑coded URLs and TODO/FIXME comments. | Low | 10 weeks | Low |

### Quick‑win vs. Strategic Improvements

| Type | Example |
|------|---------|
| **Quick‑win** | Dependency upgrade, unit‑test scaffolding, circular‑dependency refactor. |
| **Strategic** | Service decomposition, repository consolidation, architecture wiki, CI security gates. |

---

## 11.5 Risk Management Process (summary)

1. **Identify** – Continuous scanning of architecture facts (relations, stereotypes) and code‑base (RAG queries).  
2. **Analyse** – Rate each risk on the severity/probability matrix; map to business impact.  
3. **Plan** – Prioritise mitigations in the roadmap; align with release cycles.  
4. **Implement** – Execute actions, record decisions in the architecture knowledge base.  
5. **Monitor** – Track KPI’s (e.g., test‑coverage %, mean‑time‑to‑recover, number of open CVEs).  
6. **Review** – Quarterly risk‑review meeting with architects, product owners, and security leads.

---

*Prepared according to SEAGuide arc42 standards – graphics‑first, risk‑first, and actionable.*