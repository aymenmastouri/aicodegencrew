# C4 Level 2: Container Diagram

## 2.1 Overview
The system **uvz** is composed of five deployable containers.  A *container* in C4 terminology is a separately runnable or deployable unit (application, test suite, library, etc.).  This document describes the containers, their responsibilities, technology choices and the way they interact.

## 2.2 Container Inventory

### 2.2.1 Application Containers
| Container ID | Name | Technology | Primary Responsibility |
|--------------|------|------------|------------------------|
| `container.backend` | Backend | Spring Boot (Java/Gradle) | Core business logic, REST API, data processing |
| `container.frontend` | Frontend | Angular (npm) | User‑interface, SPA, consumes Backend REST services |
| `container.js_api` | JS API | Node.js (npm) | Auxiliary HTTP API used by external scripts and internal services |

### 2.2.2 Test Containers
| Container ID | Name | Technology | Purpose |
|--------------|------|------------|---------|
| `container.e2e_xnp` | E2E‑XNP | Playwright (npm) | End‑to‑end UI and API test automation |

### 2.2.3 Library Containers
| Container ID | Name | Technology | Purpose |
|--------------|------|------------|---------|
| `container.import_schema` | Import‑Schema | Java/Gradle | Shared schema import library used by Backend |

## 2.3 Container Details

### Backend (`container.backend`)
- **Technology**: Spring Boot, built with Gradle
- **Root Path**: `backend`
- **Component Count**: 494 (presentation 32, application 42, dataaccess 38, domain 360, unknown 22)
- **Key Responsibilities**:
  - Expose a REST/HTTPS API for the Frontend and JS API
  - Implement core domain services (action, deed entry, key‑manager, archiving, etc.)
  - Access data via repositories and DAOs
- **Ports / Endpoints**: See Section 2.4 for interaction summary

### Frontend (`container.frontend`)
- **Technology**: Angular, built with npm
- **Root Path**: `frontend`
- **Component Count**: 404 (presentation 214, application 131, unknown 59)
- **Key Responsibilities**:
  - Provide a rich SPA for end‑users
  - Consume Backend REST services
  - Generate client‑side services (e.g., `action_api‑generated_services`)

### JS API (`container.js_api`)
- **Technology**: Node.js, built with npm
- **Root Path**: `frontend\src\jsApi`
- **Component Count**: 52 (presentation 41, application 11)
- **Key Responsibilities**:
  - Offer lightweight HTTP endpoints for internal tooling
  - Bridge between Frontend assets and Backend services

### E2E‑XNP (`container.e2e_xnp`)
- **Technology**: Playwright, built with npm
- **Root Path**: `e2e‑xnp`
- **Purpose**: Automated UI and API regression testing; validates contracts between Frontend and Backend.

### Import‑Schema (`container.import_schema`)
- **Technology**: Java/Gradle library
- **Root Path**: `import‑schema`
- **Purpose**: Provides shared schema definitions used by Backend during data import processes.

## 2.4 Container Interactions

### 2.4.1 Synchronous Communication (REST/HTTPS)
| Source Container | Target Container | Protocol / Method | Data Format | Typical Use |
|------------------|------------------|--------------------|------------|------------|
| Frontend | Backend | HTTP GET/POST (REST) | JSON | UI actions, data retrieval, CRUD operations |
| JS API | Backend | HTTP GET/POST (REST) | JSON | Internal tooling, batch jobs |
| Backend | Import‑Schema | Library call (Java) | In‑process objects | Schema import during data processing |

### 2.4.2 Asynchronous / Test Interactions
| Source Container | Target Container | Interaction Type | Description |
|------------------|------------------|------------------|-------------|
| E2E‑XNP | Frontend | UI Automation | Playwright drives the Angular SPA to verify UI flows |
| E2E‑XNP | Backend | API Tests | Direct REST calls to verify contract compliance |

## 2.5 Technology Stack Summary
| Layer | Technology | Version (example) |
|-------|------------|-------------------|
| Presentation | Angular | 15.x |
| Application (Backend) | Spring Boot | 3.1.x |
| Application (JS API) | Node.js | 18.x |
| Test Automation | Playwright | 1.35.x |
| Build / Dependency | Gradle / npm | – |

## 2.6 Container Diagram
The visual representation of the containers and their relationships is provided in the Draw.io file.

![Container Diagram](c4/c4-container.drawio)

*Figure: C4 Level‑2 Container Diagram showing the five containers and their primary communication paths.*

---
*Document generated on 2026‑02‑09 by the Senior Software Architect – C4 Model Expert.*