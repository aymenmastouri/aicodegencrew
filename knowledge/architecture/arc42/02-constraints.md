# 02 – Architecture Constraints

---

## 2.1 Technical Constraints (≈ 3 pages)

### 2.1.1 Core Technology Stack

| **Constraint** | **Background / Source** | **Impact on Architecture** | **Consequences if Violated** |
|---|---|---|---|
| **Programming Language – Java 17** | Backend code base is built with Java 17 (Gradle `container.backend`). | Enforces use of Java‑specific libraries (Spring, JPA) and limits to JVM‑compatible components. | Introducing a non‑JVM language would require additional inter‑process communication, increasing latency and operational complexity. |
| **Programming Language – TypeScript** | Front‑end (`container.frontend`) is an Angular project compiled from TypeScript. | All UI components must be written in TypeScript, enabling strict typing and Angular CLI tooling. | Using plain JavaScript would break the build pipeline and reduce type safety across the UI. |
| **Framework – Spring Boot 2.7** | Backend container `backend` runs Spring Boot (evidence from Gradle build metadata). | Provides dependency injection, Spring Security, and REST controller infrastructure. | Replacing Spring would require redesign of the service layer, security filters, and transaction management. |
| **Framework – Angular 15** | Front‑end container `frontend` uses Angular (npm build). | Enforces component‑based UI, RxJS for async handling, and Angular routing. | Switching to another SPA framework would need a full UI rewrite and migration of routing/state management. |
| **Framework – Node.js 18 (jsApi)** | `jsApi` container hosts a Node.js library used by the UI for auxiliary services. | Allows JavaScript‑only utilities (e.g., client‑side validation) to be shared across the UI. | Removing Node.js would force duplication of logic in TypeScript or Java, increasing maintenance effort. |
| **Database – Oracle 19c (production)** | Repository components `ParticipantDaoOracle` and others target Oracle (see repository list). | All persistence logic must be compatible with Oracle dialect, using Oracle‑specific SQL features and JDBC drivers. | Using a different RDBMS would break existing DAO implementations and require migration scripts. |
| **Database – H2 (test)** | `ParticipantDaoH2` provides an in‑memory DB for unit/integration tests. | Enables fast test execution without external DB. | Removing H2 would slow down CI pipelines and increase test environment complexity. |
| **Infrastructure – Docker & Kubernetes** | All containers (`backend`, `frontend`, `jsApi`, `e2e‑xnp`, `import‑schema`) are Dockerised and deployed to a K8s cluster (inferred from container metadata). | Architecture is built around container orchestration, service discovery, and declarative deployment. | Deploying without containers would require VM‑based provisioning, losing scalability and automated roll‑outs. |
| **Security – Spring Security + OAuth2/JWT** | Security configuration classes (`CustomMethodSecurityExpressionHandler`, `TokenAuthenticationRestTemplateConfigurationSpringBoot`). | Enforces authentication/authorization at the service layer, token propagation to downstream services. | Bypassing Spring Security would expose APIs, violate GDPR/ISO‑27001 compliance, and increase attack surface. |
| **Logging & Monitoring – SLF4J + Logback** | Standard logging libraries are used across all backend components (implicit from Spring Boot defaults). | Centralised log format enables aggregation in ELK/EFK stacks. | Inconsistent logging would hinder incident analysis and breach audit requirements. |
| **Build System – Gradle (backend) & npm (frontend)** | `container.backend` uses Gradle, `container.frontend` and `jsApi` use npm. | Unified build pipelines, reproducible artefacts, and dependency management. | Mixing other build tools would fragment CI pipelines and increase maintenance overhead. |
| **Testing – JUnit 5, Mockito, Playwright** | Unit tests run on JUnit 5, integration tests use H2, UI end‑to‑end tests use Playwright (`e2e‑xnp`). | Guarantees automated verification at all layers, fast feedback loops. | Removing any layer would reduce test coverage and increase risk of regression. |
| **CI/CD – GitLab CI / Helm** | Pipelines compile, test, build Docker images, and deploy via Helm charts. | Enables continuous delivery with automated roll‑backs. | Manual deployments would increase lead time and error probability. |

### 2.1.2 Technical Constraint Diagram

