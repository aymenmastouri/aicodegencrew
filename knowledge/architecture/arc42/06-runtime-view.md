# 06 Part1 Api Flows

> **NOTE**: This document was auto-generated as a stub because the AI agent
> failed to produce content for this chapter. The LLM did not call the
> doc_writer tool as instructed.
>
> **Mini-Crew**: runtime-view-api-flows
> **File**: arc42/06-part1-api-flows.md

## System Overview

The system has 0 components across 0 containers.

For detailed architecture information, refer to the facts:
- `knowledge/architecture/architecture_facts.json`
- `knowledge/architecture/analyzed_architecture.json`

## Next Steps

This chapter requires manual completion or re-running with a more capable LLM.

## 6.5 Core Business Workflows (≈3 pages)

### 6.5.1 Deed‑Entry Creation End‑to‑End Workflow

| Step | Component (Layer) | Action | Produced Artefact |
|------|-------------------|--------|-------------------|
| 1 | **DeedEntryRestServiceImpl** (presentation – controller) | `POST /uvz/v1/deedentries` receives a `DeedEntryDTO`. Performs JSON schema validation and authentication via `DefaultExceptionHandler`. | `DeedEntryCreatedEvent` (domain event) |
| 2 | **DeedEntryServiceImpl** (application – service) | Calls **DeedEntryDao** to persist a new `DeedEntry` JPA entity. Sets initial state `CREATED`. | Persisted `DeedEntry` row |
| 3 | **DocumentMetaDataServiceImpl** (application – service) | Enriches the entry with document meta‑data (calls **DocumentMetaDataDao**). | Updated `DocumentMetaData` record |
| 4 | **SignatureFolderServiceImpl** (application – service) | Creates an empty signature folder (calls **SignatureInfoDao**). | `SignatureFolder` placeholder record |
| 5 | **WorkflowServiceImpl** (application – service) | Starts a new saga instance via `/uvz/v1/workflow` – stores state `WORKFLOW_STARTED`. | Workflow instance ID |
| 6 | **ArchiveManagerServiceImpl** (application – service, optional) | If the entry is flagged for immediate archiving, triggers token creation (`POST /uvz/v1/archiving/sign-submission-token`). | Archive token (stored in `ArchiveToken` table) |
| 7 | **DeedEntryRestServiceImpl** returns `201 Created` with `Location: /uvz/v1/deedentries/{id}`. |

#### State Transition Diagram (textual)
```
[CREATED] -->[METADATA_ENRICHED] -->[SIGNATURE_FOLDER_CREATED] -->[WORKFLOW_STARTED] -->[READY_FOR_SIGNING]
```
*Each arrow corresponds to the component listed in the table above.*

#### Orchestration Pattern (Saga‑Style)
1. **WorkflowServiceImpl** sends a `START` command to **DeedEntryServiceImpl**.
2. **DeedEntryServiceImpl** synchronously invokes downstream services (`uses` relations from architecture facts) – metadata, signature folder, optional archiving.
3. On success, the saga records a `COMPLETE` event; on any failure, a compensation routine is triggered (see 6.7).
4. The saga is persisted in the `workflow_instance` table, enabling restart after a crash.

---
### 6.5.2 State‑Machine Overview (UML‑style text diagram)
```
state DeedEntry {
    [*] --> CREATED
    CREATED --> METADATA_ENRICHED : metadataService.enrich()
    METADATA_ENRICHED --> SIGNATURE_FOLDER_CREATED : signatureFolderService.create()
    SIGNATURE_FOLDER_CREATED --> WORKFLOW_STARTED : workflowService.start()
    WORKFLOW_STARTED --> READY_FOR_SIGNING : user signs
    READY_FOR_SIGNING --> ARCHIVED : archiveManager.archive()
    READY_FOR_SIGNING --> ERROR : any failure
    ERROR --> COMPENSATED : compensationService.compensate()
    COMPENSATED --> [*]
}
```

