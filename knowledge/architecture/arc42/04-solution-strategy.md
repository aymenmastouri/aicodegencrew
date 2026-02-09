# 04 Solution Strategy

## 4.1 Technology Decisions

| Technology | Context | Decision | Rationale | Alternatives | Consequences |
|------------|---------|----------|-----------|--------------|--------------|
| **Backend Framework**<br>Spring Boot (Java 17) | Need a mature, production‑ready Java framework that supports rapid development, dependency injection, and easy integration with data access and security. | Adopt **Spring Boot** as the primary backend framework. | Provides auto‑configuration, embedded servlet container, extensive ecosystem (Spring Data, Spring Security, Spring MVC). Aligns with existing Java/Gradle codebase and developer expertise. | Jakarta EE (WildFly), Micronaut, Quarkus | Locks the stack to the Spring ecosystem; requires Spring‑specific knowledge; larger runtime footprint.
| **Database**<br>H2 (dev) & Oracle 19c (prod) | Persist domain entities (360) and support transactional operations for deed registry. | Use **H2** in‑memory for unit/integration tests and **Oracle 19c** for production. | H2 offers fast, zero‑maintenance testing; Oracle provides proven scalability, ACID compliance, and advanced SQL features required by legal domain. | PostgreSQL, MySQL, MariaDB | Dual‑dialect maintenance; need migration scripts for schema compatibility.
| **Frontend**<br>Angular 15 | Provide a rich, component‑based UI for public portal and internal tools. | Choose **Angular** as the SPA framework. | Strong typing with TypeScript, built‑in routing, CLI, and large community. Matches existing frontend component count (404). | React, Vue.js, Svelte | Larger bundle size; steeper learning curve for developers unfamiliar with Angular.
| **Build Tool (Backend)**<br>Gradle 8 | Compile, test, and package Java sources. | Use **Gradle** with Kotlin DSL. | Incremental builds, rich plugin ecosystem, native support for Spring Boot. | Maven, Ant | Requires Gradle expertise; build scripts may be less declarative than Maven.
| **Build Tool (Frontend)**<br>npm + Angular CLI | Manage JavaScript/TypeScript dependencies and build assets. | Use **npm** together with **Angular CLI**. | Standard for Angular projects, easy script configuration, wide ecosystem. | Yarn, pnpm | npm lockfile may be larger; less deterministic than Yarn PnP.
| **Container Technology**<br>Docker | Deploy backend, frontend, and test containers consistently across environments. | Containerise each module with **Docker** images (Spring Boot JAR, Angular static files, Playwright tests). | Guarantees environment parity, simplifies CI/CD, supports Kubernetes later. | Podman, OCI runtime, direct VM images | Adds container orchestration overhead; Dockerfile maintenance required.
| **Security Framework**<br>Spring Security 5 | Enforce authentication, authorization, and method‑level security across REST endpoints. | Integrate **Spring Security** with custom expression handler and token authentication. | Mature, integrates with Spring Boot, supports OAuth2/JWT, method security. | Apache Shiro, Keycloak (as external IdP) | Increases configuration complexity; developers must understand Spring Security concepts.
| **API Design**<br>REST + OpenAPI 3.0 | Expose domain services to external consumers and internal UI. | Design **RESTful** APIs documented with **OpenAPI** (via `OpenApiConfig`). | Enables contract‑first development, auto‑generated client SDKs, Swagger UI for testing. | GraphQL, gRPC | REST may be less efficient for high‑frequency, low‑latency calls; requires versioning strategy.

## 4.2 Architecture Patterns

### Macro‑Architecture Pattern
The system follows a **Layered (Onion) Architecture** combined with **Domain‑Driven Design (DDD)** bounded contexts. The layers are:

1. **Presentation** – Angular SPA and Spring MVC controllers.
2. **Application** – Service layer (`@Service` beans) orchestrating use‑cases.
3. **Domain** – Rich JPA entities (`@Entity`) and domain logic.
4. **Data Access** – Repository/DAO pattern (`JpaRepository`, custom DAOs).
5. **Infrastructure** – Configuration, security, Docker, external adapters.

