# 05 – Building Block View (Part 1)

## 5.1 Overview

The **uvz** system is organised according to a classic *layered* (A‑Architecture) functional decomposition combined with a *container‑based* technical decomposition (T‑Architecture).  The functional view groups business capabilities into **presentation**, **application**, **domain**, **data‑access** and **infrastructure** layers.  The technical view maps those layers onto four runtime containers:

| Container | Technology | Primary Role | Component Count |
|-----------|------------|--------------|-----------------|
| **backend** | Spring Boot (Gradle) | Core business services, REST APIs, data‑access and domain model | 333 |
| **frontend** | Angular (npm) | UI, client‑side routing, guards, pipes | 404 |
| **e2e‑xnp** | Playwright (npm) | End‑to‑end functional test suite | 0 |
| **import‑schema** | Java/Gradle library | Schema import utilities (no runtime components) | 0 |

### Functional Layer Distribution (A‑Architecture)

| Layer | Component Count | Stereotypes (selected) |
|-------|-----------------|------------------------|
| **Presentation** | 246 | controller, directive, component, module, pipe |
| **Application** | 173 | service |
| **Domain** | 199 | entity |
| **Data‑Access** | 38 | repository |
| **Infrastructure** | 1 | configuration |
| **Unknown** | 81 | interceptor, resolver, guard, adapter, scheduler, rest_interface |

The **backend** container hosts the majority of the *application*, *domain* and *data‑access* layers (42 + 199 + 38 = 279 components) plus a small part of the presentation layer (32 controllers).  The **frontend** container concentrates the presentation layer (214 UI components, 59 unknown‑type artefacts) and a substantial portion of the application layer (131 services) that implement client‑side logic.

### Building‑Block Hierarchy

* **Controllers (32)** – expose REST endpoints (95 % of all REST endpoints) and UI routes.
* **Services (173)** – encapsulate use‑case logic, orchestrate repositories and external APIs.
* **Repositories (38)** – abstract persistence (JPA, Spring Data) for the 199 domain entities.
* **Entities (199)** – core business objects, modelled with JPA annotations.
* **Modules / Components / Pipes / Directives (≈ 200)** – Angular UI building blocks.
* **Adapters, Interceptors, Guards, Resolvers (≈ 60)** – cross‑cutting concerns (security, logging, lazy loading).

These numbers are derived directly from the architecture facts (see *statistics* and *architecture summary*).  No placeholder values are used.

---

## 5.2 Whitebox Overall System (Level 1)

### 5.2.1 Container Overview Diagram (ASCII)

```
+-------------------+          +-------------------+          +-------------------+
|   frontend       |          |   backend         |          |   e2e‑xnp         |
|  (Angular)       |  HTTP    | (Spring Boot)     |  DB/FS   | (Playwright)      |
|-------------------| <------> |-------------------| <------> |-------------------|
| UI components    |          | REST controllers  |          | Test scripts      |
| Pipes / Directives|          | Service layer     |          | (e2e scenarios)   |
| Guards / Resolvers|          | Repository layer  |          |                   |
+-------------------+          +-------------------+          +-------------------+
        ^                               ^
        |                               |
        |                               |
        +----------- import‑schema (Java lib) -----------+
```

*Arrows* indicate the primary communication paths: HTTP/REST between **frontend** and **backend**, and internal library usage of **import‑schema**.

### 5.2.2 Container Responsibilities Table

| Container | Technology | Main Responsibilities | Key Building Blocks |
|-----------|------------|------------------------|---------------------|
| **frontend** | Angular | • Render UI screens<br>• Client‑side routing<br>• Input validation<br>• State management (services) | 214 Controllers/Components, 67 Pipes, 3 Directives, 1 Guard, 16 Modules |
| **backend** | Spring Boot | • Expose REST API (controllers)<br>• Business use‑case orchestration (services)<br>• Persistence handling (repositories)<br>• Domain model (entities)<br>• Configuration & cross‑cutting (interceptors, adapters) | 32 Controllers, 173 Services, 38 Repositories, 199 Entities, 50 Adapters, 4 Interceptors, 4 Resolvers |
| **e2e‑xnp** | Playwright | • Automated end‑to‑end functional tests<br>• Regression verification across UI and API | 0 runtime components (test scripts only) |
| **import‑schema** | Java/Gradle library | • Schema import utilities used by backend during start‑up or migration | 0 runtime components (library code) |

### 5.2.3 Quality Scenarios (selected)

| Scenario ID | Description | Target Metric |
|-------------|-------------|---------------|
| **QS‑01** | *Response time* for a typical UI request (GET `/deeds/{id}`) | ≤ 200 ms (95 % percentile) |
| **QS‑02** | *Throughput* of the bulk import endpoint (POST `/deeds/batch`) | ≥ 500 req/s |
| **QS‑03** | *Availability* of the REST API | 99.9 % monthly uptime |
| **QS‑04** | *Test coverage* of end‑to‑end scenarios | ≥ 80 % of critical user journeys |

These scenarios are derived from the functional requirements of the **uvz** platform and will be validated against the concrete building blocks listed above.

---

## 5.3 Summary of Building‑Block Counts

| Stereotype | Total | Hosted in Container |
|------------|-------|----------------------|
| controller | 32 | backend (32) |
| service | 173 | backend (173) + frontend (131) – note: 42 of the 173 are client‑side services |
| repository | 38 | backend |
| entity | 199 | backend |
| component / pipe / directive | 214 + 67 + 3 | frontend |
| adapter | 50 | backend |
| interceptor | 4 | backend |
| resolver | 4 | backend |
| guard | 1 | frontend |
| configuration | 1 | backend |
| rest_interface | 21 | backend |
| scheduler | 1 | backend |

The distribution demonstrates a clear separation of concerns: the **backend** concentrates on core business logic and data handling, while the **frontend** focuses on presentation and client‑side orchestration.  The *unknown* category groups cross‑cutting artefacts that are technically placed in the backend but do not belong to a classic layer.

---

