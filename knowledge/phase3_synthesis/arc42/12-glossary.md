# 12 – Glossary

## 12.1 Business Terms

| Term | Definition | Related Components |
|------|------------|--------------------|
| Action | Represents a user‑initiated operation or system event that triggers processing in the UVZ system. | `ActionEntity`, `ActionServiceImpl`, `ActionRestServiceImpl` |
| ActionStream | Stream of `Action` events used for asynchronous processing. | `ActionStreamEntity` |
| Change | A modification record applied to a deed or registration. | `ChangeEntity` |
| Connection | Logical link between deed entries and external systems. | `ConnectionEntity` |
| CorrectionNote | Annotation used to correct data entry errors in a deed. | `CorrectionNoteEntity`, `CorrectionNoteService` |
| DeedEntry | Core domain object representing a single entry in a deed register. | `DeedEntryEntity`, `DeedEntryServiceImpl`, `DeedEntryRestServiceImpl` |
| DeedEntryLock | Concurrency lock for a `DeedEntry` during updates. | `DeedEntryLockEntity` |
| DeedEntryLog | Audit log for changes made to a `DeedEntry`. | `DeedEntryLogEntity`, `DeedEntryLogServiceImpl` |
| DeedRegistry | Collection of all deed entries for a given jurisdiction. | `DeedRegistryLockEntity`, `DeedRegistryServiceImpl`, `DeedRegistryRestServiceImpl` |
| DocumentMetaData | Metadata describing a document attached to a deed (e.g., type, size, checksum). | `DocumentMetaDataEntity`, `DocumentMetaDataServiceImpl`, `DocumentMetaDataRestServiceImpl` |
| FinalHandoverDataSet | The definitive data set transferred during a handover process. | `FinalHandoverDataSetEntity` |
| HandoverDataSet | Intermediate data set used when handing over deed information between systems. | `HandoverDataSetEntity`, `HandoverDataSetServiceImpl`, `HandoverDataSetRestServiceImpl` |
| HandoverHistory | Historical record of all handover operations for a deed. | `HandoverHistoryEntity`, `HandoverHistoryDeedEntity` |
| IssuingCopyNote | Note attached to a copy of a deed that is issued to a third party. | `IssuingCopyNoteEntity` |
| Participant | Entity (person or organization) participating in a deed transaction. | `ParticipantEntity` |
| Registration | Formal registration of a deed in the land register. | `RegistrationEntity` |
| Remark | Free‑form comment attached to a deed or registration. | `RemarkEntity` |
| SignatureInfo | Information about signatures collected for a deed. | `SignatureInfoEntity` |
| SuccessorBatch | Batch of successor deeds processed together. | `SuccessorBatchEntity` |
| SuccessorDeedSelection | Selection criteria for determining successor deeds. | `SuccessorDeedSelectionEntity`, `SuccessorDeedSelectionMetaEntity` |
| SuccessorDetails | Detailed information about a successor deed. | `SuccessorDetailsEntity` |
| UVZNumberManager | Service responsible for generating and managing UVZ numbers (unique identifiers). | `UvzNumberManagerEntity`, `NumberManagementServiceImpl`, `NumberManagementRestServiceImpl` |
| Job | Background processing unit (e.g., archiving, re‑encryption). | `JobEntity`, `JobServiceImpl`, `JobRestServiceImpl` |
| Report | Generated statistical or compliance report. | `ReportServiceImpl`, `ReportRestServiceImpl` |
| ArchiveManager | Component handling archival storage of deed documents. | `ArchiveManagerServiceImpl`, `ArchivingServiceImpl`, `ArchivingRestServiceImpl` |
| KeyManager | Component managing cryptographic keys used for signing deeds. | `KeyManagerServiceImpl`, `KeyManagerRestServiceImpl` |
| WaWi | Abbreviation for “Warenwirtschaft” (inventory management) integration component. | `WaWiServiceImpl`, `DeedWaWiServiceImpl`, `DeedWaWiOrchestratorServiceImpl` |
| BusinessPurpose | Business purpose code attached to a deed for classification. | `BusinessPurposeServiceImpl`, `BusinessPurposeRestServiceImpl` |
| NotaryRepresentation | Representation of a notary’s authority in the system. | `NotaryRepresentationRestServiceImpl` |
| OfficialActivityMetadata | Metadata describing official activities related to a deed. | `OfficialActivityMetadataRestServiceImpl` |
| ReportMetadata | Metadata describing generated reports. | `ReportMetadataRestServiceImpl` |

## 12.2 Technical Terms

