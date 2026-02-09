# 09 – Architecture Decisions

## 9.1 Decision Log Overview

| ADR # | Title | Status | Date | Owner |
|------|-------------------------------|--------|------------|-------|
| 1 | Architecture Style – Layered (Hexagonal) | Accepted | 2024-03-01 | Architecture Team |
| 2 | Backend Framework – Spring Boot (Gradle) | Accepted | 2024-03-02 | Backend Lead |
| 3 | Frontend Framework – Angular 15 | Accepted | 2024-03-03 | Frontend Lead |
| 4 | API Gateway / JS API – Node.js (Express) | Accepted | 2024-03-04 | Integration Lead |
| 5 | Database – PostgreSQL (JPA/Hibernate) | Accepted | 2024-03-05 | Data Architecture |
| 6 | Authentication – OAuth2 / OpenID Connect (Keycloak) | Accepted | 2024-03-06 | Security Architect |
| 7 | Deployment Strategy – Kubernetes (Helm charts) | Accepted | 2024-03-07 | DevOps |
| 8 | Caching – Redis (Spring Cache) | Accepted | 2024-03-08 | Performance Engineer |
| 9 | Logging Framework – Logback + ELK Stack | Accepted | 2024-03-09 | Observability Lead |
|10| Testing Strategy – JUnit 5 + Playwright E2E | Accepted | 2024-03-10 | QA Lead |

*The table lists all Architecture Decision Records (ADRs) that are part of the current baseline. All decisions are **Accepted** and have been implemented in the code base.*

---

## 9.2 Architecture Decision Records

### ADR 1 – Architecture Style
**Status:** Accepted  
**Context:** The system consists of a rich domain model (360 entities), a large set of REST services (32 controllers, 184 services) and a substantial data‑access layer (38 repositories). The team needs clear separation of concerns, testability and the ability to evolve the domain independently of delivery mechanisms.
**Decision:** Adopt a **Layered (Hexagonal) Architecture** with explicit ports and adapters. The *application* layer (services) implements business use‑cases, the *domain* layer holds entities, the *infrastructure* layer provides Spring‑Boot adapters for persistence, security and external APIs.
**Rationale:**
- Aligns with DDD principles already reflected in the entity count.
- Enables independent evolution of UI (Angular) and API (Node.js) without touching core logic.
- Facilitates automated testing of the domain via plain JUnit.
**Alternatives considered:**
- Monolithic MVC – rejected due to tight coupling.
- Micro‑service decomposition – rejected because the current code base already provides clear module boundaries and the operational overhead would be disproportionate.
**Consequences:**
- Clear module boundaries reflected in package structure.
- Need for adapter interfaces (e.g., `ActionRestServiceImpl` implements a port).
- Documentation and onboarding must emphasize the hexagonal view.

---

### ADR 2 – Backend Framework
**Status:** Accepted  
**Context:** The backend must provide a robust, production‑grade REST API, integrate with JPA, support security extensions and be buildable with the existing Gradle ecosystem.
**Decision:** Use **Spring Boot 3.x** with Gradle as the build system.
**Rationale:**
- Spring Boot is already the technology of the `container.backend` (see container facts).
- Provides out‑of‑the‑box support for REST, security, caching and observability.
- Large community and proven stability for enterprise workloads.
**Alternatives considered:**
- Micronaut – rejected due to lack of existing expertise.
- Quarkus – rejected because of limited integration with existing Gradle scripts.
**Consequences:**
- All 32 controller classes (e.g., `ActionRestServiceImpl`, `ReportRestServiceImpl`) are Spring MVC REST controllers.
- Configuration is managed via `ProxyRestTemplateConfiguration` and `TokenAuthenticationRestTemplateConfigurationSpringBoot`.
- Enables easy migration to native images in the future.

---

### ADR 3 – Frontend Framework
**Status:** Accepted  
**Context:** The UI must be a modern, component‑based single‑page application with strong typing and tooling support.
**Decision:** Adopt **Angular 15** (TypeScript) for the `frontend` container.
**Rationale:**
- Angular is the declared technology of the `frontend` container.
- Provides built‑in routing, dependency injection and a mature ecosystem.
- Aligns with the existing `pipe`, `component`, `directive` and `module` stereotypes (total 287 presentation components).
**Alternatives considered:**
- React – rejected because the team already has Angular expertise.
- Vue – rejected due to smaller ecosystem for enterprise tooling.
**Consequences:**
- UI code lives in the `frontend` container (404 components).
- Integration with the backend via generated OpenAPI client (`OpenApiConfig`).
- Requires CI pipeline for Angular build (npm).

---

### ADR 4 – API Gateway / JS API
**Status:** Accepted  
**Context:** Certain external consumers need a lightweight JavaScript API that aggregates multiple backend endpoints.
**Decision:** Implement a **Node.js (Express) based JS API** in the `jsApi` container.
**Rationale:**
- The `jsApi` container already uses Node.js (see container facts).
- Allows fast prototyping and easy distribution as an npm package.
- Keeps the heavy business logic in Spring Boot while exposing a thin façade.
**Alternatives considered:**
- Direct consumption of Spring Boot endpoints – rejected because of CORS and versioning concerns.
- Serverless functions – rejected due to operational complexity.
**Consequences:**
- The JS API is versioned independently and published to the internal npm registry.
- Requires OAuth2 token forwarding to the backend.

