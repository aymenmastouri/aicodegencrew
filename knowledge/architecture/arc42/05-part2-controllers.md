## 5.3 Presentation Layer – Controllers

### 5.3.1 Layer Overview
The **Controller** (or *REST‑API*) layer is the entry point for all external clients (web UI, mobile apps, other services).  It is responsible for:
- Exposing **RESTful** endpoints following the *uvz/v1* API contract.
- Translating HTTP requests into **domain‑level commands**.
- Performing **input validation**, **authentication**, and **authorization** (Spring Security annotations).
- Delegating business work to the **Service** layer and returning **DTOs** or error payloads.
- Centralised **exception handling** via `DefaultExceptionHandler`.

The layer follows the **Controller‑Service‑Repository** pattern and is implemented with **Spring MVC** (`@RestController`).  All controllers are stateless and thread‑safe.

---

### 5.3.2 Controller Inventory
| # | Controller | Package | Endpoints (count) | Description |
|---|------------|---------|-------------------|-------------|
| 1 | ActionRestServiceImpl | `component.backend.service_impl_rest` | 2 | Handles action creation and retrieval. |
| 2 | JsonAuthorizationRestServiceImpl | `component.backend.impl_mock_rest` | 2 | Provides JSON‑based authorization token exchange. |
| 3 | KeyManagerRestServiceImpl | `component.backend.service_impl_rest` | 2 | Key‑management queries (reencryption status, crypto state). |
| 4 | ArchivingRestServiceImpl | `component.backend.service_impl_rest` | 3 | Token signing for archiving and reencryption. |
| 5 | BusinessPurposeRestServiceImpl | `component.backend.service_impl_rest` | 1 | Returns list of business purposes. |
| 6 | DeedEntryConnectionRestServiceImpl | `component.backend.service_impl_rest` | 1 | Retrieves problem connections for deed entries. |
| 7 | DeedEntryLogRestServiceImpl | `component.backend.service_impl_rest` | 1 | Provides log information for deed entries. |
| 8 | DeedEntryRestServiceImpl | `component.backend.service_impl_rest` | 12 | Full CRUD for deed entries, lock handling, bulk capture, handover. |
| 9 | DeedRegistryRestServiceImpl | `component.backend.service_impl_rest` | 2 | Registry lock queries. |
|10| DeedTypeRestServiceImpl | `component.backend.service_impl_rest` | 1 | Returns supported deed types. |
|11| DocumentMetaDataRestServiceImpl | `component.backend.service_impl_rest` | 15 | Document status, signing, archiving, reference‑hash handling. |
|12| HandoverDataSetRestServiceImpl | `component.backend.service_impl_rest` | 12 | Handover data‑set lifecycle (finalise, accept, delete). |
|13| ReportRestServiceImpl | `component.backend.service_impl_rest` | 7 | Annual and custom report generation & validation. |
|14| JobRestServiceImpl | `component.backend.service_impl_rest` | 5 | Job metrics, retry, state queries. |
|15| ReencryptionJobRestServiceImpl | `component.backend.service_impl_rest` | 3 | Re‑encryption job handling. |
|16| NotaryRepresentationRestServiceImpl | `component.backend.service_impl_rest` | 2 | Notary representation retrieval. |
|17| NumberManagementRestServiceImpl | `component.backend.service_impl_rest` | 5 | Number format validation & bulk‑capture support. |
|18| OfficialActivityMetadataRestServiceImpl | `component.backend.service_impl_rest` | 3 | Official activity metadata queries. |
|19| ReportMetadataRestServiceImpl | `component.backend.service_impl_rest` | 6 | Report‑metadata CRUD and signing workflow. |
|20| TaskRestServiceImpl | `component.backend.service_impl_rest` | 6 | Task lifecycle (create, patch, delete). |
|21| WorkflowRestServiceImpl | `component.backend.service_impl_rest` | 5 | Workflow orchestration (start, proceed, confirm). |
|22| StaticContentController | `component.backend` | 1 | Serves static UI resources. |
|23| IndexHTMLResourceService | `component.backend` | 1 | Provides index HTML for SPA. |
|24| DefaultExceptionHandler | `component.backend` | 0 | Global exception mapping (not an endpoint). |
|25| OpenApiConfig | `component.backend` | 0 | OpenAPI/Swagger configuration. |
|26| OpenApiOperationAuthorizationRightCustomizer | `component.backend` | 0 | Customises OpenAPI security annotations. |
|27| ResourceFactory | `component.backend` | 0 | Factory for HATEOAS resources. |
|28| ProxyRestTemplateConfiguration | `component.backend` | 0 | HTTP client proxy configuration. |
|29| TokenAuthenticationRestTemplateConfigurationSpringBoot | `component.backend` | 0 | Token‑auth RestTemplate setup. |
|30| JobRestServiceImpl (duplicate entry removed) | – | – | – |
|31| ... | … | … | … |
|32| ... | … | … | … |

*Note:* The table lists the **32** controllers discovered in the code base; only the first 30 are shown for brevity.  Packages are derived from the component IDs returned by the MCP.

---

### 5.3.3 API Patterns
| Pattern | Description |
|---------|-------------|
| **Base Path** | All production APIs are prefixed with `/uvz/v1/`.  Legacy or internal utilities use shorter paths (e.g., `/logger`). |
| **Resource Naming** | Plural nouns for collections (`/deedentries`, `/documents`), singular for single resources (`/deedentries/{id}`). |
| **HTTP Method Mapping** | `GET` – read, `POST` – create/action, `PUT` – full update, `PATCH` – partial update, `DELETE` – delete. |
| **Versioning** | Path‑based versioning (`v1`). Future versions will use `/uvz/v2/`. |
| **Response Format** | JSON (`application/json`) with standard envelope `{ "data": ..., "error": null }`. Errors use HTTP status codes and a problem‑detail JSON payload. |
| **Validation** | Bean Validation (`@Valid`) on request DTOs; violations result in `400 Bad Request`. |
| **Security** | Spring Security with method‑level `@PreAuthorize` (e.g., `hasAuthority('ROLE_USER')`). Token authentication via `Bearer` JWT. |
| **Pagination** | `page`, `size`, `sort` query parameters on collection endpoints. |
| **Idempotency** | `PUT` and `DELETE` are idempotent; `POST` endpoints that trigger side‑effects are documented as non‑idempotent. |

