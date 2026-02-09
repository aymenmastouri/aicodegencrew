# C4 Level 1 – System Context

## 1.1 Overview
The **UVZ** system is a back‑office platform that manages deed entries, document archiving, key‑management, and reporting for a notary‑related domain. It is exposed as a set of RESTful HTTP APIs and is consumed by internal front‑ends, external client applications and automated test suites.

## 1.2 System Attributes
| Attribute | Value |
|-----------|-------|
| **Name** | UVZ |
| **Domain** | Notary / Deed Management (derived from endpoint semantics) |
| **Purpose** | Provide CRUD operations for deed entries, handle cryptographic key management, generate reports, and coordinate hand‑over data sets. |
| **Technology Stack** | Spring Boot (backend), Angular (frontend), Node.js (jsApi), Playwright (e2e tests), Java/Gradle (import‑schema library) |
| **Deployment Model** | Multi‑container application (5 containers) |
| **Primary Consumers** | Human operators (e.g., notary clerks), external client systems, automated test harnesses |

## 1.3 Actors and Users
### 1.3.1 Human Actors
| Actor | Role | Primary Interactions |
|-------|------|----------------------|
| **Notary Clerk** | Operates the UI to create, edit, and approve deed entries | Uses the Angular frontend, triggers REST calls via the UI |
| **System Administrator** | Manages deployment, monitors jobs, configures key‑management | Calls admin endpoints (`/uvz/v1/job/*`, `/uvz/v1/keymanager/*`) |
| **Auditor** | Reviews logs and reports | Consumes reporting endpoints (`/uvz/v1/reports/*`) |

### 1.3.2 System Actors (External Systems)
| System | Role | Protocol |
|--------|------|----------|
| **Playwright e2e‑xnp** | Automated end‑to‑end test suite | HTTP/HTTPS (REST) |
| **External Client Application** | Integrates UVZ services into other business processes | HTTP/HTTPS (REST) |
| **Legacy Notary System** (hypothetical) | May call key‑management and archiving services | HTTP/HTTPS (REST) |

## 1.4 External Systems & Resources
### 1.4.1 Databases (internal to UVZ)
| Database | Type | Purpose |
|----------|------|---------|
| **PostgreSQL** (inferred) | Relational | Persist deed entries, documents, audit logs |
| **Key‑Store** (inferred) | Secure storage | Store cryptographic keys and re‑encryption state |

### 1.4.2 External Services
| Service | Purpose | Protocol |
|---------|---------|----------|
| **Playwright Test Harness** (`container.e2e_xnp`) | Executes UI‑level integration tests | HTTP/HTTPS |
| **Node.js jsApi** (`container.js_api`) | Provides lightweight API façade for legacy callers | HTTP/HTTPS |

## 1.5 Communication Protocols
| From | To | Protocol | Data Format |
|------|----|----------|------------|
| Human Actor → Frontend (Angular) | Browser | HTTPS | HTML/JSON |
| Frontend → Backend (`container.backend`) | HTTP | HTTPS/REST | JSON |
| Backend → Database | JDBC | TCP | SQL |
| Backend → Key‑Store | Internal API | HTTPS/REST | JSON |
| Backend → External Client | HTTP | HTTPS/REST | JSON |
| Backend ↔ Playwright Test Harness | HTTP | HTTPS/REST | JSON |

## 1.6 Container Landscape (for context awareness)
| Container ID | Name | Type | Technology | Component Count |
|--------------|------|------|------------|-----------------|
| `container.backend` | backend | Application | Spring Boot | 494 |
| `container.frontend` | frontend | Application | Angular | 404 |
| `container.js_api` | jsApi | Application | Node.js | 52 |
| `container.e2e_xnp` | e2e‑xnp | Test | Playwright | 0 |
| `container.import_schema` | import‑schema | Library | Java/Gradle | 0 |

## 1.7 Representative REST Endpoints (excerpt)
| HTTP Method | Path | Description |
|-------------|------|-------------|
| **POST** | `/uvz/v1/action/{type}` | Execute an action of the given type (e.g., create, approve) |
| **GET** | `/uvz/v1/deedentries` | Retrieve list of deed entries |
| **POST** | `/uvz/v1/deedentries` | Create a new deed entry |
| **GET** | `/uvz/v1/keymanager/cryptostate` | Query current cryptographic state |
| **GET** | `/uvz/v1/reports/annual` | Generate annual report |
| **GET** | `/uvz/v1/job/metrics` | Retrieve job execution metrics |
| **POST** | `/uvz/v1/archiving/sign-submission-token` | Obtain token for document archiving |
| **GET** | `/uvz/v1/participants` | List participants involved in a deed |
| **GET** | `/uvz/v1/numbermanagement` | Retrieve number‑management configuration |
| **GET** | `/info` | System health/info endpoint |

> **Note** – The full list contains 196 endpoints; the table above highlights the most frequently used operations.

## 1.8 System Context Diagram
The visual System Context diagram is stored as a Draw.io file:
- **File:** `c4/c4-context.drawio`
- **Diagram Name:** *UVZ System Context*

The diagram follows the SEAGuide C4 conventions:
- Blue boxes – internal containers (`backend`, `frontend`, `jsApi`)
- Gray boxes – external systems (Playwright test harness, external client)
- Person icons – human actors (Notary Clerk, System Administrator, Auditor)
- Dashed lines – trust boundaries (e.g., between UI and backend)

---
*Document generated automatically from architecture facts (951 components, 190 relations, 5 containers) on 2026‑02‑08.*
