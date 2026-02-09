# 04 – Solution Strategy

---

## 4.1 Technology Decisions (≈4 pages)

| # | Technology | Context | Decision | Rationale | Alternatives | Consequences |
|---|------------|---------|----------|-----------|--------------|--------------|
| 1 | **Backend Framework** | Java‑based micro‑services handling business logic and data persistence. | **Spring Boot 3.x** (Gradle build) | Mature ecosystem, auto‑configuration, excellent integration with JPA, Spring Security, and Docker. Reduces boilerplate and speeds up development. | Jakarta EE (WildFly), Micronaut, Quarkus | Higher memory footprint than lightweight frameworks; requires JVM tuning. |
| 2 | **Database** | Persistent storage for domain entities (≈360) and transactional operations. | **Oracle 19c (production)** + **H2 (in‑memory for tests)** | Oracle provides robust ACID guarantees, advanced indexing, and enterprise support. H2 enables fast unit/integration tests without external DB. | PostgreSQL, MySQL, MariaDB | Vendor lock‑in to Oracle; need separate migration scripts for H2 vs Oracle. |
| 3 | **Frontend Framework** | Rich client‑side UI for user interaction, built with TypeScript. | **Angular 16** (npm) | Strong typing, component‑based architecture, built‑in routing and forms, aligns with enterprise standards. | React, Vue.js, Svelte | Larger bundle size; steeper learning curve for newcomers. |
| 4 | **Build Tool (Backend)** | Compilation, packaging and dependency management for Java code. | **Gradle Kotlin DSL** | Faster incremental builds than Maven, concise DSL, native support for Spring Boot plugins. | Maven, Ant | Requires developers to learn Kotlin DSL syntax. |
| 5 | **Build Tool (Frontend)** | Asset bundling, linting and test execution for Angular. | **npm + Angular CLI** | Standard for Angular projects, integrates with Webpack, easy CI configuration. | Yarn, pnpm | npm ecosystem can be slower for large monorepos. |
| 6 | **Container Technology** | Packaging and deployment of runtime artefacts. | **Docker** (Dockerfile in `container.infrastructure`) | Consistent environment across dev, test and prod; simplifies Kubernetes deployment. | Podman, Buildah | Requires Docker daemon; image size optimisation needed. |
| 7 | **Security Framework** | Authentication, authorization and request filtering. | **Spring Security 6** (backend) + **AuthGuard / Interceptors** (frontend) | Declarative security, method‑level annotations, integrates with JWT/OAuth2. Front‑end guard enforces route protection. | Apache Shiro, custom filters | Additional configuration overhead; need to keep token handling in sync between layers. |
| 8 | **API Design** | Public contract for client‑server interaction. | **RESTful JSON API** (Spring MVC, OpenAPI 3) | Wide adoption, easy to consume from Angular, tooling for documentation (Swagger UI). | GraphQL, gRPC | Less efficient for high‑frequency, low‑latency calls; versioning must be managed. |

### Supporting Evidence
- **Backend container** `container.backend` runs Spring Boot (Gradle) and hosts 494 components, distributed across presentation, application, data‑access and domain layers (see architecture summary). 
- **Frontend container** `container.frontend` runs Angular (npm) with 404 components, mainly presentation and application logic. 
- **Repository layer** consists of 38 `@Repository` components (e.g., `ParticipantDaoOracle`, `ParticipantDaoH2`) indicating dual‑database strategy. 
- **Cross‑cutting concerns** are implemented via 4 interceptors (`RateLimitingInterceptor`, `AuthenticationHttpInterceptor`, `HttpErrorInterceptor`, `BusyIndicatorInterceptor`) and a single `AuthGuard` for route protection. 
- **Configuration** is represented by a single Dockerfile component, confirming Docker as the container technology.

---

## 4.2 Architecture Patterns (≈3 pages)

