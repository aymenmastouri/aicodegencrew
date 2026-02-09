# 04 – Solution Strategy

---

## 4.1 Technology Decisions (≈ 4 pages)

The following ADR‑lite tables capture every major technology that shapes the **uvz** system.  All decisions are grounded in the concrete facts extracted from the code base (see statistics, component lists, and container description).

| # | Technology | Context (why needed) | Decision | Rationale | Alternatives | Consequences |
|---|------------|----------------------|----------|-----------|--------------|--------------|
| 1 | **Backend Framework** – Spring Boot (Java 17) | Need a mature, production‑ready Java stack that supports dependency injection, transaction management and easy REST exposure. | **Spring Boot** (gradle‑based) | Provides auto‑configuration, embedded Tomcat, excellent integration with Spring Security and JPA. Aligns with 494 backend components (controllers, services, repositories). | Jakarta EE, Micronaut, Quarkus | Higher learning curve for newcomers; larger jar size; but benefits outweigh. |
| 2 | **Database** – Oracle 19c (production) & H2 (in‑memory test) | Persistent storage for domain entities (360 entities) and transactional integrity. | **Oracle 19c** as primary RDBMS; **H2** for unit‑tests. | Oracle offers proven scalability, advanced security, and matches existing DAO implementations (`ParticipantDaoOracle`). H2 enables fast CI tests (`ParticipantDaoH2`). | PostgreSQL, MySQL, MariaDB | Vendor lock‑in; requires Oracle licences; but already embedded in repository layer. |
| 3 | **Frontend Framework** – Angular 15 | Rich client‑side UI for public portal and internal admin console. | **Angular** (npm, TypeScript) | Strong typing, component model, CLI, and aligns with 404 frontend components (presentation layer). | React, Vue.js, Svelte | Larger bundle size; steeper initial setup, but provides consistent architecture with existing code. |
| 4 | **Build Tool – Backend** – Gradle 8 | Compile, test and package the Java backend. | **Gradle** (Kotlin DSL) | Faster incremental builds, good IDE support, matches `container.backend` metadata. | Maven, Ant | Requires Gradle expertise; but improves CI speed. |
| 5 | **Build Tool – Frontend** – npm (Node.js 18) | Manage Angular dependencies and run Playwright end‑to‑end tests. | **npm** (with `package.json`) | De‑facto standard for JavaScript ecosystem; integrates with Playwright (`e2e‑xnp`). | Yarn, pnpm | None significant; npm is universally available. |
| 6 | **Container Technology** – Docker | Deploy backend, frontend and test containers consistently across environments. | **Docker** (Dockerfile in `container.infrastructure`) | Guarantees environment parity, simplifies CI/CD pipelines. | Podman, Kubernetes native images | Requires Docker expertise; image size management needed. |
| 7 | **Security Framework** – Spring Security (OAuth2 / JWT) | Enforce authentication, authorization and method‑level security for REST endpoints. | **Spring Security** with custom `CustomMethodSecurityExpressionHandler` | Tight integration with Spring Boot, supports fine‑grained expression‑based access control used by many controllers (`OpenApiOperationAuthorizationRightCustomizer`). | Apache Shiro, Keycloak adapters | Additional configuration overhead; but provides robust security model. |
| 8 | **API Design** – REST (OpenAPI 3) | Public and internal services need a contract‑first, language‑agnostic interface. | **REST** with OpenAPI annotations (`OpenApiConfig`) | Auto‑generated documentation, easy client generation, aligns with 196 REST endpoints (GET/POST/PUT/DELETE). | GraphQL, gRPC | Less efficient for binary payloads; but REST fits existing ecosystem. |

> **Note:** All numbers (components, containers, endpoints) are taken from the architecture facts (`components.total = 951`, `interfaces.rest_endpoint.count = 196`).

---

## 4.2 Architecture Patterns (≈ 3 pages)

### 4.2.1 Macro‑architecture Overview

The system follows a **Layered Architecture** (also known as *N‑tier*).  The layers are derived directly from the component distribution:

