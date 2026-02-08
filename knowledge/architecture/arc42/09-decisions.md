# 09 - Architecture Decisions

## 9.1 Decision Log Overview

The following Architecture Decision Records (ADRs) capture the most significant technical choices made for the **uvz** system. Each ADR follows the SEAGuide‑recommended template and is linked to concrete metrics extracted from the architecture knowledge base (components, containers, relations, and interfaces). The decisions collectively define the **Layered Architecture** style, the technology stack, and the operational model.

## 9.2 Architecture Decision Records

### ADR-001: Architecture Style – Layered Architecture
| Aspect | Description |
|--------|-------------|
| **Status** | Accepted |
| **Context** | The system must support clear separation of concerns, enable independent evolution of UI, business logic, and data access, and allow teams to work on distinct layers without tight coupling. The knowledge base shows a natural distribution of components across presentation (287), application (184), domain (360), and data‑access (38) layers. |
| **Decision** | Adopt a **Layered Architecture** with five logical layers: Presentation, Application, Domain, Data‑Access, and Infrastructure. |
| **Rationale** | The existing component distribution matches a classic layered model, reducing cognitive load and simplifying onboarding. Layer boundaries are reinforced by the *uses* relation type (131 uses) which predominantly flows from higher to lower layers. |
| **Consequences** | Enables independent testing per layer, clear module boundaries, and straightforward mapping to containers (frontend, backend). Future refactoring to micro‑services can reuse the same layer definitions. |

### ADR-002: Backend Framework – Spring Boot (Java/Gradle)
| Aspect | Description |
|--------|-------------|
| **Status** | Accepted |
| **Context** | The backend container (`backend`) is built with **Spring Boot** (Gradle) and hosts 494 components, including 184 services, 360 entities, and 38 repositories. The system requires a mature, convention‑over‑configuration framework that supports REST, JPA, and security out‑of‑the‑box. |
| **Decision** | Use **Spring Boot** as the primary backend framework. |
| **Rationale** | Spring Boot provides a rich ecosystem for the required patterns (Repository, Service, Controller) and aligns with the existing component stereotypes. The Gradle build system is already in place, reducing migration effort. |
| **Consequences** | All new backend services must be implemented as Spring beans. Integration tests will rely on Spring Test utilities. The choice locks the team to the Java ecosystem for backend development. |

### ADR-003: Database – Relational Database (PostgreSQL) via Spring Data JPA
| Aspect | Description |
|--------|-------------|
| **Status** | Accepted |
| **Context** | The domain layer contains 360 **entity** components, indicating a rich domain model that benefits from strong ACID guarantees. Spring Data JPA is part of the chosen backend stack and expects a relational database. |
| **Decision** | Deploy **PostgreSQL** as the primary relational database, accessed through Spring Data JPA. |
| **Rationale** | PostgreSQL offers robust transaction support, advanced indexing, and is fully compatible with JPA. The decision leverages existing entity‑repository mappings and avoids the impedance mismatch of NoSQL solutions. |
| **Consequences** | Database schema migrations will be managed with Flyway/Liquibase. Operational teams must provision PostgreSQL clusters and handle backups. |

### ADR-004: Frontend Framework – Angular (npm)
| Aspect | Description |
|--------|-------------|
| **Status** | Accepted |
| **Context** | The `frontend` container uses **Angular** (npm) and contains 404 components, including 214 presentation‑layer components, 131 application‑layer services, and 67 pipes. The UI must be highly interactive, type‑safe, and support modular development. |
| **Decision** | Adopt **Angular** as the frontend framework. |
| **Rationale** | Angular’s strong typing (TypeScript) matches the disciplined component model observed in the code base. The existing count of Angular‑specific stereotypes (pipe, directive, component) confirms prior investment. |
| **Consequences** | All UI work will be done in Angular modules. Build pipelines must use the npm build system. Future UI libraries must be compatible with Angular. |

### ADR-005: API Design – RESTful JSON over HTTP
| Aspect | Description |
|--------|-------------|
| **Status** | Accepted |
| **Context** | The architecture defines 21 **rest_interface** components and 196 REST endpoints (GET, POST, PUT, DELETE, PATCH). The system needs a simple, language‑agnostic contract for both internal and external consumers. |
| **Decision** | Expose a **RESTful JSON** API using Spring MVC controllers and Angular HttpClient. |
| **Rationale** | The existing REST endpoint count and the presence of `rest_interface` components indicate that REST is already the dominant integration style. JSON is the de‑facto standard for web APIs and aligns with Angular’s default data handling. |
| **Consequences** | API versioning must be handled via URL path prefixes. Documentation will be generated with OpenAPI/Swagger. All new services must adhere to the established HTTP verb semantics. |

### ADR-006: Authentication & Authorization – Spring Security with JWT
| Aspect | Description |
|--------|-------------|
| **Status** | Accepted |
| **Context** | Security requirements demand stateless authentication for both the Angular SPA and the Node.js `jsApi` helper. The backend already uses Spring Boot, which integrates seamlessly with Spring Security. |
| **Decision** | Implement **JWT‑based authentication** using Spring Security on the backend and Angular’s HttpInterceptor on the frontend. |
| **Rationale** | JWT provides a stateless token that works across the Angular SPA, the Node.js `jsApi`, and any future micro‑services. Spring Security offers ready‑made filters and token validation utilities. |
| **Consequences** | Token issuance and revocation logic must be centralized. Refresh‑token handling will be added later. All endpoints must be secured with `@PreAuthorize` annotations where appropriate. |

### ADR-007: Deployment – Docker Containers orchestrated by Kubernetes
| Aspect | Description |
|--------|-------------|
| **Status** | Accepted |
| **Context** | The system consists of distinct containers: `backend` (Spring Boot), `frontend` (Angular), `jsApi` (Node.js), and `e2e-xnp` (Playwright tests). A container‑first approach simplifies scaling and environment parity. |
| **Decision** | Package each container as a **Docker image** and deploy them on a **Kubernetes** cluster. |
| **Rationale** | Docker provides reproducible builds; Kubernetes offers automated scaling, service discovery, and rolling updates. The clear separation of containers matches the layered architecture and eases CI/CD pipelines. |
| **Consequences** | CI pipelines must build Docker images and push them to a registry. Helm charts (or Kustomize) will be maintained for each service. Monitoring and logging must be integrated with the cluster (e.g., Prometheus, Loki). |

### ADR-008: Caching – Spring Cache abstraction with Redis
| Aspect | Description |
|--------|-------------|
| **Status** | Accepted |
| **Context** | Several read‑heavy services (e.g., lookup of static reference data) suffer from latency due to repeated database access. The backend already uses Spring Boot, which includes the Spring Cache abstraction. |
| **Decision** | Introduce **Redis** as the backing store for the Spring Cache abstraction. |
| **Rationale** | Redis offers low‑latency in‑memory storage and integrates natively with Spring Cache. It can be deployed as a sidecar in the Kubernetes cluster, providing high availability. |
| **Consequences** | Cache keys and eviction policies must be defined per service. Cache miss monitoring will be added to ensure data freshness. The deployment adds a Redis StatefulSet to the Kubernetes manifests. |

---

*All ADRs are traceable to the architecture knowledge base: component counts, container technologies, and interface definitions were extracted directly from the system’s factual model.*
