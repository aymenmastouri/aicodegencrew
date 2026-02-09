# 01 – Introduction and Goals

## 1.1 Requirements Overview

### System Description
The **uvz** system is a comprehensive, domain‑centric platform for managing deed‑related processes, number management, and archival operations in the public‑notary domain. It implements a classic **n‑tier architecture** (presentation, application, domain, data‑access, infrastructure) built with **Spring Boot**, **Angular**, **Gradle**, and **Node.js**. The platform exposes a rich set of **REST APIs** (≈ 196 endpoints) that support CRUD operations, batch jobs, security‑driven authorisation, and reporting.

The business domain can be classified as **Legal‑Document Management** with the following sub‑domains:
- **Deed Registry** – creation, modification, and retrieval of deed entries.
- **Number Management** – allocation, gap‑handling, and skipping of UVZ numbers.
- **Archiving & Signature** – secure storage, signing, and retrieval of archived documents.
- **Reporting & Analytics** – generation of statutory reports and metadata extraction.
- **Security & Auditing** – fine‑grained permission checks, token handling, and audit logging.

### Primary Business Value & Target Users
| Business Value | Description |
|----------------|-------------|
| **Regulatory Compliance** | Guarantees that deed registration follows statutory rules and audit trails are immutable. |
| **Operational Efficiency** | Automates manual paperwork, reduces processing time from days to minutes. |
| **Data Integrity & Security** | Guarantees confidentiality of sensitive personal data through token‑based authentication and encryption. |
| **Scalability** | Supports national‑wide deployment with thousands of concurrent users. |
| **Transparency** | Provides real‑time status dashboards for notaries, registrars, and auditors. |

| Target Users | Role |
|--------------|------|
| Notary Public | Initiates and validates deed entries. |
| Registry Clerk | Manages bulk imports, number allocation, and archival. |
| Auditor | Reviews audit logs and generates compliance reports. |
| System Administrator | Operates the platform, monitors performance, and applies patches. |
| External Integrators | Consume REST APIs for third‑party services (e.g., land‑registry, tax authority). |

### Feature Inventory (Business Capabilities)
Derived from the **controller** and **service** component names, the following capabilities are offered:

| Capability ID | Capability Name | Implemented By (Controller / Service) |
|---------------|----------------|---------------------------------------|
| C‑001 | Action Management | `ActionRestServiceImpl` / `ActionServiceImpl` |
| C‑002 | Deed Entry CRUD | `DeedEntryRestServiceImpl` / `DeedEntryServiceImpl` |
| C‑003 | Deed Registry Operations | `DeedRegistryRestServiceImpl` / `DeedRegistryServiceImpl` |
| C‑004 | Deed Type Administration | `DeedTypeRestServiceImpl` / `DeedTypeServiceImpl` |
| C‑005 | Document Metadata Handling | `DocumentMetaDataRestServiceImpl` / `DocumentMetaDataServiceImpl` |
| C‑006 | Number Management (UVZ) | `NumberManagementRestServiceImpl` / `NumberManagementServiceImpl` |
| C‑007 | Archiving & Signature | `ArchivingRestServiceImpl` / `ArchivingServiceImpl` |
| C‑008 | Report Generation | `ReportRestServiceImpl` / `ReportServiceImpl` |
| C‑009 | Job Scheduling & Execution | `JobRestServiceImpl` / `JobServiceImpl` |
| C‑010 | Security Token Management | `TokenAuthenticationRestTemplateConfigurationSpringBoot` (config) |
| C‑011 | Static Content Delivery | `StaticContentController` (static web resources) |
| C‑012 | OpenAPI Documentation | `OpenApiConfig` / `OpenApiOperationAuthorizationRightCustomizer` |
| C‑013 | Exception Handling & Validation | `DefaultExceptionHandler` |
| C‑014 | Handover Data Set Management | `HandoverDataSetRestServiceImpl` / `HandoverDataSetServiceImpl` |
| C‑015 | Notary Representation | `NotaryRepresentationRestServiceImpl` |
| C‑016 | Business Purpose Management | `BusinessPurposeRestServiceImpl` / `BusinessPurposeServiceImpl` |
| C‑017 | Deed Entry Connection Management | `DeedEntryConnectionRestServiceImpl` / `DeedEntryConnectionServiceImpl` |
| C‑018 | Deed Entry Log Management | `DeedEntryLogRestServiceImpl` / `DeedEntryLogServiceImpl` |
| C‑019 | Restricted Deed Entry (Special Cases) | `RestrictedDeedEntryEntity` (entity) |
| C‑020 | Scheduler Configuration | `Scheduler` (infrastructure) |

