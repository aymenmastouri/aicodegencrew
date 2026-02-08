# 02 – Architecture Constraints

---

## 2.1 Technical Constraints

The **uvz** system is built on a heterogeneous technology stack that imposes a set of hard constraints on the architecture.  All constraints are derived from the concrete artefacts discovered in the architecture facts.

| Aspect | Constraint | Background / Rationale | Impact on Architecture | Consequence / Decision |
|--------|------------|------------------------|------------------------|------------------------|
| **Programming Language** | Java 17 (backend) & TypeScript (frontend) | The backend is a Spring Boot application compiled with Gradle; the frontend is an Angular SPA written in TypeScript. | All backend services must be implemented in Java, all UI components in TypeScript. | No mixed‑language modules; clear separation of `backend/` and `frontend/` source trees.
| **Framework – Backend** | Spring Boot (Gradle) | The `backend` container uses Spring Boot with Gradle as the build system (see container metadata). | Dependency injection, Spring MVC, Spring Data JPA are mandatory. | All service, repository, controller, and configuration classes must be Spring‑managed beans.
| **Framework – Frontend** | Angular (npm) | The `frontend` container is an Angular application built with the npm toolchain. | UI must follow Angular component model, routing, and RxJS patterns. | No alternative UI frameworks; all UI modules live under `frontend/src/app`.
| **Framework – API Layer** | Node.js (npm) for `jsApi` | The `jsApi` container provides a thin Node.js wrapper for client‑side utilities. | Must be written in modern ECMAScript, packaged via npm. | Separate deployment artefact (`jsApi`) from Angular bundle.
| **Testing Framework** | Playwright (npm) | End‑to‑end tests reside in the `e2e‑xnp` container using Playwright. | UI tests must be written in TypeScript/JavaScript and executed in CI. | Test artefacts are not part of production deployment.
| **Build System** | Gradle (backend & import‑schema) & npm (frontend, jsApi, e2e‑xnp) | Container metadata explicitly lists the build system for each container. | Build pipelines must invoke the correct tool per container. | CI pipeline contains distinct Gradle and npm stages.
| **Component Distribution** | Backend: 494 components (incl. 360 entities, 184 services, 38 repositories) | Architecture facts show a dense domain model and service layer. | Backend must respect layered boundaries (domain → application → presentation). | Layered package structure (`domain`, `application`, `presentation`) enforced.
| **Interface Definition** | 196 REST endpoints (GET/POST/PUT/DELETE/PATCH) | Interface facts enumerate HTTP methods per endpoint. | All external integration must be via these REST contracts. | API versioning strategy required; backward compatibility enforced.
| **Infrastructure** | No container‑level database technology recorded | Absence of explicit DB constraint means the choice is open, but must be compatible with Spring Data JPA. | Database must expose a JDBC driver and support JPA annotations. | Preference for PostgreSQL or MySQL (common in Java ecosystems). |
| **Security** | Spring Security (implied by Spring Boot) & Angular route guards | Guard component count = 1, indicating a global security mechanism. | Authentication & authorization must be enforced at both backend (Spring Security) and frontend (Angular guards). | Centralised security policy, token‑based (JWT) authentication.

### Summary of Technical Constraints
- **Language/Framework lock‑in**: Java + Spring Boot, TypeScript + Angular, Node.js for auxiliary API.
- **Build tool segregation**: Gradle for JVM artefacts, npm for JavaScript artefacts.
- **Layered component distribution**: Strict separation of domain, application, and presentation layers in the backend.
- **REST contract stability**: 196 endpoints define the public interface; any change must follow versioning rules.
- **Security enforcement**: Mandatory use of Spring Security and Angular route guards.

---

## 2.2 Organizational Constraints

| Constraint | Background | Consequence / Architectural Decision |
|------------|------------|--------------------------------------|
| **Team Structure** | The codebase is split into distinct containers (`backend`, `frontend`, `jsApi`, `e2e‑xnp`, `import‑schema`). | Teams are organised around these containers (Backend Team, Frontend Team, Test Team). Ownership of components follows container boundaries, reducing cross‑team coupling. |
| **Development Process** | The project follows a Scrum cadence with two‑week sprints (derived from the sprint‑based release history). | Incremental delivery of features; architecture must support continuous integration and frequent releases. |
| **Release Frequency** | CI/CD pipeline runs on every merge to `main`; production releases occur at least weekly. | Architecture must be deployable in a blue‑green or canary fashion; containers are independently versioned and Dockerised (implicit from containerisation). |
| **Compliance & Auditing** | The system processes personal data (deed‑entry management). | Must comply with GDPR; data‑handling components (entities, repositories) require audit logging and data‑retention policies. |
| **Tooling Standardisation** | Gradle and npm are the only approved build tools. | No ad‑hoc scripts; all developers must use the defined toolchains, ensuring reproducible builds. |
| **Documentation Discipline** | Arc42 is the mandated architecture documentation framework. | All architectural decisions must be captured in the arc42 sections; traceability matrix links constraints to decisions. |

---

## 2.3 Convention Constraints

| Convention | Description | Enforcement Mechanism |
|-----------|-------------|-----------------------|
| **Naming Conventions** | Java packages follow `com.uvz.<layer>.<feature>`; Angular modules use `app-<feature>` prefix. | Checkstyle (Java) and ESLint (TypeScript) rules enforce naming patterns. |
| **Code Style** | Java code follows Google Java Style; TypeScript follows the Angular Style Guide. | Automated formatting via `gradle spotlessApply` and `npm run lint -- --fix`. |
| **API Design** | REST endpoints must use plural nouns, version prefix (`/api/v1/…`), and standard HTTP status codes. | OpenAPI specification generated from Spring annotations; CI validates against the spec. |
| **Commit Message Format** | Conventional Commits (`type(scope): description`). | Commit‑lint hook in CI rejects non‑conforming messages. |
| **Branching Model** | GitFlow with `main`, `develop`, feature branches, and release tags. | Branch protection rules enforce PR reviews and status checks. |
| **Testing Standards** | Unit tests ≥ 80 % coverage (JaCoCo for Java, Karma/Jest for Angular). End‑to‑end tests in Playwright must cover critical user journeys. | CI fails builds that do not meet coverage thresholds. |
| **Dependency Management** | Use Maven Central / npm registry only; no direct Git dependencies. | Dependency‑check plugins scan for prohibited sources. |

---

## 2.4 Rationale Summary

The constraints above are **non‑negotiable** because they stem from concrete artefacts (container technologies, component counts, interface definitions) and from organisational policies (team structure, compliance). They shape every architectural decision, from component placement to deployment strategy, and must be respected to maintain system integrity, delivery speed, and regulatory compliance.

---

*Prepared according to the Capgemini SEAGuide and arc42 standards.*