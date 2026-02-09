# 02 – Architecture Constraints

## 2.1 Technical Constraints (≈ 3 pages)

### 2.1.1 Programming Language
| Constraint | Background | Impact on Architecture | Consequences |
|------------|------------|------------------------|--------------|
| **Java 17** (backend) | All backend services are built with Java 17 to leverage modern language features and long‑term support. | Enforces JVM‑based deployment, limits use of native libraries, requires Gradle build system. | Teams must maintain Java expertise; any non‑JVM component must be isolated (e.g., Node.js API). |
| **TypeScript 5** (frontend) | Angular front‑end is written in TypeScript for static typing and tooling integration. | Front‑end compiled to JavaScript, runs in browsers; requires npm build pipeline. | Requires separate linting and test setup; cannot reuse Java libraries directly. |
| **JavaScript (Node.js)** | The `jsApi` library provides lightweight utilities for the front‑end. | Runs on Node.js runtime, bundled with the Angular build. | Adds a second runtime to the CI pipeline; version alignment must be managed. |

### 2.1.2 Framework
| Constraint | Background | Impact on Architecture | Consequences |
|------------|------------|------------------------|--------------|
| **Spring Boot 3.x** (backend) | Provides convention‑over‑configuration, embedded Tomcat, and extensive ecosystem. | All REST controllers, services and repositories are Spring beans; enables auto‑configuration. | Tight coupling to Spring ecosystem; migration to non‑Spring stack would be costly. |
| **Angular 15+** (frontend) | Component‑based UI framework with RxJS for reactive streams. | UI modules are organized in Angular packages; routing handled by Angular router. | Requires Angular CLI for builds; limits use of alternative front‑end frameworks. |
| **Playwright 1.x** (e2e‑tests) | End‑to‑end testing framework for UI validation. | Test suite runs in a separate container (`e2e‑xnp`). | Adds a dedicated test infrastructure; test failures do not affect production containers. |
| **Node.js (npm)** (jsApi) | Simple JavaScript runtime for utility scripts used by the front‑end. | Bundled as part of the `frontend/src/jsApi` module. | Separate dependency management (package.json) required. |

### 2.1.3 Database
| Constraint | Background | Impact on Architecture | Consequences |
|------------|------------|------------------------|--------------|
| **Oracle 19c** (production) | Core transactional data store for the UVZ system. | Repositories such as `ParticipantDaoOracle` use Oracle‑specific dialects. | Requires Oracle driver, licensing, and DBA support. |
| **H2 (in‑memory)** (tests) | Lightweight DB for unit and integration tests. | Test repositories like `ParticipantDaoH2` switch to H2 via Spring profiles. | Test data reset on each run; not suitable for performance testing. |
| **JPA / Hibernate** | ORM layer abstracting DB access. | Entity classes (e.g., `RestrictedDeedEntryEntity`) map to tables; enables repository pattern. | ORM overhead; complex queries may need native SQL. |

### 2.1.4 Infrastructure
| Constraint | Background | Impact on Architecture | Consequences |
|------------|------------|------------------------|--------------|
| **Docker** (containerisation) | All runtime components are packaged as Docker images. | Deployment uses Docker Compose / Kubernetes; container IDs (`container.backend`, `container.frontend`, etc.). | Requires container orchestration expertise; image size optimisation needed. |
| **Gradle** (build system) | Backend and library modules use Gradle for compilation and packaging. | Build scripts (`build.gradle.kts`) drive CI pipelines. | Teams must be familiar with Gradle DSL; Maven plugins not available. |
| **npm** (frontend) | Angular and Node.js modules built with npm. | Separate `package.json` files for `frontend` and `jsApi`. | Version conflicts between npm and Gradle must be coordinated. |
| **Kubernetes (optional)** | Planned target for production scaling. | Architecture designed for stateless services; readiness probes defined in Dockerfiles. | Additional operational overhead for cluster management. |

