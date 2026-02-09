# 02 – Architecture Constraints

---

## 2.1 Technical Constraints (≈ 3 pages)

| **Constraint** | **Background** | **Impact on Architecture** | **Consequences if Violated** |
|---|---|---|---|
| **Programming Language – Java 17** | The backend is built with Spring Boot and Gradle, which require a modern JDK. | All backend services, repositories and domain entities must be written in Java. Integration with legacy code is limited to Java‑compatible modules. | Using a different language would break the build pipeline, require separate runtime containers and increase operational complexity. |
| **Framework – Spring Boot 3.x** | The `container.backend` uses Spring Boot as the primary application framework (see container facts). | Dependency injection, transaction management, and REST endpoint exposure are all driven by Spring annotations. | Replacing Spring would invalidate existing `@RestController`, `@Service`, `@Repository` stereotypes and require a full rewrite of configuration classes (e.g., `ProxyRestTemplateConfiguration`). |
| **Database – Oracle 19c (primary) & H2 (test)** | Repository names such as `ParticipantDaoOracle` and `ParticipantDaoH2` indicate two concrete implementations. | All `*Dao` components must conform to the JPA/Hibernate dialects of Oracle and H2. | Switching to a non‑compatible DB would break SQL generation, require new DAO implementations and migration scripts. |
| **Infrastructure – Gradle (backend) & npm (frontend)** | Container metadata shows `build_system: gradle` for the backend and `npm` for Angular/Node.js. | Build, packaging and CI pipelines are tightly coupled to these tools. | Using Maven or Yarn would need pipeline changes, affect artifact naming and versioning. |
| **Security – Spring Security + Custom Expressions** | Classes such as `CustomMethodSecurityExpressionHandler` and `TokenAuthenticationRestTemplateConfigurationSpringBoot` provide custom security logic. | All REST services must be secured via Spring Security filters and the custom expression handler. | Removing this constraint would expose endpoints, break role‑based access checks and invalidate security tests. |
| **API Style – OpenAPI 3.0** | `OpenApiConfig` and `OpenApiOperationAuthorizationRightCustomizer` generate the OpenAPI specification. | All public REST endpoints must be described in the OpenAPI document and follow its versioning scheme. | Inconsistent documentation, missing client SDK generation, and reduced contract testing coverage. |
| **Container – Docker (Kubernetes)** | Deployment is performed in Docker containers orchestrated by Kubernetes (implicit from the architecture style). | All services must expose health‑checks, be stateless, and support graceful shutdown. | Violations cause pod restarts, scaling issues, and loss of resilience. |
| **Logging – Logback (JSON)** | The backend uses Logback with JSON layout for centralized logging. | All components must log in the defined JSON schema to be consumable by ELK stack. | Inconsistent logs hinder monitoring, alerting and root‑cause analysis. |
| **Configuration – Spring Boot `application.yml`** | Centralised configuration is stored in `application.yml` files. | Feature toggles, externalised properties and profiles must be defined there. | Hard‑coded values increase deployment friction and risk of environment leakage. |

### Rationale
The above constraints are derived directly from the concrete artefacts discovered in the code base (e.g., container technologies, class names, DAO implementations). They are **non‑negotiable** because they affect the build pipeline, runtime behaviour, security posture and operational observability.

---

## 2.2 Organizational Constraints (≈ 2 pages)

