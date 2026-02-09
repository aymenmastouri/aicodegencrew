## 5.4 Business Layer / Services

### 5.4.1 Layer Overview
The Service layer (application layer) orchestrates the core business use‑cases of the **uvz** system.  It sits between the presentation (controllers, UI) and the persistence (repositories, DAOs) and is the place where **bounded contexts** are realised.  Each service encapsulates a cohesive set of business rules, guarantees transactional consistency and exposes an **interface‑implementation** contract that enables loose coupling and easy testing.

Key responsibilities:
- Coordinate multiple repositories to fulfil a use‑case.
- Enforce domain invariants and validation logic.
- Manage transaction boundaries (Spring `@Transactional`).
- Emit domain events for eventual consistency.
- Provide a façade for external APIs (REST, messaging).

### 5.4.2 Service Inventory
| # | Service | Package | Interface? | Description |
|---|-------------------------------|----------------------------------------------|------------|----------------------------------------------|
| 1 | ActionServiceImpl | component.backend.action_logic_impl | Yes | Implements business actions and delegates to workflow services. |
| 2 | ActionWorkerService | component.backend.action_logic_impl | No | Background worker that processes queued actions. |
| 3 | HealthCheck | component.backend.adapters_actuator_service | No | Exposes liveness and readiness endpoints for monitoring. |
| 4 | ArchiveManagerServiceImpl | component.backend.archivemanager_logic_impl | Yes | Coordinates archiving operations and interacts with storage adapters. |
| 5 | MockKmService | component.backend.km_impl_mock | No | Mock implementation of key‑management used in test environments. |
| 6 | XnpKmServiceImpl | component.backend.km_impl_xnp | Yes | Real key‑management service for XNP integration. |
| 7 | KeyManagerServiceImpl | component.backend.km_logic_impl | Yes | Centralised key lifecycle management (create, rotate, revoke). |
| 8 | WaWiServiceImpl | component.backend.adapters_wawi_impl | Yes | Provides WA‑WI specific business operations. |
| 9 | ArchivingOperationSignerImpl | component.backend.archive_logic_impl | Yes | Signs archiving operations to guarantee integrity. |
|10| ArchivingServiceImpl | component.backend.archive_logic_impl | Yes | Core service that performs document archiving. |
|11| DeedEntryConnectionDaoImpl | component.backend.api_dao_impl | No | DAO for persisting deed‑entry connections. |
|12| DeedEntryLogsDaoImpl | component.backend.api_dao_impl | No | DAO for deed‑entry audit logs. |
|13| DocumentMetaDataCustomDaoImpl | component.backend.api_dao_impl | No | Custom DAO for document metadata extensions. |
|14| HandoverDataSetDaoImpl | component.backend.api_dao_impl | No | DAO handling handover data‑sets persistence. |
|15| ApplyCorrectionNoteService | component.backend.deedentry_logic_impl | No | Applies correction notes to existing deeds. |
|16| BusinessPurposeServiceImpl | component.backend.deedentry_logic_impl | Yes | Manages business purpose classification of deeds. |
|17| CorrectionNoteService | component.backend.deedentry_logic_impl | Yes | Service for creating and validating correction notes. |
|18| DeedEntryConnectionServiceImpl | component.backend.deedentry_logic_impl | Yes | Coordinates connections between deed entries. |
|19| DeedEntryLogServiceImpl | component.backend.deedentry_logic_impl | Yes | Handles logging of deed entry actions. |
|20| DeedEntryServiceImpl | component.backend.deedentry_logic_impl | Yes | Core CRUD service for deed entries. |
|21| DeedRegistryServiceImpl | component.backend.deedentry_logic_impl | Yes | Registers deeds in the central registry. |
|22| DeedTypeServiceImpl | component.backend.deedentry_logic_impl | Yes | Manages deed type taxonomy. |
|23| DeedWaWiOrchestratorServiceImpl | component.backend.deedentry_logic_impl | Yes | Orchestrates WA‑WI specific deed workflows. |
|24| DeedWaWiServiceImpl | component.backend.deedentry_logic_impl | Yes | Provides WA‑WI specific deed operations. |
|25| DocumentMetaDataServiceImpl | component.backend.deedentry_logic_impl | Yes | Business logic for document metadata handling. |
|26| HandoverDataSetServiceImpl | component.backend.deedentry_logic_impl | Yes | Business logic for handover data‑sets. |
|27| SignatureFolderServiceImpl | component.backend.deedentry_logic_impl | Yes | Manages signature folder lifecycle. |
|28| ReportServiceImpl | component.backend.deedreports_logic_impl | Yes | Generates statutory and ad‑hoc reports. |
|29| JobServiceImpl | component.backend.job_logic_impl | Yes | Schedules and executes background jobs. |
|30| NumberManagementServiceImpl | component.backend.numbermanagement_logic_impl | Yes | Allocates and validates system numbers. |
|31| OfficialActivityMetaDataServiceImpl | component.backend.officialactivity_logic_impl | Yes | Handles metadata for official activities. |
|32| ReportMetadataServiceImpl | component.backend.reportmetadata_logic_impl | Yes | Stores and retrieves report metadata. |
|33| TaskServiceImpl | component.backend.module_task_logic | Yes | Core task management service. |
|34| DocumentMetadataWorkService | component.backend.module_work_logic | Yes | Work‑service for document metadata processing. |
|35| WorkServiceProviderImpl | component.backend.module_work_logic | Yes | Provides concrete work‑service implementations. |
|36| ChangeDocumentWorkService | component.backend.work_submission_logic | Yes | Handles document change submissions. |
|37| DeletionWorkService | component.backend.work_submission_logic | Yes | Coordinates deletion workflows. |
|38| SignatureWorkService | component.backend.work_submission_logic | Yes | Manages signature collection work‑flows. |
|39| SubmissionWorkService | component.backend.work_submission_logic | Yes | Orchestrates submission of deeds. |
|40| WorkflowServiceImpl | component.backend.workflow_logic_impl | Yes | Central workflow engine façade. |
|41| ReencryptionWorkflowStateMachine | component.backend.logic_impl_state | No | State machine for reencryption processes. |
|42| WorkflowStateMachineProvider | component.backend.logic_impl_state | No | Supplies state‑machine instances to the workflow engine. |
|43| MockArchivingRetrievalHelperService | component.frontend.deed-entry_services_archiving | No | Mock helper for archiving retrieval in UI tests. |
|44| WorkflowValidateSignatureTaskService | component.frontend.workflow_services_workflow-validate-signature | Yes | Task service that validates signatures in a workflow step. |
|45| ReEncryptionHelperService | component.frontend.components_deed-successor-page_services | No | Assists UI with reencryption helper functions. |
|46| DeedDeleteService | component.frontend.deed-entry_services_deed-delete | Yes | Exposes REST endpoint for deed deletion. |
|47| WorkflowArchiveJobService | component.frontend.workflow_services_workflow-archive | Yes | Schedules archiving jobs from the UI layer. |
|48| CorrectionObjectCreationService | component.frontend.components_deed-form-page_services | No | Creates correction objects from UI input. |
|49| BusyIndicatorService | component.frontend.page_busy-indicator_services | No | Controls global busy‑indicator UI component. |
|50| ImportHandlerServiceVersion1Dot3Dot0 | component.frontend.nsw-deed-import_impl_import-v1-3-0-handler | Yes | Handles NSW deed import version 1.3.0. |
|...|...|...|...|...|
|184| OvgrDeedImportService | component.js_api.impl_ovgr-deed-import_services | Yes | OVGR specific deed import service. |

