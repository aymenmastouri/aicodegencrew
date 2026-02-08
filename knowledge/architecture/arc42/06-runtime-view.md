# 06 – Runtime View

## 6.1 Overview
The **uvz** system is a Spring‑Boot based backend exposing a rich set of REST APIs (196 endpoints) that are consumed by an Angular front‑end and external services.  Runtime behaviour is driven by HTTP requests that traverse the **presentation** layer (controllers), the **application** layer (services) and the **data‑access** layer (repositories).  All interactions are synchronous HTTP calls, except for internal asynchronous job processing handled by Spring’s `@Async` and scheduled tasks.

| Layer | Stereotype | Component count |
|-------|------------|-----------------|
| Presentation | controller | 32 |
| Application | service | 184 |
| Domain | entity | 360 |
| Data‑Access | repository | 38 |
| Infrastructure | configuration | 1 |
| Unknown | adapter / guard / rest_interface … | 81 |

The runtime view is organised around **key business scenarios** that illustrate typical request‑response flows, error handling and transaction boundaries.

---
## 6.2 Key Scenarios
Below are five representative scenarios.  Each scenario is expressed as a **text‑based sequence diagram** (PlantUML‑compatible) followed by a concise narrative.

### Scenario 1 – User Authentication
```
@startuml
actor Client
participant AuthController as AC
participant AuthService as AS
participant UserRepository as UR
participant Database as DB

Client -> AC : POST /jsonauth/user/to/authorization/service
activate AC
AC -> AS : authenticate(credentials)
activate AS
AS -> UR : findByUsername()
activate UR
UR -> DB : SELECT * FROM users WHERE ...
activate DB
DB --> UR : UserEntity
deactivate DB
UR --> AS : UserEntity
deactivate UR
AS --> AC : JWT token
deactivate AS
AC --> Client : 200 OK + token
deactivate AC
@enduml
```
*The authentication flow is fully synchronous.  The JWT token is generated in `AuthService` and returned to the client.  The transaction is bounded to the `UserRepository` call – any failure rolls back the read‑only transaction.*

### Scenario 2 – Create Deed Entry (CRUD – Create)
```
@startuml
actor Client
participant DeedEntryRestServiceImpl as DE
participant DeedEntryService as DES
participant DeedEntryRepository as DER
participant Database as DB

Client -> DE : POST /uvz/v1/deedentries
activate DE
DE -> DES : createDeedEntry(dto)
activate DES
DES -> DER : save(entity)
activate DER
DER -> DB : INSERT
activate DB
DB --> DER : success
deactivate DB
DER --> DES : persistedEntity
deactivate DER
DES --> DE : DTO with id
deactivate DES
DE --> Client : 201 Created
deactivate DE
@enduml
```
*The service layer (`DeedEntryService`) contains the business rules (validation, duplicate checks).  The transaction spans the repository call; Spring’s `@Transactional` ensures atomic commit.*

### Scenario 3 – Retrieve Deed Entries with Pagination
```
@startuml
actor Client
participant DeedEntryRestServiceImpl as DE
participant DeedEntryService as DES
participant DeedEntryRepository as DER
participant Database as DB

Client -> DE : GET /uvz/v1/deedentries?page=0&size=20
activate DE
DE -> DES : findPage(page,size)
activate DES
DES -> DER : findAll(PageRequest)
activate DER
DER -> DB : SELECT … LIMIT 20 OFFSET 0
activate DB
DB --> DER : Page<DeedEntry>
deactivate DB
DER --> DES : Page<DeedEntry>
deactivate DER
DES --> DE : DTO list
deactivate DES
DE --> Client : 200 OK
deactivate DE
@enduml
```
*Pagination is implemented via Spring Data `PageRequest`.  The read‑only transaction is limited to the repository call.*

### Scenario 4 – Document Archiving Process (Complex Business Flow)
```
@startuml
actor Scheduler
participant ArchivingRestServiceImpl as AR
participant ArchivingService as AS
participant DocumentRepository as DR
participant CryptoService as CS
participant ArchiveStorage as ASrc

Scheduler -> AR : POST /uvz/v1/archiving/sign-submission-token
activate AR
AR -> AS : startArchiving()
activate AS
AS -> DR : findPendingDocuments()
activate DR
DR --> AS : List<Document>
deactivate DR
AS -> CS : encrypt(document)
activate CS
CS --> AS : EncryptedBlob
deactivate CS
AS -> ASrc : store(blob)
activate ASrc
ASrc --> AS : OK
deactivate ASrc
AS -> DR : markArchived(ids)
activate DR
DR --> AS : update count
deactivate DR
AS --> AR : result summary
deactivate AS
AR --> Scheduler : 200 OK
deactivate AR
@enduml
```
*Triggered by a scheduled job, the flow spans multiple services and repositories.  The overall process is wrapped in a **Saga‑style** transaction: each step is committed individually; failures trigger compensating actions (e.g., delete stored blob).*