### Macro‑Architecture Pattern
| Pattern | Layer Responsibilities | Dependency Rules |
|---------|------------------------|------------------|
| **Layered Architecture** | Presentation (Angular components, pipes, directives), Application (Spring services), Domain (entities, value objects), Data‑Access (repositories) | Upper layers may only depend on immediate lower layer; no upward dependencies. |
| **Repository Pattern** | Encapsulates data‑access logic behind `*Dao` interfaces. | Services depend on repositories; repositories depend on JPA/Hibernate. |
| **Service Layer** | Business use‑case orchestration (`*Service` classes). | Controllers call services; services call repositories. |
| **Model‑View‑Controller (MVC)** | Controllers (`*Controller`) expose REST endpoints, delegate to services, return DTOs. | Controllers depend on services; no direct repository access. |
| **Interceptor / Guard Pattern** | Cross‑cutting concerns (logging, rate‑limiting, authentication) via Spring interceptors and Angular guards. | Interceptors are wired globally; guards protect route activation. |
| **Scheduler Pattern** | Background jobs (`*Scheduler` component) for periodic tasks. | Schedulers invoke services; isolated from request flow. |
| **Configuration as Code** | Dockerfile and Gradle scripts define runtime environment. | Build artefacts are immutable; deployment consumes these artefacts. |
| **API‑First / OpenAPI** | Contract‑first design, auto‑generated Swagger UI. | API definitions drive controller signatures and client stubs. |

### Applied Patterns Table
| Pattern | Purpose | Where Applied | Benefit |
|---------|---------|---------------|---------|
| Layered Architecture | Separation of concerns | Entire system (presentation → data‑access) | Improves maintainability and testability |
| Repository Pattern | Abstract persistence | `container.backend` repositories (`ActionDao`, `ParticipantDaoOracle`, …) | Enables swapping DB implementations (Oracle ↔ H2) |
| Service Layer | Encapsulate business rules | `*Service` components (184) | Centralises logic, reduces duplication |
| MVC | Structure request handling | Controllers (32) exposing REST endpoints (196) | Clear contract, easier client integration |
| Interceptor | Cross‑cutting concerns | `RateLimitingInterceptor`, `AuthenticationHttpInterceptor` (backend) and Angular equivalents | Consistent handling of security, logging, error handling |
| Guard | Route protection | `AuthGuard` (frontend) | Prevents unauthorized UI navigation |
| Scheduler | Periodic background processing | `*Scheduler` (1) | Enables asynchronous batch jobs |
| Configuration as Code | Environment reproducibility | Dockerfile (infrastructure) | Simplifies CI/CD and scaling |
| OpenAPI (REST) | API documentation & client generation | All REST controllers | Improves consumer experience, reduces integration errors |

---

## 4.3 Achieving Quality Goals (≈2 pages)

| Quality Goal | Solution Approach | Implemented By |
|--------------|------------------|----------------|
| **Performance** | Asynchronous request handling, connection pooling, caching via Spring Cache, lazy loading of Angular modules. | `*Service` (async methods), `RateLimitingInterceptor`, Angular lazy‑loaded routes |
| **Security** | Spring Security with JWT, method‑level `@PreAuthorize`, Angular `AuthGuard` and `AuthenticationHttpInterceptor`. | `SecurityConfig`, `AuthGuard`, `AuthenticationHttpInterceptor` |
| **Scalability** | Docker containerisation, stateless services, horizontal scaling via Kubernetes (not shown but implied by Docker). | Dockerfile, CI pipeline (Gradle/NPM) |
| **Maintainability** | Layered architecture, ADR‑lite decision records, clear package separation, extensive unit tests (Playwright e2e). | ADR tables (this chapter), `*Service`, `*Repository` |
| **Testability** | In‑memory H2 database for unit tests, Playwright end‑to‑end suite (`e2e‑xnp` container), mockable service interfaces. | `ParticipantDaoH2`, `e2e‑xnp` (Playwright), `*Service` interfaces |
| **Reliability** | Transactional boundaries via Spring `@Transactional`, retry mechanisms in interceptors, background job scheduling. | `*Repository` (transactional), `*Scheduler`, `BusyIndicatorInterceptor` |
| **Portability** | Java 17, Gradle, Docker, Angular CLI – all platform‑agnostic. | Build scripts, Dockerfile |
| **Observability** | Centralised logging (interceptors), metrics via Spring Actuator, Angular error handling. | `HttpErrorInterceptor`, `RateLimitingInterceptor`, Actuator endpoints |

### Narrative
The chosen technology stack directly supports the defined quality goals. Spring Boot’s mature ecosystem provides built‑in support for security, transaction management and observability, fulfilling **Security**, **Reliability**, and **Observability**. The dual‑database strategy (Oracle for production, H2 for tests) enables fast, reliable unit testing, contributing to **Testability** and **Maintainability**. Docker containerisation, combined with stateless service design, ensures the system can be scaled horizontally to meet **Scalability** and **Performance** targets. Front‑end Angular guards and interceptors mirror backend security controls, delivering a consistent security posture across the stack.

---

*Prepared according to Capgemini SEAGuide and arc42 standards.*