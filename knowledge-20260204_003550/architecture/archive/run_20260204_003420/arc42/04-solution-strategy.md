# 04 – Solution Strategy

## 4.1 Technology Decisions  

| Decision | Reason (problem solved) | Evidence from facts |
|----------|------------------------|---------------------|
| **Java 17 + Spring Boot (backend)** | Provides a mature, type‑safe platform with extensive ecosystem support (dependency injection, transaction management, Actuator). Solves the problem of building a robust, maintainable server‑side application that can enforce the *layered architecture* and integrate easily with PostgreSQL. | Container **backend** – technology “Spring Boot” (Java) – `src/main/java/de/bnotk/uvz/module/Application.java`. |
| **Angular v18‑lts + TypeScript 5.4.5 (frontend)** | Delivers a component‑based single‑page application, enabling fast, responsive UI and clear separation of UI concerns (components, pipes, directives). Solves the need for a rich web UI that consumes the REST API. | Container **frontend** – technology “Angular” – entry points `src/main.ts`, `src/app/app.module.ts`. |
| **PostgreSQL** | A proven relational DBMS that enforces ACID semantics, suitable for the 37 domain entities and 258 SQL scripts. Solves data‑integrity and complex querying requirements. | Container **postgres** – technology “PostgreSQL”. |
| **Docker (Ubuntu base)** | Guarantees reproducible environments, isolates the Java and Node.js runtimes, and enables the distributed deployment model (5 containers). Solves deployment‑environment drift and simplifies scaling/replication. | Container **docker** – technology “ubuntu”. |
| **Pact‑Broker** | Centralised contract‑testing repository; ensures backwards‑compatible API evolution. Solves the problem of automated consumer‑provider verification in CI/CD. | Container **broker_app** – technology “pact‑broker”. |
| **Gradle (backend build) & npm (frontend build)** | Provides fast, incremental builds and dependency management for Java and JavaScript ecosystems respectively. Solves the need for reliable, repeatable builds. | Technology stacks listed in the container descriptions. |
| **Spring Security** | Offers declarative authentication & authorization, addressing the security baseline required for the system. | Mentioned in the security analysis (authentication implemented, mock adapters to be replaced). |

### How the choices support quality goals  

* **Maintainability** – Java 17 and Spring Boot encourage strong typing and convention‑based configuration; the layered architecture (see §4.2) is enforced by the framework’s separation of `@RestController`, `@Service`, and repository beans.  
* **Scalability** – Dockerised containers can be replicated; vertical scaling is enabled by the JVM’s ability to allocate more CPU/RAM.  
* **Testability** – Pact‑Broker and the clear module boundaries (Angular components, Spring services) make unit‑, integration‑ and contract‑testing straightforward.  
* **Observability** – Spring Boot Actuator (included in the backend) provides health‑checks and metrics; the frontend can expose its own performance metrics via Angular tooling.  

---

## 4.2 Architecture Patterns  

| Pattern (exact name) | Where it is applied (exact component) | Why it is used (problem solved) |
|----------------------|--------------------------------------|---------------------------------|
| **layered_architecture** | Overall backend structure (controllers → services → repositories) | Enforces clear separation of concerns, prevents layer violations (reported zero), and simplifies reasoning about dependencies. |
| **modular_monolith_architecture** | Entire backend (single Spring Boot application) organised into packages such as `de.bnotk.uvz.module.deedentry`, `de.bnotk.uvz.module.numbermanagement`, etc. | Provides module boundaries without the operational overhead of micro‑services, enabling high cohesion and low coupling within a single deployable unit. |
| **repository_pattern** | Repository classes like `DeedEntryConnectionDaoImpl` (package `de.bnotk.uvz.module.deedentry.dataaccess.api.dao.impl`). | abstracts data‑access logic, isolates SQL handling from business logic, and allows easy swapping of persistence implementations. |
| **factory_pattern** | Service creation logic in packages such as `de.bnotk.uvz.module.action.logic.impl` (e.g., `ActionServiceImpl`). | Centralises complex object instantiation, supports extensibility when new service types are added (e.g., XNP adapters). |
| **builder_pattern** | Token generation in `ArchivingRestServiceImpl` / related service classes (e.g., building signed tokens). | Simplifies construction of immutable objects with many optional parameters, improving readability and reducing errors. |
| **singleton_pattern** | Shared utility classes in the security adapters (e.g., `JsonAuthorizationRestServiceImpl`), Actuator health‑check component `HealthCheck`. | Guarantees a single instance of stateless utilities, reducing resource usage and ensuring consistent configuration. |
| **adapter_pattern** | XNP integration adapters located in `de.bnotk.uvz.module.adapters.xnp` (e.g., `XnpAuthenticationAdapter`). | Isolates external XNP API specifics from the core business logic, allowing the system to switch or mock the external platform without code changes. |
| **observer_pattern** | Event propagation mechanisms in the generic package `de.bnotk.uvz.module` (e.g., observer implementations used by workflow state machine). | Enables decoupled notification of state changes, supporting extensibility for future features like audit logging. |

These patterns are directly listed in the **design_pattern** stereotype (six entries) and are reflected in the concrete component names shown above.

---

## 4.3 Achieving Quality Goals  

| Quality Goal | How the chosen technologies & patterns help achieve it |
|--------------|--------------------------------------------------------|
| **Maintainability** | - *Layered architecture* isolates responsibilities, making changes localized.<br>- *Modular monolith* keeps all code in one repository, avoiding inter‑service versioning problems.<br>- *Repository, factory, builder* patterns reduce boilerplate and centralise complex logic.<br>- Strongly typed Java 17 and Angular TypeScript catch errors at compile time. |
| **Scalability** | - Vertical scaling via JVM tuning (Java 17).<br>- Container‑based deployment allows horizontal replication of the whole backend if needed.<br>- Stateless REST controllers and services (no session affinity) support load‑balanced instances. |
| **Testability** | - `Pact‑Broker` validates API contracts automatically.<br>- Clear interfaces (108) and small, focused services enable unit testing.<br>- Angular’s component‑based design (163 components, 67 pipes) is unit‑testable with Jasmine/Karma.<br>- `builder_pattern` and `factory_pattern` make objects easy to mock. |
| **Reliability** | - *Singleton* utilities ensure a single point of configuration for resources like security handlers.<br>- `observer_pattern` provides robust event notification for workflow state changes.<br>- Spring Boot Actuator supplies health‑check endpoints for early failure detection. |
| **Observability** | - Actuator exposes `/actuator/health`, `/actuator/metrics` (JSON) for monitoring systems.<br>- Consistent REST API versioning (`/uvz/v1/`) simplifies logging and tracing.<br>- Uniform error handling in controllers returns proper HTTP status codes, aiding diagnostics. |
| **Security** | - Spring Security implements authentication & authorization out‑of‑the‑box.<br>- *Adapter pattern* isolates external XNP authentication, allowing secure replacement of mock adapters.<br>- The layered design makes it easy to insert input‑validation (Bean Validation) and audit‑logging filters at the controller or service boundary. |
| **Operability** | - Docker images based on Ubuntu guarantee identical runtime environments across dev, test, and production.<br>- Externalised configuration (`@ConfigurationProperties`) allows ops to change DB URLs, feature flags, etc., without code changes.<br>- Pact‑Broker integration ensures deployment pipelines only promote compatible API versions. |

By deliberately selecting **Java 17**, **Spring Boot**, **Angular**, **PostgreSQL**, and Docker, and by applying the six identified design patterns, the architecture directly addresses the quality goals outlined in the introductory chapter: high maintainability, scalable deployment, solid testability, reliable operation, and a foundation for robust security.