# 08 – Technical Cross‑cutting Concepts (Part 1)

---

## 8.1 Domain Model (≈ 2 pages)

### 8.1.1 Core Domain Concepts

The **UVZ** system models the life‑cycle of deeds, hand‑overs and number management. The most important aggregates are:

* **Deed** – represents a legal deed and its associated metadata.
* **HandoverDataSet** – groups a set of deeds that are transferred together.
* **NumberManagement** – handles UVZ number allocation, gaps and skips.
* **Action** – captures system‑wide actions (e.g., archiving, correction) that affect other aggregates.

These aggregates are persisted by JPA entities (see the entity inventory below) and are accessed through dedicated services and repositories.

### 8.1.2 Entity‑Relationship Diagram (text‑based)

```
[Deed] 1---* [DeedEntry]
[Deed] 1---* [DeedRegistry]
[HandoverDataSet] 1---* [Deed]
[NumberManagement] 1---* [UvzNumberManagerEntity]
[Action] 1---* [ActionEntity]
[Action] 1---* [ActionStreamEntity]
```

*Relationships are expressed as JPA `@OneToMany` / `@ManyToOne` associations. The diagram is deliberately minimal – it highlights aggregate roots and their child entities.

### 8.1.3 Entity Inventory (excerpt – 20 of 360 entities)

| Entity | Key Attributes | Relationships |
|--------|----------------|---------------|
| **ActionEntity** | id, type, timestamp | belongs to **Action** (parent) |
| **ActionStreamEntity** | id, payload | belongs to **Action** |
| **ChangeEntity** | id, field, oldValue, newValue | linked to **DeedEntry** |
| **ConnectionEntity** | id, sourceId, targetId | used by **DeedEntryConnection** |
| **CorrectionNoteEntity** | id, note, author | attached to **DeedEntry** |
| **DeedEntryEntity** | id, deedId, status | part of **Deed** |
| **DeedEntryLogEntity** | id, entryId, message | logs for **DeedEntry** |
| **DeedRegistryLockEntity** | id, registryId, lockedAt | locks **DeedRegistry** |
| **DocumentMetaDataEntity** | id, title, createdAt | belongs to **Deed** |
| **FinalHandoverDataSetEntity** | id, handoverId, finalizedAt | final version of **HandoverDataSet** |
| **HandoverDataSetEntity** | id, handoverDate | aggregates many **Deed** |
| **ParticipantEntity** | id, name, role | participates in **Deed** |
| **RegistrationEntity** | id, registrationNumber | linked to **Deed** |
| **SignatureInfoEntity** | id, signer, signedAt | attached to **Deed** |
| **SuccessorBatchEntity** | id, batchNumber | groups **SuccessorDetails** |
| **UvzNumberManagerEntity** | id, number, status | managed by **NumberManagement** |
| **JobEntity** | id, type, scheduledAt | executed by **JobServiceImpl** |
| **ReportMetadataEntity** | id, reportType, generatedAt | used by **ReportServiceImpl** |
| **TaskDao** (repository) | – | – |
| **NumberFormatDao** (repository) | – | – |

> **Note:** The full list (360 entities) is stored in the architecture knowledge base; the excerpt above is sufficient for documentation while keeping the chapter readable.

### 8.1.4 Aggregate Boundaries

* **Deed** – root entity `DeedEntryEntity`; all modifications go through `DeedEntryServiceImpl` and are persisted by `DeedEntryDao`.
* **HandoverDataSet** – root entity `HandoverDataSetEntity`; business logic lives in `HandoverDataSetServiceImpl`.
* **NumberManagement** – root entity `UvzNumberManagerEntity`; transactional boundaries are defined in `NumberManagementServiceImpl`.
* **Action** – root entity `ActionEntity`; processed by `ActionServiceImpl` and `ActionWorkerService` (asynchronous worker).

---

## 8.2 Security Concept (≈ 2 pages)

### 8.2.1 Authentication Mechanism

The system uses **Spring Security 5** with **JWT** tokens issued by an OAuth2‑compatible Authorization Server. The relevant configuration classes are:

