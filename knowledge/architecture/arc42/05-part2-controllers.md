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