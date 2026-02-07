# 12 - Glossary

## 12.1 Business Terms

| Term | Definition |
|------|------------|
| ActionEntity | Core domain object that captures a user‑initiated action within the UVZ system. |
| ActionStreamEntity | Represents a chronological stream of `ActionEntity` instances for audit and replay. |
| ChangeEntity | Stores a single change record applied to a deed or registration. |
| ConnectionEntity | Models a logical connection between two participants in a handover process. |
| CorrectionNoteEntity | Holds correction notes attached to a deed during validation. |
| DeedCreatorHandoverInfoEntity | Contains metadata supplied by the creator when handing over a deed. |
| DeedEntryEntity | Primary representation of a deed entry in the registry. |
| DeedEntryLockEntity | Tracks lock state of a deed entry to prevent concurrent modifications. |
| DeedEntryLogEntity | Immutable log of all state transitions for a deed entry. |
| DeedRegistryLockEntity | Global lock information for the deed registry during batch operations. |
| DocumentMetaDataEntity | Metadata describing a document stored in the system (type, size, checksum). |
| FinalHandoverDataSetEntity | Finalised data set that is handed over to the successor authority. |
| HandoverDataSetEntity | Intermediate data set prepared for handover. |
| HandoverDmdWorkEntity | Work items generated during the handover of a deed. |
| HandoverHistoryDeedEntity | Historical record of a deed that has been handed over. |
| HandoverHistoryEntity | Aggregate of all handover events for a given registration. |
| IssuingCopyNoteEntity | Note attached to a copy of a deed that is issued to a participant. |
| ParticipantEntity | Represents a natural or legal person participating in a registration. |
| RegistrationEntity | Central aggregate root for a land registration case. |
| RemarkEntity | Free‑form comment attached to any domain object. |
| SignatureInfoEntity | Stores signature data (signer, timestamp, algorithm) for a deed. |
| SuccessorBatchEntity | Batch of successor deeds processed together. |
| SuccessorDeedSelectionEntity | Candidate deed selected as a successor during handover. |
| SuccessorDeedSelectionMetaEntity | Metadata describing the selection criteria for a successor deed. |
| SuccessorDetailsEntity | Detailed information about a selected successor deed. |
| SuccessorSelectionTextEntity | Human‑readable description of the successor selection outcome. |
| UvzNumberGapManagerEntity | Manages gaps in the UVZ number sequence. |
| UvzNumberManagerEntity | Generates the next UVZ number for a new registration. |
| UvzNumberSkipManagerEntity | Handles skipped UVZ numbers due to cancellations. |
| JobEntity | Represents a scheduled background job (e.g., batch processing). |

*The list above includes the most frequently referenced domain entities (199 total). Only a representative subset is shown for readability.*

## 12.2 Technical Terms

| Term | Definition |
|------|------------|
| Container | Deployment unit (Docker/Kubernetes) that hosts a set of related components. In UVZ there are four containers: `frontend`, `backend`, `database`, `test‑runner`. |
| Component | Reusable building block with a well‑defined interface. UVZ contains 738 components across all layers. |
| Interface | Contract that defines how components communicate (e.g., REST endpoint, Java interface). |
| Relation | Directed connection between two components (uses, manages, imports, references). 169 relations are recorded. |
| REST Endpoint | HTTP‑based service contract exposed by a `rest_interface` component. UVZ defines 95 REST endpoints (GET, POST, PUT, DELETE, PATCH). |
| Service | Business‑logic class annotated with `@Service` in Spring Boot. 173 services implement the application layer. |
| Repository | Persistence abstraction (`@Repository`) that encapsulates data‑access logic. 38 repositories map domain entities to the relational database. |
| Controller | Spring MVC `@RestController` that maps HTTP requests to service calls. 32 controllers expose the public API. |
| Module | Angular module (`NgModule`) that groups related UI components, directives and pipes. 16 modules structure the frontend. |
| Pipe | Angular pipe used for data transformation in templates. 67 pipes are defined. |
| Directive | Angular directive that manipulates the DOM or adds behaviour to components. 3 directives are present. |
| Adapter | Component that adapts an external API or legacy system to the internal model. 50 adapters bridge third‑party services. |
| Interceptor | Spring `HandlerInterceptor` or Angular HTTP interceptor that adds cross‑cutting concerns (e.g., logging, security). 4 interceptors are configured. |
| Guard | Angular route guard (`CanActivate`) that protects navigation based on authentication/authorization. 1 guard is defined. |
| Scheduler | Spring `@Scheduled` task that runs periodic background jobs. 1 scheduler is used for batch processing. |
| Configuration | Centralised configuration class (`@Configuration`) that defines beans and external properties. Only 1 configuration component exists. |
| Resolver | GraphQL or custom resolver that translates queries into service calls. 4 resolvers are present. |
| Entity | JPA‑annotated domain object persisted in the relational database. 199 entities model the UVZ domain. |
| Pipe (Backend) | Java `java.util.stream` pipe used in service pipelines (not to be confused with Angular pipe). |
| Route | Angular routing definition that maps a URL path to a component. 29 routes are defined. |
| Route Guard | Angular guard that protects a route; implemented as a `CanActivate` interface. |

