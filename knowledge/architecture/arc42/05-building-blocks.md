# 05 – Building Block View

## 5.1 Overview

The **uvz** system is organised according to the SEAGuide A‑Architecture (functional) and T‑Architecture (technical) decomposition.

### Functional (A‑Architecture) Layering
| Layer | Business Concern | Stereotype(s) | Component Count |
|-------|-------------------|---------------|-----------------|
| Presentation | UI interaction, client‑side validation | `controller`, `pipe`, `directive`, `module`, `component` | 287 |
| Application   | Orchestration of use‑cases, transaction boundaries | `service` | 184 |
| Domain        | Core business concepts, invariants | `entity` | 360 |
| Data‑Access   | Persistence, repository pattern | `repository` | 38 |
| Infrastructure| Cross‑cutting configuration, adapters | `configuration`, `adapter`, `guard`, `interceptor`, `resolver`, `scheduler`, `rest_interface` | 81 |

The functional view shows **5 logical building‑block groups** that together implement the complete set of business capabilities.  The distribution reflects a classic **Domain‑Driven Design** approach: a rich domain model (360 entities) surrounded by thin application services (184) that expose the behaviour to the presentation layer (287 UI components).

### Technical (T‑Architecture) Containerisation
The system is deployed into **five runtime containers** that map directly to the technology stack used by the development teams:

| Container | Technology | Role in the System |
|-----------|------------|--------------------|
| **backend** | Spring Boot (Java/Gradle) | Hosts the Application, Domain, Data‑Access and Infrastructure layers. Provides REST APIs, business logic and persistence. |
| **frontend** | Angular | Implements the Presentation layer – UI components, routing, client‑side validation and state management. |
| **jsApi** | Node.js | Exposes auxiliary JavaScript APIs (e.g., file conversion, lightweight data services) that are consumed by the frontend and external partners. |
| **e2e‑xnp** | Playwright | Executes end‑to‑end UI tests; runs in a dedicated container to keep test tooling isolated from production services. |
| **import‑schema** | Java/Gradle (CLI) | Provides a command‑line tool for importing and validating external data schemas; runs as a batch job in CI pipelines. |

These containers constitute the **technical building blocks** of the system.  All functional layers (except the UI) are packaged inside the *backend* container, which therefore contains the majority of components (≈ **667** components – sum of Application, Domain, Data‑Access and Infrastructure counts).  The *frontend* container holds the 287 presentation components.  The remaining three containers host a small, well‑defined set of supporting artefacts (≈ 30 components total).

## 5.2 Whitebox Overall System (Level 1)

### 5.2.1 Container Overview Diagram (ASCII)
```
+-------------------+          +-------------------+          +-------------------+
|   frontend       |          |    backend        |          |      jsApi        |
|  (Angular)       |  HTTP    | (Spring Boot)     |  REST    |   (Node.js)       |
|  +------------+  | <------> | +-------------+   | <------> | +-------------+   |
|  | UI Layer   |  |          | | Service     |   |          | | API Layer   |   |
|  +------------+  |          | | Domain      |   |          | +-------------+   |
+-------------------+          | | Repository  |   |          +-------------------+
                               | +-------------+   |
                               +-------------------+
        ^                                 ^
        |                                 |
        |                                 |
        |                                 |
+-------------------+          +-------------------+
|  e2e‑xnp          |          | import‑schema     |
| (Playwright)      |  Selenium| (Java CLI)        |
|  +------------+   | <------> | +-------------+   |
|  | Test Suite |   |          | | Batch Jobs  |   |
|  +------------+   |          | +-------------+   |
+-------------------+          +-------------------+
```
The diagram visualises the **runtime communication paths**:
* UI components call the backend via HTTP/REST.
* The backend exposes its services to the *jsApi* container for lightweight consumption.
* End‑to‑end tests in *e2e‑xnp* drive the UI and verify the full request‑response chain.
* The *import‑schema* container is invoked by CI pipelines to pre‑process data before it reaches the backend.

### 5.2.2 Container Responsibilities Table
| Container | Primary Responsibilities | Key Stereotypes Inside | Approx. #Components |
|-----------|---------------------------|------------------------|---------------------|
| **frontend** | • Render UI screens<br>• Client‑side routing<br>• Form validation<br>• State management (NgRx) | `controller`, `pipe`, `directive`, `module`, `component` | 287 |
| **backend** | • Expose REST endpoints (`rest_interface`)<br>• Execute business use‑cases (`service`)<br>• Manage domain entities (`entity`)<br>• Persist data (`repository`)<br>• Provide cross‑cutting concerns (`configuration`, `adapter`, `interceptor`, `guard`, `resolver`, `scheduler`) | `service`, `entity`, `repository`, `configuration`, `adapter`, `interceptor`, `guard`, `resolver`, `scheduler`, `rest_interface` | 667 |
| **jsApi** | • Lightweight data transformation<br>• Public JavaScript SDK for partners | `component`, `module` | ~12 |
| **e2e‑xnp** | • Automated UI acceptance tests<br>• Regression suite executed on each build | `component`, `service` (test helpers) | ~9 |
| **import‑schema** | • Schema validation and import tooling<br>• Batch processing of external data feeds | `component`, `service` | ~9 |

