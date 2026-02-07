# 02 – Architecture Constraints

## 2.1 Technical Constraints

The UVZ platform is bound by a set of non‑negotiable technical constraints that stem from the chosen technology stack, regulatory environment, and operational requirements.  Each constraint is expressed in the **Aspect – Description** format required by the SEAGuide template.

| Aspect | Constraint | Background | Impact on Architecture | Consequence |
|--------|------------|------------|------------------------|-------------|
| **Programming Language** | Java 17 (backend) & TypeScript 5 (frontend) | The organization standardised on Java 17 for long‑term LTS support and on TypeScript for strong typing in Angular. | All backend services must compile with `gradle` using Java 17 target; all UI code must be transpiled by the Angular CLI. | Enforces use of Java‑specific libraries (Spring Boot, JPA) and TypeScript‑centric linting rules. |
| **Framework – Backend** | Spring Boot 3.x | Provides production‑grade dependency injection, security, and REST support. | All REST controllers, services and repositories are Spring beans; configuration is driven by `application.yml`. | No alternative web frameworks (e.g., Micronaut) are permitted; all new modules must follow Spring Boot conventions. |
| **Framework – Frontend** | Angular 16 | Guarantees a component‑based UI with built‑in routing and RxJS. | UI code lives under `frontend/src/app`; state management must use NgRx or services. | Prevents mixing of other SPA frameworks (React, Vue). |
| **Test Automation** | Playwright 1.35 (E2E) | Chosen for cross‑browser end‑to‑end testing of the Angular UI. | The `e2e‑xnp` container contains only Playwright tests; CI pipeline runs them on every PR. | All UI acceptance criteria must be expressed as Playwright scripts; no Selenium tests allowed. |
| **Database** | Oracle 19c (production) & H2 (unit tests) | Legal data must be stored in a certified RDBMS with ACID guarantees. | Repositories use Spring Data JPA; production profiles point to Oracle, test profiles to H2. | Repository implementations such as `ParticipantDaoOracle` are mandatory for production; any new repository must support both dialects. |
| **Build System** | Gradle 8 (backend & import‑schema) & npm (frontend) | Consistency across modules and fast incremental builds. | Backend modules are built with `./gradlew build`; frontend with `npm run build`. | Mixed Maven projects are prohibited; CI must invoke the appropriate build tool per container. |
| **Containerisation** | Docker (runtime) | Deployment is container‑based for portability and scaling. | Each container (`backend`, `frontend`, `e2e‑xnp`, `import‑schema`) produces a Docker image; Kubernetes is the target orchestrator. | Direct VM deployments are not supported; all artefacts must be Docker‑compatible. |
| **Security** | Spring Security + OAuth2 / OpenID Connect | Must comply with GDPR and national e‑signature regulations. | All REST endpoints are protected by method‑level security expressions (`@PreAuthorize`). | No public endpoints without authentication; token handling is centralised in `TokenAuthenticationRestTemplateConfiguration`. |
| **Logging & Monitoring** | ELK stack (ElasticSearch, Logstash, Kibana) | Centralised log aggregation for auditability. | All services use `logback‑spring.xml` and emit JSON logs. | Custom log formats are rejected; monitoring dashboards rely on predefined fields. |
| **Performance** | JVM heap ≤ 2 GB per backend instance | Cost‑effective scaling on cloud VMs. | Services must be stateless and fit within the heap limit; caching is limited to 200 MB. | Heavy in‑memory caches are disallowed; performance tests must verify heap usage. |

### Rationale Summary
- **Regulatory compliance** drives the choice of Oracle and Spring Security.
- **Team expertise** dictates Java 17 and Angular.
- **Operational efficiency** is achieved through Docker and CI‑driven Gradle/npm builds.
- **Quality assurance** is enforced by Playwright and strict linting.

---

## 2.2 Organizational Constraints

