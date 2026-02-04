# 02 – Architecture Constraints

## 2.1 Technical Constraints

| Area | Constraint | Source / Rationale |
|------|------------|--------------------|
| **Programming language** | All backend code must be written in **Java 17** (the version used by the Spring Boot application). | Derived from the *backend* container technology (Spring Boot / Java). |
| **Framework** | The server side must use **Spring Boot** (Gradle build) and respect the **layered architecture** (controller → service → repository). | Detected architecture‑style components `layered_architecture` and `modular_monolith_architecture`. |
| **Persistence** | Data must be stored in **PostgreSQL** and accessed via the **repository pattern** (`repository_pattern`). All database objects are defined by the set of 258 SQL scripts. | Container `postgres` and design‑pattern `repository_pattern`. |
| **Containerisation** | Each deployment unit is a Docker image based on **Ubuntu** (`docker`). Images for *backend*, *frontend*, *postgres* and *broker_app* must be built and orchestrated via Docker‑Compose. | Container list (`backend`, `frontend`, `docker`, `postgres`, `broker_app`). |
| **Frontend stack** | The UI must be implemented as an **Angular (v18‑lts)** single‑page application written in **TypeScript 5.4.5**. Angular modules, components and pipes must follow Angular naming conventions (`*.component.ts`, `*.pipe.ts`). | Container `frontend` technology details. |
| **Contract testing** | Interaction contracts with external consumers must be verified with **Pact‑Broker** (`broker_app`). | Container `broker_app` (pact‑broker). |
| **Build tooling** | Backend builds use **Gradle**; frontend builds use **npm**. | Technology stacks reported for each container. |
| **Security framework** | Authentication and authorization must be implemented with **Spring Security** (already present). Any mock adapters (e.g., `JsonAuthorizationRestServiceImpl`) must be replaced before production. | Security analysis in the base documentation. |
| **State handling** | Long‑running workflows are modelled with a **custom state‑machine** (`WorkflowStateMachine`) rather than an external BPM engine. | Workflow section of the analysis. |

## 2.2 Organizational Constraints

| Constraint | Explanation |
|------------|-------------|
| **Modular‑Monolith organisation** | The code base must stay as a **single Spring Boot application** (`modular_monolith_architecture`) while being organised into logical modules (e.g., `deedentry`, `numbermanagement`, `workflow`). This enables a single deployment pipeline but requires strict module boundaries. |
| **Layered development discipline** | Developers must keep **controllers** (`*RestServiceImpl`) free of business logic, delegate to **services** (`*ServiceImpl`), and only services may access **repositories** (`*DaoImpl`). The analysis reports **zero layer violations**; this must be enforced by code reviews and static analysis. |
| **Domain‑driven package structure** | Packages are grouped by bounded contexts (e.g., `de.bnotk.uvz.module.deedentry`, `de.bnotk.uvz.module.numbermanagement`). New code must be placed in the appropriate context to preserve the identified **38 entities** and **10 bounded contexts**. |
| **Continuous integration** | Every change must pass **contract tests** against the Pact‑Broker and **frontend tests** (Playwright) before merging. The pipeline must build Docker images for all five containers. |
| **Team boundaries** | Since the system is a modular monolith, feature teams own whole bounded contexts (e.g., DeedEntry team, XNP‑Integration team) and are responsible for the full stack (controller, service, repository) within that context. |
| **Security responsibility** | Security‐related components (e.g., `JsonAuthorizationRestServiceImpl`, `MockKmService`) are owned by the **Security team** and must be replaced with production‑grade implementations before release. |
| **Operational hand‑off** | Ops must receive Docker‑Compose files, health‑check definitions (Actuator), and Prometheus‑compatible metrics endpoints. The system must expose liveness/readiness probes for the *backend* container. |

## 2.3 Convention Constraints

| Area | Convention | Example (exact name from facts) |
|------|------------|---------------------------------|
| **Naming – Controllers** | Classes ending with `RestServiceImpl` and placed in a `service.impl.rest` package. | `DeedEntryRestServiceImpl` (package `de.bnotk.uvz.module.deedentry.service.impl.rest`) |
| **Naming – Services** | Classes ending with `ServiceImpl` located in a `logic.impl` package. | `ActionServiceImpl` (package `de.bnotk.uvz.module.action.logic.impl`) |
| **Naming – Repositories / DAOs** | Classes ending with `DaoImpl` and placed under `dataaccess.api.dao.impl`. | `DeedEntryConnectionDaoImpl` |
| **Entity naming** | PascalCase ending with `Entity`. | `DeedEntryEntity` |
| **Design patterns** | Use the detected patterns where appropriate: <br>• **Repository pattern** for data access <br>• **Factory pattern** for service creation <br>• **Builder pattern** for complex object construction (e.g., token generation) <br>• **Singleton pattern** for shared utilities (e.g., security handlers) <br>• **Adapter pattern** for XNP integration (`adapter_pattern`) <br>• **Observer pattern** for event propagation | Pattern names are taken from the `design_pattern` components list. |
| **Angular components** | File names end with `.component.ts`; component classes end with `Component`. | 163 Angular components follow this rule (e.g., `app.component.ts`). |
| **Angular pipes** | Pipe classes end with `Pipe` and are declared in a module. | 67 pipes detected (e.g., `customDatePipe`). |
| **SQL scripts** | All DDL/DML files are stored as `.sql` scripts and executed via migration tooling. | 258 `sql_script` components. |
| **Dockerfile** | Single Dockerfile (`dockerfile`) defines the base Ubuntu image for containers. | `Dockerfile` in the repository. |
| **Versioning** | REST API version is part of the URL (`/uvz/v1/...`). | Consistent across all controllers. |
| **Documentation** | All public APIs must be documented with OpenAPI/Swagger (not present yet – recommended). |
| **Error handling** | Controllers must return proper HTTP status codes (e.g., 400, 404, 500) as shown in the runtime scenarios. |

---

*All constraints are derived directly from the factual architecture data (containers, component counts, detected stereotypes) and the high‑level analysis (architecture style, design patterns, quality assessment). No new components have been invented.*