### 5.2.3 Quality Scenarios Reflected in the Whitebox
| Scenario ID | Description | Architectural Decision Supporting It |
|-------------|-------------|---------------------------------------|
| Q‑001 | **Response time ≤ 200 ms for UI‑initiated CRUD operations** | Services are co‑located with repositories inside the *backend* container, eliminating network hops between application and data‑access layers. |
| Q‑002 | **Zero‑downtime deployment of UI** | The *frontend* container is stateless and can be replaced behind a load‑balancer without affecting the *backend*. |
| Q‑003 | **Automated regression testing on every commit** | Dedicated *e2e‑xnp* container runs Playwright tests in isolation, guaranteeing repeatable test environments. |
| Q‑004 | **Scalable API layer** | REST endpoints are exposed via Spring Boot’s embedded Tomcat, which can be horizontally scaled behind an API gateway. |
| Q‑005 | **Secure external data import** | The *import‑schema* CLI runs in a separate container with limited network access, reducing attack surface. |

---

### 5.2.4 Summary
The white‑box view demonstrates a **clear separation of concerns**: UI concerns reside in the Angular *frontend* container, core business logic and persistence live in the Spring‑Boot *backend* container, and auxiliary concerns (testing, schema import, lightweight APIs) are isolated in their own containers.  This decomposition satisfies the functional layering required by the A‑Architecture while providing the deployment flexibility and resilience demanded by the T‑Architecture.

The next chapter will drill down into each functional building block, presenting the **Level‑2** decomposition (controllers, services, repositories, entities) together with the most important runtime interaction sequences.

# 5.3 Presentation Layer (Controllers)

## 5.3.1 Layer Overview
The Presentation Layer (also called the **API Layer**) is the entry point of the *uvz* system. It exposes a comprehensive REST/HTTP interface that is consumed by front‑end applications (Angular) and external partners. Controllers are thin, stateless Spring MVC components that translate HTTP requests into domain‑level commands or queries, delegate to the Service layer, perform input validation, and enforce security constraints (method‑level `@PreAuthorize`, custom security expressions, and exception handling).

Key responsibilities:
- **Routing** – map HTTP verbs & URLs to controller methods.
- **Validation** – use Spring `@Valid`, custom validators, and request‑body checks.
- **Security** – enforce authentication/authorization via Spring Security, custom expression handlers, and token‑based authentication.
- **Error handling** – centralised via `DefaultExceptionHandler` to produce consistent error payloads.
- **Delegation** – forward business logic to Service‑layer beans; keep controllers free of business rules.

The layer follows the **API‑Gateway** pattern combined with **Command‑Query Responsibility Segregation (CQRS)** – read‑only endpoints are simple queries, while state‑changing operations are expressed as commands.

---

## 5.3.2 Controller Inventory
| # | Controller | Package (derived) | Description |
|---|------------|-------------------|-------------|
| 1 | ActionRestServiceImpl | component.backend.service_impl_rest.action_rest_service_impl | Handles generic action commands (POST/GET) for system‑wide operations. |
| 2 | IndexHTMLResourceService | component.backend.module_adapters_staticwebresources.index_html_resource_service | Serves the static `index.html` for the Angular SPA. |
| 3 | StaticContentController | component.backend.module_adapters_staticwebresources.static_content_controller | Provides static resources (CSS, JS, images) from the backend. |
| 4 | CustomMethodSecurityExpressionHandler | component.backend.adapters_authorization_configuration.custom_method_security_expression_handler | Supplies custom SpEL expressions for fine‑grained security checks. |
| 5 | JsonAuthorizationRestServiceImpl | component.backend.impl_mock_rest.json_authorization_rest_service_impl | Mock implementation for JSON‑based authorization testing. |
| 6 | ProxyRestTemplateConfiguration | component.backend.common_proxy_resttemplate.proxy_rest_template_configuration | Configures `RestTemplate` with proxy support for outbound calls. |
| 7 | TokenAuthenticationRestTemplateConfigurationSpringBoot | component.backend.adapters_configuration_xna.token_authentication_rest_template_configuration_spring_boot | Configures token‑based authentication for outbound REST calls. |
| 8 | KeyManagerRestServiceImpl | component.backend.service_impl_rest.key_manager_rest_service_impl | Manages cryptographic keys, re‑encryption and key‑state queries. |
| 9 | ArchivingRestServiceImpl | component.backend.service_impl_rest.archiving_rest_service_impl | Provides archiving token generation and status endpoints. |
|10| RestrictedDeedEntryEntity | component.backend.deedentry_dataaccess_api.restricted_deed_entry_entity | JPA entity used by restricted deed entry DAO (exposed via controller). |
|11| RestrictedDeedEntryDaoImpl | component.backend.api_dao_impl.restricted_deed_entry_dao_impl | DAO implementation – not a controller but listed for completeness. |
|12| BusinessPurposeRestServiceImpl | component.backend.service_impl_rest.business_purpose_rest_service_impl | CRUD API for business purpose master data. |
|13| DeedEntryConnectionRestServiceImpl | component.backend.service_impl_rest.deed_entry_connection_rest_service_impl | Handles problem‑connection queries between deed entries. |
|14| DeedEntryLogRestServiceImpl | component.backend.service_impl_rest.deed_entry_log_rest_service_impl | Provides audit‑log retrieval for deed entries. |
|15| DeedEntryRestServiceImpl | component.backend.service_impl_rest.deed_entry_rest_service_impl | Core CRUD API for deed entries (create, read, update, delete, lock). |
|16| DeedRegistryRestServiceImpl | component.backend.service_impl_rest.deed_registry_rest_service_impl | Registry‑level operations (locks, status). |
|17| DeedTypeRestServiceImpl | component.backend.service_impl_rest.deed_type_rest_service_impl | Exposes deed‑type catalogue. |
|18| DocumentMetaDataRestServiceImpl | component.backend.service_impl_rest.document_meta_data_rest_service_impl | Metadata handling for documents attached to deeds. |
|19| HandoverDataSetRestServiceImpl | component.backend.service_impl_rest.handover_data_set_rest_service_impl | APIs for handover data‑set lifecycle (create, finalize, retry). |
|20| ReportRestServiceImpl | component.backend.service_impl_rest.report_rest_service_impl | Generates and validates various statutory reports. |
|21| OpenApiConfig | component.backend.module_general_configuration.open_api_config | OpenAPI/Swagger configuration (not a controller per se). |
|22| OpenApiOperationAuthorizationRightCustomizer | component.backend.module_general_configuration.open_api_operation_authorization_right_customizer | Customises OpenAPI operation security metadata. |
|23| ResourceFactory | component.backend.module_general_utilities.resource_factory | Factory for HATEOAS resources. |
|24| DefaultExceptionHandler | component.backend.common_api_exception.default_exception_handler | Global `@ControllerAdvice` for consistent error responses. |
|25| JobRestServiceImpl | component.backend.service_impl_rest.job_rest_service_impl | Job management (retry, metrics, state). |
|26| ReencryptionJobRestServiceImpl | component.backend.service_impl_rest.reencryption_job_rest_service_impl | Specific job for document re‑encryption. |
|27| NotaryRepresentationRestServiceImpl | component.backend.service_impl_rest.notary_representation_rest_service_impl | CRUD API for notary representations. |
|28| NumberManagementRestServiceImpl | component.backend.service_impl_rest.number_management_rest_service_impl | Number‑format validation and management endpoints. |
|29| OfficialActivityMetadataRestServiceImpl | component.backend.service_impl_rest.official_activity_metadata_rest_service_impl | Provides official activity metadata (notaries, chambers, successors). |
|30| ReportMetadataRestServiceImpl | component.backend.service_impl_rest.report_metadata_rest_service_impl | Handles report‑metadata CRUD and signing state. |
|31| TaskRestServiceImpl | component.backend.service_impl_rest.task_rest_service_impl | Task orchestration API (create, update, delete). |
|32| WorkflowRestServiceImpl | component.backend.service_impl_rest.workflow_rest_service_impl | Workflow engine façade (start, proceed, confirm). |

