# 06 - Runtime View

## 6.1 Overview

The **uvz** system is a Spring‑Boot based micro‑service that exposes a rich set of REST endpoints (95 in total) for managing deeds, documents, archiving, key management and reporting.  The runtime view focuses on the **backend container** (`container.backend`) which hosts all Java components (controllers, services, repositories, configuration).  The frontend (Angular) interacts with the backend via HTTP/HTTPS; Playwright is used for end‑to‑end UI tests but does not participate in the production runtime.

At runtime the system follows a **layered architecture** (presentation → application → domain → data‑access → infrastructure).  Requests enter through a **REST controller**, are delegated to **service beans** (transactional business logic), which in turn call **repository beans** (JPA / JDBC) and finally the **database**.  Cross‑cutting concerns (security, logging, exception handling) are applied by Spring **interceptors**, **guards**, and **exception handlers**.

Key runtime characteristics:

- **Synchronous HTTP/JSON** communication for the majority of use‑cases.
- **Transactional boundaries** are defined at the service layer (`@Transactional`).
- **Asynchronous processing** is limited to background jobs (e.g., re‑encryption, bulk capture) executed by Spring `@Scheduled` beans and the `JobRestServiceImpl`.
- **Stateless services** – each request is processed independently; state is persisted in the relational database.
- **Scalability** – the backend container can be horizontally scaled behind a load balancer; the stateless nature of controllers and services enables simple scaling.

The following sections illustrate the most important runtime scenarios, interaction patterns and transaction handling.

---

## 6.2 Key Scenarios

### Scenario 1: User Authentication & Token Issuance

```
Client -> AuthController (JsonAuthorizationRestServiceImpl) -> AuthService -> UserRepository -> Database
```

1. **POST /uvz/v1/action/login** (handled by `JsonAuthorizationRestServiceImpl`).
2. The controller validates the request body and forwards credentials to `AuthService`.
3. `AuthService` loads the user via `UserRepository` (JPA) and verifies the password.
4. On success a JWT token is created and returned to the client.
5. The token is stored in the security context for subsequent requests.

**Key points**: synchronous flow, service layer is `@Transactional(readOnly = true)`, exception handling is delegated to `DefaultExceptionHandler`.

---

### Scenario 2: Create Deed Entry (CRUD – Create)

```
Client -> DeedEntryRestServiceImpl -> DeedEntryService -> DeedEntryRepository -> Database
```

1. **POST /uvz/v1/deedentries** (controller `DeedEntryRestServiceImpl`).
2. Input DTO is validated (Spring `@Valid`).
3. The controller calls `DeedEntryService.createDeedEntry()` which is annotated with `@Transactional`.
4. Service performs business rules (e.g., uniqueness checks) and persists the entity via `DeedEntryRepository`.
5. After commit, an audit event is published to the `EventBus` (asynchronous) and a `201 Created` response with the new resource location is returned.

---

### Scenario 3: Read Deed Entries with Pagination

```
Client -> DeedEntryRestServiceImpl -> DeedEntryService -> DeedEntryRepository -> Database
```

1. **GET /uvz/v1/deedentries?page=0&size=20**.
2. The controller extracts pagination parameters and forwards them to `DeedEntryService.findAll(page, size)`.
3. Service invokes `DeedEntryRepository.findAll(Pageable)` which returns a `Page<DeedEntry>`.
4. The result is mapped to a DTO list and returned with pagination metadata (`totalElements`, `totalPages`).
5. No transaction is opened (read‑only) – the repository method runs in a non‑transactional context, relying on the underlying connection pool.

---

### Scenario 4: Complex Business Process – Document Archiving Workflow

```
Client -> ArchivingRestServiceImpl -> ArchivingService -> DocumentRepository -> ArchiveStorageService -> Database
```

1. **POST /uvz/v1/archiving/sign-submission-token** initiates the archiving workflow.
2. `ArchivingRestServiceImpl` validates the request and calls `ArchivingService.startArchiving()`.
3. The service creates an `ArchivingJob` entity (transactional) and persists it.
4. A **domain event** `ArchivingStarted` is published; a background worker (`@Scheduled` in `ArchivingJobProcessor`) picks up the job.
5. The worker retrieves the associated documents via `DocumentRepository`, generates a cryptographic hash, and stores the binary in `ArchiveStorageService` (external storage, e.g., S3).
6. Upon successful storage, the job status is updated, and a callback endpoint `/uvz/v1/documents/archiving-finished` is invoked to notify external systems.
7. If any step fails, the transaction is rolled back, the job status is set to `FAILED`, and an error event triggers a retry mechanism.

