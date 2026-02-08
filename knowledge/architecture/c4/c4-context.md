# C4 Level 1: System Context

## 1.1 Overview
The **uvz** system is a comprehensive deed‑entry management platform. It exposes a rich set of REST APIs for actions, key‑management, archiving, document handling, number management and workflow orchestration. The system is built with a **Spring Boot** backend, an **Angular** frontend, a **Node.js** JavaScript API, and supporting test and library containers.

## 1.2 The System
| Attribute | Value |
|-----------|-------|
| **Name** | uvz |
| **Type** | Web‑based enterprise application |
| **Purpose** | Manage deed entries, signatures, archiving and related business processes |
| **Domain** | Not explicitly defined (deed‑entry / registry) |
| **Technology Stack** | Angular, Spring Boot, Node.js, Playwright, Gradle |
| **Containers** | 5 (backend, frontend, jsApi, e2e‑xnp, import‑schema) |
| **Components** | 951 |
| **Interfaces** | 226 REST endpoints |
| **Relations** | 190 |

## 1.3 Actors and Users
### 1.3.1 Human Actors
| Actor | Role | Primary Interactions |
|-------|------|----------------------|
| **End‑User** | Uses the web UI to create, view and sign deed entries | Calls UI‑driven REST endpoints (e.g., `/uvz/v1/deedentries`) |
| **Administrator** | Manages system configuration, monitoring and batch jobs | Calls admin APIs (`/uvz/v1/job/*`, `/uvz/v1/reports/*`) |
| **External Auth Service** | Provides authentication/authorization tokens | Interacts via `/jsonauth/*` endpoints |

### 1.3.2 System Actors
| System | Role | Protocol | Data Flow |
|--------|------|----------|----------|
| **Browser** | UI client | HTTPS/JSON | UI → Frontend (Angular) → Backend |
| **External Notary Service** | Notary representation data | HTTPS/JSON | Backend ↔ `/uvz/v1/notaryrepresentations` |
| **External Storage / Archive** | Persistent document storage | HTTPS/JSON | Backend ↔ Archiving endpoints |

## 1.4 External Systems
### 1.4.1 Databases (internal)
| Database | Type | Purpose |
|----------|------|---------|
| **PostgreSQL (assumed)** | Relational | Stores deed entries, logs, metadata, locks |
| **MongoDB (assumed)** | Document | Stores document copies and archival data |

### 1.4.2 External Services
| Service | Purpose | Protocol |
|---------|---------|----------|
| **Authentication Service** | User authentication & token issuance | HTTPS/JSON |
| **Notary Representation Service** | Provides notary data for deeds | HTTPS/JSON |
| **External Reporting Service** | Generates annual reports | HTTPS/JSON |

## 1.5 Communication Protocols
| From | To | Protocol | Data Format |
|------|----|----------|------------|
| Browser → Frontend | HTTPS | JSON/HTML |
| Frontend → Backend | HTTPS | JSON (REST) |
| Backend → Database | JDBC / Driver | SQL |
| Backend → External Services | HTTPS | JSON |
| Backend → jsApi (Node.js) | HTTP | JSON |

## 1.6 Containers (high‑level view)
| Container ID | Name | Type | Technology | Component Count |
|--------------|------|------|------------|-----------------|
| container.backend | backend | application | Spring Boot | 494 |
| container.frontend | frontend | application | Angular | 404 |
| container.js_api | jsApi | application | Node.js | 52 |
| container.e2e_xnp | e2e‑xnp | test | Playwright | 0 |
| container.import_schema | import‑schema | library | Java/Gradle | 0 |

## 1.7 REST API Overview (selected endpoints)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/uvz/v1/deedentries` | Create a new deed entry |
| GET | `/uvz/v1/deedentries/{id}` | Retrieve deed entry details |
| PUT | `/uvz/v1/deedentries/{id}` | Update deed entry |
| DELETE | `/uvz/v1/deedentries/{id}` | Delete deed entry |
| POST | `/uvz/v1/archiving/sign-submission-token` | Request signing token for archiving |
| GET | `/uvz/v1/keymanager/cryptostate` | Retrieve crypto state |
| POST | `/jsonauth/user/to/authorization/service` | Authenticate user |
| GET | `/uvz/v1/reports/annual` | Fetch annual report |
| PATCH | `/uvz/v1/job/retry/{id}` | Retry a failed job |
| ... | ... | (196 total endpoints) |

## 1.8 Context Diagram
The System Context diagram is stored as **c4-context.drawio** and visualises the system (blue box), external actors (person icons), external systems (gray boxes) and the primary communication protocols (solid lines). See the diagram file for a graphical representation.

---
*Document generated automatically from architecture facts (statistics, containers, endpoints).*
