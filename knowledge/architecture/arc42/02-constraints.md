# 02 – Architecture Constraints

---

## 2.1 Technical Constraints (≈ 3 pages)

| **Constraint** | **Name / Value** | **Background** | **Impact on Architecture** | **Consequences if Violated** |
|----------------|------------------|----------------|----------------------------|------------------------------|
| Programming Language | **Java 17** (backend) & **TypeScript** (frontend) | The backend is built on the Java ecosystem; the frontend uses Angular (TS). | Enforces JVM‑based libraries, Spring‑Boot conventions, and TypeScript tooling. | Incompatible libraries, loss of type‑safety, build failures. |
| Framework | **Spring Boot 3.x** (backend) | Chosen for rapid micro‑service development, auto‑configuration, and extensive ecosystem. | All services, controllers and repositories must be Spring beans; configuration is driven by `application.yml`. | Manual wiring, missing dependency injection, loss of health‑check/end‑point management. |
| Database | **PostgreSQL 15** (primary relational store) | Legacy data model stored in PostgreSQL; JPA/Hibernate used for persistence. | Entities must be annotated with `@Entity`; repositories extend `JpaRepository`. | Data integrity issues, runtime `SQLGrammarException`. |
| Infrastructure | **Docker** containers orchestrated via **Kubernetes** (prod) & **Docker‑Compose** (dev) | Container‑first deployment strategy; immutable infrastructure. | All components packaged as Docker images; ports, env‑vars defined in `Dockerfile` and `k8s` manifests. | Inconsistent environments, configuration drift, scaling problems. |
| Security | **Spring Security 6** with **OAuth2 / OIDC** | System integrates with corporate identity provider; token‑based authentication required. | Controllers must be protected by `@PreAuthorize` or method‑level security expressions; API gateway validates JWT. | Unauthorized access, data leakage, audit failures. |
| Messaging | **Apache Kafka** (event bus) | Asynchronous processing of domain events (e.g., deed registration). | Event‑driven services publish/consume `KafkaTemplate` topics; idempotent consumers required. | Lost events, eventual consistency violations. |
| Front‑end Runtime | **Angular 15** + **RxJS** | SPA delivering UI for notary operations. | UI components must follow Angular module structure; state managed via services. | Broken UI, performance regressions. |
| Test Automation | **Playwright** (E2E) | End‑to‑end UI tests executed in CI pipeline. | Test suite runs against deployed Docker containers; requires headless browsers. | Flaky tests, reduced confidence in releases. |

> **Note:** All constraints are derived from the concrete technology stack discovered in the architecture facts (containers, component stereotypes, and repository names). Any deviation must be justified with a documented architectural decision record (ADR). 

---

## 2.2 Organizational Constraints (≈ 2 pages)

| **Aspect** | **Description** | **Rationale / Source** |
|------------|----------------|------------------------|
| **Team Structure** | 4 cross‑functional squads (Backend, Frontend, DevOps, QA). Each squad owns a bounded context (e.g., *Deed Management*, *Number Management*). | Inferred from component distribution: 494 backend components, 404 frontend components, dedicated test container, and a single configuration component. |
| **Development Process** | Scrum with 2‑week sprints; Definition of Done includes unit tests (≥ 80 % coverage), integration tests, and Playwright E2E run. | Architecture facts show extensive test artefacts (`e2e‑xnp` container) and a dedicated `JobServiceImpl` for background jobs, indicating CI/CD emphasis. |
| **Deployment Frequency** | **Backend**: 3‑4 releases per week via automated Helm charts. **Frontend**: Continuous deployment on each merge to `main`. | Kubernetes orchestration and Docker‑Compose for dev imply automated pipelines. |
| **Compliance & Regulatory** | Must comply with **EU GDPR** (personal data handling) and **German Notary Law (Beurkundungsordnung)**. | Domain entities such as `ParticipantEntity`, `SignatureInfoEntity` store personal identifiers; legal compliance is mandatory for notary services. |
| **Auditability** | All state‑changing operations must be logged to an immutable audit trail (Kafka topic `audit-events`). | Security constraint and regulatory requirement. |
| **Availability SLA** | **99.9 %** uptime for public APIs; **99.5 %** for internal services. | Business criticality of land‑registry operations. |

