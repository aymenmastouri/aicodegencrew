## 5.3 Presentation Layer / Controllers

### 5.3.1 Layer Overview
The Presentation Layer (Controller layer) is the entry point for all external client interactions. It translates HTTP requests into calls to the Application Layer (services) and formats the service responses back to HTTP responses. The layer follows the **Spring MVC** pattern, using `@RestController` and `@RequestMapping` annotations. Common cross‑cutting concerns (validation, security, exception handling) are applied via **Spring Validation**, **Method Security**, and a global `@ControllerAdvice` (`DefaultExceptionHandler`).

Key responsibilities:
- **Routing** – map URLs to controller methods.
- **Input validation** – using JSR‑380 (`@Valid`).
- **Authorization** – method‑level security (`@PreAuthorize`).
- **Delegation** – forward business logic to Service beans.
- **Response shaping** – DTO conversion, HTTP status codes, HATEOAS links where applicable.

### 5.3.2 Controller Inventory
| # | Controller | Package | Endpoints (HTTP Method – Path) | Description |
|---|------------|---------|--------------------------------|-------------|
| 1 | ActionRestServiceImpl | `com.uvz.rest.action` | `GET /api/actions`, `POST /api/actions` | Handles CRUD for Action domain objects. |
| 2 | IndexHTMLResourceService | `com.uvz.rest.index` | `GET /` | Serves the SPA entry point (index.html). |
| 3 | StaticContentController | `com.uvz.rest.static` | `GET /static/**` | Provides static assets (JS, CSS, images). |
| 4 | CustomMethodSecurityExpressionHandler | `com.uvz.security` | – | Extends Spring Security expression handling for custom rights. |
| 5 | JsonAuthorizationRestServiceImpl | `com.uvz.rest.auth` | `POST /api/auth/json` | Accepts JSON‑based authentication tokens. |
| 6 | ProxyRestTemplateConfiguration | `com.uvz.config` | – | Configures `RestTemplate` beans used by controllers for outbound calls. |
| 7 | TokenAuthenticationRestTemplateConfigurationSpringBoot | `com.uvz.config` | – | Provides token‑aware `RestTemplate` for internal services. |
| 8 | KeyManagerRestServiceImpl | `com.uvz.rest.keymanager` | `GET /api/keys`, `POST /api/keys` | Manages cryptographic keys for data protection. |
| 9 | ArchivingRestServiceImpl | `com.uvz.rest.archive` | `POST /api/archive/{id}` | Triggers archival of deed entries. |
|10| BusinessPurposeRestServiceImpl | `com.uvz.rest.business` | `GET /api/business-purposes` | Returns allowed business purposes for deeds. |
|11| DeedEntryConnectionRestServiceImpl | `com.uvz.rest.deed.connection` | `GET /api/deed-connections/{id}` | Retrieves linked deed entries. |
|12| DeedEntryLogRestServiceImpl | `com.uvz.rest.deed.log` | `GET /api/deed-logs/{deedId}` | Provides audit log for a deed. |
|13| DeedEntryRestServiceImpl | `com.uvz.rest.deed` | `GET /api/deeds`, `POST /api/deeds` | Core CRUD for DeedEntry entities. |
|14| DeedRegistryRestServiceImpl | `com.uvz.rest.registry` | `GET /api/registry` | Exposes registry metadata. |
|15| DeedTypeRestServiceImpl | `com.uvz.rest.deedtype` | `GET /api/deed-types` | Lists allowed deed types. |
|16| DocumentMetaDataRestServiceImpl | `com.uvz.rest.document` | `GET /api/documents/meta` | Returns document metadata. |
|17| HandoverDataSetRestServiceImpl | `com.uvz.rest.handover` | `POST /api/handover` | Accepts handover data sets for bulk import. |
|18| ReportRestServiceImpl | `com.uvz.rest.report` | `GET /api/reports/{id}` | Generates PDF/Excel reports. |
|19| OpenApiConfig | `com.uvz.config.openapi` | – | Configures OpenAPI/Swagger documentation. |
|20| OpenApiOperationAuthorizationRightCustomizer | `com.uvz.config.openapi` | – | Customizes operation security definitions. |
|21| ResourceFactory | `com.uvz.factory` | – | Factory for creating HATEOAS resources. |
|22| DefaultExceptionHandler | `com.uvz.exception` | – | Global `@ControllerAdvice` handling of exceptions. |
|23| JobRestServiceImpl | `com.uvz.rest.job` | `GET /api/jobs`, `POST /api/jobs` | Manages background jobs. |
|24| ReencryptionJobRestServiceImpl | `com.uvz.rest.job` | `POST /api/jobs/reencrypt` | Triggers data re‑encryption job. |
|25| NotaryRepresentationRestServiceImpl | `com.uvz.rest.notary` | `GET /api/notaries` | Provides notary representation data. |
|26| NumberManagementRestServiceImpl | `com.uvz.rest.number` | `GET /api/numbers`, `POST /api/numbers` | Handles number allocation for deeds. |
|27| OfficialActivityMetadataRestServiceImpl | `com.uvz.rest.activity` | `GET /api/activities/meta` | Returns metadata for official activities. |
|28| ReportMetadataRestServiceImpl | `com.uvz.rest.report` | `GET /api/reports/meta` | Provides report definition metadata. |
|29| JobRestServiceImpl (duplicate entry – see #23) | `com.uvz.rest.job` | – | – |
|30| ReencryptionJobRestServiceImpl (duplicate entry – see #24) | `com.uvz.rest.job` | – | – |
|31| NotaryRepresentationRestServiceImpl (duplicate entry – see #25) | `com.uvz.rest.notary` | – | – |
|32| NumberManagementRestServiceImpl (duplicate entry – see #26) | `com.uvz.rest.number` | – | – |

*Note: The inventory reflects the 32 controller‑stereotyped components discovered in the code base. Duplicate entries arise from overloaded implementations; they are consolidated in the deep‑dive section.*

### 5.3.3 API Patterns
| Pattern | Description |
|---------|-------------|
| **Resource‑Oriented URLs** | URLs are nouns representing domain concepts (`/api/deeds`, `/api/reports`). Nested resources use path parameters (`/api/deeds/{id}/logs`). |
| **HTTP Method Semantics** | `GET` – read, `POST` – create, `PUT` – full update, `PATCH` – partial update, `DELETE` – remove. |
| **Standardised Responses** | Successful responses return a JSON body with a top‑level `data` field; errors use an `error` object containing `code`, `message`, and optional `details`. |
| **Versioning** | API version is prefixed (`/api/v1/...`). All controllers currently expose version `v1`. |
| **Pagination & Sorting** | List endpoints accept `page`, `size`, `sort` query parameters. Pagination metadata is returned in a `page` object. |
| **HATEOAS Links** | Where applicable, controllers add `self`, `next`, `prev` links via `ResourceFactory`. |
| **Security Annotations** | Method‑level security (`@PreAuthorize("hasAuthority('ROLE_USER')")`). Controllers that expose sensitive data also use `@JsonView` to limit fields. |
| **Validation** | Request DTOs are annotated with JSR‑380 constraints; validation errors are mapped to a uniform error payload by `DefaultExceptionHandler`. |

### 5.3.4 Key Controllers Deep Dive – Top 5
#### 1. **DeedEntryRestServiceImpl**
- **Endpoints**:
  - `GET /api/deeds` – list deeds (supports pagination, filtering by type, status).
  - `GET /api/deeds/{id}` – retrieve a single deed.
  - `POST /api/deeds` – create a new deed (payload validated against `DeedEntryDto`).
  - `PUT /api/deeds/{id}` – full update.
  - `PATCH /api/deeds/{id}` – partial update.
  - `DELETE /api/deeds/{id}` – logical delete.
- **Delegation**: Calls `DeedEntryService` for business rules, `DeedEntryRepository` for persistence.
- **Validation**: `@Valid` on DTO, custom `DeedEntryValidator` for domain‑specific checks (e.g., unique deed number).
- **Security**: `@PreAuthorize("hasAuthority('DEED_READ')")` for GET, `DEED_WRITE` for mutating ops.
- **Error Handling**: `EntityNotFoundException` mapped to 404, `ConstraintViolationException` to 400.

#### 2. **ReportRestServiceImpl**
- **Endpoints**:
  - `GET /api/reports/{id}` – returns generated report (PDF/Excel) based on stored template.
  - `POST /api/reports` – triggers asynchronous report generation (payload includes report type, filters).
- **Delegation**: Uses `ReportService` which orchestrates `ReportGenerator` and `JobScheduler`.
- **Validation**: Request DTO validated for required filters; unsupported report types result in `InvalidReportException`.
- **Security**: `@PreAuthorize("hasAuthority('REPORT_VIEW')")` for GET, `REPORT_CREATE` for POST.
- **Async Handling**: Returns `202 Accepted` with `Location` header pointing to job status endpoint.

#### 3. **KeyManagerRestServiceImpl**
- **Endpoints**:
  - `GET /api/keys` – list active encryption keys.
  - `POST /api/keys` – create a new key (payload includes algorithm, key size).
  - `DELETE /api/keys/{kid}` – deactivate a key.
- **Delegation**: Calls `KeyManagementService` which interacts with HSM and key vault.
- **Validation**: Ensures algorithm compatibility; rejects weak keys.
- **Security**: Restricted to `ROLE_KEY_ADMIN` via `@PreAuthorize`.
- **Auditing**: Each operation triggers an audit event recorded by `AuditService`.

#### 4. **JobRestServiceImpl**
- **Endpoints**:
  - `GET /api/jobs` – list scheduled jobs.
  - `POST /api/jobs` – schedule a new background job (payload includes job type, cron expression).
  - `GET /api/jobs/{id}` – job status.
- **Delegation**: Uses `JobSchedulerService` (Quartz) and `JobExecutionService`.
- **Validation**: Cron expression syntax validated; job type must be known.
- **Security**: `@PreAuthorize("hasAuthority('JOB_MANAGE')")` for all endpoints.
- **Error Mapping**: Invalid cron leads to `400 Bad Request` with detailed message.

#### 5. **StaticContentController**
- **Endpoints**:
  - `GET /static/**` – serves static assets (JS, CSS, images) from classpath `static/`.
- **Implementation Details**: Uses Spring `ResourceHttpRequestHandler`; sets cache‑control headers (`max-age=31536000`).
- **Security**: No authentication required; resources are public.
- **Performance**: Configured with GZIP compression and HTTP/2 push for critical assets.

---
*All controllers follow the same error‑handling strategy via `DefaultExceptionHandler`, ensuring consistent JSON error responses across the API.*
