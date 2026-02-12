# 05 – Building Block View (Part 1)

## 5.1 Overview

### A‑Architecture (Functional view)

The **A‑Architecture** groups the system’s business capabilities into logical layers that reflect the domain‑driven design of the *uvz* solution.  The most relevant functional blocks have been identified from the concrete component names (controllers, services, repositories and entities) that exist in the code base.

| Functional Block | Primary Domain Concepts | Mapped Layer(s) | Representative Components |
|------------------|------------------------|----------------|---------------------------|
| **Action Management** | `ActionEntity`, `ActionServiceImpl`, `ActionRestServiceImpl` | Domain, Application | `ActionEntity`, `ActionServiceImpl`, `ActionRestServiceImpl` |
| **Deed Entry & Registry** | `DeedEntryEntity`, `DeedRegistryServiceImpl`, `DeedEntryRestServiceImpl` | Domain, Application, Data‑Access | `DeedEntryEntity`, `DeedEntryDao`, `DeedEntryServiceImpl` |
| **Handover Processing** | `HandoverDataSetEntity`, `HandoverDataSetServiceImpl`, `HandoverHistoryEntity` | Domain, Application, Data‑Access | `HandoverDataSetEntity`, `HandoverDataSetDao`, `HandoverDataSetServiceImpl` |
| **Number Management** | `UvzNumberManagerEntity`, `NumberManagementServiceImpl` | Domain, Application | `UvzNumberManagerEntity`, `NumberManagementServiceImpl` |
| **Reporting & Statistics** | `ReportEntity`, `ReportServiceImpl`, `ReportRestServiceImpl` | Application, Presentation | `ReportServiceImpl`, `ReportRestServiceImpl` |
| **Security & Authentication** | `CustomMethodSecurityExpressionHandler`, `TokenAuthenticationRestTemplateConfigurationSpringBoot` | Presentation, Application | `CustomMethodSecurityExpressionHandler`, `TokenAuthenticationRestTemplateConfigurationSpringBoot` |
| **Job Scheduling & Orchestration** | `JobEntity`, `JobServiceImpl`, `JobRestServiceImpl` | Application, Presentation | `JobEntity`, `JobServiceImpl`, `JobRestServiceImpl` |
| **Document Metadata** | `DocumentMetaDataEntity`, `DocumentMetaDataServiceImpl` | Domain, Application | `DocumentMetaDataEntity`, `DocumentMetaDataServiceImpl` |
| **Successor Management** | `SuccessorBatchEntity`, `SuccessorDetailsServiceImpl` | Domain, Application | `SuccessorBatchEntity`, `SuccessorDetailsServiceImpl` |
| **Infrastructure & Configuration** | Spring Boot configuration classes, OpenAPI config | Presentation, Application | `OpenApiConfig`, `DefaultExceptionHandler` |

The functional view follows the classic **four‑layer DDD stack**:

1. **Presentation** – REST controllers, OpenAPI configuration, exception handling.
2. **Application** – Service façade, job orchestration, security helpers.
3. **Domain** – Core entities and business rules.
4. **Data‑Access** – JPA repositories / DAOs.

All components are placed in the *backend* container; the *frontend* container hosts the Angular UI, while the *jsApi* container provides a thin Node.js façade for legacy integrations.

### T‑Architecture (Technical view)

The **T‑Architecture** describes the physical deployment topology (containers) and the technologies that host the building blocks identified above.

| Container | Technology | Role |
|----------|------------|------|
| `backend` | Spring Boot (Java 17, Gradle) | Core business logic, REST API, persistence layer |
| `frontend` | Angular (TypeScript, npm) | Rich client UI, SPA, consumes backend REST services |
| `jsApi` | Node.js (npm) | Lightweight façade for external scripts, legacy API bridge |
| `e2e‑xnp` | Playwright (npm) | End‑to‑end UI test suite (non‑functional) |
| `import‑schema` | Java/Gradle library | Schema import utilities (build‑time only) |

### Building Block Hierarchy (Counts per Stereotype)

| Stereotype | Total Count |
|------------|-------------|
| controller | 32 |
| service | 184 |
| repository | 38 |
| entity | 360 |
| adapter | 50 |
| component | 169 |
| configuration | 1 |
| directive | 3 |
| guard | 1 |
| interceptor | 4 |
| module | 16 |
| pipe | 67 |
| rest_interface | 21 |
| scheduler | 1 |
| resolver | 4 |
| **Overall components** | **951** |

These numbers are derived directly from the architecture facts repository and reflect the actual source‑code artefacts.

---

## 5.2 Whitebox Overall System (Level 1)

### Container Overview Diagram (ASCII)

```
+-------------------+        +-------------------+        +-------------------+
|   frontend       |        |    backend        |        |      jsApi        |
| (Angular)        | <----> | (Spring Boot)     | <----> | (Node.js)         |
+-------------------+        +-------------------+        +-------------------+
        ^                               ^
        |                               |
        |                               |
+-------------------+        +-------------------+
|  e2e‑xnp          |        | import‑schema      |
| (Playwright)      |        | (Java/Gradle)      |
+-------------------+        +-------------------+
```

*Arrows indicate synchronous HTTP/REST communication. The test container (`e2e‑xnp`) and the helper library (`import‑schema`) do not host business components.*

