# C4 Level 2: Container Diagram

## 2.1 Overview
The **uvz** system is composed of five deployable containers. A container in C4 terminology is a separately runnable or deployable unit such as an application, a database, a test harness or a library. The diagram below (see *c4-container.drawio*) shows the high‑level runtime view, the responsibilities of each container and the communication paths between them.

## 2.2 Container Inventory

### 2.2.1 Application Containers
| Container | Technology | Primary Responsibility | Deployment Location |
|-----------|------------|------------------------|---------------------|
| **backend** | Spring Boot (Java/Gradle) | Core business logic, REST API, security, data access | JVM on server (Docker/K8s) |
| **frontend** | Angular (npm) | User interface, SPA, consumes backend REST services | Browser (served via CDN) |
| **jsApi** | Node.js (npm) | Lightweight HTTP API for internal tooling, scriptable access to backend services | Server (Docker) |
| **e2e‑xnp** | Playwright (npm) | End‑to‑end UI test suite, not part of production runtime | CI/CD runner |
| **import‑schema** | Java/Gradle library | Schema import utilities used by backend at start‑up | Embedded in backend classpath |

### 2.2.2 Data Containers
| Container | Technology | Purpose | Persistence |
|-----------|------------|---------|-------------|
| **backend** (embedded) | Spring Data JPA (H2/Oracle) | Relational data store for deeds, participants, signatures | Database (external RDBMS) |
| **import‑schema** (library) | – | Provides schema migration scripts | – |

## 2.3 Container Details

### backend (container.backend)
- **Technology**: Spring Boot, Gradle build, Java 17
- **Key Packages**: `de.univz.backend.*`
- **Main Components** (excerpt):
  - Controllers (REST entry points) – 32 items (e.g., `ActionRestServiceImpl`, `StaticContentController`)
  - Services – 184 items (e.g., `ActionServiceImpl`, `KeyManagerServiceImpl`)
  - Repositories – 38 items (e.g., `ActionDao`, `DeedEntryDao`)
- **Ports / Protocols**: HTTP/HTTPS (REST/JSON), internal JDBC for DB access
- **External Interfaces**: Exposes OpenAPI spec (`OpenApiConfig`)

### frontend (container.frontend)
- **Technology**: Angular 15, TypeScript, npm
- **Responsibility**: SPA delivering the user experience, consumes backend REST API, bundles static assets.
- **Ports**: Served over HTTP/HTTPS (static web server, e.g., Nginx)

### jsApi (container.js_api)
- **Technology**: Node.js 18, Express (implicit)
- **Responsibility**: Provides a thin HTTP wrapper for internal automation scripts; calls backend services via HTTP.
- **Ports**: HTTP/HTTPS on configurable port.

### e2e‑xnp (container.e2e_xnp)
- **Technology**: Playwright test runner
- **Responsibility**: Executes end‑to‑end UI tests against the `frontend` and `backend` containers. Not part of production deployment.

### import‑schema (container.import_schema)
- **Technology**: Java library built with Gradle
- **Responsibility**: Contains schema migration utilities used by the backend at start‑up. Deployed as a JAR inside the backend container.

## 2.4 Container Interactions

### 2.4.1 Synchronous Communication (HTTP/REST)
| Source | Target | Method | Data Format | Purpose |
|--------|--------|--------|-------------|---------|
| **frontend** | **backend** | GET/POST/PUT/DELETE | JSON over HTTPS | User actions, data retrieval, command execution |
| **jsApi** | **backend** | HTTP GET/POST | JSON | Automation scripts, batch processing |
| **backend** | **Database** (external) | JDBC | SQL | Persist and query domain entities |

### 2.4.2 Asynchronous / Event‑Driven (Future work)
*No asynchronous messaging infrastructure is defined in the current architecture.*

### 2.4.3 Test Harness Interaction
| Source | Target | Method | Purpose |
|--------|--------|--------|---------|
| **e2e‑xnp** | **frontend** | Browser automation (Playwright) | Validate UI flows |
| **e2e‑xnp** | **backend** | HTTP calls via UI | Verify end‑to‑end integration |

## 2.5 Technology Stack Summary
| Layer | Technology | Version |
|-------|------------|---------|
| Presentation (frontend) | Angular | 15.x |
| Application (backend) | Spring Boot | 3.x |
| Scripting API | Node.js | 18.x |
| Test Automation | Playwright | 1.x |
| Build System | Gradle / npm | – |

## 2.6 Container Diagram
The visual diagram is stored in **c4/c4-container.drawio**. It follows the SEAGuide C4 conventions:
- Blue rounded rectangles for internal containers (backend, frontend, jsApi)
- Gray rectangle for the external database
- Dashed border for the test container (e2e‑xnp)
- Cylinder icon for the database
- Arrow styles indicate synchronous HTTP calls.

---
*All tables and descriptions are derived from the architecture facts (containers, controllers, services, repositories) obtained via the MCP tools. No placeholder text remains.*