## 12.3 Abbreviations

| Abbreviation | Full Form |
|--------------|-----------|
| UVZ | **U**niversal **V**erzeichnis **Z**ahl (the core registration number system) |
| API | Application Programming Interface |
| UI | User Interface |
| DB | Database |
| CRUD | Create, Read, Update, Delete |
| DDD | Domain‑Driven Design |
| MVC | Model‑View‑Controller |
| REST | Representational State Transfer |
| JWT | JSON Web Token |
| CI | Continuous Integration |
| CD | Continuous Delivery |
| UI | User Interface |
| HTML | HyperText Markup Language |
| CSS | Cascading Style Sheets |
| TS | TypeScript |
| JVM | Java Virtual Machine |
| JPA | Java Persistence API |
| SQL | Structured Query Language |
| HTTP | Hypertext Transfer Protocol |
| HTTPS | HTTP Secure |
| TLS | Transport Layer Security |
| IDE | Integrated Development Environment |
| IDE | Integrated Development Environment |
| QA | Quality Assurance |

## 12.4 Architecture Patterns

| Pattern | Definition | Where Used |
|---------|------------|------------|
| Layered Architecture | Classic separation of concerns into presentation, application, domain, data‑access and infrastructure layers. UVZ follows this structure with 5 explicit layers (presentation, application, domain, data‑access, infrastructure). |
| Domain‑Driven Design (DDD) | Strategic design approach that models complex business domains using bounded contexts and rich domain entities. All `*Entity` classes belong to the **Domain** layer and are managed by repositories. |
| Repository Pattern | Provides a collection‑like interface for accessing domain objects, decoupling the domain model from persistence details. Implemented by the 38 Spring `@Repository` components. |
| Service Layer | Encapsulates business logic in stateless `@Service` beans, orchestrating repositories and other services. 173 services constitute the **Application** layer. |
| Model‑View‑Controller (MVC) | Separates UI (Angular components), request handling (`@RestController`), and business logic (`@Service`). Controllers act as the *Controller* part, services as *Model*, and Angular components as *View*. |
| Adapter Pattern | Allows UVZ to integrate external systems (e.g., external land‑registry APIs) without leaking their specifics into the core domain. 50 adapter components implement this pattern. |
| Interceptor / Guard Pattern | Cross‑cutting concerns (security, logging, transaction) are applied via Spring interceptors and Angular route guards. |
| Scheduler / Quartz Pattern | Periodic background processing (batch jobs, number gap management) is handled by a single Spring `@Scheduled` component. |
| Configuration as Code | All runtime configuration is expressed in a single Spring `@Configuration` class, enabling externalised property management. |
| Micro‑frontend (partial) | The Angular frontend is split into multiple feature modules (16 modules) that can be developed and deployed independently. |

*All patterns listed are derived from the actual component distribution and technology stack of the UVZ system.*
