# 09 - Architecture Decisions

## 9.1 Decision Log Overview

The following decision log captures the most significant architectural decisions made during the design and implementation of the **uvz** system. Each entry follows the ADR (Architecture Decision Record) template recommended by the SEAGuide and arc42 standards. The decisions are grouped by thematic areas (style, platform, data, security, deployment, etc.) and are linked to the corresponding rationale, alternatives considered, and downstream consequences.

| ADR | Title | Status | Area |
|-----|-------|--------|------|
| ADR-001 | Adopt Layered Architecture (A‑Architecture) | Accepted | Architecture Style |
| ADR-002 | Choose Spring Boot as Backend Framework | Accepted | Backend Platform |
| ADR-003 | Select PostgreSQL as Primary Database | Accepted | Data Management |
| ADR-004 | Use Angular for Front‑end UI | Accepted | Front‑end Platform |
| ADR-005 | Define RESTful API with OpenAPI 3.0 | Accepted | API Design |
| ADR-006 | Implement OAuth2 / OpenID Connect for Authentication | Accepted | Security |
| ADR-007 | Deploy via Docker containers on Kubernetes | Accepted | Deployment |
| ADR-008 | Introduce Redis Cache for Session & Query Caching | Accepted | Performance & Caching |

The log is maintained in the `architecture/decisions` folder of the repository and each ADR is version‑controlled.

---

## 9.2 Architecture Decision Records

### ADR-001: Adopt Layered Architecture (A‑Architecture)
| Aspect | Description |
|--------|-------------|
| **Status** | Accepted |
| **Context** | The system must support clear separation of concerns, enable independent evolution of UI, business logic, and data access, and facilitate onboarding of new developers. Existing component distribution shows distinct layers: presentation (246 components), application (173 services), domain (199 entities), data‑access (38 repositories), and infrastructure (1 configuration). |
| **Decision** | Adopt a classic **Layered Architecture** (also known as N‑Tier) as the primary functional view (A‑Architecture). Each layer communicates only with the adjacent layer(s) via well‑defined interfaces. |
| **Rationale** | - Aligns with the observed component distribution.
- Supports DDD concepts (domain layer isolates business entities).
- Enables independent testing of each layer.
- Matches the technology stack (Spring MVC for presentation, Spring Service layer, JPA repositories). |
| **Consequences** | - Enforces strict dependency direction (presentation → application → domain → data‑access).
- Requires explicit mapping objects (DTOs) between layers.
- May introduce additional boilerplate code (mappers, service facades). |

---

### ADR-002: Choose Spring Boot as Backend Framework
| Aspect | Description |
|--------|-------------|
| **Status** | Accepted |
| **Context** | The backend container (`backend`) is built with **Gradle** and already contains 333 components, including 173 services, 38 repositories, and 199 domain entities. The team has strong Java expertise and requires rapid development, embedded server, and extensive ecosystem support. |
| **Decision** | Use **Spring Boot** (version 3.x) as the primary backend framework. |
| **Rationale** | - Provides auto‑configuration, reducing boilerplate.
- Integrates seamlessly with Spring MVC, Spring Data JPA, and Spring Security.
- Supports Docker image creation via the Gradle plugin.
- Aligns with the existing technology evidence (`technology: Spring Boot`). |
| **Consequences** | - Introduces Spring-specific conventions that developers must follow.
- Increases the size of the final artifact (fat JAR). |

---

### ADR-003: Select PostgreSQL as Primary Database
| Aspect | Description |
|--------|-------------|
| **Status** | Accepted |
| **Context** | The domain layer contains 199 JPA‑annotated entities. The system requires ACID compliance, complex queries, and GIS extensions for deed‑location data. |
| **Decision** | Use **PostgreSQL 15** as the relational database. |
| **Rationale** | - Mature open‑source RDBMS with strong JPA support.
- Offers advanced indexing (GIN, GiST) useful for spatial data.
- Fits the existing Spring Data JPA repository pattern (`repository` stereotype). |
| **Consequences** | - Requires DB schema migration tooling (Flyway/Liquibase).
- Operational overhead for backups and scaling. |

---

### ADR-004: Use Angular for Front‑end UI
| Aspect | Description |
|--------|-------------|
| **Status** | Accepted |
| **Context** | The frontend container (`frontend`) is built with **npm** and contains 404 components, including 214 presentation‑layer components, 131 application‑layer services, and 59 unknown‑layer utilities. The product demands a rich, responsive UI with strong type safety. |
| **Decision** | Adopt **Angular 16** as the front‑end framework. |
| **Rationale** | - Provides a component‑based architecture that mirrors the backend’s layered approach.
- Strong TypeScript support aligns with the team’s skill set.
- Integrated routing, forms, and HTTP client simplify API consumption.
- Matches the documented technology (`technology: Angular`). |
| **Consequences** | - Larger bundle size compared to lighter frameworks.
- Requires Angular CLI and build pipeline maintenance. |