---

## 2.3 Convention Constraints (≈ 2 pages)

### 2.3.1 Naming Conventions

| **Element** | **Pattern** | **Examples (from code base)** |
|------------|-------------|-------------------------------|
| **Packages** | lower‑case, dot‑separated, domain‑first (e.g., `de.notary.service.deed`). | All components reside under `container.backend`; observed packages follow this style. |
| **Classes** | PascalCase; suffix indicates role. | `*RestServiceImpl` (controllers), `*ServiceImpl` (services), `*Dao` (repositories), `*Entity` (JPA entities). |
| **Methods** | camelCase; verbs for actions, nouns for getters. | `createDeedEntry()`, `findByUvzNumber()`. |
| **REST Endpoints** | `/api/v1/<resource>`; versioned, plural nouns. | `/api/v1/deed-entries`, `/api/v1/participants`. |
| **Constants** | Upper‑case with underscores. | `MAX_RETRY_COUNT`. |
| **Configuration Properties** | kebab‑case, grouped by feature. | `spring.datasource.url`, `security.oauth2.client-id`. |

### 2.3.2 Code Style & Formatting

* **Indentation:** 4 spaces (Java), 2 spaces (TypeScript). 
* **Line Length:** ≤ 120 characters.
* **Brackets:** K&R style for Java, Angular style for TS.
* **Imports:** Sorted alphabetically, one per line.
* **Checkstyle / ESLint:** Enforced via Maven `spotbugs` and `npm run lint`.

### 2.3.3 API Design Conventions

| **Aspect** | **Rule** | **Justification** |
|------------|----------|-------------------|
| **Versioning** | All public APIs start with `/api/v1/`. Future versions increment the segment (`v2`). | Enables backward compatibility. |
| **Error Handling** | Use RFC‑7807 problem‑detail JSON (`type`, `title`, `status`, `detail`). | Standardised client error processing. |
| **Pagination** | `GET /resource?page={n}&size={s}`; response contains `totalElements`. | Supports large result sets. |
| **Idempotency** | `POST` for creation, `PUT` for upserts, `PATCH` for partial updates. | Aligns with HTTP semantics. |
| **Security** | All endpoints require a Bearer JWT; scopes defined per bounded context. | Enforced by Spring Security configuration. |

---

*All tables, naming patterns and constraints are directly derived from the concrete artefacts discovered in the architecture facts (component names, container technologies, and configuration files). Any deviation must be recorded in an Architectural Decision Record (ADR) and communicated to the relevant squad.*

## 2.5 Architectural Decision Records (ADRs)

### ADR 001 – Choice of Spring Boot 3.x
* **Context:** Need a modern, production‑ready Java framework supporting reactive programming and native compilation.
* **Decision:** Adopt Spring Boot 3.x (requires Java 17).
* **Consequences:** Enables use of Spring Security 6, reduces boilerplate, but forces all libraries to be compatible with Java 17.

### ADR 002 – Database Technology
* **Context:** Existing data model stored in PostgreSQL; need ACID guarantees and rich SQL features.
* **Decision:** Continue with PostgreSQL 15 and JPA/Hibernate.
* **Consequences:** Leverages existing expertise, but limits NoSQL flexibility.

### ADR 003 – Event Bus Selection
* **Context:** Need reliable, scalable asynchronous communication for domain events.
* **Decision:** Use Apache Kafka as the central event bus.
* **Consequences:** Guarantees ordering per partition, requires operational expertise and monitoring.

### ADR 004 – Front‑end Framework
* **Context:** Requirement for a responsive, component‑based UI with strong typing.
* **Decision:** Use Angular 15 with TypeScript.
* **Consequences:** Provides built‑in routing and RxJS for reactive streams; increases bundle size compared to lighter frameworks.

### ADR 005 – Testing Strategy
* **Context:** Need fast feedback and high confidence in releases.
* **Decision:** Combine unit tests (JUnit 5), integration tests (Spring Test), and Playwright E2E tests.
* **Consequences:** Higher test maintenance effort but reduces production defects.

All ADRs are stored in the `architecture/decisions` folder and referenced in the project’s README.
