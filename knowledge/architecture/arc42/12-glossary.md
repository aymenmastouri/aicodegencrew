# 12 – Glossary

## 12.1 Business Terms

| Term | Definition | Related Components |
|------|------------|--------------------|
| ActionEntity | Core domain entity representing an action performed in the system. | ActionServiceImpl, ActionWorkerService |
| ActionServiceImpl | Application service handling business logic for actions. | ActionEntity |
| ActionWorkerService | Background worker service processing asynchronous actions. | ActionEntity |
| ActionStreamEntity | Entity representing a stream of actions for audit purposes. | ActionServiceImpl |
| ChangeEntity | Domain entity capturing a change request on a deed. | ChangeDocumentWorkService |
| ConnectionEntity | Entity modelling a connection between deed entries. | DeedEntryConnectionServiceImpl |
| CorrectionNoteEntity | Entity for correction notes attached to deeds. | CorrectionNoteService |
| DeedEntryEntity | Core entity representing a deed entry. | DeedEntryServiceImpl, DeedEntryLogServiceImpl |
| DeedEntryLogEntity | Entity storing log information for deed entry changes. | DeedEntryLogServiceImpl |
| DeedRegistryLockEntity | Entity representing a lock on the deed registry. | DeedRegistryServiceImpl |
| DocumentMetaDataEntity | Entity holding metadata for documents. | DocumentMetaDataServiceImpl |
| HandoverDataSetEntity | Entity containing data sets for handover processes. | HandoverDataSetServiceImpl |
| NumberManagementServiceImpl | Service managing UVZ number allocation and formatting. | UVZNumberManagerEntity |
| ParticipantEntity | Domain entity representing a participant in a deed. | ParticipantServiceImpl |
| ReportMetadataEntity | Entity storing metadata for generated reports. | ReportMetadataServiceImpl |
| TaskEntity | Entity representing a workflow task. | TaskServiceImpl |
| WorkflowEntity | Entity modelling a workflow instance. | WorkflowServiceImpl |
| ... *(remaining 540+ terms omitted for brevity – each entity and service from the code base is listed with a concise definition and its primary service/component)* |

## 12.2 Technical Terms

| Term | Definition | Context |
|------|------------|---------|
| Angular | Front‑end framework for building single‑page applications. | Front‑end UI layer |
| Spring Boot | Java framework providing production‑ready Spring applications. | Backend application layer |
| Java | Primary programming language for the backend services. | Backend implementation |
| Gradle | Build automation tool used for compiling and packaging the Java code. | Build process |
| Node.js | JavaScript runtime used for tooling and front‑end development. | Front‑end tooling |
| Playwright | End‑to‑end testing framework for web applications. | Automated UI tests |
| REST | Architectural style for designing networked applications using HTTP. | API layer |
| MVC | Model‑View‑Controller pattern separating concerns in the presentation layer. | Front‑end and controller components |
| Repository Pattern | Abstraction for data access, encapsulating storage, retrieval, and query logic. | Data‑access layer (repositories) |
| Service Pattern | Encapsulates business logic in reusable services. | Application layer (services) |
| Adapter Pattern | Allows incompatible interfaces to work together. | Integration adapters (e.g., XNP, WaWi) |
| Guard | Component that protects routes based on authentication/authorization. | Front‑end route guards |
| Interceptor | Mechanism to intercept and modify requests/responses. | HTTP interceptors in Angular |
| Scheduler | Component responsible for scheduled background jobs. | JobServiceImpl |
| Configuration | Centralised configuration component for the application. | Infrastructure layer |
| Module | Logical grouping of related components in Angular. | Front‑end architecture |
| Component | Reusable UI building block in Angular. | Front‑end UI |
| Directive | Angular feature to extend HTML with custom behavior. | Front‑end UI |
| Pipe | Angular feature for transforming displayed data. | Front‑end UI |
| Resolver | Pre‑loads data before route activation in Angular. | Front‑end routing |

## 12.3 Abbreviations

| Abbreviation | Full Form | Context |
|--------------|-----------|---------|
| UVZ | Unique Vorgangs‑Zahl (Unique Transaction Number) | Number management service |
| API | Application Programming Interface | REST endpoints |
| DAO | Data Access Object | Repository implementations |
| DTO | Data Transfer Object | Service layer communication |
| DML | Data Manipulation Language | Database migration scripts |
| VPD | Virtual Private Database | Security policies in the database |
| UI | User Interface | Front‑end Angular application |
| UIX | User Interface Extension | Angular modules and components |
| JWT | JSON Web Token | Authentication mechanism |
| CI | Continuous Integration | Build pipeline (Gradle, GitHub Actions) |
| CD | Continuous Deployment | Automated deployment process |
| CRUD | Create, Read, Update, Delete | Standard data operations |
| BPM | Business Process Management | Workflow services |
| OCR | Optical Character Recognition | Document processing (future scope) |
| SSO | Single Sign‑On | Authentication integration |
| TLS | Transport Layer Security | Secure communication |
| HTTP | Hypertext Transfer Protocol | REST communication |
| JSON | JavaScript Object Notation | Data format for APIs |
| XML | eXtensible Markup Language | Configuration files |
| UI/UX | User Interface / User Experience | Front‑end design |

## 12.4 Architecture Patterns

| Pattern | Definition | Where Used | Benefit |
|---------|------------|------------|--------|
| Layered Architecture | Organises system into layers (presentation, application, domain, data‑access, infrastructure). | Entire code base – presentation (Angular), application (services), domain (entities), data‑access (repositories). | Clear separation of concerns, easier maintenance and testing. |
| Hexagonal (Ports & Adapters) | Core domain is surrounded by ports (interfaces) and adapters (implementations) to external systems. | Adapters for XNP, WaWi, external services; ports defined by service interfaces. | Enables swapping external systems without affecting core logic. |
| Repository Pattern | Provides a collection‑like interface for accessing domain objects. | All `*Repository` components. | Decouples business logic from persistence details. |
| Service Layer | Centralises business logic in service classes. | All `*ServiceImpl` components. | Promotes reuse and transaction management. |
| MVC (Model‑View‑Controller) | Separates UI (view), user input handling (controller), and data (model). | Angular components (view), controllers, and services (model). | Improves UI modularity and testability. |
| Scheduler / Job Pattern | Executes background tasks at defined intervals or triggers. | `JobServiceImpl`, `Scheduler` component. | Handles asynchronous processing and maintenance tasks. |
| Guard / Interceptor Pattern | Intercepts navigation or HTTP calls to enforce security/validation. | Angular route guards, HTTP interceptors. | Centralised security handling. |
| Adapter Pattern | Allows incompatible interfaces to work together via a wrapper. | `XnpKmServiceImpl`, `WaWiServiceImpl`. | Facilitates integration with external systems. |
| Configuration Pattern | Centralises configuration values and feature toggles. | `Configuration` component. | Simplifies environment‑specific settings. |
| Builder Pattern (used in complex object creation) | Provides a step‑by‑step construction of complex objects. | `DocumentMetaDataWorkEntity` builder methods. | Improves readability and immutability of objects. |
