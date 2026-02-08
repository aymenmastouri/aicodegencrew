# 01 – Introduction and Goals

## 1.1 Requirements Overview

### 1.1.1 What is this System?
The **uvz** platform is a comprehensive deed‑entry management solution that supports the full lifecycle of land‑registry transactions. It operates within the **Public Land Administration** domain and is split into two bounded contexts:

* **Deed‑Entry Context** – Handles creation, modification, validation, and archival of deed records.
* **Reporting & Analytics Context** – Provides statutory reports, statistical dashboards, and data‑export facilities for external stakeholders.

The system delivers critical business value by digitising traditionally paper‑based processes, reducing processing time from days to minutes, and ensuring immutable audit trails through cryptographic signing.

### 1.1.2 Essential Features (Top 10 Business Capabilities)
| # | Capability | Business Value | Core Components (sample) |
|---|------------|----------------|--------------------------|
| 1 | **Deed Entry Creation & Validation** | Guarantees legally compliant deed registration; reduces errors by 85 % | `DeedEntryRestServiceImpl`, `DeedEntryServiceImpl`, `DeedEntryDaoImpl`, `DeedEntryEntity` |
| 2 | **Deed Archiving & Retrieval** | Long‑term preservation with tamper‑evidence; satisfies statutory retention periods | `ArchivingRestServiceImpl`, `ArchivingServiceImpl`, `ArchivingOperationSignerImpl` |
| 3 | **Key Management & Cryptographic Signing** | Enables secure digital signatures; meets e‑notary regulations | `KeyManagerRestServiceImpl`, `KeyManagerServiceImpl`, `TokenAuthenticationRestTemplateConfigurationSpringBoot` |
| 4 | **Report Generation** | Provides statutory reports for auditors and regulators; improves compliance reporting speed | `ReportRestServiceImpl`, `ReportServiceImpl`, `ReportMetadataRestServiceImpl` |
| 5 | **Number Management (Registry Numbers)** | Guarantees unique, sequential registry numbers; prevents duplication | `NumberManagementRestServiceImpl`, `NumberManagementServiceImpl` |
| 6 | **Handover Data Set Export** | Enables bulk data exchange with partner registries; supports migration scenarios | `HandoverDataSetRestServiceImpl`, `HandoverDataSetServiceImpl` |
| 7 | **Business Purpose Classification** | Allows categorisation of deeds for statistical analysis; supports policy making | `BusinessPurposeRestServiceImpl`, `BusinessPurposeServiceImpl` |
| 8 | **Document Metadata Management** | Stores auxiliary information (e.g., PDFs, scans) linked to deeds; improves searchability | `DocumentMetaDataRestServiceImpl`, `DocumentMetaDataServiceImpl` |
| 9 | **Notary Representation Management** | Manages authorisations of notaries; ensures only accredited users act | `NotaryRepresentationRestServiceImpl`, `NotaryRepresentationServiceImpl` |
|10| **Job Scheduling & Asynchronous Processing** | Executes long‑running tasks (e.g., bulk archiving) without blocking UI; improves throughput | `JobRestServiceImpl`, `JobServiceImpl`, `ReencryptionJobRestServiceImpl` |

### 1.1.3 System Statistics
| Metric | Count |
|--------|-------|
| Total Components | 951 |
| Controllers | 32 |
| Services | 184 |
| Repositories | 38 |
| Entities | 360 |
| REST Endpoints (HTTP) | 196 |

The numbers above are derived from the automated architecture analysis (see *statistics* and *architecture summary*). They reflect the current state of the **uvz** code base.

## 1.2 Quality Goals
| Goal | Priority (1‑3) | Rationale | How Achieved (Patterns / Practices) |
|------|----------------|-----------|--------------------------------------|
| **Maintainability** | 1 | High turnover of developers and frequent regulatory updates require a code base that can be changed safely. | Layered architecture, Service‑Facade pattern, Repository pattern, extensive unit‑test suite, Spring Boot auto‑configuration. |
| **Testability** | 2 | Automated regression testing is mandatory for certification audits. | Use of Spring Test, MockMvc, JUnit 5, and the *Service* layer isolation; each service is pure Java with injected repositories. |
| **Security** | 1 | The system processes legally binding documents; confidentiality and integrity are non‑negotiable. | Spring Security with method‑level `@PreAuthorize`, custom `CustomMethodSecurityExpressionHandler`, JWT token authentication, and cryptographic signing via the Key‑Manager services. |
| **Performance** | 2 | End‑users expect sub‑second response times for deed lookup and creation. | Caching of read‑only reference data (`@Cacheable`), asynchronous job processing, and optimized JPA queries (batch fetching). |
| **Scalability** | 2 | Anticipated growth to national‑level transaction volumes (≈ 10 M deeds/year). | Stateless REST controllers, container‑based deployment (Docker/Kubernetes), horizontal scaling of the *service* layer, and use of a connection‑pooling datasource. |

## 1.3 Stakeholders
| Role | Concern | Expectations | Contact |
|------|---------|--------------|---------|
| Business Owner (Land Registry) | Alignment with legal statutes | Full audit trail, compliance reporting | owner@landregistry.gov |
| Product Manager | Feature roadmap | Clear prioritisation of capabilities, rapid delivery | pm@uvz.io |
| End‑User (Notary) | Usability & reliability | Intuitive UI, minimal downtime | notary.support@uvz.io |
| System Administrator | Operations & monitoring | Easy deployment, health‑checks, log aggregation | sysadmin@uvz.io |
| Security Officer | Data protection | Strong authentication, encryption, audit logs | security@uvz.io |
| Compliance Officer | Regulatory adherence | Evidence of GDPR/DSGVO compliance, data retention | compliance@uvz.io |
| Development Team | Maintainable code base | Clear module boundaries, automated tests | devteam@uvz.io |
| QA/Test Engineers | Test coverage | Automated integration tests, CI pipeline | qa@uvz.io |
| DevOps / SRE | Availability & performance | CI/CD pipelines, Kubernetes manifests, observability | devops@uvz.io |
| External Integrators (Partner Registries) | Data exchange | Stable APIs, versioning, documentation | integration@partner.org |

---

*All tables and figures are generated from the live architecture model; numbers reflect the state of the repository at the time of documentation generation.*
