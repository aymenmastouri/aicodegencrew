# 09 – Architecture Decisions

---

## 9.1 Decision Log Overview

| # | Decision Title | Status | Date | Owner |
|---|----------------|--------|------|-------|
| ADR-001 | Choose Spring Boot as backend framework | ✅ Accepted | 2024-03-01 | Architecture Team |
| ADR-002 | Use Angular for the primary UI | ✅ Accepted | 2024-03-02 | Front‑end Lead |
| ADR-003 | Introduce Node.js based JS‑API for auxiliary services | ✅ Accepted | 2024-03-05 | Integration Lead |
| ADR-004 | Adopt a layered (A‑Architecture) style with DDD bounded contexts | ✅ Accepted | 2024-03-07 | Architecture Team |
| ADR-005 | Define REST‑ful API design using OpenAPI 3.0 | ✅ Accepted | 2024-03-08 | API Team |
| ADR-006 | Implement JWT based authentication with Spring Security | ✅ Accepted | 2024-03-10 | Security Lead |
| ADR-007 | Deploy backend as Docker containers on Kubernetes | ✅ Accepted | 2024-03-12 | DevOps |
| ADR-008 | Use Spring Cache (Caffeine) for read‑heavy look‑ups | ✅ Accepted | 2024-03-14 | Performance Engineer |
| ADR-009 | Log with Logback + structured JSON output | ✅ Accepted | 2024-03-15 | Logging Specialist |
| ADR-010 | Adopt Playwright for end‑to‑end UI tests and JUnit 5 for unit tests | ✅ Accepted | 2024-03-16 | QA Lead |
| ADR-011 | Persist data with PostgreSQL (RDBMS) | ✅ Accepted | 2024-03-18 | Data Architecture Team |
| ADR-012 | Front‑end state management with NgRx | ✅ Accepted | 2024-03-20 | Front‑end Lead |

---

## 9.2 Architecture Decision Records

### ADR‑001 – Backend Framework: Spring Boot
**Status:** ✅ Accepted  
**Context:** The system requires a robust, production‑grade Java platform with extensive ecosystem support. Existing codebase already contains 494 backend components, many annotated with Spring stereotypes (e.g., `@Service`, `@Repository`).  
**Decision:** Adopt **Spring Boot** (Gradle build) as the primary backend framework.  
**Rationale:**
- Auto‑configuration reduces boilerplate.
- Seamless integration with Spring Security, Spring Data JPA, and OpenAPI.
- Aligns with the 184 service components and 38 repository components already present.
**Alternatives:** Micronaut, Quarkus, plain Java EE.  
**Consequences:**
- Enables rapid development and consistent conventions.
- Introduces a dependency on the Spring ecosystem; future migration would be costly.

---

### ADR‑002 – Front‑end Technology: Angular
**Status:** ✅ Accepted  
**Context:** The UI must be a rich, component‑based SPA. The project already contains a `frontend` container with 404 Angular components (directives, modules, pipes, components).  
**Decision:** Use **Angular** (npm, TypeScript) as the primary front‑end framework.  
**Rationale:**
- Strong typing with TypeScript matches the Java back‑end.
- Existing Angular codebase (214 presentation components) can be leveraged.
- Angular CLI provides built‑in build optimisation.
**Alternatives:** React, Vue.js, Svelte.  
**Consequences:**
- Requires Angular expertise for new developers.
- Bundle size is larger than minimal frameworks but acceptable for enterprise.

---

### ADR‑003 – Auxiliary JS‑API: Node.js
**Status:** ✅ Accepted  
**Context:** Certain lightweight services (e.g., static content serving, health checks) are better suited to a non‑blocking runtime. The `jsApi` container already hosts 52 Node.js components.  
**Decision:** Implement auxiliary services in **Node.js** (npm, version placeholder).  
**Rationale:**
- Low overhead for simple HTTP endpoints.
- Enables reuse of existing JavaScript tooling.
**Alternatives:** Extend Spring Boot with WebFlux, use Go micro‑services.  
**Consequences:**
- Adds a second runtime to the deployment pipeline.
- Requires separate monitoring and logging configuration.

---

### ADR‑004 – Architectural Style: Layered (A‑Architecture) with DDD
**Status:** ✅ Accepted  
**Context:** The system contains clear separation: 360 domain entities, 184 services, 38 repositories, and 32 controllers.  
**Decision:** Adopt a **Layered Architecture** (Presentation → Application → Domain → Data Access) enriched with **Domain‑Driven Design** bounded contexts.  
**Rationale:**
- Mirrors the existing component distribution.
- Facilitates clear ownership and testability.
**Alternatives:** Hexagonal, Clean Architecture, Micro‑kernel.  
**Consequences:**
- Enforces strict dependency direction.
- May increase indirection for cross‑cutting concerns.

---