### Scenario 5 – Error Handling for Invalid Deed Entry
```
@startuml
actor Client
participant DeedEntryRestServiceImpl as DE
participant DeedEntryService as DES
participant DefaultExceptionHandler as EH

Client -> DE : POST /uvz/v1/deedentries (invalid payload)
activate DE
DE -> DES : createDeedEntry(dto)
activate DES
DES -> DES : validate(dto)
DES --> DES : throws ValidationException
deactivate DES
DES --> DE : ValidationException
DE -> EH : handleException(e)
activate EH
EH --> Client : 400 Bad Request + error body
deactivate EH
deactivate DE
@enduml
```
*All REST controllers delegate to `DefaultExceptionHandler` (a `@ControllerAdvice`) which maps domain exceptions to appropriate HTTP status codes.*

---
## 6.3 Interaction Patterns
| Pattern | Description | Example Components |
|---------|-------------|---------------------|
| **Synchronous HTTP request/response** | Typical client‑to‑backend call, fully blocking until a response is returned. | `AuthController → AuthService → UserRepository` |
| **Asynchronous job processing** | Background jobs started via REST endpoint or scheduler, executed by Spring `@Async` workers. | `ArchivingRestServiceImpl → ArchivingService → CryptoService` |
| **Saga‑style compensation** | Long‑running multi‑step processes where each step commits independently; failures trigger compensating actions. | Document archiving flow (see Scenario 4) |
| **Exception handling via ControllerAdvice** | Centralised mapping of exceptions to HTTP status codes. | `DefaultExceptionHandler` |
| **Pagination & streaming** | Efficient data retrieval for large collections. | `DeedEntryRestServiceImpl → DeedEntryRepository` |

---
## 6.4 Transaction Boundaries
*All write‑operations are annotated with Spring’s `@Transactional` at the **service** layer.*  The following table summarises the main transaction scopes:

| Use‑case | Transaction Scope | Commit / Rollback Trigger |
|----------|-------------------|---------------------------|
| Create / Update Deed Entry | `DeedEntryService.createDeedEntry` (single DB transaction) | Exception → rollback, success → commit |
| Document Archiving (Saga) | Individual steps (`encrypt`, `store`, `markArchived`) each in their own transaction | Failure in a step → compensating action, otherwise commit |
| Authentication | Read‑only transaction in `UserRepository` | No write, so only session close |
| Bulk Capture (`/uvz/v1/deedentries/bulkcapture`) | `BulkCaptureService.processBatch` (single transaction for batch) | Any validation error → rollback whole batch |
| Job Scheduling (`/uvz/v1/job/retry`) | Scheduler‑initiated transaction in `JobService` | Failure → retry logic, otherwise commit |

### Transaction Management Details
* **Propagation** – `REQUIRED` is used for most service methods; `REQUIRES_NEW` for compensating actions in the archiving saga.
* **Isolation** – Default `READ_COMMITTED`; high‑contention endpoints (e.g., lock/unlock) use `SERIALIZABLE` via explicit `@Transactional(isolation = Isolation.SERIALIZABLE)`.
* **Rollback rules** – All unchecked exceptions trigger rollback; checked `BusinessException` is also configured to rollback via `@Transactional(rollbackFor = BusinessException.class)`.

---
## 6.5 Quality Scenarios
| Scenario | Metric | Target |
|----------|--------|--------|
| **Authentication latency** | 95th percentile response time | ≤ 150 ms |
| **Deed entry creation throughput** | Requests per second under load | ≥ 200 rps |
| **Archiving job completion** | End‑to‑end processing time per batch (100 docs) | ≤ 30 s |
| **Error‑response consistency** | Percentage of errors mapped to proper HTTP codes | 100 % |
| **Transaction integrity** | % of failed transactions correctly rolled back (simulated fault injection) | 100 % |

---
## 6.6 Summary
The runtime view of **uvz** is dominated by synchronous REST interactions that flow through a clean three‑tier stack.  Asynchronous background jobs and saga‑style compensation handle long‑running processes such as document archiving.  Transaction boundaries are clearly defined at the service layer, ensuring data consistency and enabling robust error handling.

*All diagrams and tables are derived from the actual code base (196 REST endpoints, 32 controllers, 184 services, 38 repositories).*