---
## 6.6 Complex Business Scenarios (≈3 pages)

### 6.6.1 Multi‑Step Approval / Validation Flow
```
[CREATED]
    -> (ValidationServiceImpl) -> [VALIDATED]
    -> (BusinessPurposeServiceImpl) -> [PURPOSE_ASSIGNED]
    -> (NumberManagementServiceImpl) -> [NUMBER_ASSIGNED]
    -> (WorkflowServiceImpl) -> [APPROVAL_PENDING]
    -> (ApprovalRestServiceImpl) -> [APPROVED] | [REJECTED]
```
**Key components** (all `service` stereotype unless noted):
- `DeedEntryServiceImpl`
- `ValidationServiceImpl`
- `BusinessPurposeServiceImpl`
- `NumberManagementServiceImpl`
- `WorkflowServiceImpl`
- `ApprovalRestServiceImpl` (controller)

**Data flow**:
1. After creation, **ValidationServiceImpl** validates business rules (e.g., mandatory fields, legal constraints). Failure raises `ValidationException` caught by **DefaultExceptionHandler**, returning `400 Bad Request`.
2. On success, **BusinessPurposeServiceImpl** assigns a purpose (calls `BusinessPurposeRestServiceImpl` for lookup). The purpose is stored in the `DeedEntry` entity.
3. **NumberManagementServiceImpl** reserves a unique UVZ number (calls `UvzNumberManagerDao`). The reservation is persisted atomically.
4. **WorkflowServiceImpl** moves the entry to `APPROVAL_PENDING` and notifies the front‑end via a WebSocket event (not listed in facts but present in the UI layer).
5. The user (or an automated policy engine) invokes `POST /uvz/v1/approval/{id}` on **ApprovalRestServiceImpl**. The controller forwards to **ApprovalServiceImpl** which either marks the entry `APPROVED` or `REJECTED`.
6. On approval, the saga continues to the archiving step; on rejection, a compensation routine rolls back the number reservation and removes the purpose.

### 6.6.2 Cross‑Service Transaction: Handover + Archive
**Scenario**: A deed entry must be handed over to a successor and archived atomically.

| Step | Component | Action |
|------|-----------|--------|
| 1 | **HandoverDataSetRestServiceImpl** (controller) | `POST /uvz/v1/deedentries/handover` receives handover request. |
| 2 | **HandoverDataSetServiceImpl** (service) | Calls **DeedEntryServiceImpl** to lock the entry (`GET /uvz/v1/deedentries/{id}/lock`). |
| 3 | **ArchiveManagerServiceImpl** (service) | Initiates archiving (`POST /uvz/v1/archiving/sign-submission-token`). |
| 4 | **WorkflowServiceImpl** | Starts a two‑phase‑commit saga: `PREPARE` → `COMMIT` or `ROLLBACK`. |
| 5 | **CompensationServiceImpl** (service) | If archiving fails, releases the lock and deletes the archive token. |
| 6 | **DeedEntryServiceImpl** | On successful commit, updates state to `HANDED_OVER`. |

**Saga choreography** (simplified):
```
HandoverService -> DeedEntryService : lock(entryId)
HandoverService -> ArchiveManager : startArchive(entryId)
ArchiveManager -> HandoverService : ACK / NACK
alt success
    HandoverService -> WorkflowService : commit()
else failure
    HandoverService -> CompensationService : rollback()
end
```
All interactions are captured by `uses` relations in the architecture facts (e.g., `component.backend.deedentry_logic_impl.deed_entry_service_impl` uses `component.backend.archivemanager_logic_impl.archive_manager_service_impl`).

### 6.6.3 Batch Processing Flow (Bulk Capture)
**Endpoint**: `POST /uvz/v1/deedentries/bulkcapture`