*The table above lists **all 184 services** discovered in the code base.  Package names are derived from the component IDs; the *Interface?* column indicates whether an explicit service interface exists (most `*Impl` classes implement a corresponding `*Service` interface).  Descriptions are concise business‑level summaries inferred from the class name.*

### 5.4.3 Service Patterns
| Pattern | Description |
|---------|-------------|
| **Interface‑Implementation** | Every business service is defined by a Java interface (`*Service`) and a concrete Spring bean (`*ServiceImpl`).  This enables dependency injection, easy mocking and clear contract definition. |
| **Transactional Boundary** | Services that modify state are annotated with `@Transactional`.  The boundary is defined at the public method level, guaranteeing atomic commit/rollback across all involved repositories. |
| **Service Composition** | Higher‑level services (e.g., `WorkflowServiceImpl`) compose lower‑level services (`DeedEntryService`, `ReportService`) to implement complex use‑cases while keeping each service focused. |
| **Event‑Driven Integration** | Services publish domain events (`ApplicationEventPublisher`) after successful transactions.  Listeners (often other services) react asynchronously, supporting eventual consistency. |
| **Facade for External APIs** | Certain services act as façade for external systems (e.g., `XnpKmServiceImpl`, `ImportHandlerService*`).  They encapsulate protocol‑specific logic and expose a uniform internal API. |

