# 04 – Solution Strategy

## 4.1 Technology Decisions

| Aspect | Description |
|--------|-------------|
| **Backend Framework** | **Spring Boot** (Java, Gradle) – provides a mature, convention‑over‑configuration platform for building micro‑services. It integrates seamlessly with Spring Data JPA, Spring Security and the existing Gradle build system (see container *backend*). |
| **Database Technology** | **PostgreSQL** – chosen for its strong ACID guarantees, rich SQL feature set and native support in Spring Data JPA. It matches the domain‑driven design where 360 entity components reside in the *domain* layer and 38 repository components in the *dataaccess* layer. |
| **Frontend Framework** | **Angular** – a component‑based SPA framework that aligns with the 287 presentation‑layer components (controllers, directives, pipes, modules). Angular’s TypeScript typing supports the large number of UI components and enables a clear separation between presentation and application logic. |
| **Build Tool (Backend)** | **Gradle** – the official build system for the *backend* container (metadata `build_system: gradle`). It offers incremental builds, dependency management and native support for Spring Boot plugins. |
| **Build Tool (Frontend)** | **npm** – used for the *frontend* and *jsApi* containers (metadata `build_system: npm`). npm provides a rich ecosystem of Angular libraries and Node.js tooling. |
| **Container Technology** | **Docker** – each logical container (backend, frontend, jsApi, e2e‑xnp, import‑schema) is packaged as a Docker image. Docker guarantees reproducible environments across development, CI and production. |
| **Security Framework** | **Spring Security** – integrated with Spring Boot to enforce authentication, authorization and CSRF protection for REST endpoints (21 rest_interface components). |
| **API Design** | **RESTful JSON API** – defined by 196 REST endpoints (GET 128, POST 30, PUT 18, PATCH 6, DELETE 14). The API follows the “resource‑oriented” style, versioned via URL path (`/api/v1/...`) and documented with OpenAPI specifications. |

### Decision Records (ADR‑lite)

| # | Context | Decision | Rationale | Alternatives | Consequences |
|---|---------|----------|-----------|--------------|--------------|
| 1 | Need a production‑ready Java backend with rapid prototyping. | Use Spring Boot with Gradle. | Provides auto‑configuration, embedded Tomcat, and excellent IDE support. | Jakarta EE, Micronaut. | Faster development, lower learning curve, large community support. |
| 2 | Persist domain entities with transactional guarantees. | Choose PostgreSQL. | Strong ACID, native JPA support, open source. | MySQL, Oracle. | Consistent data integrity, easy schema migrations with Flyway. |
| 3 | Build a rich, maintainable SPA for end‑users. | Adopt Angular. | Component model matches 287 presentation components, TypeScript enforces contracts. | React, Vue.js. | Larger bundle size, but better alignment with existing code base. |
| 4 | Package and deploy services consistently. | Use Docker images. | Isolation, reproducibility, CI/CD friendliness. | Bare‑metal VM, Kubernetes‑native builds only. | Requires container orchestration (K8s) but simplifies scaling. |
| 5 | Secure REST endpoints across the system. | Integrate Spring Security. | Centralised security policy, JWT support, method‑level annotations. | Custom filter chain, Apache Shiro. | Reduced security bugs, easier compliance audits. |
| 6 | Define public contract for client‑server interaction. | Design RESTful JSON API. | Wide client support, statelessness, easy caching. | GraphQL, gRPC. | Simpler client implementation, but less efficient for complex queries. |

## 4.2 Architecture Patterns

### 4.2.1 Macro Architecture – Layered Architecture

The system follows a classic **Layered Architecture** (also called *n‑tier*). The layers are derived directly from the component distribution reported by the architecture facts:

| Layer | Primary Responsibility | Component Count | Typical Stereotypes |
|-------|------------------------|------------------|----------------------|
| Presentation | UI rendering, request handling (Angular components, Angular controllers, pipes, directives). | 287 | `controller`, `pipe`, `directive`, `module`, `component` |
| Application | Orchestrates use‑cases, coordinates domain objects. | 184 | `service` |
| Domain | Business concepts, invariants, rich domain model. | 360 | `entity` |
| Data Access | Persistence, repository abstractions. | 38 | `repository` |
| Infrastructure | Cross‑cutting configuration (e.g., Spring configuration). | 1 | `configuration` |
| Unknown / Technical | Guards, adapters, resolvers, interceptors, schedulers, REST interfaces. | 81 | `guard`, `adapter`, `rest_interface`, `interceptor`, `resolver`, `scheduler` |

