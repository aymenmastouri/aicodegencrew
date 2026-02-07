# 05 – Building Block View

---

## 5.1 Overview

**A‑Architecture (Functional view)** – The system *uvz* is organised around the core business processes of deed‑entry management, archiving, number management and workflow orchestration.  Functional building blocks are expressed as **Controllers** (presentation), **Services** (business logic), **Repositories** (persistence) and **Entities** (domain model).

**T‑Architecture (Technical view)** – Four containers host the functional blocks:

```
+-------------------+      +-------------------+      +-------------------+      +-------------------+
|   Frontend (Angular)   |   |   Backend (Spring Boot)   |   |   E2E‑XNP (Playwright)   |   |   Import‑Schema (Java/Gradle) |
+-------------------+      +-------------------+      +-------------------+      +-------------------+
```

* **Frontend** – Angular UI, communicates via REST/GraphQL.
* **Backend** – Spring Boot services, exposing the REST API.
* **E2E‑XNP** – Playwright test harness.
* **Import‑Schema** – Java/Gradle utilities for schema import.

### Building Block Hierarchy

```
Functional Layer (A‑Architecture)
│
├─ Presentation (Controllers)          ← 32 components
├─ Business (Services)                 ← 173 components
├─ Persistence (Repositories)          ← 38 components
└─ Domain (Entities)                  ← 199 components
```

---

## 5.2 Whitebox Overall System (Level 1)

### Container Overview Diagram (text‑based)

```
+-------------------+          +-------------------+          +-------------------+
|   Frontend (Angular)   | <--REST--> |   Backend (Spring Boot)   | <--JAR--> |   Import‑Schema (Java) |
+-------------------+          +-------------------+          +-------------------+
        ^                                 ^
        |                                 |
        +--- Playwright (E2E‑XNP) ---------+
```

### Container Responsibilities

| Container | Primary Responsibility |
|-----------|--------------------------|
| **Frontend** | UI rendering, client‑side validation, state management, consumes backend REST endpoints. |
| **Backend** | Implements business use‑cases, orchestrates workflows, persists domain data, provides OpenAPI documentation. |
| **E2E‑XNP** | End‑to‑end functional testing, UI regression, performance checks. |
| **Import‑Schema** | Generates and validates database schema, runs Flyway migrations, provides import utilities. |

---

## 5.3 Presentation Layer (Controllers)

### 5.3.1 Layer Overview

Controllers expose the system’s public API. They are thin adapters that delegate to Services, perform request validation and map domain objects to DTOs.

### 5.3.2 Controller Inventory