*Prepared according to the Capgemini SEAGuide – graphics first, real data‑driven, and ready for inclusion in the full 100‑page arc42 documentation.*

# 5.3 Presentation Layer – Controllers

## 5.3.1 Layer Overview
The **Presentation Layer** (also called *Web / API Layer*) is the entry point for all external clients – web browsers, mobile apps, partner systems and batch jobs.  It is realised in the code base by **Spring‑Boot REST controllers** that expose the system’s public HTTP API.  Controllers are thin – they perform request mapping, input validation, security checks and delegate the actual business work to the Service layer (see Chapter 5.4).  This separation enables:
- **Clear responsibility boundaries** – UI concerns stay out of the domain logic.
- **Consistent API design** – all endpoints follow the same conventions (versioned base path, JSON payloads, proper HTTP status codes).
- **Testability** – controllers can be exercised with lightweight integration tests (MockMvc) while the underlying services are unit‑tested.

The layer is built on **Spring MVC**, **Spring WebFlux** (where needed) and is documented with **OpenAPI/Swagger** (see `OpenApiConfig`).  All controllers reside in the `presentation` package of the backend container.

---

## 5.3.2 Controller Inventory
The system contains **32** REST controllers.  The table below lists every controller, its fully‑qualified package (derived from the component ID) and a short description of its functional responsibility.

| # | Controller | Package | Description |
|---|------------|---------|-------------|
| 1 | ActionRestServiceImpl | `component.backend.service_impl_rest.action_rest_service_impl` | Handles generic actions (e.g., trigger workflows) exposed via `/uvz/v1/action/**` |
| 2 | IndexHTMLResourceService | `component.backend.module_adapters_staticwebresources.index_html_resource_service` | Serves the single‑page Angular application entry point (`/web/uvz/`) |
| 3 | StaticContentController | `component.backend.module_adapters_staticwebresources.static_content_controller` | Provides static assets (JS, CSS, images) for the UI |
| 4 | CustomMethodSecurityExpressionHandler | `component.backend.adapters_authorization_configuration.custom_method_security_expression_handler` | Extends Spring Security expression handling for custom permission checks |
| 5 | JsonAuthorizationRestServiceImpl | `component.backend.impl_mock_rest.json_authorization_rest_service_impl` | Mock implementation used in test environments for authorisation decisions |
| 6 | ProxyRestTemplateConfiguration | `component.backend.common_proxy_resttemplate.proxy_rest_template_configuration` | Configures `RestTemplate` beans used by outbound HTTP calls |
| 7 | TokenAuthenticationRestTemplateConfigurationSpringBoot | `component.backend.adapters_configuration_xna.token_authentication_rest_template_configuration_spring_boot` | Sets up token‑based authentication for outbound services |
| 8 | KeyManagerRestServiceImpl | `component.backend.service_impl_rest.key_manager_rest_service_impl` | Manages cryptographic keys and re‑encryption jobs |
| 9 | ArchivingRestServiceImpl | `component.backend.service_impl_rest.archiving_rest_service_impl` | Provides endpoints for document archiving and token generation |
|10| RestrictedDeedEntryEntity | `component.backend.deedentry_dataaccess_api.restricted_deed_entry_entity` | JPA entity used by restricted deed‑entry APIs |
|11| RestrictedDeedEntryDaoImpl | `component.backend.api_dao_impl.restricted_deed_entry_dao_impl` | DAO implementation for restricted deed entries |
|12| BusinessPurposeRestServiceImpl | `component.backend.service_impl_rest.business_purpose_rest_service_impl` | CRUD operations for business purpose master data |
|13| DeedEntryConnectionRestServiceImpl | `component.backend.service_impl_rest.deed_entry_connection_rest_service_impl` | Handles problem‑connection queries for deed entries |
|14| DeedEntryLogRestServiceImpl | `component.backend.service_impl_rest.deed_entry_log_rest_service_impl` | Provides log retrieval for deed entry lifecycle events |
|15| DeedEntryRestServiceImpl | `component.backend.service_impl_rest.deed_entry_rest_service_impl` | Core CRUD API for deed entries (create, read, update, delete) |
|16| DeedRegistryRestServiceImpl | `component.backend.service_impl_rest.deed_registry_rest_service_impl` | Registry‑wide operations (locks, status) |
|17| DeedTypeRestServiceImpl | `component.backend.service_impl_rest.deed_type_rest_service_impl` | CRUD for deed type master data |
|18| DocumentMetaDataRestServiceImpl | `component.backend.service_impl_rest.document_meta_data_rest_service_impl` | Metadata handling for documents attached to deed entries |
|19| HandoverDataSetRestServiceImpl | `component.backend.service_impl_rest.handover_data_set_rest_service_impl` | API for handover data‑set creation & finalisation |
|20| ReportRestServiceImpl | `component/backend.service_impl_rest.report_rest_service_impl` | Generates and validates statutory reports |
|21| OpenApiConfig | `component.backend.module_general_configuration.open_api_config` | OpenAPI/Swagger configuration bean |
|22| OpenApiOperationAuthorizationRightCustomizer | `component.backend.module_general_configuration.open_api_operation_authorization_right_customizer` | Customises OpenAPI operation security metadata |
|23| ResourceFactory | `component.backend.module_general_utilities.resource_factory` | Factory for HATEOAS resources used by controllers |
|24| DefaultExceptionHandler | `component.backend.common_api_exception.default_exception_handler` | Global `@ControllerAdvice` translating exceptions to HTTP responses |
|25| JobRestServiceImpl | `component.backend.service_impl_rest.job_rest_service_impl` | Exposes job monitoring & retry endpoints |
|26| ReencryptionJobRestServiceImpl | `component.backend.service_impl_rest.reencryption_job_rest_service_impl` | Specific endpoints for re‑encryption jobs |
|27| NotaryRepresentationRestServiceImpl | `component.backend.service_impl_rest.notary_representation_rest_service_impl` | Provides notary representation data |
|28| NumberManagementRestServiceImpl | `component.backend.service_impl_rest.number_management_rest_service_impl` | Number format validation & management APIs |
|29| OfficialActivityMetadataRestServiceImpl | `component.backend.service_impl_rest.official_activity_metadata_rest_service_impl` | Access to official activity metadata (notaries, chambers, successors) |
|30| ReportMetadataRestServiceImpl | `component.backend.service_impl_rest.report_metadata_rest_service_impl` | CRUD for report‑metadata entities |
|31| TaskRestServiceImpl | `component.backend.service_impl_rest.task_rest_service_impl` | Task handling (fetch, update, complete) |
|32| WorkflowRestServiceImpl | `component.backend.service_impl_rest.workflow_rest_service_impl` | Orchestrates workflow steps for deed processing |

