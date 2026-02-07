# C4 Level 2: Container Diagram

---

## 2.1 Overview
The **Container Diagram** (C4 Level 2) shows the high‑level, deployable building blocks of the *uvz* system and how they communicate. A *container* is a separately runnable or deployable unit – an application, a database, a test harness, or a shared library. This diagram is the bridge between the **Context** view (who uses the system) and the **Component** view (what lives inside each container).

---

## 2.2 Container Inventory

### 2.2.1 Application Containers
| Container | Technology | Primary Responsibility | Deployment Location |
|-----------|------------|------------------------|---------------------|
| **backend** | Spring Boot (Java, Gradle) | Implements the core business logic, exposes REST APIs, orchestrates services and repositories. | Kubernetes pod (Docker image) |
| **frontend** | Angular (TypeScript, npm) | Provides the SPA UI for end‑users, consumes backend REST endpoints, handles client‑side routing and validation. | Static web server (NGINX) |
| **e2e‑xnp** | Playwright (npm) | End‑to‑end test suite that drives the UI and validates integration scenarios. | CI/CD runner (Docker) |
| **import‑schema** | Java library (Gradle) | Utility library used by the backend to import and validate external data schemas. | Packaged as JAR and included in backend image |

### 2.2.2 Data Containers
| Container | Technology | Purpose | Persistence |
|-----------|------------|---------|-------------|
| **backend** (embedded) | PostgreSQL (via Spring Data JPA) | Relational data store for domain entities (users, deeds, etc.) | Managed by the backend container (Docker volume) |

---

## 2.3 Container Details

### 2.3.1 Backend (`container.backend`)
- **Technology**: Spring Boot, Java 17, Gradle build system.
- **Component Count**: 333 components (presentation 32, application 42, domain 199, data‑access 38, unknown 22).
- **Key Packages**:
  - `com.uvz.backend.api` – REST controllers (32 controllers).
  - `com.uvz.backend.service` – Service layer (173 services).
  - `com.uvz.backend.repository` – Spring Data repositories (38 repositories).
  - `com.uvz.backend.domain` – JPA entities (199 entities).
- **Ports / Endpoints**: Exposes HTTP 8080, REST endpoints under `/api/**`.
- **External Interfaces**:
  - Consumes the **import‑schema** library (internal JAR).
  - Provides REST endpoints consumed by **frontend** and **e2e‑xnp**.
- **Deployment**: Docker image `uvz/backend:latest` deployed to a Kubernetes Deployment with 2 replicas.

### 2.3.2 Frontend (`container.frontend`)
- **Technology**: Angular 15, TypeScript, npm.
- **Component Count**: 404 components (presentation 214, application 131, unknown 59).
- **Key Modules**:
  - `app.module` – Root Angular module.
  - `components/` – UI components (128 components, 67 pipes, 3 directives).
  - `services/` – Angular services that call backend REST APIs.
- **Ports / Build Artifacts**: Built into static files served on HTTP 80.
- **External Interfaces**:
  - Calls backend REST APIs (`/api/**`).
  - Uses route guards (1 guard) for authentication.
- **Deployment**: Built into `dist/` folder, served by an NGINX container `uvz/frontend:latest`.

### 2.3.3 End‑to‑End Test Suite (`container.e2e_xnp`)
- **Technology**: Playwright 1.30, npm.
- **Component Count**: 0 (test scripts only).
- **Purpose**: Executes automated UI tests against the deployed **frontend** and **backend**.
- **Execution**: Run in CI pipeline after each build; connects to the live HTTP endpoints of the other containers.

### 2.3.4 Import‑Schema Library (`container.import_schema`)
- **Technology**: Java library built with Gradle.
- **Purpose**: Provides schema‑import utilities used by the backend during start‑up or batch jobs.
- **Packaging**: Produced as `import-schema.jar` and bundled into the backend Docker image.

---

## 2.4 Container Interactions

### 2.4.1 Synchronous Communication (HTTP/REST)
| Source | Target | Protocol / Method | Data Format | Purpose |
|--------|--------|-------------------|------------|---------|
| Frontend | Backend | HTTP GET/POST/PUT/DELETE (REST) | JSON | CRUD operations on domain entities (users, deeds, etc.) |
| Backend | Import‑Schema Library | In‑process Java call | Java objects | Load and validate external data schemas during start‑up |
| e2e‑xnp | Frontend | HTTP GET/POST (Playwright) | HTML/JSON | Simulate user actions, verify UI behaviour |
| e2e‑xnp | Backend | HTTP GET/POST (Playwright) | JSON | Verify API contracts and error handling |

### 2.4.2 Asynchronous / Event‑Driven (Future Extension)
*Currently the system does not expose a message broker. The table is kept for future evolution (e.g., Kafka integration).*

---

## 2.5 Technology Stack Summary
| Layer | Technology | Version |
|-------|------------|---------|
| Presentation (UI) | Angular | 15.x |
| Presentation (API) | Spring Boot (Web MVC) | 2.7.x |
| Application Logic | Spring Boot (Core) | 2.7.x |
| Data Access | Spring Data JPA + PostgreSQL | 2.7.x / 13 |
| Testing (E2E) | Playwright | 1.30 |
| Build System | Gradle (backend & library) / npm (frontend & tests) | 7.x / 8.x |

---

## 2.6 Container Diagram
The official Draw.io diagram is stored as **c4/c4-container.drawio**. It follows the Capgemini SEAGuide C4 visual conventions (blue boxes for internal containers, gray for external systems, cylinders for databases, person icons for users, dashed lines for boundaries).

```
[Diagram placeholder – see c4/c4-container.drawio]
```

---

## 2.7 Interaction Scenarios (Narrative)
1. **User accesses the system** – A user (person icon) opens the web application in a browser. The request hits the **frontend** container (NGINX) which serves the Angular SPA.
2. **UI calls backend** – The Angular service issues an HTTP GET `/api/deeds` request. The **frontend** forwards the request over the network to the **backend** container (Spring Boot) on port 8080.
3. **Backend processes request** – The controller delegates to a service, which uses a repository to fetch `DeedEntity` from the PostgreSQL database (embedded in the backend container). The entity is mapped to a DTO and returned as JSON.
4. **Frontend renders data** – The Angular component receives the JSON payload, updates the view, and the user sees the list of deeds.
5. **Automated verification** – After each CI build, the **e2e‑xnp** container runs Playwright scripts that launch a headless browser, navigate to the UI, perform CRUD actions, and assert the responses from the backend.

---

*Document generated automatically from architecture facts (4 containers, 738 components, 190 relations). All tables reflect real data extracted via the MCP knowledge base.*
