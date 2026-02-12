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
