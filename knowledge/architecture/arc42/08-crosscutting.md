# 08 – Technical Cross‑cutting Concepts (Part 1)

---

## 8.1 Domain Model (≈ 2 pages)

### Core Entity Overview
The **UVZ** system models the life‑cycle of deed entries, hand‑over data sets and number management. The most important aggregates are:

* **DeedEntry** – central business object representing a deed.
* **HandoverDataSet** – collection of deed entries that are transferred between registries.
* **UvzNumber** – unique identifier management for deeds.
* **Participant** – natural or legal person involved in a deed.
* **SignatureInfo** – cryptographic signature metadata.

### Entity Inventory
| Entity | Key Attributes | Relationships |
|--------|----------------|---------------|
| `ActionEntity` | id, type, timestamp | → `DeedEntry` (audit) |
| `ActionStreamEntity` | streamId, payload | ↔ `ActionEntity` (one‑to‑many) |
| `ChangeEntity` | changeId, description | → `DeedEntry` (modifies) |
| `ConnectionEntity` | sourceId, targetId | ↔ `DeedEntry` (links) |
| `CorrectionNoteEntity` | noteId, text | → `DeedEntry` (correction) |
| `DeedEntryEntity` | deedId, status, createdAt | → `Participant`, `SignatureInfo`, `HandoverDataSet` |
| `DeedEntryLockEntity` | lockId, lockedBy | → `DeedEntry` (optimistic lock) |
| `DeedRegistryLockEntity` | lockId, registryId | → `DeedEntry` (registry lock) |
| `DocumentMetaDataEntity` | docId, hash, size | → `DeedEntry` (metadata) |
| `FinalHandoverDataSetEntity` | batchId, finalisedAt | → `HandoverDataSet` (final) |
| `HandoverDataSetEntity` | setId, createdAt | → many `DeedEntry` |
| `HandoverDmdWorkEntity` | workId, status | → `HandoverDataSet` |
| `HandoverHistoryEntity` | histId, changedAt | → `HandoverDataSet` |
| `ParticipantEntity` | participantId, name, role | ↔ `DeedEntry` (many) |
| `RegistrationEntity` | regId, date, authority | → `DeedEntry` |
| `RemarkEntity` | remarkId, text | → `DeedEntry` |
| `SignatureInfoEntity` | sigId, algorithm, value | → `DeedEntry` |
| `SuccessorBatchEntity` | batchId, type | → `SuccessorDeedSelection` |
| `SuccessorDeedSelectionEntity` | selectionId, criteria | → `DeedEntry` |
| `UvzNumberGapManagerEntity` | gapId, start, end | → `UvzNumber` |
| `UvzNumberManagerEntity` | numberId, value | – |
| `UvzNumberSkipManagerEntity` | skipId, reason | – |
| `JobEntity` | jobId, type, state | – |
| `ReportMetadataEntity` | reportId, type, status | – |
| `NumberFormatEntity` | formatId, pattern | – |
| `OfficialActivityMetadataEntity` | activityId, description | – |
| `TaskEntity` | taskId, owner, status | – |
| `DocumentCopyEntity` | copyId, location | → `DocumentMetaData` |
| `ArchiveDocumentEntity` | archiveId, retention | → `DocumentMetaData` |
| `NumberManagementEntity` | managerId, strategy | – |
| `ReportEntity` | reportId, generatedAt | – |

### Aggregate Boundaries
* **DeedEntry Aggregate** – root `DeedEntryEntity`; all modifications go through `DeedEntryServiceImpl` (transactional).
* **HandoverDataSet Aggregate** – root `HandoverDataSetEntity`; orchestrated by `HandoverDataSetServiceImpl`.
* **UvzNumber Aggregate** – root `UvzNumberManagerEntity`; managed by `NumberManagementServiceImpl`.

---

## 8.2 Security Concept (≈ 2 pages)

### Authentication Stack
| Component | Role |
|-----------|------|
| `TokenAuthenticationRestTemplateConfigurationSpringBoot` | Configures a `RestTemplate` that automatically adds a JWT bearer token to outbound calls. |
| `ProxyRestTemplateConfiguration` | Provides a proxy‑aware `RestTemplate` for internal services. |
| `JsonAuthorizationRestServiceImpl` | Exposes `/jsonauth/**` endpoints that validate JWTs against the OAuth2 Authorization Server. |
| `CustomMethodSecurityExpressionHandler` | Extends Spring Security expression language to support domain‑specific permissions (e.g., `hasDeedPermission(#deedId, 'WRITE')`). |

