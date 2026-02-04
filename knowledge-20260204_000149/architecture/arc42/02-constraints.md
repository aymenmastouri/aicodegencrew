# 02 – Architecture Constraints

## 2.1 Technical Constraints

| Aspect | Constraint | Source / Rationale |
|--------|------------|--------------------|
| **Programming language** | **Java 17** (the backend is a Spring Boot application written in Java). | Inferred from the `backend` container’s technology stack (`Spring Boot` on Java). |
| **Framework** | **Spring Boot** (latest compatible version with Java 17). All services, controllers and repositories must be built as Spring beans and wired via Spring’s dependency‑injection container. | `backend` container metadata reports `framework: Spring Boot`. |
| **Web framework (frontend)** | **Angular v18‑LTS** (TypeScript 5.4.5). The SPA must follow Angular’s module, component and service conventions. | `frontend` container metadata reports `framework: Angular v18‑LTS`. |
| **Container runtime** | **Ubuntu** base image for Docker containers. All Docker images must be derived from the provided `docker` container (Ubuntu). | `docker` container listed as technology “ubuntu”. |
| **Database** | **PostgreSQL** (any supported version that runs in the supplied `postgres` container). All persistence must use PostgreSQL dialect, and JPA/Hibernate mappings must target PostgreSQL. | `postgres` container technology is PostgreSQL. |
| **Contract testing** | **Pact‑Broker** must be used for consumer‑driven contract tests; the broker runs in the `broker_app` container. | `broker_app` container technology is `pact‑broker`. |
| **Architecture style** | **Modular Monolith** + **Layered Architecture**.  All code must respect the three‑tier layering (Controller → Service → Repository) and keep modules internally decoupled. | `list_components_by_stereotype` for `architecture_style` returned `layered_architecture` and `modular_monolith_architecture`. |
| **Design patterns** | The implementation must employ the following patterns (as they are already present and expected to remain consistent):<br>• `repository_pattern`<br>• `factory_pattern`<br>• `builder_pattern`<br>• `singleton_pattern`<br>• `adapter_pattern`<br>• `observer_pattern` | `list_components_by_stereotype` for `design_pattern` returned exactly these six pattern names. |
| **API versioning** | Path‑based versioning (`/uvz/v1/...`). All REST endpoints must include the version segment. | The runtime scenarios and API analysis use the `/uvz/v1/` prefix. |
| **Packaging** | Backend packages must follow the namespace `de.bnotk.uvz.module.*` and end‑with descriptive suffixes (`*RestServiceImpl`, `*ServiceImpl`, `*Repository`). | All controller and service classes listed in the component inventory adhere to this convention. |
| **Build tool** | **Gradle** for the backend, **npm** for the frontend. Build scripts must not rely on alternative build systems. | `backend` container metadata lists `build_tool: Gradle`; `frontend` lists `build_tool: npm`. |
| **Operating system constraints** | All production containers run on Linux (Ubuntu); any native libraries must be compatible with this OS. | `docker` container is Ubuntu‑based. |

---

## 2.2 Organizational Constraints

| Constraint | Description |
|------------|-------------|
| **Team structure** | Development is organised around bounded contexts (e.g., `deedentry`, `numbermanagement`, `workflow`, `xnp`, `infrastructure`). Teams should own one or more contexts and keep inter‑context coupling “acceptable”. |
| **Deployment model** | The system is deployed via **Docker‑Compose**. All containers (`backend`, `frontend`, `postgres`, `broker_app`, `docker`) must be defined in a single `docker‑compose.yml` file and started together. |
| **Scaling approach** | Current scalability is **vertical** – increase JVM heap / CPU resources for the monolith. Horizontal scaling (multiple backend instances) is not part of the baseline, but the use of the `factory_pattern` and `repository_pattern` allows future extraction of services. |
| **Security governance** | Production must replace the mock authentication components (`JsonAuthorizationRestServiceImpl`, `CustomMethodSecurityExpressionHandler`) with a real identity provider (e.g., JWT/OAuth2). Security reviews must verify that only Spring‑Security‑managed endpoints are exposed. |
| **Compliance & audit** | Even though no explicit regulatory domain is defined, audit‑logging must be introduced for all security‑critical actions (authentication attempts, data modifications). |
| **Testing policy** | All public REST contracts must be validated against the **Pact‑Broker** before a release. Unit tests (JUnit) for Java and Jest/Playwright for Angular are mandatory. |
| **Release management** | Version numbers are tied to the API path (`/uvz/v1/`). Any breaking change must trigger a new major version in the path (e.g., `/uvz/v2/`). |
| **Documentation** | The architecture must be documented in arc42 format; each new module or integration point requires an update to the corresponding arc42 sections. |

---

## 2.3 Convention Constraints

| Area | Convention | Example |
|------|------------|---------|
| **Naming – Java classes** | Controllers → `*RestServiceImpl`<br>Services → `*ServiceImpl`<br>Repositories → `*Repository`<br>Entities → `<Domain>Entity` (PascalCase, suffix `Entity`) | `DeedEntryRestServiceImpl`, `ActionServiceImpl`, `DeedEntryEntity` |
| **Package structure** | Root package `de.bnotk.uvz.module` followed by bounded‑context name and layer (`api`, `service.impl.rest`, `dataaccess.api.dao`, …). | `de.bnotk.uvz.module.deedentry.service.impl.rest` |
| **Angular component naming** | Files end with `.component.ts`; component class names end with `Component`. Modules end with `.module.ts`. | `app.component.ts`, `app.module.ts` |
| **REST endpoint naming** | Plural nouns for collections, singular nouns for single resources, action verbs as sub‑resources (e.g., `/archiving/sign-submission-token`). All URLs start with `/uvz/v1/`. | `GET /uvz/v1/deedentries`, `POST /uvz/v1/archiving/sign-submission-token` |
| **Configuration** | All configurable values must be externalised via Spring `@ConfigurationProperties` (backend) or Angular environment files (frontend). No hard‑coded literals. |
| **Version control** | Feature branches must be merged through pull‑requests; the main branch reflects the current production version (`v1`). |
| **Logging** | Use SLF4J with Logback; log messages must include a correlation ID (e.g., request ID) to trace across components. |
| **Error handling** | Centralised `DefaultExceptionHandler` must translate exceptions to a consistent JSON error structure (`errorCode`, `message`, `timestamp`). |
| **Testing naming** | Test classes mirror the class under test with suffix `Test` (e.g., `DeedEntryServiceImplTest`). Angular tests end with `.spec.ts`. |
| **Build scripts** | Backend Gradle scripts must be placed under `build.gradle.kts` at the project root; frontend npm scripts must be defined in `package.json` (`build`, `test`, `start`). |
| **Docker images** | Image tags must follow the pattern `<component>-<version>` (e.g., `backend-1.0.0`). The `docker` container is used as the base for all images. |

These constraints together define the technical, organisational and conventional boundaries within which the **uvz** system must be designed, implemented, and evolved.