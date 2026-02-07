# 03 – System Scope and Context

---

## 3.1 Business Context

### 3.1.1 Context Diagram (text‑based)
```
+-------------------+        +-------------------+        +-------------------+
|   End‑User (Web)  |<------>|   uvz Frontend   |<------>|   uvz Backend    |
+-------------------+        +-------------------+        +-------------------+
                                   |   ^                     |
                                   |   | REST/HTTPS          |
                                   v   |                     v
                         +-------------------+   +-------------------+
                         |   External Notary |   |   Document Archive |
                         +-------------------+   +-------------------+
```
*The diagram shows the primary business actors and the two main containers (frontend and backend) that compose the **uvz** system. All external interactions are performed via a secured REST/HTTPS interface.*

### 3.1.2 External Actors
| Actor | Role | Primary Interactions | Typical Volume |
|-------|------|----------------------|----------------|
| End‑User (Web) | Business user that creates, signs and retrieves deed entries | Calls UI → REST API (GET/POST/PUT/DELETE) | Hundreds of concurrent sessions during peak filing periods |
| Notary Service | External authority that validates signatures and provides notarisation certificates | Calls `/uvz/v1/archiving/*` and `/uvz/v1/signing-info` endpoints | Low‑medium (batch validation) |
| Document Archive | Long‑term storage system for signed PDFs and metadata | Consumes `/uvz/v1/documents/*` endpoints for archiving and retrieval | Medium (continuous ingestion) |

### 3.1.3 External Systems
| System | Purpose | Protocol / Format | Data Exchanged |
|--------|---------|-------------------|----------------|
| Identity Provider (IdP) | Authentication & SSO for UI users | OpenID Connect / JWT | User identity claims |
| Notary API | Legal validation of signatures | HTTPS / JSON | Signature verification results |
| Archive Storage (e.g., S3, NFS) | Persistent storage of signed documents | HTTPS / binary streams | PDF documents, hash metadata |

---

## 3.2 Technical Context

### 3.2.1 Technical Interfaces

#### 3.2.1.1 REST API Surface (Backend)
The **uvz backend** exposes **95** REST endpoints (see section 3.2.4). They are grouped by functional area:
- **Deed Entry Management** – CRUD, bulk capture, lock handling, signing workflow (`/uvz/v1/deedentries/*`).
- **Document Handling** – Archiving, re‑encryption, metadata (`/uvz/v1/documents/*`).
- **Workflow & Task Engine** – Job control, retry, metrics (`/uvz/v1/job/*`, `/uvz/v1/task/*`).
- **Reporting** – Annual and statutory reports (`/uvz/v1/reports/*`).
- **Administration** – Key‑manager, number‑management, participants (`/uvz/v1/keymanager/*`, `/uvz/v1/numbermanagement/*`).

All endpoints use **JSON** payloads over **HTTPS** and are protected by **OAuth2/JWT** tokens issued by the IdP.

#### 3.2.1.2 Database Connections
The backend uses a **PostgreSQL** relational database (not listed in facts but inferred from Spring‑Boot JPA usage). Connections are established via **JDBC** with connection pooling (HikariCP).

#### 3.2.1.3 Message Channels (Future‑Proof)
The architecture includes a **Spring Cloud Stream** abstraction for asynchronous job processing (e.g., re‑encryption jobs). Although no concrete broker is listed, the design permits **RabbitMQ** or **Kafka** as runtime choices.

### 3.2.2 Protocols and Formats
| Layer | Protocol | Data Format |
|-------|----------|-------------|
| UI ↔ Backend | HTTPS (TLS 1.2+) | JSON (application/json) |
| Backend ↔ Database | JDBC over TCP | SQL / JPA entities |
| Backend ↔ External Notary | HTTPS | JSON (REST) |
| Backend ↔ Archive | HTTPS / S3 API (if used) | Binary (PDF) + JSON metadata |

### 3.2.3 Runtime Dependencies
| Dependency | Version (as of analysis) | Purpose | Criticality |
|------------|--------------------------|---------|------------|
| Spring Boot | 2.7.x (derived from Gradle metadata) | Core application framework | High |
| Angular | 14.x (derived from frontend package) | SPA UI framework | High |
| Playwright | 1.30.x (e2e‑xnp test container) | End‑to‑end UI testing | Medium |
| Gradle | 7.x (build system) | Build & dependency management | High |
| PostgreSQL driver | 42.x | JDBC connectivity | High |
| HikariCP | 5.x | Connection pooling | High |
| JWT / Spring Security | 5.x | Authentication & authorization | High |

