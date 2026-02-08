# C4 Level 2: Container Diagram

---

## 2.1 Overview
The **Container Diagram** shows the high‑level, deployable building blocks of the *uvz* system and how they communicate. A *container* is a separately runnable or deployable unit (application, database, library, test suite). This diagram follows the Capgemini SEAGuide C4 conventions: internal containers are shown as blue boxes, external systems as gray, databases as cylinders, and users as person icons. All communication protocols, ports and data formats are documented.

---

## 2.2 Container Inventory

### 2.2.1 Application Containers
| Container | Technology | Primary Responsibility | Deployment Location |
|-----------|------------|------------------------|---------------------|
| **backend** | Spring Boot (Java/Gradle) | Core business logic, REST API, orchestration of domain services and data‑access repositories | Kubernetes pod (Docker container) |
| **frontend** | Angular (npm) | Single‑page web UI for end‑users, consumes backend REST endpoints | Static web server (NGINX) |
| **jsApi** | Node.js (npm) | Lightweight JavaScript API layer used by external scripts and internal tooling | Node runtime on same host as frontend |
| **import‑schema** | Java/Gradle library | Schema import utilities, used by backend during start‑up and batch jobs | Packaged as JAR, loaded by backend |

### 2.2.2 Test & Supporting Containers
| Container | Technology | Role | Deployment |
|-----------|------------|------|------------|
| **e2e‑xnp** | Playwright (npm) | End‑to‑end UI test suite, validates user flows against the deployed frontend | CI/CD pipeline (Docker container) |

---

## 2.3 Container Details

### 2.3.1 backend (container.backend)
- **Technology**: Spring Boot, built with Gradle
- **Root Path**: `backend/`
- **Component Count**: 494 (presentation 32, application 42, data‑access 38, domain 360, unknown 22)
- **Exposed Interfaces**: 196 REST endpoints (GET 128, POST 30, PUT 18, DELETE 14, PATCH 6)
- **Ports**: HTTP 8080 (REST), HTTPS 8443 (optional)
- **Database Access**: Connects to external PostgreSQL (not modelled as a container here)
- **Key Packages**: `deedentry_logic_impl`, `service.impl`, `repository.impl`

### 2.3.2 frontend (container.frontend)
- **Technology**: Angular (npm)
- **Root Path**: `frontend/`
- **Component Count**: 404 (presentation 214, application 131, unknown 59)
- **Build**: `npm run build` → static assets
- **Served From**: NGINX on port 80/443
- **Key Modules**: UI components, routing, state management (NgRx)

### 2.3.3 jsApi (container.js_api)
- **Technology**: Node.js (npm)
- **Root Path**: `frontend\src\jsApi/`
- **Component Count**: 52 (presentation 41, application 11)
- **Purpose**: Provides a thin HTTP wrapper for internal tooling and third‑party scripts; forwards calls to the backend REST API.
- **Ports**: HTTP 3000 (internal only)

### 2.3.4 import‑schema (container.import_schema)
- **Technology**: Java/Gradle library
- **Root Path**: `import-schema/`
- **Component Count**: 0 (pure library)
- **Purpose**: Contains schema‑import utilities executed by the backend at start‑up or via scheduled jobs.

### 2.3.5 e2e‑xnp (container.e2e_xnp)
- **Technology**: Playwright (npm)
- **Root Path**: `e2e‑xnp/`
- **Component Count**: 0 (test scripts only)
- **Purpose**: Automated end‑to‑end UI tests executed in CI pipelines against the deployed frontend.

---

## 2.4 Container Interactions

### 2.4.1 Synchronous Communication (REST/HTTP)
| Source | Target | Protocol / Method | Data Format | Purpose |
|--------|--------|-------------------|------------|---------|
| **frontend** | **backend** | HTTPS/REST (GET, POST, PUT, DELETE, PATCH) | JSON | UI actions → business operations, data retrieval |
| **jsApi** | **backend** | HTTP/REST (GET, POST) | JSON | Script‑level API calls, batch operations |
| **backend** | **PostgreSQL (external DB)** | JDBC (SQL) | SQL | Persist and query domain entities |
| **backend** | **import‑schema** | Java library call | Java objects | Load/validate external schemas during start‑up |

### 2.4.2 Asynchronous / Event‑Based Communication
| Source | Target | Mechanism | Payload | Reason |
|--------|--------|-----------|---------|--------|
| **backend** | **frontend** | Server‑Sent Events / WebSocket (optional) | JSON | Real‑time notifications (e.g., job status) |
| **e2e‑xnp** | **frontend** | HTTP (test harness) | N/A | UI test execution against live UI |

---

## 2.5 Technology Stack Summary
| Layer | Technology | Version (as of latest build) |
|-------|------------|------------------------------|
| Presentation (Web) | Angular | 15.x |
| Presentation (Node) | Node.js | 18.x |
| Application (Backend) | Spring Boot | 3.1.x |
| Build System (Backend) | Gradle | 8.x |
| Test Automation | Playwright | 1.35.x |
| Library (Schema) | Java | 17 |
| Container Runtime | Docker / Kubernetes | 1.27 / 1.28 |

---

## 2.6 Container Diagram
The visual diagram is stored as a Draw.io file: **c4/c4-container.drawio**. It follows the SEAGuide C4 conventions:
- Blue rounded rectangles for internal containers (backend, frontend, jsApi, import‑schema)
- Gray rounded rectangles for external systems (PostgreSQL, CI/CD pipeline)
- Dashed boundary for the *uvz* system
- Person icon for end‑users interacting with the frontend
- Arrow styles: solid for synchronous HTTP/REST, dotted for asynchronous/event‑based.

---

*Document generated on 2026‑02‑08 using real architecture facts.*
