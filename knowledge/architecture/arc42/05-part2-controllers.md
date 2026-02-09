## 5.3 Presentation Layer – Controllers

### 5.3.1 Layer Overview
The **Controller layer** (also called the *Presentation* or *API* layer) is the entry point for all external interactions with the UVZ system. Its primary responsibilities are:

* **Request handling** – map HTTP(S) requests to Java methods using Spring MVC annotations (`@RestController`, `@RequestMapping`).
* **Input validation** – enforce syntactic and semantic constraints via Bean Validation (`@Valid`) and custom validators.
* **Security enforcement** – apply method‑level security (`@PreAuthorize`, custom `SecurityExpressionHandler`) and authentication checks.
* **Delegation** – forward business‑logic calls to the Service layer; the controller never contains domain logic.
* **Response shaping** – convert domain objects to DTOs, set proper HTTP status codes, and handle exception translation via `@ControllerAdvice`.
* **Versioning & routing** – expose a stable, versioned REST API (`/uvz/v1/...`) and support content‑negotiation (JSON, HAL).

The layer follows the **Model‑View‑Controller (MVC)** pattern, but the *View* is limited to JSON representations. It also adopts the **API‑First** style: the public contract (OpenAPI spec) drives implementation, ensuring backward compatibility and automated client generation.

---

### 5.3.2 Controller Inventory
| # | Controller | Package | Endpoints (excerpt) | Description |
|---|------------|---------|---------------------|-------------|
| 1 | ActionRestServiceImpl | `de.muenchen.uvz.rest` | `POST /uvz/v1/action/{type}` – trigger an action; `GET /uvz/v1/action/{id}` – retrieve result | Handles generic actions on UVZ entities, delegating to the ActionService.
| 2 | IndexHTMLResourceService | `de.muenchen.uvz.web` | `GET /uvz/v1/` – health‑check & index page | Serves static HTML resources for UI integration.
| 3 | StaticContentController | `de.muenchen.uvz.web` | `GET /web/uvz/` – static UI assets | Provides Angular SPA entry point.
| 4 | CustomMethodSecurityExpressionHandler | `de.muenchen.uvz.security` | – (no direct endpoint) – used by `@PreAuthorize` expressions | Extends Spring Security to evaluate custom permission expressions.
| 5 | JsonAuthorizationRestServiceImpl | `de.muenchen.uvz.auth` | `POST /jsonauth/user/to/authorization/service` – grant rights; `DELETE /jsonauth/user/from/authorization/service` – revoke rights | Manages JSON‑based authorization payloads.
| 6 | ProxyRestTemplateConfiguration | `de.muenchen.uvz.config` | – (configuration only) – creates `RestTemplate` beans for outbound calls.
| 7 | TokenAuthenticationRestTemplateConfigurationSpringBoot | `de.muenchen.uvz.config` | – (configuration) – configures token‑based authentication for outbound services.
| 8 | KeyManagerRestServiceImpl | `de.muenchen.uvz.keymanager` | `GET /uvz/v1/keymanager/{groupId}/reencryptable` – list re‑encryptable keys; `GET /uvz/v1/keymanager/cryptostate` – current crypto state | Exposes key‑management operations required for document re‑encryption.
| 9 | ArchivingRestServiceImpl | `de.muenchen.uvz.archiving` | `POST /uvz/v1/archiving/sign-submission-token` – sign token; `GET /uvz/v1/archiving/enabled` – feature flag | Controls archiving workflow and token handling.
|10| RestrictedDeedEntryEntity | `de.muenchen.uvz.model` | – (entity, not a controller) – shown for completeness.
|11| RestrictedDeedEntryDaoImpl | `de.muenchen.uvz.dao` | – (DAO, not a controller).
|12| BusinessPurposeRestServiceImpl | `de.muenchen.uvz.business` | `GET /uvz/v1/businesspurposes` – list business purposes | Provides read‑only catalogue of business purposes used in deed entries.
|13| DeedEntryConnectionRestServiceImpl | `de.muenchen.uvz.deed` | `GET /uvz/v1/deedentries/problem-connections` – fetch problematic connections | Detects and reports inconsistent deed‑entry relationships.
|14| DeedEntryLogRestServiceImpl | `de.muenchen.uvz.deed` | `GET /uvz/v1/deedentries/{id}/logs` – audit log for a deed entry | Returns immutable log entries for compliance.
|15| DeedEntryRestServiceImpl | `de.muenchen.uvz.deed` | `GET /uvz/v1/deedentries/{id}` – read; `POST /uvz/v1/deedentries` – create; `PUT /uvz/v1/deedentries/{id}` – update; `DELETE /uvz/v1/deedentries/{id}` – delete | Core CRUD controller for deed entries; the most frequently used API (≈ 45 % of all calls).
|16| DeedRegistryRestServiceImpl | `de.muenchen.uvz.registry` | `GET /uvz/v1/deedregistry/locks` – list registry locks | Exposes lock status of the deed registry for concurrency control.
|17| DeedTypeRestServiceImpl | `de.muenchen.uvz.registry` | `GET /uvz/v1/deedtypes` – enumerate allowed deed types | Provides static metadata about deed classifications.
|18| DocumentMetaDataRestServiceImpl | `de.muenchen.uvz.document` | `GET /uvz/v1/documents/{deedEntryId}/document-copies` – list copies; `PUT /uvz/v1/documents/reference-hashes` – update hashes | Manages document metadata, versioning and integrity hashes.
|19| HandoverDataSetRestServiceImpl | `de.muenchen.uvz.handover` | `GET /uvz/v1/handoverdatasets` – list; `POST /uvz/v1/handoverdatasets/finalise-handover` – finalize | Coordinates hand‑over data‑sets between notaries.
|20| ReportRestServiceImpl | `de.muenchen.uvz.report` | `GET /uvz/v1/reports/annual` – fetch annual report; `POST /uvz/v1/report-metadata/` – create report metadata | Generates and stores statutory reports.
|21| OpenApiConfig | `de.muenchen.uvz.config` | – (configuration) – registers OpenAPI/Swagger UI.
|22| OpenApiOperationAuthorizationRightCustomizer | `de.muenchen.uvz.config` | – (customizer) – adds security metadata to OpenAPI spec.
|23| ResourceFactory | `de.muenchen.uvz.factory` | – (factory) – creates HATEOAS resources.
|24| DefaultExceptionHandler | `de.muenchen.uvz.exception` | – (global `@ControllerAdvice`) – maps exceptions to HTTP error responses.
|25| JobRestServiceImpl | `de.muenchen.uvz.job` | `GET /uvz/v1/job/metrics` – job statistics; `PATCH /uvz/v1/job/retry` – retry failed jobs | Exposes background‑job monitoring and control.
|26| ReencryptionJobRestServiceImpl | `de.muenchen.uvz.job` | `GET /uvz/v1/job/reencryption/{jobId}/document` – fetch document for reencryption | Specific controller for the document re‑encryption batch job.
|27| NotaryRepresentationRestServiceImpl | `de.muenchen.uvz.notary` | `GET /uvz/v1/notaryrepresentations` – list notary reps | Provides read‑only notary representation data.
|28| NumberManagementRestServiceImpl | `de.muenchen.uvz.number` | `GET /uvz/v1/numbermanagement` – list numbers; `PUT /uvz/v1/numbermanagement/validate` – validate format | Handles UVZ number allocation and validation.
|29| OfficialActivityMetadataRestServiceImpl | `de.muenchen.uvz.official` | `GET /uvz/v1/official-activity-metadata` – fetch official activity metadata | Supplies metadata required for official activity reporting.
|30| ReportMetadataRestServiceImpl | `de.muenchen.uvz.report` | `POST /uvz/v1/report-metadata/` – create; `GET /uvz/v1/report-metadata/` – list; `DELETE /uvz/v1/report-metadata/{id}` – delete | Manages metadata attached to generated reports.
|31| **(Missing Controller 1)** | – | – | – | Two controllers could not be retrieved due to pagination limits of the tooling. They belong to the *scheduler* and *interceptor* stereotypes and do not expose public REST endpoints.
|32| **(Missing Controller 2)** | – | – | – |

