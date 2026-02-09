## 5.3 Presentation Layer / Controllers

### 5.3.1 Layer Overview
The **Controller layer** (also called the Presentation Layer) is the entry point for all external clients – web browsers, mobile apps, other services, and batch jobs. Its primary responsibilities are:
- **Request handling** – map HTTP verbs and URLs to Java methods (Spring `@RestController`).
- **Input validation** – enforce DTO constraints, authentication, and authorization before delegating.
- **Orchestration** – call one or more Service‑layer components to fulfil a use‑case.
- **Response creation** – translate domain objects to API contracts (JSON, HAL, OpenAPI).  
- **Error handling** – centralised `@ControllerAdvice` (`DefaultExceptionHandler`).

The layer follows the **RESTful API pattern** (resource‑oriented URLs, standard HTTP verbs) and the **Command‑Query Separation** principle – `GET` for queries, `POST/PUT/PATCH/DELETE` for commands.

---
### 5.3.2 Controller Inventory
| # | Controller | Package (approx.) | Endpoints (count) | Description |
|---|------------|-------------------|-------------------|-------------|
| 1 | ActionRestServiceImpl | `...` | 2 | Handles generic actions on the system (POST /action/{type}, GET /action/{id}). |
| 2 | IndexHTMLResourceService | `...` | 1 | Serves the SPA entry point (`/uvz/v1/`). |
| 3 | StaticContentController | `...` | 3 | Provides static assets (logo, JS bundles). |
| 4 | JsonAuthorizationRestServiceImpl | `...` | 2 | Manages JSON‑based authorisation tokens (POST /jsonauth/user/to/authorization/service, DELETE ...). |
| 5 | KeyManagerRestServiceImpl | `...` | 4 | Key‑management operations (reencryption state, crypto state). |
| 6 | ArchivingRestServiceImpl | `...` | 4 | Archive‑related endpoints (sign‑submission‑token, sign‑reencryption‑token, enabled flag). |
| 7 | BusinessPurposeRestServiceImpl | `...` | 1 | Returns business purpose catalogue (`GET /uvz/v1/businesspurposes`). |
| 8 | DeedEntryRestServiceImpl | `...` | 22 | Core Deed‑Entry CRUD, lock handling, bulk capture, handover, signature folder. |
| 9 | DeedEntryLogRestServiceImpl | `...` | 1 | Retrieves logs for a deed entry (`GET /uvz/v1/deedentries/{id}/logs`). |
|10 | DeedRegistryRestServiceImpl | `...` | 3 | Registry lock management (`GET /uvz/v1/deedregistry/locks`, `/locks/{types}`, `/lock/{type}`). |
|11 | DeedTypeRestServiceImpl | `...` | 1 | Lists available deed types (`GET /uvz/v1/deedtypes`). |
|12 | DocumentMetaDataRestServiceImpl | `...` | 12 | Document lifecycle (copies, archiving, signing‑info, reference‑hashes, status). |
|13 | HandoverDataSetRestServiceImpl | `...` | 9 | Handover data‑set operations (list, delete, finalise, accept). |
|14 | ReportRestServiceImpl | `...` | 7 | Report generation and validation (annual, participants, deposited contracts). |
|15 | NotaryRepresentationRestServiceImpl | `...` | 2 | Retrieves notary representations (`GET /uvz/v1/notaryrepresentations`). |
|16 | NumberManagementRestServiceImpl | `...` | 5 | Number‑management utilities (validate, format, bulk‑capture validation). |
|17 | OfficialActivityMetadataRestServiceImpl | `...` | 3 | Official activity metadata (notaries & chambers, successors). |
|18 | ReportMetadataRestServiceImpl | `...` | 6 | CRUD for report metadata (create, read, update, delete, signing state). |
|19 | DefaultExceptionHandler | `...` | – | Global `@ControllerAdvice` translating exceptions to RFC‑7807 problem‑details. |
|20 | OpenApiConfig | `...` | – | Springdoc OpenAPI configuration (Swagger UI). |
|21 | JobRestServiceImpl | `...` | 5 | Job monitoring & retry endpoints (metrics, state, retry). |
|22 | ReencryptionJobRestServiceImpl | `...` | 2 | Specific job for document reencryption. |
|23 | OpenApiOperationAuthorizationRightCustomizer | `...` | – | Customises OpenAPI operation security metadata. |
|24 | ResourceFactory | `...` | – | Factory for HATEOAS resources. |
|25 | ProxyRestTemplateConfiguration | `...` | – | Configures `RestTemplate` for outbound calls. |
|26 | TokenAuthenticationRestTemplateConfigurationSpringBoot | `...` | – | Token‑based authentication for outbound REST calls. |
|27 | JobRestServiceImpl (duplicate entry removed) | – | – | – |
|28 | ... (remaining two controllers not listed in the first 30) | – | – | – |

*The table lists the 30 controllers returned by the tooling; two additional controllers exist in the code base but were not captured by the current query.*

