# 12 Glossary

## 12.1 Business Terms

| Term | Definition | Related Components |
|------|------------|--------------------|
| ActionEntity | Represents an action performed within the system, storing its type and timestamp. | ActionEntity, ActionServiceImpl |
| ActionStreamEntity | Captures a stream of actions for audit trails. | ActionStreamEntity, ActionServiceImpl |
| ChangeEntity | Records a change request on a deed or document. | ChangeEntity, CorrectionNoteService |
| ConnectionEntity | Models a connection between participants in a handover process. | ConnectionEntity, DeedEntryConnectionServiceImpl |
| CorrectionNoteEntity | Holds correction notes applied to documents. | CorrectionNoteEntity, CorrectionNoteService |
| DeedCreatorHandoverInfoEntity | Stores handover information created by the deed creator. | DeedCreatorHandoverInfoEntity, HandoverDataSetServiceImpl |
| DeedEntryEntity | Core entity representing a deed entry record. | DeedEntryEntity, DeedEntryServiceImpl |
| DeedEntryLockEntity | Represents a lock on a deed entry to prevent concurrent modifications. | DeedEntryLockEntity, DeedEntryServiceImpl |
| DeedEntryLogEntity | Audit log for actions performed on a deed entry. | DeedEntryLogEntity, DeedEntryLogServiceImpl |
| DeedRegistryLockEntity | Lock entity for the deed registry during batch operations. | DeedRegistryLockEntity, DeedRegistryServiceImpl |
| DocumentMetaDataEntity | Stores metadata about documents such as type, creation date, and owner. | DocumentMetaDataEntity, DocumentMetaDataServiceImpl |
| FinalHandoverDataSetEntity | Finalized data set used for handover to external systems. | FinalHandoverDataSetEntity, HandoverDataSetServiceImpl |
| HandoverDataSetEntity | Intermediate data set for handover processes. | HandoverDataSetEntity, HandoverDataSetServiceImpl |
| HandoverDmdWorkEntity | Represents work items related to handover demand management. | HandoverDmdWorkEntity, HandoverDataSetServiceImpl |
| HandoverHistoryDeedEntity | Historical record of deed handovers. | HandoverHistoryDeedEntity, HandoverHistoryEntity |
| HandoverHistoryEntity | General history of handover activities. | HandoverHistoryEntity, HandoverDataSetServiceImpl |
| IssuingCopyNoteEntity | Stores notes related to issuing copies of documents. | IssuingCopyNoteEntity, DocumentMetaDataServiceImpl |
| ParticipantEntity | Represents a participant (person or organization) in a deed. | ParticipantEntity, DeedEntryServiceImpl |
| RegistrationEntity | Captures registration details for a deed. | RegistrationEntity, DeedRegistryServiceImpl |
| RemarkEntity | Generic remark attached to various domain objects. | RemarkEntity, DocumentMetaDataServiceImpl |
| SignatureInfoEntity | Holds information about signatures on documents. | SignatureInfoEntity, SignatureFolderServiceImpl |
| SuccessorBatchEntity | Batch information for successor processing. | SuccessorBatchEntity, SuccessorDetailsEntity |
| SuccessorDeedSelectionEntity | Selection criteria for successor deeds. | SuccessorDeedSelectionEntity, SuccessorDetailsEntity |
| SuccessorDeedSelectionMetaEntity | Metadata for successor deed selection. | SuccessorDeedSelectionMetaEntity, SuccessorDetailsEntity |
| SuccessorDetailsEntity | Detailed information about a successor deed. | SuccessorDetailsEntity, SuccessorSelectionTextEntity |
| SuccessorSelectionTextEntity | Textual description used during successor selection. | SuccessorSelectionTextEntity, SuccessorDetailsEntity |
| UvzNumberGapManagerEntity | Manages gaps in UVZ number sequences. | UvzNumberGapManagerEntity, NumberManagementServiceImpl |
| UvzNumberManagerEntity | Handles allocation of UVZ numbers. | UvzNumberManagerEntity, NumberManagementServiceImpl |
| UvzNumberSkipManagerEntity | Manages skipped UVZ numbers. | UvzNumberSkipManagerEntity, NumberManagementServiceImpl |
| JobEntity | Represents a background job scheduled in the system. | JobEntity, JobServiceImpl |
| ActionServiceImpl | Service implementing business logic for actions. | ActionServiceImpl, ActionEntity |
| ActionWorkerService | Background worker handling asynchronous action processing. | ActionWorkerService, ActionEntity |
| HealthCheck | Provides health status of the application for monitoring. | HealthCheck, HealthCheck (exposed via REST) |
| ArchiveManagerServiceImpl | Manages archiving operations and storage lifecycle. | ArchiveManagerServiceImpl, ArchiveManagerServiceImpl |
| MockKmService | Mock implementation of the Key Management service for testing. | MockKmService, KeyManagerServiceImpl |
| XnpKmServiceImpl | Production implementation of the Key Management service. | XnpKmServiceImpl, KeyManagerServiceImpl |
| KeyManagerServiceImpl | Central service for cryptographic key handling. | KeyManagerServiceImpl, SignatureFolderServiceImpl |
| WaWiServiceImpl | Service for handling WaWi (document exchange) operations. | WaWiServiceImpl, DeedWaWiServiceImpl |
| ArchivingOperationSignerImpl | Signs archiving operations to ensure integrity. | ArchivingOperationSignerImpl, ArchiveManagerServiceImpl |
| ArchivingServiceImpl | Core service for archiving documents and metadata. | ArchivingServiceImpl, ArchiveManagerServiceImpl |
| DeedEntryConnectionDaoImpl | Data access object for deed entry connections. | DeedEntryConnectionDaoImpl, DeedEntryConnectionServiceImpl |
| DeedEntryLogsDaoImpl | DAO for deed entry logs. | DeedEntryLogsDaoImpl, DeedEntryLogServiceImpl |
| DocumentMetaDataCustomDaoImpl | Custom DAO for advanced document metadata queries. | DocumentMetaDataCustomDaoImpl, DocumentMetaDataServiceImpl |
| HandoverDataSetDaoImpl | DAO for handover data set persistence. | HandoverDataSetDaoImpl, HandoverDataSetServiceImpl |
| ApplyCorrectionNoteService | Service applying correction notes to documents. | ApplyCorrectionNoteService, CorrectionNoteService |
| BusinessPurposeServiceImpl | Handles business purpose classification for deeds. | BusinessPurposeServiceImpl, DeedEntryServiceImpl |
| CorrectionNoteService | Service managing correction notes lifecycle. | CorrectionNoteService, CorrectionNoteEntity |
| DeedEntryConnectionServiceImpl | Service managing connections between deed entries. | DeedEntryConnectionServiceImpl, ConnectionEntity |
| DeedEntryLogServiceImpl | Service for logging deed entry actions. | DeedEntryLogServiceImpl, DeedEntryLogEntity |
| DeedEntryServiceImpl | Core service for CRUD operations on deed entries. | DeedEntryServiceImpl, DeedEntryEntity |
| DeedRegistryServiceImpl | Service handling deed registry operations. | DeedRegistryServiceImpl, RegistrationEntity |
| DeedTypeServiceImpl | Service providing deed type lookup and validation. | DeedTypeServiceImpl, DeedEntryEntity |
| DeedWaWiOrchestratorServiceImpl | Orchestrates WaWi processes across multiple services. | DeedWaWiOrchestratorServiceImpl, WaWiServiceImpl |
| DeedWaWiServiceImpl | Service for WaWi specific deed handling. | DeedWaWiServiceImpl, WaWiServiceImpl |
| DocumentMetaDataServiceImpl | Service exposing document metadata via API. | DocumentMetaDataServiceImpl, DocumentMetaDataEntity |
| HandoverDataSetServiceImpl | Service managing handover data sets lifecycle. | HandoverDataSetServiceImpl, HandoverDataSetEntity |
| SignatureFolderServiceImpl | Service for storing and retrieving signature files. | SignatureFolderServiceImpl, SignatureInfoEntity |
| ReportServiceImpl | Generates reports on deeds, handovers, and audits. | ReportServiceImpl, Report endpoints |
| JobServiceImpl | Executes scheduled background jobs. | JobServiceImpl, JobEntity |
| NumberManagementServiceImpl | Manages UVZ number allocation and gaps. | NumberManagementServiceImpl, UvzNumberManagerEntity |

