# 08 – Technical Crosscutting Concepts (Part 1)

---

## 8.1 Domain Model (≈ 2 pages)

### 8.1.1 Core Domain Concepts

The **UVZ** system models the lifecycle of deeds, handovers and number management. The most important bounded contexts are:

| Bounded Context | Core Aggregate Root | Key Entities |
|-----------------|--------------------|--------------|
| **Deed Management** | `DeedEntryEntity` | `DeedEntryEntity`, `DeedEntryLogEntity`, `DeedEntryLockEntity`, `DeedRegistryLockEntity` |
| **Handover** | `HandoverDataSetEntity` | `HandoverDataSetEntity`, `HandoverHistoryEntity`, `HandoverHistoryDeedEntity` |
| **Number Management** | `UvzNumberManagerEntity` | `UvzNumberManagerEntity`, `UvzNumberGapManagerEntity`, `UvzNumberSkipManagerEntity` |
| **Document Metadata** | `DocumentMetaDataEntity` | `DocumentMetaDataEntity`, `RemarkEntity`, `SignatureInfoEntity` |
| **Action Stream** | `ActionEntity` | `ActionEntity`, `ActionStreamEntity` |

### 8.1.2 Entity Relationship Diagram (text‑based)

```
[DeedEntryEntity] "1" -- "*" [DeedEntryLogEntity]
[DeedEntryEntity] "1" -- "0..1" [DeedEntryLockEntity]
[DeedEntryEntity] "*" -- "*" [ActionEntity]
[HandoverDataSetEntity] "1" -- "*" [HandoverHistoryEntity]
[HandoverHistoryEntity] "*" -- "1" [DeedEntryEntity]
[UvzNumberManagerEntity] "1" -- "*" [UvzNumberGapManagerEntity]
[DocumentMetaDataEntity] "1" -- "*" [RemarkEntity]
[DocumentMetaDataEntity] "1" -- "0..1" [SignatureInfoEntity]
```

### 8.1.3 Entity Inventory

| Entity | Key Attributes | Relationships |
|--------|----------------|---------------|
| **ActionEntity** | id, type, timestamp | belongs to `DeedEntryEntity` (many‑to‑one) |
| **ActionStreamEntity** | streamId, payload | aggregates many `ActionEntity` |
| **ChangeEntity** | changeId, description | referenced by `DeedEntryEntity` |
| **ConnectionEntity** | connectionId, status | used by `DeedEntryConnectionEntity` |
| **DeedEntryEntity** | deedId, status, createdAt | owns `DeedEntryLogEntity`, `DeedEntryLockEntity`, `ActionEntity` |
| **DeedEntryLogEntity** | logId, message, ts | belongs to `DeedEntryEntity` |
| **DeedRegistryLockEntity** | lockId, reason | protects `DeedEntryEntity` |
| **DocumentMetaDataEntity** | docId, title, version | aggregates `RemarkEntity`, `SignatureInfoEntity` |
| **HandoverDataSetEntity** | setId, handoverDate | contains `HandoverHistoryEntity` |
| **UvzNumberManagerEntity** | number, status | manages gaps via `UvzNumberGapManagerEntity` |
| **JobEntity** | jobId, type, state | scheduled by `JobServiceImpl` |
| … (remaining 350+ entities omitted for brevity) | | |

### 8.1.4 Aggregate Boundaries

* **Deed Aggregate** – Root: `DeedEntryEntity`. All modifications go through `DeedEntryServiceImpl` and are persisted by `DeedEntryDao`.
* **Handover Aggregate** – Root: `HandoverDataSetEntity`. Business rules are enforced by `HandoverDataSetServiceImpl`.
* **Number Management Aggregate** – Root: `UvzNumberManagerEntity`. Consistency is guaranteed by `NumberManagementServiceImpl` with explicit locking via `UvzNumberGapManagerDao`.

---

## 8.2 Security Concept (≈ 2 pages)

### 8.2.1 Authentication Mechanism

The system uses **Spring Security 5** with **JWT** tokens issued by an external OAuth2 provider. The relevant configuration classes are:

* `TokenAuthenticationRestTemplateConfigurationSpringBoot`
* `CustomMethodSecurityExpressionHandler`
* `ProxyRestTemplateConfiguration`

These classes are wired in the `SecurityConfig` (generated at runtime) and expose a `BearerTokenAuthenticationFilter` that validates the JWT signature, expiration and audience.

### 8.2.2 Authorization Model

* **Roles** – `ROLE_USER`, `ROLE_ADMIN`, `ROLE_AUDITOR`.
* **Permissions** – fine‑grained permissions are expressed as Spring Security expressions, e.g. `@PreAuthorize("hasPermission(#deedId, 'deed:read')")`.
* The custom expression handler (`CustomMethodSecurityExpressionHandler`) adds domain‑specific functions such as `hasDeedAccess(deedId)` that delegate to `KeyManagerServiceImpl` for policy checks.

### 8.2.3 Security Annotations & Filters

| Component | Purpose |
|-----------|---------|
| `@EnableGlobalMethodSecurity(prePostEnabled = true)` (in `SecurityConfig`) | Enables `@PreAuthorize` / `@PostAuthorize` |
| `CustomMethodSecurityExpressionHandler` | Provides `hasDeedAccess`, `hasNumberManagementRight` expressions |
| `TokenAuthenticationRestTemplateConfigurationSpringBoot` | Configures `RestTemplate` with `BearerToken` for outbound calls |
| `ProxyRestTemplateConfiguration` | Centralised proxy handling for external services |

### 8.2.4 Defensive Measures