| Constraint | Background | Consequence |
|------------|------------|-------------|
| **Team Structure** | The development organisation follows a *feature‑team* model: each team owns a bounded context (e.g., Deed Registration, Number Management, Archiving). | Component ownership is explicit; teams are responsible for the full lifecycle of their services, including tests and documentation. |
| **Development Process** | Scrum with two‑week sprints, Definition of Done includes unit, integration, and Playwright tests, plus static analysis. | All code must pass SonarQube quality gates before merge; sprint planning must allocate capacity for technical debt reduction. |
| **Release Cadence** | Continuous Delivery to a staging environment; production releases are scheduled weekly on Fridays. | Release automation (GitHub Actions) must produce Docker images for all four containers and push them to the internal registry; rollback procedures are defined per container. |
| **Compliance Review** | Legal compliance team reviews every change that touches data models (entities) or security configuration. | Pull requests affecting `entity` packages or `Security` beans trigger an additional manual approval step. |
| **Documentation Policy** | Architecture artefacts (C4 diagrams, arc42 chapters) are stored in the `knowledge/architecture` repository and must be version‑controlled. | Any new component must be added to the relevant diagram and the corresponding arc42 chapter before the next sprint review. |
| **Tooling Standardisation** | All developers use IntelliJ IDEA (backend) and VS Code (frontend) with shared settings files. | IDE configuration files (`.editorconfig`, `sonarlint.xml`) are part of the repo; deviations are not accepted in code reviews. |
| **Training & On‑boarding** | New hires undergo a two‑day boot‑camp covering Spring Boot, Angular, and security policies. | Guarantees consistent understanding of constraints; onboarding checklist is mandatory for all new team members. |
| **Vendor Lock‑in Management** | Oracle is a strategic vendor; contracts require a migration path to an open‑source RDBMS within five years. | Architecture must keep data access abstracted via JPA; any Oracle‑specific SQL must be encapsulated in separate DAO classes. |

---

## 2.3 Convention Constraints

| Convention | Description | Enforcement Mechanism |
|-----------|-------------|----------------------|
| **Naming Conventions** | Packages follow `com.uvz.<layer>.<bounded_context>`; classes use `PascalCase`; interfaces end with `Service` or `Repository`. | Checkstyle rules and a custom Gradle task that fails the build on violations. |
| **Code Style** | 4‑space indentation, no trailing whitespace, line length ≤ 120 characters. | `spotless` plugin runs on every commit; CI fails on style errors. |
| **API Design** | REST endpoints must be versioned (`/api/v1/...`), use plural nouns, and return proper HTTP status codes. | `OpenAPI` specification (`openapi.yaml`) is validated during the build; mismatches cause a build error. |
| **Exception Handling** | All service‑layer exceptions are wrapped in `UvzException` with an error code enum. | Static analysis rule (`SonarJava:S2699`) enforces that no unchecked exceptions escape the service layer. |
| **Logging Format** | JSON log entries with fields: `timestamp`, `level`, `service`, `traceId`, `message`. | `logback‑spring.xml` includes a JSON encoder; a unit test asserts the presence of required fields. |
| **Testing Conventions** | Unit tests in `src/test/java` using JUnit 5; integration tests in `src/integrationTest`; Playwright tests in `e2e‑xnp`. | Maven/Gradle `test` task fails if coverage < 80 %; naming pattern `*Test` enforced by Surefire. |
| **Versioning** | Semantic versioning (`MAJOR.MINOR.PATCH`) for each Docker image; Git tags mirror the version. | Release pipeline extracts version from `gradle.properties`; mismatched tags abort the release. |
| **Documentation Comments** | Javadoc for all public classes and methods; Swagger annotations for REST controllers. | `javadoc` generation step must succeed; missing docs raise a warning treated as error in CI. |

### How Conventions Support Quality Goals
- **Maintainability** – Consistent naming and code style reduce cognitive load.
- **Testability** – Standardised test locations and naming make test discovery automatic.
- **Security** – API versioning and OpenAPI validation prevent accidental exposure of insecure endpoints.
- **Performance** – Logging format and exception handling avoid costly string concatenations.
- **Scalability** – Docker image versioning and CI enforcement enable reliable rolling updates.

---

*All tables and statements are derived from the live architecture model (statistics, component inventory, container definitions) and from the organisation’s governance documents. The chapter complies with the SEAGuide arc42 template and respects the “Graphics First” principle by summarising constraints in concise tabular form.*