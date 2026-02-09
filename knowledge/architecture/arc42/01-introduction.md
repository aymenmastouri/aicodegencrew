# 01 – Introduction and Goals

---

## 1.1 Requirements Overview

### System Description
The **UVZ** platform is a domain‑centric, end‑to‑end solution for the public‑notary and land‑registry domain. It orchestrates the complete lifecycle of deed entries – from creation, validation, signing, hand‑over, archiving, to reporting – while guaranteeing legal compliance, data integrity, and auditability. The architecture follows a classic **Layered** style (presentation, application, domain, data‑access, infrastructure) and embraces **Domain‑Driven Design (DDD)** with clearly bounded contexts:

| Bounded Context | Core Responsibility |
|-----------------|----------------------|
| **Deed Management** | CRUD of deed entries, connection handling, logging, and state transitions |
| **Archiving** | Token‑based signing, document preservation, failure handling |
| **Key Management** | Cryptographic key lifecycle, re‑encryption, state queries |
| **Reporting & Analytics** | Generation of statutory reports, statistical dashboards |
| **Number Management** | Validation and formatting of official numbers |
| **Security & Authorization** | Role‑based access control, JWT handling, custom security expressions |

The system is built with **Spring Boot (Java/Gradle)** on the backend and **Angular** on the frontend. It is containerised (Docker/Kubernetes) and integrates with external services via REST and OpenAPI contracts.

### Business Domain Classification
- **Domain**: Public‑notary & land‑registry services (legal‑tech)
- **Primary Business Value**: Secure, auditable, and traceable handling of deeds and related documents, enabling statutory compliance and reducing manual processing time.
- **Target Users**:
  - Notary officials (core users)
  - Registry clerks (batch operators)
  - Auditors & compliance officers (reviewers)
  - External partners (banks, land‑registry offices)
  - System administrators & DevOps teams

### Feature Inventory (derived from controllers & services)
| # | Business Capability | Representative Component(s) |
|---|----------------------|-----------------------------|
| 1 | Action processing (create, query) | `ActionRestServiceImpl`, `ActionServiceImpl` |
| 2 | Static content delivery | `StaticContentController` |
| 3 | JSON‑based authorization | `JsonAuthorizationRestServiceImpl` |
| 4 | Key‑manager re‑encryption | `KeyManagerRestServiceImpl`, `KeyManagerServiceImpl` |
| 5 | Archiving token signing | `ArchivingRestServiceImpl`, `ArchivingServiceImpl` |
| 6 | Business purpose catalogue | `BusinessPurposeRestServiceImpl`, `BusinessPurposeServiceImpl` |
| 7 | Deed entry CRUD & lifecycle | `DeedEntryRestServiceImpl`, `DeedEntryServiceImpl` |
| 8 | Deed connection handling | `DeedEntryConnectionRestServiceImpl`, `DeedEntryConnectionServiceImpl` |
| 9 | Deed log management | `DeedEntryLogRestServiceImpl`, `DeedEntryLogServiceImpl` |
|10 | Deed registry operations | `DeedRegistryRestServiceImpl`, `DeedRegistryServiceImpl` |
|11 | Deed type catalogue | `DeedTypeRestServiceImpl`, `DeedTypeServiceImpl` |
|12 | Document metadata handling | `DocumentMetaDataRestServiceImpl`, `DocumentMetaDataServiceImpl` |
|13 | Handover data‑set processing | `HandoverDataSetRestServiceImpl`, `HandoverDataSetServiceImpl` |
|14 | Reporting services | `ReportRestServiceImpl`, `ReportServiceImpl` |
|15 | Job & retry management | `JobRestServiceImpl`, `JobServiceImpl` |
|16 | Number management (format/validation) | `NumberManagementRestServiceImpl`, `NumberManagementServiceImpl` |
|17 | Official activity metadata | `OfficialActivityMetadataRestServiceImpl` |
|18 | Notary representation handling | `NotaryRepresentationRestServiceImpl` |
|19 | OpenAPI configuration & security customisation | `OpenApiConfig`, `OpenApiOperationAuthorizationRightCustomizer` |
|20 | Global exception handling | `DefaultExceptionHandler` |
|21 | Scheduler & background jobs | `ReencryptionJobRestServiceImpl` |
|22 | Health‑check endpoint | `HealthCheck` |
|23 | Resource factory utilities | `ResourceFactory` |
|24 | Security expression handling | `CustomMethodSecurityExpressionHandler` |
|25 | Proxy RestTemplate configuration | `ProxyRestTemplateConfiguration` |
|26 | Token authentication configuration | `TokenAuthenticationRestTemplateConfigurationSpringBoot` |
|27 | Index HTML resource service | `IndexHTMLResourceService` |
|28 | Miscellaneous utilities (guards, interceptors) | `Guard`, `Interceptor` |
|29 | Batch capture of deed entries | `BulkCaptureServiceImpl` (derived from batch endpoints) |
|30 | Document status & archiving workflow | `DocumentStatusServiceImpl` (derived from document endpoints) |

*The table lists **all** high‑level business capabilities identified from the 32 controllers and 184 services.*

### System Statistics (snapshot from architecture facts)
| Metric | Value |
|--------|-------|
| Total components (all layers) | 951 |
| Controllers (REST) | 32 |
| Services (application layer) | 184 |
| Repositories (data‑access) | 38 |
| Entities (domain model) | 360 |
| REST endpoints (HTTP) | 196 |
| Interfaces (incl. routes & guards) | 226 |
| Relations (uses / manages) | 190 |
| Containers (deployment units) | 5 |
| Modules (Angular) | 16 |
| Pipes (Angular) | 67 |
| Directives (Angular) | 3 |
| Adapters (integration) | 50 |
| Schedulers | 1 |

