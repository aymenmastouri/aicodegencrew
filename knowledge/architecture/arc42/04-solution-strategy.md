# 04 – Solution Strategy

---

## 4.1 Technology Decisions (≈ 4 pages)

| Technology | Context | Decision | Rationale | Alternatives | Consequences |
|------------|---------|----------|-----------|--------------|--------------|
| **Backend Framework** | Java‑based micro‑services handling core business logic and data persistence. | **Spring Boot 3.x** (with Spring MVC, Spring Data JPA, Spring Security) | Mature ecosystem, auto‑configuration, strong community, seamless integration with Gradle and Docker. Enables rapid development of REST APIs and leverages existing expertise in the team. | Jakarta EE (WildFly), Micronaut, Quarkus | Higher startup time compared to native GraalVM builds, larger jar size, but proven stability and tooling outweighs.
| **Database** | Persistent storage for domain entities (≈ 360 entity components) and transactional operations. | **PostgreSQL 15** (relational) | ACID compliance, rich SQL features, good support for JPA/Hibernate, open‑source, fits existing data model. | MySQL, Oracle, MariaDB | Requires schema migration strategy (Flyway/Liquibase). No vendor lock‑in for core business logic.
| **Frontend** | Single‑page application for user interaction, built with Angular components (≈ 214 presentation components). | **Angular 16** (TypeScript) | Component‑based architecture, strong typing, built‑in routing, RxJS for reactive streams, aligns with existing Angular directives, pipes, and guards. | React, Vue.js, Svelte | Larger bundle size, steeper learning curve, but provides a consistent development model across the UI.
| **Build Tool (Backend)** | Compilation, dependency management, packaging of Java services. | **Gradle 8** (Kotlin DSL) | Incremental builds, rich plugin ecosystem, native Docker image support, aligns with existing `container.backend` Gradle configuration. | Maven, Ant | Requires developers to adopt Kotlin DSL syntax; however, faster builds improve CI/CD throughput.
| **Build Tool (Frontend)** | Asset bundling, linting, testing for Angular and Node.js code. | **npm 9** + **Angular CLI** | Standard for Angular projects, integrates with Playwright end‑to‑end tests (`e2e‑xnp`). | Yarn, pnpm | None significant; npm is universally available.
| **Container Technology** | Deployment of backend, frontend, and test artefacts. | **Docker** (Dockerfile in `container.infrastructure`) | Portable, reproducible environments, aligns with CI pipelines, supports multi‑stage builds for Spring Boot and Angular. | Podman, Kubernetes native images | Requires Docker daemon on build agents; however, Docker is widely supported.
| **Security Framework** | Authentication, authorization, method‑level security for REST endpoints. | **Spring Security 6** (with OAuth2 Resource Server) | Declarative security, integrates with custom `CustomMethodSecurityExpressionHandler`, supports JWT, aligns with existing `TokenAuthenticationRestTemplateConfigurationSpringBoot`. | Apache Shiro, Keycloak adapters | Slightly higher configuration effort, but provides fine‑grained control.
| **API Design** | Public contract for client‑server interaction. | **OpenAPI 3.0** (generated via `springdoc-openapi` and `OpenApiConfig`) | Machine‑readable specification, enables client code generation, Swagger UI for exploration, matches `OpenApiOperationAuthorizationRightCustomizer`. | RAML, GraphQL | Requires maintenance of spec alongside code; however, auto‑generation reduces drift.

### Decision Log (ADR‑lite snippets)

**ADR‑001 – Choose Spring Boot as Backend Framework**
- *Status*: Accepted
- *Context*: Need a robust Java framework for REST services, data access, and security.
- *Decision*: Adopt Spring Boot 3.x.
- *Consequences*: Enables rapid development, but introduces a larger runtime footprint.

**ADR‑002 – Use PostgreSQL for Persistence**
- *Status*: Accepted
- *Context*: Domain model consists of 360 JPA entities.
- *Decision*: PostgreSQL 15.
- *Consequences*: Requires schema migration tooling; provides strong relational capabilities.

*(Additional ADRs for each technology are stored in the repository; the table above summarises the final decisions.)*

---

## 4.2 Architecture Patterns (≈ 3 pages)

### Macro‑Architecture Pattern

The system follows a **Layered (Onion) Architecture**:

- **Presentation Layer** – Angular components, Angular directives, pipes, guards, and the `StaticContentController`.
- **Application Layer** – Spring Boot services (`*ServiceImpl`), orchestrating use‑cases.
- **Domain Layer** – JPA entities (`entity` stereotype) and business rules.
- **Data‑Access Layer** – Repository pattern (`*Dao` components) using Spring Data JPA.
- **Infrastructure Layer** – Docker containers, configuration (`Dockerfile`), external libraries.

