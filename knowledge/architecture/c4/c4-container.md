# C4 Level 2: Container Diagram

## 2.1 Overview
The **uvz** system is realised as a set of five deployable containers.  Each container groups a coherent set of Spring‑Boot services, Angular UI, Node.js API or test artefacts and runs on its own runtime.  The container diagram shows the high‑level building blocks, the technology choices and the communication paths between them.

## 2.2 Container Inventory
| Container ID | Name | Type | Technology | Primary Responsibility |
|--------------|------|------|------------|------------------------|
| `container.backend` | Backend | application | Spring Boot (Java/Gradle) | Core business logic, REST API, security, data access |
| `container.frontend` | Frontend | application | Angular (npm) | User‑facing web UI |
| `container.js_api` | jsApi | application | Node.js (npm) | Lightweight helper API for static assets and client‑side utilities |
| `container.e2e_xnp` | e2e‑xnp | test | Playwright (npm) | End‑to‑end UI test suite |
| `container.import_schema` | import‑schema | library | Java/Gradle | Schema import library used at build time |

## 2.3 Component Inventory (selected key components)
### 2.3.1 Controllers (backend)
| Component | Package | Description |
|-----------|---------|-------------|
| ActionRestServiceImpl |  | Exposes `/uvz/v1/action/**` endpoints |
| IndexHTMLResourceService |  | Serves the SPA entry point |
| StaticContentController |  | Delivers static resources |
| JsonAuthorizationRestServiceImpl |  | Handles JSON‑based auth token exchange |
| DeedEntryRestServiceImpl |  | CRUD operations for deed entries |
| ReportRestServiceImpl |  | Generates and streams reports |
| JobRestServiceImpl |  | Job management and monitoring |
| ... (total 32 controllers) |

### 2.3.2 Services (backend)
| Component | Package | Description |
|-----------|---------|-------------|
| ActionServiceImpl |  | Business logic for actions |
| KeyManagerServiceImpl |  | Encryption key lifecycle |
| WaWiServiceImpl |  | Integration with external WaWi system |
| ArchiveManagerServiceImpl |  | Archiving workflow orchestration |
| DeedEntryServiceImpl |  | Core deed entry processing |
| DocumentMetaDataServiceImpl |  | Document metadata handling |
| NumberManagementServiceImpl |  | Number generation & validation |
| ReportServiceImpl |  | Report data aggregation |
| JobServiceImpl |  | Background job execution |
| ... (total 184 services) |

## 2.4 REST Endpoint Summary (backend)
The backend container exposes **196** HTTP endpoints (GET, POST, PUT, DELETE, PATCH).  A representative subset is shown below:
| HTTP Method | Path | Primary Controller |
|-------------|------|--------------------|
| POST | `/uvz/v1/action/{type}` | ActionRestServiceImpl |
| GET  | `/uvz/v1/action/{id}` | ActionRestServiceImpl |
| GET  | `/uvz/v1/deedentries` | DeedEntryRestServiceImpl |
| POST | `/uvz/v1/deedentries` | DeedEntryRestServiceImpl |
| GET  | `/uvz/v1/deedentries/{id}` | DeedEntryRestServiceImpl |
| PUT  | `/uvz/v1/deedentries/{id}` | DeedEntryRestServiceImpl |
| DELETE| `/uvz/v1/deedentries/{id}` | DeedEntryRestServiceImpl |
| GET  | `/uvz/v1/reports/annual` | ReportRestServiceImpl |
| PATCH| `/uvz/v1/job/retry` | JobRestServiceImpl |
| GET  | `/uvz/v1/participants` | ParticipantController |
| ... |

## 2.5 Container Interactions
| Source Container | Target Container | Protocol | Description |
|------------------|------------------|----------|-------------|
| Frontend (Angular) | Backend (Spring Boot) | HTTPS/REST | UI calls the public `/uvz/v1/**` API |
| jsApi (Node.js) | Backend (Spring Boot) | HTTP | Helper API for static asset versioning |
| Backend | Import‑schema (library) | Java classpath | Uses schema import utilities at start‑up |
| e2e‑xnp (Playwright) | Frontend | HTTP (browser) | Executes end‑to‑end UI tests against the deployed UI |
| Backend | Database (external, not modelled) | JDBC | Persists entities (not shown as a container) |

## 2.6 Technology Stack Summary
| Layer | Technology | Version (example) |
|-------|------------|-------------------|
| Presentation | Angular | 15.x |
| Presentation (helper) | Node.js | 18.x |
| Application | Spring Boot | 3.1.x |
| Build / Package | Gradle | 8.x |
| Test | Playwright | 1.40.x |
| Data Access | JPA / Hibernate | 6.x |

## 2.7 Container Diagram
The visual diagram is stored as a Draw.io file:

```
📁 c4/c4-container.drawio
```
It follows the SEAGuide C4 visual conventions (blue boxes for internal containers, gray for external systems, cylinders for databases, person icons for users, dashed lines for boundaries).

---
*Document generated automatically from architecture facts.*