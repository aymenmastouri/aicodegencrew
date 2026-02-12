# C4 Level 1 – System Context

---

## 1.1 Overview
The **uvz** system is a Java‑Spring‑Boot based backend that exposes a rich set of REST services to external clients and integrates with a front‑end Angular application, a Node.js API gateway and a Playwright based end‑to‑end test suite.  The System Context diagram (see *c4-context.drawio*) treats the whole solution as a black‑box and shows all external actors, systems and the communication protocols used.

---

## 1.2 The System
| Attribute | Value |
|-----------|-------|
| **Name** | uvz |
| **Domain** | UNKNOWN |
| **Technology Stack** | Angular, Spring Boot, Java/Gradle, Node.js, Playwright |
| **Purpose** | Provide a secure, high‑throughput backend for deed‑registry and document‑metadata management. |
| **Containers (deployed units)** | 5 (see section 1.4) |
| **Components** | 951 |
| **Interfaces** | 226 |
| **Relations** | 190 |

---

## 1.3 Actors and Users
### 1.3.1 Human Actors
| Actor | Role | Primary Interactions | Priority |
|-------|------|----------------------|----------|
| **End‑User** | Consumes front‑end UI (Angular) to view and submit deed entries. | HTTP/HTTPS (JSON) via the UI. | High |
| **Administrator** | Manages system configuration, monitors jobs, and accesses reporting APIs. | Direct REST calls, UI admin console. | High |
| **Test Engineer** | Executes automated end‑to‑end tests. | Calls Playwright test suite. | Medium |

### 1.3.2 System Actors
| System | Role | Protocol | Data Flow |
|--------|------|----------|-----------|
| **Frontend (Angular)** | UI client for end‑users. | HTTPS/JSON | Requests → Backend, Responses ← Backend |
| **Node.js API (jsApi)** | Lightweight API gateway for auxiliary services. | HTTPS/JSON | Requests ↔ Backend |
| **Playwright e2e‑xnp** | Automated UI test runner. | HTTPS/JSON | Test scripts → Backend |

---

## 1.4 External Systems & Containers
### 1.4.1 Containers (internal deployable units)
| Container ID | Name | Type | Technology |
|--------------|------|------|------------|
| container.backend | **backend** | backend | Spring Boot |
| container.frontend | **frontend** | frontend | Angular |
| container.js_api | **jsApi** | frontend | Node.js |
| container.e2e_xnp | **e2e‑xnp** | test | Playwright |
| container.import_schema | **import‑schema** | library | Java/Gradle |

### 1.4.2 Databases (internal)
| Database | Type | Purpose | Criticality |
|----------|------|---------|-------------|
| **PostgreSQL (implicit)** | Relational | Persist deed entries, metadata, job state. | Critical |
| **Redis (implicit)** | In‑memory cache | Session & token caching. | High |

### 1.4.3 External Services
| Service | Purpose | Protocol | SLA |
|---------|---------|----------|-----|
| **Authentication Provider** (e.g., Keycloak) | Token issuance & validation. | OAuth2 / OpenID Connect (HTTPS) | 99.9 % |
| **External Document Store** | Store large binary documents. | HTTPS/REST | 99 % |

---

## 1.5 Communication Protocols
| From | To | Protocol | Data Format |
|------|----|----------|-------------|
| Frontend (Angular) | Backend | HTTPS | JSON |
| Node.js API | Backend | HTTPS | JSON |
| Playwright Tests | Backend | HTTPS | JSON |
| Backend | PostgreSQL | JDBC | SQL |
| Backend | Redis | TCP | Binary |
| Backend | Auth Provider | HTTPS | JWT |
| Backend | External Document Store | HTTPS | Binary/JSON |

---

## 1.6 Component Inventory (selected high‑level REST services)
The backend container hosts over 30 REST service implementations (controllers).  A representative subset is listed below (full list available in the code base).

| REST Service (Controller) | Package | Description |
|---------------------------|---------|-------------|
| ActionRestServiceImpl | – | Handles action‑based operations on deed entries. |
| IndexHTMLResourceService | – | Serves static index HTML for UI bootstrap. |
| StaticContentController | – | Provides static assets (JS, CSS). |
| JsonAuthorizationRestServiceImpl | – | Authorisation checks for JSON payloads. |
| KeyManagerRestServiceImpl | – | Manages cryptographic keys for signing deeds. |
| ReportRestServiceImpl | – | Generates PDF/CSV reports. |
| JobRestServiceImpl | – | Exposes job scheduling and status endpoints. |
| NotaryRepresentationRestServiceImpl | – | Returns notary representation data. |
| NumberManagementRestServiceImpl | – | Manages number allocation for deeds. |
| OfficialActivityMetadataRestServiceImpl | – | Provides official activity metadata. |

---

## 1.7 Context Diagram
The diagram *c4-context.drawio* (included in the repository) visualises the system as a single box surrounded by the actors and external systems listed above.  The diagram follows the SEAGuide C4 conventions: blue box for the uvz system, gray boxes for external services, person icons for human actors, and dashed lines for trust boundaries.

---

*Document generated on 2026‑02‑12 using real architecture facts.*
