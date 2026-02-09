# C4 Level 2 – Container Diagram

## 2.1 Overview
The **uvz** system is composed of five deployable containers.  It provides a web UI (Angular), a Node.js based JavaScript API, a Spring‑Boot backend, a Java library used for schema import and an automated end‑to‑end test suite (Playwright).  All external actors interact through HTTP/HTTPS.

## 2.2 Container Inventory
| Container ID | Name | Technology | Type | Primary Responsibility |
|--------------|------|------------|------|------------------------|
| `container.frontend` | Frontend | Angular | Application | Browser UI, consumes backend REST APIs |
| `container.js_api` | jsApi | Node.js | Application | Lightweight JSON API used by internal services |
| `container.backend` | Backend | Spring Boot (Java/Gradle) | Application | Core business logic, REST services, security, data access |
| `container.import_schema` | Import‑Schema | Java/Gradle | Library | Schema import utilities used by backend |
| `container.e2e_xnp` | e2e‑xnp | Playwright | Test Suite | End‑to‑end UI tests |

## 2.3 Component Summary per Container
### Backend (`container.backend`)
- **Controllers**: 32 (e.g., `ActionRestServiceImpl`, `DeedEntryRestServiceImpl`, `ReportRestServiceImpl`)
- **Services**: 184 (e.g., `ActionServiceImpl`, `KeyManagerServiceImpl`, `ReportServiceImpl`)
- **Repositories**: 38 (e.g., `ActionDao`, `DeedEntryDao`, `SignatureInfoDao`)
- **Other**: Exception handlers, security configuration, OpenAPI config.

### Frontend (`container.frontend`)
- Angular modules, components and routing – 404 UI artefacts (derived from component count).

### jsApi (`container.js_api`)
- Small set of Express‑style endpoints exposing JSON services to the UI.

### Import‑Schema (`container.import_schema`)
- Utility classes, no public REST endpoints.

### e2e‑xnp (`container.e2e_xnp`)
- Playwright test scripts, no runtime components.

## 2.4 REST Endpoint Inventory (Backend)
The backend exposes **196** HTTP endpoints.  A representative subset is listed below:
| HTTP Method | Path | Purpose |
|-------------|------|---------|
| POST | `/uvz/v1/action/{type}` | Create a new action record |
| GET | `/uvz/v1/action/{id}` | Retrieve action details |
| POST | `/uvz/v1/deedentries` | Create a deed entry |
| GET | `/uvz/v1/deedentries/{id}` | Read a deed entry |
| PUT | `/uvz/v1/deedentries/{id}` | Update a deed entry |
| DELETE | `/uvz/v1/deedentries/{id}` | Delete a deed entry |
| GET | `/uvz/v1/businesspurposes` | List business purposes |
| GET | `/uvz/v1/deedtypes` | List deed types |
| POST | `/uvz/v1/archiving/sign-submission-token` | Obtain token for document archiving |
| GET | `/uvz/v1/participants` | Retrieve participant catalogue |
| PATCH | `/uvz/v1/job/retry/{id}` | Retry a background job |
| … | … | … |

## 2.5 Container Interaction Matrix
| Source | Target | Protocol | Data Format | Typical Use |
|--------|--------|----------|------------|------------|
| User (Browser) | `container.frontend` | HTTPS | HTML/JSON | UI interaction |
| `container.frontend` | `container.backend` | HTTPS | REST/JSON | Business API calls |
| `container.js_api` | `container.backend` | HTTPS | REST/JSON | Internal service calls |
| `container.backend` | `container.import_schema` | Java library call | In‑process objects | Schema import during startup |
| `container.e2e_xnp` | `container.frontend` | HTTP | Browser automation | End‑to‑end UI tests |

## 2.6 Technology Stack Summary
| Layer | Technology | Version (example) |
|-------|------------|-------------------|
| Presentation (Web) | Angular | 15.x |
| Presentation (JS API) | Node.js + Express | 18.x |
| Application (Backend) | Spring Boot | 3.1.x |
| Build / Dependency | Gradle | 8.x |
| Test Automation | Playwright | 1.40.x |
| Database (not shown) | PostgreSQL / H2 (embedded) | 15.x |

## 2.7 Diagram
The official Draw.io diagram is stored as **c4/c4-container.drawio** and visualises the containers, the external user actor and the primary communication paths.

---
*Document generated automatically from architecture facts (2026‑02‑09).*