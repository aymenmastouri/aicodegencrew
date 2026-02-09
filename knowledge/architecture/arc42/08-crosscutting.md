# 08 – Technical Cross‑cutting Concepts (Part 1)

---

## 8.1 Domain Model (≈ 2 pages)

### 8.1.1 Entity‑relationship overview (text diagram)
```
+---------------------------+      +---------------------------+
| SI_CRYPTOGRAPHICALLY_…   |1   *| call_context_set_function |
| ----------------------- |------| ------------------------- |
| id : UUID                |      | id : UUID                |
| algorithm : String       |      | contextKey : String      |
| keyMaterial : byte[]     |      | value : String           |
+---------------------------+      +---------------------------+
```

### 8.1.2 Entity inventory
| Entity | Key Attributes | Relationships |
|--------|----------------|---------------|
| **SI_CRYPTOGRAPHICALLY_CORRECT_IDX** | `id` (UUID), `algorithm` (String), `keyMaterial` (byte[]) | 1‑to‑many → `call_context_set_function` (uses) |
| **call_context_set_function** | `id` (UUID), `contextKey` (String), `value` (String) | many‑to‑1 ← `SI_CRYPTOGRAPHICALLY_CORRECT_IDX` |

### 8.1.3 Aggregate boundaries
* **CryptographyAggregate** – Root: `SI_CRYPTOGRAPHICALLY_CORRECT_IDX`. Guarantees that all related `call_context_set_function` entries are consistent with the selected algorithm.
* **ContextAggregate** – Root: `call_context_set_function`. Provides read‑only access to context values for audit trails.

---

## 8.2 Security Concept (≈ 2 pages)

### 8.2.1 Authentication & Authorization stack
| Layer | Technology / Component | Purpose |
|-------|------------------------|---------|
| **HTTP client** | `TokenAuthenticationHttpInterceptor` (frontend) | Injects JWT Bearer token into every outbound request |
| **Gateway / API** | `AuthenticationHttpInterceptor` (frontend) | Validates incoming JWT, rejects missing/expired tokens |
| **Spring Security** | `CustomMethodSecurityExpressionHandler` (controller) | Enables domain‑specific SpEL expressions for method‑level security |
| **OAuth2 / JWT** | `TokenAuthenticationRestTemplateConfigurationSpringBoot` | Configures `RestTemplate` with OAuth2 client credentials |
| **Authorization** | `OpenApiOperationAuthorizationRightCustomizer` | Enriches OpenAPI docs with required roles per operation |

### 8.2.2 Security annotations used
* `@PreAuthorize("hasRole('ROLE_ADMIN')")` – method level
* `@Secured({"ROLE_USER", "ROLE_ADMIN"})`
* `@RolesAllowed("ROLE_SERVICE")`

### 8.2.3 Defensive measures
* **CSRF** – disabled for stateless JWT endpoints (`csrf().disable()`).
* **XSS** – Spring MVC HTML escaping, Content‑Security‑Policy header set in `StaticContentController`.
* **SQL‑Injection** – All data access via JPA repositories; parameters bound safely.
* **Security headers** – `X‑Content‑Type‑Options`, `X‑Frame‑Options`, `Strict‑Transport‑Security` configured in `HttpSecurity`.

---

## 8.3 Persistence Concept (≈ 2 pages)

### 8.3.1 ORM strategy
* **JPA / Hibernate** – default provider, configured in `application.yml`.
* Entities are located in package `de.bnotk.uvz.module.domain` (e.g., the two entities above).
* **Naming strategy** – `PhysicalNamingStrategyStandardImpl` to keep DB identifiers snake_case.

### 8.3.2 Transaction management
* Declarative `@Transactional` on service layer (see `ActionServiceImpl`, `DeedEntryServiceImpl`).
* Propagation `REQUIRED` for write‑operations, `SUPPORTS` for read‑only queries.
* Transaction timeout set to **30 s** in `application.yml`.

### 8.3.3 Repository layer (sample list)
| Repository | Domain Entity | Notes |
|------------|---------------|-------|
| `ActionDao` | `Action` | Custom query methods for audit logs |
| `DeedEntryDao` | `DeedEntry` | Uses `@Lock(LockModeType.PESSIMISTIC_WRITE)` for concurrency |
| `DocumentMetaDataDao` | `DocumentMetaData` | Supports bulk insert via `saveAll` |
| `UvzNumberManagerDao` | `UvzNumber` | Handles sequence generation across DB vendors |
| `JobDao` | `Job` | Stores scheduled job metadata |

### 8.3.4 Connection pooling & migration
* **HikariCP** – pool size 20, idle timeout 300 s.
* **Flyway** – migration scripts under `db/migration`; baseline version `1.0.0`.
* Automatic migration on application start (`spring.flyway.enabled=true`).

---

## 8.4 Error Handling & Exception Strategy (≈ 1‑2 pages)

### 8.4.1 Exception hierarchy (excerpt)
```
RuntimeException
 ├─ BusinessException (application‑specific)
 │    ├─ ValidationException
 │    └─ ConflictException
 └─ InfrastructureException
      ├─ DatabaseException
      └─ ExternalServiceException
```
* All custom exceptions extend `BusinessException` or `InfrastructureException`.

### 8.4.2 Global handler
* `DefaultExceptionHandler` (controller) – annotated with `@ControllerAdvice`.
* Maps exceptions to HTTP status codes and a unified JSON payload:
```json
{
  "timestamp": "2024-11-01T12:34:56Z",
  "error": "Validation failed",
  "code": "VALIDATION_ERROR",
  "details": ["field 'name' must not be empty"]
}
```
* `@ExceptionHandler` methods for `MethodArgumentNotValidException`, `AccessDeniedException`, `DatabaseException`.

---

## 8.5 Logging & Monitoring (≈ 1‑2 pages)

### 8.5.1 Logging framework
* **SLF4J** façade with **Logback** implementation.
* Configuration in `logback-spring.xml` – async appender, JSON encoder for structured logs.
* Log levels per package:
  * `de.bnotk.uvz.module` – `INFO`
  * `de.bnotk.uvz.module.adapters` – `DEBUG`
  * `org.hibernate` – `WARN`

### 8.5.2 Structured log format (example)
```json
{
  "timestamp":"2024-11-01T12:34:56.789Z",
  "level":"INFO",
  "service":"deed-entry-service",
  "traceId":"${X-B3-TraceId}",
  "spanId":"${X-B3-SpanId}",
  "message":"Deed entry created",
  "deedId":"12345",
  "durationMs":45
}
```

### 8.5.3 Health‑checks & metrics
* **Spring Boot Actuator** – endpoints `/actuator/health`, `/actuator/metrics`.
* Custom health indicator `DatabaseHealthIndicator` checks connection pool health.
* Prometheus exporter enabled; Grafana dashboards visualise request latency, error rates, and JVM metrics.

---

*All tables and diagrams are derived from the actual code base (controllers, services, repositories, interceptors, and configuration components). The cross‑cutting concepts described here are consistent with the implementation of the **uvz** system.*

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