**Interaction pattern**: synchronous request → asynchronous background processing → callback.

---

### Scenario 5: Global Error Handling & Fallback

```
Client -> AnyController -> Service -> Repository -> Database
          |
          v
   DefaultExceptionHandler -> ErrorResponse
```

1. Any uncaught exception (e.g., `DataIntegrityViolationException`) propagates up the call stack.
2. `DefaultExceptionHandler` (annotated with `@ControllerAdvice`) intercepts the exception.
3. It maps the exception to a standardized `ErrorResponse` JSON payload (fields: `timestamp`, `status`, `error`, `message`, `path`).
4. The HTTP status code is derived from the exception type (e.g., 409 for conflict, 400 for bad request).
5. The client receives a deterministic error response, enabling robust UI handling.

---

## 6.3 Interaction Patterns

| Pattern | Description | Example Components |
|---------|-------------|--------------------|
| **Synchronous HTTP** | Direct request‑response cycle; the caller blocks until the response is returned. | `DeedEntryRestServiceImpl` → `DeedEntryService` → `DeedEntryRepository` |
| **Asynchronous Event‑Driven** | Domain events are published and processed by background workers; decouples long‑running work from the request thread. | `ArchivingService` → `EventBus` → `ArchivingJobProcessor` (scheduled) |
| **Scheduled Jobs** | Periodic tasks executed by Spring `@Scheduled`. Used for re‑encryption, bulk capture, cleanup. | `ReencryptionJobRestServiceImpl` (trigger) → `ReencryptionScheduler` |
| **Callback/Webhook** | Backend calls external endpoint after async processing completes. | `ArchivingJobProcessor` → external `/uvz/v1/documents/archiving-finished` |
| **Exception‑Driven Flow** | Centralized error handling transforms exceptions into HTTP error responses. | `DefaultExceptionHandler` |

No message‑queue or broker is currently part of the runtime; all async work is handled internally via Spring’s task executor.

---

## 6.4 Transaction Boundaries

| Layer | Transaction Scope | Roll‑back Triggers |
|-------|-------------------|-------------------|
| **Controller** | No transaction (stateless). | N/A |
| **Service** | `@Transactional` (default propagation = REQUIRED). | RuntimeException, checked exceptions annotated with `@Transactional(rollbackFor=…)` |
| **Repository** | Executes within the service transaction; uses Spring Data JPA. | Database constraint violation, deadlock, explicit `TransactionStatus.setRollbackOnly()` |
| **Background Job** | Each job execution starts a new transaction in the worker thread. | Any uncaught exception inside the job processing method |

### Example: Deed Entry Creation

```java
@Service
@Transactional
public DeedEntry createDeedEntry(CreateDto dto) {
    // business validation
    if (repository.existsByReference(dto.getReference())) {
        throw new DuplicateKeyException("Reference already exists");
    }
    DeedEntry entity = mapper.toEntity(dto);
    repository.save(entity); // commit at method exit
    eventBus.publish(new DeedCreatedEvent(entity.getId()));
    return entity;
}
```

If `DuplicateKeyException` is thrown, the transaction is rolled back automatically, and the controller receives the exception which is transformed by `DefaultExceptionHandler` into a **409 Conflict** response.

---

## 6.5 Summary Table of Core Runtime Components

| Component | Stereotype | Package (excerpt) | Primary Responsibility |
|-----------|------------|-------------------|------------------------|
| `ActionRestServiceImpl` | controller | `...rest` | Handles generic actions (POST /action/{type}) |
| `DeedEntryRestServiceImpl` | controller | `...rest` | CRUD for deed entries |
| `ArchivingRestServiceImpl` | controller | `...rest` | Starts archiving workflow |
| `AuthService` (implicit) | service | `...service` | Authentication & JWT generation |
| `DeedEntryService` | service | `...service` | Business rules for deed lifecycle |
| `ArchivingService` | service | `...service` | Orchestrates document archiving, publishes events |
| `DeedEntryRepository` | repository | `...repository` | JPA access to `deed_entry` table |
| `DocumentRepository` | repository | `...repository` | Access to document metadata |
| `DefaultExceptionHandler` | component | `...exception` | Global error translation |
| `JobRestServiceImpl` | controller | `...rest` | Exposes job management endpoints |
| `ReencryptionJobRestServiceImpl` | controller | `...rest` | Triggers re‑encryption jobs |

---

*The runtime view presented here follows the SEAGuide principle “Graphics First”. The textual description complements the sequence diagrams above and the component table, allowing stakeholders to understand request flows, transaction scopes and asynchronous processing without redundant duplication.*
