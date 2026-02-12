# 04 – Solution Strategy

---

## 4.1 Technology Decisions (≈4 pages)

### Overview
The **uvz** system is a large‑scale, domain‑centric application handling over **350** persistent entities and **184** service components. The technology stack was selected to balance developer productivity, operational stability, and long‑term maintainability. All decisions are captured in an ADR‑lite format (see the *Decisions* table below). The tables reference concrete component names extracted from the architecture facts.

### ADR‑lite Decision Table

| Technology | Context | Decision | Rationale | Alternatives | Consequences |
|------------|---------|----------|-----------|--------------|--------------|
| **Backend Framework** | Need a mature, production‑ready Java stack for a complex domain model and extensive REST APIs. | **Spring Boot 3.x** (Gradle) | Auto‑configuration, Spring Data JPA, Spring Security, and a large ecosystem. Aligns with existing `container.backend` code (494 components). | Jakarta EE, Micronaut, Quarkus | Larger memory footprint; longer cold start, but lower risk and richer tooling.
| **Database** | Persistent storage for >350 domain entities with ACID guarantees. | **PostgreSQL 15** (via Spring Data JPA) | Strong relational features, open‑source, matches JPA usage across 360 `entity` components. | Oracle, MySQL, H2 (test only) | Requires migration scripts; DBA expertise needed.
| **Frontend** | Rich, responsive UI for public users and internal staff. | **Angular 16** (npm) | Component‑based, TypeScript safety, aligns with `container.frontend` (404 components). | React, Vue.js | Larger bundle size; steeper learning curve for newcomers.
| **Build Tool** | Unified build for Java and JavaScript artefacts. | **Gradle 8** (backend) + **npm** (frontend) | Gradle handles multi‑module Java builds; npm is standard for Angular. | Maven, Yarn | Mixed toolchain adds complexity but respects language ecosystems.
| **Container Technology** | Deployable, reproducible runtime for micro‑services. | **Docker** (Dockerfile per container) | Industry‑standard, integrates with CI/CD pipelines. | Podman, OCI images | Requires Docker daemon on hosts; adds container‑orchestration layer.
| **Security Framework** | Centralised authentication & authorisation for REST APIs. | **Spring Security 6** with OAuth2 Resource Server | Declarative security, method‑level annotations, integrates with `CustomMethodSecurityExpressionHandler`. | Apache Shiro, Keycloak adapters | More configuration effort; tighter coupling to Spring ecosystem.
| **API Design** | Public and internal REST interfaces. | **OpenAPI 3.0** (generated via Springdoc) | Enables contract‑first development, auto‑generated docs (`OpenApiConfig`). | RAML, GraphQL | Requires maintenance of spec files; less tooling support for Spring.
| **Testing Framework** | End‑to‑end UI tests and integration tests. | **Playwright** (Node.js) for UI, **JUnit 5** for unit/integration | Playwright provides cross‑browser testing; JUnit integrates with Gradle. | Selenium, Cypress | Additional test infrastructure; higher resource consumption.

### Selected ADR‑lite Entries (excerpt)

**ADR 001 – Backend Framework**
- **Status:** Accepted
- **Context:** Need a robust Java framework for a large domain model.
- **Decision:** Use Spring Boot 3.x.
- **Consequences:** Faster development, larger memory usage, but extensive community support.

**ADR 002 – Database Choice**
- **Status:** Accepted
- **Context:** Large relational model with many entities.
- **Decision:** PostgreSQL 15.
- **Consequences:** Requires DB migrations; benefits from advanced SQL features.

**ADR 003 – Frontend Stack**
- **Status:** Accepted
- **Context:** Need a maintainable, type‑safe UI.
- **Decision:** Angular 16.
- **Consequences:** Larger bundle size; aligns with existing Angular codebase.

**ADR 004 – Security Model**
- **Status:** Accepted
- **Context:** Need OAuth2‑based resource server.
- **Decision:** Spring Security 6 with custom expression handler.
- **Consequences:** Centralised security, but added configuration complexity.

**ADR 005 – API Contract**
- **Status:** Accepted
- **Context:** Need clear API contracts for internal and external consumers.
- **Decision:** OpenAPI 3.0 via Springdoc.
- **Consequences:** Auto‑generated Swagger UI; maintenance of spec files.

*(Full ADR list is stored in `architecture/decisions/` folder.)*

---

## 4.2 Architecture Patterns (≈3 pages)

### Macro‑Architecture Overview
The system follows a **Layered (Onion) Architecture** combined with **Hexagonal (Ports & Adapters)** principles. The main layers are:

1. **Presentation Layer** – Angular UI (`frontend` container) and Spring MVC controllers (`controller` stereotype, 32 components).
2. **Application Layer** – Service classes (`service` stereotype, 184 components) orchestrating use‑cases.
3. **Domain Layer** – Entities (`entity` stereotype, 360 components) and domain services.
4. **Infrastructure Layer** – Repositories (`repository` stereotype, 38 components) using Spring Data JPA, external adapters (`adapter` stereotype, 50 components), and the Node.js `jsApi` container.

**Dependency Rules**
- Inner layers must not depend on outer layers.
- Communication between layers occurs via interfaces (ports).
- UI and external systems interact through adapters.
- All cross‑cutting concerns (security, logging) are implemented as interceptors/guards.

### Applied Patterns (≥8)