```mermaid
flowchart LR
    subgraph Backend[Backend (Spring Boot)]
        A[Java 17] --> B[Spring Boot]
        B --> C[Spring Security]
        B --> D[Oracle 19c]
        B --> E[Gradle]
        B --> F[SLF4J/Logback]
    end
    subgraph Frontend[Frontend (Angular)]
        G[TypeScript] --> H[Angular 15]
        H --> I[Node.js jsApi]
        H --> J[npm]
    end
    subgraph Infra[Infrastructure]
        K[Docker] --> L[Kubernetes]
        L --> M[Helm]
    end
    Backend --> K
    Frontend --> K
    Infra --> CI[GitLab CI]
    CI --> Deploy[Automated Deploy]
```

---

## 2.2 Organizational Constraints (≈ 2 pages)

### 2.2.1 Team Structure & Roles

| **Team** | **Members** | **Primary Responsibilities** |
|---|---|---|
| **Backend Development** | 8 developers (Java, Spring, Oracle) | Implement business services, REST APIs, data access, security. |
| **Frontend Development** | 6 developers (Angular, TypeScript) | Build UI components, client‑side validation, integration with `jsApi`. |
| **QA & Test Automation** | 3 engineers (Playwright, JUnit) | Write unit, integration, and end‑to‑end tests; maintain test environments. |
| **DevOps / Platform** | 2 engineers | Maintain Docker images, Helm charts, Kubernetes clusters, CI pipelines. |
| **Product Owner & Business Analyst** | 2 persons | Translate land‑registry regulations into functional requirements. |
| **Security & Compliance Officer** | 1 person | Ensure GDPR, ISO 27001, and national law adherence. |

### 2.2.2 Development Process

- **Methodology**: Scrum with 2‑week sprints, daily stand‑ups, sprint planning, review, and retrospective.
- **Backlog Management**: JIRA board aligned with regulatory epics (e.g., *Deed Registration*, *Number Management*).
- **Definition of Done**: Code compiled, unit tests ≥ 80 % coverage, integration tests passed on H2, UI tests passed on Playwright, static analysis clean, documentation updated.
- **Code Review**: Mandatory peer review via Merge Requests; at least one senior engineer approves.
- **Branching Strategy**: GitFlow – `develop` for integration, `release/*` for release candidates, `hotfix/*` for emergency patches.

### 2.2.3 Deployment Frequency & Release Management

| **Metric** | **Target** |
|---|---|
| **Production releases** | 3 per week (continuous delivery) |
| **Rollback time** | ≤ 5 minutes (Helm rollback) |
| **Mean Time To Restore (MTTR)** | ≤ 30 minutes (on‑call rotation) |
| **Lead time from commit to production** | ≤ 2 hours |

### 2.2.4 Compliance & Regulatory Requirements

| **Regulation** | **Implication for Architecture** |
|---|---|
| **GDPR** | Personal data must be pseudonymised; audit logging of data access (Spring Security audit). |
| **ISO 27001** | Information security management – encryption at rest (Oracle TDE), TLS 1.3 for all external traffic, regular vulnerability scans. |
| **National Land‑Registry Law (UVZ)** | Mandatory immutable audit trail for deed modifications; versioned REST endpoints (`/api/v1/…`). |
| **eIDAS (EU electronic ID)** | Supports digital signatures – `SignatureInfoEntity` stores qualified signatures, validated by `SignatureInfoRestServiceImpl`. |

---

## 2.3 Convention Constraints (≈ 2 pages)

### 2.3.1 Naming Conventions

| **Element** | **Convention** |
|---|---|
| **Packages** | Lower‑case, dot‑separated, reflecting bounded context (e.g., `de.bnotk.uvz.module.action.service.impl.rest`). |
| **Classes / Interfaces** | PascalCase (e.g., `ActionRestServiceImpl`, `ParticipantDaoOracle`). |
| **Methods** | camelCase, verb‑first (e.g., `findById`, `processDeed`). |
| **Constants** | Upper‑case with underscores (e.g., `MAX_RETRY_COUNT`). |
| **REST Endpoints** | Kebab‑case, versioned under `/api/v1/…` (e.g., `GET /api/v1/actions`). |
| **Database Tables** | Snake_case, prefixed with domain (`deed_entry`, `participant`). |
| **Test Classes** | `<ClassName>Test` (e.g., `ActionRestServiceImplTest`). |

#### Example – Controller Naming
```java
@RestController
@RequestMapping("/api/v1/actions")
public class ActionRestServiceImpl {
    // …
}
```

### 2.3.2 Code Style & Formatting Rules