## 12.2 Technical Terms

| Term | Definition | Context |
|------|------------|---------|
| Spring Boot | Java framework that simplifies creation of stand‑alone, production‑grade Spring applications. | Used for all backend services (e.g., `ActionServiceImpl`). |
| Angular | Front‑end web application platform based on TypeScript. | Powers the UI layer (presentation components). |
| REST | Representational State Transfer, an architectural style for stateless client‑server communication. | Implemented by `rest_interface` components exposing HTTP endpoints. |
| Repository Pattern | Encapsulates data access logic, providing a collection‑like interface to domain objects. | Realised by `*Repository` and `*DaoImpl` components. |
| Service Layer | Provides an API for business logic, decoupling controllers from domain model. | Implemented by all `*ServiceImpl` components. |
| Controller (MVC) | Handles HTTP requests, maps them to service calls, and returns responses. | Implemented by `*Controller` components. |
| Dependency Injection | Technique where an object receives its dependencies from an external source rather than creating them. | Core to Spring Boot's bean management. |
| Adapter Pattern | Allows incompatible interfaces to work together via a wrapper. | Used by `adapter` components bridging external systems. |
| Guard | Security construct that checks permissions before route activation. | Implemented by the single `guard` component in the UI layer. |
| Interceptor | Intercepts requests/responses to apply cross‑cutting concerns (e.g., logging). | Implemented by `interceptor` components in the backend. |
| Scheduler | Executes recurring background jobs at defined intervals. | Implemented by the single `scheduler` component. |
| Configuration | Centralised definition of application settings and beans. | Implemented by the `configuration` component. |
| Node.js | JavaScript runtime used for tooling and test automation (e.g., Playwright). | Supports end‑to‑end test execution. |
| Playwright | Automated browser testing framework. | Used for UI integration tests. |
| Gradle | Build automation tool for Java projects. | Manages compilation, testing, and packaging. |

