# 01 – Introduction and Goals

## 1.1 Requirements Overview

### System Description & Business Domain
The **uvz** system is a back‑office platform for managing public‑record deeds, archiving, and related legal documentation. It belongs to the **Public Administration / Land Registry** domain and supports the full lifecycle of deed creation, modification, validation, and archival. The platform integrates with external key‑management services, provides fine‑grained access control, and exposes a comprehensive REST API for internal and partner consumption.

### Primary Business Value & Target Users
| Business Value | Target Users |
|----------------|--------------|
| Centralised, auditable deed registry | Registry clerks, notaries, legal officers |
| Automated archiving & compliance reporting | Compliance officers, auditors |
| Secure key‑management for digital signatures | Security officers, cryptographic service providers |
| Real‑time data exchange with partner systems | Integration partners, external portals |
| Scalable processing of high‑volume transactions | Operations managers |

### Feature Inventory (derived from controllers & services)
| # | Business Capability | Primary Provider (Controller / Service) | Brief Description |
|---|----------------------|------------------------------------------|-------------------|
| 1 | Action Management | `ActionRestServiceImpl` / `ActionServiceImpl` | Create, update, and execute system actions (e.g., batch jobs). |
| 2 | Static Content Delivery | `StaticContentController` | Serves UI assets and static HTML pages. |
| 3 | Authentication & Token Management | `TokenAuthenticationRestTemplateConfigurationSpringBoot` | Provides OAuth2 token handling for internal services. |
| 4 | Key Management | `KeyManagerRestServiceImpl` / `KeyManagerServiceImpl` | Generates, stores, and rotates cryptographic keys. |
| 5 | Archiving Operations | `ArchivingRestServiceImpl` / `ArchivingServiceImpl` | Moves completed deeds to long‑term storage and signs archives. |
| 6 | Deed Entry CRUD | `DeedEntryRestServiceImpl` / `DeedEntryServiceImpl` | Full create‑read‑update‑delete lifecycle for deed entries. |
| 7 | Deed Registry Management | `DeedRegistryRestServiceImpl` / `DeedRegistryServiceImpl` | Handles registry metadata and versioning. |
| 8 | Deed Type Catalog | `DeedTypeRestServiceImpl` / `DeedTypeServiceImpl` | Maintains catalogue of deed types and associated rules. |
| 9 | Document Metadata Handling | `DocumentMetaDataRestServiceImpl` / `DocumentMetaDataServiceImpl` | Stores and retrieves metadata for attached documents. |
|10| Handover Data Set Processing | `HandoverDataSetRestServiceImpl` / `HandoverDataSetServiceImpl` | Manages data sets transferred between agencies. |
|11| Reporting & Analytics | `ReportRestServiceImpl` / `ReportServiceImpl` | Generates statutory reports and dashboards. |
|12| Job Scheduling & Execution | `JobRestServiceImpl` / `JobServiceImpl` | Executes background jobs (e.g., re‑encryption, cleanup). |
|13| Number Management | `NumberManagementRestServiceImpl` / `NumberManagementServiceImpl` | Issues and validates unique identifiers for deeds. |
|14| Security & Authorization Customisation | `OpenApiOperationAuthorizationRightCustomizer` | Enforces fine‑grained API rights per operation. |
|15| Exception Handling & API Consistency | `DefaultExceptionHandler` | Centralised error mapping to REST responses. |
|16| Notary Representation | `NotaryRepresentationRestServiceImpl` | Manages notary signatures and representation data. |
|17| Official Activity Metadata | `OfficialActivityMetadataRestServiceImpl` | Stores activity logs required for legal compliance. |
|18| Report Metadata Management | `ReportMetadataRestServiceImpl` | Handles metadata for generated reports. |
|19| Health Check & Monitoring | `HealthCheck` | Provides liveness and readiness endpoints. |
|20| Mock KM Service (Testing) | `MockKmService` | Simulated key‑management for test environments. |

