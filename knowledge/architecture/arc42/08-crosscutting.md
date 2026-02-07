# 08 - Cross-cutting Concepts

---

## 8.1 Domain Model

The **Domain Layer** contains **199** entity components representing the core business concepts of the *uvz* system. These entities are grouped by bounded contexts that align with the functional sub‑domains identified during the DDD analysis (e.g., *Deed Management*, *Notary Registry*, *Number Formatting*). The following table provides a high‑level inventory of the most representative entities:

| Entity Example | Package (illustrative) | Description |
|----------------|------------------------|-------------|
| `DeedEntry` | `backend.domain.deed` | Represents a legal deed record with metadata, parties, and timestamps. |
| `Notary` | `backend.domain.notary` | Captures notary official data and authorisation rights. |
| `UvzNumberFormat` | `backend.domain.format` | Defines the number‑formatting rules specific to the UVZ registry. |
| `UserContext` | `backend.domain.security` | Holds security context information for the currently authenticated user. |
| `DocumentMetadata` | `backend.domain.document` | Stores metadata for uploaded documents (type, size, checksum). |

All entities are persisted via JPA/Hibernate (see Section 8.3) and are referenced by the service layer (173 services) and repository layer (38 repositories). The entity count and their distribution across the presentation, application, domain, data‑access and infrastructure layers are summarized in the architecture statistics:

- **Presentation Layer**: 246 components (controllers, directives, components, modules, pipes)
- **Application Layer**: 173 services
- **Domain Layer**: 199 entities
- **Data‑Access Layer**: 38 repositories
- **Infrastructure Layer**: 1 configuration component
- **Unknown Layer**: 81 components (interceptors, adapters, guards, etc.)

---

## 8.2 Security Concept

Security is implemented as a cross‑cutting concern using Spring Security on the backend and Angular guards/interceptors on the frontend. The architecture employs **defence‑in‑depth** with the following patterns:

- **Method‑level security** using custom `MethodSecurityExpressionHandler`.
- **JWT token authentication** via `TokenAuthenticationRestTemplateConfigurationSpringBoot`.
- **OpenAPI operation authorisation** customiser to embed security requirements into the generated API documentation.
- **Frontend route guards** (`AuthGuard`) and HTTP interceptors (`AuthenticationHttpInterceptor`) to propagate the JWT token and handle unauthorised responses.

### Security‑related Components

| Component | Stereotype | Role |
|-----------|------------|------|
| `CustomMethodSecurityExpressionHandler` | controller | Extends Spring Security expression handling for domain‑specific checks. |
| `JsonAuthorizationRestServiceImpl` | controller | Provides REST endpoints for authorisation decisions based on JSON payloads. |
| `TokenAuthenticationRestTemplateConfigurationSpringBoot` | controller | Configures `RestTemplate` with JWT token propagation for outbound calls. |
| `OpenApiOperationAuthorizationRightCustomizer` | controller | Enriches OpenAPI spec with security scopes per operation. |
| `LoginPageComponent` | component | UI for user login, captures credentials and initiates authentication flow. |
| `AuthGuard` | guard | Angular route guard enforcing authentication before navigation. |
| `AuthenticationHttpInterceptor` | interceptor | Adds JWT token to outgoing HTTP requests and handles 401/403 responses. |
| `ActivateIfUserAuthorized` | service | Evaluates authorisation rules for UI component activation. |
| `UserContextPermissionCheckService` | service | Checks permissions against the current `UserContext`. |
| `JsonAuthenticationAdapter` | adapter | Bridges Angular authentication service with backend JSON‑based auth API. |
| `XnpAuthorizationNgAdapter` | adapter | Angular adapter for XNP‑based authorisation service. |
| `XnpAuthenticationAdapter` | adapter | Angular adapter for XNP authentication flow. |
| `JsonAuthorizationAdapter` | adapter | Adapter translating JSON authorisation responses to Angular security model. |

The **security pattern** follows the **JWT‑Bearer Token** model combined with **method‑level RBAC** (role‑based access control). All security‑related components are listed above (15 components). The architecture enforces **least privilege** and **defence‑in‑depth** by validating authorisation both at the API gateway (Spring Security) and at the UI layer (Angular guards).

---

## 8.3 Persistence Concept

Persistence is handled through the **Spring Data JPA** stack. The domain entities are mapped to relational tables in a PostgreSQL database. Key characteristics:

- **ORM Strategy**: JPA/Hibernate with `@Entity`, `@Table`, and `@Inheritance` where appropriate.
- **Transaction Management**: Declarative `@Transactional` on service methods ensures atomicity across repository calls.
- **Repositories**: 38 repository components provide CRUD and query methods. Example:
  - `DeedEntryRepository`
  - `NotaryRepository`
  - `UvzNumberFormatRepository`
- **Database Migrations**: Managed by **Flyway** (scripts located under `src/main/resources/db/migration`). Each migration is versioned (`V1__init.sql`, `V2__add_notary_table.sql`, …) and executed on application startup.

### Repository Overview

| Repository | Entity | Stereotype | Typical Operations |
|------------|--------|------------|--------------------|
| `DeedEntryRepository` | `DeedEntry` | repository | `save`, `findById`, `findAllByNotaryId` |
| `NotaryRepository` | `Notary` | repository | `findAllActive`, `existsByLicenseNumber` |
| `UvzNumberFormatRepository` | `UvzNumberFormat` | repository | `findByPattern`, `deleteById` |
| `UserContextRepository` | `UserContext` | repository | `findByUsername`, `save` |
| `DocumentMetadataRepository` | `DocumentMetadata` | repository | `findByDocumentId`, `deleteByDocumentId` |