## 12.3 Abbreviations

| Abbreviation | Full Form | Context |
|--------------|-----------|---------|
| API | Application Programming Interface | REST endpoints exposed by controllers. |
| CRUD | Create, Read, Update, Delete | Basic operations provided by service layer. |
| DTO | Data Transfer Object | Objects used to transport data between layers. |
| UI | User Interface | Angular front‑end components. |
| DB | Database | Persistence layer accessed via repositories. |
| JVM | Java Virtual Machine | Runtime for Spring Boot services. |
| CI | Continuous Integration | Build pipeline using Gradle. |
| CD | Continuous Deployment | Automated deployment of backend services. |
| JWT | JSON Web Token | Used for authentication in REST calls. |
| TLS | Transport Layer Security | Secures HTTP communication. |
| OSS | Open Source Software | Libraries such as Spring, Angular, Playwright. |
| SLA | Service Level Agreement | Defined for health‑check and uptime. |
| BPM | Business Process Management | Governs handover workflows. |
| DDD | Domain‑Driven Design | Influences entity and service naming. |
| MVC | Model‑View‑Controller | Architectural pattern for UI layer. |
| OOP | Object‑Oriented Programming | Paradigm used throughout Java codebase. |

## 12.4 Architecture Patterns

| Pattern | Definition | Where Used | Benefit |
|---------|------------|------------|---------|
| Layered Architecture | Organises system into horizontal layers (presentation, application, domain, data‑access, infrastructure). | All components are grouped by layer in the architecture summary. | Clear separation of concerns, easier maintenance. |
| Repository Pattern | Abstracts data‑access logic behind a collection‑like interface. | All `*Repository` and `*DaoImpl` components. | Decouples domain model from persistence technology. |
| Service Layer | Centralises business logic in services, exposing a cohesive API. | All `*ServiceImpl` components. | Promotes reuse and testability. |
| MVC (Model‑View‑Controller) | Separates input logic, business logic, and UI rendering. | Angular components (View), Controllers (Controller), Entities (Model). | Improves UI modularity and testability. |
| Adapter Pattern | Allows integration with external systems via a compatible interface. | `adapter` components bridging to legacy systems or third‑party APIs. | Enables flexible integration without changing core logic. |
| Guard / Interceptor Pattern | Implements cross‑cutting concerns such as security and logging. | Single `guard` component (UI) and `interceptor` components (backend). | Centralised handling of non‑functional requirements. |
| Scheduler / Quartz Pattern | Executes periodic background jobs. | Single `scheduler` component managing `JobEntity` processing. | Automates routine maintenance tasks. |
| Configuration Pattern | Externalises configuration values from code. | `configuration` component providing beans and properties. | Simplifies environment‑specific deployments. |
| RESTful API Pattern | Exposes resources via stateless HTTP methods following REST conventions. | All `rest_interface` components and generated OpenAPI specs. | Enables interoperable client‑server communication. |
| Dependency Injection | Provides required dependencies to objects at runtime. | Spring Boot container managing beans across all layers. | Reduces coupling and improves testability.
