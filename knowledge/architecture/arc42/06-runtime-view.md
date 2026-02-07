# 06 – Runtime View

---

## 6.1 Overview

The **uvz** system is a Spring‑Boot based backend that exposes a rich set of REST APIs to support deed‑entry management, archiving, key‑management, reporting and workflow orchestration.  All runtime interactions are driven by HTTP requests from the Angular front‑end or external clients, which are handled by **controller** components (REST services) and delegated to **service** components that encapsulate the business logic.  Persistence is performed by JPA repositories (not shown here) and transactional boundaries are defined at the service layer using Spring’s `@Transactional` annotation.

The runtime view is organised around **five key scenarios** that represent the most frequent and most complex interactions in the system.  Each scenario is illustrated with a textual sequence diagram that follows the **SEAGuide** “runtime view sequence” pattern.  The diagrams deliberately avoid duplicating information that is already visible in the component inventory tables – they focus on the flow of messages, the involved layers and the transaction scope.

---

## 6.2 Component Inventory (Runtime Relevant)

| Layer | Stereotype | Example Component | Description |
|-------|------------|-------------------|-------------|
| Presentation | **controller** | `DeedEntryRestServiceImpl` | Exposes CRUD endpoints for deed entries (`/uvz/v1/deedentries/**`). |
| Presentation | **controller** | `KeyManagerRestServiceImpl` | Handles key‑management API (`/uvz/v1/keymanager/**`). |
| Application | **service** | `DeedEntryServiceImpl` | Core business logic for deed entry lifecycle, transaction demarcation. |
| Application | **service** | `ArchiveManagerServiceImpl` | Coordinates archiving of documents and signing tokens. |
| Application | **service** | `JobServiceImpl` | Executes background jobs (retry, metrics). |
| Application | **service** | `NumberManagementServiceImpl` | Validates and formats case numbers. |
| Application | **service** | `ReportServiceImpl` | Generates annual and custom reports. |
| Application | **service** | `WorkflowServiceImpl` *(implicit in endpoints)* | Orchestrates state‑machine driven workflows (`/uvz/v1/workflow/**`). |

> **Note** – The full inventory contains 32 controllers and 173 services; the table lists the most frequently used ones in the runtime scenarios.

---

## 6.3 Key Scenarios

### Scenario 1 – User Authentication & Token Retrieval

```
Client -> AuthController (POST /uvz/v1/action/login) -> AuthService -> UserRepository -> Database
AuthService -> JwtTokenProvider -> Token
Token -> Client
```
*All calls are synchronous HTTP. The `AuthService` method is annotated with `@Transactional(readOnly = true)` because only a read‑only lookup is performed.*

---

### Scenario 2 – Create Deed Entry (CRUD – Create)

```
Client -> DeedEntryRestServiceImpl (POST /uvz/v1/deedentries) -> DeedEntryServiceImpl -> DeedEntryDaoImpl -> Database
DeedEntryServiceImpl -> DocumentMetaDataServiceImpl (for attached documents) -> DocumentMetaDataDaoImpl -> Database
DeedEntryServiceImpl -> ArchiveManagerServiceImpl (optional archiving) -> ArchiveRepository -> Database
DeedEntryServiceImpl -> Transaction Commit
Response (201 Created) -> Client
```
*The `DeedEntryServiceImpl.createDeedEntry(..)` method is the transaction boundary (`@Transactional`). All downstream DAO calls participate in the same transaction.*

---

### Scenario 3 – Read Deed Entries with Pagination

