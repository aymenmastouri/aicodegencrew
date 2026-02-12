# 09 – Architecture Decisions

---

## 9.1 Decision Log Overview

| ADR # | Title | Status | Date | Owner |
|-------|------------------------------|----------|------------|-------|
| ADR‑001 | Choose **Spring Boot** as the backend framework | Accepted | 2024‑03‑12 | Architecture Team |
| ADR‑002 | Adopt **Angular** for the web UI | Accepted | 2024‑03‑15 | Front‑end Lead |
| ADR‑003 | Use **Node.js** for the JavaScript API layer (jsApi) | Accepted | 2024‑03‑18 | Integration Team |
| ADR‑004 | Persist domain data with **PostgreSQL** (JPA/Hibernate) | Accepted | 2024‑03‑20 | Data Architecture |
| ADR‑005 | Expose **RESTful JSON** APIs via Spring MVC | Accepted | 2024‑03‑22 | API Team |
| ADR‑006 | Secure APIs with **OAuth2 / JWT** and Spring Security | Accepted | 2024‑03‑25 | Security Architect |
| ADR‑007 | Deploy services on **Kubernetes** (GKE) with Helm charts | Accepted | 2024‑04‑01 | DevOps |
| ADR‑008 | Introduce **Redis** as a distributed cache for read‑heavy look‑ups | Accepted | 2024‑04‑05 | Performance Engineer |
| ADR‑009 | Centralise logging with **ELK Stack** (Elastic, Logstash, Kibana) | Accepted | 2024‑04‑10 | Observability Lead |
| ADR‑010 | Adopt **JUnit 5** + **Testcontainers** for integration testing | Accepted | 2024‑04‑12 | QA Lead |

---

## 9.2 Architecture Decision Records

### ADR‑001 – Backend Framework: Spring Boot

**Status:** Accepted  
**Context:**
- The system requires a mature, production‑ready Java framework.
- Existing codebase heavily uses Spring annotations (e.g., `@RestController`, `@Service`).
- Need built‑in support for dependency injection, transaction management, and security.

**Decision:** Adopt **Spring Boot 3.x** as the primary backend framework.

**Rationale:**
- Provides auto‑configuration, reducing boilerplate.
- Strong ecosystem (Spring Security, Spring Data JPA) aligns with other ADRs (security, persistence).
- Compatible with Gradle build system used in `container.backend`.

**Alternatives Considered:**
- **Jakarta EE** – rejected due to higher configuration overhead.
- **Micronaut** – rejected because of limited team expertise.

**Consequences:**
- All new services must be Spring beans (`@Service`, `@Component`).
- Legacy code will be gradually refactored to Spring Boot conventions.
- Enables easy integration with Spring Cloud for future micro‑service patterns.

---

### ADR‑002 – Front‑end Technology: Angular

**Status:** Accepted  
**Context:**
- The UI must be a rich, component‑based single‑page application.
- Existing `container.frontend` uses Angular with a large component library (≈214 presentation components).

**Decision:** Standardise on **Angular 16** for the web UI.

**Rationale:**
- Strong TypeScript support matches the Java back‑end’s static typing.
- Angular CLI integrates with the existing npm build pipeline.
- Enables reuse of existing UI components and styling.

**Alternatives Considered:**
- **React** – rejected due to lack of existing code and required re‑training.
- **Vue.js** – rejected for similar reasons.

**Consequences:**
- All UI features must be implemented as Angular modules.
- Future UI work will follow the Angular style guide defined in the repository.

---

### ADR‑003 – JavaScript API Layer: Node.js

**Status:** Accepted  
**Context:**
- Some client‑side logic (e.g., file processing) is better served by a lightweight JavaScript runtime.
- `container.jsApi` already contains a Node.js project (technology: Node.js, build system npm).

**Decision:** Use **Node.js 20** for the auxiliary JavaScript API layer.

**Rationale:**
- Allows fast prototyping of utility endpoints.
- Keeps the Java back‑end focused on core business logic.
- Leverages existing npm tooling.

**Alternatives Considered:**
- Consolidate everything into Spring Boot – rejected due to performance concerns for CPU‑intensive JS tasks.
- Use Deno – rejected because of limited ecosystem.

**Consequences:**
- Deployment of the Node.js service will be containerised alongside Spring Boot services.
- Communication between Node.js and Spring Boot will use REST over HTTP.

---

### ADR‑004 – Persistence: PostgreSQL with JPA/Hibernate

**Status:** Accepted  
**Context:**
- Domain entities (e.g., `DeedEntryEntity`, `ParticipantEntity`) are annotated as JPA entities.
- Repositories such as `ActionDao`, `DeedEntryDao` follow Spring Data JPA naming conventions.

**Decision:** Use **PostgreSQL 15** as the relational database, accessed via **JPA/Hibernate**.

**Rationale:**
- PostgreSQL offers robust ACID compliance and advanced indexing needed for deed‑registry queries.
- JPA integrates seamlessly with Spring Data, reducing boilerplate DAO code.
- Existing Docker compose files already reference a PostgreSQL service.

**Alternatives Considered:**
- **MySQL** – rejected due to lack of needed JSONB features.
- **NoSQL (MongoDB)** – rejected because the domain model is highly relational.

**Consequences:**
- All entity classes must include proper JPA annotations (`@Entity`, `@Table`).
- Database migrations will be managed with Flyway.

---