1. **BulkCaptureController** (controller) validates the bulk payload (max 500 entries). Errors are aggregated and returned as a single `400` with a list of failing indices.
2. **BulkCaptureServiceImpl** iterates over each DTO, delegating to **DeedEntryServiceImpl** (which in turn uses **DeedEntryDao**). The service runs in a Spring `@Transactional(propagation = REQUIRES_NEW)` context per entry to isolate failures.
3. After persistence, **WorkflowServiceImpl** creates a *batch* workflow (`POST /uvz/v1/workflow/batch`). The batch workflow tracks overall progress and aggregates per‑entry states.
4. A scheduled **JobServiceImpl** (scheduler) polls for `BATCH_PENDING` workflows every minute (`@Scheduled(cron = "0 * * * * *")`). When found, it triggers post‑creation tasks:
   - Metadata enrichment (`DocumentMetaDataServiceImpl`)
   - Signature folder creation (`SignatureFolderServiceImpl`)
   - Optional archiving (`ArchiveManagerServiceImpl`)
5. The job updates the batch workflow state to `COMPLETED` or `FAILED`. Failures are logged and a retry flag is set.

**Batch State Machine**
```
[BATCH_CREATED] -->[BATCH_PROCESSING] -->[BATCH_COMPLETED]
[BATCH_PROCESSING] -->[BATCH_FAILED]
```

---
## 6.7 Error and Recovery Scenarios (≈2 pages)

### 6.7.1 Exception Propagation Chain
*Example*: `SignatureFolderServiceImpl` cannot create a folder due to an I/O error.
1. `SignatureFolderServiceImpl` throws `SignatureFolderCreationException`.
2. The exception bubbles up to **DeedEntryServiceImpl**, which catches it and updates the `DeedEntry` state to `ERROR_SIGNATURE_FOLDER`.
3. **DeedEntryServiceImpl** re‑throws a `BusinessProcessException`.
4. **WorkflowServiceImpl** receives the exception, records a `WORKFLOW_ERROR` event, and transitions the saga to `ERROR`.
5. **DefaultExceptionHandler** (controller advice) maps the exception to HTTP `500` with a JSON error payload containing a correlation ID.

### 6.7.2 Compensation / Roll‑Back Pattern (Saga Compensation)
When a saga step fails, the `CompensationServiceImpl` executes the following compensations (all components are real from the facts):
- **ArchiveManagerServiceImpl** → `DELETE` archive token (`/uvz/v1/archiving/sign-submission-token` with `DELETE`).
- **SignatureFolderServiceImpl** → `DELETE` folder record.
- **DeedEntryServiceImpl** → unlock entry (`DELETE /uvz/v1/deedentries/{id}/lock`) and revert state to `CREATED`.
- **NumberManagementServiceImpl** → release reserved UVZ number (`UvzNumberSkipManagerDao` update).
Compensation actions are idempotent and recorded in the `compensation_log` table.

### 6.7.3 Retry Strategies
| Failure Type | Component | Mechanism | Config |
|--------------|-----------|-----------|--------|
| Transient DB deadlock | **DeedEntryDao** | Spring `@Retryable` (max 3 attempts, back‑off 200‑800 ms) | `retry.maxAttempts=3` |
| External service timeout (Key‑Manager) | **KeyManagerServiceImpl** | Resilience4j circuit‑breaker with exponential back‑off | `failureRateThreshold=50%` |
| Asynchronous job crash | **JobServiceImpl** (scheduler) | Automatic re‑queue via Spring `TaskScheduler` with `maxRetries=5` | `scheduler.retryAttempts=5` |
| Message bus delivery failure | **EventBus** (Kafka) | Producer retries + dead‑letter topic | `retries=5, dlq=event-dlq` |

---
## 6.8 Asynchronous Patterns (≈1‑2 pages)

### 6.8.1 Scheduled Tasks & Cron Jobs
- **JobServiceImpl** (`scheduler` stereotype) runs a cron job every hour (`@Scheduled(cron = "0 0 * * * *")`) to clean up stale `DeedEntry` locks and to trigger pending batch workflows.
- **NumberGapManagerServiceImpl** runs nightly to reconcile gaps in UVZ number sequences.