---

### ADR-005: Define RESTful API with OpenAPI 3.0
| Aspect | Description |
|--------|-------------|
| **Status** | Accepted |
| **Context** | The system exposes 95 REST endpoints (POST, GET, PUT, DELETE, PATCH) across 21 `rest_interface` components. Consistency and client generation are critical for both internal and external consumers. |
| **Decision** | Document the public API using **OpenAPI 3.0** specifications and generate server stubs (Spring MVC) and client SDKs (TypeScript) from the spec. |
| **Rationale** | - Guarantees contract‑first design.
- Enables automated validation, testing, and documentation (Swagger UI).
- Facilitates front‑end integration with generated TypeScript clients. |
| **Consequences** | - Requires maintenance of the OpenAPI YAML/JSON files.
- Adds a generation step to the CI pipeline. |

---

### ADR-006: Implement OAuth2 / OpenID Connect for Authentication
| Aspect | Description |
|--------|-------------|
| **Status** | Accepted |
| **Context** | Security requirements dictate single‑sign‑on (SSO) across multiple client applications (web UI, mobile, third‑party services). The backend already uses Spring Security. |
| **Decision** | Use **OAuth2** with **OpenID Connect** (OIDC) as the authentication and authorization mechanism, delegating to an external IdP (Keycloak). |
| **Rationale** | - Industry‑standard, well‑supported by Spring Security.
- Provides token‑based stateless authentication suitable for REST APIs.
- Enables fine‑grained scopes for micro‑service calls. |
| **Consequences** | - Additional infrastructure (Keycloak server) to provision and manage.
- Requires token validation logic in each service. |

---

### ADR-007: Deploy via Docker containers on Kubernetes
| Aspect | Description |
|--------|-------------|
| **Status** | Accepted |
| **Context** | The system consists of four containers: `backend` (Spring Boot), `frontend` (Angular), `e2e-xnp` (Playwright tests), and `import-schema` (Java library). Scalability, resilience, and cloud‑native operation are required. |
| **Decision** | Package each runtime container as a **Docker** image and orchestrate them with **Kubernetes** (managed GKE/EKS). |
| **Rationale** | - Aligns with container‑first development approach.
- Kubernetes provides automated scaling, rolling updates, and service discovery.
- Docker images are already defined in the build system (Gradle for backend, npm for frontend). |
| **Consequences** | - Introduces Kubernetes operational complexity (helm charts, CI/CD pipelines).
- Requires monitoring and logging infrastructure (Prometheus, Grafana, ELK). |

---

### ADR-008: Introduce Redis Cache for Session & Query Caching
| Aspect | Description |
|--------|-------------|
| **Status** | Accepted |
| **Context** | Performance tests show latency spikes on frequent read‑heavy operations (e.g., deed lookup). Stateless authentication tokens are stored in memory, and certain repository queries are cache‑able. |
| **Decision** | Deploy **Redis** as an in‑memory cache for HTTP session storage and query result caching. |
| **Rationale** | - Low latency, high throughput data store.
- Native Spring Cache abstraction support.
- Enables horizontal scaling of stateless services. |
| **Consequences** | - Adds another managed service to the Kubernetes cluster.
- Requires cache invalidation strategy and TTL configuration. |

---

## 9.3 Decision Tracking and Governance

All ADRs are stored in the `architecture/decisions` directory, version‑controlled alongside the source code. The Architecture Review Board (ARB) meets bi‑weekly to reassess decisions against evolving business goals, technical debt, and emerging standards. Any deviation from an accepted decision must be recorded as a **Decision Change Request (DCR)** and approved by the ARB.

## 9.4 Impact Assessment Summary

| Decision | Impact on Quality Attributes |
|----------|------------------------------|
| Layered Architecture | Improves **Maintainability** and **Modifiability**; adds slight **Performance** overhead due to layer traversal. |
| Spring Boot | Boosts **Productivity** and **Reliability**; increases **Deployment Size**. |
| PostgreSQL | Enhances **Data Integrity** and **Scalability**; requires **Operational Effort** for backups. |
| Angular | Provides rich UI (**Usability**) but larger **Bundle Size**. |
| OpenAPI 3.0 | Improves **Interoperability** and **Documentation**; adds **Process Overhead**. |
| OAuth2/OIDC | Strengthens **Security**; adds **Complexity** in token management. |
| Kubernetes/Docker | Increases **Scalability**, **Resilience**, and **Portability**; introduces **Operational Complexity**. |
| Redis Cache | Reduces **Response Time** and **Load**; adds **Consistency Management** concerns. |

---

*Prepared by the Architecture Team – 2026-02-07*