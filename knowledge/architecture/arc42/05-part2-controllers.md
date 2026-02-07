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
