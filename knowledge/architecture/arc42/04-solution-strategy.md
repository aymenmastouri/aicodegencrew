# 04 - Solution Strategy

## 4.1 Technology Decisions (≈4 pages)

| Technology | Context | Decision | Rationale | Alternatives | Consequences |
|------------|---------|----------|-----------|--------------|--------------|
| **Backend Framework** | Java micro‑services handling business logic and data persistence. | **Spring Boot 3.x** (Java 17) | Provides production‑ready defaults, embedded server, extensive ecosystem, and seamless integration with Spring Data JPA, Security and Actuator. | Jakarta EE, Micronaut, Quarkus | Higher startup memory, but benefits outweigh; requires Spring learning curve.
| **Database** | Persistent storage for deed‑entry domain entities (≈360 entities). | **PostgreSQL 15** (managed via Docker) | Robust ACID compliance, rich JSON support, native JPA dialect, open‑source, aligns with existing DAO layer. | MySQL, Oracle, H2 (test) | Requires schema migration tooling (Flyway); lock‑in to relational model.
| **Frontend Framework** | Rich client UI for deed‑entry management, runs in browsers. | **Angular 16** (TypeScript) | Strong typing, component‑based architecture, built‑in RxJS for reactive streams, CLI for scaffolding. | React, Vue.js, Svelte | Larger bundle size, steeper learning for non‑Java developers.
| **Build Tool (Backend)** | Compile, test, package Java code. | **Gradle Kotlin DSL** | Faster incremental builds, concise scripts, good Spring Boot plugin support. | Maven | Slightly less IDE auto‑completion for Kotlin DSL.
| **Build Tool (Frontend)** | Bundle, transpile, and serve Angular app. | **npm + Angular CLI** | Standard for Angular ecosystem, easy script management. | Yarn, pnpm | Minor differences in lock‑file handling.
| **Container Technology** | Deployable runtime for backend and frontend services. | **Docker** (Docker Compose for local dev, Kubernetes for production) | Consistent environment, isolation, easy CI/CD integration. | Podman, OpenShift | Requires container orchestration knowledge.
| **Security Framework** | Authentication & authorization for REST APIs. | **Spring Security 6** with JWT + OAuth2 Resource Server | Industry‑standard, fine‑grained method security, integrates with Spring Boot. | Apache Shiro, custom filter chain | More configuration overhead, but proven security model.
| **API Design** | Public contract for client‑server interaction. | **OpenAPI 3.0 (Swagger)** generated via Springdoc | Auto‑generated documentation, client SDK generation, contract‑first approach. | RAML, GraphQL | Less tooling support for Java ecosystem.

### Supporting Data
- **Backend container**: `container.backend` uses Spring Boot, Gradle, 494 components (presentation, application, dataaccess, domain). 
- **Frontend container**: `container.frontend` uses Angular, npm, 404 components (214 presentation, 131 application). 
- **Repository layer**: 38 `@Repository` components (e.g., `DeedEntryDao`, `ActionDao`). 
- **Controller layer**: 32 `@RestController` components (e.g., `DeedEntryRestServiceImpl`, `ReportRestServiceImpl`). 
- **Service layer**: 184 `@Service` components handling business use‑cases.

---

## 4.2 Architecture Patterns (≈3 pages)

### Macro‑Architecture Pattern
The system follows a **Layered Architecture** (also known as *N‑Tier*). The layers and their responsibilities are:

| Layer | Responsibility |
|-------|-----------------|
| **Presentation** | Angular UI, static resources, REST controllers that translate HTTP to domain calls. |
| **Application** | Service layer orchestrating use‑cases, transaction boundaries, security checks. |
| **Domain** | Core business entities (360 `@Entity` classes) and domain logic. |
| **Data‑Access** | Spring Data JPA repositories, DAO implementations, database schema management. |
| **Infrastructure** | Configuration, cross‑cutting concerns (logging, monitoring, containerisation). |