---

### ADR 5 – Database Technology
**Status:** Accepted  
**Context:** Persistent storage must support ACID transactions, complex queries and be compatible with JPA/Hibernate.
**Decision:** Use **PostgreSQL 15** as the primary relational database.
**Rationale:**
- PostgreSQL integrates seamlessly with Spring Data JPA used by the 38 repository classes.
- Supports advanced data types needed for domain entities (e.g., JSONB for flexible metadata).
- Proven scalability for the expected load (≈200 REST endpoints).
**Alternatives considered:**
- Oracle – rejected due to licensing costs.
- MySQL – rejected because of missing advanced features.
**Consequences:**
- Database schema is generated from JPA entities (e.g., `DeedEntry`, `SignatureInfo`).
- Migration scripts are managed via Flyway.

---

### ADR 6 – Authentication & Authorization
**Status:** Accepted  
**Context:** The system must protect sensitive deed data and support single sign‑on across UI and API.
**Decision:** Deploy **Keycloak** as an external OAuth2 / OpenID Connect provider and integrate it with Spring Security.
**Rationale:**
- Keycloak provides out‑of‑the‑box user federation, role mapping and token introspection.
- The `CustomMethodSecurityExpressionHandler` and `JsonAuthorizationRestServiceImpl` already reference security expressions.
**Alternatives considered:**
- In‑house JWT implementation – rejected due to security risk and maintenance overhead.
- LDAP only – rejected because modern UI requires OIDC flows.
**Consequences:**
- All REST controllers are secured via method‑level annotations.
- Frontend obtains tokens via the standard OIDC flow.
- Token propagation is handled in the JS API.

---

### ADR 7 – Deployment Strategy
**Status:** Accepted  
**Context:** The application must be highly available, scalable and support blue‑green deployments.
**Decision:** Deploy the system on **Kubernetes** using **Helm charts** for each container (backend, frontend, jsApi, e2e‑xnp).
**Rationale:**
- Kubernetes matches the container‑based architecture (5 containers).
- Helm provides repeatable releases and parameterised configuration (e.g., DB connection strings).
- Enables horizontal scaling of the Spring Boot pods and Angular static assets via an Ingress.
**Alternatives considered:**
- Docker‑Compose – rejected for production due to lack of orchestration.
- VM‑based deployment – rejected because of scaling constraints.
**Consequences:**
- CI/CD pipelines now produce Docker images and Helm releases.
- Monitoring is integrated via Prometheus and Grafana.

---

### ADR 8 – Caching Strategy
**Status:** Accepted  
**Context:** Certain read‑heavy endpoints (e.g., `ReportRestServiceImpl`) suffer from latency under load.
**Decision:** Introduce **Redis** as a distributed cache, accessed via Spring Cache abstraction.
**Rationale:**
- Redis is already a common choice in the ecosystem and works well with Spring Boot.
- Provides low‑latency data access for frequently requested data (e.g., lookup tables).
**Alternatives considered:**
- In‑memory Caffeine cache – rejected because it does not survive pod restarts.
- Hazelcast – rejected due to operational overhead.
**Consequences:**
- Cache annotations added to service methods.
- Cache eviction policies defined per use‑case.
- Redis cluster is deployed as a StatefulSet in the same Kubernetes namespace.

---

### ADR 9 – Logging & Observability
**Status:** Accepted  
**Context:** The system must provide structured logs for troubleshooting and support audit requirements.
**Decision:** Use **Logback** as the logging framework in Spring Boot, ship logs to an **ELK stack** (Elasticsearch, Logstash, Kibana).
**Rationale:**
- Logback is the default for Spring Boot and supports JSON layout.
- ELK provides powerful search and dashboard capabilities.
- Aligns with the existing `DefaultExceptionHandler` which formats error responses.
**Alternatives considered:**
- Splunk – rejected due to cost.
- Loki – rejected because the team already has ELK expertise.
**Consequences:**
- All containers emit JSON logs.
- Kubernetes side‑car collects logs and forwards to Logstash.
- Kibana dashboards are created for request latency, error rates, and security events.

---

### ADR 10 – Testing Strategy
**Status:** Accepted  
**Context:** High reliability is required; both unit and end‑to‑end tests must be automated.
**Decision:** Combine **JUnit 5** for unit/integration tests (backend) with **Playwright** for UI E2E tests (frontend) and **Spring Test** for REST contract verification.
**Rationale:**
- JUnit 5 is the standard for Java and already used in the `e2e‑xnp` container (Playwright).
- Playwright provides cross‑browser testing and integrates with CI pipelines.
- The large number of REST endpoints (196) benefits from contract tests (`OpenApiOperationAuthorizationRightCustomizer`).
**Alternatives considered:**
- TestNG – rejected due to lack of native Spring support.
- Cypress – rejected because Playwright already covers the required browsers.
**Consequences:**
- Test coverage reports are generated per build.
- CI pipeline fails fast on unit test failures before UI tests run.
- Test data is seeded via the `MockKmService` and `XnpKmServiceImpl`.

---

*End of Chapter 9 – Architecture Decisions.*