* **CSRF** – Disabled for stateless REST endpoints (JWT). Enabled for any state‑changing UI endpoints (Angular front‑end) via `CsrfTokenRepository`.
* **XSS** – All user‑generated content is HTML‑escaped in the Angular layer; server side validates input using Bean Validation (`@Size`, `@Pattern`).
* **SQL Injection** – All data access uses JPA repositories (`DeedEntryDao`, `UvzNumberManagerDao`) with parameterised queries; no native string concatenation.

---

## 8.3 Persistence Concept (≈ 2 pages)

### 8.3.1 ORM Strategy

* **JPA / Hibernate** – Primary ORM, configured in `application.yml` under `spring.jpa`.
* Entities listed in Section 8.1 are mapped with `@Entity`, `@Table`, and appropriate `@Id` strategies (mostly `@GeneratedValue` with `SEQUENCE`).
* **Repositories** – Spring Data JPA interfaces such as `DeedEntryDao`, `UvzNumberManagerDao`, `DocumentMetaDataDao` extend `JpaRepository`.

### 8.3.2 Transaction Management

* All service methods that modify state are annotated with `@Transactional` (e.g. `DeedEntryServiceImpl.saveDeed`, `NumberManagementServiceImpl.allocateNumber`).
* Read‑only transactions use `@Transactional(readOnly = true)` to optimise session handling.
* Propagation is set to `REQUIRED` for most use‑cases; explicit `REQUIRES_NEW` is used in `ArchivingServiceImpl` to isolate archival writes.

### 8.3.3 Connection Pooling

* **HikariCP** – Configured via `spring.datasource.hikari.*` properties. Default pool size = 20, max‑lifetime = 30 min.
* Monitoring of pool metrics is exposed through the Actuator endpoint `/actuator/metrics/hikaricp.connections`.

### 8.3.4 Database Migration Strategy

* **Flyway** (v8) – Migration scripts live under `src/main/resources/db/migration` with naming `V1__init.sql`, `V2__add_deed_tables.sql`, …
* The migration is executed on application start (`flyway.enabled=true`).
* Version history is stored in the `flyway_schema_history` table, enabling roll‑backs via `flyway.undo` when needed.

---

## 8.4 Error Handling and Exception Strategy (≈ 1‑2 pages)

### 8.4.1 Exception Hierarchy

```
└─ RuntimeException (Spring)
   ├─ BusinessException (custom base)
   │   ├─ DeedNotFoundException
   │   ├─ NumberAllocationException
   │   └─ UnauthorizedActionException
   └─ SystemException (custom base)
       ├─ DatabaseAccessException
       └─ ExternalServiceException
```

All custom exceptions extend either `BusinessException` or `SystemException` to allow consistent handling.

### 8.4.2 Global Exception Handler

The class **`DefaultExceptionHandler`** (stereotype *controller*) is annotated with `@ControllerAdvice` and defines:

* `@ExceptionHandler(BusinessException.class)` → returns **HTTP 400** with a JSON payload `{ "error": "<code>", "message": "..." }`.
* `@ExceptionHandler(SystemException.class)` → returns **HTTP 500** with a generic message and logs the stack trace.
* `@ExceptionHandler(MethodArgumentNotValidException.class)` → returns **HTTP 422** with field‑error details.

### 8.4.3 Error Response Format

```json
{
  "timestamp": "2024-11-01T12:34:56.789Z",
  "path": "/api/deed/123",
  "error": "DEED_NOT_FOUND",
  "message": "Deed with id 123 does not exist.",
  "status": 404,
  "traceId": "a1b2c3d4e5"
}
```

The `traceId` is generated by `HealthCheck` and propagated via MDC for correlation.

---

## 8.5 Logging and Monitoring (≈ 1‑2 pages)

### 8.5.1 Logging Framework

* **SLF4J** API with **Logback** implementation.
* Configuration file `logback-spring.xml` defines three appenders:
  * `CONSOLE` – development, pattern `%d{HH:mm:ss.SSS} %-5level %logger{36} - %msg%n`
  * `FILE` – production, rolling daily, size‑based rollover 100 MB.
  * `JSON` – structured JSON logs for ELK stack, fields: `timestamp`, `level`, `logger`, `traceId`, `message`.

### 8.5.2 Log Levels Strategy per Layer

| Layer | Package Pattern | Log Level |
|-------|----------------|----------|
| **Controller** | `..controller..` | `INFO` (request entry/exit) |
| **Service** | `..service..` | `DEBUG` (business decisions) |
| **Repository** | `..dao..` | `TRACE` (SQL statements) |
| **Infrastructure** | `..config..` | `WARN` (mis‑config) |

### 8.5.3 Structured Logging Example

```json
{
  "timestamp":"2024-11-01T12:35:01.123Z",
  "level":"INFO",
  "logger":"com.uvz.service.DeedEntryServiceImpl",
  "traceId":"a1b2c3d4e5",
  "message":"Deed 123 created",
  "deedId":"123",
  "user":"john.doe"
}
```

### 8.5.4 Health Checks & Metrics

* **`HealthCheck`** (service) implements Spring Boot Actuator `HealthIndicator` exposing `/actuator/health`.
* Metrics collected via Micrometer and exposed on `/actuator/metrics` – includes:
  * `jvm.memory.used`
  * `http.server.requests`
  * `db.pool.usage`
* Alerting thresholds are defined in `application.yml` (e.g., `management.endpoint.health.show-details=always`).

---

*All sections reference concrete component names extracted from the code base, ensuring the documentation reflects the actual implementation.*