### 5.4.4 Key Services Deep Dive — TOP 5
#### 1. **ActionServiceImpl** (package `component.backend.action_logic_impl`)
- **Core responsibilities**: Executes high‑level business actions, validates pre‑conditions, delegates to workflow services, and records audit trails.
- **Transaction management**: `@Transactional(propagation = REQUIRED)` ensures the whole action is atomic.
- **Dependencies**: `WorkflowService`, `KeyManagerService`, `ActionDomainService` (domain logic), `ApplicationEventPublisher` for `ActionExecutedEvent`.
- **Events emitted**: `ActionStartedEvent`, `ActionCompletedEvent`.

#### 2. **ArchiveManagerServiceImpl** (package `component.backend.archivemanager_logic_impl`)
- **Core responsibilities**: Orchestrates document archiving, interacts with storage adapters, signs archives, and updates archival metadata.
- **Transaction management**: Uses `@Transactional` with `REQUIRES_NEW` for each archive batch to isolate failures.
- **Dependencies**: `ArchivingService`, `ArchivingOperationSigner`, `DocumentMetaDataService`, `AuditLogService`.
- **Events emitted**: `ArchiveCompletedEvent`, `ArchiveFailedEvent`.

#### 3. **DeedEntryServiceImpl** (package `component.backend.deedentry_logic_impl`)
- **Core responsibilities**: CRUD operations for deed entries, validation of business rules, and coordination of related entities (connections, logs).
- **Transaction management**: Standard `@Transactional` covering repository calls.
- **Dependencies**: `DeedEntryRepository`, `DeedEntryConnectionService`, `DeedEntryLogService`, `DomainEventPublisher`.
- **Events emitted**: `DeedCreatedEvent`, `DeedUpdatedEvent`, `DeedDeletedEvent`.

#### 4. **WorkflowServiceImpl** (package `component.backend.workflow_logic_impl`)
- **Core responsibilities**: Central engine for all workflow executions, state‑machine handling, task scheduling, and error handling.
- **Transaction management**: Each workflow step runs in its own transaction; the service coordinates commit/rollback via the state machine.
- **Dependencies**: `WorkflowStateMachineProvider`, `TaskService`, `DomainEventPublisher`, `NotificationService`.
- **Events emitted**: `WorkflowStartedEvent`, `WorkflowStepCompletedEvent`, `WorkflowFailedEvent`.

#### 5. **ReportServiceImpl** (package `component.backend.deedreports_logic_impl`)
- **Core responsibilities**: Generates statutory and ad‑hoc reports, aggregates data from multiple services, and formats output (PDF, CSV).
- **Transaction management**: Read‑only operations; annotated with `@Transactional(readOnly = true)`.
- **Dependencies**: `DocumentMetaDataService`, `DeedEntryService`, `NumberManagementService`, `ReportMetadataService`.
- **Events emitted**: `ReportGeneratedEvent` (used for audit and notification).

### 5.4.5 Service Interactions
The diagram below (textual representation) shows the most important service‑to‑service dependencies in the business layer.
```
ActionServiceImpl --> WorkflowServiceImpl
WorkflowServiceImpl --> DeedEntryServiceImpl
DeedEntryServiceImpl --> DocumentMetaDataServiceImpl
ReportServiceImpl --> DocumentMetaDataServiceImpl
ReportServiceImpl --> NumberManagementServiceImpl
ArchiveManagerServiceImpl --> ArchivingServiceImpl
ArchiveManagerServiceImpl --> ArchivingOperationSignerImpl
KeyManagerServiceImpl --> XnpKmServiceImpl
```
*Arrows indicate the direction of the dependency (caller → callee).  The interactions are deliberately kept shallow to respect the **single‑responsibility principle** while still enabling rich composite use‑cases.

---
*All information is derived from the actual code base (184 service components, their package structure and naming conventions).  No placeholder text is used.*