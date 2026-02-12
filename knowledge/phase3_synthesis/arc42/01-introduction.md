# 01 - Introduction and Goals

---

## 1.1 Requirements Overview

### System Description & Business Domain
The **UVZ** platform is a **public‑record‑keeping and deed‑management system** that supports the complete lifecycle of land‑registry entries, deed transfers, and associated metadata. It belongs to the **Government / Public Administration** domain and implements the **Digital Land Registry** sub‑domain. The solution replaces legacy manual processes with a fully automated, auditable, and searchable service.

### Primary Business Value & Target Users
| Business Value | Description |
|----------------|-------------|
| **Legal Certainty** | Guarantees immutable, tamper‑proof records of property rights. |
| **Operational Efficiency** | Reduces processing time of deed registrations from days to minutes. |
| **Transparency & Auditability** | Provides full audit trails for every operation. |
| **Scalability** | Handles national‑wide transaction volumes and future extensions (e.g., integration with GIS). |

| Target User | Role |
|------------|------|
| **Notary Public** | Initiates and validates deed entries. |
| **Registry Clerk** | Performs day‑to‑day operations, queries, and reporting. |
| **Citizen / Property Owner** | Views status of their deeds via a portal. |
| **External Systems** (e.g., GIS, Tax Authority) | Consume REST APIs for data exchange. |

### Feature Inventory (Business Capabilities)
The following table lists the **business capabilities** derived from the names of the discovered **controllers** and **services** (partial list – full catalogue contains 32 controllers and 184 services). Each capability is expressed as a verb‑noun phrase that reflects a user‑visible function.

| Capability ID | Source Component | Capability Description |
|---------------|------------------|------------------------|
| BC‑001 | `ActionRestServiceImpl` | Execute generic system actions (e.g., health‑check, maintenance). |
| BC‑002 | `IndexHTMLResourceService` | Serve static UI resources and landing pages. |
| BC‑003 | `StaticContentController` | Provide downloadable static documents (templates, guidelines). |
| BC‑004 | `JsonAuthorizationRestServiceImpl` | Authorize JSON‑based API calls using custom security expressions. |
| BC‑005 | `KeyManagerRestServiceImpl` | Manage cryptographic keys for signing and encryption. |
| BC‑006 | `ArchivingRestServiceImpl` | Archive historic deed records according to retention policies. |
| BC‑007 | `BusinessPurposeRestServiceImpl` | Retrieve and update business purpose metadata for deeds. |
| BC‑008 | `DeedEntryRestServiceImpl` | Create, read, update, delete (CRUD) deed entries. |
| BC‑009 | `DeedRegistryRestServiceImpl` | Register new deeds and assign registry numbers. |
| BC‑010 | `DeedTypeRestServiceImpl` | Manage deed type catalog (e.g., purchase, mortgage). |
| BC‑011 | `DocumentMetaDataRestServiceImpl` | Store and retrieve document metadata linked to deeds. |
| BC‑012 | `HandoverDataSetRestServiceImpl` | Transfer deed data sets between systems or departments. |
| BC‑013 | `ReportRestServiceImpl` | Generate statutory and operational reports. |
| BC‑014 | `JobRestServiceImpl` | Schedule and monitor background jobs (e.g., batch imports). |
| BC‑015 | `NumberManagementRestServiceImpl` | Allocate and manage unique UVZ numbers. |
| BC‑016 | `ReportMetadataRestServiceImpl` | Maintain metadata for generated reports. |
| BC‑017 | `ActionServiceImpl` | Business‑level implementation of generic actions. |
| BC‑018 | `ArchiveManagerServiceImpl` | Orchestrate archiving workflows and storage tiering. |
| BC‑019 | `KeyManagerServiceImpl` | Provide cryptographic services to other components. |
| BC‑020 | `DeedEntryServiceImpl` | Core business logic for deed entry lifecycle. |
| BC‑021 | `DeedRegistryServiceImpl` | Business rules for deed registration and numbering. |
| BC‑022 | `DeedTypeServiceImpl` | Validation and handling of deed type specific rules. |
| BC‑023 | `DocumentMetaDataServiceImpl` | Enrich deeds with document metadata. |
| BC‑024 | `HandoverDataSetServiceImpl` | Business logic for data‑set handover processes. |
| BC‑025 | `ReportServiceImpl` | Assemble data for statutory reporting. |
| BC‑026 | `JobServiceImpl` | Execute scheduled background jobs. |
| BC‑027 | `NumberManagementServiceImpl` | Allocate UVZ numbers with gap‑management. |
| BC‑028 | `SignatureFolderServiceImpl` | Manage signature folders for signed documents. |
| BC‑029 | `NotaryRepresentationRestServiceImpl` | Handle notary representation data. |
| BC‑030 | `OfficialActivityMetadataRestServiceImpl` | Store official activity metadata linked to deeds. |
| ... | ... | (additional capabilities continue for the remaining controllers/services) |

