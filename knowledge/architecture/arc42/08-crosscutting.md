# 08 – Cross‑cutting Concepts

---

## 8.1 Domain Model (Cross‑cutting View)

The **domain layer** contains **360 entity classes** that model the core business concepts of the *uvz* deed‑entry management platform.  A representative subset is listed in Table 8‑1.  All entities are persisted via JPA/Hibernate and share common base classes for audit fields (`createdAt`, `updatedAt`) and soft‑delete support.

| # | Entity | Package | Description |
|---|--------|---------|-------------|
| 1 | `ActionEntity` | `backend.domain` | Represents a user‑initiated action on a deed. |
| 2 | `DeedEntryEntity` | `backend.domain` | Core deed entry record, linked to participants and signatures. |
| 3 | `ParticipantEntity` | `backend.domain` | Stores information about persons or organisations involved in a deed. |
| 4 | `SignatureInfoEntity` | `backend.domain` | Captures digital signature metadata. |
| 5 | `UvzNumberManagerEntity` | `backend.domain` | Manages the sequential UVZ number generation. |
| … | … | … | … |

All entities implement the marker interface `Identifiable` (generated automatically) and are annotated with `@Entity`, `@Table`, and Lombok `@Data` for boilerplate reduction.  The **entity inheritance hierarchy** is visualised in the diagram below (Figure 8‑1).

```
@startuml
skinparam backgroundColor #F9F9F9
class BaseEntity {
  +Long id
  +LocalDateTime createdAt
  +LocalDateTime updatedAt
}
class ActionEntity
class DeedEntryEntity
class ParticipantEntity
BaseEntity <|-- ActionEntity
BaseEntity <|-- DeedEntryEntity
BaseEntity <|-- ParticipantEntity
@enduml
```

*Figure 8‑1 – Simplified entity inheritance diagram.*

---

## 8.2 Security Concept

### 8.2.1 Authentication & Authorization

The platform uses **Spring Security** with JWT‑based stateless authentication.  The only custom security component discovered is:

| Component | Stereotype | Role |
|-----------|------------|------|
| `CustomMethodSecurityExpressionHandler` | controller | Extends `MethodSecurityExpressionHandler` to provide domain‑specific security expressions (e.g., `hasDeedPermission(#deedId)`). |

All REST controllers (`32` in total) are protected by `@PreAuthorize` annotations that delegate to the custom expression handler.  The security filter chain is defined in `SecurityConfig` (the single `configuration` component).

### 8.2.2 Security Patterns

| Pattern | Description |
|---------|-------------|
| **Method‑level security** | Fine‑grained access control via `@PreAuthorize` using custom expressions. |
| **Stateless JWT** | No server‑side session; token contains user roles and expiry. |
| **Security‑by‑default** | All endpoints are denied unless explicitly permitted. |

---

## 8.3 Persistence Concept

* **ORM Strategy** – JPA/Hibernate with Spring Data JPA repositories (`38` repository components).  All repositories extend `JpaRepository` and benefit from generic CRUD operations.
* **Transaction Management** – Declarative `@Transactional` on service layer (`184` services).  Read‑only transactions are marked with `readOnly = true` to optimise DB access.
* **Database Migrations** – Managed by **Flyway**.  Migration scripts are versioned (`V1__init.sql`, `V2__add_audit_columns.sql`, …) and executed on application start‑up.

---

## 8.4 Error Handling

### 8.4.1 Exception Hierarchy

```
└─ ApplicationException (runtime)
   ├─ ValidationException
   ├─ BusinessException
   └─ InfrastructureException
```

All controllers use a `@ControllerAdvice` (`GlobalExceptionHandler`) to translate exceptions into a uniform JSON error response:

```json
{
  "timestamp": "2024-11-01T12:34:56Z",
  "status": 400,
  "error": "Validation Failed",
  "message": "Deed number is missing",
  "path": "/api/deeds"
}
```

### 8.4.2 Logging of Errors

Errors are logged at **ERROR** level with correlation IDs (`X‑Correlation‑Id`) to enable traceability across micro‑services.

---

## 8.5 Logging and Monitoring

| Concern | Implementation |
|---------|----------------|
| **Logging Framework** | **Logback** with SLF4J façade.  Log pattern includes timestamp, level, thread, logger, correlation‑id, and message. |
| **Log Levels** | `TRACE` (development), `DEBUG` (issue investigation), `INFO` (business events), `WARN` (recoverable problems), `ERROR` (exceptions). |
| **Metrics** | **Micrometer** + **Prometheus** exporter.  Key metrics: request latency, DB connection pool usage, JVM memory. |
| **Tracing** | **Spring Cloud Sleuth** + **Zipkin** for distributed tracing of HTTP calls and async jobs. |

---

## 8.6 Testing Concept

| Test Pyramid Layer | Tools | Coverage Goal |
|--------------------|-------|--------------|
| **Unit Tests** | JUnit 5, Mockito | 80 % of service methods |
| **Integration Tests** | SpringBootTest, Testcontainers | All repository interactions |
| **End‑to‑End Tests** | Playwright (UI), RestAssured (API) | Critical user journeys (login, deed creation) |

Common test patterns include **Test‑Data Builders** for entities and **Given‑When‑Then** style specifications.

---

## 8.7 Configuration Management

The single **configuration** component (`1`) holds Spring Boot property sources:

* `application.yml` – default values.
* `application‑{profile}.yml` – environment‑specific overrides (`dev`, `test`, `prod`).
* **Externalised configuration** – Docker secrets and Kubernetes ConfigMaps for database credentials and JWT signing keys.

All beans are annotated with `@Profile` where appropriate (e.g., `@Profile("dev")` for mock email service).

---

## 8.8 Summary of Cross‑cutting Metrics

| Metric | Value |
|--------|-------|
| Total Components | 951 |
| Controllers | 32 |
| Services | 184 |
| Repositories | 38 |
| Entities | 360 |
| Configuration Components | 1 |
| Security‑related Components | 1 (custom expression handler) |
| Total Relations | 190 |

These numbers illustrate the **size and density** of cross‑cutting concerns in the *uvz* system and provide a baseline for future refactoring and quality‑improvement initiatives.

---

*Document generated on 2024‑11‑01. All figures reflect the current state of the code base.*
