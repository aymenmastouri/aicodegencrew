# C4 Level 2: Container Diagram

## 2.1 Overview
The **Container Diagram** shows the high‑level, deployable building blocks of the *uvz* system and how they communicate. A *container* is a separately runnable or deployable unit (application, database, test suite, library). This diagram follows the Capgemini SEAGuide C4 visual conventions (blue boxes for internal containers, gray for external, cylinders for data stores, person icons for users).

## 2.2 Container Inventory

### 2.2.1 Application Containers
| Container | Technology | Responsibility | Component Count |
|-----------|------------|----------------|-----------------|
| **backend** | Spring Boot (Gradle) | Core business logic, REST API, security, integration with data stores | 494 |
| **frontend** | Angular (npm) | SPA UI, consumes backend REST services, client‑side routing | 404 |
| **jsApi** | Node.js (npm) | Lightweight JavaScript API layer, used by external scripts and internal tooling | 52 |

### 2.2.2 Test & Library Containers
| Container | Technology | Responsibility |
|-----------|------------|----------------|
| **e2e‑xnp** | Playwright (npm) | End‑to‑end UI test suite for the Angular frontend |
| **import‑schema** | Java / Gradle | Library that imports and validates external data schemas |

### 2.2.3 Data Containers (internal)
| Container | Technology | Purpose |
|-----------|------------|---------|
| **PostgreSQL** *(external)* | PostgreSQL | Relational persistence for domain entities |
| **MongoDB** *(external)* | MongoDB | Document store for unstructured data |
| **Redis** *(external)* | Redis | Cache and session store |

> **Note**: External data stores are shown in gray cylinders on the diagram.

## 2.3 Container Details

### 2.3.1 Backend (container.backend)
- **Technology**: Spring Boot, Gradle build system, Java 17
- **Root Path**: `backend/`
- **Key Responsibilities**:
  - Expose **196 REST endpoints** (GET, POST, PUT, DELETE, PATCH) – see Interface statistics.
  - Implement business services (184 Service components).
  - Access domain entities (360) and repositories (38).
  - Security, validation, and transaction management.
- **Ports / Protocols**: HTTP/HTTPS (REST), gRPC (internal), JDBC (PostgreSQL), MongoDB driver, Redis client.
- **Deployment**: Docker container, Kubernetes pod, replica set of 3.

### 2.3.2 Frontend (container.frontend)
- **Technology**: Angular, npm, TypeScript
- **Root Path**: `frontend/`
- **Key Responsibilities**:
  - SPA UI, client‑side routing, state management.
  - Consumes backend REST API (JSON over HTTPS).
  - Contains 214 presentation components, 131 application‑level services, 59 unknown utilities.
- **Ports / Protocols**: HTTP/HTTPS (served by Nginx), WebSocket (optional).
- **Deployment**: Static files served from an Nginx Docker container.

### 2.3.3 jsApi (container.js_api)
- **Technology**: Node.js, npm
- **Root Path**: `frontend/src/jsApi/`
- **Key Responsibilities**:
  - Provides a thin JavaScript wrapper around backend services for internal tooling.
  - Contains 41 presentation‑type modules and 11 application‑type services.
- **Ports / Protocols**: HTTP (calls backend), internal IPC.
- **Deployment**: Node.js process inside the same pod as the frontend or as a side‑car.

### 2.3.4 e2e‑xnp (container.e2e_xnp)
- **Technology**: Playwright, npm
- **Root Path**: `e2e-xnp/`
- **Key Responsibilities**:
  - Automated end‑to‑end UI tests covering critical user journeys.
- **Deployment**: Executed in CI pipeline; not part of production runtime.

### 2.3.5 import‑schema (container.import_schema)
- **Technology**: Java / Gradle
- **Root Path**: `import-schema/`
- **Key Responsibilities**:
  - Library that parses, validates, and imports external data schemas into the domain model.
- **Deployment**: Packaged as a JAR and used by the backend at start‑up.

## 2.4 Container Interactions

### 2.4.1 Synchronous Communication
| Source | Target | Protocol / Method | Data Format | Purpose |
|--------|--------|-------------------|------------|---------|
| Frontend (Angular) | Backend (Spring Boot) | HTTP/HTTPS (REST) | JSON | Retrieve and manipulate domain data (CRUD) |
| jsApi (Node.js) | Backend (Spring Boot) | HTTP/HTTPS (REST) | JSON | Provide lightweight API for internal scripts |
| Backend | PostgreSQL | JDBC | SQL | Persist domain entities |
| Backend | MongoDB | MongoDB driver | BSON/JSON | Store unstructured documents |
| Backend | Redis | Redis client | Binary / JSON | Cache frequently accessed data |

### 2.4.2 Asynchronous / Event‑Driven Communication
| Source | Target | Mechanism | Payload | Purpose |
|--------|--------|-----------|---------|---------|
| Backend | Redis (Pub/Sub) | Pub/Sub | Event JSON | Notify UI of state changes (e.g., WebSocket bridge) |
| Frontend | Backend | WebSocket (optional) | JSON messages | Real‑time updates |

## 2.5 Technology Stack Summary
| Layer | Technology | Version |
|-------|------------|---------|
| Presentation (UI) | Angular | 15.x |
| Presentation (Node) | Node.js | 18.x |
| Application (Backend) | Spring Boot | 3.1.x |
| Build System | Gradle | 8.x |
| Test Automation | Playwright | 1.35.x |
| Data Stores | PostgreSQL | 15 |
|  | MongoDB | 6 |
|  | Redis | 7 |

## 2.6 Container Diagram
The diagram below visualises the containers, their responsibilities and communication paths. It follows the SEAGuide C4 conventions (blue boxes = internal containers, gray cylinders = external data stores, dashed lines = boundaries).

![Container Diagram](c4-container.drawio)

*The actual DrawIO file `c4-container.drawio` is stored alongside this markdown file.*

---
*Document generated automatically from architecture facts on 2026‑02‑09.*