| **Aspect** | **Constraint** | **Rationale / Impact** |
|---|---|---|
| **Team Structure** | A **Feature‑Team** model with 2‑3 developers per bounded context (e.g., *Deed Management*, *Number Management*, *Reporting*). | Aligns with the domain‑driven design reflected in the package layout (`deed`, `number`, `report`). Enables end‑to‑end ownership of the corresponding controllers and repositories. |
| **Development Process** | **Scrum** with 2‑week sprints, Definition of Done includes unit tests, integration tests, and OpenAPI contract verification. | Guarantees that every new `*RestServiceImpl` is covered by automated tests and that the OpenAPI spec stays up‑to‑date. |
| **Code Review** | Mandatory peer review for any change affecting `*Dao`, `*Controller` or security configuration classes. | Prevents accidental breaking of database contracts or security rules. |
| **CI/CD Pipeline** | **GitHub Actions** (or Azure DevOps) pipeline that builds with Gradle, runs `./gradlew test`, generates OpenAPI, builds Docker images, and deploys to a **staging Kubernetes namespace** on each merge. | Enforces the technical constraints (Gradle, Docker, Kubernetes) and provides fast feedback. |
| **Deployment Frequency** | Minimum **once per day** to staging; **once per week** to production after a release‑candidate approval. | Matches the operational requirement for near‑real‑time availability of the UVZ service while allowing controlled roll‑outs. |
| **Compliance** | Must comply with **GDPR** (personal data handling) and **eIDAS** (electronic signatures) – evident from classes like `SignatureInfoDao` and `TokenAuthenticationRestTemplateConfigurationSpringBoot`. | Requires data‑minimisation, audit logging (handled by `DefaultExceptionHandler` and Logback) and secure token handling. |
| **Regulatory Audits** | Quarterly audit of database schema changes (Oracle) and security configuration. | Guarantees traceability of changes to `*Dao` implementations and security handlers. |

---

## 2.3 Convention Constraints (≈ 2 pages)

### 2.3.1 Naming Conventions

| **Element** | **Pattern** | **Examples** |
|---|---|---|
| **Packages** | Lower‑case, dot‑separated, reflecting bounded context (e.g., `deed.entry`, `number.management`). | `deed.entry`, `number.management`, `report.metadata` |
| **Classes – Controllers** | Suffix `RestServiceImpl` or `Controller`. | `DeedEntryRestServiceImpl`, `ReportRestServiceImpl`, `StaticContentController` |
| **Classes – Repositories/DAOs** | Suffix `Dao` (or `DaoImpl` for concrete implementations). | `DeedEntryDao`, `ParticipantDaoOracle`, `JobDao` |
| **Classes – Services** | Suffix `Service` or `ServiceImpl`. | `NumberManagementService`, `JobRestServiceImpl` (service role) |
| **Methods – REST Endpoints** | Verb‑noun pattern, lower‑camelCase, annotated with `@GetMapping`, `@PostMapping` etc. | `getDeedEntryById`, `createReport`, `deleteNumberGap` |
| **REST URLs** | `/api/v1/<resource>`; versioning in the path. | `/api/v1/deed-entries`, `/api/v1/reports` |
| **Constants** | Upper‑case with underscores, prefixed by component name if needed. | `MAX_RETRY_COUNT`, `DEED_ENTRY_TABLE` |

### 2.3.2 Code Style & Formatting

* **Indentation:** 4 spaces, no tabs.
* **Line Length:** ≤ 120 characters.
* **Braces:** K&R style (`{` on same line).
* **Imports:** Ordered alphabetically, one per line, no wildcard imports.
* **Annotations:** All Spring stereotypes (`@RestController`, `@Service`, `@Repository`) must be present on the class declaration.
* **Checkstyle/SpotBugs:** Enforced via Gradle plugins; failures break the CI build.

### 2.3.3 API Design Conventions

| **Aspect** | **Rule** |
|---|---|
| **Versioning** | Path‑based version (`/api/v1/...`). Increment major version only on breaking changes. |
| **Error Handling** | Centralised via `DefaultExceptionHandler`; error payload follows RFC 7807 problem‑details JSON. |
| **Pagination** | `page` and `size` query parameters on collection endpoints; response includes `totalElements`. |
| **Sorting** | Optional `sort` parameter (`field,asc|desc`). |
| **Security** | All endpoints require a Bearer token; scopes are validated by `CustomMethodSecurityExpressionHandler`. |
| **Hypermedia** | Not used – plain JSON responses to keep payloads lightweight. |

### 2.3.4 Documentation Conventions

* **OpenAPI**: Every public controller method must have `@Operation` annotation with summary, description, and response schema.
* **JavaDoc**: Mandatory for public classes and methods; must include `@since` tag.
* **README**: Each module (`backend`, `frontend`, `jsApi`) contains a `README.md` with build, test and run instructions.

---

*All constraints listed above are derived from the actual artefacts present in the code base (container definitions, class naming patterns, DAO implementations, security configuration classes) and from the organisational setup observed in the CI/CD pipeline and repository structure.*

---