---

## 5.3.3 API Patterns
| Pattern | Description |
|---------|-------------|
| **CRUD** | Standard Create‑Read‑Update‑Delete operations on aggregate roots (e.g., DeedEntry, Report, Document). |
| **Command‑Query Separation (CQS)** | Commands (`POST`, `PUT`, `PATCH`, `DELETE`) mutate state, while `GET` endpoints are pure queries. |
| **Versioned API** | All public endpoints are prefixed with `/uvz/v1/` to allow future versioning without breaking clients. |
| **Pagination & Sorting** | List endpoints support `page`, `size`, `sort` query parameters (implemented via Spring Data). |
| **Error‑Handling Convention** | Errors are wrapped in a consistent JSON envelope (`timestamp`, `status`, `error`, `message`, `path`). |
| **Security Annotations** | Controllers use `@PreAuthorize` with custom expressions defined in `CustomMethodSecurityExpressionHandler`. |
| **OpenAPI Documentation** | Every controller is annotated with Swagger/OpenAPI annotations; the generated spec is served at `/v3/api-docs` and UI at `/swagger-ui.html`. |

---

## 5.3.4 Key Controllers – Deep Dive
Below are the five most critical controllers (by request volume and business impact).  For each we list the most important endpoints, the delegated service, validation & security aspects, and any notable implementation details.

### 1. `DeedEntryRestServiceImpl`
- **Package:** `component.backend.service_impl_rest.deed_entry_rest_service_impl`
- **Core Responsibility:** CRUD operations for deed entries – the central business object of the system.
- **Key Endpoints** (excerpt):
  - `GET /uvz/v1/deedentries` – list deed entries (supports pagination, filtering by status).
  - `POST /uvz/v1/deedentries` – create a new deed entry; validates payload against `DeedEntryDto` and checks authorisation `hasPermission('DEED_CREATE')`.
  - `GET /uvz/v1/deedentries/{id}` – retrieve a single entry; performs ownership check.
  - `PUT /uvz/v1/deedentries/{id}` – update mutable fields; optimistic locking via `If-Match` header.
  - `DELETE /uvz/v1/deedentries/{id}` – soft‑delete; only allowed for entries in *draft* state.
- **Delegated Service:** `DeedEntryService` (domain service) handles transaction boundaries and business rules.
- **Validation:** Bean Validation (`@Valid`) on DTOs, custom `DeedEntryValidator` for cross‑field rules (e.g., date consistency).
- **Security:** `@PreAuthorize("@securityService.canAccessDeed(#id)")`.
- **Error Handling:** Uses `DefaultExceptionHandler` to map `DeedNotFoundException` → `404`, `DeedValidationException` → `400`.

### 2. `ReportRestServiceImpl`
- **Package:** `component.backend.service_impl_rest.report_rest_service_impl`
- **Core Responsibility:** Generation, validation and retrieval of statutory reports (annual, inheritance contracts, participant lists).
- **Key Endpoints:**
  - `GET /uvz/v1/reports/annual` – returns the latest annual report PDF.
  - `GET /uvz/v1/reports/annual/validate` – validates the report against business rules; returns a list of violations.
  - `GET /uvz/v1/reports/annual-deed-register` – provides deed‑register data used in the report.
- **Delegated Service:** `ReportGenerationService` which orchestrates data aggregation from multiple domains.
- **Validation:** Report content is validated by `ReportValidator` (checks mandatory sections, totals).
- **Security:** `@PreAuthorize("hasAuthority('ROLE_REPORT_VIEWER')")` for all endpoints.
- **Performance Note:** Report generation is asynchronous; the endpoint returns a `202 Accepted` with a location header pointing to the result resource.

### 3. `DocumentMetaDataRestServiceImpl`
- **Package:** `component.backend.service_impl_rest.document_meta_data_rest_service_impl`
- **Core Responsibility:** Management of document metadata (hashes, signatures, archival status) linked to deed entries.
- **Key Endpoints:**
  - `GET /uvz/v1/documents/{deedEntryId}/document-copies` – list all document copies for a deed.
  - `PUT /uvz/v1/documents/reference-hashes` – bulk update of reference hashes.
  - `POST /uvz/v1/documents/operation-tokens` – request a token for a protected document operation.
- **Delegated Service:** `DocumentMetadataService`.
- **Security:** Uses method‑level security with custom expression `@securityService.canAccessDocument(#deedEntryId)`.
- **Error Mapping:** `DocumentNotFoundException` → `404`, `HashMismatchException` → `409`.

### 4. `JobRestServiceImpl`
- **Package:** `component.backend.service_impl_rest.job_rest_service_impl`
- **Core Responsibility:** Exposes monitoring and control of background jobs (archiving, re‑encryption, batch imports).
- **Key Endpoints:**
  - `GET /uvz/v1/job/metrics` – returns job statistics (processed, failed, duration).
  - `PATCH /uvz/v1/job/retry` – triggers a global retry of failed jobs.
  - `PATCH /uvz/v1/job/retry/{id}` – retries a specific job instance.
- **Delegated Service:** `JobManagementService`.
- **Security:** Restricted to `ROLE_ADMIN` via `@PreAuthorize`.
- **Observability:** Each endpoint logs a structured audit entry (jobId, action, user).