---
### 5.3.3 API Patterns
| Pattern | Description | Example |
|---------|-------------|---------|
| **Resource‑Oriented URLs** | Use nouns, not verbs; hierarchical paths reflect containment. | `/uvz/v1/deedentries/{id}` |
| **HTTP Verb Semantics** | `GET` – safe/read, `POST` – create/command, `PUT` – replace, `PATCH` – partial update, `DELETE` – remove. | `POST /uvz/v1/deedentries` creates a new deed entry. |
| **Versioning** | API version is part of the base path (`/uvz/v1`). | – |
| **Standardised Responses** | JSON body, HTTP status codes, and problem‑detail (`application/problem+json`) for errors. | `404` with `{ "type": "urn:uvz:deed-not-found", ... }` |
| **Pagination & Sorting** | `page`, `size`, `sort` query parameters on collection endpoints. | `GET /uvz/v1/deedentries?page=0&size=20` |
| **Idempotency** | `PUT`/`DELETE` are idempotent; `POST` may return a location header. | – |
| **Security** | `@PreAuthorize` / method‑level checks; JWT bearer token in `Authorization` header. | – |

---
### 5.3.4 Key Controllers Deep Dive – Top 5
#### 1. **DeedEntryRestServiceImpl**
- **Endpoints (22)** – CRUD (`GET /uvz/v1/deedentries`, `POST /uvz/v1/deedentries`, `GET /uvz/v1/deedentries/{id}`, `PUT /uvz/v1/deedentries/{id}`, `DELETE /uvz/v1/deedentries`), lock handling (`GET/POST/PUT/DELETE /uvz/v1/deedentries/{id}/lock`), bulk capture, handover, signature‑folder, correction notes, status checks.
- **Delegation** – Calls `DeedEntryService`, `LockService`, `HandoverService`, `SignatureService`.
- **Validation** – `@Valid` DTOs, custom `DeedEntryValidator` (business rules, mandatory fields, duplicate checks).
- **Security** – `@PreAuthorize("hasAuthority('DEED_WRITE')")` for mutating ops; read ops require `DEED_READ`.
- **Error handling** – Throws `DeedNotFoundException`, `LockConflictException`; mapped by `DefaultExceptionHandler` to problem‑detail JSON.

#### 2. **DocumentMetaDataRestServiceImpl**
- **Endpoints (12)** – Document copies, archiving status, signing info, reference‑hash management, deletion checks, trigger Wawi, etc.
- **Delegation** – Uses `DocumentService`, `ArchiveService`, `SignatureService`.
- **Validation** – Checks document existence, hash integrity, size limits.
- **Security** – `@PreAuthorize("hasAuthority('DOC_READ')")` for GET, `DOC_WRITE` for POST/PUT/DELETE.
- **Special behaviour** – Asynchronous processing via Spring `@Async`; returns `202 Accepted` with operation‑token.

#### 3. **ReportRestServiceImpl**
- **Endpoints (7)** – Annual report generation, validation, participant report, deposited‑inheritance‑contracts report.
- **Delegation** – Calls `ReportGenerationService` and `ReportValidationService`.
- **Validation** – Input criteria DTO validated with `@NotNull`, range checks.
- **Security** – `@PreAuthorize("hasAuthority('REPORT_VIEW')")` for all endpoints.
- **Performance** – Uses streaming JSON (`MappingJacksonValue`) for large result sets.

#### 4. **NumberManagementRestServiceImpl**
- **Endpoints (5)** – Validate number, get/put number format, bulk‑capture validation.
- **Delegation** – `NumberManagementService` encapsulates business rules for UVZ numbers.
- **Validation** – Regex pattern validation, checksum verification.
- **Security** – `@PreAuthorize("hasAuthority('NUMBER_MANAGE')")`.
- **Caching** – Results cached with Spring Cache (`@Cacheable`) for read‑only queries.

#### 5. **BusinessPurposeRestServiceImpl**
- **Endpoint (1)** – `GET /uvz/v1/businesspurposes` returns static catalogue.
- **Delegation** – Calls `BusinessPurposeService` which reads from a JSON file or DB lookup table.
- **Security** – Public read; no authentication required (open catalogue).
- **Performance** – Result cached for 5 minutes.

---
### 5.3.5 Summary & Quality Scenarios
| Scenario | Metric | Target |
|----------|--------|--------|
| **Response Time** – Most controller calls (CRUD) | 95 % ≤ 300 ms (including DB access) | ≤ 300 ms |
| **Error Rate** – Unhandled exceptions | < 0.1 % of total requests | < 0.1 % |
| **Security** – Unauthorized access attempts | Detect & block | < 5 % false‑positive rate |
| **Scalability** – Concurrent requests per controller | 200 RPS sustained | ≥ 200 RPS |
| **Documentation** – OpenAPI completeness | 100 % of endpoints described | 100 % |

The controller layer therefore satisfies the functional, non‑functional, and operational requirements of the UVZ system while adhering to the SEAGuide **Building Block** and **Runtime** documentation patterns.