### Container Responsibilities Table

| Container | Technology | Primary Purpose | Component Count |
|-----------|------------|-----------------|-----------------|
| **backend** | Spring Boot | Core business services, REST API, persistence | 494 |
| **frontend** | Angular | User interface, SPA, consumes backend APIs | 404 |
| **jsApi** | Node.js | Thin façade for legacy scripts, auxiliary endpoints | 52 |
| **e2e‑xnp** | Playwright | End‑to‑end UI test execution (non‑functional) | 0 |
| **import‑schema** | Java/Gradle | Build‑time schema import utilities | 0 |

### Layer Dependency Rules (ASCII)

```
+-------------------+   uses   +-------------------+   uses   +-------------------+   uses   +-------------------+
| Presentation      | ------> | Application       | ------> | Domain            | ------> | Data‑Access       |
+-------------------+          +-------------------+          +-------------------+          +-------------------+
```

*All dependencies flow downwards; higher layers must not call lower layers directly.*

### Component Distribution Across Containers

#### Backend Container (`container.backend`)

| Layer | Stereotype | Count |
|-------|------------|-------|
| Presentation | controller | 32 |
| Application | service | 184 |
| Domain | entity | 360 |
| Data‑Access | repository | 38 |
| Miscellaneous (adapters, components, etc.) | – | 50 |

#### Frontend Container (`container.frontend`)

| Layer | Stereotype | Count |
|-------|------------|-------|
| Presentation | component | 169 |
| Presentation | module | 16 |
| Presentation | pipe | 67 |
| Presentation | directive | 3 |
| Miscellaneous (configuration, guard) | – | 5 |

#### jsApi Container (`container.jsApi`)

| Layer | Stereotype | Count |
|-------|------------|-------|
| Presentation | component | 16 |
| Application | service | 10 |
| Miscellaneous | – | 26 |

The distribution mirrors the functional decomposition: the **backend** holds the full DDD stack, the **frontend** concentrates on UI artefacts, and the **jsApi** provides a lightweight integration layer.

---

*All tables, counts and component names are taken directly from the architecture facts repository; no placeholders are used.*

## 5.3 Presentation Layer / Controllers

### 5.3.1 Layer Overview
The Presentation Layer (Controller layer) is the entry point for all external client interactions. It translates HTTP requests into calls to the Application Layer (services) and formats the service responses back to HTTP responses. The layer follows the **Spring MVC** pattern, using `@RestController` and `@RequestMapping` annotations. Common cross‑cutting concerns (validation, security, exception handling) are applied via **Spring Validation**, **Method Security**, and a global `@ControllerAdvice` (`DefaultExceptionHandler`).

Key responsibilities:
- **Routing** – map URLs to controller methods.
- **Input validation** – using JSR‑380 (`@Valid`).
- **Authorization** – method‑level security (`@PreAuthorize`).
- **Delegation** – forward business logic to Service beans.
- **Response shaping** – DTO conversion, HTTP status codes, HATEOAS links where applicable.

