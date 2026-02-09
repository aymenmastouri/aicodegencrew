# 12 – Glossary

---

## 12.1 Business Terms (≈ 2 pages)

| Term | Definition | Related Components |
|------|------------|--------------------|
| **Action** | A discrete operation performed on a deed or document, such as creation, modification, or deletion. | `ActionEntity`, `ActionServiceImpl`, `ActionRestServiceImpl` |
| **Deed** | The core legal record representing a property transaction. It aggregates several sub‑entities (e.g., `DeedEntryEntity`, `DeedRegistryLockEntity`). | `DeedEntryEntity`, `DeedEntryServiceImpl`, `DeedRegistryRestServiceImpl` |
| **Deed Entry** | A single line item within a deed, containing details like participant, amount, and timestamps. | `DeedEntryEntity`, `DeedEntryServiceImpl`, `DeedEntryRestServiceImpl` |
| **Participant** | An actor (person or organization) that takes part in a deed transaction. | `ParticipantEntity`, `DeedEntryServiceImpl` |
| **Signature Info** | Cryptographic data that proves the authenticity of a deed or its parts. | `SignatureInfoEntity`, `SignatureFolderServiceImpl` |
| **Handover Data Set** | A collection of data required to transfer ownership from one party to another. | `HandoverDataSetEntity`, `HandoverDataSetServiceImpl`, `HandoverDataSetRestServiceImpl` |
| **Correction Note** | An amendment record that corrects errors in previously stored deed data. | `CorrectionNoteEntity`, `ApplyCorrectionNoteService`, `CorrectionNoteService` |
| **Number Management** | The subsystem responsible for generating, reserving, and skipping UVZ numbers. | `UvzNumberManagerEntity`, `UvzNumberSkipManagerEntity`, `NumberManagementServiceImpl`, `NumberManagementRestServiceImpl` |
| **Job** | A scheduled or on‑demand background task (e.g., archiving, re‑encryption). | `JobEntity`, `JobServiceImpl`, `JobRestServiceImpl` |
| **Report** | Aggregated information extracted from deeds for analytics or regulatory purposes. | `ReportServiceImpl`, `ReportRestServiceImpl` |
| **Archive** | Long‑term storage of immutable deed records. | `ArchiveManagerServiceImpl`, `ArchivingServiceImpl`, `ArchivingRestServiceImpl` |
| **Health Check** | A lightweight endpoint used by monitoring tools to verify service availability. | `HealthCheck` |
| **Key Manager** | Handles cryptographic key lifecycle for signing and encryption. | `KeyManagerServiceImpl`, `KeyManagerRestServiceImpl` |
| **WaWi** | Abbreviation for *Warenwirtschaft* (inventory management) – used in the context of deed‑related inventory data. | `WaWiServiceImpl`, `DeedWaWiServiceImpl`, `DeedWaWiOrchestratorServiceImpl` |
| **Notary Representation** | Data structure that represents the notary’s role in a deed transaction. | `NotaryRepresentationRestServiceImpl` |
| **Official Activity Metadata** | Metadata describing official activities linked to a deed (e.g., registration, publication). | `OfficialActivityMetadataRestServiceImpl` |
| **Report Metadata** | Descriptive information about generated reports (type, period, status). | `ReportMetadataRestServiceImpl` |
| **Document Meta Data** | Information about a document (title, version, creation date) stored alongside the deed. | `DocumentMetaDataEntity`, `DocumentMetaDataServiceImpl`, `DocumentMetaDataRestServiceImpl` |
| **Successor Details** | Information about the next owner(s) of a deed after a handover. | `SuccessorDetailsEntity`, `SuccessorDeedSelectionEntity` |
| **Uvz Number Gap Manager** | Component that detects and resolves gaps in the sequential UVZ number series. | `UvzNumberGapManagerEntity` |
| **Action Stream** | Real‑time feed of actions performed on deeds, used for audit and monitoring. | `ActionStreamEntity` |
| **Change** | Generic term for any modification applied to a deed or its related entities. | `ChangeEntity` |
| **Connection** | Logical link between two deed entries (e.g., parent‑child relationship). | `ConnectionEntity`, `DeedEntryConnectionServiceImpl` |
| **Remark** | Free‑form comment attached to a deed for internal notes. | `RemarkEntity` |
| **Scheduler** | Component that triggers periodic jobs such as number gap checks. | `Scheduler` |
| **Guard** | Security component that protects routes or services. | `Guard` |
| **Adapter** | Bridge component that translates between external systems and internal domain models. | `Adapter` |
| **Resolver** | GraphQL or similar component that resolves data for API queries. | `Resolver` |
| **Interceptor** | Spring component that intercepts HTTP requests for cross‑cutting concerns (e.g., logging). | `Interceptor` |