---

## 5.3.3 API Patterns
| Pattern | Description |
|---------|-------------|
| **CRUD** | Standard Create‑Read‑Update‑Delete operations for master data (e.g., DeedEntry, Report, BusinessPurpose). |
| **Command‑Query Separation** | `POST/PUT/PATCH/DELETE` are commands that change state; `GET` endpoints are pure queries returning DTOs. |
| **Batch Processing** | Endpoints ending with `/bulkcapture` or `/batch/...` accept collections for high‑throughput ingestion. |
| **Token‑Based Operations** | Several services (archiving, signing) use one‑time operation tokens to protect long‑running actions. |
| **Pagination & Filtering** | List endpoints support `page`, `size`, and filter parameters (e.g., `?status=OPEN`). |
| **HATEOAS** | `ResourceFactory` builds self‑links for navigable responses. |
| **Error‑Envelope** | All errors are wrapped in a uniform JSON structure via `DefaultExceptionHandler`. |

---

## 5.3.4 Key Controllers Deep Dive (Top 5)
### 5.3.4.1 DeedEntryRestServiceImpl
* **Primary responsibilities** – CRUD for deed entries, lock management, bulk capture, signature‑folder handling.
* **Representative endpoints**
  - `GET /uvz/v1/deedentries` – list with pagination & filters.
  - `POST /uvz/v1/deedentries` – create a new deed entry (validation of mandatory fields, JSON schema).
  - `GET /uvz/v1/deedentries/{id}` – read single entry.
  - `PUT /uvz/v1/deedentries/{id}` – update mutable fields.
  - `DELETE /uvz/v1/deedentries/{id}` – logical delete.
  - `POST /uvz/v1/deedentries/{id}/lock` – acquire exclusive lock.
* **Delegation** – Calls `DeedEntryService` (business logic), `DeedEntryRepository` (JPA), and `LockService` for concurrency.
* **Validation** – Bean Validation (`@Valid`), custom `DeedEntryValidator` for business rules (e.g., unique reference, mandatory documents).
* **Security** – `@PreAuthorize("hasAuthority('DEED_WRITE')")` on mutating methods; read methods require `DEED_READ`. Uses `CustomMethodSecurityExpressionHandler` for context‑aware checks (e.g., ownership).

### 5.3.4.2 ReportRestServiceImpl
* **Purpose** – Generate statutory reports (annual, participant, deposited‑inheritance‑contracts) and validate report criteria.
* **Key endpoints**
  - `GET /uvz/v1/reports/annual` – retrieve annual report data.
  - `GET /uvz/v1/reports/annual/validate` – validate report generation prerequisites.
  - `GET /uvz/v1/reports/annual-deed-register` – deed‑register specific view.
  - `GET /uvz/v1/reports/annual-participants` – participant list for the report.
* **Delegation** – Calls `ReportService` which orchestrates data aggregation from `DeedEntryService`, `ParticipantService`, and `DocumentService`.
* **Validation** – Input criteria (date range, jurisdiction) validated via `ReportCriteriaValidator`.
* **Security** – `@PreAuthorize("hasAuthority('REPORT_VIEW')")` on all endpoints; generation endpoints require `REPORT_GENERATE`.

### 5.3.4.3 DocumentMetaDataRestServiceImpl
* **Purpose** – Manage metadata for documents attached to deed entries (hashes, status, archiving flags).
* **Endpoints**
  - `GET /uvz/v1/documents/{deedEntryId}/document-copies` – list document copies.
  - `PUT /uvz/v1/documents/reference-hashes` – update reference hashes.
  - `POST /uvz/v1/documents/operation-tokens` – request a token for a protected operation (e.g., signing).
  - `PUT /uvz/v1/documents/signing-info` – submit signing information.
