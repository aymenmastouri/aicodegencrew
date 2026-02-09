# 12 – Glossary

---

## 12.1 Business Terms

The following table lists the domain‑specific business terms that appear in the UVZ system.  Terms are derived from **entity** names (domain model) and **service** names (application logic).  For each term we provide a concise definition and reference the components that primarily implement or manipulate the concept.

| Term | Definition | Related Components |
|------|------------|--------------------|
| **Action** | An operation that can be performed on a deed or handover, e.g., create, update, delete. | `ActionEntity`, `ActionServiceImpl`, `ActionRestServiceImpl` |
| **ActionStream** | A continuous flow of actions used for audit and event sourcing. | `ActionStreamEntity`, `ActionWorkerService` |
| **Change** | Modification record of a deed or handover data. | `ChangeEntity`, `CorrectionNoteService`, `ApplyCorrectionNoteService` |
| **Connection** | Logical link between deed entries, representing relationships such as predecessor‑successor. | `ConnectionEntity`, `DeedEntryConnectionServiceImpl`, `DeedEntryConnectionRestServiceImpl` |
| **CorrectionNote** | A note attached to a deed entry to correct data after submission. | `CorrectionNoteEntity`, `CorrectionNoteService`, `ApplyCorrectionNoteService` |
| **DeedEntry** | Core business object representing a single deed record in the registry. | `DeedEntryEntity`, `DeedEntryServiceImpl`, `DeedEntryRestServiceImpl` |
| **DeedRegistry** | Collection of all deed entries; provides locking and batch operations. | `DeedRegistryLockEntity`, `DeedRegistryServiceImpl`, `DeedRegistryRestServiceImpl` |
| **DeedType** | Classification of deeds (e.g., inheritance, donation). | `DeedTypeServiceImpl`, `DeedTypeRestServiceImpl` |
| **DocumentMetaData** | Metadata describing a document attached to a deed (size, hash, type). | `DocumentMetaDataEntity`, `DocumentMetaDataServiceImpl`, `DocumentMetaDataRestServiceImpl` |
| **HandoverDataSet** | Set of data required to transfer a deed from one authority to another. | `HandoverDataSetEntity`, `HandoverDataSetServiceImpl`, `HandoverDataSetRestServiceImpl` |
| **Participant** | Person or legal entity taking part in a deed (owner, successor, notary). | `ParticipantEntity`, `ParticipantServiceImpl` |
| **Registration** | Official recording of a deed in the land register. | `RegistrationEntity`, `RegistrationServiceImpl` |
| **Remark** | Free‑form comment attached to a deed for internal use. | `RemarkEntity`, `RemarkServiceImpl` |
| **SignatureInfo** | Information about the digital signature applied to a document. | `SignatureInfoEntity`, `SignatureFolderServiceImpl` |
| **Successor** | The entity that receives rights from a deed (e.g., heir). | `SuccessorDetailsEntity`, `SuccessorSelectionTextEntity`, `SuccessorBatchEntity` |
| **UVZNumber** | Unique identifier assigned to each deed entry within the UVZ system. | `UvzNumberManagerEntity`, `UvzNumberGapManagerEntity`, `UvzNumberSkipManagerEntity` |
| **Job** | Background processing unit (e.g., re‑encryption, archiving). | `JobEntity`, `JobServiceImpl`, `JobRestServiceImpl` |
| **BusinessPurpose** | The purpose for which a deed is created (e.g., inheritance, donation). | `BusinessPurposeServiceImpl`, `BusinessPurposeRestServiceImpl` |
| **KeyManager** | Component responsible for cryptographic key handling and re‑encryption. | `KeyManagerServiceImpl`, `KeyManagerRestServiceImpl` |
| **Archiving** | Process of moving completed documents to long‑term storage. | `ArchivingServiceImpl`, `ArchivingRestServiceImpl`, `ArchivingOperationSignerImpl` |
| **Report** | Generated statistical or compliance document based on deed data. | `ReportServiceImpl`, `ReportRestServiceImpl` |
| **NumberManagement** | Service that validates and formats UVZ numbers. | `NumberManagementServiceImpl`, `NumberManagementRestServiceImpl` |
| **Task** | Unit of work in the workflow engine (e.g., approval, signing). | `TaskServiceImpl`, `TaskRestServiceImpl` |
| **Workflow** | Orchestrated sequence of tasks that a deed passes through. | `WorkflowServiceImpl`, `WorkflowRestServiceImpl` |
| **Guard** | Security guard that protects routes based on authentication/authorization. | `GuardComponent` |
| **Scheduler** | Component that triggers periodic jobs (e.g., cleanup, retry). | `SchedulerComponent` |
| **Adapter** | Bridge between external systems (e.g., external key manager) and internal services. | `AdapterComponent` |
| **Interceptor** | Spring interceptor used for request/response manipulation. | `InterceptorComponent` |
| **Resolver** | GraphQL or REST resolver translating API calls to service calls. | `ResolverComponent` |

---

## 12.2 Technical Terms