### 2.1.5 Security
| Constraint | Background | Impact on Architecture | Consequences |
|------------|------------|------------------------|--------------|
| **Spring Security 6** | Central authentication & authorization framework. | All REST endpoints are secured via method‑level annotations; custom `CustomMethodSecurityExpressionHandler` provides domain‑specific checks. | Requires security expertise; custom expressions increase maintenance. |
| **OAuth2 / JWT** | Token‑based authentication for external clients. | `TokenAuthenticationRestTemplateConfigurationSpringBoot` configures RestTemplate to propagate JWTs. | Token validation adds latency; token revocation strategy needed. |
| **CORS policy** | Front‑end (Angular) accesses backend APIs. | CORS filters configured in Spring Boot. | Misconfiguration can block legitimate UI calls. |
| **Secure Docker images** | Base images are scanned for CVEs. | `Dockerfile` (found in `container.infrastructure`) pins versions. | Regular image updates required to stay compliant. |

## 2.2 Organizational Constraints (≈ 2 pages)

| Constraint | Background | Impact on Architecture | Consequences |
|------------|------------|------------------------|--------------|
| **Team Structure** | 5 cross‑functional squads (Backend, Frontend, Test, DevOps, Security). | Each squad owns a subset of containers (`backend`, `frontend`, `e2e‑xnp`). | Clear ownership reduces merge conflicts; inter‑squad coordination needed for shared libraries. |
| **Development Process** | Scrum with 2‑week sprints, CI/CD pipelines on GitHub Actions. | Incremental delivery of Docker images; automated unit, integration and e2e tests. | Requires strict branch policies; failing pipeline blocks releases. |
| **Deployment Frequency** | Minimum of **twice per week** to staging; production releases **monthly** after manual approval. | Architecture must support blue‑green deployments; feature toggles used in code. | Longer production windows increase risk; rollback mechanisms must be in place. |
| **Compliance & Regulatory** | The UVZ system processes personal identification data (GDPR). | Data‑at‑rest encryption, audit logging, and access control enforced by Spring Security. | Additional documentation and data‑protection impact assessments required. |
| **Tooling Standardisation** | All teams use IntelliJ IDEA, SonarQube, and Checkstyle for static analysis. | Code quality gates integrated into CI; uniform coding standards. | Learning curve for new developers; tool licensing costs. |

## 2.3 Convention Constraints (≈ 2 pages)

### 2.3.1 Naming Conventions
- **Package structure** follows the reverse‑domain pattern `de.bnotk.uvz.module.<domain>.<layer>.<type>` (e.g., `de.bnotk.uvz.module.deedentry.service.api.rest`).
- **Classes** use **PascalCase**; interfaces end with `Service` or `Repository` (e.g., `ActionRestServiceImpl`, `ParticipantDao`).
- **REST controllers** are suffixed with `RestService` or `Controller` and placed in the `presentation` layer.
- **Database entities** end with `Entity` (e.g., `RestrictedDeedEntryEntity`).
- **Configuration classes** end with `Configuration` (e.g., `ProxyRestTemplateConfiguration`).

### 2.3.2 Code Style & Formatting
- **Indentation:** 4 spaces, no tabs.
- **Line length:** 120 characters max.
- **Brackets:** K&R style for Java, Angular style for TypeScript.
- **Static analysis:** SonarQube quality profile `java-spring` and `typescript-angular` enforced.
- **Commit messages:** Conventional Commits (`feat:`, `fix:`, `chore:`). 

### 2.3.3 API Design Conventions
- **REST endpoints** use **plural nouns** and **snake‑case** is avoided; e.g., `/api/v1/deed-entries`.
- **Versioning** is done via URL prefix (`/api/v1/`).
- **HTTP methods** follow CRUD semantics (`GET`, `POST`, `PUT`, `DELETE`).
- **Response format** is JSON with a standard envelope `{ "data": ..., "meta": ... }`.
- **Error handling** uses Spring `@ControllerAdvice` (`DefaultExceptionHandler`).
- **OpenAPI** specification generated by `OpenApiConfig` and customised by `OpenApiOperationAuthorizationRightCustomizer`.

---
*All tables and examples are derived from the actual code base (see components such as `ActionRestServiceImpl`, `ParticipantDaoOracle`, `CustomMethodSecurityExpressionHandler`, and containers `backend`, `frontend`, `e2e‑xnp`).*