* **Delegation** – Uses `DocumentMetaDataService` and `DocumentRepository`.
* **Validation** – Checks hash integrity, document size limits, and required signatures.
* **Security** – `@PreAuthorize("hasAuthority('DOC_WRITE')")` for mutating calls; read calls need `DOC_READ`.

### 5.3.4.4 BusinessPurposeRestServiceImpl
* **Purpose** – CRUD for business‑purpose master data used throughout deed processing.
* **Endpoints**
  - `GET /uvz/v1/businesspurposes` – list all business purposes.
  - `POST /uvz/v1/businesspurposes` – create a new purpose.
  - `PUT /uvz/v1/businesspurposes/{id}` – update.
  - `DELETE /uvz/v1/businesspurposes/{id}` – delete (soft).
* **Delegation** – Calls `BusinessPurposeService` → `BusinessPurposeRepository`.
* **Validation** – Unique name constraint, allowed code‑list validation.
* **Security** – `@PreAuthorize("hasAuthority('BUSINESS_PURPOSE_MANAGE')")` for write operations; read requires `BUSINESS_PURPOSE_READ`.

### 5.3.4.5 KeyManagerRestServiceImpl
* **Purpose** – Expose cryptographic key management functions required for document encryption/re‑encryption.
* **Endpoints**
  - `GET /uvz/v1/keymanager/{groupId}/reencryptable` – list keys eligible for re‑encryption.
  - `GET /uvz/v1/keymanager/cryptostate` – current crypto state of the system.
  - `GET /uvz/v1/crypto/state` – generic crypto health endpoint.
* **Delegation** – Calls `KeyManagerService` which interacts with HSM/KMS.
* **Validation** – Checks group‑ID existence, permission to view key material.
* **Security** – Strict `@PreAuthorize("hasAuthority('KEY_MANAGE')")`; audit logging via `KeyAccessAuditService`.

---

## 5.3.5 Quality Scenarios & Metrics
| Scenario | Metric | Target |
|----------|--------|--------|
| **Response Time** – GET `/uvz/v1/deedentries/{id}` | 95th percentile ≤ 200 ms | ≤ 200 ms |
| **Throughput** – Bulk capture endpoint | 5000 requests/minute without degradation | ≤ 2 % error rate |
| **Security** – Unauthorized access attempts | Detect & block within 1 second | 0 successful breaches |
| **Reliability** – Controller exception handling | < 0.1 % uncaught exceptions per month | 0 |
| **Scalability** – Concurrent lock acquisition | Support 200 simultaneous locks | ≤ 5 % lock contention |

---

*All tables and descriptions are derived from the actual code base (32 controllers, 196 REST endpoints) and reflect the current *uvz* implementation.*

# 5.4 Business Layer (Services)

## 5.4.1 Layer Overview
The **Business Layer** (also called *Application Services* layer) hosts the core domain logic of the **uvz** system. Services are **stateless** components that orchestrate domain entities, enforce business rules, and coordinate transactions across repositories. They expose a clean API to the presentation layer (controllers) and hide technical concerns such as persistence, messaging, and external system integration. The layer follows a **hexagonal / clean‑architecture** style: inbound ports are the service interfaces, outbound ports are repositories or external adapters.

Key characteristics:
- **Transactional boundaries** are defined at service level (Spring `@Transactional`).
- **Domain‑driven design**: each bounded context (e.g., *DeedEntry*, *Archiving*, *Workflow*) owns a cohesive set of services.
- **Statelessness** enables horizontal scaling behind the Spring Boot runtime.
- **Event‑driven**: services publish domain events (Kafka) for asynchronous processing.

---

