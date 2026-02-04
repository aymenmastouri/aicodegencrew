# 04 – Solution Strategy

## 4.1 Technology Decisions

| Technology | Reason for selection | Problem it solves |
|------------|----------------------|-------------------|
| **Spring Boot (Java 17)** – backend container `backend` | Provides a mature, convention‑over‑configuration framework for building a **modular monolith** with a clear **layered architecture** (Controller → Service → Repository). Java 17 is the language version used by the code base. | Reduces boiler‑plate for REST controllers, dependency injection and transaction management; enables rapid development while keeping the application runnable in a single JVM (vertical scaling). |
| **Angular v18‑LTS (TypeScript 5.4.5)** – frontend container `frontend` | Offers a component‑based SPA framework that aligns with the **Component‑Based SPA** style discovered in the front‑end code. Lazy‑loading and service‑based state management are already used. | Delivers a responsive UI with a single page load, reduces round‑trips to the server, and allows the UI to be developed and deployed independently of the backend. |
| **PostgreSQL** – database container `postgres` | A reliable relational DBMS that matches the existing JPA/Hibernate mappings (the repository layer uses the **repository_pattern**). | Stores the 37 domain entities with ACID guarantees; supports complex queries needed for deed, number‑management and workflow data. |
| **Pact‑Broker** – container `broker_app` | Centralised contract‑testing broker used by the CI/CD pipeline. | Guarantees backward‑compatible REST contracts between clients and the backend, preventing breaking API changes. |
| **Ubuntu** – base image container `docker` | Linux distribution used as the foundation for all Docker images. | Provides a stable, well‑supported OS for running Java, Node.js and PostgreSQL containers. |
| **Gradle** (backend) / **npm** (frontend) | Build tools that are already configured in the project. | Ensure reproducible builds and dependency management for Java and TypeScript code. |

These technology choices directly support the **modular monolith** primary style and the **layered architecture** constraint identified in the architecture facts.

## 4.2 Architecture Patterns

| Pattern (exact name) | Where it is applied | Purpose / Benefit |
|----------------------|---------------------|-------------------|
| **repository_pattern** | Implemented by the four `*Repository` components (e.g., `DeedEntryRepository`). | Abstracts data‑access logic behind a clean interface, decoupling the service layer from the persistence details and enabling easy swapping of the underlying data source if needed. |
| **factory_pattern** | Used in various `*ServiceImpl` classes to create domain objects (e.g., building DTOs for deed creation). | Centralises object creation, improves testability by allowing mock factories, and hides complex construction logic behind a simple API. |
| **builder_pattern** | Employed in the construction of immutable request/response objects (e.g., token generation in `ArchivingRestServiceImpl`). | Provides a fluent API for assembling objects with many optional fields, reducing constructor explosion and enhancing readability. |
| **singleton_pattern** | Applied to shared utilities such as `HealthCheck` and security configuration classes. | Guarantees a single instance, conserving resources and ensuring consistent configuration across the application. |
| **adapter_pattern** | All 24 XNP integration services (`XnpAuthenticationAdapter`, `XnpArchiveManagerEndpoint`, …) act as adapters between the internal domain model and the external XNP platform. | Isolates external protocol changes, allowing the core system to remain stable while XNP APIs evolve. |
| **observer_pattern** | Used in the custom workflow state‑machine implementation (`WorkflowStateMachine`) to notify listeners about state transitions. | Enables loose coupling between the state‑machine core and interested components (e.g., audit logging, UI updates). |

The **layered architecture** (controllers → services → repositories) together with these six design patterns creates a well‑structured code base where each concern is isolated, promoting maintainability and testability.

## 4.3 Achieving Quality Goals

| Quality Goal | How the selected technologies & patterns fulfil it |
|--------------|---------------------------------------------------|
| **Maintainability (grade A)** | The **modular monolith** combined with the **layered architecture** enforces strict separation of concerns. The six design patterns (repository, factory, builder, singleton, adapter, observer) further reduce coupling and duplication, delivering high cohesion (average 0.15 dependencies per component) and zero layer violations. |
| **Reliability** | The **builder_pattern** ensures immutable objects are correctly constructed, while the **observer_pattern** centralises state‑change notifications, reducing error‑prone manual handling. Spring Boot’s health‑checks (Actuator) and the use of **repository_pattern** guarantee consistent data access and graceful degradation. |
| **Scalability** | Although the primary scaling approach is vertical, the **factory_pattern** and **repository_pattern** make it straightforward to extract services into separate processes or micro‑services later, supporting future horizontal scaling if required. |
| **Extensibility** | The **adapter_pattern** isolates the XNP integration, allowing new external services to be added or existing ones to change without touching core business logic. Angular’s component model also supports adding new UI features with minimal impact on existing code. |
| **Testability** | The **singleton_pattern** and **factory_pattern** simplify mocking of shared utilities and object creation in unit tests. The contract‑testing setup with **Pact‑Broker** validates REST API contracts automatically, while the layered design enables isolated testing of controllers, services and repositories. |
| **Security** | Spring Security (configured in the backend) enforces authentication and authorization at the controller layer. The **adapter_pattern** keeps external authentication calls (XNP) encapsulated, and the clear separation of concerns prevents accidental exposure of repository methods. |
| **Observability** | Spring Boot Actuator provides health endpoints and metrics out of the box; the **observer_pattern** can be leveraged to emit custom events for monitoring. |

By aligning technology choices with the identified architectural style and patterns, the solution strategy directly addresses the quality goals defined in the analysis, resulting in a system that is maintainable, reliable, and ready for future evolution.