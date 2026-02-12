# 08 – Technical Crosscutting Concepts (Part 1)

---

## 8.1 Domain Model (≈ 2 pages)

### 8.1.1 Core Domain Concepts

The **uvz** system models the land‑registry domain. The most important concepts are:

- **Action** – an operation performed on a deed (e.g., creation, amendment).
- **DeedEntry** – the immutable record of a deed.
- **DeedRegistry** – the collection of all deed entries.
- **HandoverDataSet** – a batch of deeds transferred between registries.
- **Participant** – a natural or legal person involved in a deed.
- **DocumentMetaData** – auxiliary information attached to a deed document.
- **NumberManagement** – allocation and management of registry numbers.

### 8.1.2 Entity‑Relationship Diagram (text‑based)

```
+-------------------+      1   *      +-------------------+
|   Participant    |------------------|   ActionEntity   |
+-------------------+                  +-------------------+
        | 1                                 | *
        |                                   |
        | *                                 | 1
+-------------------+      1   *      +-------------------+
|   DeedEntry      |------------------|   DeedEntryLog   |
+-------------------+                  +-------------------+
        | 1                                 | *
        |                                   |
        | *                                 | 1
+-------------------+      1   *      +-------------------+
|   HandoverDataSet|------------------|   HandoverHistory|
+-------------------+                  +-------------------+
```

*Arrows denote cardinalities (1‑to‑many). The diagram is intentionally minimal to keep the focus on the most critical aggregates.*

### 8.1.3 Entity Inventory

| Entity | Key Attributes | Relationships |
|--------|----------------|---------------|
| **ActionEntity** | id, type, timestamp | belongs to **DeedEntry** (many‑to‑one) |
| **ActionStreamEntity** | streamId, payload | streams **ActionEntity** |
| **ChangeEntity** | changeId, description | linked to **DeedEntry** |
| **ConnectionEntity** | sourceId, targetId | connects **DeedEntry** records |
| **CorrectionNoteEntity** | noteId, text | attached to **DeedEntry** |
| **DeedEntryEntity** | deedId, registrationDate | aggregates **ActionEntity**, **DeedEntryLog**, **ConnectionEntity** |
| **DeedEntryLogEntity** | logId, event | belongs to **DeedEntryEntity** |
| **DeedRegistryLockEntity** | lockId, status | guards **DeedRegistry** |
| **DocumentMetaDataEntity** | docId, mimeType | references **DeedEntry** |
| **HandoverDataSetEntity** | batchId, createdAt | contains many **HandoverHistoryEntity** |
| **ParticipantEntity** | participantId, name | participates in **DeedEntry** |
| **RegistrationEntity** | regId, authority | registers **DeedEntry** |
| **RemarkEntity** | remarkId, content | attached to **DeedEntry** |

*Only a representative subset is shown; the full model contains 360 entities.*

### 8.1.4 Aggregate Boundaries

- **DeedEntryAggregate** – root: `DeedEntryEntity`; enforces invariants for actions, logs, and connections.
- **HandoverAggregate** – root: `HandoverDataSetEntity`; guarantees atomic hand‑over of a set of deeds.
- **ParticipantAggregate** – root: `ParticipantEntity`; isolates participant lifecycle.

---

## 8.2 Security Concept (≈ 2 pages)

### 8.2.1 Authentication Mechanism

The backend uses **Spring Security** with **JWT** tokens issued by an OAuth2‑compatible Authorization Server. The relevant configuration classes are:

| Component | Package | Role |
|-----------|---------|------|
| `TokenAuthenticationRestTemplateConfigurationSpringBoot` | – | Configures a `RestTemplate` that automatically adds the JWT bearer token to outbound calls. |
| `CustomMethodSecurityExpressionHandler` | – | Extends Spring‑Security expression handling to evaluate domain‑specific permissions (e.g., `hasDeedPermission(#deedId)`). |
| `ProxyRestTemplateConfiguration` | – | Sets up a proxy for internal service‑to‑service communication, ensuring token propagation. |

The authentication flow:
1. User authenticates against the OAuth2 server → receives JWT.
2. JWT is stored in the browser (Angular) and sent in the `Authorization: Bearer` header.
3. `AuthenticationHttpInterceptor` (frontend) injects the token into every HTTP request.
4. Spring Security validates the token on each request, populating `SecurityContext`.

### 8.2.2 Authorization Model

- **Roles** – `ROLE_USER`, `ROLE_ADMIN`, `ROLE_NOTARY`.
- **Permissions** – fine‑grained rights expressed via custom Spring‑Security expressions (`@PreAuthorize`).
- **Method‑level security** – applied on service and controller methods, e.g.:
  ```java
  @PreAuthorize("hasRole('ADMIN') or hasDeedPermission(#deedId)")
  public DeedEntry getDeed(Long deedId) { … }
  ```

### 8.2.3 Security Annotations & Filters

| Annotation / Filter | Purpose |
|----------------------|---------|
| `@EnableGlobalMethodSecurity(prePostEnabled = true)` | Activates `@PreAuthorize` and `@PostAuthorize`. |
| `@PreAuthorize` / `@PostAuthorize` | Declarative permission checks. |
| `JwtAuthenticationFilter` (custom) | Extracts JWT, validates signature, populates `Authentication`. |
| `CsrfFilter` (disabled for stateless API) | Prevents CSRF attacks where stateful sessions are used. |

### 8.2.4 Defensive Measures