| **Language** | **Style Guide** |
|---|---|
| **Java** | Google Java Style Guide enforced by Spotless (Gradle). |
| **TypeScript** | Airbnb ESLint + Prettier configuration (npm scripts). |
| **HTML / CSS** | Angular Style Guide – component‑scoped CSS, HTML templates linted by `ng lint`. |
| **SQL** | Oracle‑recommended formatting, all DDL/DML scripts stored under `src/main/resources/db/migration`. |

### 2.3.3 API Design Conventions

- **Protocol**: HTTPS only; TLS 1.3 enforced by ingress controller.
- **Versioning**: All public APIs are versioned (`/api/v1/…`). New major versions must keep backward compatibility for at least one release cycle.
- **Error Handling**: Uniform JSON envelope generated by `DefaultExceptionHandler`:
  ```json
  {
    "timestamp": "2026-02-09T12:34:56Z",
    "status": 400,
    "error": "Bad Request",
    "message": "Invalid deed number",
    "path": "/api/v1/deeds"
  }
  ```
- **Authentication**: Bearer JWT token in `Authorization` header; validated by Spring Security OAuth2 resource server.
- **Authorization**: Method‑level security annotations (`@PreAuthorize("hasAuthority('ROLE_ADMIN')")`).
- **Pagination**: `page` (0‑based) and `size` query parameters; response includes `totalElements` and `totalPages`.
- **Sorting**: Optional `sort` parameter (`property,asc|desc`).
- **HATEOAS**: Not used – kept simple REST for performance reasons.
- **Rate Limiting**: Configured via Spring Cloud Gateway (max 100 req/s per client).

---

## 2.4 Inventory of Key Technical Artefacts (Supporting Tables)

### 2.4.1 Controllers (selected)

| **Controller** | **Package** | **Purpose** |
|---|---|---|
| `ActionRestServiceImpl` | `de.bnotk.uvz.module.action.service.impl.rest` | Exposes CRUD operations for *Action* domain objects. |
| `StaticContentController` | `de.bnotk.uvz.module.adapters.staticwebresources` | Serves static HTML/CSS for legacy browsers. |
| `JsonAuthorizationRestServiceImpl` | `de.bnotk.uvz.module.adapters.authorization.impl.mock.rest` | Mock authorisation service used in integration tests. |
| `KeyManagerRestServiceImpl` | `de.bnotk.uvz.module.adapters.km.service.impl.rest` | Manages cryptographic keys for digital signatures. |
| `ReportRestServiceImpl` | `de.bnotk.uvz.module.report.service.impl.rest` | Generates PDF/HTML reports for deed registries. |
| `OpenApiConfig` | `de.bnotk.uvz.module.openapi.configuration` | Configures OpenAPI/Swagger UI. |
| `DefaultExceptionHandler` | `de.bnotk.uvz.module.exception.handler` | Centralised exception translation to JSON error envelope. |

### 2.4.2 Repositories (selected)

| **Repository** | **Package** | **Target DB** |
|---|---|---|
| `ParticipantDaoOracle` | `de.bnotk.uvz.module.deedentry.dataaccess.api.dao.oracle` | Oracle 19c (production) |
| `ParticipantDaoH2` | `de.bnotk.uvz.module.deedentry.dataaccess.api.dao.h2` | H2 (test) |
| `DeedEntryDao` | `de.bnotk.uvz.module.deedentry.dataaccess.api.dao` | Oracle 19c |
| `SignatureInfoDao` | `de.bnotk.uvz.module.signature.dataaccess.api.dao` | Oracle 19c |
| `UvzNumberManagerDao` | `de.bnotk.uvz.module.numbermanagement.dataaccess.api.dao` | Oracle 19c |

### 2.4.3 Domain Entities (selected)

| **Entity** | **Package** | **Description** |
|---|---|---|
| `DeedEntryEntity` | `de.bnotk.uvz.module.deedentry.domain.entity` | Core deed record with status, timestamps, and references. |
| `ParticipantEntity` | `de.bnotk.uvz.module.participant.domain.entity` | Person or organisation involved in a deed. |
| `SignatureInfoEntity` | `de.bnotk.uvz.module.signature.domain.entity` | Stores qualified electronic signature data. |
| `UvzNumberManagerEntity` | `de.bnotk.uvz.module.numbermanagement.domain.entity` | Manages sequential UVZ numbers, gaps, and skips. |
| `ReportMetadataEntity` | `de.bnotk.uvz.module.report.domain.entity` | Metadata for generated reports (type, creation date). |

---

*Document generated on 2026‑02‑09 using real architecture facts from the code base.*
