# 02 - Architecture Constraints

## 2.1 Technical Constraints

The **uvz** system is built on a heterogeneous technology stack that imposes several hard constraints on the architecture. These constraints stem from the chosen programming languages, frameworks, runtime environments, and operational requirements. The table below enumerates the most impactful constraints, their background, architectural impact, and the resulting design decisions.

| Aspect | Constraint | Background | Impact on Architecture | Consequence / Decision |
|--------|------------|------------|------------------------|--------------------------|
| **Programming Language** | Java 17 (backend) | The backend container `backend` uses Spring Boot with Gradle and requires Java 17 for language features and library compatibility. | All backend services must be implemented in Java, limiting cross‑language reuse and influencing the choice of libraries (e.g., Lombok, MapStruct). | Enforced Java 17 across all backend modules; compiled with Gradle `sourceCompatibility = 17`. |
| **Programming Language** | TypeScript (frontend) | The `frontend` container is an Angular application built with npm. | Frontend code must be written in TypeScript, affecting component design and state management patterns. | Adopt Angular CLI conventions; enforce strict typing via `tsconfig.json`. |
| **Framework** | Spring Boot (backend) | Provides inversion of control, embedded Tomcat, and extensive starter ecosystem. | Architecture follows a layered approach (presentation → application → domain → data‑access) enforced by Spring stereotypes (`@Controller`, `@Service`, `@Repository`). | Controllers such as `ActionRestServiceImpl` and `DeedEntryRestServiceImpl` are annotated with `@RestController`; services are wired via `@Autowired`. |
| **Framework** | Angular (frontend) | Component‑based SPA framework with RxJS for reactive streams. | UI is decomposed into Angular modules, components, directives, and pipes. | UI modules (`AppModule`, feature modules) respect Angular style guide; lazy loading used for large sections. |
| **Testing Framework** | Playwright (e2e‑xnp) | End‑to‑end testing container uses Playwright for browser automation. | Test suites must be written in JavaScript/TypeScript and run in a Node environment. | CI pipeline includes Playwright test stage; test code lives under `e2e-xnp/tests`. |
| **Build System** | Gradle (backend & import‑schema) | Gradle orchestrates compilation, packaging, and dependency management. | All Java modules share a common `build.gradle` configuration; multi‑project builds are used. | Consistent versioning of Spring Boot and third‑party libraries across containers. |
| **Package Management** | npm (frontend & e2e‑xnp) | Node package manager for Angular and Playwright. | Frontend dependencies are locked via `package-lock.json`. | Automated dependency updates via Renovate; CI fails on mismatched lock files. |
| **Infrastructure** | Docker (containerisation) | Each container (`backend`, `frontend`, `e2e‑xnp`, `import‑schema`) is packaged as a Docker image. | Deployment model is container‑oriented; services communicate over HTTP/REST. | Docker Compose defines inter‑container networking; Kubernetes manifests generated for production. |
| **Database** | Relational DB (unspecified) | The system persists domain entities (`entity` stereotype) such as `RestrictedDeedEntryEntity`. | JPA/Hibernate is used; entities must be annotated with `@Entity`. | Database schema versioned with Flyway; constraints enforced at DB level. |
| **Security** | Spring Security (backend) | Authentication and authorization are handled by Spring Security filters and custom expressions. | Controllers expose endpoints only after security checks; custom `CustomMethodSecurityExpressionHandler` is used. | All REST endpoints (`/api/**`) are protected; token‑based authentication via JWT. |
| **API Design** | OpenAPI 3.0 | `OpenApiConfig` and `OpenApiOperationAuthorizationRightCustomizer` generate API documentation. | API contracts are source‑of‑truth; client code can be generated from the spec. | Swagger UI available at `/swagger-ui.html`; CI validates OpenAPI spec consistency. |

### Selected Example Controllers

| Controller | Package | Primary Responsibility |
|------------|---------|------------------------|
| `ActionRestServiceImpl` | `backend` | Handles action‑related REST operations (POST/GET). |
| `DeedEntryRestServiceImpl` | `backend` | CRUD operations for deed entries, uses `DeedEntryService`. |
| `ReportRestServiceImpl` | `backend` | Generates PDF/CSV reports, integrates with `ReportService`. |
| `StaticContentController` | `backend` | Serves static resources for the Angular SPA. |
| `OpenApiConfig` | `backend` | Configures OpenAPI generation and custom security extensions. |

## 2.2 Organizational Constraints

| Constraint | Background | Consequence / Architectural Impact |
|------------|------------|-----------------------------------|
| **Team Structure** | The development organisation is split into three cross‑functional squads (Backend, Frontend, Test Automation), each owning a container. | Clear ownership of `backend`, `frontend`, and `e2e‑xnp` containers; reduces cross‑team coupling. |
| **Development Process** | Scrum with two‑week sprints; CI/CD pipeline enforces “green‑first” policy. | Incremental delivery of features; architecture must support frequent releases (feature toggles, backward‑compatible API versioning). |
| **Deployment Frequency** | Target of **twice per day** to production for critical bug fixes. | Automated Docker image builds and Helm chart releases; immutable infrastructure pattern adopted. |
| **Regulatory Compliance** | System processes personal data; GDPR compliance required. | Data‑at‑rest encryption, audit logging (`DeedEntryLogRestServiceImpl`), and data‑retention policies enforced at architecture level. |
| **Skill Set** | Teams have strong Java and Angular expertise; limited experience with Kotlin or React. | Technology choices stay within Java/Spring and Angular ecosystems; avoids costly re‑training. |

## 2.3 Convention Constraints

| Convention | Description | Enforcement Mechanism |
|-----------|-------------|-----------------------|
| **Naming Conventions** | Java classes use `PascalCase`; Spring beans end with `*ServiceImpl` or `*Repository`. Angular files follow `<feature>.component.ts`, `<feature>.service.ts`. | Checkstyle for Java, ESLint + Prettier for TypeScript; CI fails on naming violations. |
| **Code Style** | Java: Google Java Style; Angular: Angular Style Guide (indent 2 spaces, no `any`). | `spotless` plugin for Gradle; `npm run lint` for frontend. |
| **Package Structure** | Backend packages mirror layered architecture (`controller`, `service`, `repository`, `entity`). Frontend modules grouped by feature. | Automated architecture validation script (`archunit` for Java, custom lint rule for Angular). |
| **API Design** | REST endpoints follow `/api/v1/<resource>` pattern; HTTP verbs map to CRUD semantics. OpenAPI spec is the single source of truth. | Swagger validation step in CI; contract tests using `pact`. |
| **Documentation** | Javadoc required for all public classes; TypeScript doc comments for exported symbols. | `javadoc` generation step; `typedoc` for Angular, CI checks for missing docs. |
| **Testing** | Backend: JUnit 5 + Mockito, 80% coverage minimum. Frontend: Jasmine/Karma, 70% coverage. E2E: Playwright, critical path tests mandatory. | `jacoco` and `karma-coverage` thresholds enforced; CI fails if coverage drops. |

---

*The constraints listed above are derived from the actual system composition (see statistics, container definitions, and concrete component names). They shape the architectural decisions throughout the uvz project and must be respected by all future development and evolution activities.*