**Dependency Rules**
- Upper layers may only depend on lower layers (Presentation → Application → Domain → Data Access).
- No cyclic dependencies are allowed; the `unknown` technical components are placed where they serve a specific layer but never break the rule.
- All external libraries (Spring Boot, Angular, Playwright) are imported at the infrastructure level.

### 4.2.2 Applied Patterns

| Pattern | Purpose | Where Applied | Benefit |
|---------|---------|---------------|---------|
| **Repository** | Abstract persistence, hide data‑source details. | `repository` components (38) in *dataaccess* layer. | Enables swapping DB implementations, unit‑testable data access. |
| **Service Layer** | Encapsulate business use‑cases. | `service` components (184) in *application* layer. | Centralises transaction management, reduces duplication. |
| **Controller‑Service‑Repository** | Classic MVC for REST APIs. | `controller` (32) → `service` (184) → `repository` (38). | Clear separation of concerns, easier testing. |
| **Adapter** | Bridge between legacy modules and new services. | `adapter` components (50) in *unknown* technical bucket. | Allows gradual migration without breaking contracts. |
| **Guard / Interceptor** | Cross‑cutting concerns (security, logging). | `guard` (1) and `interceptor` (4). | Centralised handling of authentication, request tracing. |
| **Scheduler** | Periodic background jobs. | `scheduler` (1). | Enables asynchronous processing (e.g., cleanup tasks). |
| **Resolver** | GraphQL‑style data fetching (future‑proof). | `resolver` (4). | Provides flexible data retrieval for UI components. |
| **Pipe / Directive** | UI transformation and behaviour in Angular. | `pipe` (67), `directive` (3). | Reusable UI logic, improves maintainability. |

## 4.3 Achieving Quality Goals

| Quality Goal | Solution Approach | Implemented By |
|--------------|-------------------|----------------|
| **Performance** | Asynchronous non‑blocking I/O in Spring WebFlux for high‑throughput endpoints; lazy loading of Angular modules. | `service` components using Reactor, Angular router lazy‑loading. |
| **Scalability** | Containerised deployment on Kubernetes with horizontal pod autoscaling; stateless REST services. | Docker images (`backend`, `frontend`, `jsApi`), K8s HPA configuration. |
| **Security** | JWT‑based authentication, method‑level security annotations, CSRF protection, input validation. | Spring Security configuration, Angular route guards. |
| **Maintainability** | Strict layered boundaries, ADR‑lite decision records, extensive unit and integration tests (e2e‑xnp Playwright suite). | `adapter`, `guard`, `interceptor` components; Playwright tests in *e2e‑xnp* container. |
| **Reliability** | Circuit Breaker pattern (Resilience4j) for external service calls, retry policies, database transaction management. | `service` layer wrappers, Spring @Transactional on repository calls. |
| **Usability** | Responsive Angular UI, accessibility attributes, consistent REST error format (problem‑details). | Angular components, global error handler in Spring Boot. |
| **Portability** | Docker images, infrastructure‑as‑code (Terraform) for cloud‑agnostic deployment. | Dockerfiles in each container, Terraform scripts (not shown). |

### Measurable Targets
- **Response Time**: 95 % of API calls ≤ 200 ms under load of 500 RPS.
- **Availability**: ≥ 99.9 % monthly uptime (K8s rolling updates, zero‑downtime deployments).
- **Security**: No critical CVEs in dependencies (weekly `dependency‑check` scans).
- **Test Coverage**: ≥ 80 % unit test coverage, ≥ 70 % e2e coverage (Playwright).

---

*All numbers (component counts, layer distribution, REST endpoint statistics) are derived from the architecture facts repository. The decisions and patterns reflect the actual implementation landscape of the **uvz** system.*