*The list reflects the most relevant capabilities; the full code base contains 32 controllers and 184 services that collectively support the above functions.*

### System Statistics
| Metric | Value |
|--------|-------|
| Total Components | 951 |
| Controllers | 32 |
| Services | 184 |
| Repositories | 38 |
| Entities (Domain Model) | 360 |
| REST Endpoints (HTTP methods) | 196 (GET 128, POST 30, PUT 18, DELETE 14, PATCH 6) |
| Interfaces (incl. routes) | 226 |
| Relations (uses, manages, imports, references) | 190 |

## 1.2 Quality Goals

| # | Quality Goal | Priority | Rationale | Realisation Pattern(s) | Measurement |
|---|--------------|----------|-----------|------------------------|-------------|
| 1 | **Maintainability** | High | Frequent regulatory updates require quick code changes. | Layered Architecture, Hexagonal Ports, Feature‑Toggle pattern. | Mean Time to Change (MTTC) ≤ 2 days; Cyclomatic complexity ≤ 10 for 80 % of classes. |
| 2 | **Testability** | High | Automated regression testing is mandatory for compliance. | Test‑Driven Development, In‑Memory Repositories, Mock KM Service. | Unit test coverage ≥ 80 %; Integration test pass rate ≥ 95 %. |
| 3 | **Security** | Critical | Sensitive personal data and digital signatures are processed. | Spring Security, Method‑level Authorization, OpenAPI Operation Rights Customizer. | No critical OWASP‑Top‑10 findings; Pen‑test vulnerability score ≤ 3. |
| 4 | **Performance** | Medium | High transaction volume during peak filing periods. | Asynchronous Job Scheduling, Caching (Spring Cache), Bulk‑Insert optimisation. | 95 % of API calls ≤ 200 ms; Batch job throughput ≥ 10 k records/min. |
| 5 | **Scalability** | Medium | System must handle growth of registry entries and partner integrations. | Horizontal scaling via containerised services, Stateless REST interfaces, Load‑balancer pattern. | Linear performance up to 5× current load; No degradation > 5 % under load test. |

## 1.3 Stakeholders

| # | Role | Concern(s) | Expectations | Primary Interaction with System |
|---|------|-----------|-------------|--------------------------------|
| 1 | **Product Owner** | Alignment with legislative requirements, roadmap prioritisation | Clear feature backlog, measurable ROI | Reviews functional specifications, approves releases |
| 2 | **Registry Clerk / End User** | Usability, data accuracy, fast response | Intuitive UI, minimal errors, quick transaction processing | Uses UI (served by `StaticContentController`) and REST APIs for deed entry |
| 3 | **Compliance Officer** | Auditability, data retention, legal conformity | Full audit trail, immutable archives | Consumes reporting endpoints (`ReportRestServiceImpl`) and archival logs |
| 4 | **Security Officer** | Confidentiality, integrity, access control | Zero‑trust authentication, role‑based authorisation | Reviews security configuration, token handling, OpenAPI customizer |
| 5 | **DevOps Engineer** | Deployability, observability, resilience | Automated CI/CD, health checks, scaling | Interacts with health endpoint, container orchestration, job scheduling |
| 6 | **Integration Partner** (e.g., municipal portal) | API stability, versioning, data contracts | Stable OpenAPI spec, backward compatibility | Calls REST services (`DeedEntryRestServiceImpl`, `NumberManagementServiceImpl`) |
| 7 | **Business Analyst** | Requirement traceability, impact analysis | Traceability matrix, clear documentation | Works with feature inventory and stakeholder tables |
| 8 | **System Administrator** | Operational uptime, backup/restore | Monitoring dashboards, disaster‑recovery procedures | Manages infrastructure, configuration (`ProxyRestTemplateConfiguration`) |

*Stakeholder concerns drive the quality goals defined above and are reflected throughout the architecture.*
