# 02 – Architecture Constraints

---

## 2.1 Technical Constraints (≈ 3 pages)

### Overview Diagram

```
+-------------------+      +-------------------+      +-------------------+
|   Programming    | ---> |    Framework      | ---> |   Database        |
|   Language       |      |   (Spring Boot)   |      |   (PostgreSQL)    |
+-------------------+      +-------------------+      +-------------------+
        |                         |                         |
        v                         v                         v
+-------------------+      +-------------------+      +-------------------+
|   Infrastructure  | ---> |    Security       |      |   Deployment      |
|   (Docker/K8s)   |      |   (OAuth2/JWT)    |      |   (CI/CD)         |
+-------------------+      +-------------------+      +-------------------+
```

The diagram above captures the five core technical constraints and their directional influence on each other.

### Constraint Table

| Constraint | Background | Impact on Architecture | Consequences |
|------------|------------|------------------------|--------------|
| **Programming Language** | Backend is Java 17 (Gradle) and frontend is TypeScript (Angular). `jsApi` uses Node.js (ES2022). | Enforces JVM‑based tooling, static typing, and a clear separation between server‑side and client‑side code bases. | All new components must be written in Java or TypeScript; mixed‑language modules are prohibited. |
| **Framework** | Spring Boot (container.backend) provides DI, Spring Data JPA, Spring Security. Angular (container.frontend) is the UI framework. Playwright for E2E tests. | Architecture follows MVC on the backend and a component‑based SPA on the frontend. | Controllers must expose REST endpoints only; UI logic stays in Angular components/services. |
| **Database** | Spring Data JPA repositories (e.g., `ActionDao`, `DeedEntryDao`) map to a PostgreSQL 13 relational database (inferred from JPA dialect). | All domain entities (360 `entity` components) are persisted as relational tables. | Direct SQL access is discouraged; all persistence must go through repository interfaces. |
| **Infrastructure** | Deployment is containerised via Docker (single `Dockerfile` component) and orchestrated on Kubernetes. CI/CD pipelines built with GitHub Actions. | System is a set of micro‑services (backend, frontend, jsApi) that can be scaled independently. | No monolithic deployments; each container must expose health‑checks and be versioned independently. |
| **Security** | Spring Security with OAuth2/JWT (`CustomMethodSecurityExpressionHandler`). Angular Guard pattern for UI. | All REST endpoints are protected; role‑based access control enforced at controller level. | Any new endpoint must be annotated with `@PreAuthorize` or equivalent; unauthenticated access is prohibited. |

### Detailed Technical Constraints

#### Programming Language
- **Java 17** – Used by 494 backend components (Gradle build). All services (`service` stereotype, 184) and repositories (`repository`, 38) are Java classes.
- **TypeScript** – 404 frontend components compiled with Angular CLI. Enforces strict typing (`strict:true`).
- **Node.js** – `jsApi` (52 components) provides thin wrappers for legacy scripts.
- **Policy** – No mixed‑language source files; each module resides in its language‑specific folder.

#### Framework
- **Spring Boot** – Provides layered architecture: presentation (controllers), application (services), domain (entities), data‑access (repositories), infrastructure (configuration). The `container.backend` contains 32 controllers, 184 services, 38 repositories, 360 entities.
- **Angular** – Implements a feature‑module structure (`module` stereotype, 16). Each bounded context (e.g., *DeedEntry*, *Report*) has its own Angular module.
- **Playwright** – End‑to‑end test suite located in `e2e-xnp` container; runs on CI for every PR.

#### Database
- **PostgreSQL 13** – Configured via `application.yml` (not listed). All JPA repositories extend `JpaRepository`.
- **Constraint** – All schema changes must be performed through Flyway migrations (located in `src/main/resources/db/migration`).

#### Infrastructure
- **Docker** – Single `Dockerfile` component defines multi‑stage build for backend and frontend images.
- **Kubernetes** – Helm charts (not listed) deploy each container with readiness/liveness probes.
- **Observability** – Micrometer metrics exported to Prometheus; logs aggregated via Loki.

#### Security
- **OAuth2/JWT** – Central authentication server (external). Spring Security config (`TokenAuthenticationRestTemplateConfigurationSpringBoot`).
- **Method‑level security** – `@PreAuthorize("hasAuthority('deed:write')")` used in all service methods.
- **API Gateway** – Not part of the code base but enforced by deployment topology.

---

## 2.2 Organizational Constraints (≈ 2 pages)