*The table lists the most frequently used business terms extracted from the domain model (entities) and the application layer (services & controllers). The related components column references the concrete Java classes that implement the term.*

---

## 12.2 Technical Terms (≈ 2 pages)

| Term | Definition | Context |
|------|------------|---------|
| **REST** | Representational State Transfer – architectural style for stateless client‑server communication using HTTP verbs. | Used by all `*RestServiceImpl` controllers; defined in `OpenApiConfig`. |
| **DTO** | Data Transfer Object – lightweight object used to carry data between processes. | Frequently returned by controller methods (e.g., `ActionRestServiceImpl`). |
| **JPA** | Java Persistence API – specification for object‑relational mapping. | Underlies all `*Entity` classes and repository implementations. |
| **Spring Boot** | Convention‑over‑configuration framework that simplifies creation of stand‑alone Spring applications. | The whole backend is built on Spring Boot 2.x. |
| **Dependency Injection (DI)** | Design pattern where an object receives its dependencies from an external source rather than creating them itself. | Managed by Spring’s IoC container; visible in `@Autowired` services. |
| **Layered Architecture** | Architectural pattern that separates concerns into distinct layers (presentation, application, domain, data‑access). | Reflected in the component distribution shown in the architecture summary. |
| **Repository Pattern** | Abstraction that mediates between domain and data‑mapping layers, providing collection‑like interfaces for accessing domain objects. | Implemented by `*Repository` and `*DaoImpl` classes. |
| **Service Layer** | Layer that contains business logic and orchestrates domain objects. | Implemented by all `*ServiceImpl` classes. |
| **Scheduler** | Component that executes tasks at predefined intervals (e.g., number‑gap detection). | Implemented by the single `Scheduler` component. |
| **Guard** | Security construct that protects routes or methods, typically used in Angular front‑end but also represented in backend security configuration. | `Guard` component and `CustomMethodSecurityExpressionHandler`. |
| **Interceptor** | Mechanism to intercept HTTP requests/responses for cross‑cutting concerns (logging, authentication). | Implemented by `Interceptor` components. |
| **Adapter** | Pattern that allows incompatible interfaces to work together. | `Adapter` components translate external system messages into internal domain events. |
| **Resolver** | Component (often in GraphQL) that resolves a field’s value by fetching data from underlying services. | `Resolver` components present in the unknown layer. |
| **OpenAPI** | Specification for describing RESTful APIs, enabling automatic documentation and client generation. | Configured in `OpenApiConfig` and customized by `OpenApiOperationAuthorizationRightCustomizer`. |
| **Health Endpoint** | Minimal endpoint (`/actuator/health`) used by orchestration platforms to check service health. | Implemented by `HealthCheck`. |
| **CRUD** | Create, Read, Update, Delete – basic operations on persistent storage. | Exposed by most `*RestServiceImpl` controllers. |
| **DTO Validation** | Use of Bean Validation (`@Valid`, `@NotNull`, etc.) to ensure incoming request payloads meet constraints. | Applied in controller method parameters. |
| **Logging** | Systematic recording of runtime events for monitoring and debugging. | Implemented via Spring’s logging framework and custom interceptors. |
| **Exception Handling** | Centralized mechanism to translate exceptions into HTTP responses. | Implemented by `DefaultExceptionHandler`. |

---

## 12.3 Abbreviations (≈ 1 page)