| Term | Definition | Context |
|------|------------|---------|
| Spring Boot | Convention‑over‑configuration framework for building Java microservices. | Backend services, REST controllers |
| REST | Representational State Transfer – architectural style for web APIs using HTTP verbs. | All `*RestServiceImpl` components |
| JPA | Java Persistence API – specification for object‑relational mapping. | Entity persistence, repositories |
| Repository Pattern | Design pattern that abstracts data access logic behind a collection‑like interface. | `*Repository` components (e.g., `KeyManagerRepository`) |
| Service Layer | Layer that contains business logic and orchestrates repository calls. | `*ServiceImpl` components |
| Controller Layer (MVC) | Presentation layer exposing HTTP endpoints. | `*RestServiceImpl` and `*Controller` components |
| Dependency Injection | Technique where a framework supplies component dependencies at runtime. | Spring’s `@Autowired`, constructor injection |
| Gradle | Build automation tool for Java projects. | Project build configuration |
| Angular | Front‑end framework for building SPA UI. | UI client (not part of backend code but referenced) |
| Node.js | JavaScript runtime used for tooling and UI tests. | Playwright test runner |
| Playwright | End‑to‑end testing framework for web applications. | UI test suite |
| JWT | JSON Web Token – compact token format for authentication/authorization. | Security configuration, `TokenAuthenticationRestTemplateConfigurationSpringBoot` |
| OAuth2 | Open standard for access delegation. | Security configuration |
| OpenAPI | Specification for describing RESTful APIs. | `OpenApiConfig`, API documentation |
| DTO | Data Transfer Object – lightweight object for transferring data across layers. | Used in controller request/response models |
| DAO | Data Access Object – low‑level persistence abstraction. | `*DaoImpl` components |
| CI/CD | Continuous Integration / Continuous Deployment pipelines. | Build and deployment process |
| Docker | Containerisation platform for packaging services. | Deployment environment |
| Kubernetes | Orchestration system for managing containerised workloads. | Production deployment |

## 12.3 Abbreviations

| Abbreviation | Full Form | Context |
|--------------|-----------|---------|
| UVZ | **U**niversal **V**erzeichnis **Z**ahl (system‑specific unique identifier) | Domain identifiers, number management |
| API | Application Programming Interface | REST services |
| DAO | Data Access Object | Persistence layer implementations |
| DTO | Data Transfer Object | Controller request/response models |
| JPA | Java Persistence API | Entity mapping |
| UI | User Interface | Front‑end Angular application |
| CI | Continuous Integration | Build pipeline |
| CD | Continuous Deployment | Release pipeline |
| JWT | JSON Web Token | Security/authentication |
| OAuth | Open Authorization | Security framework |
| REST | Representational State Transfer | API style |
| CRUD | Create, Read, Update, Delete | Basic data operations |
| DB | Database | PostgreSQL / Oracle backend |
| BPM | Business Process Management | Orchestration of handover workflows |
| SLA | Service Level Agreement | Operational targets |
| KPI | Key Performance Indicator | Monitoring metrics |
| XML | eXtensible Markup Language | Configuration files |
| YAML | Yet Another Markup Language | Spring Boot configuration |
| HTTP | Hypertext Transfer Protocol | Communication protocol |
| HTTPS | HTTP Secure | Encrypted communication |
| SSL | Secure Sockets Layer | Transport security |
| TLS | Transport Layer Security | Transport security |
| IDE | Integrated Development Environment | Development tooling |
| IDE | IntelliJ IDEA / Eclipse (used for Java development) |
| IDE | Visual Studio Code (used for Angular) |

## 12.4 Architecture Patterns

| Pattern | Definition | Where Used | Benefit |
|---------|------------|------------|---------|
| Layered Architecture | Organises system into logical layers (presentation, service, repository, domain). | Controllers → Services → Repositories → Entities | Clear separation of concerns, easier testing |
| Repository Pattern | Provides a collection‑like interface for data access, decoupling domain from persistence. | All `*Repository` and `*DaoImpl` components | Centralised data access, swap persistence implementations |
| Service Layer | Encapsulates business logic in dedicated services. | `*ServiceImpl` classes | Reuse of business rules, transaction management |
| RESTful API | Exposes resources via HTTP using standard verbs. | All `*RestServiceImpl` controllers | Interoperability, statelessness |
| Dependency Injection (DI) | Framework supplies required dependencies at runtime. | Spring Boot `@Autowired`, constructor injection | Reduced coupling, easier configuration |
| MVC (Model‑View‑Controller) | Separates input logic, business logic, and UI rendering. | Controllers (presentation) + Services (model) | Improves maintainability |
| CQRS (Command Query Responsibility Segregation) | Separates write (command) and read (query) models. | `ActionServiceImpl` (commands) vs. read‑only endpoints | Optimised read/write performance |
| Scheduler / Job Pattern | Executes background tasks on a schedule or asynchronously. | `JobServiceImpl`, `ReencryptionJobRestServiceImpl` | Off‑load long‑running work, improve responsiveness |
| Security Filter Chain | Centralised request authentication/authorization. | `CustomMethodSecurityExpressionHandler`, JWT filters | Consistent security enforcement |
| OpenAPI Documentation | Generates machine‑readable API specifications. | `OpenApiConfig`, `OpenApiOperationAuthorizationRightCustomizer` | Improves developer experience, enables client generation |
| Bulk Processing Pattern | Handles large data sets in batches. | `SuccessorBatchEntity`, `ArchiveManagerServiceImpl` | Efficient resource utilisation |
| Event‑Driven Architecture | Uses events to decouple components. | `ActionStreamEntity`, asynchronous workers | Scalability, loose coupling |
