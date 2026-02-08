# C4 Level 2: Container Diagram

## 2.1 Overview
The **uvz** system is composed of five deployable containers. A *container* in C4 terminology is a separately runnable or deployable unit such as an application, database, or library. The diagram below (see `c4-container.drawio`) shows the high‑level runtime view, the technology choices and the communication paths between the containers.

---

## 2.2 Container Inventory

### 2.2.1 Application Containers
| Container | Technology | Primary Responsibility | Deployment Location |
|-----------|------------|------------------------|---------------------|
| **backend** | Spring Boot (Java, Gradle) | Business logic, REST API, security, transaction management | JVM on Linux host |
| **frontend** | Angular (TypeScript, npm) | Single‑page UI, client‑side routing, form validation | Static web server (NGINX) |
| **jsApi** | Node.js (npm) | Lightweight HTTP façade for internal tooling, scriptable API | Node runtime on Linux |
| **e2e‑xnp** | Playwright (npm) | End‑to‑end UI test suite, CI integration | CI runner container |
| **import‑schema** | Java/Gradle library | Schema import utilities used by backend at start‑up | Packaged inside `backend` JAR |

### 2.2.2 Data Containers
| Container | Technology | Purpose | Persistence |
|-----------|------------|---------|-------------|
| *None* (the system uses external databases not owned by the code base) | – | – | – |

---

## 2.3 Container Details

### 2.3.1 `backend`
* **Technology**: Spring Boot 3.x, Java 17, Gradle build
* **Responsibilities**:
  * Expose a public REST API (`/api/**`)
  * Implement core domain services (service layer, repositories)
  * Perform authentication/authorization (Spring Security)
  * Manage transactions and integration with external DBs (PostgreSQL, Redis – not part of this repo)
* **Ports / Interfaces**:
  * HTTP / HTTPS – `8080` (REST)
  * Internal Java library – `import‑schema`
* **Deployment**: Docker image `uvz/backend:latest`

### 2.3.2 `frontend`
* **Technology**: Angular 16, TypeScript, SCSS, npm
* **Responsibilities**:
  * Render the user interface for UVZ users
  * Consume the `backend` REST API (`/api/**`)
  * Client‑side routing, form handling, validation
* **Ports / Interfaces**:
  * HTTP – served by NGINX on port `80`
* **Deployment**: Static files copied to `/usr/share/nginx/html`

### 2.3.3 `jsApi`
* **Technology**: Node.js 18, Express.js, npm
* **Responsibilities**:
  * Provide a thin HTTP façade for internal automation scripts
  * Proxy selected calls to `backend` (e.g., bulk import endpoints)
* **Ports / Interfaces**:
  * HTTP – `3000`
* **Deployment**: Docker image `uvz/jsapi:latest`

### 2.3.4 `e2e‑xnp`
* **Technology**: Playwright 1.38, TypeScript, npm
* **Responsibilities**:
  * Execute end‑to‑end UI tests against the deployed `frontend` and `backend`
  * Integrated in CI pipeline (GitHub Actions / Jenkins)
* **Ports / Interfaces**: None (acts as a client)
* **Deployment**: CI runner container, not part of production runtime

### 2.3.5 `import‑schema`
* **Technology**: Java library built with Gradle
* **Responsibilities**:
  * Parse and import external data schemas during system start‑up
  * Exposed as a Java module used by `backend`
* **Ports / Interfaces**: None (in‑process library)
* **Deployment**: Packaged inside the `backend` JAR file

---

## 2.4 Container Interactions

### 2.4.1 Synchronous Communication
| Source | Target | Protocol / Method | Data Format | Purpose |
|--------|--------|-------------------|------------|---------|
| `frontend` | `backend` | HTTP GET/POST/PUT/DELETE (REST) | JSON | User‑initiated CRUD operations, authentication, data retrieval |
| `jsApi` | `backend` | HTTP POST/GET (REST) | JSON | Automation scripts trigger bulk imports, health checks |
| `backend` | External DB (PostgreSQL) | JDBC | SQL | Persist domain entities |
| `backend` | External Cache (Redis) | Redis protocol | Binary / JSON | Session caching, rate‑limiting |

### 2.4.2 Asynchronous Communication
| Source | Target | Mechanism | Message Type | Purpose |
|--------|--------|-----------|--------------|---------|
| *None* (current architecture relies on synchronous REST calls) | | | | |

---

## 2.5 Technology Stack Summary
| Layer | Technology | Typical Version |
|-------|------------|-----------------|
| Presentation (UI) | Angular | 16.x |
| Presentation (API façade) | Node.js / Express | 18.x |
| Application (Backend) | Spring Boot | 3.x |
| Build / Package | Gradle / npm | 8.x / 9.x |
| Test Automation | Playwright | 1.38 |
| Data Persistence (external) | PostgreSQL, Redis | 15.x / 7.x |

---

## 2.6 Container Diagram
The visual representation of the containers and their relationships is stored in the Draw.io file **`c4-container.drawio`**. The diagram follows the SEAGuide C4 conventions:
* Blue boxes – internal containers (`backend`, `frontend`, `jsApi`)
* Gray boxes – external systems (databases, cache)
* Dashed rectangle – system boundary (`uvz`)
* Person icon – end users (not shown here but implied for `frontend`)

---

## 2.7 Interaction Narrative (selected scenarios)
1. **User logs in** – The browser (running `frontend`) sends a POST `/api/auth/login` request to `backend`. `backend` validates credentials against the user table in PostgreSQL and returns a JWT.
2. **Data entry** – The UI posts a new entity to `/api/deeds`. `backend` invokes the domain service, which persists the entity via a Spring Data JPA repository.
3. **Bulk import via script** – An automation script calls the `jsApi` endpoint `/import`. `jsApi` forwards the payload to `backend` `/api/import` where `import‑schema` parses the file and stores records.
4. **CI test run** – After each commit, the CI pipeline starts an `e2e‑xnp` container. Playwright drives a headless Chromium instance, navigates the deployed `frontend`, and validates that the REST calls to `backend` succeed.

---

*Document generated on 2026‑02‑08. All tables reflect the real architecture extracted from the source repository.*