### System Statistics
| Statistic | Value |
|-----------|-------|
| **Containers** | 5 |
| **Components** | 951 |
| **Interfaces** | 226 |
| **Relations** | 190 |
| **Controllers** | 32 |
| **Services** | 184 |
| **Repositories** | 38 |
| **Entities** | 360 |
| **REST Endpoints** | 0 *(no endpoint metadata discovered – will be documented in later chapters)* |

---

## 1.2 Quality Goals

| Goal | Priority | Rationale | Achieving Pattern(s) | Measurement |
|------|----------|-----------|----------------------|------------|
| **Maintainability** | High | Frequent regulatory updates require quick code changes. | Layered Architecture, Hexagonal Ports & Adapters, CI/CD pipelines. | Mean Time to Change (MTTC) ≤ 2 days; Code‑coverage ≥ 80 %. |
| **Testability** | High | Critical legal operations must be verified automatically. | Test‑Driven Development, Mock‑based Service Isolation, Contract Tests. | Unit test coverage ≥ 80 %; Integration test pass rate ≥ 95 %. |
| **Security** | Critical | Sensitive personal and property data must be protected. | Spring Security with Method‑Level Authorization, JWT, Encryption‑at‑Rest, Zero‑Trust Network. | No critical vulnerabilities (CVSS ≥ 7) in OWASP scans; 100 % of endpoints protected. |
| **Performance** | Medium | High‑volume batch imports and real‑time queries. | Asynchronous Processing, Caching (Redis), Bulk‑Insert Optimisation. | 95 % of API calls ≤ 200 ms; Batch import ≥ 10 k records/min. |
| **Scalability** | Medium | Nationwide rollout and future EU‑wide expansion. | Microservice decomposition, Containerisation (Docker/K8s), Horizontal scaling. | System can handle 2× peak load without degradation; Auto‑scale latency ≤ 30 s. |

---

## 1.3 Stakeholders

| Stakeholder | Role | Primary Concern | Expectations | Key Interactions |
|------------|------|----------------|--------------|------------------|
| **Product Owner (Public Registry)** | Business sponsor | Alignment with legal regulations | Feature completeness, compliance reporting | Reviews backlog, approves releases |
| **Notary Public** | End‑user (deed creation) | Accuracy & speed of deed entry | Immediate validation, audit trail | Uses UI & API for deed submission |
| **Registry Clerk** | Operational user | Efficient processing of large batches | Bulk import, search, reporting | Interacts with batch jobs and reporting services |
| **Citizen / Property Owner** | External user | Transparency of property status | Access to read‑only view, status notifications | Consumes public REST endpoints or portal |
| **Security Officer** | Governance | Data protection & access control | Full compliance with GDPR & national law | Audits security configuration, reviews logs |
| **DevOps Engineer** | Operations | Deployability & reliability | Automated CI/CD, monitoring, rollback | Manages Kubernetes clusters, CI pipelines |
| **QA Engineer** | Quality assurance | Test coverage & defect detection | Automated test suites, defect metrics | Executes regression suites, reviews test reports |
| **External System Integrator** (e.g., GIS) | Partner system | Stable API contract | Versioned, documented, backward compatible APIs | Consumes REST APIs, receives webhook events |
| **System Administrator** | Infrastructure | Availability & performance | SLA adherence, capacity planning | Monitors health checks, scaling policies |
| **Legal Auditor** | Compliance | Traceability of all actions | Immutable audit logs, export capability | Reviews audit logs, requests data extracts |

---

*The above sections constitute the complete **Chapter 1 – Introduction and Goals** of the arc42 documentation for the UVZ system.*