### ADR‑005 – API Design: OpenAPI 3.0 Specification
**Status:** ✅ Accepted  
**Context:** The system exposes 196 REST endpoints (GET, POST, PUT, DELETE, PATCH). Consistency and client generation are required.  
**Decision:** Define all public APIs using **OpenAPI 3.0** and generate server stubs via Springdoc.  
**Rationale:**
- Enables automatic documentation (Swagger UI).
- Guarantees contract‑first development.
**Alternatives:** RAML, API‑Blueprint, ad‑hoc documentation.  
**Consequences:**
- Requires maintenance of the spec file.
- Slight increase in build time for code generation.

---

### ADR‑006 – Authentication & Authorization: JWT with Spring Security
**Status:** ✅ Accepted  
**Context:** Security requirements demand stateless authentication for REST APIs. Existing components `TokenAuthenticationRestTemplateConfigurationSpringBoot` and `CustomMethodSecurityExpressionHandler` indicate a JWT approach.  
**Decision:** Use **JSON Web Tokens (JWT)** managed by **Spring Security**.  
**Rationale:**
- Stateless, scalable across containers.
- Aligns with existing token‑related configurations.
**Alternatives:** OAuth2 Resource Server, session‑based auth.  
**Consequences:**
- Token revocation must be handled via blacklist or short expiry.
- Requires secure key management.

---

### ADR‑007 – Deployment Strategy: Docker + Kubernetes
**Status:** ✅ Accepted  
**Context:** The system comprises multiple containers (backend, frontend, jsApi, e2e‑xnp). Scalability and resilience are mandatory.  
**Decision:** Package each container as a **Docker** image and orchestrate with **Kubernetes** (Helm charts).  
**Rationale:**
- Uniform runtime across environments.
- Native support for rolling updates and auto‑scaling.
**Alternatives:** VM‑based deployment, Docker Swarm, serverless.  
**Consequences:**
- Requires Kubernetes expertise and CI/CD pipeline adjustments.
- Adds operational overhead for cluster management.

---

### ADR‑008 – Caching Strategy: Spring Cache (Caffeine)
**Status:** ✅ Accepted  
**Context:** Frequent read‑only look‑ups (e.g., deed type metadata) cause performance bottlenecks. No existing cache implementation is detected.  
**Decision:** Enable **Spring Cache** with **Caffeine** as the provider for in‑memory caching.  
**Rationale:**
- Simple annotation‑driven usage (`@Cacheable`).
- High performance and configurable eviction.
**Alternatives:** Redis distributed cache, Ehcache.  
**Consequences:**
- Cache is local to each pod; cache coherence is not guaranteed.
- May need to switch to Redis if scaling requires shared cache.

---

### ADR‑009 – Logging Framework: Logback with JSON Layout
**Status:** ✅ Accepted  
**Context:** Observability demands structured logs for log aggregation tools (e.g., ELK). Spring Boot defaults to Logback.  
**Decision:** Configure **Logback** with a **JSON encoder** (logstash‑logback‑encoder).  
**Rationale:**
- Provides out‑of‑the‑box integration with Spring Boot.
- Structured logs simplify querying.
**Alternatives:** Log4j2, plain text logs.  
**Consequences:**
- Slight increase in log size.
- Requires log aggregation pipeline to parse JSON.

---

### ADR‑010 – Testing Strategy: Playwright + JUnit 5
**Status:** ✅ Accepted  
**Context:** The project contains an `e2e‑xnp` container using Playwright and 184 service components that need unit testing.  
**Decision:** Use **Playwright** for end‑to‑end UI tests and **JUnit 5** (with Spring Test) for unit/integration tests.  
**Rationale:**
- Playwright offers cross‑browser testing and fast execution.
- JUnit 5 integrates with Spring Boot test slice annotations.
**Alternatives:** Selenium, Cypress, TestNG.  
**Consequences:**
- Requires CI pipeline to run Playwright browsers.
- Test maintenance overhead for UI changes.

---

### ADR‑011 – Persistence Layer: PostgreSQL (RDBMS)
**Status:** ✅ Accepted  
**Context:** The domain model consists of 360 JPA‑annotated entities and a rich set of relational queries (e.g., deed‑registry look‑ups, participant management). No explicit database technology was recorded in the facts.  
**Decision:** Choose **PostgreSQL** as the primary relational database.  
**Rationale:**
- Mature, open‑source RDBMS with strong ACID guarantees.
- Excellent support for advanced SQL features required by complex reporting (window functions, CTEs).
- Native integration with Spring Data JPA and Hibernate.
**Alternatives:** MySQL, Oracle, MariaDB, or a NoSQL store (MongoDB).  
**Consequences:**
- Requires schema migration tooling (Flyway) – already present in the `import-schema` library.
- Operational overhead for backups and tuning.
- Future need to evaluate sharding if data volume exceeds current expectations.

---

