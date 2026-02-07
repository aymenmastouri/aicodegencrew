# 12 - Glossary

## 12.1 Business Terms

| Term | Definition |
|------|------------|
| ActionEntity | Represents a single action performed on a deed, storing timestamps and actor information. |
| ActionStreamEntity | Captures a chronological stream of actions related to a deed for audit purposes. |
| ChangeEntity | Holds details of a change request applied to a deed record. |
| ConnectionEntity | Models the relationship between participants in a deed transaction. |
| CorrectionNoteEntity | Stores notes describing corrections made to deed metadata. |
| DeedCreatorHandoverInfoEntity | Contains hand‑over information supplied by the creator of a deed. |
| DeedEntryEntity | Core domain object representing a deed entry in the registry. |
| DeedEntryLockEntity | Tracks lock state of a deed entry to prevent concurrent modifications. |
| DeedEntryLogEntity | Persistent log of all operations performed on a deed entry. |
| DeedRegistryLockEntity | Global lock used during batch registry operations. |
| DocumentMetaDataEntity | Holds metadata (type, size, checksum) for documents attached to deeds. |
| FinalHandoverDataSetEntity | Finalised data set prepared for hand‑over to the land registry. |
| HandoverDataSetEntity | Intermediate data set used during the hand‑over process. |
| HandoverDmdWorkEntity | Represents work items generated for a hand‑over demand. |
| HandoverHistoryDeedEntity | Historical record of a deed that has been handed over. |
| HandoverHistoryEntity | General history of hand‑over events for a deed. |
| IssuingCopyNoteEntity | Note attached to a copy of a deed that is issued to a participant. |
| ParticipantEntity | Domain object describing a participant (owner, buyer, authority) in a deed. |
| RegistrationEntity | Represents the registration event of a deed in the official register. |
| RemarkEntity | Free‑form comment attached to a deed for internal use. |
| SignatureInfoEntity | Stores information about signatures (signer, method, timestamp) on a deed. |
| SuccessorBatchEntity | Batch of successor deeds generated during a succession process. |
| SuccessorDeedSelectionEntity | Temporary entity used while selecting successor deeds. |
| SuccessorDeedSelectionMetaEntity | Metadata describing the selection criteria for successor deeds. |
| SuccessorDetailsEntity | Detailed information about a successor deed. |
| SuccessorSelectionTextEntity | Textual description used in UI for successor selection. |
| UvzNumberGapManagerEntity | Manages gaps in the UVZ numbering sequence. |
| UvzNumberManagerEntity | Central manager for UVZ number allocation. |
| UvzNumberSkipManagerEntity | Handles skipped UVZ numbers due to cancellations. |
| JobEntity | Represents a scheduled background job (e.g., batch processing). |

## 12.2 Technical Terms

| Term | Definition |
|------|------------|
| Controller | Spring MVC component that receives HTTP requests, validates input and delegates to services. |
| Service | Business‑logic component (application layer) that orchestrates domain entities and repositories. |
| Repository | Data‑access component implementing persistence operations for entities (e.g., JPA repositories). |
| Entity | Domain object mapped to a database table (JPA @Entity). |
| Module | Angular or Spring module that groups related components, services and configuration. |
| Component | UI building block in Angular or a reusable Spring bean. |
| Pipe | Angular pipe used to transform data in templates. |
| Directive | Angular directive that manipulates DOM behaviour. |
| Adapter | Structural component that adapts external APIs to internal models. |
| Guard | Angular route guard that protects navigation based on authentication/authorization. |
| Interceptor | Spring or Angular interceptor that intercepts requests/responses for cross‑cutting concerns. |
| Resolver | Angular resolver that pre‑fetches data before route activation. |
| Scheduler | Spring @Scheduled component that runs periodic background jobs. |
| Configuration | Spring @Configuration class that defines beans and externalised settings. |
| REST Interface | Public HTTP API exposing resources via standard REST verbs (GET, POST, PUT, DELETE, PATCH). |
| Route | Angular routing definition mapping a URL path to a component. |
| Route Guard | Mechanism that decides whether a route can be activated based on runtime checks. |
| DTO (Data Transfer Object) | Lightweight object used to transfer data between layers without exposing domain entities. |
| CRUD | Acronym for Create, Read, Update, Delete – basic data‑manipulation operations. |
| DI (Dependency Injection) | Design pattern used by Spring and Angular to inject required collaborators at runtime. |

## 12.3 Abbreviations

| Abbreviation | Full Form |
|--------------|-----------|
| UVZ | Unique Vz (system name for the deed‑entry platform) |
| API | Application Programming Interface |
| UI | User Interface |
| DB | Database |
| JPA | Java Persistence API |
| MVC | Model‑View‑Controller |
| DTO | Data Transfer Object |
| CRUD | Create, Read, Update, Delete |
| DI | Dependency Injection |
| CI/CD | Continuous Integration / Continuous Delivery |
| QA | Quality Assurance |
| HTTP | Hypertext Transfer Protocol |
| JSON | JavaScript Object Notation |
| XML | eXtensible Markup Language |

## 12.4 Architecture Patterns

| Pattern | Definition | Where Used |
|---------|------------|------------|
| Layered Architecture | Organises the system into horizontal layers (Presentation, Application, Domain, Data Access, Infrastructure) with strict dependency direction. | All modules – presentation (controllers), application (services), domain (entities), data‑access (repositories), infrastructure (configuration). |
| MVC (Model‑View‑Controller) | Separates UI (View) from request handling (Controller) and business model (Model). | Angular front‑end and Spring MVC controllers. |
| Repository Pattern | Provides a collection‑like interface for accessing domain objects, abstracting persistence details. | Spring Data JPA repositories for all `*Entity` classes. |
| Service Layer | Encapsulates business use‑cases, coordinating multiple repositories and domain objects. | All `*ServiceImpl` components in the application layer (173 services). |
| Dependency Injection | Framework‑managed injection of required collaborators, promoting loose coupling. | Spring `@Autowired` and Angular DI containers. |
| Configuration‑as‑Code | Externalises configuration into code‑based classes or property files, enabling version control. | Single `Configuration` component in the infrastructure layer. |
| Scheduler / Batch Pattern | Executes recurring background jobs without manual intervention. | `JobEntity` processed by Spring `@Scheduled` components. |
| Guard / Interceptor Pattern | Implements cross‑cutting concerns such as security, logging, and validation. | Angular `Guard` for route protection; Spring `Interceptor` for request logging. |

*Statistics (as of the latest analysis): 738 components, 199 domain entities, 173 services, 38 repositories, 32 controllers, 21 REST interfaces, 4 interceptors, 1 guard, 1 scheduler, 1 configuration component.*
