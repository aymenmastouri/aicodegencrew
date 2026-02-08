# 01 – Introduction and Goals

## 1.1 Requirements Overview

**System name:** **uvz** – a deed‑entry management platform for public registries.

**Business domain classification:**
- **Core domain:** Deed entry lifecycle (creation, signing, hand‑over, archiving).
- **Supporting sub‑domains:** Number management, Document metadata, Reporting, Security & Auditing.

**Primary business value:**
- Provide a reliable, auditable, and legally compliant service for registering, signing and archiving deeds.
- Reduce manual processing time for notaries and registry offices by up to 70 %.
- Ensure traceability of every operation for statutory audits.

**Target users:**
- Notaries and registry clerks (internal users).
- External partners (e.g., banks, legal firms) via secured REST APIs.
- Supervisory authorities (read‑only audit access).

### Feature Inventory (derived from controllers & services)
| Business Capability | Representative Controllers / Services |
|----------------------|--------------------------------------|
| Deed entry CRUD | `DeedEntryRestServiceImpl`, `DeedEntryServiceImpl` |
| Deed signing & signature folder | `DeedEntryRestServiceImpl` (POST `/signature-folder`), `SignatureFolderServiceImpl` |
| Handover of deed data sets | `HandoverDataSetRestServiceImpl`, `HandoverDataSetServiceImpl` |
| Archiving & re‑encryption | `ArchivingRestServiceImpl`, `ArchivingServiceImpl`, `ArchivingOperationSignerImpl` |
| Number management (UVZ numbers) | `NumberManagementRestServiceImpl`, `NumberManagementServiceImpl` |
| Business purpose catalogue | `BusinessPurposeRestServiceImpl`, `BusinessPurposeServiceImpl` |
| Document metadata handling | `DocumentMetaDataRestServiceImpl`, `DocumentMetaDataServiceImpl` |
| Reporting & analytics | `ReportRestServiceImpl`, `ReportServiceImpl` |
| Security & authentication | `JsonAuthorizationRestServiceImpl`, `TokenAuthenticationRestTemplateConfigurationSpringBoot` |
| Job & batch processing | `JobRestServiceImpl`, `JobServiceImpl` |
| Audit logging & history | `DeedEntryLogRestServiceImpl`, `DeedEntryLogServiceImpl` |
| Lock management for concurrency | `DeedEntryRestServiceImpl` (lock endpoints), `DeedEntryLockServiceImpl` |
| Participant & notary data | `ParticipantRestServiceImpl`, `ParticipantServiceImpl` |
| Official activity metadata | `OfficialActivityMetadataRestServiceImpl` |
| Report metadata management | `ReportMetadataRestServiceImpl` |
| Task & workflow orchestration | `TaskRestServiceImpl`, `TaskServiceImpl` |
| Key management | `KeyManagerRestServiceImpl`, `KeyManagerServiceImpl` |
| Validation & exception handling | `DefaultExceptionHandler`, `ValidationException` |
| Health & monitoring | `HealthCheck` |

### System Statistics
| Metric | Value |
|--------|-------|
| Total components (all stereotypes) | 951 |
| Controllers | 32 |
| Services (application layer) | 184 |
| Repositories (data‑access layer) | 38 |
| Entities (domain model) | 360 |
| REST endpoints (HTTP) | 196 |
| Containers (runtime modules) | 5 |
| Relations (uses, manages, imports, references) | 190 |

---

## 1.2 Quality Goals

| Quality Goal | Priority | Rationale | Pattern(s) Used | Measurement |
|--------------|----------|-----------|----------------|-------------|
| **Maintainability** | High | Frequent regulatory changes require fast adaptation. | Layered Architecture, Repository, Service‑Facade, DTO mapping. | Mean Time to Change (MTTC) ≤ 2 days for rule updates. |
| **Testability** | High | Critical for legal compliance; automated regression needed. | Hexagonal Architecture, Mock‑based unit tests, Contract testing (Pact). | 80 % unit coverage, 90 % integration coverage, < 5 min CI pipeline. |
| **Security** | Critical | Handles personal data and legal documents. | Spring Security, JWT, OAuth2, Method‑level security annotations, API‑gateway pattern. | OWASP ASVS Level 2 compliance, no critical findings in quarterly scans. |
| **Performance** | Medium | High‑volume batch imports and real‑time signing. | Asynchronous processing (Spring @Async), Bulk‑capture endpoints, Caching (Caffeine). | 95 % of API calls ≤ 200 ms, batch import ≤ 10 k records/min. |
| **Scalability** | Medium | Expected growth of registries and external partners. | Microservice‑ready modularisation, Horizontal scaling via Kubernetes, Circuit‑breaker (Resilience4j). | Linear throughput increase up to 5× current load without latency degradation. |

---

## 1.3 Stakeholders

| Role | Concern | Expectations | Key Interactions |
|------|---------|--------------|------------------|
| **Notary / Registry Clerk** | Efficient deed entry & signing | Intuitive UI, fast response, audit trail | Uses UI (Angular) → calls REST APIs (deed entry, signing). |
| **External Partner (Bank, Law Firm)** | Secure API access to deed data | Authentication, SLA, versioned endpoints | Consumes public REST endpoints (e.g., `/uvz/v1/deedentries`). |
| **Regulatory Authority** | Compliance & auditability | Full log export, immutable records | Reads audit logs via `/uvz/v1/audit` (internal). |
| **System Administrator** | Operability & monitoring | Health checks, metrics, easy deployment | Interacts with `/actuator/health`, Prometheus, Kubernetes. |
| **Security Officer** | Data protection, threat mitigation | OWASP compliance, encryption, access control | Reviews security config, token policies. |
| **Product Owner** | Business value delivery | Feature completeness, time‑to‑market | Prioritises backlog items, validates functional demos. |
| **DevOps Engineer** | CI/CD, infrastructure automation | Automated builds, zero‑downtime deployments | Uses Docker, Helm charts, GitLab CI pipelines. |
| **Support Engineer** | Incident resolution | Clear error messages, traceability | Consults logs, uses `/uvz/v1/logger` endpoint. |

---

*The above sections constitute the complete Chapter 1 of the arc42 documentation for the **uvz** system.*