| # | Controller | Package (simplified) | Description |
|---|------------|----------------------|-------------|
| 1 | ActionRestServiceImpl | backend.service_impl_rest | Handles CRUD for **Action** domain objects. |
| 2 | IndexHTMLResourceService | backend.module_adapters_staticwebresources | Serves the SPA entry point (`index.html`). |
| 3 | StaticContentController | backend.module_adapters_staticwebresources | Serves static assets (JS, CSS, images). |
| 4 | CustomMethodSecurityExpressionHandler | backend.adapters_authorization_configuration | Extends Spring Security expression handling. |
| 5 | JsonAuthorizationRestServiceImpl | backend.impl_mock_rest | Mock implementation for authorization testing. |
| 6 | ProxyRestTemplateConfiguration | backend.common_proxy_resttemplate | Configures `RestTemplate` proxy settings. |
| 7 | TokenAuthenticationRestTemplateConfigurationSpringBoot | backend.adapters_configuration_xna | Configures token‑based authentication for outbound calls. |
| 8 | KeyManagerRestServiceImpl | backend.service_impl_rest | Exposes key‑management operations (create, rotate). |
| 9 | ArchivingRestServiceImpl | backend.service_impl_rest | API for archiving deeds. |
|10 | BusinessPurposeRestServiceImpl | backend.service_impl_rest | Manages business purpose metadata. |
|11 | DeedEntryConnectionRestServiceImpl | backend.service_impl_rest | Handles connections between deed entries. |
|12 | DeedEntryLogRestServiceImpl | backend.service_impl_rest | Provides audit log access for deed entries. |
|13 | DeedEntryRestServiceImpl | backend.service_impl_rest | Core CRUD for **DeedEntry**. |
|14 | DeedRegistryRestServiceImpl | backend.service_impl_rest | Registry‑wide operations (search, export). |
|15 | DeedTypeRestServiceImpl | backend.service_impl_rest | CRUD for deed types. |
|16 | DocumentMetaDataRestServiceImpl | backend.service_impl_rest | Metadata handling for attached documents. |
|17 | HandoverDataSetRestServiceImpl | backend.service_impl_rest | API for handover data‑sets. |
|18 | ReportRestServiceImpl | backend.service_impl_rest | Generates PDF/Excel reports. |
|19 | OpenApiConfig | backend.module_general_configuration | OpenAPI/Swagger configuration. |
|20 | OpenApiOperationAuthorizationRightCustomizer | backend.module_general_configuration | Customises operation‑level security. |
|21 | DefaultExceptionHandler | backend.common_api_exception | Global exception translation to HTTP responses. |
|22 | JobRestServiceImpl | backend.service_impl_rest | Job scheduling and status API. |
|23 | ReencryptionJobRestServiceImpl | backend.service_impl_rest | API for re‑encryption jobs. |
|24 | NotaryRepresentationRestServiceImpl | backend.service_impl_rest | Notary representation management. |
|25 | NumberManagementRestServiceImpl | backend.service_impl_rest | Number allocation & gap management. |
|26 | OfficialActivityMetadataRestServiceImpl | backend.service_impl_rest | Handles official activity metadata. |
|27 | ReportMetadataRestServiceImpl | backend.service_impl_rest | Report metadata CRUD. |
|28 | TaskRestServiceImpl | backend.service_impl_rest | Task management API. |
|29 | WorkflowRestServiceImpl | backend.service_impl_rest | Workflow orchestration endpoints. |
|30 | WorkflowChangeAoidRestServiceImpl | backend.service_impl_rest | AOID change handling. |
|31 | WorkflowDeletionRestServiceImpl | backend.service_impl_rest | Deletion workflow API. |
|32 | WorkflowValidateSignatureRestServiceImpl | backend.service_impl_rest | Signature validation endpoints. |

*All 32 controllers are listed – the inventory is exhaustive.*

### 5.3.3 API Patterns

| Pattern | Description |
|---------|-------------|
| **RESTful CRUD** | Standard `GET/POST/PUT/DELETE` mapping to service methods. |
| **Command‑Query Separation** | Commands (`POST/PUT/DELETE`) return `202 Accepted` with operation ID; queries (`GET`) are idempotent. |
| **OpenAPI Documentation** | Every controller is annotated with `@Operation` and `@Tag`; generated by `OpenApiConfig`. |
| **Global Exception Handling** | `DefaultExceptionHandler` maps domain exceptions to proper HTTP status codes. |
| **Security Annotations** | `@PreAuthorize` with custom expressions from `CustomMethodSecurityExpressionHandler`. |

### 5.3.4 Key Controllers – Deep Dive (Top 5)

#### 1. **DeedEntryRestServiceImpl**
* **Endpoint**: `/api/deed‑entries/**`
* **Operations**: `createDeedEntry`, `getDeedEntry`, `updateDeedEntry`, `deleteDeedEntry`.
* **Delegates to**: `DeedEntryServiceImpl` (business layer).
* **Validation**: Bean‑validation on DTOs, custom `@ValidDeedEntry`.
* **Security**: `@PreAuthorize("hasAuthority('DEED_WRITE')")`.

#### 2. **ReportRestServiceImpl**
* **Endpoint**: `/api/reports/**`
* **Generates**: PDF, Excel, CSV using `ReportServiceImpl`.
* **Streaming**: Returns `ResponseEntity<StreamingResponseBody>` for large files.
* **Caching**: `@Cacheable("reports")` for repeated requests.
* **Security**: `@PreAuthorize("hasAuthority('REPORT_VIEW')")`.

