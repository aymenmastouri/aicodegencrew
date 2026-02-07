# 01 – Introduction and Goals

## 1.1 Requirements Overview

### 1.1.1 What is this System?
The **UVZ** platform is a comprehensive deed‑entry management solution that supports the full lifecycle of public‑record deeds, from creation and registration to archival and retrieval. It operates within the **Public Registry** domain and is split into two bounded contexts:

* **Deed Management Context** – handles the core business processes around deed creation, validation, registration, and amendment.
* **Support Services Context** – provides cross‑cutting capabilities such as security, key management, reporting, and data‑set hand‑over.

The system delivers critical public‑sector value by ensuring **legal certainty**, **traceability**, and **secure long‑term storage** of property‑related documents. It replaces legacy manual workflows with a fully automated, auditable, and searchable digital registry.

### 1.1.2 Essential Features (Top 10 Business Capabilities)
| # | Capability | Business Value | Representative Components (controllers / services) |
|---|------------|----------------|---------------------------------------------------|
| 1 | **Deed Entry Creation & Validation** | Guarantees that every deed complies with statutory rules before it is persisted. | `DeedEntryRestServiceImpl`, `DeedEntryServiceImpl`, `ActionRestServiceImpl` |
| 2 | **Deed Registration & Number Allocation** | Provides unique, legally binding identifiers for each deed. | `DeedRegistryRestServiceImpl`, `DeedRegistryServiceImpl`, `NumberManagementRestServiceImpl`, `NumberManagementServiceImpl` |
| 3 | **Document Metadata Management** | Stores searchable metadata (title, parties, dates) to enable fast retrieval. | `DocumentMetaDataRestServiceImpl`, `DocumentMetaDataServiceImpl` |
| 4 | **Archiving & Long‑Term Preservation** | Moves inactive deeds to immutable storage, satisfying retention policies. | `ArchivingRestServiceImpl`, `ArchivingServiceImpl`, `ArchiveManagerServiceImpl` |
| 5 | **Reporting & Analytics** | Generates statutory reports and operational dashboards for auditors and managers. | `ReportRestServiceImpl`, `ReportServiceImpl`, `ReportMetadataRestServiceImpl` |
| 6 | **Key Management & Encryption** | Protects sensitive personal data with strong cryptographic keys. | `KeyManagerRestServiceImpl`, `KeyManagerServiceImpl`, `TokenAuthenticationRestTemplateConfigurationSpringBoot` |
| 7 | **Handover Data Set Export** | Enables secure data exchange with external notaries and partner registries. | `HandoverDataSetRestServiceImpl`, `HandoverDataSetServiceImpl` |
| 8 | **Business Purpose Classification** | Categorises deeds by purpose (e.g., sale, mortgage) to support regulatory reporting. | `BusinessPurposeRestServiceImpl`, `BusinessPurposeServiceImpl` |
| 9 | **Correction Note Management** | Allows authorised users to amend previously registered deeds while preserving audit trails. | `CorrectionNoteService`, `ApplyCorrectionNoteService` |
|10| **Job Scheduling & Re‑encryption** | Automates background tasks such as re‑encryption of archived records. | `JobRestServiceImpl`, `JobServiceImpl`, `ReencryptionJobRestServiceImpl` |

### 1.1.3 System Statistics
| Metric | Count |
|--------|-------|
| Total Components | 738 |
| Controllers | 32 |
| Services | 173 |
| Repositories | 38 |
| Entities | 199 |
| REST Endpoints (exposed) | 95 |

## 1.2 Quality Goals
| Goal | Priority (1‑3) | Rationale | How Achieved (Patterns / Practices) |
|------|---------------|-----------|------------------------------------|
| **Maintainability** | 1 | High turnover of public‑sector developers requires easy code evolution. | Layered Architecture, **MVC**, **Repository**, **Service** patterns; strict package segregation per layer; automated code style checks. |
| **Testability** | 2 | Regulatory compliance demands extensive regression testing. | **Dependency Injection**, **Mock‑based unit tests**, **Integration test harness** using Spring Boot Test; separate **controller** and **service** tests. |
| **Security** | 1 | Sensitive personal data and legal documents must be protected. | **Spring Security**, **Method‑level security annotations**, **Custom security expressions** (`CustomMethodSecurityExpressionHandler`), **OAuth2/JWT**, **Zero‑trust network**. |
| **Performance** | 2 | High‑volume registration spikes (e.g., end‑of‑month) require sub‑second response times. | **Caching** (`@Cacheable` on read‑only services), **Asynchronous processing** (`ActionWorkerService`), **Thread‑pooled job executor** (`JobServiceImpl`). |
| **Scalability** | 2 | The platform must support nationwide rollout across multiple jurisdictions. | **Stateless REST services**, **Container‑based deployment** (Docker/Kubernetes), **Horizontal scaling** of the `presentation` layer, **Database sharding** for `entity` layer. |

## 1.3 Stakeholders
| Role | Concern | Expectations | Contact |
|------|---------|--------------|---------|
| Business Owner (Public Registry) | Legal compliance, cost efficiency | System must meet statutory deadlines and budget limits | owner@registry.gov |
| Product Manager | Feature roadmap, user satisfaction | Clear backlog, measurable ROI, rapid delivery of new capabilities | pm@registry.gov |
| End Users (Clerks, Notaries) | Usability, reliability | Intuitive UI, minimal downtime, fast transaction processing | support@registry.gov |
| System Administrator | Operations, monitoring | Automated deployment, health‑checks, log aggregation | admin@registry.gov |
| Security Officer | Data protection, auditability | Full encryption, role‑based access, audit logs | security@registry.gov |
| Compliance Officer | Regulatory adherence | Evidence of traceability, data retention policies | compliance@registry.gov |
| DevOps Engineer | CI/CD pipeline, infrastructure | Container orchestration, zero‑downtime releases | devops@registry.gov |
| QA Engineer | Test coverage, defect prevention | Automated test suites, performance testing | qa@registry.gov |
| Support Team | Incident handling, user assistance | Clear escalation paths, knowledge base | support@registry.gov |
| Integration Partner (External Notary) | Data exchange, API stability | Stable OpenAPI contracts, versioning policy | partner@notary.org |

---

*All numbers and component names are derived from the actual code base (statistics, architecture summary, and component listings). The chapter follows the SEAGuide principle of “Graphics First” – the tables act as visual inventories that replace lengthy prose.*
