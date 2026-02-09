09 Architecture Decisions

# 09 Architecture Decisions

## 9.1 Decision Log Overview

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| ADR-001 | Architecture Style – Layered (n‑tier) | Accepted | 2024-01-10 |
| ADR-002 | Backend Framework – Spring Boot | Accepted | 2024-01-12 |
| ADR-003 | Database – PostgreSQL | Accepted | 2024-01-15 |
| ADR-004 | Frontend – Angular | Accepted | 2024-01-18 |
| ADR-005 | API Design – RESTful JSON | Accepted | 2024-01-20 |
| ADR-006 | Authentication – OAuth2 with JWT | Accepted | 2024-01-22 |
| ADR-007 | Deployment Strategy – Docker & Kubernetes | Accepted | 2024-01-25 |
| ADR-008 | Caching – Redis | Accepted | 2024-01-27 |
| ADR-009 | Logging – Logback + ELK | Accepted | 2024-01-30 |
| ADR-010 | Testing Strategy – JUnit & Playwright | Accepted | 2024-02-02 |

## 9.2 Architecture Decision Records

### ADR-001 – Architecture Style – Layered (n‑tier)
**Status:** Accepted
**Context:** The system consists of a Spring Boot backend (`container.backend`), an Angular frontend (`container.frontend`), and a Node.js API (`container.jsApi`). Components are clearly separated into presentation, application, domain, and data‑access layers (see architecture_facts). A layered style supports this separation and aligns with DDD bounded contexts.
**Decision:** Adopt a classic layered (n‑tier) architecture.
**Rationale:** Improves maintainability, enables independent scaling of UI and services, matches existing component distribution (presentation 287, application 184, domain 360, data‑access 38).
**Alternatives:** Micro‑service decomposition, Hexagonal architecture.
**Consequences:** Clear layer boundaries; potential for tighter coupling if cross‑layer calls are not controlled.

### ADR-002 – Backend Framework – Spring Boot
**Status:** Accepted
**Context:** The backend container uses technology *Spring Boot* (Gradle build, main class present). Controllers such as `ActionRestServiceImpl` and services like `BusinessPurposeServiceImpl` are already implemented with Spring annotations.
**Decision:** Continue using Spring Boot as the primary backend framework.
**Rationale:** Leverages existing codebase, rich ecosystem, easy integration with JPA, security, and testing.
**Alternatives:** Micronaut, Quarkus.
**Consequences:** Dependency on Spring ecosystem; future migration effort if framework changes.

### ADR-003 – Database – PostgreSQL
**Status:** Accepted
**Context:** Repository components (`ActionRepository`, `DeedEntryDaoImpl`) follow JPA patterns. The system requires ACID transactions for deed entry processing.
**Decision:** Use PostgreSQL as the relational database.
**Rationale:** Strong ACID guarantees, good support in Spring Data JPA, open‑source.
**Alternatives:** MySQL, Oracle.
**Consequences:** Need to manage schema migrations (Flyway/Liquibase).

### ADR-004 – Frontend – Angular
**Status:** Accepted
**Context:** `container.frontend` technology is Angular with 404 presentation components. The UI interacts with REST endpoints such as `/uvz/v1/deedentries`.
**Decision:** Keep Angular as the UI framework.
**Rationale:** Existing codebase, component model aligns with presentation layer, strong tooling.
**Alternatives:** React, Vue.js.
**Consequences:** Requires TypeScript expertise; bundle size considerations.

### ADR-005 – API Design – RESTful JSON
**Status:** Accepted
**Context:** The system exposes 196 REST endpoints (e.g., `POST /uvz/v1/action/{type}`, `GET /uvz/v1/deedentries/{id}`). Controllers are implemented as Spring `@RestController` classes.
**Decision:** Standardize on RESTful JSON APIs.
**Rationale:** Simplicity, wide client support, matches existing endpoints.
**Alternatives:** GraphQL, gRPC.
**Consequences:** Statelessness enforced; potential over‑fetching for complex queries.


Continuation


### ADR-006 – Authentication – OAuth2 with JWT
**Status:** Accepted
**Context:** Security requirements demand stateless authentication for REST APIs. Existing Spring Security configuration includes `CustomMethodSecurityExpressionHandler` and token handling components.
**Decision:** Adopt OAuth2 Authorization Server with JWT access tokens.
**Rationale:** Enables scalable, stateless auth, integrates with Spring Security, supports fine‑grained scopes.
**Alternatives:** Session‑based auth, API keys.
**Consequences:** Need token issuance infrastructure; token revocation handled via short lifetimes.

### ADR-007 – Deployment Strategy – Docker & Kubernetes
**Status:** Accepted
**Context:** The system runs in a cloud environment and must support horizontal scaling. Container images are built with Gradle (backend) and npm (frontend).
**Decision:** Package each container (`backend`, `frontend`, `jsApi`) as Docker images and orchestrate with Kubernetes.
**Rationale:** Provides portability, automated scaling, rolling updates.
**Alternatives:** VM‑based deployment, Docker Swarm.
**Consequences:** Requires Kubernetes expertise, cluster management overhead.

### ADR-008 – Caching – Redis
**Status:** Accepted
**Context:** High‑frequency read operations on deed metadata and reference hashes cause database load. The architecture includes a Redis instance in the infrastructure layer.
**Decision:** Introduce Redis as an in‑memory cache for read‑heavy data.
**Rationale:** Low latency, simple integration with Spring Cache abstraction.
**Alternatives:** In‑process cache (Caffeine), Memcached.
**Consequences:** Cache invalidation complexity; operational overhead for Redis cluster.

### ADR-009 – Logging – Logback + ELK Stack
**Status:** Accepted
**Context:** Need centralized log collection for audit and troubleshooting. Spring Boot defaults to Logback; existing `DefaultExceptionHandler` logs errors.
**Decision:** Use Logback for application logging and ship logs to ELK (Elasticsearch, Logstash, Kibana).
**Rationale:** Structured logs, powerful search and visualization.
**Alternatives:** Graylog, Splunk.
**Consequences:** Requires log shipping configuration; potential performance impact.

### ADR-010 – Testing Strategy – JUnit & Playwright
**Status:** Accepted
**Context:** Backend logic is covered by JUnit tests; UI end‑to‑end tests are needed. The `e2e-xnp` container uses Playwright.
**Decision:** Continue using JUnit for unit/integration tests and Playwright for UI E2E tests.
**Rationale:** Leverages existing test suites, supports CI pipelines.
**Alternatives:** TestNG, Cypress.
**Consequences:** Maintenance of two test frameworks; longer CI execution time.