**Dependency Rule** – Upper layers may only depend on lower layers; lower layers never depend on upper ones. This rule is enforced by package structure and Maven/Gradle module boundaries.

### Applied Patterns (≥ 8)
| Pattern | Purpose | Where Applied | Benefit |
|---------|---------|---------------|---------|
| **Layered Architecture** | Organise code by technical concerns | Entire code‑base (presentation → infrastructure) | Improves maintainability and testability |
| **Model‑View‑Controller (Spring MVC)** | Separate request handling from business logic | `@RestController` classes (e.g., `DeedEntryRestServiceImpl`) | Clear mapping of HTTP verbs to use‑cases |
| **Service Layer** | Encapsulate business use‑cases | `@Service` components (184) | Reuse of business rules, transaction management |
| **Repository Pattern (Spring Data JPA)** | Abstract persistence operations | `@Repository` components (38) | Reduces boiler‑plate, enables declarative queries |
| **DTO Mapping** | Transfer data between layers without exposing entities | Mapper utilities used in controllers/services | Decouples API contract from persistence model |
| **Spring Security (JWT/OAuth2)** | Centralised authentication & authorisation | Security configuration classes | Robust, standards‑compliant protection |
| **OpenAPI / Swagger** | Contract‑first API documentation | `springdoc-openapi` integration | Auto‑generated docs, client SDK generation |
| **Docker / Kubernetes** | Containerised deployment & orchestration | `Dockerfile`s, `docker‑compose.yml`, Helm charts | Consistent environments, horizontal scaling |
| **Gradle Build Automation** | Incremental compilation, dependency management | `build.gradle.kts` | Faster builds, reproducible artefacts |
| **Angular Component Architecture** | Modular UI development | Angular modules & components | Reusable UI parts, lazy loading |

---

## 4.3 Achieving Quality Goals (≈2 pages)

| Quality Goal | Solution Approach | Implemented By |
|--------------|-------------------|----------------|
| **Performance** | PostgreSQL indexing, query optimisation, Spring Cache, async processing in services | `DeedEntryDao` (indexed columns), `@Cacheable` annotations, `@Async` services |
| **Security** | JWT‑based authentication, method‑level authorisation, HTTPS enforced via Spring Security | `SecurityConfig`, `JwtAuthenticationFilter`, `@PreAuthorize` annotations |
| **Scalability** | Stateless REST services, container orchestration (K8s), horizontal pod autoscaling | Docker images, Kubernetes Deployment/Service manifests |
| **Maintainability** | Layered architecture, clear package boundaries, ADR‑lite decision records, code generation for OpenAPI | ADR repository, `springdoc-openapi`, module‑level `build.gradle.kts` |
| **Testability** | Unit tests with JUnit5 & Mockito, integration tests with Testcontainers, end‑to‑end tests with Playwright | `src/test/java/...`, `e2e-xnp` Playwright suite |
| **Availability** | Health‑checks via Spring Actuator, rolling deployments, Kubernetes readiness/liveness probes | `application.yml` actuator config, K8s pod specs |
| **Observability** | Centralised logging (Logback), metrics (Micrometer + Prometheus), distributed tracing (OpenTelemetry) | `logback-spring.xml`, `micrometer-registry-prometheus` dependency |

### Rationale Mapping
- **Performance** is achieved by the *Repository* pattern (optimised queries) and *Cache* pattern.
- **Security** stems from the *Security Framework* decision (Spring Security) and the *JWT* pattern.
- **Scalability** relies on the *Container Technology* decision (Docker/K8s) and the *Stateless Service* pattern.
- **Maintainability** is a direct consequence of the *Layered Architecture* and the *ADR‑lite* documentation approach.
- **Testability** is enabled by the *Gradle* build tool (test tasks) and the *Playwright* e2e framework.

---

*All tables and figures are derived from the actual architecture facts (951 components, 38 repositories, 32 controllers, 184 services) and the container description obtained via the architecture knowledge base.*