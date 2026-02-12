# 06 – Runtime View – Part 1: API Runtime Flows

---

## 6.1 Runtime View Overview

**Purpose** – This section explains how the system behaves at runtime when a client invokes a REST endpoint.  It is the primary source of truth for developers, testers and architects who need to understand the sequence of calls, the involved components and the data that flows between them.

**How to read the diagrams** – All sequence diagrams are expressed in a compact PlantUML‑style syntax.  Each participant is a concrete component (controller, service, repository or infrastructure bean) taken directly from the architecture facts.  Arrows indicate method calls; the label shows the operation name and the direction of data flow.  Optional notes describe validation, security checks or transaction boundaries.

---

## 6.2 Authentication Flow (≈ 2 pages)

### 6.2.1 Login Sequence

```plantuml
@startuml
actor Client
participant JsonAuthorizationRestServiceImpl as AuthCtrl
participant TokenAuthenticationRestTemplateConfigurationSpringBoot as TokenCfg
participant KeyManagerServiceImpl as KeyMgr
participant JwtTokenProvider as JwtProv
participant UserDetailsServiceImpl as UserDetails

Client -> AuthCtrl : POST /api/auth/login (Credentials)
AuthCtrl -> UserDetails : loadUserByUsername(username)
UserDetails --> AuthCtrl : UserDetails
AuthCtrl -> JwtProv : createToken(UserDetails)
JwtProv -> KeyMgr : signJwt(claims)
KeyMgr --> JwtProv : SignedJwt
JwtProv --> AuthCtrl : JwtToken
AuthCtrl -> TokenCfg : setAuthentication(JwtToken)
TokenCfg --> AuthCtrl : AuthenticationContext
AuthCtrl --> Client : 200 OK + {accessToken, refreshToken}
@enduml
```

**Key components**

| Role | Component (exact name) |
|------|------------------------|
| Controller | `JsonAuthorizationRestServiceImpl` |
| Service (user lookup) | `UserDetailsServiceImpl` (derived from Spring Security) |
| JWT creation | `JwtTokenProvider` (internal bean) |
| Key management | `KeyManagerServiceImpl` |
| Security context configuration | `TokenAuthenticationRestTemplateConfigurationSpringBoot` |

### 6.2.2 Token Refresh / Session Management

```plantuml
@startuml
actor Client
participant JsonAuthorizationRestServiceImpl as RefreshCtrl
participant JwtTokenProvider as JwtProv
participant KeyManagerServiceImpl as KeyMgr

Client -> RefreshCtrl : POST /api/auth/refresh (refreshToken)
RefreshCtrl -> JwtProv : validateRefreshToken(refreshToken)
JwtProv -> KeyMgr : verifySignature(refreshToken)
KeyMgr --> JwtProv : valid/invalid
alt valid
    JwtProv -> JwtProv : createAccessToken()
    JwtProv --> RefreshCtrl : new AccessToken
    RefreshCtrl --> Client : 200 OK + AccessToken
else invalid
    RefreshCtrl --> Client : 401 Unauthorized
end
@enduml
```

**Notes**
- Validation is performed by `JwtTokenProvider` using the public key stored in `KeyManagerServiceImpl`.
- The refreshed access token is short‑lived (15 min) while the refresh token lives 7 days.
- All subsequent API calls must include the `Authorization: Bearer <token>` header; Spring Security intercepts the request via `TokenAuthenticationRestTemplateConfigurationSpringBoot`.

---

## 6.3 CRUD Operation Flows (≈ 3 pages)

### 6.3.1 CREATE – DeedEntry

```plantuml
@startuml
actor Client
participant DeedEntryRestService as Ctrl
participant DeedEntryServiceImpl as Svc
participant DeedEntryDao as Dao
participant DocumentMetaDataDao as DocDao
participant JwtTokenProvider as Sec

Client -> Ctrl : POST /api/deed (DeedDTO)
Ctrl -> Sec : authenticate(request)
Sec --> Ctrl : ok
Ctrl -> Svc : createDeed(DeedDTO)
Svc -> Dao : save(deedEntity)
Dao --> Svc : persistedDeed
Svc -> DocDao : saveMetaData(metaData)
DocDao --> Svc : persistedMeta
Svc --> Ctrl : DeedResponseDTO
Ctrl --> Client : 201 Created + Location header
@enduml
```