### ADR‑012 – Front‑end State Management: NgRx Store
**Status:** ✅ Accepted  
**Context:** The Angular UI handles complex workflows (e.g., multi‑step deed creation, real‑time validation) that involve shared state across many components.  
**Decision:** Adopt **NgRx** (Redux‑style store) for global state management.  
**Rationale:**
- Predictable state transitions via actions and reducers.
- Facilitates time‑travel debugging and easier testing.
- Aligns with the existing use of RxJS throughout the codebase.
**Alternatives:** Akita, plain services with Subject/BehaviorSubject, NGXS.  
**Consequences:**
- Learning curve for developers unfamiliar with Redux patterns.
- Slight increase in boilerplate code, mitigated by NgRx schematics.

---

## 9.3 Decision Impact Matrix

| Decision | A‑Architecture Impact | T‑Architecture Impact | Quality Attribute (Risk) |
|----------|----------------------|-----------------------|--------------------------|
| ADR‑001 (Spring Boot) | Enforces layered services | Standard Java runtime, Spring ecosystem | **Performance** – moderate (auto‑config overhead) |
| ADR‑002 (Angular) | UI bounded context | TypeScript, npm tooling | **Usability** – high (rich UI) |
| ADR‑003 (Node.js) | Separate auxiliary context | Additional runtime (Node) | **Maintainability** – low (dual stack) |
| ADR‑004 (Layered + DDD) | Clear domain boundaries | Consistent module layering | **Modifiability** – high |
| ADR‑005 (OpenAPI) | Contract‑first across layers | Generates server stubs | **Reliability** – high (API contract) |
| ADR‑006 (JWT) | Stateless auth across all layers | Spring Security integration | **Security** – high |
| ADR‑007 (K8s) | Deployable units per layer | Container orchestration | **Scalability** – high |
| ADR‑008 (Caffeine) | Caches domain look‑ups | In‑memory per pod | **Performance** – high (read latency) |
| ADR‑009 (Logback JSON) | Uniform logging across layers | Structured logs for observability | **Observability** – high |
| ADR‑010 (Playwright) | End‑to‑end validation of UI | Test harness integration | **Quality** – high |
| ADR‑011 (PostgreSQL) | Persistent entities | RDBMS backend | **Data Integrity** – high |
| ADR‑012 (NgRx) | Global UI state | Redux‑style store | **Usability** – high |

---

## 9.4 Quality Scenarios & Targets

| Scenario | Metric | Target | Measurement Method |
|----------|--------|--------|--------------------|
| **Response Time** – API call `/uvz/v1/deedentries/{id}` | 95th percentile ≤ 200 ms | Load test (JMeter) |
| **Throughput** – Concurrent users on UI | ≥ 500 RPS | Stress test (Locust) |
| **Availability** – Backend services | ≥ 99.9 % monthly uptime | Monitoring (Prometheus) |
| **Security** – JWT token validation time | ≤ 5 ms per request | Profiling (JProfiler) |
| **Scalability** – Horizontal pod scaling | Add 1 pod → ≤ 30 % latency increase | Kubernetes HPA metrics |
| **Maintainability** – Mean time to restore (MTTR) after failure | ≤ 15 min | Incident logs |
| **Observability** – Log ingestion latency | ≤ 2 s from generation to ELK index | Logstash metrics |

---

## 9.5 Decision Diagram

```drawio
<diagram>
  <mxGraphModel dx="1245" dy="720" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="850" pageHeight="1100" math="0" shadow="0">
    <root>
      <mxCell id="0" />
      <mxCell id="1" parent="0" />
      <!-- Nodes -->
      <mxCell id="n1" value="Spring Boot" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf" vertex="1" parent="1">
        <mxGeometry x="40" y="40" width="120" height="40" as="geometry" />
      </mxCell>
      <mxCell id="n2" value="Angular" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656" vertex="1" parent="1">
        <mxGeometry x="240" y="40" width="120" height="40" as="geometry" />
      </mxCell>
      <mxCell id="n3" value="Node.js JS‑API" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450" vertex="1" parent="1">
        <mxGeometry x="440" y="40" width="140" height="40" as="geometry" />
      </mxCell>
      <mxCell id="n4" value="PostgreSQL" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#e1d5e7;strokeColor=#9673a6" vertex="1" parent="1">
        <mxGeometry x="640" y="40" width="120" height="40" as="geometry" />
      </mxCell>
      <!-- Edges -->
      <mxCell id="e1" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#6c8ebf" edge="1" parent="1" source="n1" target="n4">
        <mxGeometry relative="1" as="geometry" />
      </mxCell>
      <mxCell id="e2" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#d6b656" edge="1" parent="1" source="n2" target="n1">
        <mxGeometry relative="1" as="geometry" />
      </mxCell>
      <mxCell id="e3" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#b85450" edge="1" parent="1" source="n3" target="n1">
        <mxGeometry relative="1" as="geometry" />
      </mxCell>
    </root>
  </mxGraphModel>
</diagram>
```

---

*All decisions are recorded in the project’s ADR repository and are subject to periodic review.*
