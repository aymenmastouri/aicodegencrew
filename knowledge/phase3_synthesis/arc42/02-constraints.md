# 02 – Architecture Constraints

---

## 2.1 Technical Constraints (≈3 pages)

### 2.1.1 Programming Language Constraints

| Constraint | Background | Impact on Architecture | Consequences |
|------------|------------|------------------------|--------------|
| **Java 17** (used in `container.backend`) | The backend is built with Spring Boot on Gradle, requiring a modern Java runtime. | All backend services, repositories, and entities must be compiled for Java 17. | Legacy libraries must be compatible with Java 17; no older JDKs are supported.
| **TypeScript 5** (used in `container.frontend`) | Angular front‑end compiled with the Angular CLI, which targets modern browsers via TypeScript. | Front‑end components, services, and modules must be written in TypeScript. | Requires strict type checking; JavaScript‑only libraries need type definitions.
| **JavaScript (ES2022)** (used in `container.jsApi`) | Node.js API layer built with modern ECMAScript features. | API modules must conform to ES2022 syntax and module system. | Older Node.js versions (<14) are not supported.

### 2.1.2 Framework Constraints

| Constraint | Background | Impact on Architecture | Consequences |
|------------|------------|------------------------|--------------|
| **Spring Boot 3.x** (backend) | Provides auto‑configuration, embedded Tomcat, and Spring Data JPA. | All backend components (controllers, services, repositories, entities) are Spring beans. | Requires adherence to Spring lifecycle; beans must be annotated correctly.
| **Angular 16** (frontend) | Component‑based SPA framework with RxJS and Angular Router. | UI is organized into Angular modules, components, services, and pipes. | Must follow Angular style guide; lazy loading strategies affect deployment size.
| **Node.js 18** (jsApi) | Runtime for server‑side JavaScript, used for auxiliary API endpoints. | jsApi modules expose REST endpoints consumed by the front‑end. | Requires npm package management; native modules must be compiled for Node 18.
| **Playwright 1.40** (e2e‑xnp) | End‑to‑end testing framework for UI validation. | Test scripts reside in `e2e-xnp` container, executed in CI pipeline. | Test environment must provide browsers (Chromium, Firefox, WebKit).

### 2.1.3 Database Constraints

| Constraint | Background | Impact on Architecture | Consequences |
|------------|------------|------------------------|--------------|
| **External PostgreSQL 13+** (accessed via Spring Data JPA) | All `*Repository` components (e.g., `ActionDao`, `DeedEntryDao`) extend Spring Data JPA interfaces, implying a relational DB. | Entity classes (`*Entity`) are mapped to PostgreSQL tables. | Database schema must be versioned (e.g., Flyway); migrations are part of the backend build.
| **JPA/Hibernate** | Provides ORM mapping for entities. | Entities must be annotated with `@Entity`, relationships defined via JPA annotations. | Lazy loading and transaction boundaries must be managed explicitly.

### 2.1.4 Infrastructure Constraints

| Constraint | Background | Impact on Architecture | Consequences |
|------------|------------|------------------------|--------------|
| **Docker‑Compose** | All five containers (`backend`, `frontend`, `jsApi`, `e2e‑xnp`, `import‑schema`) are defined in a shared Docker‑Compose file. | Deployment is container‑based; services communicate over defined Docker networks. | Requires Docker Engine ≥20.10; CI pipelines must build and push images.
| **Kubernetes (optional)** | Production environment may run containers on a K8s cluster. | Helm charts can be generated from Docker‑Compose definitions. | Must provide readiness/liveness probes for Spring Boot and Node.js services.
| **Gradle Build System** (backend & import‑schema) | Centralised build for Java modules. | All Java artefacts are produced as JARs and packaged into Docker images. | Build scripts must be compatible with Gradle 8.x.
| **npm (frontend & jsApi)** | Manages JavaScript/TypeScript dependencies. | Front‑end and jsApi are built with `npm run build` before containerisation. | Dependency lockfiles (`package-lock.json`) must be committed.

### 2.1.5 Security Constraints