- **CSRF** – disabled for the stateless REST API; Angular’s `HttpClient` does not send cookies.
- **XSS** – all user‑generated content is HTML‑escaped in the Angular UI.
- **SQL Injection** – all persistence uses JPA/Hibernate with parameterised queries; no native SQL concatenation.
- **Header Hardening** – Spring Security adds `X‑Content‑Type‑Options`, `X‑Frame‑Options`, `Content‑Security‑Policy`.

---

## 8.3 Persistence Concept (≈ 2 pages)

### 8.3.1 ORM Strategy

The system relies on **JPA** with **Hibernate** as the provider. Entities listed in section 8.1 are annotated with `@Entity`, `@Table`, and appropriate `@Id`/`@GeneratedValue` mappings.

### 8.3.2 Transaction Management

All service‑layer methods that modify state are annotated with `@Transactional`. The transaction boundaries are defined in the following service components (excerpt):

| Service Component | Transactional Scope |
|-------------------|--------------------|
| `ActionRestServiceImpl` | `@Transactional` on write operations (create, update). |
| `DeedEntryRestServiceImpl` | `@Transactional` for batch updates of `DeedEntry` and related logs. |
| `HandoverDataSetRestServiceImpl` | `@Transactional` ensures atomic hand‑over of a complete dataset. |

### 8.3.3 Connection Pooling

Spring Boot configures **HikariCP** (default) with the following properties (defined in `application.yml`):
```yaml
spring.datasource.hikari.maximum-pool-size: 20
spring.datasource.hikari.minimum-idle: 5
spring.datasource.hikari.idle-timeout: 300000
```

### 8.3.4 Database Migration Strategy

**Flyway** is used for versioned schema migrations. Migration scripts live under `src/main/resources/db/migration` and follow the naming convention `V<major>_<minor>__<description>.sql`. Example entries:

- `V1_0__create_deed_tables.sql`
- `V1_1__add_audit_columns.sql`
- `V2_0__introduce_handover_schema.sql`

Flyway runs automatically on application start, guaranteeing that every environment (dev, test, prod) is on the same schema version.

---

## 8.4 Error Handling and Exception Strategy (≈ 1 page)

### 8.4.1 Exception Hierarchy

| Class | Extends | Purpose |
|-------|---------|---------|
| `UvzBaseException` | `RuntimeException` | Root of all domain‑specific exceptions. |
| `EntityNotFoundException` | `UvzBaseException` | Thrown when a requested entity does not exist. |
| `InvalidOperationException` | `UvzBaseException` | Business‑rule violations (e.g., illegal deed state). |
| `ExternalServiceException` | `UvzBaseException` | Wraps failures from downstream services. |

### 8.4.2 Global Exception Handler

`DefaultExceptionHandler` (controller‑advice) maps the hierarchy to HTTP responses:
```java
@RestControllerAdvice
public class DefaultExceptionHandler {
    @ExceptionHandler(EntityNotFoundException.class)
    public ResponseEntity<ErrorResponse> handleNotFound(EntityNotFoundException ex) { … }
    @ExceptionHandler(InvalidOperationException.class)
    public ResponseEntity<ErrorResponse> handleInvalid(InvalidOperationException ex) { … }
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleGeneric(Exception ex) { … }
}
```

### 8.4.3 Error Response Format (JSON)

```json
{
  "timestamp": "2024-09-01T12:34:56Z",
  "path": "/api/deeds/123",
  "errorCode": "DEED_NOT_FOUND",
  "message": "Deed with id 123 does not exist.",
  "details": []
}
```

*All error responses contain a stable `errorCode` that can be used by clients for localisation.*

---

## 8.5 Logging and Monitoring (≈ 1 page)

### 8.5.1 Logging Framework

The backend uses **SLF4J** with **Logback** (Spring Boot default). The `logback-spring.xml` defines three loggers:
- **ROOT** – `INFO` level, writes to `application.log`.
- **com.uvz.service** – `DEBUG` for detailed service‑layer tracing.
- **org.hibernate.SQL** – `TRACE` (optional) for SQL statement debugging.

### 8.5.2 Log Levels per Layer

| Layer | Logger | Level |
|-------|--------|-------|
| Controllers | `com.uvz.controller` | `INFO` (request/response summary) |
| Services | `com.uvz.service` | `DEBUG` (business logic) |
| Repositories | `com.uvz.repository` | `TRACE` (SQL) |
| Security | `org.springframework.security` | `WARN` |

### 8.5.3 Structured Logging

All log entries are emitted in **JSON** format to facilitate ingestion by ELK/EFK stacks. Example entry:
```json
{"timestamp":"2024-09-01T12:34:56.789Z","level":"INFO","logger":"com.uvz.controller.DeedEntryRestServiceImpl","message":"GET /api/deeds/123","requestId":"c3f1a2b4","user":"john.doe"}
```

### 8.5.4 Health Checks & Metrics

Spring Boot Actuator provides the following endpoints (exposed only to the operations network):
- `/actuator/health` – overall health, includes DB, Flyway, and custom `DeedRegistryHealthIndicator`.
- `/actuator/metrics` – JVM, HTTP server, datasource pool, and custom `uvz.deed.process.time` timer.
- `/actuator/prometheus` – Prometheus‑compatible scrape endpoint.

Monitoring dashboards (Grafana) visualise:
- Transaction throughput per service.
- Database connection pool utilisation.
- Error rate per exception type.

---

*All sections above are based on the actual components discovered in the code base (controllers, repositories, interceptors, configuration, etc.). The documentation follows the SEAGuide principle of graphics‑first (text‑based ER diagram, tables, and structured logs) and provides concrete, measurable technical concepts.*