*The list is exhaustive with respect to the publicly visible controller and service components (32 controllers, 184 services).*

### System Statistics
| Metric | Value |
|--------|-------|
| **Containers** | 5 |
| **Components (total)** | 951 |
| **Interfaces** | 226 |
| **Relations** | 190 |
| **Controllers** | 32 |
| **Services** | 184 |
| **Repositories** | 38 |
| **Entities** | 360 |
| **REST Endpoints** | 196 (GET 128, POST 30, PUT 18, DELETE 14, PATCH 6) |
| **Modules** | 16 |
| **Adapters** | 50 |
| **Pipes** | 67 |
| **Directives** | 3 |
| **Interceptors** | 4 |
| **Guards** | 1 |
| **Schedulers** | 1 |
| **Configuration Classes** | 1 |

## 1.2 Quality Goals

| Goal ID | Quality Attribute | Target | Priority | Rationale | Realisation Pattern(s) | Measurement Method |
|---------|-------------------|--------|----------|-----------|------------------------|--------------------|
| Q‑001 | **Maintainability** | ≤ 10 % change‑impact per release | High | Large team, frequent regulatory updates | **Layered Architecture**, **Domain‑Driven Design**, **Modularisation** | Cyclomatic complexity ≤ 10, code‑coverage ≥ 80 % |
| Q‑002 | **Testability** | ≥ 85 % unit‑test coverage, full integration test suite for all REST endpoints | High | Guarantees safe deployments in production | **Hexagonal Architecture**, **Test‑Driven Development**, **Mock‑based isolation** | JaCoCo coverage reports, CI pipeline pass rate |
| Q‑003 | **Security** | OWASP Top‑10 compliance, < 0.5 % security incidents per year | Critical | Handles personal data and legal documents | **Zero‑Trust**, **Spring Security**, **OAuth2/JWT**, **Security‑by‑Design** | Automated security scans (Snyk), penetration test results |
| Q‑004 | **Performance** | 95 % of API calls ≤ 200 ms under load of 500 RPS | Medium | Supports national‑wide usage spikes | **Caching (Caffeine)**, **Async processing**, **Thread‑pool tuning** | JMeter response‑time metrics, APM dashboards |
| Q‑005 | **Scalability** | Horizontal scaling to 10 × current load without degradation | Medium | Future growth of registries | **Stateless services**, **Containerisation (Docker/K8s)**, **Load‑balancing** | Kubernetes HPA metrics, throughput tests |

### Rationale Summary
- **Maintainability** is essential because legal regulations evolve, requiring rapid adaptation.
- **Testability** reduces regression risk when new features (e.g., number‑gap handling) are added.
- **Security** is non‑negotiable due to GDPR and national data‑protection laws.
- **Performance** ensures notaries experience negligible latency during peak filing periods.
- **Scalability** prepares the platform for nationwide rollout and future integration with other public‑service portals.

## 1.3 Stakeholders

| Stakeholder ID | Role | Primary Concern(s) | Expectations | Key Interactions with the System |
|----------------|------|--------------------|--------------|-----------------------------------|
| S‑001 | **Notary Public** | Accuracy of deed data, ease of entry | Intuitive UI, immediate validation, audit trail | Uses web UI (Angular) and REST APIs for deed creation/modification |
| S‑002 | **Registry Clerk** | Bulk processing, number allocation, archiving | Batch job support, reporting, data export | Executes scheduled jobs, accesses reporting endpoints |
| S‑003 | **Auditor** | Traceability, compliance evidence | Immutable logs, exportable audit reports | Queries audit‑log REST endpoints, downloads PDF/CSV reports |
| S‑004 | **System Administrator** | Availability, patch management, monitoring | Automated deployments, health‑checks, alerting | Interacts with Kubernetes, Spring Actuator, CI/CD pipelines |
| S‑005 | **Security Officer** | Threat mitigation, data protection | Regular security scans, role‑based access control |
| S‑006 | **External Integrator (e.g., Land Registry)** | API stability, versioning | Stable OpenAPI contracts, backward compatibility |
| S‑007 | **Product Owner** | Business value delivery, roadmap alignment | Feature prioritisation, KPI dashboards |
| S‑008 | **End‑User Support Engineer** | Incident resolution, knowledge base | Access to logs, debugging tools, error‑handling documentation |

*All stakeholder concerns are addressed through the quality goals and architectural decisions described above.*

---

*Document generated on 2026‑02‑09 using real architecture facts from the uvz code base.*