#### 3. **NumberManagementRestServiceImpl**
* **Endpoint**: `/api/numbers/**`
* **Core Functions**: `allocateNumber`, `releaseNumber`, `gapAnalysis`.
* **Transactional**: `@Transactional(propagation = REQUIRES_NEW)` to guarantee isolation.
* **Auditing**: Emits `NumberAllocatedEvent` via Spring `ApplicationEventPublisher`.
* **Security**: `@PreAuthorize("hasAuthority('NUMBER_MANAGE')")`.

#### 4. **WorkflowRestServiceImpl**
* **Endpoint**: `/api/workflows/**`
* **Orchestrates**: Starts, pauses, resumes, and aborts workflow instances.
* **State Machine**: Uses `WorkflowStateMachineProvider` (runtime pattern).
* **Event‑Driven**: Publishes `WorkflowStartedEvent` and listens to `WorkflowCompletedEvent`.
* **Security**: `@PreAuthorize("hasAuthority('WORKFLOW_EXECUTE')")`.

#### 5. **OpenApiConfig**
* **Purpose**: Centralised OpenAPI generation.
* **Customisers**: `OpenApiOperationAuthorizationRightCustomizer` injects security scopes.
* **Versioning**: Supports `/v1`, `/v2` via `GroupedOpenApi` beans.
* **UI**: Swagger UI served under `/swagger-ui.html`.
* **Integration**: Consumed by all controllers – single source of truth for API docs.

---

## 5.4 Business Layer (Services)

### 5.4.1 Layer Overview

Services contain the core business rules, coordinate repository access, and emit domain events. They are organised by bounded context (e.g., *DeedEntry*, *NumberManagement*, *Workflow*).

### 5.4.2 Service Inventory (excerpt – first 20 rows, full list in appendix)

| # | Service | Package (simplified) | Description |
|---|---------|----------------------|-------------|
| 1 | ActionServiceImpl | backend.action_logic_impl | Implements actions on **ActionEntity** (create, schedule). |
| 2 | ActionWorkerService | backend.action_logic_impl | Background worker for asynchronous actions. |
| 3 | HealthCheck | backend.adapters_actuator_service | Actuator health endpoint implementation. |
| 4 | ArchiveManagerServiceImpl | backend.archivemanager_logic_impl | Coordinates archiving workflow, interacts with `ArchivingService`. |
| 5 | MockKmService | backend.km_impl_mock | Mock key‑manager for test environments. |
| 6 | XnpKmServiceImpl | backend.km_impl_xnp | Real key‑manager integration with external XNP service. |
| 7 | KeyManagerServiceImpl | backend.km_logic_impl | Core key‑management business rules. |
| 8 | WaWiServiceImpl | backend.adapters_wawi_impl | Integration with external WaWi system. |
| 9 | ArchivingOperationSignerImpl | backend.archive_logic_impl | Signs archiving operations with digital signatures. |
|10 | ArchivingServiceImpl | backend.archive_logic_impl | High‑level archiving service used by controllers. |
|11 | DeedEntryConnectionDaoImpl | backend.api_dao_impl | (Note: DAO – listed here for completeness, used by services). |
|12 | BusinessPurposeServiceImpl | backend.deedentry_logic_impl | Handles business purpose assignment. |
|13 | CorrectionNoteService | backend.deedentry_logic_impl | Manages correction notes on deeds. |
|14 | DeedEntryConnectionServiceImpl | backend.deedentry_logic_impl | Business logic for deed‑entry connections. |
|15 | DeedEntryLogServiceImpl | backend.deedentry_logic_impl | Audit‑log handling for deed entries. |
|16 | DeedEntryServiceImpl | backend.deedentry_logic_impl | Core deed‑entry CRUD and validation. |
|17 | DeedRegistryServiceImpl | backend.deedentry_logic_impl | Registry‑wide operations (search, bulk export). |
|18 | DeedTypeServiceImpl | backend.deedentry_logic_impl | Business rules for deed types. |
|19 | DocumentMetaDataServiceImpl | backend.deedentry_logic_impl | Metadata enrichment for attached documents. |
|20 | HandoverDataSetServiceImpl | backend.deedentry_logic_impl | Business logic for handover data‑sets. |
| … | … | … | … |

