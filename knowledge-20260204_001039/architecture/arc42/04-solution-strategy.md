# 04 – Solution Strategy

## 4.1 Technology Decisions

| Technology | Reason for Selection | Problems Solved |
|------------|----------------------|-----------------|
| **Spring Boot (Java)** – backend container | Provides a mature, opinionated framework for building production‑grade REST services, dependency injection, transaction management and Actuator health endpoints. | Reduces boiler‑plate for wiring services, repositories and controllers; simplifies configuration and enables rapid development of the **layered_architecture**. |
| **Angular (TypeScript)** – frontend container | Delivers a component‑based single‑page application (SPA) with lazy‑loaded routing, built‑in state handling via services and a rich ecosystem (ng‑bootstrap). | Allows a responsive UI that consumes the REST API without page reloads, supports modular development of the **163 component** UI layer. |
| **PostgreSQL** – database container | Reliable open‑source relational database with strong ACID guarantees and native support for JPA/Hibernate. | Persists the **37 entity** domain model, ensures transactional integrity for deed, workflow and number‑management data. |
| **Pact‑Broker** – contract‑testing container | Central repository for consumer‑driven contract files (JSON). | Guarantees backward‑compatible API evolution; integrates into CI pipelines to verify that the **108 interfaces** remain stable. |
| **Ubuntu (Docker base)** – docker container | Lightweight, well‑supported Linux base for container images. | Provides a uniform runtime environment for all containers, simplifying deployment and resource isolation. |
| **Docker Compose** (orchestration) | Declarative definition of the five containers (backend, frontend, postgres, pact‑broker, docker host). | Enables reproducible, distributed deployment while keeping the system vertically scalable as a **modular_monolith_architecture**. |

These choices align with the identified **architecture_style** components (`layered_architecture`, `modular_monolith_architecture`) and give the system a solid, industry‑standard stack that is easy to operate, test and extend.

---

## 4.2 Architecture Patterns

| Pattern (exact component name) | Where It Is Applied | Intent / Benefit |
|-------------------------------|----------------------|------------------|
| `layered_architecture` | Overall backend structure: Controllers → Services → Repositories | Enforces clear separation of concerns, prevents layer violations, and makes the system **maintainable** and **testable**. |
| `modular_monolith_architecture` | All source modules reside in a single deployable JAR, but each bounded context (e.g., DeedEntry, NumberManagement, Workflow, XNP) is a separate Java module. | Retains the modularity of micro‑services while avoiding the operational overhead of separate deployments; supports **vertical scalability**. |
| `repository_pattern` | Repository interfaces (`ActionRepository`, `DeedEntryRepository`, `NumberManagementRepository`, `WorkflowRepository`). | Abstracts data‑access logic, isolates JPA/Hibernate details, enables easy swapping of persistence strategies and improves **testability**. |
| `factory_pattern` | Service factories such as `action_factory` used by `action_service_impl` and `action_worker_service`. | Centralises object creation, encapsulates complex construction logic, and simplifies unit testing via mock factories. |
| `builder_pattern` | Used in DTO and domain‑object construction (e.g., building complex request payloads for deed signing). | Provides a fluent, readable way to construct immutable objects, reducing errors and enhancing **code readability**. |
| `singleton_pattern` | Configuration helpers and shared utilities (e.g., a global `ObjectMapper` or a centralized `KeyManager` singleton). | Guarantees a single, shared instance where needed, reducing memory footprint and avoiding duplicated state. |
| `adapter_pattern` | All XNP integration classes (`XnpAuthenticationAdapter`, `XnpArchiveManagerEndpoint`, `XnpFileApiAdapter`, `XnpSignatureEndpoint`). | Decouples the core UVZ domain from external XNP services, allowing the external API to evolve without impacting internal business logic. |
| `observer_pattern` | Event‑driven components such as `WorkflowStateMachine` listeners and internal audit hooks. | Enables loose coupling between state changes and side‑effects (e.g., notifications), supporting **extensibility** and **reactive** behaviour. |

By consistently applying these patterns, the architecture achieves a high degree of **separation of concerns**, **low coupling**, and **high cohesion**, which are the foundations for the quality goals described later.

---

## 4.3 Achieving Quality Goals

| Quality Goal | How It Is Realised Through Technology & Patterns |
|--------------|-------------------------------------------------|
| **Maintainability** | The `layered_architecture` enforces a strict Controller → Service → Repository flow, making it straightforward to locate and modify logic. Combined with `repository_pattern` and `factory_pattern`, new features can be added in a single layer without ripple effects. |
| **Extensibility** | The `adapter_pattern` isolates XNP dependencies, allowing new external services or replacement of XNP without touching core modules. The `modular_monolith_architecture` keeps bounded contexts independent, so additional modules (e.g., a new reporting capability) can be introduced with minimal impact. |
| **Testability** | `factory_pattern` enables injection of mock objects; `repository_pattern` allows repository stubs; `observer_pattern` decouples event emission from handling. The presence of a **pact‑broker** ensures contract‑driven tests for all **108 interfaces**, guaranteeing that consumer expectations are validated automatically. |
| **Reusability** | `builder_pattern` promotes reusable, immutable request/response objects across services. Shared singletons (`singleton_pattern`) provide common utilities (e.g., cryptographic helpers) without duplication. |
| **Performance (low coupling & resource use)** | The `singleton_pattern` limits unnecessary object creation. The **Angular** SPA with lazy‑loaded modules reduces initial payload size, leading to faster UI load times. The **PostgreSQL** DB provides efficient query execution for the 37 JPA entities. |
| **Reliability** | `repository_pattern` shields business logic from persistence failures; Spring Boot’s `@Transactional` (leveraged by the layered design) ensures atomic operations. Health endpoints exposed by Actuator (enabled by Spring Boot) allow automated monitoring and rapid detection of failures. |
| **Scalability (vertical)** | The **modular_monolith_architecture** concentrates all code in a single JVM, making vertical scaling (adding CPU/memory) trivial. Docker’s container limits (CPU/memory) can be tuned per deployment to match load expectations. |
| **Security** | Spring Security (part of the Spring Boot stack) provides authentication and method‑level authorization. The `adapter_pattern` isolates external authentication flows (XNP) from internal services, simplifying security audits. |

Together, the chosen technologies, the explicit architectural patterns, and the disciplined layering provide a coherent strategy that directly addresses the system’s non‑functional requirements while keeping the solution simple to operate and evolve.