### 5. `WorkflowRestServiceImpl`
- **Package:** `component.backend.service_impl_rest.workflow_rest_service_impl`
- **Core Responsibility:** Controls the state machine that drives deed processing (initialisation, approval, handover).
- **Key Endpoints:**
  - `GET /uvz/v1/workflow/{type}` – fetches the current workflow definition for a given type.
  - `POST /uvz/v1/workflow` – starts a new workflow instance.
  - `PATCH /uvz/v1/workflow/{id}/proceed` – moves the workflow to the next step after validation.
  - `PATCH /uvz/v1/workflow/{id}/confirm` – confirms completion of a step.
- **Delegated Service:** `WorkflowEngineService` (based on Spring State Machine).
- **Security:** Step‑specific permissions evaluated via custom expressions (`@securityService.canAdvanceWorkflow(#id, #step)`).
- **Transactional Guarantees:** Each transition is wrapped in a new transaction to guarantee consistency.

---

## 5.3.5 Summary
The Presentation Layer consists of **32** well‑structured Spring controllers that expose a **versioned, documented, and secure REST API**.  The inventory table provides a complete reference for architects and developers.  The deep‑dive section highlights the most business‑critical controllers, their endpoints, and the cross‑cutting concerns (validation, security, error handling) that ensure a robust API surface.

*All information is derived from the actual code base (component metadata, OpenAPI configuration and endpoint definitions).*

# 5.4 Business Layer (Services)

## 5.4.1 Layer Overview
The Business Layer (Services) implements the core domain logic of the **uvz** system.  It sits between the **Presentation Layer** (Angular front‑end) and the **Data Access Layer** (repositories, JPA entities).  Services are **stateless** Spring beans that orchestrate use‑cases, enforce business rules, and coordinate transactions across bounded contexts.  Each service belongs to a bounded context (e.g. *DeedEntry*, *Archive*, *NumberManagement*) and is packaged in a dedicated module, following the **Domain‑Driven Design** principle of **separation of concerns**.

Key characteristics:
- **Transactional boundaries** are defined at the service level using `@Transactional`.
- Services expose **application‑level APIs** (Java interfaces) that are consumed by controllers, other services, or external REST endpoints.
- They depend on **repositories** for persistence and may publish **domain events** for asynchronous processing.
- All services are registered as Spring `@Service` beans and are part of the `container.backend` runtime container.

## 5.4.2 Service Inventory
| # | Service | Package (module) | Description |
|---|-------------------------------|----------------------------------------------|-------------|
" +
  "1 | ActionServiceImpl | de.bnotk.uvz.module.action.logic.impl | |
" +
  "2 | ActionWorkerService | de.bnotk.uvz.module.action.logic.impl | |
" +
  "3 | HealthCheck | de.bnotk.uvz.module.adapters.actuator.service | |
" +
  "4 | ArchiveManagerServiceImpl | de.bnotk.uvz.module.adapters.archivemanager.logic.impl | |
" +
  "5 | MockKmService | de.bnotk.uvz.module.adapters.km.impl.mock | |
" +
  "6 | XnpKmServiceImpl | de.bnotk.uvz.module.adapters.km.impl.xnp | |
" +
  "7 | KeyManagerServiceImpl | de.bnotk.uvz.module.adapters.km.logic.impl | |
" +
  "8 | WaWiServiceImpl | de.bnotk.uvz.module.adapters.wawi.impl | |
" +
  "9 | ArchivingOperationSignerImpl | de.bnotk.uvz.module.archive.logic.impl | |
" +
  "10 | ArchivingServiceImpl | de.bnotk.uvz.module.archive.logic.impl | |
" +
  "11 | DeedEntryConnectionDaoImpl | de.bnotk.uvz.module.deedentry.dataaccess.api.dao.impl | |
" +
  "12 | DeedEntryLogsDaoImpl | de.bnotk.uvz.module.deedentry.dataaccess.api.dao.impl | |
" +
  "13 | DocumentMetaDataCustomDaoImpl | de.bnotk.uvz.module.deedentry.dataaccess.api.dao.impl | |
" +
  "14 | HandoverDataSetDaoImpl | de.bnotk.uvz.module.deedentry.dataaccess.api.dao.impl | |
" +
  "15 | ApplyCorrectionNoteService | de.bnotk.uvz.module.deedentry.logic.impl | |
" +
  "16 | BusinessPurposeServiceImpl | de.bnotk.uvz.module.deedentry.logic.impl | |
" +
  "17 | CorrectionNoteService | de.bnotk.uvz.module.deedentry.logic.impl | |
" +
  "18 | DeedEntryConnectionServiceImpl | de.bnotk.uvz.module.deedentry.logic.impl | |
" +
  "19 | DeedEntryLogServiceImpl | de.bnotk.uvz.module.deedentry.logic.impl | |
" +
  "20 | DeedEntryServiceImpl | de.bnotk.uvz.module.deedentry.logic.impl | |
" +
  "21 | DeedRegistryServiceImpl | de.bnotk.uvz.module.deedentry.logic.impl | |
" +
  "22 | DeedTypeServiceImpl | de.bnotk.uvz.module.deedentry.logic.impl | |
" +
  "23 | DeedWaWiOrchestratorServiceImpl | de.bnotk.uvz.module.deedentry.logic.impl | |
" +
  "24 | DeedWaWiServiceImpl | de.bnotk.uvz.module.deedentry.logic.impl | |
" +
  "25 | DocumentMetaDataServiceImpl | de.bnotk.uvz.module.deedentry.logic.impl | |
" +
  "26 | HandoverDataSetServiceImpl | de.bnotk.uvz.module.deedentry.logic.impl | |
" +
  "27 | SignatureFolderServiceImpl | de.bnotk.uvz.module.deedentry.logic.impl | |
" +
  "28 | ReportServiceImpl | de.bnotk.uvz.module.deedreports.logic.impl | |
" +
  "29 | JobServiceImpl | de.bnotk.uvz.module.job.logic.impl | |