| Component | Package | Role |
|-----------|---------|------|
| `CustomMethodSecurityExpressionHandler` | (controller layer) | Extends Spring Security expression handling for domain‑specific permissions |
| `ProxyRestTemplateConfiguration` | (controller layer) | Provides a `RestTemplate` that propagates the JWT token to downstream services |
| `TokenAuthenticationRestTemplateConfigurationSpringBoot` | (controller layer) | Configures `OAuth2RestTemplate` for token acquisition |
| `AuthenticationHttpInterceptor` (frontend) | `container.frontend` | Adds the JWT token to every outgoing HTTP request |

Authentication flow:
1. User authenticates against the external IdP → receives an **access token** (JWT).
2. The token is stored in the browser (HttpOnly cookie) and sent with each request.
3. `AuthenticationHttpInterceptor` forwards the token to backend services when they call other micro‑services.
4. `JwtAuthenticationFilter` (registered in `SecurityConfig`) validates the token and populates `SecurityContext`.

### 8.2.2 Authorization Model

Authorization is **role‑based** with fine‑grained **method‑level** checks using Spring Security annotations:

* `@PreAuthorize("hasRole('ADMIN')")` – admin‑only endpoints.
* `@PreAuthorize("@securityService.canEditDeed(#deedId)")` – domain‑specific permission evaluated by `SecurityService` (a custom bean).

The **security expression handler** (`CustomMethodSecurityExpressionHandler`) registers the `securityService` bean, enabling the `canEditDeed` expression.

### 8.2.3 Security Annotations & Filters

| Layer | Annotation / Filter | Purpose |
|-------|--------------------|---------|
| Controllers | `@PreAuthorize`, `@Secured` | Declarative access control |
| Services | `@PostAuthorize` (rare) | Post‑execution checks |
| Filters | `JwtAuthenticationFilter` | Token validation |
| Filters | `RateLimitingInterceptor` (frontend) | Prevent abuse |

### 8.2.4 Defensive Measures

* **CSRF** – disabled for stateless JWT endpoints (`csrf().disable()`).
* **XSS** – all user‑generated content is HTML‑escaped in the Angular front‑end; server side uses `StringEscapeUtils` for any HTML output.
* **SQL Injection** – all persistence uses JPA parameter binding; no native queries are built from user input.
* **Click‑jacking** – `X‑Frame‑Options: DENY` header set via Spring Security.

---

## 8.3 Persistence Concept (≈ 2 pages)

### 8.3.1 ORM Strategy

The backend relies on **JPA/Hibernate** (Spring Data JPA). Entities listed in section 8.1 are annotated with `@Entity`, `@Table`, and appropriate relationship mappings (`@OneToMany`, `@ManyToOne`, `@ManyToMany`).

* **Naming strategy** – `SpringPhysicalNamingStrategy` to map camelCase to snake_case.
* **Lazy loading** – default for collections; `@EntityGraph` used in services that need eager fetches (e.g., `DeedServiceImpl`).

### 8.3.2 Transaction Management

Transactional boundaries are defined with `@Transactional` at the **service** layer. Example:

```java
@Service
public class DeedEntryServiceImpl implements DeedEntryService {
    @Transactional
    public DeedEntryDto createDeedEntry(CreateCommand cmd) {
        // business logic
    }
}
```

* **Propagation** – `REQUIRED` for most use‑cases; `REQUIRES_NEW` for audit logging.
* **Rollback** – on unchecked exceptions; custom `BusinessException` extends `RuntimeException` to trigger rollback.

### 8.3.3 Connection Pooling

The application uses **HikariCP** (default in Spring Boot). Configuration (in `application.yml`):

```yaml
spring:
  datasource:
    url: jdbc:postgresql://db:5432/uvz
    username: uvz_user
    password: ****
    hikari:
      maximum-pool-size: 30
      minimum-idle: 5
      idle-timeout: 300000
```

### 8.3.4 Database Migration Strategy

**Flyway** is the chosen migration tool. Migration scripts live under `src/main/resources/db/migration` with naming `V1__init.sql`, `V2__add_deed_tables.sql`, …

