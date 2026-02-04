# 02 – Architecture Constraints

## 2.1 Technical Constraints

| Area | Constraint | Source / Rationale |
|------|------------|--------------------|
| **Programming language** | All backend code must be written in **Java** and compiled for the JVM used by Spring Boot. | Derived from the *backend* container (`technology: "Spring Boot"`). |
| **Framework** | The backend must run on **Spring Boot** and respect its auto‑configuration and dependency‑injection mechanisms. | `backend` container → `technology: "Spring Boot"`. |
| **Layered architecture** | The system must keep the strict three‑tier separation **Controller → Service → Repository** enforced by the `layered_architecture` component. | `list_components_by_stereotype` → `layered_architecture`. |
| **Modular monolith** | All source modules must remain inside a single deployable artifact (the *backend* JAR) as required by `modular_monolith_architecture`. | `list_components_by_stereotype` → `modular_monolith_architecture`. |
| **Design patterns** | The following patterns must be used where indicated: <br>• `repository_pattern` for data‑access layers <br>• `factory_pattern` for creation of complex objects <br>• `builder_pattern` for immutable DTO construction <br>• `singleton_pattern` only for truly shared helpers (e.g., configuration) <br>• `adapter_pattern` for all external XNP integrations <br>• `observer_pattern` for event‑driven communication between services. | `list_components_by_stereotype` → design‑pattern components. |
| **Database** | Persistence must be handled by **PostgreSQL** using JPA/Hibernate mappings; no other DBMS is allowed. | `postgres` container → `technology: "PostgreSQL"`. |
| **Frontend** | The UI must be built with **Angular** (TypeScript) and follow the Angular module system; all UI code lives in the `frontend` container. | `frontend` container → `technology: "Angular"`. |
| **Container platform** | All runtime units are Docker containers based on **Ubuntu**; images must be built from the provided `Dockerfile` (single file). | `docker` container → `technology: "ubuntu"` and `dockerfile` stereotype. |
| **Contract testing** | All public REST contracts must be published to the **pact‑broker**; consumer‑driven contract tests are mandatory for CI. | `broker_app` container → `technology: "pact-broker"`. |
| **Version compatibility** | The Spring Boot version and Angular version must be compatible with the respective JDK (≥ 11) and Node .js versions used in the build pipelines. | Implied by the technology stack; ensures build‑time compatibility. |
| **Resource limits** | Containers must respect defined CPU and memory limits in the Docker Compose configuration to guarantee vertical scalability. | Consistent with the **distributed** deployment model described in the analysis. |

---

## 2.2 Organizational Constraints

| Constraint | Explanation |
|------------|-------------|
| **Team skill set** | Development teams must possess expertise in **Java Spring Boot**, **Angular**, **Docker**, and **PostgreSQL** to maintain the modular monolith. |
| **Continuous Integration / Delivery** | CI pipelines must build the backend JAR, the Angular SPA, run unit tests, contract tests against the **pact‑broker**, and produce Docker images for all five containers. |
| **Governance of design patterns** | Architecture reviews must verify that new code adheres to the mandatory design‑pattern list (`repository_pattern`, `factory_pattern`, `builder_pattern`, `singleton_pattern`, `adapter_pattern`, `observer_pattern`). |
| **Change management** | Any change that touches the layered boundaries (Controller ↔ Service ↔ Repository) requires a review to prevent layer violations; the analysis reports *zero* layer violations, which must be preserved. |
| **Security ownership** | The security team is responsible for replacing the mock authentication (`JsonAuthorizationRestServiceImpl`) with production‑grade authentication (e.g., JWT/OAuth2) and for adding input validation and audit logging. |
| **Documentation** | All public APIs must be documented (OpenAPI/Swagger) and versioned via the **path‑based** versioning strategy (`/uvz/v1/...`). |
| **Release coordination** | Because the backend is a modular monolith, releases are coordinated across all backend modules; front‑end releases are independent but must stay compatible with the published REST contracts. |

---

## 2.3 Convention Constraints

| Area | Convention | Example |
|------|------------|---------|
| **Naming – Entities** | Class names must end with `Entity`. | `DeedEntryEntity`, `WorkflowEntity`. |
| **Naming – REST services** | Controllers implementing REST endpoints must end with `RestServiceImpl`. | `DeedEntryRestServiceImpl`, `NumberManagementRestServiceImpl`. |
| **Package structure** | Packages follow a **domain‑first** hierarchy (e.g., `de.bnotk.uvz.module.deedentry.service.impl.rest`). | Ensures clear bounded‑context separation. |
| **Layer suffixes** | Service implementations end with `ServiceImpl`; repository interfaces end with `Repository`. | `ActionServiceImpl`, `ActionRepository`. |
| **Angular component naming** | Component class names end with `Component`; files use kebab‑case. | `deed-entry-list.component.ts`. |
| **Configuration files** | Spring configuration resides in `application.yml` / `application-*.yml`; Angular environment files follow `environment*.ts`. |
| **Docker naming** | Container images are named `<system>-backend`, `<system>-frontend`, `<system>-postgres`, `<system>-pact-broker`. |
| **Versioning** | REST API version is part of the path (`/uvz/v1/...`). | Guarantees backward compatibility. |
| **Logging** | Log messages must include the fully qualified class name and a correlation ID for tracing. |
| **Testing** | Unit tests use JUnit 5; contract tests use Pact; UI tests use Playwright. |
| **Documentation style** | Architectural artefacts (C4 diagrams, arc42 chapters) must be kept in the `knowledge/architecture/` folder with clear version control. |

These constraints capture the *technical*, *organizational* and *convention* limits that directly stem from the identified technologies, the discovered architectural style (`modular_monolith_architecture`, `layered_architecture`), and the mandatory design‑pattern list. Adhering to them ensures that the **uvz** system remains maintainable, extensible, and deployable within the established Docker‑based, vertically scalable environment.