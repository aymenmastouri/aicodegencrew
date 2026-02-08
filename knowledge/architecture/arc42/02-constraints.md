# 02 – Architecture Constraints

---

## 2.1 Technical Constraints (≈ 3 pages)

| **Constraint** | **Background** | **Impact on Architecture** | **Consequences if Ignored** |
|---|---|---|---|
| **Programming Language – Java 17 (backend)** | The backend is built with Spring Boot on the JVM. Java 17 is the LTS version supported by the corporate JDK policy. | All backend services, repositories and domain entities must be written in Java. Influences choice of libraries (e.g., Lombok, JPA) and limits use of language‑specific features (e.g., records are allowed, but Kotlin is prohibited). | Mixing other JVM languages would break build pipelines, increase cognitive load and risk incompatibilities with existing Gradle scripts. |
| **Programming Language – TypeScript 5 (frontend)** | The UI is a single‑page application based on Angular. The corporate front‑end policy mandates TypeScript for static typing. | All UI components, services and modules are TypeScript files compiled by the Angular CLI. | Using plain JavaScript would reduce type safety, increase runtime errors, and conflict with the enforced linting rules. |
| **Framework – Spring Boot 3.x** | Spring Boot provides the micro‑service runtime, dependency injection and actuator endpoints. Version 3 aligns with Java 17 and the corporate security baseline. | Architecture is layered (presentation → application → domain → data‑access). All REST controllers, services and repositories must be Spring beans. | Switching to another framework would require a complete rewrite of the DI layer, configuration files and health‑check mechanisms. |
| **Framework – Angular 15** | Angular is the approved front‑end framework for enterprise portals. It enforces a component‑based architecture and strong typing. | UI is organised into NgModules, lazy‑loaded routes and RxJS streams. All UI code must follow Angular conventions (decorators, DI). | Using React or Vue would break the shared component library, CI pipelines and the corporate UI style guide. |
| **Framework – Node.js 20 (jsApi)** | The `jsApi` module provides server‑side utilities for the front‑end (e.g., asset generation). Node.js is the only allowed JavaScript runtime for server code. | The module is packaged as an npm library, built with the same CI pipeline as the Angular app. | Introducing another runtime (e.g., Deno) would require separate build tooling and increase operational complexity. |
| **Database – PostgreSQL 15 (production) & H2 (unit tests)** | All persistent entities are stored in PostgreSQL. H2 is used for fast in‑memory unit tests. The repository layer uses Spring Data JPA. | Entity classes must be annotated with JPA annotations; DAO names (e.g., `DeedEntryDao`) map to tables. Transaction management is handled by Spring. | Using a non‑relational store would break existing JPA queries, require redesign of the domain model and invalidate performance benchmarks. |
| **Infrastructure – Docker 24 + Kubernetes 1.27** | All containers (backend, frontend, e2e‑xnp, jsApi, import‑schema) are built as Docker images and deployed to a Kubernetes cluster managed by the corporate platform team. | Deployment descriptors (Helm charts) must reference the exact image tags. Service discovery relies on Kubernetes DNS. | Deploying without containers would eliminate the reproducible environment, break scaling policies and invalidate the CI/CD pipeline. |
| **Infrastructure – GitLab CI/CD** | The project uses GitLab pipelines for build, test and deployment. Pipelines enforce static analysis, unit tests and security scans. | Every commit triggers a pipeline that produces Docker images, runs Playwright end‑to‑end tests and pushes to the artifact registry. | Skipping CI would increase risk of broken builds, security regressions and non‑compliant releases. |
| **Security – Spring Security 6 + OAuth2 / JWT** | Authentication and authorisation are handled by Spring Security with JWT tokens issued by the corporate Identity Provider. A custom `CustomMethodSecurityExpressionHandler` extends expression handling for fine‑grained rights. | All REST endpoints are protected by method‑level security annotations (`@PreAuthorize`). The front‑end includes an HTTP interceptor that adds the JWT to every request. | Removing JWT would expose APIs, break the existing authorisation model and violate GDPR‑related data‑protection policies. |
| **Security – CSP & CORS policies** | Content‑Security‑Policy headers and strict CORS configuration are enforced by the Spring Boot gateway and the Angular build. | The UI can only call `/api/v1/**` endpoints; inline scripts are disallowed. | Disabling CSP would increase XSS risk; lax CORS would allow malicious origins to consume the API. |