**Dependency Rules**
- Outer layers may depend only on inner layers.
- No direct access from Presentation to Data Access.
- All cross‑cutting concerns (security, logging) are injected via Spring AOP.

### Applied Patterns
| Pattern | Purpose | Where Applied | Benefit |
|---------|---------|---------------|---------|
| **Layered Architecture** | Separate concerns by technical responsibility | Entire backend (`controller → service → repository → entity`) | Improves maintainability and testability |
| **Repository (DAO) Pattern** | Abstract persistence operations | `*Dao` classes (e.g., `ActionDao`, `ParticipantDaoOracle`) | Decouples domain from DB, enables swapping H2/Oracle |
| **Service Layer** | Encapsulate business use‑cases | `*ServiceImpl` classes (e.g., `DeedEntryRestServiceImpl`) | Centralises transaction management |
| **Controller (MVC) Pattern** | Expose HTTP endpoints | `*RestServiceImpl`, `StaticContentController` | Clear API contract, leverages Spring MVC |
| **Configuration Pattern** | Externalise environment‑specific settings | `Dockerfile`, `ProxyRestTemplateConfiguration` | Simplifies deployment across environments |
| **Security Expression Handler** | Fine‑grained method security | `CustomMethodSecurityExpressionHandler` | Enables domain‑specific authorization rules |
| **OpenAPI / Swagger** | API documentation & contract | `OpenApiConfig`, `OpenApiOperationAuthorizationRightCustomizer` | Auto‑generated docs, client SDKs |
| **Scheduler / Job Pattern** | Background processing | `JobRestServiceImpl`, `ReencryptionJobRestServiceImpl` | Handles long‑running tasks, improves responsiveness |
| **Interceptor Pattern** | Cross‑cutting concerns (logging, metrics) | `*Interceptor` beans | Centralised handling without polluting business code |
| **Factory / Builder** | Complex object creation (e.g., DTOs) | Service layer utilities | Reduces constructor overload, improves readability |

## 4.3 Achieving Quality Goals

| Quality Goal | Solution Approach | Implemented By |
|--------------|-------------------|----------------|
| **Performance** | Asynchronous REST endpoints, connection pooling, Oracle indexing, caching of static Angular assets | Spring Boot `@Async`, HikariCP, Angular Service Workers |
| **Security** | Spring Security with JWT, method‑level security, custom expression handler, HTTPS enforced in Docker images | `CustomMethodSecurityExpressionHandler`, `TokenAuthenticationRestTemplateConfigurationSpringBoot` |
| **Maintainability** | Layered architecture, repository pattern, extensive unit tests, Gradle incremental builds | Service & Repository classes, Gradle `test` task |
| **Scalability** | Containerised deployment, stateless services, Oracle RAC support, horizontal scaling of Angular static files via CDN | Dockerfiles, Kubernetes readiness probes (future), Oracle RAC configuration |
| **Testability** | In‑memory H2 for unit tests, Playwright end‑to‑end tests, mock repositories, CI pipeline with Docker | `e2e-xnp` Playwright suite, JUnit tests in `container.backend` |
| **Reliability** | Transactional boundaries in service layer, retry mechanisms, database backups, Docker health checks | Spring `@Transactional`, Spring Retry, Docker `HEALTHCHECK` |
| **Usability** | Responsive Angular UI, OpenAPI UI for developers, clear error handling via `DefaultExceptionHandler` | Angular Material, Swagger UI, `DefaultExceptionHandler` |
| **Portability** | Docker containers, Gradle wrapper, npm scripts, no OS‑specific dependencies | `Dockerfile`, `gradlew`, `package.json` |

---

*All tables reflect the actual components, containers and relations extracted from the code base (951 components, 190 relations). The decisions are grounded in concrete evidence from the architecture facts and the observed technology stack.*