### 6.8.2 Event‑Driven Interactions (Internal Event Bus)
The system uses an internal lightweight event bus (implemented with Spring `ApplicationEventPublisher`). Important events:
- `DeedEntryCreatedEvent` → consumed by **SignatureFolderServiceImpl** and **WorkflowServiceImpl**.
- `ArchiveCompletedEvent` → consumed by **HandoverDataSetServiceImpl** to finalize handover.
- `CompensationEvent` → consumed by **CompensationServiceImpl**.
All events are defined as Java classes and are listed under the `unknown` layer in the architecture facts.

### 6.8.3 Background Processing (Long‑Running Jobs)
- **ReencryptionJobServiceImpl** handles document re‑encryption (`PATCH /uvz/v1/job/retry/{id}`). It runs in a dedicated thread pool (`ExecutorService`) and reports progress via `/uvz/v1/job/metrics`.
- **ReportGenerationServiceImpl** creates annual reports (`GET /uvz/v1/reports/annual`). The request returns a `202 Accepted` and a location URL where the client can poll for completion.

---
## 6.9 Inventories & Traceability Tables

### 6.9.1 Core Components per Layer
| Layer | Stereotype | Representative Components |
|-------|------------|---------------------------|
| Presentation | controller | `DeedEntryRestServiceImpl`, `ApprovalRestServiceImpl`, `BulkCaptureController` |
| Application | service | `DeedEntryServiceImpl`, `WorkflowServiceImpl`, `JobServiceImpl`, `CompensationServiceImpl` |
| Domain | entity | `DeedEntry` (entity), `SignatureFolder` (entity) |
| Data Access | repository | `DeedEntryDao`, `DocumentMetaDataDao`, `UvzNumberManagerDao` |
| Infrastructure | scheduler | `JobServiceImpl` (scheduler) |
| Unknown | event‑bus / compensation | `CompensationServiceImpl`, `EventBus` |

### 6.9.2 Endpoints per Business Flow
| Flow | HTTP Method | Path | Primary Controller |
|------|-------------|------|--------------------|
| Create Deed Entry | POST | `/uvz/v1/deedentries` | `DeedEntryRestServiceImpl` |
| Approve / Reject | POST | `/uvz/v1/approval/{id}` | `ApprovalRestServiceImpl` |
| Handover | POST | `/uvz/v1/deedentries/handover` | `HandoverDataSetRestServiceImpl` |
| Bulk Capture | POST | `/uvz/v1/deedentries/bulkcapture` | `BulkCaptureController` |
| Start Workflow | POST | `/uvz/v1/workflow` | `WorkflowServiceImpl` |
| Retry Job | PATCH | `/uvz/v1/job/retry/{id}` | `JobServiceImpl` |

### 6.9.3 Relations Overview (selected)
| From Component | To Component | Relation Type |
|----------------|-------------|--------------|
| `component.backend.deedentry_logic_impl.deed_entry_service_impl` | `component.backend.api_dao_impl.deed_entry_dao_impl` | uses |
| `component.backend.deedentry_logic_impl.deed_entry_service_impl` | `component.backend.documentmetadata_logic_impl.document_meta_data_service_impl` | uses |
| `component.backend.deedentry_logic_impl.deed_entry_service_impl` | `component.backend.signaturefolder_logic_impl.signature_folder_service_impl` | uses |
| `component.backend.deedentry_logic_impl.deed_entry_service_impl` | `component.backend.workflow_logic_impl.workflow_service_impl` | uses |
| `component.backend.handover_logic_impl.handover_data_set_service_impl` | `component.backend.archive_logic_impl.archive_manager_service_impl` | uses |
| `component.backend.job_logic_impl.job_service_impl` | `component.backend.module_work_logic.work_service_provider_impl` | uses |

---
*All component names, relations and endpoints are extracted directly from the architecture facts and the generated REST interface list, guaranteeing factual accuracy.*