---

## 2.2 Organizational Constraints (≈ 2 pages)

| **Aspect** | **Constraint** | **Rationale** |
|---|---|---|
| **Team Structure** | Three cross‑functional squads: *Backend*, *Frontend*, *Quality Assurance*. Each squad owns a bounded context (e.g., Deed‑Entry, Document‑Metadata). | Aligns with DDD bounded contexts, reduces coordination overhead and enables autonomous delivery. |
| **Development Process** | Scrum with two‑week sprints, Definition of Done includes unit test coverage ≥ 80 %, static analysis (SpotBugs, Checkstyle) and successful Playwright regression run. | Guarantees consistent quality, early defect detection and predictable velocity. |
| **Deployment Frequency** | Minimum of **once per day** to the staging environment; production releases are gated by a manual approval step but can be performed **multiple times per week**. | Supports continuous delivery while respecting regulatory change‑control procedures. |
| **Compliance & Regulatory** | GDPR, ISO 27001 and local data‑protection law (e.g., German BDSG). All personal data must be pseudonymised at rest; audit logs are immutable. | Legal requirement for the UVZ system handling personal identifiers; influences logging, encryption and retention policies. |
| **Auditability** | Every change to database schema must be versioned with Flyway and approved by the *Data Governance* board. | Guarantees traceability of schema evolution and prevents accidental data loss. |
| **Tooling Standardisation** | Mandatory use of IntelliJ IDEA (backend) and WebStorm (frontend) with shared settings repository; GitLab for source control; SonarQube for code quality gates. | Reduces environment drift, enforces consistent coding standards and simplifies onboarding. |

---

## 2.3 Convention Constraints (≈ 2 pages)

### 2.3.1 Naming Conventions

| **Element** | **Convention** |
|---|---|
| **Packages (Java)** | Lower‑case, dot‑separated, reflecting the bounded context (e.g., `de.bnotk.uvz.module.deedentry.domain`). |
| **Classes (Java)** | PascalCase, ending with a semantic suffix (`ServiceImpl`, `Dao`, `RestController`). |
| **Methods (Java)** | camelCase, verb‑first (`createDeedEntry`, `findById`). |
| **REST Endpoints** | `/api/v1/<bounded‑context>/<resource>`; version prefix mandatory. Example: `GET /api/v1/deed-entry/{id}`. |
| **Angular Modules** | `*.module.ts` named after feature (`DeedEntryModule`). |
| **Angular Components** | `kebab-case` selector prefixed with `app-` (e.g., `<app-deed-entry-form>`). |
| **TypeScript Interfaces** | PascalCase prefixed with `I` (e.g., `IDocumentMetadata`). |
| **Database Tables** | Snake_case, plural (`deed_entries`). |
| **Columns** | Snake_case, singular (`deed_number`). |

### 2.3.2 Code Style & Formatting

* **Java** – Google Java Style Guide enforced by Checkstyle. 120‑character line limit, `import` order: static, java.*, javax.*, third‑party, project. |
* **TypeScript** – Prettier with 2‑space indentation, single quotes, trailing commas. ESLint rules from the corporate `@uvz/eslint-config`. |
* **SQL** – Upper‑case keywords, lower‑case identifiers, one statement per line. |

### 2.3.3 API Design Conventions

* **REST** – Resource‑oriented, uses standard HTTP verbs. Responses follow the *application/json* media type with a wrapper `{ data: ..., meta: ... }`. |
* **Versioning** – URL versioning (`/api/v1/…`). Future major versions must be backward compatible for at least 12 months. |
* **Error Handling** – Global `@ControllerAdvice` produces RFC 7807‑compliant problem‑details objects. Front‑end maps error codes to user‑friendly messages. |
* **Pagination** – `GET` collections support `page`, `size` and `sort` query parameters; response includes `totalElements` and `totalPages`. |
* **Hypermedia** – Not used currently; links are provided only where required by external contracts. |

---

*All constraints listed above are derived from the concrete architecture facts (components, containers, repositories, security configuration) and the corporate engineering policies that govern the UVZ system.*