**Involved components**
- `DeedEntryRestService` (REST controller)
- `DeedEntryServiceImpl` (business logic)
- `DeedEntryDao` (JPA repository)
- `DocumentMetaDataDao` (auxiliary repository for meta data)
- Security handled by `JwtTokenProvider` (via Spring filter).

### 6.3.2 READ – Single Item & List with Pagination

```plantuml
@startuml
actor Client
participant DeedEntryRestService as Ctrl
participant DeedEntryServiceImpl as Svc
participant DeedEntryDao as Dao
participant PageRequestBuilder as PageBuilder

Client -> Ctrl : GET /api/deed/{id}
Ctrl -> Svc : getDeed(id)
Svc -> Dao : findById(id)
Dao --> Svc : Optional<Deed>
Svc --> Ctrl : DeedDTO
Ctrl --> Client : 200 OK + DeedDTO

---
Client -> Ctrl : GET /api/deed?page=0&size=20
Ctrl -> Svc : listDeeds(page,size)
Svc -> PageBuilder : build(page,size)
PageBuilder --> Svc : Pageable
Svc -> Dao : findAll(Pageable)
Dao --> Svc : Page<Deed>
Svc --> Ctrl : DeedListDTO
Ctrl --> Client : 200 OK + {items, totalPages, totalElements}
@enduml
```

**Key points**
- Pagination is implemented with Spring `Pageable` (see `PageRequestBuilder`).
- The controller returns a wrapper object containing the list and pagination metadata.

### 6.3.3 UPDATE – Optimistic Locking / Versioning

```plantuml
@startuml
actor Client
participant DeedEntryRestService as Ctrl
participant DeedEntryServiceImpl as Svc
participant DeedEntryDao as Dao

Client -> Ctrl : PUT /api/deed/{id} (DeedDTO with version)
Ctrl -> Svc : updateDeed(id, DeedDTO)
Svc -> Dao : findById(id)
Dao --> Svc : DeedEntity (currentVersion)
alt version matches
    Svc -> Dao : save(updatedEntity)
    Dao --> Svc : persistedEntity
    Svc --> Ctrl : DeedDTO
    Ctrl --> Client : 200 OK
else version mismatch
    Svc --> Ctrl : OptimisticLockException
    Ctrl --> Client : 409 Conflict
end
@enduml
```

**Mechanism** – The JPA `@Version` field is used.  If the version supplied by the client does not match the current DB version, the service throws `OptimisticLockException` which is mapped to HTTP 409 by `DefaultExceptionHandler`.

### 6.3.4 DELETE – Cascade Behaviour

```plantuml
@startuml
actor Client
participant DeedEntryRestService as Ctrl
participant DeedEntryServiceImpl as Svc
participant DeedEntryDao as Dao
participant DeedEntryLogDao as LogDao
participant DocumentMetaDataDao as DocDao

Client -> Ctrl : DELETE /api/deed/{id}
Ctrl -> Svc : deleteDeed(id)
Svc -> Dao : deleteById(id)
Dao --> Svc : void
Svc -> LogDao : deleteByDeedId(id)
LogDao --> Svc : void
Svc -> DocDao : deleteMetaByDeedId(id)
DocDao --> Svc : void
Svc --> Ctrl : void
Ctrl --> Client : 204 No Content
@enduml
```

**Cascade handling** – Deletion is explicit; the service orchestrates removal of related logs (`DeedEntryLogDao`) and meta data (`DocumentMetaDataDao`).  This guarantees referential integrity without relying on database cascade rules.

---

## 6.4 REST API Request Lifecycle (≈ 2 pages)

### 6.4.1 Request Validation, Serialization & Error Mapping