```
Client -> DeedEntryRestServiceImpl (GET /uvz/v1/deedentries?page=0&size=20) -> DeedEntryServiceImpl
DeedEntryServiceImpl -> DeedEntryDaoImpl.findAll(Pageable) -> Database
DeedEntryDaoImpl -> Result Set
DeedEntryServiceImpl -> Mapping to DTOs
Response (200 OK, JSON list) -> Client
```
*Read‑only transaction (`@Transactional(readOnly = true)`. No side effects, therefore no commit required.*

---

### Scenario 4 – Business Process: Document Signing & Archiving (Complex Flow)

```
Client -> DeedEntryRestServiceImpl (POST /uvz/v1/deedentries/{id}/signature-folder) -> DeedEntryServiceImpl
DeedEntryServiceImpl -> SignatureFolderServiceImpl -> DocumentMetaDataServiceImpl
DocumentMetaDataServiceImpl -> DocumentMetaDataDaoImpl -> Database
SignatureFolderServiceImpl -> WaWiServiceImpl (external WA‑Wi system) -> External System
SignatureFolderServiceImpl -> ArchiveManagerServiceImpl -> ArchiveRepository -> Database
SignatureFolderServiceImpl -> Transaction Commit (all steps succeed)
Response (200 OK) -> Client
```
*This scenario spans multiple services and external system calls. The outermost service (`DeedEntryServiceImpl`) defines the transaction boundary. If any downstream call fails, Spring rolls back the whole transaction, guaranteeing consistency between the deed entry, its metadata and the archive.*

---

### Scenario 5 – Error Handling & Retry of Background Job

```
Scheduler -> JobServiceImpl (triggered by Quartz) -> JobRestServiceImpl (GET /uvz/v1/job/{type}/state)
JobRestServiceImpl -> JobRepository -> Database
JobServiceImpl -> if job failed -> ReencryptionJobRestServiceImpl (POST /uvz/v1/job/reencryption/{jobId}/document)
ReencryptionJobRestServiceImpl -> DocumentService -> Database
JobServiceImpl -> Update Job status (SUCCESS/FAILED) -> JobRepository -> Database
```
*Background jobs run in their own transaction (`@Transactional`). On failure the job status is persisted and the scheduler may retry according to the configured policy.*

---

## 6.4 Interaction Patterns

| Pattern | Description | Example Components |
|---------|-------------|--------------------|
| **Synchronous HTTP** | Client initiates a request, waits for response. All REST controllers use this pattern. | `DeedEntryRestServiceImpl`, `KeyManagerRestServiceImpl` |
| **Asynchronous Job Processing** | Long‑running work is delegated to a background job (Quartz scheduler). The caller receives an immediate acknowledgment and can poll status. | `JobServiceImpl`, `ReencryptionJobRestServiceImpl` |
| **External System Call (Fire‑and‑Forget)** | Service invokes an external system (e.g., WA‑Wi) without waiting for a response; errors are handled via callbacks or retries. | `WaWiServiceImpl` (called from `SignatureFolderServiceImpl`) |
| **Event‑Driven (Future)** | Currently not used; placeholders exist for future Kafka integration (see `adapter` components). | – |

---

## 6.5 Transaction Boundaries & Consistency

1. **Service‑Level Transactions** – Every public method in a `*ServiceImpl` class that mutates state is annotated with `@Transactional`. The transaction starts when the method is entered and is committed when the method returns without exception.
2. **Read‑Only Transactions** – Methods that only read data are marked `@Transactional(readOnly = true)` to optimise locking and avoid unnecessary flushes.
3. **Propagation Rules** – Default `REQUIRED` propagation ensures that nested service calls participate in the same transaction. For external calls (e.g., WA‑Wi) the transaction is **not** propagated; failures are caught and translated into domain exceptions, triggering a rollback.
4. **Rollback Scenarios** – Any unchecked exception thrown from a service method triggers a rollback. Specific business exceptions (`DeedEntryValidationException`, `ArchiveException`) are also configured to cause rollback via `@Transactional(rollbackFor = ...)`.
5. **Compensating Actions** – For operations that involve external systems (Scenario 4), compensating actions are defined in the service layer (e.g., `ArchiveManagerServiceImpl.undoArchive(..)`) and are executed in the `@Transactional` rollback hook.

---

## 6.6 Quality Scenarios (Runtime)

| # | Quality Goal | Metric | Acceptance Criterion |
|---|--------------|--------|----------------------|
| 1 | **Response Time** – CRUD operations must complete within 200 ms under normal load. | Average latency (ms) measured by APM. | ≤ 200 ms for 95 % of requests. |
| 2 | **Throughput** – System must handle 150 req/s for `/uvz/v1/deedentries` endpoints. | Requests per second (RPS). | ≥ 150 RPS sustained for 10 min. |
| 3 | **Reliability** – Background jobs must succeed ≥ 99 % without manual intervention. | Job success rate. | ≥ 99 % of scheduled jobs complete successfully. |
| 4 | **Consistency** – No partial updates when a multi‑service transaction fails. | Number of inconsistent records detected by nightly audit. | 0 inconsistent records. |
| 5 | **Scalability** – Adding a second backend instance must linearly increase throughput. | Throughput before/after scaling. | ≥ 90 % increase when scaling from 1→2 instances. |

---

## 6.7 Summary

The runtime view of **uvz** is dominated by **synchronous REST interactions** orchestrated by a thin controller layer and a robust service layer that defines clear transaction boundaries.  Asynchronous processing is limited to scheduled jobs, which are isolated in their own transactional context.  The five scenarios above capture the most critical paths, illustrating how the system guarantees consistency, handles errors, and meets the defined quality goals.

---

*Document generated automatically from architecture facts on 2026‑02‑07.*