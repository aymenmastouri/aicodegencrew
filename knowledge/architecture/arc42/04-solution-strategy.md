# 04 – Solution Strategy

*This chapter describes the concrete technical decisions, the architectural patterns applied, and how the solution meets the quality goals defined in Chapter 3.*

---

## 4.1 Technology Decisions (ADR‑lite)

| Decision Area | Context | Decision | Rationale | Alternatives | Consequences |
|---|---|---|---|---|---|
| **Backend Framework** | Need a mature, production‑ready Java stack with strong ecosystem for REST, security and data access. | **Spring Boot 3.x** (Gradle build) | Provides auto‑configuration, embedded servlet container, extensive community support, and seamless integration with Spring Security, Spring Data JPA, and Actuator. | Jakarta EE (WildFly), Micronaut, Quarkus | Standardised configuration, fast developer onboarding, larger binary size, but proven stability.
| **Database Technology** | Persistent storage for deed‑entry domain entities (≈199 entities) with transactional consistency and complex queries. | **Relational DB (PostgreSQL 15)** accessed via **Spring Data JPA / Hibernate** | Strong ACID guarantees, rich SQL features, mature tooling, matches existing JPA repositories (38 repository components). | MySQL, MariaDB, Oracle, NoSQL (MongoDB) | Requires schema migrations, but aligns with existing JPA DAO layer.
| **Frontend Framework** | Rich, responsive UI for deed‑entry management, with need for component reuse and strong typing. | **Angular 16** (npm, TypeScript) | Component‑based architecture, built‑in routing, RxJS for reactive streams, CLI for scaffolding. | React, Vue.js, Svelte | Larger bundle size, but provides opinionated structure that matches our domain‑driven modules.
| **Build Tool (Backend)** | Need reproducible builds, dependency management, and multi‑module support. | **Gradle Kotlin DSL** | Incremental builds, rich plugin ecosystem, easy integration with Docker and CI pipelines. | Maven, Ant | Slight learning curve, but faster builds and better multi‑project handling.
| **Build Tool (Frontend)** | Manage JavaScript/TypeScript dependencies and asset pipeline. | **npm + Angular CLI** | Standard for Angular projects, simple scripts, wide community support. | Yarn, pnpm, Vite | No major impact; npm is already used in the e2e Playwright container.
| **Container Technology** | Deployable artefacts must run consistently across environments (dev, test, prod). | **Docker** (single‑container per logical component: `backend`, `frontend`, `e2e-xnp`, `import-schema`) | Isolation, reproducibility, easy orchestration with Docker Compose/K8s. | Podman, OCI runtime, direct VM deployment | Requires container image maintenance, but aligns with CI/CD pipeline.
| **Security Framework** | Enforce authentication, authorization, and secure communication for REST APIs. | **Spring Security 6** (OAuth2 Resource Server) | Declarative security, integration with JWT, method‑level security, proven in enterprise.
| **API Design** | Public contract for UI and external consumers, need versioning and discoverability. | **RESTful API (OpenAPI 3.1)** generated from Spring MVC controllers (32 controllers) | Human‑readable, tooling support (Swagger UI), aligns with existing `rest_interface` components (21). | GraphQL, gRPC, SOAP | REST is already used; switching would require major refactor.

> **Note:** All decisions are documented in the project’s ADR repository (e.g., `adr/0001-use-spring-boot.md`).

---

## 4.2 Architecture Patterns

### 4.2.1 Macro Architecture – Layered Architecture

The solution follows a classic **Layered Architecture** (also called *N‑tier*). The layers are strictly ordered, and each layer may only depend on the one directly below it.

| Layer | Responsibility | Primary Stereotypes | Example Components |
|---|---|---|---|
| **Presentation** | UI handling, request routing, view models. | `controller`, `directive`, `component`, `module`, `pipe` | `DeedEntryController`, `DeedSuccessorPageComponent` |
| **Application** | Orchestrates use‑cases, transaction boundaries, service façade. | `service` | `DeedEntryServiceImpl`, `WorkflowService` |
| **Domain** | Core business concepts, invariants, entities. | `entity` | `DeedEntryEntity`, `OfficialActivityEntity` |
| **Data Access** | Persistence, repository abstractions, DAO implementations. | `repository` | `DeedEntryRepository`, `AnnualReportRepository` |
| **Infrastructure** | Cross‑cutting concerns (configuration, security, logging). | `configuration` | `ApplicationDataSourceProperties`, `SecurityConfig` |

**Dependency Rules**
- Presentation → Application (uses services)
- Application → Domain (manipulates entities) & Data Access (calls repositories)
- Data Access → Domain (maps entities)
- Infrastructure may be accessed by any layer but should be injected via interfaces.

### 4.2.2 Applied Patterns