### High‑Level Context Diagram (textual representation)
```
[External Partners] <--HTTPS--> [UVZ API Gateway] <--REST--> [UVZ Backend Services]
    ^                                         |
    |                                         v
[Angular Front‑end] <--WebSocket/REST--> [Presentation Layer]
```
*The diagram is intentionally minimal – the visual version will be placed in the final PDF.*

### Key Business Scenarios (illustrative)
1. **Create Deed Entry** – Notary fills a form → backend validates → cryptographic signature is generated → entry stored and logged.
2. **Batch Capture** – Registry clerk uploads CSV → service validates each record, creates deeds, triggers asynchronous archiving jobs.
3. **Re‑encryption** – Security policy change triggers re‑encryption job → key‑manager re‑encrypts stored documents, updates state.
4. **Report Generation** – Auditor requests annual report → reporting service aggregates data, produces PDF, signs with audit key.
5. **Handover Process** – Document hand‑over to external partner → handover data‑set service prepares package, logs handover, notifies partner.

---

## 1.2 Quality Goals

| # | Quality Goal | Priority | Rationale | Realisation Pattern(s) | Measurement |
|---|--------------|----------|-----------|------------------------|------------|
| 1 | **Maintainability** | High | Regulatory changes require rapid adaptation of business rules. | Layered Architecture, Modularisation, Spring DI, Angular feature modules | Mean Time to Change (MTTC) ≤ 2 days for non‑critical features; Code churn < 5 % per release |
| 2 | **Testability** | High | Legal processes must be verifiable automatically. | Service‑layer unit tests, Mock‑based integration tests, Contract testing (OpenAPI), Testcontainers for DB | Unit test coverage ≥ 80 %; Integration test pass rate ≥ 95 % |
| 3 | **Security** | Critical | Handling of personal/property data mandates confidentiality, integrity, and non‑repudiation. | Zero‑Trust API gateway, Spring Security with method‑level annotations, OAuth2/JWT, OpenAPI security extensions, Custom security expressions | OWASP Top‑10 compliance; No critical CVSS ≥ 7 findings in quarterly scans |
| 4 | **Performance** | Medium | High‑volume batch imports and real‑time signing must meet SLA. | Asynchronous job processing, Spring Cache, Reactive endpoints where applicable, HTTP/2 | 95 % of API calls ≤ 200 ms; Batch import ≤ 5 min for 10 k records |
| 5 | **Scalability** | Medium | System must support nationwide notary workload growth. | Stateless REST services, Horizontal scaling (Kubernetes), Database sharding/partitioning, Load‑balanced API gateway | Linear throughput increase up to 10× load; No > 5 % latency degradation under peak load |

### Quality Scenarios (selected)
- **Scenario 1 – Rapid Feature Toggle**: A new legal clause is added. Developers modify the corresponding service, run unit tests, and deploy without downtime (MTTC ≤ 2 days).
- **Scenario 2 – Security Breach Simulation**: Red‑team attempts to access `/uvz/v1/deedentries/**` without a valid JWT. Access is denied, logged, and an alert is raised (OWASP compliance).
- **Scenario 3 – Load Spike**: During end‑of‑year reporting, request rate spikes to 500 req/s. Autoscaling adds pods, latency stays < 250 ms (scalability).

---

## 1.3 Stakeholders

| # | Role | Concern(s) | Expectations | Primary Interaction Points |
|---|------|------------|--------------|---------------------------|
| 1 | **Notary Official** | Data integrity, auditability, ease of use | Accurate deed entry, quick signature workflow, minimal UI friction | Angular UI, `/uvz/v1/deedentries/**` REST APIs |
| 2 | **Registry Clerk** | Bulk processing, reporting | Efficient batch capture, reliable export of reports | Batch endpoints (`/uvz/v1/deedentries/bulkcapture`), reporting APIs |
| 3 | **Auditor / Compliance Officer** | Traceability, security logs | Full audit trail, immutable logs, easy query of historic data | `DeedEntryLogRestServiceImpl`, `/logger` endpoint |
| 4 | **System Administrator** | Deployment, monitoring, uptime | Stable containers, health checks, easy rollback, observability | Health‑check (`/actuator/health`), Kubernetes manifests, `HealthCheck` service |
| 5 | **Security Engineer** | Threat modelling, access control | Zero‑trust, role‑based permissions, vulnerability management | Spring Security config, OpenAPI security definitions, `/oauth2/**` |
| 6 | **External Partner (e.g., Bank)** | API reliability, data exchange | Stable, documented REST contracts, SLA adherence | Public OpenAPI (`/v3/api-docs`), OAuth2 token endpoint |
| 7 | **Product Owner** | Feature delivery, ROI | Prioritised backlog, measurable business value, stakeholder alignment | Feature inventory table, roadmap meetings |
| 8 | **Developer / Maintainer** | Code quality, testability | Clear module boundaries, automated tests, CI/CD pipelines | Source repository, CI pipelines, unit test coverage reports |

*All stakeholder concerns are addressed through the architectural decisions documented in later chapters (runtime, deployment, and cross‑cutting concerns).* 

---

*The next chapters will detail the runtime view, deployment view, cross‑cutting concepts, and decision log.*