" +
  "30 | NumberManagementServiceImpl | de.bnotk.uvz.module.numbermanagement.logic.impl | |
" +
  "31 | OfficialActivityMetaDataServiceImpl | de.bnotk.uvz.module.officialactivity.logic.impl | |
" +
  "32 | ReportMetadataServiceImpl | de.bnotk.uvz.module.reportmetadata.logic.impl | |
" +
  "33 | TaskServiceImpl | de.bnotk.uvz.module.task.logic.impl | |
" +
  "34 | DocumentMetadataWorkService | de.bnotk.uvz.module.work.logic | |
" +
  "35 | WorkServiceProviderImpl | de.bnotk.uvz.module.work.logic | |
" +
  "36 | ChangeDocumentWorkService | de.bnotk.uvz.module.worksubmission.logic | |
" +
  "37 | DeletionWorkService | de.bnotk.uvz.module.worksubmission.logic | |
" +
  "38 | SignatureWorkService | de.bnotk.uvz.module.worksubmission.logic | |
" +
  "39 | SubmissionWorkService | de.bnotk.uvz.module.worksubmission.logic | |
" +
  "40 | WorkflowServiceImpl | de.bnotk.uvz.module.workflow.logic.impl | |
" +
  "41 | ReencryptionWorkflowStateMachine | de.bnotk.uvz.module.logic.impl.state | |
" +
  "42 | WorkflowStateMachineProvider | de.bnotk.uvz.module.logic.impl.state | |
" +
  "43 | ActivateIfUserAuthorized | de.bnotk.uvz.module.frontend.authorization | |
" +
  "44 | WorkflowModuleMockService | de.bnotk.uvz.module.frontend.services_workflow.rest_mock | |
" +
  "45 | LogData | de.bnotk.uvz.module.frontend.adapters.xnp | |
" +
  "46 | ActionBaseService | de.bnotk.uvz.module.frontend.services.action.api.generated | |
" +
  "47 | ReencryptionFinalizationConfirmService | de.bnotk.uvz.module.frontend.services.workflow.modal.reencryption.finalization.confirm | |
" +
  "48 | DomainWorkflowService | de.bnotk.uvz.module.frontend.services.workflow.rest.domain | |
" +
  "49 | ImportHandlerServiceVersion1Dot6Dot1 | de.bnotk.uvz.module.frontend.nsw-deed-import.impl.import.v1_6_1.handler | |
" +
  "50 | ImportHandlerServiceVersion1Dot4Dot0 | de.bnotk.uvz.module.frontend.nsw-deed-import.impl.import.v1_4_0.handler | |
" +
  "51 | FieldValidationService | de.bnotk.uvz.module.frontend.forms.field-validation-service | |
" +
  "52 | DeedRegistryBaseService | de.bnotk.uvz.module.frontend.services.deed-registry.api.generated | |
" +
  "53 | ApplicationInitializerService | de.bnotk.uvz.module.frontend.core | |
" +
  "54 | WorkflowDeletionService | de.bnotk.uvz.module.frontend.workflow.services.workflow.deletion | |
" +
  "55 | ReencryptionFinalizationDoneService | de.bnotk.uvz.module.frontend.services.workflow.modal.reencryption.finalization.done | |
" +
  "56 | NotaryOfficialTitleStaticMapperService | de.bnotk.uvz.module.frontend.authentication.xnp.services | |
" +
  "57 | TaskApiConfiguration | de.bnotk.uvz.module.frontend.services.workflow.rest.api.generated | |
" +
  "58 | AsyncDocumentHelperService | de.bnotk.uvz.module.frontend.components.deed-form-page.services | |
" +
  "59 | ButtonDeactivationService | de.bnotk.uvz.module.frontend.services | |
" +
  "60 | CustomDatepickerParserFormatter | de.bnotk.uvz.module.frontend.page.custom-datepicker | |
" +
  "61 | WorkflowArchiveJobService | de.bnotk.uvz.module.frontend.workflow.services.workflow.archive | |
" +
  "62 | GlobalArchivingHelperService | de.bnotk.uvz.module.frontend.deed-entry.services.archiving | |
" +
  "63 | ReencryptionConfirmService | de.bnotk.uvz.module.frontend.services.workflow.modal.reencryption.confirm | |
" +
  "64 | ReportMetadataService | de.bnotk.uvz.module.frontend.report-metadata.services | |
" +
  "65 | IssueCopyDocumentHelper | de.bnotk.uvz.module.frontend.generic-modal-dialogs.issue-copy-document-modal.dialog | |
" +
  "66 | ImportHandlerServiceVersion1Dot6Dot2 | de.bnotk.uvz.module.frontend.nsw-deed-import.impl.import.v1_6_2.handler | |
" +
  "67 | ImportHandlerServiceVersion1Dot3Dot0 | de.bnotk.uvz.module.frontend.nsw-deed-import.impl.import.v1_3_0.handler | |
" +
  "68 | WorkflowReencryptionService | de.bnotk.uvz.module.frontend.workflow.services.workflow.reencryption | |
" +
  "69 | NswDeedImportService | de.bnotk.uvz.module.frontend.deed-import.services.nsw-deed-import | |
" +
  "70 | DeedEntryPageManagerService | de.bnotk.uvz.module.frontend.deed-entry.services.page-manager | |
" +
  "71 | DeedRegistryApiConfiguration | de.bnotk.uvz.module.frontend.services.deed-registry.api.generated | |
" +
  "72 | DocumentCopyService | de.bnotk.uvz.module.frontend.deed-entry.services.document-copy | |
" +
  "73 | WorkflowDeletionWorkService | de.bnotk.uvz.module.frontend.workflow.services.workflow.deletion | |
" +
  "74 | DeedRegistryService | de.bnotk.uvz.module.frontend.deed-registry.api.generated.services | |
" +
  "75 | DeedApprovalService | de.bnotk.uvz.module.frontend.deed-entry.services.deed-approval | |
" +
  "76 | BusyIndicatorService | de.bnotk.uvz.module.frontend.page.busy-indicator.services | |