| Term | Definition | Context |
|------|------------|---------|
| **Spring Boot** | Convention‑over‑configuration framework for building Java microservices. | Used for all backend services and controllers. |
| **REST** | Architectural style for stateless client‑server communication using HTTP verbs. | All `*RestServiceImpl` controllers expose REST endpoints. |
| **HTTP** | Protocol used for request/response exchange over the web. | Underlies all API calls listed in the interface section. |
| **JWT** | JSON Web Token, a compact, URL‑safe means of representing claims for authentication. | Used by `JsonAuthorizationRestServiceImpl` and security guards. |
| **OAuth2** | Authorization framework enabling third‑party access delegation. | Integrated via Spring Security configuration. |
| **DTO** | Data Transfer Object, a plain object used to carry data between layers. | Frequently returned by service methods and REST controllers. |
| **JPA** | Java Persistence API, standard for ORM mapping to relational databases. | Underpins all `*Entity` and `*Repository` implementations. |
| **Repository Pattern** | Abstraction that mediates between domain and data mapping layers. | Implemented by `*Repository` components. |
| **Service Layer** | Application‑level layer that contains business logic. | All `*ServiceImpl` classes belong here. |
| **Controller Layer** | Presentation layer exposing HTTP endpoints. | All `*RestServiceImpl` and `*Controller` classes. |
| **Adapter Pattern** | Allows incompatible interfaces to work together. | Implemented by `AdapterComponent` classes. |
| **Interceptor** | Mechanism to intercept HTTP requests/responses for cross‑cutting concerns. | Implemented by `InterceptorComponent`. |
| **Guard** | Route guard that checks authentication/authorization before navigation. | Implemented by `GuardComponent`. |
| **Scheduler** | Component that runs jobs on a timed schedule. | Implemented by `SchedulerComponent`. |
| **GraphQL** | Query language for APIs (optional, used by resolvers). | `ResolverComponent` may expose GraphQL endpoints. |
| **Docker** | Containerisation platform used for deployment. | Mentioned in deployment diagrams (not shown here). |
| **Kubernetes** | Orchestration system for containerised workloads. | Used in the runtime and deployment views. |
| **CI/CD** | Continuous Integration / Continuous Deployment pipelines. | Part of the DevOps infrastructure. |
| **OpenAPI/Swagger** | Specification for describing RESTful APIs. | Generated by `OpenApiConfig`. |
| **Playwright** | End‑to‑end testing framework for UI. | Used in the front‑end test suite. |
| **Angular** | Front‑end framework for the UI layer. | Not part of the back‑end glossary but referenced in technology stack. |

---

## 12.3 Abbreviations

| Abbreviation | Full Form | Context |
|--------------|-----------|---------|
| **UVZ** | *Umsatz‑Verzeichnis‑Zentral* (system name) | Overall system identifier. |
| **API** | Application Programming Interface | REST endpoints listed in the interface section. |
| **DTO** | Data Transfer Object | Used between service and controller layers. |
| **JPA** | Java Persistence API | ORM for entity persistence. |
| **CRUD** | Create, Read, Update, Delete | Basic operations exposed by REST services. |
| **JWT** | JSON Web Token | Authentication token format. |
| **OAuth** | Open Authorization | Delegated authentication protocol. |
| **CI** | Continuous Integration | Build pipeline stage. |
| **CD** | Continuous Deployment | Release pipeline stage. |
| **UI** | User Interface | Angular front‑end. |
| **DB** | Database | Underlying relational store for entities. |
| **REST** | Representational State Transfer | Architectural style of the API. |
| **HTTP** | Hypertext Transfer Protocol | Transport protocol for API calls. |
| **SQL** | Structured Query Language | Used by repositories for data access. |
| **K8s** | Kubernetes | Container orchestration platform. |
| **DI** | Dependency Injection | Spring framework feature. |
| **POJO** | Plain Old Java Object | Base class for entities and DTOs. |
| **IDE** | Integrated Development Environment | Development tooling (e.g., IntelliJ). |
| **DSL** | Domain‑Specific Language | Used in configuration files (e.g., Gradle). |

---

## 12.4 Architecture Patterns

| Pattern | Definition | Where Used | Benefit |
|---------|------------|------------|--------|
| **Layered Architecture** | Separation of concerns into presentation, application, domain, and data‑access layers. | Presentation (`*Controller`, `*RestServiceImpl`), Application (`*ServiceImpl`), Domain (`*Entity`), Data‑Access (`*Repository`). | Improves maintainability and testability. |
| **Repository Pattern** | Provides a collection‑like interface for accessing domain objects. | All `*Repository` components. | Decouples business logic from persistence details. |
| **Service Layer Pattern** | Encapsulates business logic in reusable services. | All `*ServiceImpl` classes. | Centralises rules, reduces duplication. |
| **Controller (Facade) Pattern** | Exposes a simplified API to clients, delegating to services. | All `*RestServiceImpl` and `*Controller` classes. | Hides internal complexity, enables versioning. |
| **Adapter Pattern** | Converts one interface to another to enable integration with external systems. | `AdapterComponent` classes (e.g., external key manager adapters). | Allows reuse of existing components without modification. |
| **Interceptor Pattern** | Intercepts requests/responses for cross‑cutting concerns (logging, security). | `InterceptorComponent`. | Centralises cross‑cutting logic, reduces boilerplate. |
| **Guard (Route Guard) Pattern** | Prevents navigation to protected resources without proper authorization. | `GuardComponent`. | Enhances security at the routing level. |
| **Scheduler Pattern** | Executes recurring background jobs. | `SchedulerComponent`. | Automates maintenance tasks (e.g., retries). |
| **Configuration Pattern** | Externalises configuration into dedicated classes/files. | `ConfigurationComponent`. | Enables environment‑specific settings without code changes. |
| **OpenAPI/Swagger Documentation** | Generates machine‑readable API specifications from code annotations. | `OpenApiConfig`, `OpenApiOperationAuthorizationRightCustomizer`. | Improves API discoverability and client generation. |
| **Circuit Breaker (Implied)** | Protects downstream services from failure cascades. | Potentially used in `KeyManagerServiceImpl` when calling external key services. | Increases resilience. |
| **Event‑Driven (Implicit via ActionStream)** | Publishes domain events for asynchronous processing. | `ActionStreamEntity`, `ActionWorkerService`. | Enables loose coupling and scalability. |

---

*All tables above are derived from the actual component names, relations and REST interface definitions present in the UVZ code base.*