**Dependency Rules**: Outer layers may depend only on inner layers; inner layers are independent of outer ones. This rule is enforced by package structure and Gradle module boundaries.

### Applied Patterns Overview

| Pattern | Purpose | Where Applied | Benefit |
|---------|---------|---------------|---------|
| Layered Architecture | Separation of concerns | Entire system (presentation → infrastructure) | Improves maintainability and testability |
| Repository Pattern | Abstract data access | `container.backend` DAOs (e.g., `ActionDao`, `ParticipantDao`) | Decouples domain from persistence technology |
| Service Layer | Encapsulate business use‑cases | `*ServiceImpl` classes (e.g., `BusinessPurposeRestServiceImpl`) | Centralises transaction management |
| DTO / Mapper | Transfer data between layers | REST controllers ↔ services | Prevents leaking domain entities over the wire |
| Exception Handling (ControllerAdvice) | Global error handling | `DefaultExceptionHandler` | Consistent API error responses |
| Method Security (Spring Security) | Fine‑grained authorization | `CustomMethodSecurityExpressionHandler` | Enforces business‑level security rules |
| OpenAPI / Swagger | API documentation | `OpenApiConfig`, `OpenApiOperationAuthorizationRightCustomizer` | Auto‑generated contract, client code generation |
| Scheduler / Asynchronous Jobs | Background processing | `JobRestServiceImpl`, `ReencryptionJobRestServiceImpl` | Improves responsiveness, handles long‑running tasks |
| Interceptor / Filter | Cross‑cutting concerns (logging, tracing) | `interceptor` stereotype components | Centralised request/response handling |
| Guard / Route Guard | UI‑level access control | Angular `guard` component | Prevents unauthorized navigation |

### Pattern Details (selected examples)

#### Repository Pattern
Implemented by 38 DAO components (see Section 4.1). Each DAO extends Spring Data JPA interfaces, providing CRUD operations without boiler‑plate SQL. Example: `ActionDao` manages `Action` entity persistence.

#### Service Layer
184 service components orchestrate domain logic. Example: `NumberManagementRestServiceImpl` coordinates number allocation using `UvzNumberManagerDao` and `UvzNumberSkipManagerDao`.

#### Scheduler
A single `scheduler` component runs periodic jobs (e.g., data cleanup). Integrated via Spring `@Scheduled` annotations.

---

## 4.3 Achieving Quality Goals (≈ 2 pages)

| Quality Goal | Solution Approach | Implemented By |
|--------------|-------------------|----------------|
| **Performance** | Asynchronous job processing, pagination on REST endpoints, connection pooling (HikariCP) | `JobRestServiceImpl`, `*RestServiceImpl` with `Pageable` parameters |
| **Security** | Spring Security with JWT, method‑level expressions, OpenAPI security definitions, Angular route guards | `CustomMethodSecurityExpressionHandler`, `TokenAuthenticationRestTemplateConfigurationSpringBoot`, Angular `guard` |
| **Scalability** | Containerised micro‑services, stateless REST APIs, horizontal scaling via Docker/Kubernetes | Docker images (`container.backend`, `container.frontend`), CI/CD pipelines |
| **Maintainability** | Layered architecture, ADR documentation, code generation for OpenAPI, strict typing in Angular | ADR‑lite tables, `OpenApiConfig`, TypeScript interfaces |
| **Testability** | Unit tests for services, integration tests with Testcontainers, end‑to‑end tests with Playwright (`e2e‑xnp`) | `src/test/java`, Playwright test suite |
| **Availability** | Health‑check endpoints, graceful shutdown, retry mechanisms in HTTP clients | `HealthIndicator` beans, `RestTemplate` configurations |
| **Observability** | Centralised logging (Logback), metrics via Micrometer, tracing with OpenTelemetry | `interceptor` components, `metrics` configuration |
| **Compliance** | OpenAPI spec versioning, API contracts, audit logging in services | `OpenApiOperationAuthorizationRightCustomizer`, audit fields in entities |

### Mapping to Technology Decisions
- **Spring Security** (Tech Decision) directly satisfies *Security*.
- **Docker** enables *Scalability* and *Availability*.
- **Playwright** tests support *Testability*.
- **OpenAPI** drives *Maintainability* and *Compliance*.
- **Gradle** incremental builds improve *Performance* of the CI pipeline.

---

*Prepared according to Capgemini SEAGuide and arc42 standards. All data reflects the current state of the `uvz` system as extracted from the architecture knowledge base.*