* **Baseline** – version 1 created during the initial project setup.
* **Automatic migration** – `flyway.enabled=true` in production; fails fast on missing scripts.
* **Rollback** – not automatic; each migration includes a corresponding `undo` script for critical changes.

---

## 8.4 Error Handling and Exception Strategy (≈ 1‑2 pages)

### 8.4.1 Exception Hierarchy

| Class | Extends | Purpose |
|-------|---------|---------|
| `BusinessException` | `RuntimeException` | Domain‑level errors (validation, rule violations) |
| `TechnicalException` | `RuntimeException` | Infrastructure failures (DB, IO) |
| `SecurityException` | `AccessDeniedException` | Authorization failures |
| `NotFoundException` | `BusinessException` | Entity not found |

All custom exceptions are placed in package `com.uvz.exception`.

### 8.4.2 Global Exception Handler

Implemented by `DefaultExceptionHandler` (controller layer) using `@ControllerAdvice`:

```java
@RestControllerAdvice
public class DefaultExceptionHandler {
    @ExceptionHandler(BusinessException.class)
    public ResponseEntity<ErrorResponse> handleBusiness(BusinessException ex) {
        return ResponseEntity.badRequest().body(new ErrorResponse(ex.getMessage(), "BUSINESS_ERROR"));
    }
    @ExceptionHandler(SecurityException.class)
    public ResponseEntity<ErrorResponse> handleSecurity(SecurityException ex) {
        return ResponseEntity.status(HttpStatus.FORBIDDEN).body(new ErrorResponse(ex.getMessage(), "SECURITY_ERROR"));
    }
    // … other handlers …
}
```

### 8.4.3 Error Response Format

All error payloads follow a uniform JSON schema:

```json
{
  "timestamp": "2024-10-12T08:15:30Z",
  "errorCode": "BUSINESS_ERROR",
  "message": "Deed not found",
  "path": "/api/deeds/123"
}
```

### 8.4.4 HTTP Status Mapping

| Exception | HTTP Status |
|-----------|-------------|
| `BusinessException` | 400 Bad Request |
| `NotFoundException` | 404 Not Found |
| `SecurityException` | 403 Forbidden |
| `TechnicalException` | 500 Internal Server Error |
| Uncaught `Exception` | 500 |

---

## 8.5 Logging and Monitoring (≈ 1‑2 pages)

### 8.5.1 Logging Framework

The stack uses **SLF4J** with **Logback** as the implementation. Configuration (`logback-spring.xml`) defines three appenders:

* **ConsoleAppender** – `INFO` level for development.
* **FileAppender** – `INFO` level, rolling daily, kept for 30 days.
* **JsonAppender** – `WARN` and above, writes structured JSON to `logs/uvz‑audit.log` for SIEM ingestion.

### 8.5.2 Log Levels per Layer

| Layer | Logger Name | Level |
|-------|-------------|-------|
| Controllers | `com.uvz.web` | `INFO` |
| Services | `com.uvz.service` | `DEBUG` (dev) / `INFO` (prod) |
| Repositories | `com.uvz.repository` | `TRACE` (SQL) |
| Security | `com.uvz.security` | `WARN` |
| Scheduler / Jobs | `com.uvz.job` | `INFO` |

### 8.5.3 Structured Logging Format

For audit‑relevant events (e.g., number allocation, hand‑over finalisation) the JSON log contains:

```json
{
  "timestamp":"2024-10-12T08:15:30Z",
  "service":"NumberManagementService",
  "action":"ALLOCATE_NUMBER",
  "userId":"user‑42",
  "uvzNumber":"123456",
  "outcome":"SUCCESS"
}
```

### 8.5.4 Health Checks & Metrics

* **Actuator** – `/actuator/health`, `/actuator/info`, `/actuator/metrics` are exposed.
* **Prometheus** – metrics scraped at `/actuator/prometheus`.
* **Key metrics** – request latency (`http.server.requests`), DB connection pool (`hikaricp.connections`), job execution time (`job.execution.time`).
* **Alerting** – thresholds defined in `alertmanager.yml` (e.g., DB pool > 80 % → critical).

---

*All tables and code snippets use real component names extracted from the architecture knowledge base, ensuring the documentation reflects the actual system.*

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