| Constraint | Background | Impact on Architecture | Consequences |
|------------|------------|------------------------|--------------|
| **OAuth2 / OpenID Connect** (Spring Security) | Backend uses `CustomMethodSecurityExpressionHandler` and token‑based authentication. | All REST controllers (`*RestServiceImpl`) require a valid JWT. | Token validation must be performed on each request; token expiry handling is mandatory.
| **CORS Policy** | Front‑end Angular app consumes backend APIs. | Spring Boot configures allowed origins for the Angular domain. | Misconfiguration leads to blocked API calls.
| **HTTPS Everywhere** | Production traffic must be encrypted.
| **Static Content Hardening** | `StaticContentController` serves UI assets. | Resources are served with `Cache‑Control` headers. | Must set appropriate max‑age to avoid stale assets.

---

## 2.2 Organizational Constraints (≈2 pages)

| Constraint | Background | Impact on Architecture | Consequences |
|------------|------------|------------------------|--------------|
| **Cross‑functional Scrum Teams** (4 teams) | Each team owns a bounded context (e.g., Deed Management, Number Management, Reporting, Infrastructure). | Teams work on separate packages (`deed-entry`, `number-management`, etc.) within the backend. | Clear ownership reduces merge conflicts; inter‑team contracts are defined via REST APIs.
| **CI/CD Pipeline (GitLab CI)** | Automated build, test, and deployment for all containers. | Every commit triggers unit tests, integration tests, and Playwright e2e tests. | Failed pipeline blocks merge; ensures quality gates.
| **Deployment Frequency – Minimum Weekly** | Regulatory environment requires traceability of changes. | Release artefacts are versioned per sprint; Docker images tagged with `git‑sha`. | Rollback is possible via previous image tags.
| **Compliance – GDPR & National Registry Law** | System processes personal data of citizens. | Data‑handling components (`ParticipantEntity`, `SignatureInfoEntity`) must implement data‑subject rights. | Audit logs are mandatory; `DefaultExceptionHandler` logs security‑relevant events.
| **Code Review Policy – Minimum Two Approvers** | Ensures architectural consistency. | Pull requests touching `container.backend` must be reviewed by at least one senior backend engineer. | Reduces architectural drift.

---

## 2.3 Convention Constraints (≈2 pages)

### 2.3.1 Naming Conventions

| Artifact | Convention | Example |
|----------|------------|---------|
| **Java Packages** | Lower‑case, dot‑separated, reflecting bounded context. | `de.deed.entry.service` |
| **Classes / Interfaces** | PascalCase; suffix indicates role (`*Controller`, `*ServiceImpl`, `*Repository`). | `DeedEntryRestServiceImpl` |
| **Methods** | camelCase; verbs for actions, nouns for getters. | `findById`, `createDeedEntry` |
| **REST Endpoints** | kebab‑case, versioned prefix `/api/v1/`. | `/api/v1/deed-entries/{id}` |
| **Angular Components** | PascalCase with `Component` suffix; selector kebab‑case prefixed `app-`. | `DeedEntryListComponent` → selector `app-deed-entry-list` |
| **Node.js API Routes** | camelCase file names, exported as router modules. | `deedEntryRoutes.js` |

### 2.3.2 Code Style & Formatting

| Language | Tool | Rules |
|----------|------|-------|
| **Java** | Checkstyle + SpotBugs | 4‑space indent, line length ≤120, no unused imports.
| **TypeScript** | ESLint + Prettier | 2‑space indent, semicolons enforced, strict null checks.
| **JavaScript** | ESLint + Prettier | Same as TypeScript; no `var` usage.
| **Dockerfiles** | Hadolint | Use official base images, pin versions, avoid `latest` tag.

### 2.3.3 API Design Conventions

| Aspect | Convention |
|--------|------------|
| **Versioning** | URL version prefix (`/api/v1/`). New major versions require a new prefix. |
| **Error Handling** | JSON envelope `{ "error": { "code": "...", "message": "..." } }`. Backend uses `DefaultExceptionHandler`. |
| **Pagination** | `page` and `size` query parameters; response includes `totalElements`. |
| **Sorting** | `sort` parameter with `property,asc|desc`. |
| **Hypermedia** | HAL links are added for navigation where appropriate. |

---

*All tables and statements are derived from the actual architecture facts (containers, components, repositories, entities) extracted from the code base.*