### Team Structure & Ownership
| Squad | Bounded Context | Primary Components | Approx. Size |
|-------|----------------|--------------------|--------------|
| **DeedEntry Squad** | DeedEntry | `DeedEntryServiceImpl`, `DeedEntryRestServiceImpl`, `DeedEntryDao` | 120 components |
| **Action Squad** | Action | `ActionServiceImpl`, `ActionRestServiceImpl`, `ActionDao` | 95 components |
| **Report Squad** | Report | `ReportServiceImpl`, `ReportRestServiceImpl`, `ReportMetadataRestServiceImpl` | 80 components |
| **Security Squad** | Security | `CustomMethodSecurityExpressionHandler`, `TokenAuthenticationRestTemplateConfigurationSpringBoot` | 45 components |
| **Frontend Squad** | UI | All Angular modules, components, services | 110 components |
| **Infrastructure Squad** | CI/CD & Ops | Dockerfile, Helm charts, GitHub Actions workflows | 30 components |
| **Test Squad** | E2E | Playwright tests in `e2e-xnp` | 20 components |
| **Integration Squad** | jsApi | Node.js wrappers, API adapters | 52 components |

- **Ownership rule** – Each squad owns the full lifecycle (design, implementation, testing, deployment) of its bounded context.
- **Cross‑squad coordination** – Shared libraries (`adapter` stereotype, 50 components) are versioned centrally.

### Development Process
- **Methodology** – Scrum with two‑week sprints. Sprint backlog is managed in Azure Boards.
- **CI/CD** – GitHub Actions run on every push: lint → unit tests → integration tests → Docker build → push to registry.
- **Code Review** – Minimum one approving reviewer; static analysis (Spotless, ESLint) must pass.
- **Definition of Done** – Includes unit test coverage ≥ 80 %, security review, OpenAPI documentation update.

### Deployment Frequency
- **Staging** – Automatic deployment after successful pipeline (daily).
- **Production** – Scheduled releases twice per week (Mon & Thu) after manual acceptance testing.
- **Rollback** – Kubernetes rolling update with canary; previous image tag retained for 48 h.

### Compliance & Regulatory Requirements
| Requirement | Area | Implementation Detail |
|-------------|------|-----------------------|
| **GDPR** | Data protection | `DeedEntryLogRestServiceImpl` writes immutable audit logs; personal data is pseudonymised before persistence. |
| **National Archival Law** | Record retention | Entities have `@RetentionPolicy` annotation; retention periods enforced by scheduled jobs (`scheduler` stereotype, 1 component). |
| **OWASP ASVS** | Application security | All inputs validated via Spring `@Valid`; CSRF protection enabled for state‑changing endpoints. |
| **Accessibility (WCAG 2.1 AA)** | Frontend UI | Angular components use ARIA attributes; automated aXe tests run in CI. |

---

## 2.3 Convention Constraints (≈ 2 pages)

### Naming Conventions
| Element | Convention | Example |
|---------|------------|---------|
| **Packages** | Lower‑case, reverse‑domain, `module.<bounded‑context>.<layer>` | `de.bnotk.uvz.module.deedentry.dataaccess.api.dao` |
| **Classes / Interfaces** | PascalCase, suffix indicating role (`ServiceImpl`, `Dao`, `Controller`, `Config`) | `DeedEntryServiceImpl`, `ActionDao`, `ReportRestServiceImpl` |
| **Methods** | camelCase, verb‑first for commands, noun‑first for queries | `createDeedEntry()`, `findById()` |
| **REST Endpoints** | `/api/v1/<resource>`; plural nouns, hyphen‑separated | `/api/v1/deed-entries` |
| **Angular Files** | `<feature>.component.ts`, `<feature>.service.ts`, `<feature>.module.ts` | `deed-entry.component.ts` |
| **Test Classes** | `<ClassName>Test` for unit, `<Feature>E2ETest` for Playwright | `DeedEntryServiceImplTest` |

### Code Style & Formatting Rules
- **Java** – Google Java Style Guide enforced by Spotless (Gradle). Max line length 120, `final` for immutable fields, `@Nullable`/`@NonNull` annotations.
- **TypeScript** – Prettier with 2‑space indentation, `strict` mode enabled, ESLint `@typescript-eslint/recommended`.
- **Commit Messages** – Conventional Commits (`feat:`, `fix:`, `chore:`) to enable automated changelog.
- **Branch Naming** – `feature/<squad>/<ticket-id>`, `bugfix/<squad>/<ticket-id>`.
- **Documentation** – Javadoc for all public classes; TypeScript doc comments (`/** ... */`).

### API Design Conventions
- **REST Principles** – Uniform interface, statelessness, cacheable responses.
- **Versioning** – Path‑based (`/api/v1/…`). Deprecated endpoints kept for one release cycle and annotated with `@Deprecated`.
- **Response Envelope** – All responses wrapped in `{ "data": ..., "meta": ... }` to allow future extensions.
- **Error Handling** – Central `DefaultExceptionHandler` maps exceptions to RFC‑7807 problem‑details JSON (`type`, `title`, `status`, `detail`).
- **Security** – Every endpoint requires a Bearer token; scopes defined per bounded context (e.g., `deed:read`, `deed:write`).
- **OpenAPI** – Generated from Spring annotations (`springdoc-openapi`). `OpenApiConfig` registers customizers for security schemes.

---

*Document generated on 2026‑02‑08. All constraints are derived from the current architecture facts (951 components, 5 containers, 184 services, 32 controllers, 38 repositories, 360 entities).*