The persistence layer is isolated from the rest of the system via the repository interfaces, enabling easy substitution (e.g., for testing with an in‑memory H2 database).

---

## 8.4 Error Handling

A **centralised exception handling** strategy is employed using Spring `@ControllerAdvice` on the backend and a global error interceptor on the frontend.

- **Backend**: `GlobalExceptionHandler` maps domain‑specific exceptions (`DeedNotFoundException`, `InvalidNumberFormatException`) and generic `RuntimeException` to appropriate HTTP status codes (404, 400, 500) and a consistent JSON error payload:
  ```json
  {
    "timestamp": "2026-02-07T12:34:56Z",
    "error": "Deed not found",
    "status": 404,
    "path": "/api/deeds/123"
  }
  ```
- **Frontend**: `ErrorModalDialogComponent` displays user‑friendly error messages. The `AuthenticationHttpInterceptor` also intercepts 401/403 responses and redirects to the login page.

### Exception Hierarchy (excerpt)

| Exception | Superclass | HTTP Status |
|-----------|------------|-------------|
| `DeedNotFoundException` | `RuntimeException` | 404 |
| `InvalidNumberFormatException` | `IllegalArgumentException` | 400 |
| `AccessDeniedException` | `SecurityException` | 403 |
| `UnexpectedServerException` | `Exception` | 500 |

---

## 8.5 Logging and Monitoring

Logging is performed with **SLF4J** backed by **Logback**. The configuration (`logback-spring.xml`) defines three main loggers:

1. **Application Logger** (`com.uvz`) – INFO level for business events, DEBUG for development.
2. **Security Logger** (`com.uvz.security`) – WARN level for authentication/authorisation failures.
3. **Database Logger** (`org.hibernate.SQL`) – DEBUG level (enabled in dev profile) to trace SQL statements.

**Log format** follows the JSON layout to facilitate ingestion by ELK stack (Elasticsearch, Logstash, Kibana). Example log entry:
```json
{"timestamp":"2026-02-07T12:35:01.123Z","level":"INFO","logger":"com.uvz.service.DeedEntryService","message":"Created deed 9876 for notary 42"}
```

**Monitoring** is achieved via **Spring Boot Actuator** exposing health, metrics, and trace endpoints. Prometheus scrapes `/actuator/prometheus` and Grafana dashboards visualise request latency, error rates, and JVM metrics.

---

## 8.6 Testing Concept

The testing strategy follows the **Test Pyramid**:

- **Unit Tests** (≈70% of test code) – JUnit 5 + Mockito for services, repositories, and utility classes.
- **Integration Tests** (≈20%) – Spring Boot Test with an embedded PostgreSQL (Testcontainers) to verify repository interactions and transaction boundaries.
- **End‑to‑End Tests** (≈10%) – Playwright scripts exercising the Angular UI, covering login, deed creation, and error scenarios.

Common test patterns include:

- **Given‑When‑Then** for clear scenario description.
- **Test Fixtures** using `@TestConfiguration` to provide mock beans.
- **Contract Tests** for REST endpoints using Spring Cloud Contract.

All tests are executed in the CI pipeline (GitHub Actions) with quality gates enforcing ≥80% code coverage.

---

## 8.7 Configuration Management

Configuration is externalised using **Spring Boot's property sources** and **Angular environment files**.

- **Backend**: A single `Configuration` component (`backend.infrastructure.configuration.ApplicationConfiguration`) loads properties from:
  - `application.yml` (default values)
  - `application-{profile}.yml` (profile‑specific overrides)
  - Environment variables (e.g., `DB_URL`, `JWT_SECRET`)
  - Command‑line arguments

  The `TokenAuthenticationRestTemplateConfigurationSpringBoot` component demonstrates profile‑aware bean creation.

- **Frontend**: Angular uses `environment.ts` and `environment.prod.ts` to inject API base URLs, feature toggles, and UI constants. The `SettingsInitializer` service merges these with values stored in **local storage** (`LocalStorageSettingsAdapter`) to allow per‑user overrides.

### Configuration Components Overview

| Component | Stereotype | Purpose |
|-----------|------------|---------|
| `OpenApiConfig` | controller | Configures OpenAPI generation (title, version, security schemes). |
| `ProxyRestTemplateConfiguration` | controller | Sets up a `RestTemplate` with proxy settings for outbound calls. |
| `TokenAuthenticationRestTemplateConfigurationSpringBoot` | controller | Enables JWT token propagation for backend‑to‑backend communication. |
| `ReportConfigurationComponent` | component | UI component exposing report format options. |
| `LocalStorageSettingsAdapter` | adapter | Persists user‑specific settings in browser local storage. |
| `SettingsAdapterService` | adapter | Provides a unified API for reading/writing configuration across adapters. |
| `TaskApiConfiguration`, `JobApiConfiguration`, `WorkflowApiConfiguration` | service | Angular module configurations for generated REST API clients. |

Configuration values are version‑controlled in the repository and can be overridden at runtime via environment variables or Kubernetes ConfigMaps, ensuring **immutable infrastructure** and **continuous delivery** compliance.

---

*This chapter captures all cross‑cutting concerns of the *uvz* system, providing a clear, diagram‑first view of how security, persistence, error handling, logging, testing, and configuration are woven throughout the architecture.*