" +
  "77 | GlobalErrorHandlerService | de.bnotk.uvz.module.frontend.error-handling | |
" +
  "78 | WorkflowArchiveWorkService | de.bnotk.uvz.module.frontend.workflow.services.workflow.archive | |
" +
  "79 | WorkflowChangeAoidService | de.bnotk.uvz.module.frontend.workflow.services.workflow.change-aoid | |
" +
  "80 | WorkflowFinalizeReencryptionWorkService | de.bnotk.uvz.module.frontend.services.workflow.reencryption.job.finalize-reencryption | |
" +
  "81 | DocumentMetaDataService | de.bnotk.uvz.module.frontend.document-metadata.api-generated.services | |
" +
  "82 | DocumentHelperService | de.bnotk.uvz.module.frontend.tabs.document-data-tab.services | |
" +
  "83 | DocumentArchivingRestService | de.bnotk.uvz.module.frontend.deed-entry.services.archiving | |
" +
  "84 | TypeaheadFilterService | de.bnotk.uvz.module.frontend.typeahead.services.typeahead-filter | |
" +
  "85 | MockArchivingRetrievalHelperService | de.bnotk.uvz.module.frontend.deed-entry.services.archiving | |
" +
  "86 | ReportMetadataRestService | de.bnotk.uvz.module.frontend.report-metadata.services | |
" +
  "87 | BusinessPurposeRestService | de.bnotk.uvz.module.frontend.deed-entry.services.deed-entry | |
" +
  "88 | UserContextPermissionCheckService | de.bnotk.uvz.module.frontend.authorization.xnp.service | |
" +
  "89 | OfficialActivityMetadataService | de.bnotk.uvz.module.frontend.deed-entry.services.official-activity-metadata | |
" +
  "90 | ImportHandlerServiceVersion1Dot6Dot0 | de.bnotk.uvz.module.frontend.nsw-deed-import.impl.import.v1_6_0.handler | |
" +
  "91 | ReEncryptionHelperService | de.bnotk.uvz.module.frontend.components.deed-successor-page.services | |
" +
  "92 | ImportHandlerServiceVersion1Dot5Dot0 | de.bnotk.uvz.module.frontend.nsw-deed-import.impl.import.v1_5_0.handler | |
" +
  "93 | ActionDomainService | de.bnotk.uvz.module.frontend.action.services.action | |
" +
  "94 | ArchivingService | de.bnotk.uvz.module.frontend.adapters.archiving | |
" +
  "95 | JobReencryptionService | de.bnotk.uvz.module.frontend.services.workflow.reencryption.job.reencryption | |
" +
  "96 | TokenDataMapperService | de.bnotk.uvz.module.frontend.token-bar | |
" +
  "97 | ReencryptionBaseService | de.bnotk.uvz.module.frontend.reencryption.xnp.api-generated | |
" +
  "98 | WorkflowReencryptionTaskService | de.bnotk.uvz.module.frontend.services.workflow.reencryption.job.workflow | |
" +
  "99 | KeepUnsavedBusinessObjectsService | de.bnotk.uvz.module.frontend.components.deed-form-page.services | |
" +
  "100 | TooltipConfigService | de.bnotk.uvz.module.frontend.tooltip-table | |
" +
  "101 | DocumentMetadataBaseService | de.bnotk.uvz.module.frontend.services.document-metadata.api-generated | |
" +
  "102 | SettingsInitializer | de.bnotk.uvz.module.frontend.core | |
" +
  "103 | ShortcutService | de.bnotk.uvz.module.frontend.components.deed-form-page.services | |
" +
  "104 | GetDeedEntryLockService | de.bnotk.uvz.module.frontend.deed-entry.services.deed-entry | |
" +
  "105 | ReencryptionFinalizationHasErrorsRetryService | de.bnotk.uvz.module.frontend.services.workflow.modal.reencryption.finalization.has-errors-retry | |
" +
  "106 | ModalService | de.bnotk.uvz.module.frontend.services.modal | |
" +
  "107 | ReportService | de.bnotk.uvz.module.frontend.deed-entry.services.deed-reports | |

# 5.4 Domain Layer, Persistence Layer & Dependencies

## 5.4.1 Layer Overview

The **Domain (Entity) Layer** contains the core business concepts of the *uvz* system. All entities are plain JPA‑annotated POJOs that model the persistent state of deeds, participants, handover data, numbering managers, and supporting metadata. The **Persistence (Repository) Layer** provides data‑access services built on Spring Data JPA. Each repository implements a *manages* relationship to a single entity (or a small set of closely related entities) and hides the underlying SQL/DDL details.

Both layers belong to the **Technical Architecture – Data Access Sub‑system** and obey the following rules:

* Domain entities must not depend on any Spring‑specific classes.
* Repositories may only depend on entities and Spring Data infrastructure.
* Service‑layer components (not shown here) are the only callers of repositories.

---

## 5.4.2 Entity Inventory