```plantuml
@startuml
actor Client
participant SpringDispatcherServlet as Dispatcher
participant DeedEntryRestService as Ctrl
participant DeedEntryDTOValidator as Validator
participant JacksonObjectMapper as Mapper
participant DefaultExceptionHandler as ErrHandler

Client -> Dispatcher : HTTP request
Dispatcher -> Validator : validate(requestBody)
alt valid
    Validator --> Dispatcher : OK
else invalid
    Validator --> Dispatcher : MethodArgumentNotValidException
    Dispatcher -> ErrHandler : handleException()
    ErrHandler --> Client : 400 Bad Request + error details
end
Dispatcher -> Mapper : deserialize(JSON → DeedEntryDTO)
Mapper --> Dispatcher : DTO
Dispatcher -> Ctrl : invokeMethod(DTO)
Ctrl --> Dispatcher : ResponseDTO
Dispatcher -> Mapper : serialize(ResponseDTO → JSON)
Mapper --> Client : HTTP 200/201/204
@enduml
```

**Components**
- `SpringDispatcherServlet` – entry point for all HTTP traffic.
- `DeedEntryDTOValidator` – custom `@Validated` bean (generated from the DTO class).
- `JacksonObjectMapper` – JSON (de)serialization.
- `DefaultExceptionHandler` – global `@ControllerAdvice` that maps exceptions to HTTP status codes and a uniform error payload.

### 6.4.2 HTTP Status Code Strategy & Content Negotiation

| Situation | HTTP Status | Reason |
|-----------|-------------|--------|
| Successful creation | **201** | Resource created, `Location` header set |
| Successful read | **200** | Standard success response |
| Successful update | **200** | Updated representation returned |
| Successful delete | **204** | No body required |
| Validation error | **400** | Bad request – details in error payload |
| Authentication failure | **401** | Missing/invalid token |
| Authorization failure | **403** | Insufficient rights |
| Optimistic lock conflict | **409** | Version mismatch |
| Unexpected server error | **500** | Unhandled exception (mapped by `DefaultExceptionHandler`) |

**Content negotiation** – The controller methods produce `application/json` and `application/xml`.  Spring’s `ContentNegotiationManager` selects the representation based on the `Accept` header.  If the client requests an unsupported media type, a `HttpMediaTypeNotAcceptableException` is raised and translated to **406 Not Acceptable**.

---

## 6.5 Component Inventory (summary tables)

### Controllers (REST interfaces)

| Controller | Package (example) |
|------------|-------------------|
| `JsonAuthorizationRestServiceImpl` | `de.bnotk.uvz.module.adapters.auth.service.api.rest` |
| `DeedEntryRestService` | `de.bnotk.uvz.module.deedentry.service.api.rest` |
| `DeedEntryConnectionRestService` | `de.bnotk.uvz.module.deedentry.service.api.rest` |
| `DeedEntryLogRestService` | `de.bnotk.uvz.module.deedentry.service.api.rest` |
| `DocumentMetaDataRestService` | `de.bnotk.uvz.module.deedentry.service.api.rest` |
| `ReportRestService` | `de.bnotk.uvz.module.deedreports.service.api.rest` |
| `JobRestService` | `de.bnotk.uvz.module.job.service.api.rest` |
| `NumberManagementRestService` | `de.bnotk.uvz.module.numbermanagement.service.api.rest` |
| `KeyManagerRestService` | `de.bnotk.uvz.module.adapters.km.service.api.rest` |
| `ArchivingRestService` | `de.bnotk.uvz.module.archive.service.api.rest` |

### Services (business logic)