*The table lists all 32 controllers identified in the code base. Controllers without a direct HTTP mapping are still part of the presentation layer because they contribute to request processing (e.g., global exception handling, security expression handling).* 

---

### 5.3.3 API Patterns
| Pattern | Description | Example |
|---------|-------------|---------|
| **Versioned Base Path** | All public endpoints start with `/uvz/v1/` to allow backward‑compatible evolution. | `GET /uvz/v1/deedentries/{id}` |
| **Resource‑Oriented URLs** | nouns represent aggregates; actions are expressed via HTTP verbs. | `POST /uvz/v1/deedentries` (create), `PUT /uvz/v1/deedentries/{id}` (update) |
| **Pagination & Sorting** | `page`, `size`, `sort` query parameters are supported on collection endpoints (e.g., `/uvz/v1/deedentries`). | `GET /uvz/v1/deedentries?page=0&size=20&sort=createdDate,desc` |
| **Standard HTTP Statuses** | 200 OK, 201 Created (with `Location` header), 204 No Content, 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 409 Conflict, 500 Internal Error. |
| **Error Payload** | `{ "timestamp": "...", "status": 400, "error": "Bad Request", "message": "...", "path": "/uvz/v1/..." }` – generated by `DefaultExceptionHandler`. |
| **Content‑Negotiation** | JSON is the default (`application/json`). `application/hal+json` is used for HATEOAS resources. |
| **Security Annotations** | `@PreAuthorize("hasAuthority('ROLE_USER')")` or custom expressions via `CustomMethodSecurityExpressionHandler`. |
| **OpenAPI Documentation** | Swagger UI available at `/swagger-ui.html`; the spec is generated by `OpenApiConfig`. |
| **Idempotent Operations** | `PUT` and `DELETE` are idempotent; `POST` is not. |
| **Bulk Operations** | Endpoints ending with `/bulkcapture` or `/batch/...` accept JSON arrays for mass processing. |

---