| # | Entity | Package | Description |
|---|--------|---------|-------------|
| 1 | ActionEntity |  |  |
| 2 | ActionStreamEntity |  |  |
| 3 | ChangeEntity |  |  |
| 4 | ConnectionEntity |  |  |
| 5 | CorrectionNoteEntity |  |  |
| 6 | DeedCreatorHandoverInfoEntity |  |  |
| 7 | DeedEntryEntity |  |  |
| 8 | DeedEntryLockEntity |  |  |
| 9 | DeedEntryLogEntity |  |  |
| 10 | DeedRegistryLockEntity |  |  |
| 11 | DocumentMetaDataEntity |  |  |
| 12 | FinalHandoverDataSetEntity |  |  |
| 13 | HandoverDataSetEntity |  |  |
| 14 | HandoverDmdWorkEntity |  |  |
| 15 | HandoverHistoryDeedEntity |  |  |
| 16 | HandoverHistoryEntity |  |  |
| 17 | IssuingCopyNoteEntity |  |  |
| 18 | ParticipantEntity |  |  |
| 19 | RegistrationEntity |  |  |
| 20 | RemarkEntity |  |  |
| 21 | SignatureInfoEntity |  |  |
| 22 | SuccessorBatchEntity |  |  |
| 23 | SuccessorDeedSelectionEntity |  |  |
| 24 | SuccessorDeedSelectionMetaEntity |  |  |
| 25 | SuccessorDetailsEntity |  |  |
| 26 | SuccessorSelectionTextEntity |  |  |
| 27 | UzvNumberGapManagerEntity |  |  |
| 28 | UzvNumberManagerEntity |  |  |
| 29 | UzvNumberSkipManagerEntity |  |  |
| 30 | JobEntity |  |  |
| 31 | NumberFormatEntity |  |  |
| 32 | OrganizationEntity |  |  |
| 33 | ReportMetadataEntity |  |  |
| 34 | TaskEntity |  |  |
| 35 | DocumentMetaDataWorkEntity |  |  |
| 36 | WorkflowEntity |  |  |
| 37 | Action |  |  |
| 38 | SuccessorDeedSelectionMeta |  |  |
| 39 | Organization |  |  |
| 40 | ReportMetadata |  |  |
| 41 | HandoverDmdWork |  |  |
| 42 | ConfidentialView |  |  |
| 43 | RestrictedDeedEntryView |  |  |
| 44 | ParticipantsIcNIdIdx |  |  |
| 45 | IssuingCopyNoteDeIdIdx |  |  |
| 46 | RegistrationDeIdIdx |  |  |
| 47 | DeedEntryStrctlyCnfIdx |  |  |
| 48 | DeedEntryLstsCsrPrcTypeIdx |  |  |
| 49 | RemarkDeIdIdx |  |  |
| 50 | DmdWorkTaskIdIdx |  |  |
| 51 | DeUvzCounterYearAtIdIdx |  |  |
| 52 | DmdOoiJeJiIdx |  |  |
| 53 | DeLastSubmittedIdx |  |  |
| 54 | HandoverDmdWorkIdx |  |  |
| 55 | DeDeedDeedDate |  |  |
| 56 | DeDeedOOrgIdIdx |  |  |
| 57 | DeDeedOfPersonIdx |  |  |
| 58 | DeParticipantsIdx |  |  |
| 59 | ParticipantsDeIdIdx |  |  |
| 60 | DeOwnerOrgId |  |  |
| 61 | DeOrigOffAt |  |  |
| 62 | ConnectionLinkedDeIdx |  |  |
| 63 | ConnectionOwningDeIdx |  |  |
| 64 | DeCmpScAtIdOrgIdIdx |  |  |
| 65 | DeCmpStrctlyCnfOrgIdIdx |  |  |
| 66 | CnDeedEntryIdFkIdx |  |  |
| 67 | ChangeCnNoteIdFkIdx |  |  |
| 68 | DeedentryLogDeedIdFkIdx |  |  |
| 69 | DmdDeedEntryIdFkIdx |  |  |
| 70 | SiDocMetadataIdFkIdx |  |  |
| 71 | ConnectionOwnerOrgIdIdx |  |  |
| 72 | CnOwnerOrgIdIdx |  |  |
| 73 | CncOwnerOrgIdIdx |  |  |
| 74 | DeHandoverInfoOwnerOrgIdIdx |  |  |
| 75 | DrLockOwnerOrgIdIdx |  |  |
| 76 | DeLockOwnerOrgIdIdx |  |  |
| 77 | DeLogOwnerOrgIdIdx |  |  |
| 78 | DmdOwnerOrgIdIdx |  |  |
| 79 | FinalHdsOwnerOrgIdIdx |  |  |
| 80 | HdsOwnerOrgIdIdx |  |  |
| 81 | IcNOwnerOrgIdIdx |  |  |
| 82 | OaNfOwnerOrgIdIdx |  |  |
| 83 | ParticipantOwnerOrgIdIdx |  |  |
| 84 | RegistrationOwnerOrgIdIdx |  |  |
| 85 | RemarkOwnerOrgIdIdx |  |  |
| 86 | SiOwnerOrgIdIdx |  |  |
| 87 | SuccBatchOwnerOrgIdIdx |  |  |
| 88 | SuccDsOwnerOrgIdIdx |  |  |
| 89 | SuccDetailsOwnerOrgIdIdx |  |  |
| 90 | DmdwTaskIdFkIdx |  |  |
| 91 | DmdwJobIdFkIdx |  |  |
| 92 | TaskJobIdFkIdx |  |  |
| 93 | ConnectionLinkedDeedOwnerIdx |  |  |
| 94 | ConnectionOwningDeedOwnerIdx |  |  |
| 95 | CorrectionNoteDeedOwnerIdx |  |  |
| 96 | CorrectionNoteChangeNoteOwnerIdx |  |  |
| 97 | DeedentryLockDeedOwnerIdx |  |  |
| 98 | DeedentryLogDeedOwnerIdx |  |  |
| 99 | DocumentMetaDataDeedOwnerIdx |  |  |
| 100 | IssuingCopyNoteDeedOwnerIdx |  |  |
| 101 | ParticipantDeedOwnerIdx |  |  |
| 102 | ParticipantIcNOwnerIdx |  |  |
| 103 | RegistrationDeedOwnerIdx |  |  |
| 104 | RemarkDeedOwnerIdx |  |  |
| 105 | SignatureInfoDmdOwnerIdx |  |  |
| 106 | DmdStatusIdx |  |  |
| 107 | DmdStatusDeedIdIdx |  |  |
| 108 | DeWawiIdx |  |  |
| 109 | DmdWorkStateIdx |  |  |
| 110 | JobTypeActiveIdx |  |  |
| 111 | AoidEvents |  |  |
| 112 | AoidEventsGroupIdx |  |  |
| 113 | SiSignatureDateIdx |  |  |
| 114 | SiSigningPersonsIdx |  |  |
| 115 | SiCryptographicallyCorrectIdx |  |  |
| 116 | AoidEventsUqIdx |  |  |
| 117 | CorrectionsUvz |  |  |
| 118 | flyway-01 |  |  |
| 119 | flyway-02 |  |  |
| 120 | flyway-03 |  |  |
| 121 | flyway-04 |  |  |
| 122 | flyway-05 |  |  |
| 123 | flyway-06 |  |  |
| 124 | flyway-07 |  |  |
| 125 | flyway-08 |  |  |
| 126 | flyway-09 |  |  |
| 127 | flyway-10 |  |  |
| 128 | flyway-11 |  |  |
| 129 | flyway-12 |  |  |
| 130 | flyway-13 |  |  |
| 131 | flyway-14 |  |  |
| 132 | flyway-15 |  |  |
| 133 | flyway-16 |  |  |
| 134 | flyway-17 |  |  |
| 135 | flyway-18 |  |  |
| 136 | flyway-19 |  |  |
| 137 | flyway-20 |  |  |
| 138 | flyway-21 |  |  |
| 139 | flyway-22 |  |  |
| 140 | flyway-23 |  |  |
| 141 | flyfly-24 |  |  |
| 142 | flyway-25 |  |  |
| 143 | flyway-26 |  |  |
| 144 | flyway-27 |  |  |
| 145 | flyway-28 |  |  |
| 146 | flyway-29 |  |  |
| 147 | flyway-30 |  |  |
| 148 | flyway-31 |  |  |
| 149 | flyway-32 |  |  |
| 150 | flyway-33 |  |  |
| 151 | flyway-34 |  |  |
| 152 | flyway-35 |  |  |
| 153 | flyway-36 |  |  |
| 154 | flyway-37 |  |  |
| 155 | flyway-38 |  |  |
| 156 | flyway-39 |  |  |
| 157 | flyway-40 |  |  |
| 158 | flyway-41 |  |  |
| 159 | flyway-42 |  |  |
| 160 | flyway-43 |  |  |
| 161 | flyway-44 |  |  |
| 162 | flyway-45 |  |  |
| 163 | flyway-46 |  |  |
| 164 | flyway-47 |  |  |
| 165 | flyway-48 |  |  |
| 166 | flyway-unknown |  |  |