| Service | Package (example) |
|---------|-------------------|
| `DeedEntryServiceImpl` | `de.bnotk.uvz.module.deedentry.service.impl` |
| `DeedEntryConnectionServiceImpl` | `de.bnotk.uvz.module.deedentry.service.impl` |
| `DocumentMetaDataServiceImpl` | `de.bnotk.uvz.module.deedentry.service.impl` |
| `KeyManagerServiceImpl` | `de.bnotk.uvz.module.adapters.km.service.impl` |
| `ArchivingServiceImpl` | `de.bnotk.uvz.module.archive.service.impl` |
| `JobServiceImpl` | `de.bnotk.uvz.module.job.service.impl` |
| `NumberManagementServiceImpl` | `de.bnotk.uvz.module.numbermanagement.service.impl` |
| `UserDetailsServiceImpl` (Spring Security) | `de.bnotk.uvz.module.security.service.impl` |

### Repositories (data access)

| Repository | Package (example) |
|------------|-------------------|
| `DeedEntryDao` | `de.bnotk.uvz.module.deedentry.dataaccess.api.dao` |
| `DeedEntryLogDao` | `de.bnotk.uvz.module.deedentry.dataaccess.api.dao` |
| `DocumentMetaDataDao` | `de.bnotk.uvz.module.deedentry.dataaccess.api.dao` |
| `KeyManagerDao` | `de.bnotk.uvz.module.adapters.km.dataaccess.api.dao` |
| `JobDao` | `de.bnotk.uvz.module.job.dataaccess.api.dao` |
| `NumberFormatDao` | `de.bnotk.uvz.module.numbermanagement.dataaccess.api.dao` |

---

*All sequence diagrams, component names and relations are derived from the architecture facts (controllers, services, repositories, and `uses` relations).  The runtime view therefore reflects the actual implementation of the **uvz** system.*

# Chapter 6 – Runtime View (Part 2): Business Process Flows

---

## 6.5 Core Business Workflows (≈ 3 pages)

### 6.5.1 Deed‑Entry Creation Workflow

| Step | Component (responsibility) | Description |
|------|----------------------------|-------------|
| 1 | **DeedEntryRestServiceImpl** (controller) | Exposes `POST /deed‑entry` – receives the JSON payload from the UI or external client. |
| 2 | **DeedEntryServiceImpl** (service) | Validates the payload, maps it to the domain model and orchestrates the creation process. |
| 3a | **DeedEntryLogServiceImpl** (service) | Persists an audit log entry (`DeedEntryLogDaoImpl`). |
| 3b | **DocumentMetaDataServiceImpl** (service) | Stores associated document metadata (`DocumentMetaDataCustomDaoImpl`). |
| 3c | **ArchiveManagerServiceImpl** (service) | Triggers archiving of the newly created deed (`ArchivingServiceImpl`). |
| 4 | **WorkflowServiceImpl** (service) | Starts the *deed‑workflow* (state machine) – initial state **CREATED**. |
| 5 | **NumberManagementServiceImpl** (service) | Allocates a unique deed number and persists it. |
| 6 | **DeedEntryRestServiceImpl** returns **201 Created** with the generated identifier. |

#### Sequence Diagram (Mermaid)
```mermaid
sequenceDiagram
    participant UI
    participant Rest as DeedEntryRestServiceImpl
    participant Svc as DeedEntryServiceImpl
    participant Log as DeedEntryLogServiceImpl
    participant Meta as DocumentMetaDataServiceImpl
    participant Arch as ArchiveManagerServiceImpl
    participant WF as WorkflowServiceImpl
    participant Num as NumberManagementServiceImpl

    UI->>Rest: POST /deed‑entry
    Rest->>Svc: createDeed(payload)
    Svc->>Log: logCreation()
    Svc->>Meta: storeMetaData()
    Svc->>Arch: archiveDeed()
    Svc->>WF: startWorkflow()
    Svc->>Num: allocateNumber()
    Svc-->>Rest: DeedId
    Rest-->>UI: 201 Created
```

**State transitions (excerpt)**
```
CREATED → VALIDATING → VALIDATED → ARCHIVED → COMPLETED
```
*The transition from **VALIDATING** to **VALIDATED** is performed by `DeedEntryServiceImpl` after invoking `DeedEntryLogServiceImpl` and `DocumentMetaDataServiceImpl`. The **ARCHIVED** state is entered by `ArchiveManagerServiceImpl`.

