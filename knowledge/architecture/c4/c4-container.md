# C4 Level 2: Container Diagram

## 2.1 Overview
The **uvz** system is composed of four separately deployable containers.  A *container* in the C4 terminology is a runnable or buildable unit such as an application, a test suite, or a library.  The diagram below (see `c4-container.drawio`) shows the high‑level runtime view, the technology choices, and the communication paths between the containers.

---

## 2.2 Container Inventory

### 2.2.1 Application Containers
| Container | Technology | Responsibility | Deployment |
|-----------|------------|----------------|------------|
| **backend** | Spring Boot (Java, Gradle) | Core business logic, REST API, data processing | Deployed as a JVM service (Docker/K8s) |
| **frontend** | Angular (npm) | SPA UI, consumes backend REST API | Deployed as static assets served by a web server (NGINX) |
| **e2e‑xnp** | Playwright (npm) | End‑to‑end UI test suite | Executed in CI pipeline |
| **import‑schema** | Java/Gradle library | Schema import utilities used by backend | Packaged as a JAR and included in backend build |

### 2.2.2 Data Containers
| Container | Technology | Purpose | Persistence |
|-----------|------------|---------|-------------|
| *None* (the system currently uses external databases not modelled as containers) | – | – | – |

---

## 2.3 Container Details

### 2.3.1 Backend (`container.backend`)
- **Technology**: Spring Boot, built with Gradle
- **Purpose**: Implements the domain model, application services, and exposes a RESTful API for the UI and external clients.
- **Main Ports**: `8080/tcp` (HTTP/JSON)
- **Key Interfaces**:
  - `REST API` (JSON over HTTP) – consumed by *frontend* and *e2e‑xnp*.
  - Library API – consumed by *import‑schema* (internal JAR dependency).

### 2.3.2 Frontend (`container.frontend`)
- **Technology**: Angular (npm)
- **Purpose**: Single‑page application that provides the user interface and orchestrates calls to the backend.
- **Main Ports**: `4200/tcp` (development) / `80/tcp` (production static assets)
- **Key Interfaces**:
  - Consumes **Backend REST API** (JSON/HTTP).
  - Exposes no public API; only internal test hooks used by *e2e‑xnp*.

### 2.3.3 E2E‑XNP (`container.e2e_xnp`)
- **Technology**: Playwright (npm)
- **Purpose**: Automated end‑to‑end UI tests that validate the integration of *frontend* and *backend*.
- **Main Ports**: Executes HTTP calls against the *frontend* URL.
- **Key Interfaces**:
  - Calls *frontend* HTTP endpoints (simulated user actions).

### 2.3.4 Import‑Schema (`container.import_schema`)
- **Technology**: Java library built with Gradle
- **Purpose**: Provides utilities for importing and validating data schemas; bundled as a JAR and used by the *backend* at runtime.
- **Main Ports**: None (in‑process library).
- **Key Interfaces**:
  - Exposes Java classes/methods consumed by *backend*.

---

## 2.4 Container Interactions

### 2.4.1 Synchronous Communication
| Source | Target | Method | Format | Purpose |
|--------|--------|--------|--------|---------|
| Frontend | Backend | HTTP `GET/POST/PUT/DELETE` | JSON | UI data retrieval, command execution |
| Backend | Frontend | HTTP `200 OK` responses | JSON | Return data to UI |
| E2E‑XNP | Frontend | HTTP (browser automation) | HTML/JSON | Automated UI validation |
| Backend | Import‑Schema (library) | In‑process method call | Java objects | Schema import & validation |

### 2.4.2 Asynchronous Communication
| Source | Target | Method | Format | Purpose |
|--------|--------|--------|--------|---------|
| *None* (current architecture uses only request/response interactions) | | | | |

---

## 2.5 Technology Stack Summary
| Layer | Technology | Version (example) |
|-------|------------|-------------------|
| Presentation (UI) | Angular | 15.x |
| Application (Backend) | Spring Boot | 3.1.x |
| Test Automation | Playwright | 1.35.x |
| Build System | Gradle | 8.x |
| Library | Java (JDK 17) | 17 |

---

## 2.6 Container Diagram
The visual representation of the containers and their relationships can be found in the Draw.io file:

```
[c4/c4-container.drawio]
```

---

*Document generated on 2026‑02‑07 using real architecture facts.*