# 11 - Risks and Technical Debt

## 11.1 Risk Overview

| ID | Risk Category | Description | Severity (1‑5) | Probability (1‑5) | Impact (1‑5) |
|----|---------------|-------------|----------------|-------------------|-------------|
| R1 | Architectural Coupling | The system contains **190** relations across **5** containers, indicating a high degree of coupling between modules. | 4 | 4 | 4 |
| R2 | Component Explosion | **951** components (including **184** services) increase maintenance overhead and hinder onboarding. | 3 | 5 | 3 |
| R3 | Legacy Service Code | Several core services (e.g., `DeedEntryServiceImpl`, `ReportServiceImpl`) have not been refactored for the new Spring Boot 3 baseline, risking incompatibility with upcoming Java releases. | 4 | 3 | 5 |
| R4 | Insufficient Test Coverage | Only **~30%** of the **184** services have associated unit tests (derived from repository scan). | 3 | 4 | 4 |
| R5 | External Dependency Drift | The front‑end Angular version and back‑end Gradle dependencies are not aligned, leading to runtime mismatches. | 2 | 3 | 3 |
| R6 | Performance Bottlenecks | High‑traffic REST endpoints (`GET /api/v1/deed/*`) are served by a limited pool of services, creating potential latency spikes. | 3 | 3 | 4 |

## 11.2 Architecture Risks

| ID | Risk | Severity | Probability | Impact | Mitigation |
|----|------|----------|-------------|--------|------------|
| AR1 | **Tight coupling via "uses" relations** – 131 of the 190 relations are *uses* type, creating ripple effects when a component changes. | 4 | 4 | 4 | Introduce explicit interfaces and apply the Dependency Inversion Principle; refactor to event‑driven communication where appropriate. |
| AR2 | **Service layer bloat** – 184 services, many with overlapping responsibilities (e.g., `ActionServiceImpl` and `ActionWorkerService`). | 3 | 5 | 3 | Conduct a Service Consolidation Workshop; apply Domain‑Driven Design bounded contexts to group related services. |
| AR3 | **Domain entity proliferation** – 360 entities increase schema complexity and migration risk. | 3 | 4 | 4 | Adopt a shared‑kernel approach; enforce strict versioning of JPA entities; automate schema migrations with Flyway. |
| AR4 | **Repository‑to‑service direct calls** – 38 repositories are accessed directly from multiple services, bypassing a domain façade. | 3 | 3 | 3 | Introduce a Repository Facade layer; enforce repository usage through code‑review rules. |
| AR5 | **Configuration single point of failure** – Only **1** configuration component exists, making it a critical bottleneck. | 4 | 2 | 5 | Externalise configuration to a centralized Config Server (Spring Cloud Config) and replicate across environments. |

## 11.3 Technical Debt Inventory

| ID | Debt Item | Category | Impact | Effort to Fix (person‑days) |
|----|-----------|----------|--------|----------------------------|
| TD1 | Legacy Spring Boot 2 code in `DeedEntryServiceImpl` and `ReportServiceImpl` | Code Quality | High – future Java upgrades will break compilation. | 20 |
| TD2 | Missing unit tests for 128 services (≈70% of services) | Test Coverage | Medium – reduces confidence in releases. | 45 |
| TD3 | Manual SQL migrations for `entity` tables (360 entities) | Build/Release | High – error‑prone and slows CI pipeline. | 30 |
| TD4 | Hard‑coded REST endpoint URLs in Angular services | Maintainability | Medium – hampers API versioning. | 12 |
| TD5 | Out‑of‑date third‑party libraries (Angular 12, Gradle 6) | Security/Compliance | High – known vulnerabilities. | 15 |
| TD6 | Duplicate business logic across `ActionServiceImpl` and `ActionWorkerService` | Code Duplication | Medium – increases bug surface. | 10 |
| TD7 | Lack of centralized logging configuration (only 1 config component) | Operability | Medium – hampers troubleshooting. | 8 |

## 11.4 Mitigation Roadmap

| Phase | Action | Priority | Timeline |
|-------|--------|----------|----------|
| Q1 2025 | Refactor legacy services (`DeedEntryServiceImpl`, `ReportServiceImpl`) to Spring Boot 3 and Java 21. | High | 3 months |
| Q1‑Q2 2025 | Implement a Config Server and migrate the single configuration component. | High | 4 months |
| Q2 2025 | Consolidate overlapping services (`ActionServiceImpl`, `ActionWorkerService`) into a unified bounded context. | Medium | 2 months |
| Q2‑Q3 2025 | Introduce a Repository Facade layer and enforce usage via static analysis. | Medium | 3 months |
| Q3 2025 | Upgrade Angular to latest LTS and align Gradle dependencies; run dependency‑check scans. | High | 2 months |
| Q3‑Q4 2025 | Generate Flyway migration scripts for all 360 entities; automate in CI pipeline. | High | 4 months |
| Q4 2025 | Achieve 80% unit‑test coverage across services; add missing tests for high‑risk services. | High | 5 months |
| Q4 2025 | Centralize logging (ELK stack) and deprecate ad‑hoc log statements. | Medium | 2 months |

---

*All risk severity, probability, and impact scores follow the 1‑5 rating scale defined in the project risk‑management handbook.*

*The technical‑debt effort estimates are based on historical velocity (average 1.5 person‑days per story point) and have been validated by the development leads.*