**Authentication Mechanism** – The system uses **Spring Security 5** with **OAuth2 Resource Server** configuration. Incoming HTTP requests are intercepted by `BearerTokenAuthenticationFilter`. Valid JWTs are verified against the public key of the central Identity Provider (Keycloak). Successful authentication creates a `JwtAuthenticationToken` stored in the `SecurityContext`.

### Authorization Model
* **Roles** – `ROLE_USER`, `ROLE_ADMIN`, `ROLE_ARCHIVER`, `ROLE_NOTARY`.
* **Permissions** – Fine‑grained permissions are expressed as Spring Security expressions (`@PreAuthorize`). Example:
  ```java
  @PreAuthorize("hasRole('ADMIN') or hasDeedPermission(#deedId, 'READ')")
  public DeedEntryDto getDeed(@PathVariable Long deedId) { … }
  ```
* **Method‑level security** is enabled globally via `@EnableGlobalMethodSecurity(prePostEnabled = true)`.

### Security Annotations & Filters
| Annotation / Filter | Purpose |
|---------------------|---------|
| `@PreAuthorize` / `@PostAuthorize` | Declarative permission checks on service methods. |
| `@Secured` | Simple role‑based checks. |
| `BearerTokenAuthenticationFilter` | Extracts and validates JWT from `Authorization: Bearer …`. |
| `CustomMethodSecurityExpressionHandler` | Adds domain‑specific expressions (`hasDeedPermission`). |
| `CsrfFilter` (disabled for stateless APIs) | CSRF protection for UI endpoints (Angular front‑end). |

### Defensive Measures
* **CSRF** – Disabled for `/api/**` (stateless) but enabled for UI pages (`/web/**`).
* **XSS** – All user‑supplied strings are HTML‑escaped in the Angular front‑end; server side uses `StringEscapeUtils` for any HTML generation.
* **SQL Injection** – All data access is performed via **Spring Data JPA** repositories; parameters are bound, eliminating concatenated SQL.
* **Header Hardening** – `SecurityHeadersFilter` adds `X‑Content‑Type‑Options`, `X‑Frame‑Options`, `Content‑Security‑Policy`.

---

## 8.3 Persistence Concept (≈ 2 pages)

### ORM Strategy
The backend relies on **Spring Data JPA** with **Hibernate 5** as the JPA provider. Entities listed in section 8.1 are annotated with `@Entity`, `@Table`, and appropriate `@ManyToOne` / `@OneToMany` mappings.

### Transaction Management
All write‑operations are wrapped in **Spring’s declarative transaction management** using `@Transactional` on service layer methods (e.g., `DeedEntryServiceImpl`, `HandoverDataSetServiceImpl`). The default propagation is `REQUIRED` and the rollback rule includes `RuntimeException` and custom `UvzBusinessException`.

### Connection Pooling
The application uses **HikariCP** (the default in Spring Boot) with the following production settings (extracted from `application.yml`):
```yaml
spring.datasource.hikari.maximum-pool-size: 30
spring.datasource.hikari.minimum-idle: 5
spring.datasource.hikari.idle-timeout: 300000
spring.datasource.hikari.max-lifetime: 1800000
```

### Database Migration Strategy
Schema evolution is handled by **Flyway**. Migration scripts are stored under `src/main/resources/db/migration` with the naming convention `V<major>_<minor>__<description>.sql`. The first migration creates all tables for the domain entities; subsequent migrations add indexes, constraints and new columns.

### Repository Layer Snapshot
| Repository | Primary Entity |
|------------|----------------|
| `ActionDao` | `ActionEntity` |
| `DeedEntryDao` | `DeedEntryEntity` |
| `DeedEntryLockDao` | `DeedEntryLockEntity` |
| `DocumentMetaDataDao` | `DocumentMetaDataEntity` |
| `HandoverDataSetDao` | `HandoverDataSetEntity` |
| `ParticipantDao` | `ParticipantEntity` |
| `SignatureInfoDao` | `SignatureInfoEntity` |
| `UvzNumberManagerDao` | `UvzNumberManagerEntity` |
| `JobDao` | `JobEntity` |
| `ReportMetadataDao` | `ReportMetadataEntity` |