| Abbreviation | Full Form | Context |
|--------------|-----------|---------|
| **API** | Application Programming Interface | Used by all REST controllers (`*RestServiceImpl`). |
| **DTO** | Data Transfer Object | Returned by controllers, consumed by front‑end. |
| **JPA** | Java Persistence API | Underlies entity‑repository mapping. |
| **UVZ** | *Umsatz‑Verzeichnis‑Zähler* (system‑specific identifier) | Managed by `UvzNumberManagerEntity` and related services. |
| **REST** | Representational State Transfer | Architectural style of the public API. |
| **CRUD** | Create, Read, Update, Delete | Basic operations on entities. |
| **DI** | Dependency Injection | Spring’s IoC container. |
| **IoC** | Inversion of Control | Spring framework principle. |
| **SQL** | Structured Query Language | Used by repositories to query the relational database. |
| **HTML** | HyperText Markup Language | Served by `IndexHTMLResourceService`. |
| **CSS** | Cascading Style Sheets | Served as static content by `StaticContentController`. |
| **JS** | JavaScript | Served as static content. |
| **UI** | User Interface | Front‑end built with Angular. |
| **MVC** | Model‑View‑Controller | Architectural pattern of the presentation layer. |
| **WS** | Web Service | Generic term for REST endpoints. |
| **JWT** | JSON Web Token | Used for authentication in `TokenAuthenticationRestTemplateConfigurationSpringBoot`. |
| **ACL** | Access Control List | Managed by `CustomMethodSecurityExpressionHandler`. |
| **DB** | Database | Underlying persistence store for entities. |
| **CI** | Continuous Integration | Part of the DevOps pipeline (not represented in code). |
| **CD** | Continuous Delivery/Deployment | Part of the DevOps pipeline. |

---

## 12.4 Architecture Patterns (≈ 1‑2 pages)

| Pattern | Definition | Where Used | Benefit |
|---------|------------|------------|--------|
| **Layered Architecture** | Organises system into horizontal layers with defined responsibilities (presentation, application, domain, data‑access). | Presentation: controllers, directives, components. Application: services. Domain: entities. Data‑access: repositories. | Improves separation of concerns, eases maintenance and testing. |
| **Repository Pattern** | Provides a collection‑like interface for accessing domain objects, abstracting persistence details. | All `*Repository` and `*DaoImpl` classes. | Decouples domain logic from data‑store specifics, enables swapping DB implementations. |
| **Service Layer** | Encapsulates business logic and transaction management in a dedicated layer. | All `*ServiceImpl` classes. | Centralises business rules, reduces duplication across controllers. |
| **RESTful API** | Uses HTTP verbs and resource‑oriented URLs to expose functionality. | All `*RestServiceImpl` controllers, OpenAPI configuration. | Enables language‑agnostic client integration, leverages HTTP caching and tooling. |
| **Dependency Injection (DI)** | Objects receive their dependencies from an external container rather than constructing them. | Spring’s `@Autowired` in services, controllers, repositories. | Improves testability, reduces coupling, simplifies configuration. |
| **Scheduler / Quartz‑like Pattern** | Executes recurring background jobs at defined intervals. | `Scheduler` component, `JobServiceImpl`, `ReencryptionJobRestServiceImpl`. | Automates maintenance tasks (e.g., number‑gap detection, archiving). |
| **Adapter Pattern** | Converts the interface of a class into another interface clients expect. | `Adapter` components that integrate external systems (e.g., external key‑manager). | Allows reuse of existing code without modification. |
| **Guard / Route‑Guard Pattern** | Prevents navigation to a route unless certain conditions are met (e.g., authentication). | `Guard` component, `CustomMethodSecurityExpressionHandler`. | Enhances security by enforcing access rules at the entry point. |
| **Interceptor Pattern** | Intercepts incoming requests/responses to apply cross‑cutting concerns. | `Interceptor` components, `DefaultExceptionHandler`. | Centralises logging, authentication, error handling. |
| **OpenAPI / Swagger Documentation** | Generates interactive API documentation from annotations. | `OpenApiConfig`, `OpenApiOperationAuthorizationRightCustomizer`. | Improves developer experience, enables client code generation. |
| **Exception Mapping** | Translates internal exceptions into standardized HTTP error responses. | `DefaultExceptionHandler`. | Provides consistent error handling across the API. |
| **Configuration as Code** | Stores configuration (e.g., security, proxy) in version‑controlled source files. | `ProxyRestTemplateConfiguration`, `TokenAuthenticationRestTemplateConfigurationSpringBoot`. | Enables reproducible environments and easier changes. |

---

*All patterns listed above have been identified directly from the component distribution, naming conventions, and configuration classes present in the code base.*

---

*End of Chapter 12 – Glossary*