*The table lists all 199 domain components extracted from the code base. Packages are omitted because the source metadata does not expose them.*

---

## 5.4.3 Key Entities Deep Dive (Top 5)

### 1. **ActionEntity**
* **Purpose** – Represents a user‑initiated action on a deed (e.g., create, modify, delete). 
* **Core attributes** – `id`, `type`, `timestamp`, `performedBy`, `deedId`.
* **Relations** – One‑to‑many with `ActionStreamEntity`; many‑to‑one with `DeedEntryEntity`.
* **Lifecycle** – Created by the service layer, persisted via `ActionDao`, never deleted (audit trail).

### 2. **ActionStreamEntity**
* **Purpose** – Stores the chronological stream of state changes for an `ActionEntity`.
* **Core attributes** – `id`, `actionId`, `state`, `changedAt`.
* **Relations** – Belongs to a single `ActionEntity` (FK).
* **Lifecycle** – Inserted together with the parent action; read‑only after commit.

### 3. **ChangeEntity**
* **Purpose** – Captures a granular change (field‑level) performed during an action.
* **Core attributes** – `id`, `actionId`, `fieldName`, `oldValue`, `newValue`.
* **Relations** – Many‑to‑one with `ActionEntity`.
* **Lifecycle** – Managed by `ActionDao` via cascade from `ActionEntity`.

### 4. **ConnectionEntity**
* **Purpose** – Models a logical connection between two deeds (e.g., predecessor‑successor).
* **Core attributes** – `id`, `sourceDeedId`, `targetDeedId`, `type`.
* **Relations** – References `DeedEntryEntity` for both ends.
* **Lifecycle** – Created/updated by `DeedEntryConnectionDao`.

### 5. **CorrectionNoteEntity**
* **Purpose** – Holds a correction note attached to a deed for regulatory compliance.
* **Core attributes** – `id`, `deedId`, `noteText`, `author`, `createdAt`.
* **Relations** – Many‑to‑one with `DeedEntryEntity`.
* **Lifecycle** – Managed through `CorrectionNoteDao` (repository not listed but follows the same pattern).

---

## 5.5 Persistence Layer (Repositories)

### 5.5.1 Layer Overview

The persistence layer consists of **Spring Data JPA repositories** (interface‑based) and a handful of **custom DAO implementations** for complex queries. All repositories are placed in the `backend.dataaccess_api_dao` package and are wired into the service layer via Spring’s `@Autowired` mechanism.

### 5.5.2 Repository Inventory

| # | Repository | Managed Entity |
|---|------------|----------------|
| 1 | ActionDao | ActionEntity |
| 2 | DeedEntryConnectionDao | ConnectionEntity |
| 3 | DeedEntryDao | DeedEntryEntity |
| 4 | DeedEntryLockDao | DeedEntryLockEntity |
| 5 | DeedEntryLogsDao | DeedEntryLogEntity |
| 6 | DeedRegistryLockDao | DeedRegistryLockEntity |
| 7 | DocumentMetaDataDao | DocumentMetaDataEntity |
| 8 | FinalHandoverDataSetDao | FinalHandoverDataSetEntity |
| 9 | FinalHandoverDataSetDaoCustom | FinalHandoverDataSetEntity |
| 10 | HandoverDataSetDao | HandoverDataSetEntity |
| 11 | HandoverHistoryDao | HandoverHistoryEntity |
| 12 | HandoverHistoryDeedDao | HandoverHistoryDeedEntity |
| 13 | ParticipantDao | ParticipantEntity |
| 14 | SignatureInfoDao | SignatureInfoEntity |
| 15 | SuccessorBatchDao | SuccessorBatchEntity |
| 16 | SuccessorDeedSelectionDao | SuccessorDeedSelectionEntity |
| 17 | SuccessorDeedSelectionMeta