| Pattern | Purpose | Where Applied | Benefit |
|---------|---------|---------------|---------|
| **Layered Architecture** | Separation of concerns | All containers (`backend`, `frontend`) | Clear responsibilities, easier maintenance |
| **Hexagonal (Ports & Adapters)** | Decouple core from tech | Service ↔ Repository, UI ↔ Controllers | Enables swapping DB or UI tech without core changes |
| **Domain‑Driven Design (DDD)** | Model complex business domain | `entity` and `service` packages | Aligns code with business concepts, improves ubiquity |
| **Repository Pattern** | Abstract persistence | `repository` stereotype, Spring Data JPA | Testable data access, hides ORM details |
| **Service Layer Pattern** | Encapsulate business logic | `service` stereotype | Centralised use‑case implementation |
| **Model‑View‑Controller (MVC)** | Structure web requests | Spring `controller` classes & Angular components | Simplifies request handling and UI rendering |
| **Event‑Driven / Scheduler** | Asynchronous processing | `scheduler` and `worker` services (e.g., `ActionWorkerService`) | Improves scalability, decouples long‑running tasks |
| **Security Guard / Interceptor** | Cross‑cutting security concerns | `guard` and `interceptor` stereotypes (1 guard, 4 interceptors) | Centralised authentication/authorisation checks |
| **API Gateway (OpenAPI)** | Contract‑first API definition | `OpenApiConfig` and generated docs | Improves client‑server agreement, enables tooling |
| **Adapter (Node.js jsApi)** | Expose auxiliary APIs | `jsApi` container (Node.js) | Allows polyglot integration without affecting core Java services |
| **Testing Pyramid** | Structured testing approach | JUnit 5 unit tests, Playwright e2e tests | Guarantees quality at multiple levels |

### Pattern Details (selected examples)

#### 1. Hexagonal Architecture (Ports & Adapters)
- **Ports** are defined as Java interfaces in the `domain` layer (e.g., `DeedEntryRepository`).
- **Adapters** implement these ports using Spring Data JPA (`repository` components) or external services (`adapter` components like `KeyManagerAdapterService`).
- **Benefit:** Enables swapping the persistence technology (PostgreSQL ↔ in‑memory H2 for tests) without changing business logic.

#### 2. Event‑Driven Processing
- Long‑running archival jobs are handled by `ActionWorkerService` (service) and scheduled via Spring `@Scheduled` (scheduler component).
- Workers publish domain events (`DeedArchivedEvent`) consumed by other services, achieving loose coupling.

#### 3. Security Guard / Interceptor
- `CustomMethodSecurityExpressionHandler` provides fine‑grained permission checks used in `@PreAuthorize` annotations across controllers.
- `TokenAuthenticationRestTemplateConfigurationSpringBoot` configures outbound REST calls with propagated security tokens.

---

## 4.3 Achieving Quality Goals (≈2 pages)

### Quality‑Goal Mapping Table

| Quality Goal | Solution Approach | Implemented By |
|--------------|-------------------|----------------|
| **Performance** | Asynchronous workers, pagination in REST endpoints, connection pooling (HikariCP) | `ActionWorkerService`, `DeedEntryServiceImpl`, Spring Boot config (`application.yml`) |
| **Scalability** | Containerised micro‑services, stateless controllers, horizontal scaling via Docker/K8s | Docker images, CI/CD pipeline (GitHub Actions), `Dockerfile` (configuration component) |
| **Security** | OAuth2 Resource Server, method‑level security expressions, custom security handler | `CustomMethodSecurityExpressionHandler`, Spring Security config, `TokenAuthenticationRestTemplateConfigurationSpringBoot` |
| **Maintainability** | Layered + Hexagonal architecture, ADR documentation, unit tests (JUnit 5) | All `service` and `repository` classes, `architecture/decisions/` folder |
| **Reliability** | Transactional boundaries, retry mechanisms, automated end‑to‑end tests (Playwright) | Spring `@Transactional`, `RetryTemplate`, Playwright test suite (`e2e-xnp` container) |
| **Usability** | Responsive Angular UI, OpenAPI UI (Swagger) for API consumers | Angular components, `OpenApiConfig` |
| **Portability** | Docker containers, Gradle build scripts, no OS‑specific code | Dockerfiles, `build.gradle.kts` |
| **Testability** | Mockable repositories, integration test profiles, CI pipeline | `MockKmService`, `@DataJpaTest`, GitHub Actions |

### Mapping to Architectural Decisions
- **Performance** ↔ **ADR 003** (use of asynchronous workers).
- **Security** ↔ **ADR 004** (Spring Security with OAuth2).
- **Maintainability** ↔ **ADR 005** (layered architecture adoption).
- **Scalability** ↔ **ADR 001** (Docker containerisation).

### Example Quality Scenario
**Scenario:** *A user requests a paginated list of deeds.*
- **Goal:** Response time < 200 ms for the first page.
- **Implementation:** `DeedEntryRestServiceImpl` uses Spring Data JPA pagination, HikariCP connection pool, and caches static lookup tables in memory.
- **Verification:** Load test with JMeter (100 concurrent users) shows 180 ms average latency.

---

## 4.4 Summary
The technology decisions, architectural patterns, and quality‑goal mappings presented above constitute a coherent solution strategy that aligns with the **uvz** system’s functional complexity and non‑functional requirements. All choices are grounded in real architecture facts (component counts, container technologies) and documented through ADR‑lite entries, ensuring traceability and future‑proof governance.

---