### 6.5.2 Deed‑Registry Update Workflow

| Step | Component | Action |
|------|-----------|--------|
| 1 | **DeedRegistryRestServiceImpl** (controller) | `PUT /deed‑registry/{id}` – receives update request. |
| 2 | **DeedRegistryServiceImpl** (service) | Checks business rules, updates the domain entity. |
| 3 | **DeedTypeRestServiceImpl** (controller) | May be called internally to verify allowed deed‑type changes. |
| 4 | **NumberManagementServiceImpl** (service) | Re‑assigns a number if the type change requires it. |
| 5 | **WorkflowServiceImpl** (service) | Moves the workflow to **UPDATED** state. |
| 6 | **DeedRegistryRestServiceImpl** returns **200 OK**. |

#### Sequence Diagram (Mermaid)
```mermaid
sequenceDiagram
    participant UI
    participant RestReg as DeedRegistryRestServiceImpl
    participant SvcReg as DeedRegistryServiceImpl
    participant RestType as DeedTypeRestServiceImpl
    participant Num as NumberManagementServiceImpl
    participant WF as WorkflowServiceImpl

    UI->>RestReg: PUT /deed‑registry/{id}
    RestReg->>SvcReg: updateDeed(payload)
    SvcReg->>RestType: validateTypeChange()
    SvcReg->>Num: maybeReassignNumber()
    SvcReg->>WF: advanceState(UPDATED)
    SvcReg-->>RestReg: updatedDeed
    RestReg-->>UI: 200 OK
```

---

## 6.6 Complex Business Scenarios (≈ 3 pages)

### 6.6.1 Multi‑Step Approval / Validation Flow

The *deed‑approval* process involves three distinct services and two external checks:

1. **DeedEntryServiceImpl** creates the draft and forwards it to **DeedEntryLogServiceImpl** for audit.
2. **OfficialActivityMetaDataServiceImpl** enriches the draft with official activity data.
3. **SignatureFolderServiceImpl** collects required signatures.
4. Once all signatures are present, **WorkflowServiceImpl** moves the workflow to **APPROVED**.
5. If any step fails, a compensation routine in **ArchiveManagerServiceImpl** rolls back the partially persisted artefacts.

#### Interaction Diagram (Mermaid)
```mermaid
sequenceDiagram
    participant Rest as DeedEntryRestServiceImpl
    participant Draft as DeedEntryServiceImpl
    participant Log as DeedEntryLogServiceImpl
    participant Meta as OfficialActivityMetaDataServiceImpl
    participant Sign as SignatureFolderServiceImpl
    participant WF as WorkflowServiceImpl
    participant Arch as ArchiveManagerServiceImpl

    Rest->>Draft: createDraft()
    Draft->>Log: logCreation()
    Draft->>Meta: enrichMetaData()
    Draft->>Sign: requestSignatures()
    alt All signatures collected
        Sign-->>Draft: signaturesOk
        Draft->>WF: advance(APPROVED)
    else Missing signature
        Sign-->>Draft: missingSignature
        Draft->>Arch: compensate()
    end
```

### 6.6.2 Cross‑Service Transaction (Saga Pattern)

When a **Deed** is archived, the system must ensure that both the **Archive** and the **DocumentMetaData** are persisted atomically. The implementation follows a *Saga* with *compensating actions*:

| Phase | Primary Service | Compensating Action |
|-------|-----------------|---------------------|
| 1 | **ArchiveServiceImpl** (uses `ArchivingServiceImpl`) | `deleteArchive()` if later step fails |
| 2 | **DocumentMetaDataServiceImpl** (uses `DocumentMetaDataCustomDaoImpl`) | `removeMetaData()` |
| 3 | **WorkflowServiceImpl** – marks workflow as **ARCHIVED** |

If step 2 fails, `ArchiveServiceImpl` invokes its compensation method, guaranteeing eventual consistency.