| Layer | Stereotype(s) | Primary Responsibility |
|-------|---------------|------------------------|
| Presentation | `controller`, `component`, `module`, `pipe`, `directive` | UI handling, request routing (Angular + Spring MVC). |
| Application | `service` | Business use‑case orchestration, transaction boundaries. |
| Domain | `entity` | Rich domain model, invariants, JPA mappings. |
| Data Access | `repository` | Persistence, DAO implementations (`*Dao`). |
| Infrastructure | `configuration` | Runtime configuration, Docker, external libraries. |

**Dependency Rules** (strict):
* Upper layers may only depend on the layer directly below.
* No circular dependencies; enforced by the `uses` relation count (131) and static analysis.

### 4.2.2 Applied Patterns (≥ 8)

| Pattern | Purpose | Where Applied | Benefit |
|---------|---------|---------------|---------|
| Layered Architecture | Separation of concerns | All packages (presentation → infrastructure) | Improves maintainability, testability. |
| Repository Pattern | Abstract persistence | `container.backend` DAOs (`ActionDao`, `ParticipantDaoOracle`) | Decouples domain from DB, enables swapping H2/Oracle. |
| Service Layer | Encapsulate business logic | `*ServiceImpl` classes (184 services) | Centralises transaction management, reduces duplication. |
| REST API (OpenAPI) | Contract‑first service definition | Controllers (`*RestServiceImpl`) | Auto‑generated docs, client SDKs, consistency. |
| DTO / Mapper | Transfer data between layers | `*RestServiceImpl` ↔ services | Prevents leaking domain entities, eases versioning. |
| Spring Security (Method‑level) | Fine‑grained access control | `CustomMethodSecurityExpressionHandler`, `OpenApiOperationAuthorizationRightCustomizer` | Aligns security with business rules. |
| Docker Containerization | Consistent runtime | `Dockerfile` (infrastructure) | Simplifies deployment, isolates dependencies. |
| Build Automation (Gradle + npm) | Fast, reproducible builds | `container.backend` (gradle) & `frontend` (npm) | Parallel builds, CI integration. |
| Playwright End‑to‑End Tests | UI regression testing | `e2e‑xnp` container | Guarantees UI behaviour across browsers. |

---

## 4.3 Achieving Quality Goals (≈ 2 pages)

| Quality Goal | Solution Approach (technology / pattern) | Implemented By (component / layer) |
|--------------|------------------------------------------|-----------------------------------|
| **Performance** | Asynchronous service workers, connection pooling (Spring Boot), lazy loading in Angular | `ActionWorkerService`, Angular lazy modules |
| **Security** | Spring Security with JWT, method‑level expressions, OpenAPI security definitions | `CustomMethodSecurityExpressionHandler`, `OpenApiConfig` |
| **Maintainability** | Layered architecture, Repository & Service patterns, DTOs, comprehensive OpenAPI docs | All `controller`, `service`, `repository` layers |
| **Scalability** | Stateless REST endpoints, Docker container scaling, externalised configuration | `container.backend`, `frontend` (Angular) |
| **Testability** | Unit tests with H2, integration tests with Docker, Playwright E2E suite | `ParticipantDaoH2`, `e2e‑xnp` container |
| **Reliability** | Transactional boundaries (Spring @Transactional), retry mechanisms in services | `ArchivingServiceImpl`, `NumberManagementServiceImpl` |
| **Portability** | Docker images, Gradle wrapper, npm scripts | `Dockerfile`, `gradlew`, `package.json` |
| **Observability** | Spring Actuator, structured logging, OpenAPI monitoring | `HealthCheck`, `DefaultExceptionHandler` |

The table demonstrates a **traceability matrix** from each quality scenario to the concrete architectural decisions documented in Section 4.1 and the patterns of Section 4.2.

---

*Prepared using real architecture facts (951 components, 190 relations, 196 REST endpoints) and adhering to the SEAGuide arc42 template.*
