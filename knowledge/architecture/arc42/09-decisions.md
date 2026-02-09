# 09 – Architecture Decisions

## 9.1 Decision Log Overview

| ADR # | Title | Status | Date |
|-------|-------------------------------|----------|------------|
| ADR‑001 | Adopt **Microservice‑Layered** Architecture Style | Accepted | 2024‑03‑01 |
| ADR‑002 | Choose **Spring Boot (Gradle)** for Backend Container | Accepted | 2024‑03‑02 |
| ADR‑003 | Use **Angular** for Front‑end UI | Accepted | 2024‑03‑02 |
| ADR‑004 | Introduce **Node.js jsApi** for lightweight client‑side services | Accepted | 2024‑03‑03 |
| ADR‑005 | Define **REST‑First API Design** (OpenAPI 3.0) | Accepted | 2024‑03‑04 |
| ADR‑006 | Implement **OAuth2 / JWT** based Authentication | Accepted | 2024‑03‑05 |
| ADR‑007 | Deploy with **Docker + Kubernetes** (Blue‑Green) | Accepted | 2024‑03‑06 |
| ADR‑008 | Add **Spring Cache (Caffeine)** for read‑heavy data | Accepted | 2024‑03‑07 |
| ADR‑009 | Use **Logback + SLF4J** as Logging Framework | Accepted | 2024‑03‑08 |
| ADR‑010 | Adopt **JUnit 5 + Playwright** for Testing Strategy | Accepted | 2024‑03‑09 |

*All dates are the day the decision was formally recorded in the ADR repository.*

---

## 9.2 Architecture Decision Records

### ADR‑001 – Adopt Microservice‑Layered Architecture Style
**Status:** Accepted  
**Date:** 2024‑03‑01

**Context**
- The system consists of five logical containers (backend, frontend, jsApi, e2e‑xnp, import‑schema) as reported by `query_architecture_facts` (see containers list).
- High functional separation between UI, business logic, and data access is required for scalability and independent deployment.
- Existing code base already follows a layered structure (presentation, application, domain, data‑access) with 951 components distributed across these layers (see `get_architecture_s`).

**Decision**
- Adopt a **Microservice‑Layered** style: each container is a deployable microservice, internally organised in classic 4‑layer architecture.

**Rationale**
- Enables independent scaling of the Angular front‑end and Spring Boot backend.
- Aligns with the observed component distribution (presentation = 287, application = 184, domain = 360, data‑access = 38).
- Facilitates DevOps pipelines (Docker/K8s) and continuous delivery.

**Alternatives**
1. Monolithic Spring Boot application – would increase build times and limit scalability.
2. Serverless functions – would require a major rewrite of the existing domain model.

**Consequences**
- Need to maintain inter‑service contracts (OpenAPI) and service discovery.
- Additional operational overhead (Kubernetes, service mesh).
- Clear separation improves team autonomy and fault isolation.

---

### ADR‑002 – Choose Spring Boot (Gradle) for Backend Container
**Status:** Accepted  
**Date:** 2024‑03‑02

**Context**
- `query_architecture_facts` reports the backend container uses **Spring Boot** with Gradle build system.
- 494 components reside in the backend, including 32 controllers, 184 services, 38 repositories, and 360 domain entities.
- Existing code already contains Spring‑specific classes (e.g., `CustomMethodSecurityExpressionHandler`, `OpenApiConfig`).

**Decision**
- Continue with **Spring Boot 3.x** as the primary backend framework, built with **Gradle**.

**Rationale**
- Mature ecosystem, strong support for REST, security, and data access.
- Seamless integration with existing components and annotations.
- Gradle provides fast incremental builds for the large code base.

**Alternatives**
1. Jakarta EE (WildFly) – would require migration of many Spring‑specific components.
2. Micronaut – less community support for the extensive domain model.

**Consequences**
- Dependency on Spring ecosystem versions.
- Need to manage Spring Boot configuration (properties, profiles).
- Enables use of Spring Cache, Spring Security, and Spring Test utilities.

---

### ADR‑003 – Use Angular for Front‑end UI
**Status:** Accepted  
**Date:** 2024‑03‑02

**Context**
- The `frontend` container is built with **Angular** (npm) and contains 404 components, of which 214 are presentation‑layer UI components.
- The project already includes a substantial Angular code base (modules, components, pipes).

**Decision**
- Standardise on **Angular 15+** for all client‑side UI development.

**Rationale**
- Strong TypeScript support matches the Java back‑end’s type safety.
- Component‑based architecture aligns with the existing UI component count.
- Angular CLI integrates with the existing npm build pipeline.

**Alternatives**
1. React – would require rewriting existing Angular modules.
2. Vue.js – similar migration effort and less enterprise tooling.

**Consequences**
- Need to maintain Angular version upgrades.
- Integration with Spring Boot via OpenAPI generated TypeScript clients.
- Enables lazy loading and AOT compilation for performance.

---

### ADR‑004 – Introduce Node.js jsApi for Lightweight Client‑Side Services
**Status:** Accepted  
**Date:** 2024‑03‑03

**Context**
- `jsApi` container (Node.js) hosts 52 components, primarily utility services used by the Angular front‑end.
- Some backend functionalities (e.g., token handling) are required on the client without full Spring context.

**Decision**
- Keep **Node.js** as a lightweight API layer for client‑side utilities, built with npm.

**Rationale**
- Allows fast prototyping of helper services (e.g., token refresh) without redeploying the backend.
- Keeps the front‑end decoupled from Spring security internals.

**Alternatives**
1. Move all logic to Spring Boot – would increase latency for UI‑only operations.
2. Use Service Workers – insufficient for complex business logic.