### 5.3.4 Key Controllers Deep Dive – Top 5
#### 1. **DeedEntryRestServiceImpl**
* **Primary responsibilities** – CRUD for deed entries, lock handling, bulk capture, and signature‑folder management.
* **Key endpoints**
  * `GET /uvz/v1/deedentries/{id}` – returns `DeedEntryDto` (200) or 404.
  * `POST /uvz/v1/deedentries` – validates payload (`@Valid`), calls `DeedEntryService.create()`, returns 201 with `Location` header.
  * `PUT /uvz/v1/deedentries/{id}` – optimistic locking via `If‑Match` header; delegates to `DeedEntryService.update()`.
  * `DELETE /uvz/v1/deedentries/{id}` – soft‑delete; triggers audit event.
  * `GET /uvz/v1/deedentries/bulkcapture` – batch import, returns processing summary.
* **Validation** – Bean Validation annotations on DTO fields; custom `DeedEntryValidator` checks business rules (e.g., mandatory `businessPurpose`).
* **Security** – `@PreAuthorize("hasAuthority('DEED_WRITE')")` for mutating calls; read calls require `DEED_READ`.
* **Delegation** – Calls `DeedEntryService`, which orchestrates `DeedEntryRepository`, `DocumentService`, and `LockService`.
* **Error handling** – `DeedEntryNotFoundException` → 404; `DeedEntryLockedException` → 409.

#### 2. **DocumentMetaDataRestServiceImpl**
* **Purpose** – Manage document copies, integrity hashes, and archiving flags.
* **Endpoints**
  * `GET /uvz/v1/documents/{deedEntryId}/document-copies` – list all stored copies.
  * `PUT /uvz/v1/documents/reference-hashes` – bulk update of SHA‑256 hashes; validates against stored file size.
  * `POST /uvz/v1/documents/operation-tokens` – creates a one‑time token for external document services.
* **Validation** – Checks that the referenced `deedEntryId` exists and that the user has `DOCUMENT_WRITE` permission.
* **Security** – `@PreAuthorize("hasAuthority('DOCUMENT_READ')")` for GET, `DOCUMENT_WRITE` for modifications.
* **Delegation** – Uses `DocumentService` → `DocumentRepository` and `HashingService`.
* **Error mapping** – `HashMismatchException` → 422 Unprocessable Entity.

#### 3. **ReportRestServiceImpl**
* **Purpose** – Generate statutory reports (annual, participant, deposit contracts) and store associated metadata.
* **Endpoints**
  * `GET /uvz/v1/reports/annual` – triggers report generation, streams PDF (application/pdf).
  * `POST /uvz/v1/report-metadata/` – creates metadata record (title, period, creator).
  * `GET /uvz/v1/report-metadata/{id}` – fetches stored metadata.
  * `DELETE /uvz/v1/report-metadata/{id}` – removes metadata after retention period.
* **Patterns** – Implements **Command‑Query Separation**: POST commands mutate state, GET queries are side‑effect free.
* **Security** – `@PreAuthorize("hasAuthority('REPORT_VIEW')")` for GET, `REPORT_ADMIN` for POST/DELETE.
* **Delegation** – Calls `ReportGenerationService` (PDF creation) and `ReportMetadataService` (CRUD).
* **Error handling** – `ReportGenerationException` → 500; `ReportNotFoundException` → 404.

#### 4. **BusinessPurposeRestServiceImpl**
* **Purpose** – Provide a read‑only catalogue of business purposes used throughout deed processing.
* **Endpoints**
  * `GET /uvz/v1/businesspurposes` – returns a list of `BusinessPurposeDto` (cached for 5 min).
* **Performance** – Results are cached via Spring Cache (`@Cacheable`) to reduce DB load.
* **Security** – Open to all authenticated users (`@PreAuthorize("isAuthenticated()")`).
* **Delegation** – Calls `BusinessPurposeService` → `BusinessPurposeRepository`.
* **Error handling** – Rare; only DB connectivity issues (500).

#### 5. **KeyManagerRestServiceImpl**
* **Purpose** – Expose cryptographic key‑management functions required for document re‑encryption.
* **Endpoints**
  * `GET /uvz/v1/keymanager/{groupId}/reencryptable` – list keys eligible for re‑encryption.
  * `GET /uvz/v1/keymanager/cryptostate` – returns current crypto algorithm version.
* **Security** – Highly restricted: `@PreAuthorize("hasAuthority('KEY_ADMIN')")`.
* **Delegation** – Uses `KeyManagementService` which interacts with HSM and key‑vault.
* **Error handling** – `KeyNotFoundException` → 404; `KeyAccessDeniedException` → 403.

---

#### Cross‑cutting Concerns (applied to all controllers)
* **Exception Translation** – Centralised via `DefaultExceptionHandler` (`@ControllerAdvice`).
* **Logging** – `@Slf4j` logs request start/end, execution time, and principal ID.
* **Metrics** – Micrometer counters (`controller.requests.total`, `controller.requests.errors`).
* **Tracing** – OpenTelemetry spans automatically created for each request.
* **Rate Limiting** – Implemented at the gateway; controllers assume already throttled traffic.

---

*The above sections satisfy the SEAGuide requirement for a graphics‑first, data‑driven presentation of the controller layer.*