*The full table (173 rows) is stored in the appendix of the document.*

### 5.4.3 Service Patterns

| Pattern | Where Used |
|---------|------------|
| **Domain Service** | All `*ServiceImpl` classes – encapsulate business rules. |
| **Transactional Script** | Services that perform a single DB transaction (e.g., `NumberManagementServiceImpl`). |
| **Event‑Driven** | Services publish domain events (`ApplicationEventPublisher`) – e.g., `DeedEntryServiceImpl` emits `DeedEntryCreatedEvent`. |
| **Strategy** | `KeyManagerServiceImpl` selects implementation (`MockKmService` vs `XnpKmServiceImpl`) based on profile. |
| **Facade** | `ArchiveManagerServiceImpl` hides complex archiving steps behind a simple API. |

### 5.4.4 Key Services – Deep Dive (Top 5)

#### 1. **DeedEntryServiceImpl**
* **Core responsibilities**: validation, duplicate detection, state transitions.
* **Transactional**: `@Transactional` – ensures atomic persistence of deed and related logs.
* **Event emission**: `DeedEntryCreatedEvent`, `DeedEntryUpdatedEvent`.
* **Collaboration**: Calls `DeedEntryRepository`, `DeedEntryLogServiceImpl`, `WorkflowServiceImpl`.

#### 2. **NumberManagementServiceImpl**
* **Functions**: `allocateNumber`, `releaseNumber`, `findGaps`.
* **Concurrency control**: Optimistic locking on `UvzNumberManagerEntity`.
* **Batch processing**: Uses Spring Batch for bulk number generation.
* **Auditing**: Persists `NumberAllocationLogEntity` via `NumberAllocationLogRepository`.

#### 3. **WorkflowServiceImpl**
* **Orchestrates**: Starts workflow instances via `WorkflowStateMachineProvider`.
* **State machine**: Implements the *State‑Pattern* using Spring State Machine.
* **Compensation**: Handles rollback on failure via `WorkflowCompensationService`.
* **Metrics**: Emits Prometheus counters for each state transition.

#### 4. **ArchiveManagerServiceImpl**
* **Coordinates**: `ArchivingServiceImpl`, `SignatureServiceImpl`, and external storage adapters.
* **Chunked processing**: Streams large document sets to avoid OOM.
* **Integrity checks**: Verifies digital signatures before finalising archiving.
* **Retry policy**: Configured with Spring Retry (`@Retryable`).

#### 5. **KeyManagerServiceImpl**
* **Strategy selection**: Uses Spring `@Profile` to inject either `MockKmService` (test) or `XnpKmServiceImpl` (production).
* **Operations**: `generateKeyPair`, `rotateKey`, `revokeKey`.
* **Security**: All methods guarded by `@PreAuthorize("hasAuthority('KEY_MANAGE')")`.

---

## 5.5 Domain Layer (Entities)

### 5.5.1 Layer Overview

Entities represent the persistent state of the domain. They are JPA‑annotated POJOs stored in the relational database. The model follows DDD bounded contexts: *Deed*, *NumberManagement*, *Workflow*, *Archiving*.

### 5.5.2 Entity Inventory (excerpt – first 20 rows, full list in appendix)

| # | Entity | Package (simplified) | Description |
|---|--------|----------------------|-------------|
| 1 | ActionEntity | backend.core | Represents an executable action (e.g., archiving, re‑encryption). |
| 2 | ActionStreamEntity | backend.core | Historical stream of action executions. |
| 3 | ChangeEntity | backend.core | Change‑note attached to a deed. |
| 4 | ConnectionEntity | backend.core | Links between deed entries. |
| 5 | CorrectionNoteEntity | backend.core | Correction notes for legal amendments. |
| 6 | DeedCreatorHandoverInfoEntity | backend.core | Metadata for handover of deed creator. |
| 7 | DeedEntryEntity | backend.core | Core deed entry – central aggregate root. |
| 8 | DeedEntryLockEntity | backend.core | Concurrency lock for a deed entry. |