| Pattern | Purpose | Where Applied | Benefit |
|---|---|---|---|
| **Model‑View‑Controller (MVC)** | Separate UI, request handling, and business logic. | Presentation layer (`@Controller`, Angular components). | Testable UI, clear separation of concerns. |
| **Repository** | Abstract persistence, hide ORM details. | Data Access layer (`Spring Data JPA` repositories). | Decouples domain from storage, enables swapping DBs. |
| **Service Layer** | Encapsulate use‑case orchestration. | Application layer (`@Service` beans). | Centralised transaction management, reusable business logic. |
| **DTO (Data Transfer Object)** | Transport data across boundaries without exposing entities. | REST controllers (`@RestController`), Angular services. | Prevents lazy‑loading issues, versioning flexibility. |
| **Factory** | Create complex domain objects. | Domain layer (entity factories). | Simplifies object creation, enforces invariants. |
| **Adapter** | Integrate external systems (e.g., external registry). | `adapter` stereotype (50 components). | Isolates third‑party APIs, eases testing. |
| **Interceptor / Guard** | Cross‑cutting request validation and security. | Spring Interceptors, Angular Route Guards. | Centralised pre‑processing, consistent security checks. |
| **Scheduler** | Periodic background jobs (e.g., report generation). | `scheduler` component (1). | Automates maintenance tasks. |

---

## 4.3 Achieving Quality Goals

| Quality Goal (from Chapter 3) | Solution Approach | Implemented By |
|---|---|---|
| **Performance** | - Asynchronous processing with Spring’s `@Async` and Angular RxJS. <br> - Database indexing on frequently queried columns (e.g., `uvzNr`). <br> - Pagination on REST endpoints (95 REST endpoints, 52 GET). | `PerformanceService`, `DeedEntryRepository` (custom queries), Angular `HttpClient` with caching. |
| **Scalability** | - Stateless REST services behind load balancer. <br> - Containerised deployment enables horizontal scaling (Docker/K8s). <br> - Separate read‑replica for reporting (via Spring Data). | `backend` Docker image, `frontend` Docker image, Kubernetes Deployment manifests (not shown). |
| **Security** | - Spring Security OAuth2 Resource Server with JWT validation. <br> - Angular route guards (`guard` stereotype) enforce client‑side access control. <br> - HTTPS enforced at ingress. | `SecurityConfig`, `JwtAuthenticationFilter`, Angular `AuthGuard`. |
| **Maintainability** | - Layered architecture with clear module boundaries. <br> - 173 service components, each adhering to single‑responsibility principle. <br> - Automated tests: unit (JUnit), integration (Spring Test), end‑to‑end (Playwright). | `service` components, `e2e-xnp` Playwright suite. |
| **Reliability** | - Transactional boundaries via Spring `@Transactional`. <br> - Retry mechanisms on external adapters. <br> - Health checks via Spring Actuator. | `DeedEntryServiceImpl`, `AdapterRetryPolicy`, Actuator endpoints. |
| **Usability** | - Angular Material UI library for consistent look‑and‑feel. <br> - Responsive design, accessible components. | `frontend` Angular components, CSS guidelines. |
| **Portability** | - Docker images abstract OS differences. <br> - Java 17 LTS and Node 20 LTS ensure long‑term support. | Dockerfiles in `backend/Dockerfile` and `frontend/Dockerfile`. |

---

## 4.4 Decision Rationale Summary

| # | Decision | Impact on Architecture |
|---|---|---|
| 1 | Spring Boot + Spring Security | Enables layered, declarative security; simplifies configuration; adds minimal runtime overhead. |
| 2 | PostgreSQL + JPA | Drives the domain‑centric repository pattern; ensures ACID compliance for deed entries. |
| 3 | Angular | Aligns UI with component‑driven presentation layer; leverages TypeScript for compile‑time safety. |
| 4 | Docker | Provides immutable runtime environments; supports CI/CD pipelines and cloud‑native deployment. |
| 5 | REST + OpenAPI | Guarantees discoverable contracts; facilitates client generation for Angular services. |

---

## 4.5 Risks & Mitigations

| Risk | Description | Mitigation |
|---|---|---|
| **Database Vendor Lock‑in** | Heavy reliance on PostgreSQL‑specific features (e.g., JSONB). | Abstract via Spring Data JPA, keep SQL portable, maintain migration scripts. |
| **Front‑end Performance** | Large Angular bundle may affect first‑paint. | Enable lazy loading of modules, use Angular Ivy tree‑shaking, CDN for static assets. |
| **Security Misconfiguration** | Incorrect JWT validation could expose APIs. | Automated security scans, integration tests for auth flows, strict CSP headers. |
| **Container Image Size** | Multi‑layer images may be large, slowing deployments. | Use multi‑stage builds, base images `eclipse-temurin:17-jre-alpine`. |
| **Operational Complexity** | Managing multiple containers (backend, frontend, e2e, import‑schema). | Orchestrate with Docker Compose for local dev, Kubernetes Helm charts for production. |

---

## 4.6 Summary

The **Solution Strategy** combines proven enterprise technologies (Spring Boot, PostgreSQL, Angular) with a disciplined layered architecture and a suite of well‑known design patterns. This foundation directly addresses the quality goals of performance, scalability, security, and maintainability while keeping the system portable and future‑proof through containerisation and clear ADR documentation.

*The next chapter (5 – Building Blocks) will detail the concrete components, their responsibilities, and the runtime interactions that realise the architecture described here.*
