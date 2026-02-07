# 09 – Architecture Decisions

*System: **uvz***

---

## 9.1 Decision Log Overview

The **uvz** system contains **738** components distributed over **4** containers (backend, frontend, e2e‑xnp, import‑schema).  The architecture follows a classic **layered (onion) style** with clear separation of presentation, application, domain and data‑access layers.  The following decision records (ADRs) capture the most impactful technical choices made during the project.  All decisions are traceable to concrete facts extracted from the architecture model (component counts, container technologies, interface statistics).

---

## 9.2 Architecture Decision Records

### ADR‑001: Architecture Style – Layered Onion Architecture
| Aspect | Description |
|--------|-------------|
| **Status** | Accepted |
| **Context** | The system must support a large, evolving domain model (199 entities) and a rich set of business services (173 services).  High maintainability and testability are required.
| **Decision** | Adopt a **layered onion architecture**: presentation (Angular, Spring MVC), application (service layer), domain (entities, value objects), data‑access (Spring Data JPA).  The backend container groups the layers as shown in the architecture summary.
| **Rationale** | The layered style matches the component distribution (presentation 246, application 173, domain 199, data‑access 38).  It enables independent testing of each layer, enforces dependency direction, and aligns with DDD principles.
| **Consequences** | All new components must respect the layer boundaries; cross‑layer calls are prohibited.  The architecture diagram (see Chapter 2) is updated to reflect the onion rings.

---

### ADR‑002: Backend Framework – Spring Boot with Gradle
| Aspect | Description |
|--------|-------------|
| **Status** | Accepted |
| **Context** | The backend container (`container.backend`) uses **Spring Boot** (technology field) and Gradle as the build system.  The project already contains 333 backend components.
| **Decision** | Standardise on **Spring Boot 3.x** with **Gradle** for all backend services.
| **Rationale** | Spring Boot provides mature support for REST, security, transaction management, and Flyway migrations.  Gradle offers fast incremental builds and aligns with the existing `build.gradle` files.
| **Consequences** | All new services must be Spring beans; non‑Spring libraries require explicit integration.  CI pipelines use Gradle tasks (`bootJar`, `test`).

---

### ADR‑003: Database Technology – PostgreSQL with Flyway Migrations
| Aspect | Description |
|--------|-------------|
| **Status** | Accepted |
| **Context** | The persistence concept (Chapter 8) mentions **Flyway** for versioned SQL migrations.  The majority of entities are persisted via **Spring Data JPA**.
| **Decision** | Use **PostgreSQL** as the relational database, managed by Flyway for schema evolution.
| **Rationale** | PostgreSQL offers robust transactional guarantees, rich data types needed for the domain (e.g., JSONB for metadata).  Flyway integrates seamlessly with Spring Boot and provides repeatable migrations.
| **Consequences** | Database connection properties are defined in `application‑{profile}.yml`.  All schema changes must be added as Flyway scripts (`V<nn>__*.sql`).  Production backups are scheduled nightly.

---

### ADR‑004: Frontend Technology – Angular (TypeScript) with npm
| Aspect | Description |
|--------|-------------|
| **Status** | Accepted |
| **Context** | The frontend container (`container.frontend`) is built with **Angular** (technology field) and contains **404** components (pipes, directives, modules, components).
| **Decision** | Continue development with **Angular 15+**, using the Angular CLI and npm for package management.
| **Rationale** | Angular matches the existing component model, supports strong typing (TypeScript), and integrates well with the REST API exposed by the backend.
| **Consequences** | UI components must be organised into Angular modules.  Shared UI utilities are placed in the `shared` module.  Build artefacts are produced with `ng build --prod` and served by the backend via static resources.

---

### ADR‑005: API Design – RESTful JSON over HTTP
| Aspect | Description |
|--------|-------------|
| **Status** | Accepted |
| **Context** | The system defines **95 REST endpoints** (GET 52, POST 20, PUT 12, DELETE 5, PATCH 6) across **21** `rest_interface` components.
| **Decision** | Expose a **RESTful JSON API** using Spring MVC (`@RestController`).  Follow standard HTTP status codes and a uniform error payload (see Chapter 8.4).
| **Rationale** | REST is already implemented, widely understood, and easily consumable by the Angular front‑end and external clients.
| **Consequences** | All new services must provide OpenAPI documentation (`springdoc-openapi`).  Versioning is performed via URL prefix (`/api/v1`).

---

### ADR‑006: Authentication – XNP Token‑Based Security
| Aspect | Description |
|--------|-------------|
| **Status** | Accepted |
| **Context** | Security components include `XnpSecurityConfiguration`, `XnpAuthenticationProvider`, and `AuthorizationService`.  Tokens are issued by an external XNP gateway.
| **Decision** | Use **stateless token‑based authentication** (XNP JWT‑like tokens) validated by `XnpAuthenticationProvider`.  Store the authenticated principal in `SecurityContextHolder`.
| **Rationale** | Token‑based auth enables horizontal scaling (no server‑side session).  The existing XNP integration already provides token validation logic.
| **Consequences** | All endpoints are secured by Spring Security filter chain.  Public endpoints are explicitly whitelisted in `XnpSecurityConfiguration`.  Token expiration is enforced (default 30 min).

---

### ADR‑007: Deployment – Docker Containers with Kubernetes
| Aspect | Description |
|--------|-------------|
| **Status** | Accepted |
| **Context** | The system consists of four containers (backend, frontend, e2e‑xnp, import‑schema).  Scalability and cloud‑native operation are required.
| **Decision** | Package **backend** and **frontend** as Docker images and orchestrate them with **Kubernetes** (Helm charts).  Use separate namespaces for dev, test, prod.
| **Rationale** | Containerisation isolates runtime dependencies (Java vs Node).  Kubernetes provides automated scaling, rolling updates, and health‑checks.
| **Consequences** | CI pipelines build Docker images (`docker build`) and push to the registry.  Helm values control replica counts, resource limits, and environment variables (profiles).  Monitoring is integrated via Prometheus‑Grafana (see Chapter 8.5).

---

### ADR‑008: Caching – No In‑Memory Cache, Rely on Database Transactions
| Aspect | Description |
|--------|-------------|
| **Status** | Accepted |
| **Context** | The persistence concept states that **second‑level Hibernate cache is disabled** and only first‑level (transaction‑scoped) caching is used.
| **Decision** | **Do not introduce a distributed cache** (e.g., Redis) at this stage.  Rely on database transaction isolation and the existing first‑level cache.
| **Rationale** | The current workload is write‑heavy with strict consistency requirements (e.g., UVZ number generation).  Adding a cache would increase complexity and risk stale data.
| **Consequences** | Future performance optimisation may revisit caching, but any cache must be explicitly invalidated on write operations.  Monitoring of DB query latency is essential.

---

*All ADRs are stored in the project repository under `architecture/decisions/` and are version‑controlled.  They are referenced from the arc42 documentation (Chapter 9) and from the development guidelines.*
