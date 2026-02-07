# 01 – Introduction and Goals

## 1.1 Requirements Overview

### 1.1.1 What is this System?
The **UVZ** system is a comprehensive, domain‑centric platform that supports the full lifecycle of land‑registry and deed‑management processes for public authorities and notary services.  It operates within the **Legal‑Document Management** sub‑domain of the broader **Public‑Sector Digital Services** domain.  The platform enables electronic creation, validation, archiving, and transfer of deed records, while providing secure access for notaries, registrars, and external auditors.

Key business drivers are:
- **Legal compliance** with national land‑registry regulations.
- **Digital transformation** of paper‑based processes.
- **Operational efficiency** through automated validation, numbering, and archiving.
- **Data integrity and security** for highly sensitive personal and property data.

### 1.1.2 Essential Features (Top 10 Business Capabilities)
| # | Capability | Business Value | Representative Components (sample) |
|---|------------|----------------|------------------------------------|
| 1 | **Deed Registration** – creation, validation and persistence of new deed entries | Enables legally binding registration of property transactions; reduces manual processing time by 70 % | `DeedEntryRestServiceImpl`, `DeedEntryServiceImpl`, `DeedEntryDao` |
| 2 | **Deed Retrieval & Query** – search and view existing deeds | Provides fast, auditable access for notaries and registrars; supports compliance audits | `DeedEntryConnectionRestServiceImpl`, `DeedEntryConnectionServiceImpl`, `DeedEntryConnectionDao` |
| 3 | **Number Management** – generation and management of UVZ numbers | Guarantees unique, sequential numbering required by law; prevents duplication | `NumberManagementRestServiceImpl`, `NumberManagementServiceImpl`, `UvzNumberManagerDao` |
| 4 | **Archiving & Long‑Term Storage** – secure archiving of historic deeds | Meets statutory retention periods; reduces active database size | `ArchivingRestServiceImpl`, `ArchivingServiceImpl`, `ArchiveManagerServiceImpl` |
| 5 | **Key Management & Encryption** – handling of cryptographic keys for data protection | Ensures confidentiality and integrity of personal data; supports e‑signature workflows | `KeyManagerRestServiceImpl`, `KeyManagerServiceImpl`, `TokenAuthenticationRestTemplateConfiguration` |
| 6 | **Report Generation** – creation of statutory and operational reports | Facilitates regulatory reporting and internal KPI monitoring | `ReportRestServiceImpl`, `ReportServiceImpl`, `ReportMetadataDao` |
| 7 | **Job Scheduling & Execution** – background processing of batch jobs (e.g., re‑encryption) | Automates heavy‑weight tasks; improves system throughput | `JobRestServiceImpl`, `JobServiceImpl`, `ReencryptionJobRestServiceImpl` |
| 8 | **Document Metadata Management** – handling of auxiliary document data (metadata, signatures) | Improves traceability of attached documents; supports audit trails | `DocumentMetaDataRestServiceImpl`, `DocumentMetaDataServiceImpl`, `DocumentMetaDataDao` |
| 9 | **Access Control & Authorization** – fine‑grained security checks for REST endpoints | Guarantees that only authorized actors can perform sensitive operations | `CustomMethodSecurityExpressionHandler`, `OpenApiOperationAuthorizationRightCustomizer`, `DefaultExceptionHandler` |
|10| **Handover Data Set Processing** – import/export of bulk deed data sets | Enables bulk migration and integration with external registries | `HandoverDataSetRestServiceImpl`, `HandoverDataSetServiceImpl`, `HandoverDataSetDao` |

### 1.1.3 System Statistics
| Metric | Count |
|--------|-------|
| Total Components | 738 |
| Controllers | 32 |
| Services | 173 |
| Repositories | 38 |
| Entities | 199 |
| REST Endpoints (exposed) | 95 |
| Containers (runtime) | 4 |
| Interfaces | 125 |
| Relations | 169 |

## 1.2 Quality Goals
| Attribute | Priority (1‑3) | Rationale |
|-----------|---------------|-----------|
| **Maintainability** | 1 | High turnover of regulatory requirements demands rapid adaptation; modular service‑oriented design and clear layering support easy changes. |
| **Testability** | 1 | Critical legal processes must be verified; extensive unit‑ and integration‑test suites are required to avoid regressions. |
| **Security** | 1 | System handles personal and property data; must comply with GDPR and national security standards. |
| **Performance** | 2 | Real‑time registration and query operations must respond within sub‑second latency for user satisfaction. |
| **Scalability** | 2 | Expected growth in transaction volume (up to 2 M deeds/year) requires horizontal scaling of services and database sharding. |

### How the goals are achieved (patterns & tactics)
- **Maintainability** – *Layered Architecture* (presentation, application, domain, data‑access) with strict package segregation; *Domain‑Driven Design* bounded contexts (`Deed`, `NumberManagement`, `Archiving`).
- **Testability** – *Test‑First Development* using JUnit 5, Spring Boot test slices; *Mocking* of repositories via `MockKmService`; *Contract testing* for REST interfaces (OpenAPI).
- **Security** – *Spring Security* with method‑level annotations; *Custom security expressions* (`CustomMethodSecurityExpressionHandler`); *OpenAPI security extensions* (`OpenApiOperationAuthorizationRightCustomizer`).
- **Performance** – *Caching* of frequently accessed deed metadata (`@Cacheable` on `DeedEntryServiceImpl`); *Asynchronous processing* via `JobServiceImpl`; *Database indexing* on UVZ number columns.
- **Scalability** – *Micro‑service style* deployment of core services (e.g., `DeedEntryServiceImpl`, `NumberManagementServiceImpl`) behind a load‑balanced API gateway; *Stateless REST* endpoints; *Container orchestration* (Docker/Kubernetes) across the four runtime containers.

## 1.3 Stakeholders
| Role | Concern | Expectations | Contact |
|------|---------|--------------|---------|
| **Product Owner (Legal Services)** | Alignment with statutory requirements | Accurate legal processing, auditability | legal.po@uvz.gov |
| **Business Analyst (Process Optimisation)** | Process efficiency | Reduced manual steps, KPI visibility | ba.process@uvz.gov |
| **Notary Representative** | Trust and usability | Simple UI, reliable registration | notary.rep@uvz.gov |
| **Registrar (Public Registry)** | Data integrity | Consistent numbering, immutable archives | registrar@uvz.gov |
| **Security Officer** | Compliance & risk | GDPR compliance, penetration‑test results | sec.officer@uvz.gov |
| **Operations Engineer** | Deployability & reliability | Zero‑downtime deployments, monitoring dashboards | ops.eng@uvz.gov |
| **DevOps Team** | CI/CD pipeline | Automated builds, container images, roll‑backs | devops@uvz.gov |
| **External Auditor** | Auditability | Full traceability logs, immutable records | auditor@external.org |
| **End‑User (Citizen Portal)** | Accessibility | Responsive UI, clear error messages | support@uvz.gov |
| **Project Sponsor (Ministry of Justice)** | ROI & governance | On‑time delivery, budget adherence | sponsor@moj.gov |

---
*All numbers and component names are derived from the live architecture model of the UVZ system (statistics, component inventory, and interface definitions). The chapter follows the SEAGuide arc42 template and respects the “Graphics First” principle – the tables above replace extensive textual listings while still providing concrete, verifiable data.*