### ADR‑005 – API Design: RESTful JSON over HTTP

**Status:** Accepted  
**Context:**
- The system exposes many services (e.g., `ActionRestServiceImpl`, `DeedEntryRestServiceImpl`).
- Clients include Angular front‑end and external partners.

**Decision:** Define a **RESTful JSON** API using Spring MVC (`@RestController`).

**Rationale:**
- Aligns with industry standards and tooling (Swagger/OpenAPI).
- Enables easy consumption by web browsers and mobile apps.
- Supports versioning via URL path (`/api/v1/...`).

**Alternatives Considered:**
- **GraphQL** – rejected due to higher learning curve and limited need for flexible queries.
- **gRPC** – rejected because of limited browser support.

**Consequences:**
- All public endpoints must be documented in the OpenAPI spec (`OpenApiConfig`).
- Controllers must return DTOs, not entities, to avoid leaking persistence details.

---

### ADR‑006 – Security: OAuth2 / JWT with Spring Security

**Status:** Accepted  
**Context:**
- Sensitive deed‑registry data requires strong authentication and fine‑grained authorisation.
- Existing components such as `CustomMethodSecurityExpressionHandler` indicate a custom security expression setup.

**Decision:** Implement **OAuth2** resource‑server flow with **JWT** tokens, using Spring Security.

**Rationale:**
- Stateless tokens fit the micro‑service architecture.
- JWTs can carry custom claims for fine‑grained authorisation (e.g., `right` claims used by `OpenApiOperationAuthorizationRightCustomizer`).
- Integration with existing Spring Security configuration is straightforward.

**Alternatives Considered:**
- **Session‑based authentication** – rejected for scalability.
- **API keys** – rejected due to insufficient granularity.

**Consequences:**
- All controllers must be secured with `@PreAuthorize` expressions.
- Token validation will be performed by a dedicated `TokenAuthenticationRestTemplateConfigurationSpringBoot` bean.

---

### ADR‑007 – Deployment: Kubernetes (GKE) with Helm

**Status:** Accepted  
**Context:**
- The system consists of multiple containers (`backend`, `frontend`, `jsApi`, `e2e-xnp`).
- Need automated scaling, self‑healing, and blue‑green deployments.

**Decision:** Deploy all services on **Google Kubernetes Engine (GKE)** using **Helm charts** for packaging.

**Rationale:**
- Kubernetes provides native support for rolling updates and health checks.
- Helm enables versioned, repeatable releases.
- GKE integrates with Google Cloud IAM for secret management.

**Alternatives Considered:**
- **Docker Swarm** – rejected due to limited feature set.
- **VM‑based deployment** – rejected for lack of elasticity.

**Consequences:**
- CI/CD pipelines will produce Docker images and Helm releases.
- Configuration (e.g., DB connection strings) will be injected via Kubernetes Secrets.

---

### ADR‑008 – Caching: Redis for Distributed Cache

**Status:** Accepted  
**Context:**
- Frequent read‑only look‑ups (e.g., `DeedTypeRestServiceImpl`) cause database load.
- Stateless services require a shared cache.

**Decision:** Introduce **Redis** as a distributed cache, accessed via Spring Cache abstraction.

**Rationale:**
- Low latency, in‑memory storage.
- Supports TTLs for cache invalidation.
- Works well with Kubernetes (stateful set or managed service).

**Alternatives Considered:**
- **Caffeine** – rejected because it is local to each JVM.
- **Hazelcast** – rejected due to operational complexity.

**Consequences:**
- Cacheable methods must be annotated with `@Cacheable`.
- Cache keys will follow a naming convention (`entity:{id}`).

---

### ADR‑009 – Logging & Observability: ELK Stack

**Status:** Accepted  
**Context:**
- Need centralised log aggregation for troubleshooting across services.
- Existing `DefaultExceptionHandler` and `OpenApiOperationAuthorizationRightCustomizer` produce structured logs.

**Decision:** Deploy **ElasticSearch**, **Logstash**, and **Kibana** (ELK) as the logging backbone.

**Rationale:**
- ElasticSearch provides powerful full‑text search.
- Kibana offers dashboards for metrics and error rates.
- Logstash can enrich logs with request IDs and correlation IDs.

**Alternatives Considered:**
- **EFK (Fluentd)** – rejected due to team familiarity with Logstash.
- **Splunk** – rejected for licensing cost.

**Consequences:**
- All services must log in JSON format.
- Logback configuration will ship logs to Logstash via TCP.

---

### ADR‑010 – Testing Strategy: JUnit 5 + Testcontainers

**Status:** Accepted  
**Context:**
- High reliability is required for deed‑registry operations.
- Existing test suite is minimal; need integration tests that run against real dependencies.

**Decision:** Use **JUnit 5** for unit tests and **Testcontainers** for integration tests against PostgreSQL and Redis.

**Rationale:**
- JUnit 5 provides modern extensions and parameterised tests.
- Testcontainers spin up lightweight Docker containers, ensuring environment parity.
- Aligns with the Gradle build system used in `container.backend`.

**Alternatives Considered:**
- **Spring Boot Test with embedded DB** – rejected because it does not test real DB behaviour.
- **Mocking frameworks only** – rejected for insufficient coverage.

**Consequences:**
- New modules must include a `src/test` directory with JUnit 5 tests.
- CI pipeline will start Docker daemon to run Testcontainers.

---

*End of Chapter 9 – Architecture Decisions.*