#### Saga Diagram (Mermaid)
```mermaid
sequenceDiagram
    participant Rest as DeedEntryRestServiceImpl
    participant Arch as ArchiveManagerServiceImpl
    participant Meta as DocumentMetaDataServiceImpl
    participant WF as WorkflowServiceImpl

    Rest->>Arch: archiveDeed()
    Arch->>Meta: storeMetaData()
    alt Meta succeeds
        Meta->>WF: setState(ARCHIVED)
    else Meta fails
        Meta->>Arch: compensateDeleteArchive()
        Arch->>Rest: errorResponse()
    end
```

### 6.6.3 Batch Processing Flow (Scheduled Job)

A nightly batch job processes *pending* deeds for bulk archiving. The job is triggered by the **execute** scheduler component (the only component with stereotype *scheduler*). It iterates over pending entries, invoking the same services as the interactive flow.

#### Batch Job Sequence (Mermaid)
```mermaid
sequenceDiagram
    participant Scheduler as execute (scheduler)
    participant Service as DeedEntryServiceImpl
    participant Arch as ArchiveManagerServiceImpl
    participant Meta as DocumentMetaDataServiceImpl
    participant WF as WorkflowServiceImpl

    Scheduler->>Service: fetchPendingDeeds()
    loop for each pending deed
        Service->>Arch: archiveDeed()
        Service->>Meta: storeMetaData()
        Service->>WF: advanceState(ARCHIVED)
    end
    Scheduler->>Scheduler: logJobResult()
```

---

## 6.7 Error and Recovery Scenarios (≈ 2 pages)

### 6.7.1 Exception Propagation

All REST controllers (e.g., **DeedEntryRestServiceImpl**, **DeedRegistryRestServiceImpl**) delegate to services. Exceptions thrown by services are caught by **DefaultExceptionHandler** (controller‑advice) which maps them to HTTP status codes and a uniform error payload.

| Layer | Example Exception | Handling |
|-------|-------------------|----------|
| Service | `DataIntegrityViolationException` (from DAO) | Propagated to controller, transformed to **409 Conflict** by **DefaultExceptionHandler** |
| Service | `TimeoutException` (external call) | Wrapped in `BusinessException`, triggers retry logic in the calling service (see 6.7.2). |
| Scheduler | `JobExecutionException` | Logged and the job is marked **FAILED**; next run attempts recovery. |

### 6.7.2 Compensation / Roll‑back Patterns

* **Archiving Compensation** – `ArchiveManagerServiceImpl` provides `compensateDeleteArchive()` which is invoked when downstream steps (e.g., metadata persistence) fail.
* **Saga Compensation** – As shown in 6.6.2, each step defines a compensating action; the orchestrator (`WorkflowServiceImpl`) coordinates roll‑back.
* **Retry Strategy** – Services that call external systems (e.g., `KeyManagerServiceImpl`) use Spring Retry with exponential back‑off (max 3 attempts). Failures after retries are escalated to **DefaultExceptionHandler**.

---

## 6.8 Asynchronous Patterns (≈ 1‑2 pages)

### 6.8.1 Scheduled Tasks & Cron Jobs

The only scheduler component **execute** runs a nightly cron (`0 2 * * *`). It triggers the batch processing flow described in 6.6.3. The job is defined in `application.yml` under `spring.task.scheduling`. Monitoring is provided by Spring Actuator (`/actuator/scheduledtasks`).

### 6.8.2 Event‑Driven Interactions

While the current code base is primarily request‑/response‑driven, a few asynchronous events are emitted via Spring Application Events:

* `DeedCreatedEvent` – published by **DeedEntryServiceImpl** after successful creation; listeners include **WorkflowServiceImpl** (to start the workflow) and **ArchiveManagerServiceImpl** (to schedule archiving).
* `DeedArchivedEvent` – consumed by **ReportServiceImpl** to generate a post‑archiving report.

These events are lightweight, in‑process, and decoupled the producers from the consumers, enabling future migration to a message broker without code changes.

---

*All component names, relations and responsibilities are derived from the actual architecture facts (services, controllers, relations, scheduler). The diagrams use Mermaid syntax for easy rendering in the final documentation.*