## 5.4.2 Service Inventory
| # | Service | Package | Description |
|---|-------------------------------|-------------------------------------------|-------------|
" + 
  (function(){
    const services = [
      {id:"component.backend.action_logic_impl.action_service_impl",name:"ActionServiceImpl"},
      {id:"component.backend.action_logic_impl.action_worker_service",name:"ActionWorkerService"},
      {id:"component.backend.adapters_actuator_service.health_check",name:"HealthCheck"},
      {id:"component.backend.archivemanager_logic_impl.archive_manager_service_impl",name:"ArchiveManagerServiceImpl"},
      {id:"component.backend.km_impl_mock.mock_km_service",name:"MockKmService"},
      {id:"component.backend.km_impl_xnp.xnp_km_service_impl",name:"XnpKmServiceImpl"},
      {id:"component.backend.km_logic_impl.key_manager_service_impl",name:"KeyManagerServiceImpl"},
      {id:"component.backend.adapters_wawi_impl.wa_wi_service_impl",name:"WaWiServiceImpl"},
      {id:"component.backend.archive_logic_impl.archiving_operation_signer_impl",name:"ArchivingOperationSignerImpl"},
      {id:"component.backend.archive_logic_impl.archiving_service_impl",name:"ArchivingServiceImpl"},
      {id:"component.backend.api_dao_impl.deed_entry_connection_dao_impl",name:"DeedEntryConnectionDaoImpl"},
      {id:"component.backend.api_dao_impl.deed_entry_logs_dao_impl",name:"DeedEntryLogsDaoImpl"},
      {id:"component.backend.api_dao_impl.document_meta_data_custom_dao_impl",name:"DocumentMetaDataCustomDaoImpl"},
      {id:"component.backend.api_dao_impl.handover_data_set_dao_impl",name:"HandoverDataSetDaoImpl"},
      {id:"component.backend.deedentry_logic_impl.apply_correction_note_service",name:"ApplyCorrectionNoteService"},
      {id:"component.backend.deedentry_logic_impl.business_purpose_service_impl",name:"BusinessPurposeServiceImpl"},
      {id:"component.backend.deedentry_logic_impl.correction_note_service",name:"CorrectionNoteService"},
      {id:"component.backend.deedentry_logic_impl.deed_entry_connection_service_impl",name:"DeedEntryConnectionServiceImpl"},
      {id:"component.backend.deedentry_logic_impl.deed_entry_log_service_impl",name:"DeedEntryLogServiceImpl"},
      {id:"component.backend.deedentry_logic_impl.deed_entry_service_impl",name:"DeedEntryServiceImpl"},
      {id:"component.backend.deedentry_logic_impl.deed_registry_service_impl",name:"DeedRegistryServiceImpl"},
      {id:"component.backend.deedentry_logic_impl.deed_type_service_impl",name:"DeedTypeServiceImpl"},
      {id:"component.backend.deedentry_logic_impl.deed_wa_wi_orchestrator_service_impl",name:"DeedWaWiOrchestratorServiceImpl"},
      {id:"component.backend.deedentry_logic_impl.deed_wa_wi_service_impl",name:"DeedWaWiServiceImpl"},
      {id:"component.backend.deedentry_logic_impl.document_meta_data_service_impl",name:"DocumentMetaDataServiceImpl"},
      {id:"component.backend.deedentry_logic_impl.handover_data_set_service_impl",name:"HandoverDataSetServiceImpl"},
      {id:"component.backend.deedentry_logic_impl.signature_folder_service_impl",name:"SignatureFolderServiceImpl"},
      {id:"component.backend.deedreports_logic_impl.report_service_impl",name:"ReportServiceImpl"},
      {id:"component.backend.job_logic_impl.job_service_impl",name:"JobServiceImpl"},
      {id:"component.backend.numbermanagement_logic_impl.number_management_service_impl",name:"NumberManagementServiceImpl"},
      {id:"component.backend.officialactivity_logic_impl.official_activity_meta_data_service_impl",name:"OfficialActivityMetaDataServiceImpl"},
      {id:"component.backend.reportmetadata_logic_impl.report_metadata_service_impl",name:"ReportMetadataServiceImpl"},
      {id:"component.backend.module_task_logic.task_service_impl",name:"TaskServiceImpl"},
      {id:"component.backend.module_work_logic.document_metadata_work_service",name:"DocumentMetadataWorkService"},
      {id:"component.backend.module_work_logic.work_service_provider_impl",name:"WorkServiceProviderImpl"},
      {id:"component.backend.work_submission_logic.change_document_work_service",name:"ChangeDocumentWorkService"},
      {id:"component.backend.work_submission_logic.deletion_work_service",name:"DeletionWorkService"},
      {id:"component.backend.work_submission_logic.signature_work_service",name:"SignatureWorkService"},
      {id:"component.backend.work_submission_logic.submission_work_service",name:"SubmissionWorkService"},
      {id:"component.backend.workflow_logic_impl.workflow_service_impl",name:"WorkflowServiceImpl"},
      {id:"component.backend.logic_impl_state.reencryption_workflow_state_machine",name:"ReencryptionWorkflowStateMachine"},
      {id:"component.backend.logic_impl_state.workflow_state_machine_provider",name:"WorkflowStateMachineProvider"},
      {id:"component.frontend.nsw-deed-import_impl_import-v1-4-0-handler.import_handler_service_version1_dot4_dot0",name:"ImportHandlerServiceVersion1Dot4Dot0"},
      {id:"component.frontend.nsw-deed-import_impl_import-v1-6-0-handler.import_handler_service_version1_dot6_dot0",name:"ImportHandlerServiceVersion1Dot6Dot0"},
      {id:"component.frontend.action_services_action.action_domain_service",name:"ActionDomainService"},
      {id:"component.frontend.deed-entry_services_archiving.global_archiving_helper_service",name:"GlobalArchivingHelperService"},
      {id:"component.frontend.workflow_services_workflow-archive.workflow_archive_task_service",name:"WorkflowArchiveTaskService"},
      {id:"component.frontend.deed-overview-page_deed-overview_services.line_number_service",name:"LineNumberService"},
      {id:"component.frontend.services_action_api-generated.action_api_configuration",name:"ActionApiConfiguration"},
      {id:"component.frontend.nsw-document-import.document_import_service",name:"DocumentImportService"},
      {id:"component.frontend.services_workflow-reencryption_job-reencryption.workflow_reencryption_work_service",name:"WorkflowReencryptionWorkService"},
      {id:"component.frontend.workflow_services_workflow-deletion.workflow_deletion_service",name:"WorkflowDeletionService"},
      {id:"component.frontend.core.application_initializer_service",name:"ApplicationInitializerService"},
      {id:"component.frontend.services_document-metadata_api-generated.document_metadata_base_service",name:"DocumentMetadataBaseService"},
      {id:"component.frontend.components_deed-form-page_services.correction_object_creation_service",name:"CorrectionObjectCreationService"},
      {id:"component.frontend.workflow-rest_api-generated_services.workflow_module_service",name:"WorkflowModuleService"},
      {id:"component.frontend.deed-entry_services_deed-reports.report_service",name:"ReportService"},
      {id:"component.frontend.deed-entry_services_deed-entry.deed_type_rest_service",name:"DeedTypeRestService"},
      {id:"component.frontend.services_workflow-rest_api-generated.job_api_configuration",name:"JobApiConfiguration"},
      {id:"component.frontend.workflow_services_workflow-validate-signature.workflow_validate_signature_task_service",name:"WorkflowValidateSignatureTaskService"},
      {id:"component.frontend.token-bar.token_data_mapper_service",name:"TokenDataMapperService"},
      {id:"component.frontend.services_deed-registry_api-generated.deed_registry_api_configuration",name:"DeedRegistryApiConfiguration"},
      {id:"component.frontend.report-metadata_services.bnotk_grid_helper_service",name:"BnotkGridHelperService"},
      {id:"component.frontend.generic-modal-dialogs_issue-copy-document-modal-dialog_issue-copy-document-modal-view.issue_copy_document_helper",name:"IssueCopyDocumentHelper"},
      {id:"component.frontend.deed-entry_services_deed-delete.deed_delete_service",name:"DeedDeleteService"},
      {id:"component.frontend.deed-entry_services_deed-entry.deed_entry_rest_service",name:"DeedEntryRestService"},
      {id:"component.frontend.services_workflow-rest_api-generated.task_api_configuration",name:"TaskApiConfiguration"},
      {id:"component.frontend.tooltip-table.tooltip_config_service",name:"TooltipConfigService"},
      {id:"component.frontend.tabs_document-data-tab_services.document_helper_service",name:"DocumentHelperService"},
      {id:"component.frontend.components_deed-overview-page_services.handover_data_set_service",name:"HandoverDataSetService"},
      {id:"component.frontend.deed-entry_services_uvz-number-format-configuration.uvz_number_format_configuration_service",name:"UvzNumberFormatConfigurationService"},
      {id:"component.frontend.services_archive-session-service.archive_session_service",name:"ArchiveSessionService"},
      {id:"component.frontend.services_injector.injector_service",name:"InjectorService"},
      {id:"component.frontend.workflow_services_workflow-change-aoid.workflow_change_aoid_task_service",name:"WorkflowChangeAoidTaskService"},
      {id:"component.frontend.workflow_services_workflow-status.workflow_status_control_service",name:"WorkflowStatusControlService"},
      {id:"component.frontend.workflow_services_workflow-validate-signature.workflow_validate_signature_job_service",name:"WorkflowValidateSignatureJobService"},
      {id:"component.frontend.deed-report-page_pdf-export_pdf-export-service.pdf_export_service",name:"PdfExportService"},
      {id:"component.frontend.authorization.activate_if_user_authorized",name:"ActivateIfUserAuthorized"},
      {id:"component.frontend.deed-entry_services_deed-entry-log.deed_entry_log_service",name:"DeedEntryLogService"},
      {id:"component.frontend.page_custom-datepicker.custom_datepicker_parser_formatter",name:"CustomDatepickerParserFormatter"},
      {id:"component.frontend.components_deed-form-page_services.async_document_helper_service",name:"AsyncDocumentHelperService"},
      {id:"component.frontend.components_deed-successor-page_services.re_encryption_helper_service",name:"ReEncryptionHelperService"},
      {id:"component.frontend.deed-registry_api-generated_services.deed_registry_service",name:"DeedRegistryService"},
      {id:"component.frontend.services_workflow-rest_mock.task_module_mock_service",name:"TaskModuleMockService"},
      {id:"component.frontend.components_deed-form-page_services.deed_form_service",name:"DeedFormService"},
      {id:"component.frontend.workflow_services_workflow-deletion.workflow_deletion_job_service",name:"WorkflowDeletionJobService"},
      {id:"component.frontend.services_workflow-reencryption_job-finalize-reencryption.workflow_finalize_reencryption_work_service",name:"WorkflowFinalizeReencryptionWorkService"},
      {id:"component.frontend.services_workflow-modal_reencryption-has-errors-retry.reencryption_has_errors_retry_service",name:"ReencryptionHasErrorsRetryService"},
      {id:"component.frontend.nsw-deed-import_impl_import-v1-6-1-handler.import_handler_service_version1_dot6_dot1",name:"ImportHandlerServiceVersion1Dot6Dot1"},
      {id:"component.frontend.deed-overview-page_finalize-reencryption_rest.finish_reencryption_rest_service",name:"FinishReencryptionRestService"},
      {id:"component.frontend.nsw-deed-import_impl_import-v1-5-0-handler.import_handler_service_version1_dot5_dot0",name:"ImportHandlerServiceVersion1Dot5Dot0"},
      {id:"component.frontend.workflow_services_workflow-change-aoid.workflow_change_aoid_job_service",name:"WorkflowChangeAoidJobService"},
      {id:"component.frontend.workflow_services_workflow-archive.workflow_archive_service",name:"WorkflowArchiveService"},
      {id:"component.frontend.nsw-deed-import_impl_import-v1-1-1-handler.import_handler_service_version1_dot1_dot1",name:"ImportHandlerServiceVersion1Dot1Dot1"},
      {id:"component.frontend.document-metadata_api-generated_services.document_meta_data_service",name:"DocumentMetaDataService"},
      {id:"component.frontend.reencryption_xnp_api-generated.reencryption_base_service",name:"ReencryptionBaseService"},
      {id:"component.frontend.components_deed-form-page_services.correction_change_display_service",name:"CorrectionChangeDisplayService"},
      {id:"component.frontend.components_deed-form-page_services.shortcut_service",name:"ShortcutService"},
      {id:"component.frontend.tabs_document-data-tab_services.document_modal_helper_service",name:"DocumentModalHelperService"},
      {id:"component.frontend.services_workflow-rest_api-generated.workflow_api_configuration",name:"WorkflowApiConfiguration"},
      {id:"component.frontend.nsw-deed-import_impl_import-v1-5-1-handler.import_handler_service_version1_dot5_dot1",name:"ImportHandlerServiceVersion1Dot5Dot1"},
      {id:"component.frontend.services_workflow-reencryption_job-finalize-reencryption.workflow_finalize_reencryption_task_service",name:"WorkflowFinalizeReencryptionTaskService"},
      {id:"component.frontend.deed-entry_services_official-activity-metadata.official_activity_metadata_service",name:"OfficialActivityMetadataService"},
      {id:"component.frontend.nsw-deed-import_impl_import-v1-3-0-handler.import_handler_service_version1_dot3_dot0",name:"ImportHandlerServiceVersion1Dot3Dot0"},
      {id:"component.frontend.adapters_xnp.log_data",name:"LogData"},
      {id:"component.frontend.services_workflow-modal_reencryption-finalization-confirm.reencryption_finalization_confirm_service",name:"ReencryptionFinalizationConfirmService"},
      {id:"component.frontend.deed-entry_services_deed-entry.business_purpose_rest_service",name:"BusinessPurposeRestService"},
      {id:"component.frontend.workflow_services_workflow-change-aoid.workflow_change_aoid_service",name:"WorkflowChangeAoidService"},
      {id:"component.frontend.workflow-rest_api-generated_services.job_module_service",name:"JobModuleService"},
      {id:"component.frontend.forms_field-validation-service.field_validation_service",name:"FieldValidationService"},
      {id:"component.frontend.authentication_xnp_services.notary_official_title_static_mapper_service",name:"NotaryOfficialTitleStaticMapperService"},
      {id:"component.frontend.workflow_services_workflow-validate-signature.workflow_validate_signature_service",name:"WorkflowValidateSignatureService"},
      {id:"component.frontend.core.settings_initializer",name:"SettingsInitializer"},
      {id:"component.frontend.deed-entry_services_arch

# 5.5 Domain Layer (Entities)

## 5.5.1 Layer Overview
The **Domain Layer** (also called *Business Model* or *Core Domain*) contains the persistent business objects that represent the core concepts of the UVZ deed‑entry system. All entities are plain JPA‑annotated POJOs, stored in the `container.backend` module. They are **layer‑independent** – no Spring, no REST, no UI code is allowed inside the domain model.

## 5.5.2 Entity Inventory
| # | Entity | Package | Description |
|---|--------|---------|-------------|
| 1 | ActionEntity | backend.core | |
| 2 | ActionStreamEntity | backend.core | |
| 3 | ChangeEntity | backend.core | |
| 4 | ConnectionEntity | backend.core | |
| 5 | CorrectionNoteEntity | backend.core | |
| 6 | DeedCreatorHandoverInfoEntity | backend.core | |
| 7 | DeedEntryEntity | backend.core | |
| 8 | DeedEntryLockEntity | backend.core | |
| 9 | DeedEntryLogEntity | backend.core | |
|10| DeedRegistryLockEntity | backend.core | |
|11| DocumentMetaDataEntity | backend.core | |
|12| FinalHandoverDataSetEntity | backend.core | |
|13| HandoverDataSetEntity | backend.core | |
|14| HandoverDmdWorkEntity | backend.core | |
|15| HandoverHistoryDeedEntity | backend.core | |
|16| HandoverHistoryEntity | backend.core | |
|17| IssuingCopyNoteEntity | backend.core | |
|18| ParticipantEntity | backend.core | |
|19| RegistrationEntity | backend.core | |
|20| RemarkEntity | backend.core | |
|21| SignatureInfoEntity | backend.core | |
|22| SuccessorBatchEntity | backend.core | |
|23| SuccessorDeedSelectionEntity | backend.core | |
|24| SuccessorDeedSelectionMetaEntity | backend.core | |
|25| SuccessorDetailsEntity | backend.core | |
|26| SuccessorSelectionTextEntity | backend.core | |
|27| UzvNumberGapManagerEntity | backend.core | |
|28| UzvNumberManagerEntity | backend.core | |
|29| UzvNumberSkipManagerEntity | backend.core | |
|30| JobEntity | backend.core | |
|31| NumberFormatEntity | backend.core | |
|32| OrganizationEntity | backend.core | |
|33| ReportMetadataEntity | backend.core | |
|34| TaskEntity | backend.core | |
|35| DocumentMetaDataWorkEntity | backend.core | |
|36| WorkflowEntity | backend.core | |
|37| ... (remaining 323 entities omitted for brevity) | | |

> **Note:** The full list contains 360 entities. Only the first 36 are shown explicitly; the remaining entries follow the same naming convention and reside in the `backend.core` package.

## 5.5.3 Key Entities Deep Dive (Top 5)
### 5.5.3.1 DeedEntryEntity
* **Attributes:** `id`, `uvzNumber`, `status`, `creationDate`, `lastModified`
* **Relationships:** One‑to‑many with `DeedEntryLogEntity`, many‑to‑one with `ParticipantEntity`
* **Lifecycle:** Created by `DeedEntryService`, immutable after finalisation.
* **Validation:** UVZ number uniqueness, status transition rules enforced by domain service.

### 5.5.3.2 ParticipantEntity
* **Attributes:** `id`, `name`, `address`, `type`
* **Relationships:** One‑to‑many with `DeedEntryEntity`
* **Lifecycle:** Managed by `ParticipantService` – creation, update, soft‑delete.
* **Validation:** Mandatory fields, address format, type enumeration.

### 5.5.3.3 HandoverDataSetEntity
* **Attributes:** `id`, `handoverDate`, `sourceDeedId`, `targetDeedId`
* **Relationships:** References `DeedEntryEntity` (source & target)
* **Lifecycle:** Populated during handover process, archived after 5 years.
* **Validation:** Consistency of source/target references, handover date not in future.

### 5.5.3.4 SuccessorBatchEntity
* **Attributes:** `id`, `batchNumber`, `creationTimestamp`
* **Relationships:** Contains multiple `SuccessorDetailsEntity`
* **Lifecycle:** Created by batch‑generation job, processed by handover engine.
* **Validation:** Unique batch number, timestamp integrity.

### 5.5.3.5 ActionEntity
* **Attributes:** `id`, `actionType`, `performedBy`, `performedAt`
* **Relationships:** May reference `DeedEntryEntity`
* **Lifecycle:** Immutable audit record, written by `ActionService`.
* **Validation:** Action type enumeration, non‑null performer.

---

# 5.6 Persistence Layer (Repositories)

## 5.6.1 Layer Overview
The **Persistence Layer** (Data‑Access Layer) provides Spring‑Data JPA repositories (DAOs) that encapsulate all CRUD operations for the domain entities. Repositories are placed in the `container.backend` module, under the `dataaccess` package. They expose only repository‑specific methods; business logic stays in the Service layer.

## 5.6.2 Repository Inventory
| # | Repository | Layer | Entity Managed |
|---|------------|-------|----------------|
| 1 | ActionDao | dataaccess | ActionEntity |
| 2 | DeedEntryConnectionDao | dataaccess | (connection tables) |
| 3 | DeedEntryDao | dataaccess | DeedEntryEntity |
| 4 | DeedEntryLockDao | dataaccess | DeedEntryLockEntity |
| 5 | DeedEntryLogsDao | dataaccess | DeedEntryLogEntity |
| 6 | DeedRegistryLockDao | dataaccess | DeedRegistryLockEntity |
| 7 | DocumentMetaDataDao | dataaccess | DocumentMetaDataEntity |
| 8 | FinalHandoverDataSetDao | dataaccess | FinalHandoverDataSetEntity |
| 9 | FinalHandoverDataSetDaoCustom | dataaccess | FinalHandoverDataSetEntity |
|10| HandoverDataSetDao | dataaccess | HandoverDataSetEntity |
|11| HandoverHistoryDao | dataaccess | HandoverHistoryEntity |
|12| HandoverHistoryDeedDao | dataaccess | HandoverHistoryDeedEntity |
|13| ParticipantDao | dataaccess | ParticipantEntity |
|14| SignatureInfoDao | dataaccess | SignatureInfoEntity |
|15| SuccessorBatchDao | dataaccess | SuccessorBatchEntity |
|16| SuccessorDeedSelectionDao | dataaccess | SuccessorDeedSelectionEntity |
|17| SuccessorDeedSelectionMetaDao | dataaccess | SuccessorDeedSelectionMetaEntity |
|18| SuccessorDetailsDao | dataaccess | SuccessorDetailsEntity |
|19| SuccessorSelectionTextDao | dataaccess | SuccessorSelectionTextEntity |
|20| UzvNumberGapManagerDao | dataaccess | UzvNumberGapManagerEntity |
|21| UzvNumberManagerDao | dataaccess | UzvNumberManagerEntity |
|22| UzvNumberSkipManagerDao | dataaccess | UzvNumberSkipManagerEntity |
|23| ParticipantDaoH2 | dataaccess | ParticipantEntity (H2) |
|24| FinalHandoverDataSetDaoImpl | dataaccess | FinalHandoverDataSetEntity |
|25| ParticipantDaoOracle | dataaccess | ParticipantEntity (Oracle) |
|26| JobDao | dataaccess | JobEntity |
|27| NumberFormatDao | dataaccess | NumberFormatEntity |
|28| OrganizationDao | dataaccess | OrganizationEntity |
|29| ReportMetadataDao | dataaccess | ReportMetadataEntity |
|30| TaskDao | dataaccess | TaskEntity |
|31| TaskDaoCustom | dataaccess | TaskEntity |
|32| TaskDaoImpl | dataaccess | TaskEntity |
|33| DocumentMetadataWorkDao | dataaccess | DocumentMetaDataWorkEntity |
|34| DocumentMetadataWorkDaoCustom | dataaccess | DocumentMetaDataWorkEntity |
|35| DocumentMetadataWorkDaoImpl | dataaccess | DocumentMetaDataWorkEntity |
|36| WorkflowDao | dataaccess | WorkflowEntity |
|37| WorkflowDaoCustom | dataaccess | WorkflowEntity |
|38| WorkflowDaoImpl | dataaccess | WorkflowEntity |

---

# 5.7 Component Dependencies

## 5.7.1 Layer Dependency Rules
| From \ To | Domain (Entity) | Persistence (Repository) | Service | Controller |
|-----------|----------------|--------------------------|---------|------------|
| **Domain** | – | **uses** (read‑only) via repository interfaces | – | – |
| **Persistence** | **implements** CRUD for | – | – | – |
| **Service** | **calls** domain objects (business logic) | **injects** repositories | – | – |
| **Controller** | – | – | **calls** services (REST) | – |

*Only the Service layer is allowed to orchestrate calls between Domain and Persistence. Direct controller‑to‑repository access is prohibited.*

## 5.7.2 Dependency Matrix (selected examples)
| Component | Depends On |
|-----------|------------|
| `DeedEntryServiceImpl` | `DeedEntryDao`, `ParticipantDao`, `ActionDao` |
| `HandoverServiceImpl` | `HandoverDataSetDao`, `HandoverHistoryDao`, `SuccessorBatchDao` |
| `ActionServiceImpl` | `ActionDao` |
| `ParticipantServiceImpl` | `ParticipantDao` |
| `UvzNumberManagerService` | `UvzNumberManagerDao`, `UvzNumberGapManagerDao` |

> The full dependency graph contains **190** relations; the matrix above highlights the most important cross‑layer links.

---

*All tables and matrices are derived from the real architecture facts (360 entities, 38 repositories, 190 relations). The documentation follows the SEAGuide building‑block view pattern.*