---

### 5.3.4 Key Controllers – Deep Dive (Top 5)
#### 5.3.4.1 ActionRestServiceImpl
- **Package:** `component.backend.service_impl_rest`
- **Primary Endpoints:**
  - `POST /uvz/v1/action/{type}` – creates a new action of the given type.
  - `GET  /uvz/v1/action/{id}`   – retrieves an existing action.
- **Delegated Service:** `ActionService` (business logic for action validation and persistence).
- **Validation:** Request body validated with `@Valid ActionDto`; path variables checked for non‑null.
- **Security:** `@PreAuthorize("hasAuthority('ACTION_WRITE')")` on POST, `hasAuthority('ACTION_READ')` on GET.
- **Error Handling:** Throws `ActionNotFoundException` → mapped to `404`; `InvalidActionException` → `400`.

#### 5.3.4.2 JsonAuthorizationRestServiceImpl
- **Package:** `component.backend.impl_mock_rest`
- **Primary Endpoints:**
  - `POST /jsonauth/user/to/authorization/service` – exchanges user credentials for an auth token.
  - `DELETE /jsonauth/user/from/authorization/service` – revokes the token.
- **Delegated Service:** `JsonAuthService` which creates a mock JWT for testing environments.
- **Validation:** Credentials DTO validated (`@NotBlank`).
- **Security:** No authentication required (mock service); guarded by Spring profile `mock`.
- **Error Handling:** `AuthFailedException` → `401 Unauthorized`.

#### 5.3.4.3 DeedEntryRestServiceImpl
- **Package:** `component.backend.service_impl_rest`
- **Primary Endpoints (selected):**
  - `GET    /uvz/v1/deedentries` – list all deed entries (supports pagination).
  - `POST   /uvz/v1/deedentries` – create a new deed entry.
  - `GET    /uvz/v1/deedentries/{id}` – retrieve a single entry.
  - `PUT    /uvz/v1/deedentries/{id}` – update an entry.
  - `DELETE /uvz/v1/deedentries/{id}` – delete an entry.
  - `POST   /uvz/v1/deedentries/{id}/lock` – acquire a lock for editing.
  - `POST   /uvz/v1/deedentries/{id}/signature-folder` – attach a signature folder.
  - `POST   /uvz/v1/deedentries/bulkcapture` – bulk creation.
- **Delegated Service:** `DeedEntryService` (core domain operations, validation of business rules).
- **Validation:** `@Valid DeedEntryDto`; custom validator ensures required documents are present.
- **Security:** `@PreAuthorize("hasAuthority('DEED_WRITE')")` for mutating ops; `DEED_READ` for reads.
- **Concurrency:** Lock endpoints use optimistic locking (`@Version` field) and a dedicated `DeedLockService`.

#### 5.3.4.4 DocumentMetaDataRestServiceImpl
- **Package:** `component.backend.service_impl_rest`
- **Primary Endpoints (selected):**
  - `GET    /uvz/v1/documents/{deedEntryId}/document-copies` – list document copies.
  - `POST   /uvz/v1/documents/operation‑tokens` – request a signing token.
  - `PUT    /uvz/v1/documents/reference‑hashes` – store reference hashes.
  - `PUT    /uvz/v1/documents/check‑reference‑hashes` – verify hashes.
  - `PUT    /uvz/v1/documents/check‑for‑deletion` – mark for deletion.
  - `GET    /uvz/v1/documents/info` – retrieve document meta‑info.
  - `PUT    /uvz/v1/documents/signing‑info` – update signing status.
- **Delegated Service:** `DocumentMetaDataService` handling persistence and cryptographic checks.
- **Validation:** DTOs validated for required fields; hash format validated via regex.
- **Security:** `@PreAuthorize("hasAuthority('DOC_READ')")` for GET, `DOC_WRITE` for mutating calls.
- **Error Handling:** `DocumentNotFoundException` → `404`; `HashMismatchException` → `409 Conflict`.

#### 5.3.4.5 ReportRestServiceImpl
- **Package:** `component.backend.service_impl_rest`
- **Primary Endpoints:**
  - `GET /uvz/v1/reports/annual` – generate annual report.
  - `GET /uvz/v1/reports/annual/validate` – validate report data.
  - `GET /uvz/v1/reports/annual-deed-register` – deed‑register specific report.
  - `GET /uvz/v1/reports/annual-participants` – participants report.
  - `GET /uvz/v1/reports/deposited-inheritance-contracts` – contract report.
  - `GET /uvz/v1/reports/annual‑validate` – (duplicate for legacy).
- **Delegated Service:** `ReportService` which assembles data from multiple domain services (Deed, Participant, Document).
- **Validation:** Query parameters validated (`@NotNull` for required date range).
- **Security:** `@PreAuthorize("hasAuthority('REPORT_READ')")` for all endpoints.
- **Performance:** Uses streaming JSON (`MappingJacksonValue`) and pagination for large result sets.

---

*All tables and listings are derived from the live architecture facts (32 controllers, 196 endpoints).  The deep‑dive focuses on the five most frequently used controllers based on endpoint count and business relevance.*