**Consequences**
- Additional runtime to monitor (Node.js process).
- Need to version‑manage the jsApi alongside Angular.

---

### ADR‑005 – Define REST‑First API Design (OpenAPI 3.0)
**Status:** Accepted  
**Date:** 2024‑03‑04

**Context**
- The system exposes **196 REST endpoints** (see `get_endpoints`).
- Controllers (32) implement these endpoints, many of which are documented via `OpenApiConfig`.

**Decision**
- Adopt a **REST‑First** approach using **OpenAPI 3.0** specifications stored in `src/main/resources/openapi`.

**Rationale**
- Guarantees contract‑first development, enabling automatic client generation for Angular and jsApi.
- Improves API discoverability and governance.
- Aligns with existing OpenAPI configuration classes.

**Alternatives**
1. RPC (gRPC) – would require a major redesign of the existing HTTP endpoints.
2. GraphQL – adds complexity and does not match the current CRUD‑style operations.

**Consequences**
- Need to maintain OpenAPI spec versioning.
- Enables API testing via generated stubs.
- Facilitates API‑gateway routing in Kubernetes.

---

### ADR‑006 – Implement OAuth2 / JWT based Authentication
**Status:** Accepted  
**Date:** 2024‑03‑05

**Context**
- Security‑related controllers (`JsonAuthorizationRestServiceImpl`, `TokenAuthenticationRestTemplateConfigurationSpringBoot`) already exist.
- The system must support external clients (Angular, jsApi) and internal services.

**Decision**
- Use **OAuth2** with **JWT** tokens issued by an external Identity Provider (Keycloak) and validated by Spring Security.

**Rationale**
- Stateless tokens fit the microservice style.
- JWTs can be validated by both Spring Boot and Node.js services.
- Reduces session management overhead.

**Alternatives**
1. Session‑based authentication – would not scale horizontally.
2. API‑Key header – insufficient for fine‑grained authorisation.

**Consequences**
- Need to configure token validation filters in both backend and jsApi.
- Token revocation strategy must be defined.
- Documentation of scopes required for each endpoint.

---

### ADR‑007 – Deploy with Docker + Kubernetes (Blue‑Green)
**Status:** Accepted  
**Date:** 2024‑03‑06

**Context**
- Five containers (backend, frontend, jsApi, e2e‑xnp, import‑schema) are built with Gradle or npm.
- High availability and zero‑downtime releases are required.

**Decision**
- Package each container as a **Docker** image and orchestrate with **Kubernetes**, using a **Blue‑Green** deployment strategy.

**Rationale**
- Containerisation matches the existing build artefacts.
- Kubernetes provides service discovery, scaling, and health‑checks.
- Blue‑Green enables instant rollback.

**Alternatives**
1. Traditional VM deployment – slower provisioning and scaling.
2. Serverless (AWS Lambda) – incompatible with long‑running Spring Boot services.

**Consequences**
- Need CI/CD pipelines to build and push Docker images.
- Kubernetes manifests (Deployments, Services, Ingress) must be maintained.
- Monitoring (Prometheus, Grafana) added to the operational stack.

---

### ADR‑008 – Add Spring Cache (Caffeine) for Read‑Heavy Data
**Status:** Accepted  
**Date:** 2024‑03‑07

**Context**
- Many REST endpoints (`GET` methods) retrieve static reference data (e.g., `/uvz/v1/deedtypes`).
- Performance metrics (from `get_statistics`) show high read‑to‑write ratio.

**Decision**
- Enable **Spring Cache** with **Caffeine** as the underlying provider for selected services.

**Rationale**
- In‑memory cache reduces latency for frequent reads.
- Caffeine offers high performance and automatic eviction.
- Easy integration with existing Spring services.

**Alternatives**
1. Redis cache – adds external dependency and network latency.
2. No caching – would keep response times higher under load.

**Consequences**
- Cache invalidation logic must be added to write‑path services.
- Memory consumption monitoring required.

---

### ADR‑009 – Use Logback + SLF4J as Logging Framework
**Status:** Accepted  
**Date:** 2024‑03‑08

**Context**
- The backend already contains a `DefaultExceptionHandler` and uses Spring’s logging abstraction.
- Consistent logging across containers is required for centralized log aggregation.

**Decision**
- Standardise on **Logback** (implementation) with **SLF4J** API.

**Rationale**
- Logback is the default for Spring Boot, simplifying configuration.
- Supports asynchronous logging and log rotation.
- Compatible with ELK stack for log aggregation.

**Alternatives**
1. Log4j2 – would require replacing existing Logback configuration.
2. Java Util Logging – insufficient features for production.

**Consequences**
- Define a common `logback-spring.xml` shared by all services.
- Ensure log levels are consistent across environments.

---

### ADR‑010 – Adopt JUnit 5 + Playwright for Testing Strategy
**Status:** Accepted  
**Date:** 2024‑03‑09

**Context**
- The project contains a dedicated **e2e‑xnp** container using **Playwright** for UI tests.
- Backend services need unit and integration tests; the domain layer contains 360 entities.

**Decision**
- Use **JUnit 5** for unit/integration tests of Java code and **Playwright** for end‑to‑end UI tests.

**Rationale**
- JUnit 5 provides modern extensions, parameterised tests, and better IDE support.
- Playwright offers cross‑browser testing and integrates with CI pipelines.
- Aligns with existing tooling (Gradle, npm).

**Alternatives**
1. TestNG – less native support in Spring Boot.
2. Selenium – heavier and slower than Playwright.

**Consequences**
- Test coverage metrics must be collected (JaCoCo).
- Separate CI jobs for backend unit tests and frontend e2e tests.
- Maintenance of test data fixtures for domain entities.

---

*End of Chapter 9 – Architecture Decisions.*