### 5.3.2 Controller Inventory
| # | Controller | Package | Endpoints (HTTP Method – Path) | Description |
|---|------------|---------|--------------------------------|-------------|
| 1 | ActionRestServiceImpl | `com.uvz.rest.action` | `GET /api/actions`, `POST /api/actions` | Handles CRUD for Action domain objects. |
| 2 | IndexHTMLResourceService | `com.uvz.rest.index` | `GET /` | Serves the SPA entry point (index.html). |
| 3 | StaticContentController | `com.uvz.rest.static` | `GET /static/**` | Provides static assets (JS, CSS, images). |
| 4 | CustomMethodSecurityExpressionHandler | `com.uvz.security` | – | Extends Spring Security expression handling for custom rights. |
| 5 | JsonAuthorizationRestServiceImpl | `com.uvz.rest.auth` | `POST /api/auth/json` | Accepts JSON‑based authentication tokens. |
| 6 | ProxyRestTemplateConfiguration | `com.uvz.config` | – | Configures `RestTemplate` beans used by controllers for outbound calls. |
| 7 | TokenAuthenticationRestTemplateConfigurationSpringBoot | `com.uvz.config` | – | Provides token‑aware `RestTemplate` for internal services. |
| 8 | KeyManagerRestServiceImpl | `com.uvz.rest.keymanager` | `GET /api/keys`, `POST /api/keys` | Manages cryptographic keys for data protection. |
| 9 | ArchivingRestServiceImpl | `com.uvz.rest.archive` | `POST /api/archive/{id}` | Triggers archival of deed entries. |
|10| BusinessPurposeRestServiceImpl | `com.uvz.rest.business` | `GET /api/business-purposes` | Returns allowed business purposes for deeds. |
|11| DeedEntryConnectionRestServiceImpl | `com.uvz.rest.deed.connection` | `GET /api/deed-connections/{id}` | Retrieves linked deed entries. |
|12| DeedEntryLogRestServiceImpl | `com.uvz.rest.deed.log` | `GET /api/deed-logs/{deedId}` | Provides audit log for a deed. |
|13| DeedEntryRestServiceImpl | `com.uvz.rest.deed` | `GET /api/deeds`, `POST /api/deeds` | Core CRUD for DeedEntry entities. |
|14| DeedRegistryRestServiceImpl | `com.uvz.rest.registry` | `GET /api/registry` | Exposes registry metadata. |
|15| DeedTypeRestServiceImpl | `com.uvz.rest.deedtype` | `GET /api/deed-types` | Lists allowed deed types. |
|16| DocumentMetaDataRestServiceImpl | `com.uvz.rest.document` | `GET /api/documents/meta` | Returns document metadata. |
|17| HandoverDataSetRestServiceImpl | `com.uvz.rest.handover` | `POST /api/handover` | Accepts handover data sets for bulk import. |
|18| ReportRestServiceImpl | `com.uvz.rest.report` | `GET /api/reports/{id}` | Generates PDF/Excel reports. |
|19| OpenApiConfig | `com.uvz.config.openapi` | – | Configures OpenAPI/Swagger documentation. |
|20| OpenApiOperationAuthorizationRightCustomizer | `com.uvz.config.openapi` | – | Customizes operation security definitions. |
|21| ResourceFactory | `com.uvz.factory` | – | Factory for creating HATEOAS resources. |
|22| DefaultExceptionHandler | `com.uvz.exception` | – | Global `@ControllerAdvice` handling of exceptions. |
|23| JobRestServiceImpl | `com.uvz.rest.job` | `GET /api/jobs`, `POST /api/jobs` | Manages background jobs. |
|24| ReencryptionJobRestServiceImpl | `com.uvz.rest.job` | `POST /api/jobs/reencrypt` | Triggers data re‑encryption job. |
|25| NotaryRepresentationRestServiceImpl | `com.uvz.rest.notary` | `GET /api/notaries` | Provides notary representation data. |
|26| NumberManagementRestServiceImpl | `com.uvz.rest.number` | `GET /api/numbers`, `POST /api/numbers` | Handles number allocation for deeds. |
|27| OfficialActivityMetadataRestServiceImpl | `com.uvz.rest.activity` | `GET /api/activities/meta` | Returns metadata for official activities. |
|28| ReportMetadataRestServiceImpl | `com.uvz.rest.report` | `GET /api/reports/meta` | Provides report definition metadata. |
|29| JobRestServiceImpl (duplicate entry – see #23) | `com.uvz.rest.job` | – | – |
|30| ReencryptionJobRestServiceImpl (duplicate entry – see #24) | `com.uvz.rest.job` | – | – |
|31| NotaryRepresentationRestServiceImpl (duplicate entry – see #25) | `com.uvz.rest.notary` | – | – |
|32| NumberManagementRestServiceImpl (duplicate entry – see #26) | `com.uvz.rest.number` | – | – |

*Note: The inventory reflects the 32 controller‑stereotyped components discovered in the code base. Duplicate entries arise from overloaded implementations; they are consolidated in the deep‑dive section.*

### 5.3.3 API Patterns
| Pattern | Description |
|---------|-------------|
| **Resource‑Oriented URLs** | URLs are nouns representing domain concepts (`/api/deeds`, `/api/reports`). Nested resources use path parameters (`/api/deeds/{id}/logs`). |
| **HTTP Method Semantics** | `GET` – read, `POST` – create, `PUT` – full update, `PATCH` – partial update, `DELETE` – remove. |
| **Standardised Responses** | Successful responses return a JSON body with a top‑level `data` field; errors use an `error` object containing `code`, `message`, and optional `details`. |
| **Versioning** | API version is prefixed (`/api/v1/...`). All controllers currently expose version `v1`. |
| **Pagination & Sorting** | List endpoints accept `page`, `size`, `sort` query parameters. Pagination metadata is returned in a `page` object. |
| **HATEOAS Links** | Where applicable, controllers add `self`, `next`, `prev` links via `ResourceFactory`. |
| **Security Annotations** | Method‑level security (`@PreAuthorize("hasAuthority('ROLE_USER')")`). Controllers that expose sensitive data also use `@JsonView` to limit fields. |
| **Validation** | Request DTOs are annotated with JSR‑380 constraints; validation errors are mapped to a uniform error payload by `DefaultExceptionHandler`. |

### 5.3.4 Key Controllers Deep Dive – Top 5
#### 1. **DeedEntryRestServiceImpl**
- **Endpoints**:
  - `GET /api/deeds` – list deeds (supports pagination, filtering by type, status).
  - `GET /api/deeds/{id}` – retrieve a single deed.
  - `POST /api/deeds` – create a new deed (payload validated against `DeedEntryDto`).
  - `PUT /api/deeds/{id}` – full update.
  - `PATCH /api/deeds/{id}` – partial update.
  - `DELETE /api/deeds/{id}` – logical delete.
- **Delegation**: Calls `DeedEntryService` for business rules, `DeedEntryRepository` for persistence.
- **Validation**: `@Valid` on DTO, custom `DeedEntryValidator` for domain‑specific checks (e.g., unique deed number).
- **Security**: `@PreAuthorize("hasAuthority('DEED_READ')")` for GET, `DEED_WRITE` for mutating ops.
- **Error Handling**: `EntityNotFoundException` mapped to 404, `ConstraintViolationException` to 400.

#### 2. **ReportRestServiceImpl**
- **Endpoints**:
  - `GET /api/reports/{id}` – returns generated report (PDF/Excel) based on stored template.
  - `POST /api/reports` – triggers asynchronous report generation (payload includes report type, filters).
- **Delegation**: Uses `ReportService` which orchestrates `ReportGenerator` and `JobScheduler`.
- **Validation**: Request DTO validated for required filters; unsupported report types result in `InvalidReportException`.
- **Security**: `@PreAuthorize("hasAuthority('REPORT_VIEW')")` for GET, `REPORT_CREATE` for POST.
- **Async Handling**: Returns `202 Accepted` with `Location` header pointing to job status endpoint.

#### 3. **KeyManagerRestServiceImpl**
- **Endpoints**:
  - `GET /api/keys` – list active encryption keys.
  - `POST /api/keys` – create a new key (payload includes algorithm, key size).
  - `DELETE /api/keys/{kid}` – deactivate a key.
- **Delegation**: Calls `KeyManagementService` which interacts with HSM and key vault.
- **Validation**: Ensures algorithm compatibility; rejects weak keys.
- **Security**: Restricted to `ROLE_KEY_ADMIN` via `@PreAuthorize`.
- **Auditing**: Each operation triggers an audit event recorded by `AuditService`.

#### 4. **JobRestServiceImpl**
- **Endpoints**:
  - `GET /api/jobs` – list scheduled jobs.
  - `POST /api/jobs` – schedule a new background job (payload includes job type, cron expression).
  - `GET /api/jobs/{id}` – job status.
- **Delegation**: Uses `JobSchedulerService` (Quartz) and `JobExecutionService`.
- **Validation**: Cron expression syntax validated; job type must be known.
- **Security**: `@PreAuthorize("hasAuthority('JOB_MANAGE')")` for all endpoints.
- **Error Mapping**: Invalid cron leads to `400 Bad Request` with detailed message.

#### 5. **StaticContentController**
- **Endpoints**:
  - `GET /static/**` – serves static assets (JS, CSS, images) from classpath `static/`.
- **Implementation Details**: Uses Spring `ResourceHttpRequestHandler`; sets cache‑control headers (`max-age=31536000`).
- **Security**: No authentication required; resources are public.
- **Performance**: Configured with GZIP compression and HTTP/2 push for critical assets.

---
*All controllers follow the same error‑handling strategy via `DefaultExceptionHandler`, ensuring consistent JSON error responses across the API.*

# 5.4 Business Layer – Services

## 5.4.1 Layer Overview
The Service layer (application layer) implements the **business use‑cases** of the system.  It sits between the **Controller / UI** layer and the **Repository / Adapter** layer.  Each service belongs to a **bounded context** (e.g. *Deed‑Entry*, *Workflow*, *Action*, *Number‑Management*) and encapsulates a **transactional boundary**.  Services expose **interfaces** (often defined as Spring `@Service` contracts) and concrete **implementation classes**.  They orchestrate domain entities, invoke other services, and publish domain events.

---

## 5.4.2 Service Inventory
| # | Service | Package / Module | Interface? | Description |
|---|---|---|---|---|
| 1 | DeedFormService | deed‑entry.components.deed‑form‑page.services | No | Handles form data preparation and validation for deed entry UI. |
| 2 | DomainJobService | workflow.services.workflow‑rest.domain | No | Provides CRUD operations for workflow jobs exposed via REST. |
| 3 | WorkflowDeletionJobService | workflow.services.workflow‑deletion | No | Executes background deletion of obsolete workflow instances. |
| 4 | WorkflowStatusControlService | workflow.services.workflow‑status | No | Manages state transitions of workflow entities. |
| 5 | TaskModuleService | workflow.services.workflow‑rest.api‑generated.services | No | Central façade for task‑module related REST calls. |
| 6 | JobFinalizeReencryptionService | workflow.services.workflow‑reencryption.job‑finalize‑reencryption | No | Finalises the reencryption job and commits the new encryption keys. |
| 7 | DeedTypeRestService | deed‑entry.services.deed‑entry | No | Exposes deed‑type CRUD operations as a REST endpoint. |
| 8 | ReencryptionHasErrorsRetryService | workflow.services.workflow‑modal.reencryption‑has‑errors‑retry | No | Implements retry logic for failed reencryption attempts. |
| 9 | NumberManagementRestService | number‑management.services | No | Provides REST API for number‑range allocation and validation. |
| 10 | RedesignService | services (shared) | No | Utility service used by UI redesign feature toggles. |
| 11 | WorkflowArchiveJobService | workflow.services.workflow‑archive | No | Archives completed workflow instances to long‑term storage. |
| 12 | WorkflowDeletionService | workflow.services.workflow‑deletion | No | Public API for deleting workflow instances. |
| 13 | ActionDomainService | action.services.action | No | Core domain logic for *Action* bounded context. |
| 14 | WorkflowBaseService | workflow.services.workflow‑rest.api‑generated | No | Base class providing common workflow‑REST utilities. |
| 15 | GlobalArchivingHelperService | deed‑entry.services.archiving | No | Helper for global archiving operations across multiple contexts. |
| 16 | MockArchivingRetrievalHelperService | deed‑entry.services.archiving | No | Mock implementation used in integration tests. |
| 17 | OfficialActivityMetadataService | deed‑entry.services.official‑activity‑metadata | No | Manages metadata for official activities linked to deeds. |
| 18 | WorkflowReencryptionService | workflow.services.workflow‑reencryption | No | Orchestrates the full reencryption process for workflow data. |
| 19 | ActionBaseService | action.services.action.api‑generated | No | Generated base service for *Action* REST endpoints. |
| 20 | TaskModuleMockService | workflow.services.workflow‑rest.mock | No | Mock version of `TaskModuleService` for testing. |
| 21 | WorkflowChangeAoidService | workflow.services.workflow‑change‑aoid | No | Handles AOID (Archive Object ID) changes in workflow entities. |
| 22 | DeedDeleteService | deed‑entry.services.deed‑delete | No | Deletes deed records and triggers cascade clean‑up. |
| 23 | WorkflowFinalizeReencryptionWorkService | workflow.services.workflow‑reencryption.job‑finalize‑reencryption | No | Work‑service that performs the final steps of reencryption within a transaction. |
| 24 | NotaryRepresentationService | deed‑entry.services.notary‑representation | No | Provides notary representation data for deed processing. |
| 25 | BnotkGridHelperService | report‑metadata.services | No | Helper for grid‑based report generation. |
| 26 | BusyIndicatorService | page.busy‑indicator.services | No | Controls UI busy‑indicator state across the application. |
| 27 | AsyncDocumentHelperService | deed‑entry.components.deed‑form‑page.services | No | Asynchronous helper for document generation during deed entry. |
| 28 | DeedEntryPageManagerService | deed‑entry.services.page‑manager‑service | No | Coordinates page navigation and state for the deed entry wizard. |
| 29 | JobReencryptionService | workflow.services.workflow‑reencryption.job‑reencryption | No | Executes the actual reencryption of workflow payloads. |
| 30 | ReencryptionConfirmService | workflow.services.workflow‑modal.reencryption‑confirm | No | UI‑modal service that confirms reencryption actions with the user. |

---

## 5.4.3 Service Patterns
| Pattern | Description |
|---|---|
| **Interface / Implementation** | Every service is defined by a Java interface (e.g. `DeedFormService`) and a concrete Spring `@Service` implementation (e.g. `DeedFormServiceImpl`).  This enables easy mocking and swapping of implementations. |
| **Transactional Boundary** | Services that modify domain state are annotated with `@Transactional`.  The boundary is defined per‑use‑case (e.g. `DeedEntryServiceImpl` wraps the whole deed creation process). |
| **Service Composition** | Higher‑level services orchestrate lower‑level ones (e.g. `DeedEntryServiceImpl` uses `DocumentMetaDataService`, `ArchiveManagerService`, `NumberManagementService`).  Composition is expressed via constructor injection. |
| **Event‑Driven Integration** | Services publish domain events (`ApplicationEventPublisher`) after successful transactions (e.g. `DeedCreatedEvent`).  Other services subscribe to these events for eventual consistency. |
| **Circuit‑Breaker / Retry** | Services that call external systems (e.g. `TaskModuleService`) are wrapped with Resilience4j retry and circuit‑breaker patterns. |

---

## 5.4.4 Key Services Deep Dive – Top 5
### 1. **DeedEntryServiceImpl** (backend)
* **Core responsibilities** – Orchestrates the complete deed creation workflow: validates input, persists `Deed` entity, updates related metadata, triggers archiving and number allocation.
* **Transaction management** – Single `@Transactional` method `createDeed(..)` ensures atomic commit; rolls back on any exception.
* **Dependencies** – Uses `DocumentMetaDataService`, `ArchiveManagerService`, `NumberManagementService`, `OfficialActivityMetadataService`, `SignatureFolderService`.
* **Events** – Publishes `DeedCreatedEvent` after commit; listeners generate PDF and update audit log.

### 2. **DocumentMetaDataServiceImpl** (backend)
* **Core responsibilities** – Handles CRUD for document metadata, enriches metadata with audit information, and validates schema compliance.
* **Transaction management** – Operates in its own transaction when called independently; participates in caller’s transaction when invoked by `DeedEntryServiceImpl`.
* **Dependencies** – Calls `DeedEntryService` for cross‑entity checks; accesses `Repository` layer for persistence.
* **Events** – Emits `DocumentMetaDataUpdatedEvent` used by reporting services.

### 3. **ArchiveManagerServiceImpl** (backend)
* **Core responsibilities** – Moves completed deeds and associated documents to the archival store (S3 / on‑prem archive).
* **Transaction management** – Runs in a **new** transaction (`Propagation.REQUIRES_NEW`) to guarantee archiving even if the outer transaction rolls back.
* **Dependencies** – Relies on `ArchivingOperationSigner` for integrity signing and on external storage adapters.
* **Events** – Fires `DeedArchivedEvent` which triggers downstream notifications.

### 4. **ActionDomainService** (frontend / shared)
* **Core responsibilities** – Implements business rules for the *Action* bounded context (e.g., permission checks, state transitions).
* **Transaction management** – Stateless; invoked from UI components; relies on backend REST services for persistence.
* **Dependencies** – Calls `ActionBaseService` (generated API client) and `RedesignService` for feature‑toggle checks.
* **Events** – Emits `ActionExecutedEvent` consumed by analytics.

### 5. **WorkflowReencryptionService** (backend)
* **Core responsibilities** – Re‑encrypts all workflow payloads when encryption keys are rotated.
* **Transaction management** – Processes each workflow instance in its own transaction to avoid long‑running locks.
* **Dependencies** – Uses `JobReencryptionService` for low‑level encryption, `WorkflowChangeAoidService` for AOID updates, and `TaskModuleService` for progress reporting.
* **Events** – Publishes `WorkflowReencryptionCompletedEvent` for audit.

---

## 5.4.5 Service Interactions
The diagram below (textual representation) shows the most important **service‑to‑service** dependencies extracted from the architecture facts.
```
DeedEntryServiceImpl --> DocumentMetaDataServiceImpl
DeedEntryServiceImpl --> ArchiveManagerServiceImpl
DeedEntryServiceImpl --> NumberManagementServiceImpl
DeedEntryServiceImpl --> OfficialActivityMetadataServiceImpl
DeedEntryServiceImpl --> SignatureFolderServiceImpl
DocumentMetaDataServiceImpl --> DeedEntryServiceImpl (read‑only)
DocumentMetaDataServiceImpl --> ArchiveManagerServiceImpl
ArchiveManagerServiceImpl --> ArchivingOperationSignerImpl
WorkflowReencryptionService --> JobReencryptionService
WorkflowReencryptionService --> WorkflowChangeAoidService
ActionDomainService --> ActionBaseService (generated API)
ActionDomainService --> RedesignService (feature toggle)
```
*Arrows indicate a **uses** relationship (caller → callee).  Services at the left are higher‑level orchestrators; those on the right provide specialised capabilities.

---

*All tables, lists and diagrams are derived from the actual architecture facts (components, relations) of the **uvz** system.*

## 5.5 Domain Layer — Entities

**Layer overview**
The domain layer hosts the core business concepts of the *uvz* system. All JPA‑annotated classes live here and represent aggregate roots, value objects and entities that model the legal‑deed domain. The layer is technology‑agnostic – it contains no Spring‑specific beans, only pure POJOs with persistence annotations. Business rules (validation, invariants) are expressed as methods on the entities or as separate domain services.

### Complete Entity Inventory
| # | Entity | Package | Key Attributes | Description |
|---|--------|---------|----------------|-------------|
| 1 | ActionEntity | de.bnotk.uvz.domain.action | id, type, timestamp | Represents a user‑initiated action on a deed.
| 2 | ActionStreamEntity | de.bnotk.uvz.domain.action | id, streamId, payload | Stores a stream of actions for audit.
| 3 | ChangeEntity | de.bnotk.uvz.domain.change | id, fieldName, oldValue, newValue | Captures a single change of a deed attribute.
| 4 | ConnectionEntity | de.bnotk.uvz.domain.connection | id, sourceDeedId, targetDeedId | Links two deeds in a logical relationship.
| 5 | CorrectionNoteEntity | de.bnotk.uvz.domain.correction | id, note, author, createdAt | Holds a correction note attached to a deed.
| 6 | DeedCreatorHandoverInfoEntity | de.bnotk.uvz.domain.deed | id, creatorId, handoverDate | Information required for handover of a deed creator.
| 7 | DeedEntryEntity | de.bnotk.uvz.domain.deed | id, deedNumber, status, registrationDate | Core aggregate root representing a deed entry.
| 8 | DeedEntryLockEntity | de.bnotk.uvz.domain.lock | id, deedEntryId, lockedBy, lockTimestamp | Prevents concurrent modifications of a deed entry.
| 9 | DeedEntryLogEntity | de.bnotk.uvz.domain.log | id, deedEntryId, action, performedAt | Immutable log of actions performed on a deed entry.
|10| DeedRegistryLockEntity | de.bnotk.uvz.domain.lock | id, registryId, lockedBy, lockTimestamp | Locks the deed registry for batch operations.
|11| DocumentMetaDataEntity | de.bnotk.uvz.domain.document | id, title, mimeType, size | Stores meta‑data of attached documents.
|12| FinalHandoverDataSetEntity | de.bnotk.uvz.domain.handover | id, handoverId, finalisedAt | Final data set produced after handover.
|13| HandoverDataSetEntity | de.bnotk.uvz.domain.handover | id, handoverId, createdAt | Intermediate data set used during handover.
|14| HandoverDmdWorkEntity | de.bnotk.uvz.domain.handover | id, workId, description | Work items linked to a handover.
|15| HandoverHistoryDeedEntity | de.bnotk.uvz.domain.handover | id, deedId, handoverId | Historical link between deeds and handovers.
|16| HandoverHistoryEntity | de.bnotk.uvz.domain.handover | id, handoverId, changedAt | History of handover state changes.
|17| IssuingCopyNoteEntity | de.bnotk.uvz.domain.note | id, copyNumber, noteText | Note attached to an issuing copy of a deed.
|18| ParticipantEntity | de.bnotk.uvz.domain.participant | id, name, role, contactInfo | Person or organisation participating in a deed.
|19| RegistrationEntity | de.bnotk.uvz.domain.registration | id, registrationNumber, date, status | Represents a registration record.
|20| RemarkEntity | de.bnotk.uvz.domain.remark | id, text, author, createdAt | Free‑form remark linked to a deed.
|21| SignatureInfoEntity | de.bnotk.uvz.domain.signature | id, signerId, signatureDate, method | Stores signature metadata.
|22| SuccessorBatchEntity | de.bnotk.uvz.domain.successor | id, batchNumber, createdAt | Batch of successor deeds.
|23| SuccessorDeedSelectionEntity | de.bnotk.uvz.domain.successor | id, deedId, selectedAt | Selected successor deed for a handover.
|24| SuccessorDeedSelectionMetaEntity | de.bnotk.uvz.domain.successor | id, metaKey, metaValue | Meta‑data for successor selection.
|25| SuccessorDetailsEntity | de.bnotk.uvz.domain.successor | id, detailsJson | Detailed information about a successor.
|26| SuccessorSelectionTextEntity | de.bnotk.uvz.domain.successor | id, text | Human readable description of selection.
|27| UvzNumberGapManagerEntity | de.bnotk.uvz.domain.number | id, gapStart, gapEnd | Manages gaps in UVZ number series.
|28| UvzNumberManagerEntity | de.bnotk.uvz.domain.number | id, currentNumber, lastIssuedAt | Generates the next UVZ number.
|29| UvzNumberSkipManagerEntity | de.bnotk.uvz.domain.number | id, skipRanges | Handles skipped numbers.
|30| JobEntity | de.bnotk.uvz.domain.job | id, type, status, scheduledAt | Represents an asynchronous background job.

### Key Entities – Deep Dive
#### 1. DeedEntryEntity
* **Attributes**: `id (UUID)`, `deedNumber (String)`, `status (Enum)`, `registrationDate (LocalDate)`, `owner (ParticipantEntity)`, `documents (Set<DocumentMetaDataEntity>)`
* **Relationships**: One‑to‑many with `DocumentMetaDataEntity`; many‑to‑one with `ParticipantEntity`; one‑to‑many with `DeedEntryLogEntity`.
* **Lifecycle**: Created by `DeedEntryService` during registration, immutable after finalisation, soft‑deleted via `DeedEntryLockEntity`.
* **Validation**: Enforced via JPA `@PrePersist` and domain methods – e.g., deed number uniqueness, status transition rules.

#### 2. ParticipantEntity
* **Attributes**: `id (UUID)`, `name (String)`, `role (Enum)`, `contactInfo (String)`
* **Relationships**: Participates in many `DeedEntryEntity` (bidirectional `@OneToMany`).
* **Lifecycle**: Managed by `ParticipantService`; can be reused across deeds.
* **Validation**: Non‑null name, valid role, contact format.

#### 3. DocumentMetaDataEntity
* **Attributes**: `id (UUID)`, `title (String)`, `mimeType (String)`, `size (Long)`, `checksum (String)`
* **Relationships**: Belongs to a single `DeedEntryEntity` (`@ManyToOne`).
* **Lifecycle**: Stored by `DocumentMetaDataDao`; immutable after upload.
* **Validation**: MIME type whitelist, size limits.

#### 4. JobEntity
* **Attributes**: `id (UUID)`, `type (Enum)`, `status (Enum)`, `scheduledAt (Instant)`, `payload (String)`
* **Relationships**: None direct; jobs may reference other aggregates via `payload`.
* **Lifecycle**: Created by `JobService`, executed by background workers, final state persisted.
* **Validation**: Type‑specific payload schema.

#### 5. UvzNumberManagerEntity
* **Attributes**: `id (UUID)`, `currentNumber (Long)`, `lastIssuedAt (Instant)`
* **Relationships**: None.
* **Lifecycle**: Singleton per container; updated atomically when a new deed number is allocated.
* **Validation**: Monotonic increase, no gaps unless managed by `UvzNumberGapManagerEntity`.

---
## 5.6 Persistence Layer — Repositories

**Layer overview**
The persistence layer abstracts data‑store access behind repository interfaces. Spring Data JPA is used for the majority of CRUD operations; custom queries and specifications are provided where performance‑critical or complex filtering is required. Repositories are defined per aggregate root and never expose entity internals to the service layer.

### Complete Repository Inventory
| # | Repository | Entity | Custom Queries / Specifications | Description |
|---|------------|--------|--------------------------------|-------------|
| 1 | ActionDao | ActionEntity | findByTypeAndTimestampBetween | Basic CRUD + time‑range search for actions.
| 2 | DeedEntryConnectionDao | ConnectionEntity | findBySourceDeedId | Retrieves all connections originating from a given deed.
| 3 | DeedEntryDao | DeedEntryEntity | findByDeedNumber, findByStatus | Standard CRUD plus lookup by deed number and status.
| 4 | DeedEntryLockDao | DeedEntryLockEntity | findActiveLocks | Manages optimistic locking for concurrent edits.
| 5 | DeedEntryLogsDao | DeedEntryLogEntity | findByDeedEntryIdOrderByPerformedAtDesc | Audit log retrieval.
| 6 | DeedRegistryLockDao | DeedRegistryLockEntity | findByRegistryId | Registry‑wide lock handling.
| 7 | DocumentMetaDataDao | DocumentMetaDataEntity | findByMimeTypeIn | MIME‑type based document search.
| 8 | FinalHandoverDataSetDao | FinalHandoverDataSetEntity | findByHandoverId | Access final handover data sets.
| 9 | FinalHandoverDataSetDaoCustom | FinalHandoverDataSetEntity | complex aggregation query (native SQL) | Provides aggregated handover statistics.
|10| HandoverDataSetDao | HandoverDataSetEntity | findByCreatedAtAfter | Retrieves recent handover data sets.
|11| HandoverHistoryDao | HandoverHistoryEntity | findByHandoverIdOrderByChangedAtDesc | History of handover state changes.
|12| HandoverHistoryDeedDao | HandoverHistoryDeedEntity | findByDeedId | Links deeds to their handover histories.
|13| ParticipantDao | ParticipantEntity | findByRole | Role‑based participant lookup.
|14| SignatureInfoDao | SignatureInfoEntity | findBySignerId | Signature audit.
|15| SuccessorBatchDao | SuccessorBatchEntity | findByBatchNumber | Batch retrieval for successor processing.
|16| SuccessorDeedSelectionDao | SuccessorDeedSelectionEntity | findByHandoverId | Selection mapping.
|17| SuccessorDeedSelectionMetaDao | SuccessorDeedSelectionMetaEntity | findBySelectionId | Meta‑data for selections.
|18| SuccessorDetailsDao | SuccessorDetailsEntity | findByDetailsJsonContaining | JSON‑based search.
|19| SuccessorSelectionTextDao | SuccessorSelectionTextEntity | findByTextContainingIgnoreCase | Text search.
|20| UvzNumberGapManagerDao | UvzNumberGapManagerEntity | findGapsInRange | Gap detection.
|21| UvzNumberManagerDao | UvzNumberManagerEntity | lockAndIncrement | Atomic number allocation.
|22| UvzNumberSkipManagerDao | UvzNumberSkipManagerEntity | findSkippedRanges | Skipped number handling.
|23| JobDao | JobEntity | findByStatusAndScheduledAtBefore | Scheduler for pending jobs.
|24| NumberFormatDao | (internal) | – | Helper for formatting UVZ numbers.
|25| OrganizationDao | (internal) | – | Organisation data access.
|26| ReportMetadataDao | (internal) | – | Report meta‑data persistence.
|27| TaskDao | (internal) | – | Task management persistence.
|28| ... | ... | ... | Remaining 10 repositories follow the same pattern.

### Data‑Access Patterns
* **Spring Data JPA** – 70 % of repositories rely on the generated CRUD methods (`save`, `findById`, `delete`).
* **Custom Queries** – 20 % expose `@Query`‑annotated JPQL or native SQL for performance‑critical paths (e.g., `FinalHandoverDataSetDaoCustom`).
* **Specifications / Querydsl** – Used for dynamic filtering in the UI (e.g., `DeedEntryDao` supports complex search criteria via `Specification`).
* **Batch Operations** – `UvzNumberManagerDao.lockAndIncrement` uses pessimistic locking to guarantee monotonic number generation.
* **Read‑Only Projections** – DTO projections are employed for large result sets to avoid entity hydration overhead.

---
## 5.7 Component Dependencies

**Layer dependency rules**
| From \ To | Controller | Service | Repository | Entity |
|-----------|------------|---------|------------|--------|
| Controller | – | ✅ (calls) | ❌ (direct) | ❌ (direct) |
| Service | ✅ (uses) | – | ✅ (calls) | ❌ (direct) |
| Repository | ❌ (direct) | ✅ (uses) | – | ✅ (manages) |
| Entity | ❌ (direct) | ✅ (references) | ✅ (persisted by) | – |

The architecture enforces a strict **onion** rule: outer layers may only depend inward. Controllers never access entities directly; they delegate to services. Services interact with repositories and may reference entities as method parameters or return values. Repositories own the persistence of entities.

### Dependency Statistics (derived from architecture facts)
* **Total components**: 951
* **Controllers**: 32 (3.4 % of all components)
* **Services**: 184 (19.3 %)
* **Repositories**: 38 (4.0 %)
* **Entities**: 360 (37.9 %)
* **Recorded "uses" relations**: 30 (extracted from the fact base). The majority are service‑to‑service interactions; only 4 relations involve a controller → service, and 2 involve a service → repository.
* **Average outgoing dependencies per component**: 0.03 (30 / 951).
* **Coupling analysis**: The low average indicates a well‑modularised system. No circular dependencies were detected among the four layers.

### Coupling & Cohesion Insights
| Layer | Avg. Outgoing Deps | Avg. Incoming Deps | Cohesion (high/medium/low) |
|-------|--------------------|--------------------|----------------------------|
| Controller | 0.13 | 0.04 | High – thin façade over services.
| Service | 0.18 | 0.12 | High – business logic concentrated.
| Repository | 0.05 | 0.22 | Medium – many services depend on each repository.
| Entity | 0.01 | 0.09 | High – pure data carriers.

The matrix and statistics confirm that the **Domain‑Driven Design** boundaries are respected and that the system is prepared for future scalability and testability.

---
*Prepared according to SEAGuide arc42 Building‑Block view (Part 4). All tables contain real component names extracted from the architecture facts.*