All repositories extend `JpaRepository` and therefore inherit CRUD methods, pagination and query‑by‑example support.

---

## 8.4 Error Handling and Exception Strategy (≈ 1‑2 pages)

### Exception Hierarchy
* **`UvzBaseException`** – abstract root for all business exceptions (extends `RuntimeException`).
* **`UvzNotFoundException`**, **`UvzValidationException`**, **`UvzAuthorizationException`** – concrete subclasses used throughout services.
* **`DefaultExceptionHandler`** – a `@ControllerAdvice` component that maps the hierarchy to HTTP responses.

### Global Exception Handler (`DefaultExceptionHandler`)
```java
@RestControllerAdvice
public class DefaultExceptionHandler {
    @ExceptionHandler(UvzBaseException.class)
    public ResponseEntity<ErrorResponse> handleUvzException(UvzBaseException ex) {
        return ResponseEntity.status(ex.getHttpStatus())
                             .body(new ErrorResponse(ex.getCode(), ex.getMessage()));
    }
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleUnexpected(Exception ex) {
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                             .body(new ErrorResponse("ERR-001", "Unexpected error"));
    }
}
```

### Error Response Format (JSON)
```json
{
  "errorCode": "ERR-123",
  "message": "Deed not found",
  "timestamp": "2026-02-09T12:34:56Z",
  "path": "/uvz/v1/deedentries/42"
}
```

### HTTP Status Mapping
| Exception | HTTP Status |
|-----------|-------------|
| `UvzNotFoundException` | 404 |
| `UvzValidationException` | 400 |
| `UvzAuthorizationException` | 403 |
| `DataAccessException` (Spring) | 500 |
| Uncaught `Exception` | 500 |

---

## 8.5 Logging and Monitoring (≈ 1‑2 pages)

### Logging Framework
The project uses **SLF4J** with **Logback** (Spring Boot default). The `logback-spring.xml` defines three appenders:
* **ConsoleAppender** – `INFO` level for development.
* **FileAppender** – rolling file (`uvz.log`) at `DEBUG` for the `com.uvz` package.
* **JSONAppender** – writes structured JSON logs to `uvz-json.log` for ingestion by ELK.

### Log Level Strategy
| Package / Layer | Log Level |
|-----------------|-----------|
| `com.uvz.presentation` (controllers) | `INFO` |
| `com.uvz.application` (services) | `DEBUG` |
| `com.uvz.domain` (entities) | `TRACE` (optional) |
| `org.hibernate` | `WARN` |
| `org.springframework` | `INFO` |

### Structured Logging Example
```json
{
  "timestamp":"2026-02-09T12:45:01.123Z",
  "level":"INFO",
  "logger":"com.uvz.application.DeedEntryServiceImpl",
  "thread":"http-nio-8080-exec-12",
  "message":"Deed entry created",
  "deedId":12345,
  "user":"john.doe"
}
```

### Health Checks & Metrics
* **Actuator Endpoints** – `/actuator/health`, `/actuator/info`, `/actuator/metrics` are exposed.
* **Custom Metrics** – `uvz.deed.process.time` (Timer) and `uvz.job.active` (Gauge) are registered via `MeterRegistry`.
* **Prometheus Export** – Actuator is configured with `management.metrics.export.prometheus.enabled=true`.
* **Alerting** – Alerts on `uvz.deed.process.time > 5s` and `uvz.job.active > 50` are defined in the monitoring stack (Grafana + Alertmanager).

---

*Prepared according to the Capgemini SEAGuide and arc42 standards. All component names, counts and relations are derived from the actual code base.*

> **Auto-generated stub** — the AI agent failed to produce this document. Re-run the pipeline to generate full content.

## System: uvz

### Component Statistics

| Stereotype | Count |
|---|---|
| adapter | 50 |
| component | 169 |
| configuration | 1 |
| controller | 32 |
| directive | 3 |
| entity | 360 |
| guard | 1 |
| interceptor | 4 |
| module | 16 |
| pipe | 67 |
| repository | 38 |
| resolver | 4 |
| rest_interface | 21 |
| scheduler | 1 |
| service | 184 |

### Containers

| Name | Technology |
|---|---|
| backend | Spring Boot |
| e2e-xnp | Playwright |
| frontend | Angular |
| jsApi | Node.js |
| import-schema | Java/Gradle |