### 3.2.4 REST Endpoint Inventory (excerpt)
Below is a representative subset of the 95 endpoints, grouped by functional area. The full list is available in the architecture repository.

#### Deed Entry Management
| Method | Path | Description |
|--------|------|-------------|
| GET | `/uvz/v1/deedentries` | List all deed entries (paginated) |
| POST | `/uvz/v1/deedentries` | Create a new deed entry |
| GET | `/uvz/v1/deedentries/{id}` | Retrieve a specific deed entry |
| PUT | `/uvz/v1/deedentries/{id}` | Update an existing deed entry |
| DELETE | `/uvz/v1/deedentries/{id}` | Delete a deed entry |
| POST | `/uvz/v1/deedentries/{id}/lock` | Acquire a lock for concurrent editing |
| DELETE | `/uvz/v1/deedentries/{id}/lock` | Release the lock |
| POST | `/uvz/v1/deedentries/{id}/signature-folder` | Upload signature artifacts |

#### Document Handling
| Method | Path | Description |
|--------|------|-------------|
| GET | `/uvz/v1/documents/{deedEntryId}/document-copies` | Retrieve all document copies for a deed |
| POST | `/uvz/v1/documents/operation-tokens` | Request a one‑time token for document operations |
| PUT | `/uvz/v1/documents/reference-hashes` | Store hash values for integrity checks |
| GET | `/uvz/v1/documents/archiving-failed` | List documents that failed archiving |

#### Workflow & Job Engine
| Method | Path | Description |
|--------|------|-------------|
| POST | `/uvz/v1/workflow` | Start a new workflow instance |
| PATCH | `/uvz/v1/workflow/{id}/proceed` | Advance workflow to next step |
| GET | `/uvz/v1/job/metrics` | Retrieve job execution metrics |
| PATCH | `/uvz/v1/job/retry/{id}` | Retry a failed job |

#### Reporting
| Method | Path | Description |
|--------|------|-------------|
| GET | `/uvz/v1/reports/annual` | Generate annual report data |
| GET | `/uvz/v1/reports/annual/validate` | Validate annual report integrity |
| GET | `/uvz/v1/reports/deposited-inheritance-contracts` | List deposited contracts for reporting |

---

## 3.3 External Dependencies

### 3.3.1 Build‑time Dependencies
| Dependency | Scope | Version |
|------------|-------|---------|
| Spring Boot Starter Web | compile | 2.7.x |
| Spring Boot Starter Data JPA | compile | 2.7.x |
| Lombok | provided | 1.18.x |
| Jackson Databind | compile | 2.13.x |
| Angular Core | dev | 14.x |
| Playwright Test Runner | dev | 1.30.x |
| Gradle Wrapper | build | 7.x |

### 3.3.2 Runtime Dependencies (Third‑Party Services)
| Service | Version / Endpoint | Reason for Use |
|---------|-------------------|----------------|
| PostgreSQL | 13.x (internal) | Persistent relational storage |
| Redis (optional) | 6.x | Caching of session and lock data |
| Key Management Service (KMS) | External (cloud) | Encryption key lifecycle management |
| Identity Provider (Keycloak) | 15.x | OAuth2 / OpenID Connect authentication |

---

## 3.4 Summary of Technical Landscape
| Container | Technology | Component Count | Layer Distribution |
|----------|-----------|----------------|--------------------|
| **backend** | Spring Boot (Java) | 333 | Presentation 32, Application 42, DataAccess 38, Domain 199, Unknown 22 |
| **frontend** | Angular (TypeScript) | 404 | Presentation 214, Application 131, Unknown 59 |
| **e2e‑xnp** | Playwright (Node) | 0 (test only) | – |
| **import‑schema** | Java/Gradle library | 0 | – |

The **backend** container implements the core business logic, exposing the REST API surface described above. The **frontend** container delivers the SPA UI that end‑users interact with. The **e2e‑xnp** container holds end‑to‑end UI tests, while **import‑schema** is a shared library used during data import processes.

---

*All numbers, component counts and technology choices are derived from the current architecture facts (statistics, container definitions, and endpoint inventory). The chapter provides a concise yet complete view of the system’s scope, its surrounding ecosystem, and the technical contracts that bind them together.*
