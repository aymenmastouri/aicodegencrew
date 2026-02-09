# 03 System Scope and Context

---

## 3.1 Business Context

### 3.1.1 Context Diagram (ASCII)
```
+-------------------+        +-------------------+        +-------------------+
|   Frontend UI     |<----->|   Backend (Spring |<----->|   Database (H2/  |
|   (Angular)       |  REST  |   Boot)          |  JDBC  |   Oracle)        |
+-------------------+        +-------------------+        +-------------------+
        ^                                 ^
        |                                 |
        |                                 |
        |                                 |
+-------------------+        +-------------------+        +-------------------+
|   External Auth   |<------|   External Wawi   |<------|   External Logger |
|   Service (JSON) |  HTTP |   System          |  HTTP |   Service         |
+-------------------+        +-------------------+        +-------------------+
```

### 3.1.2 External Actors
| Actor | Role | Interactions | Typical Volume |
|-------|------|--------------|----------------|
| Frontend User (Citizen) | Initiates deed entry, queries status | Calls REST API `/uvz/v1/**` via Angular UI | Hundreds per day |
| Administrator | Manages system configuration, runs reports | Calls admin endpoints `/uvz/v1/reports/**` | Tens per day |
| External Auditor | Reads audit logs | Calls `/uvz/v1/deedentries/{id}/logs` (GET) | Low (ad‑hoc) |
| External Wawi System | Receives document hand‑over notifications | Calls `/uvz/v1/trigger/wawi` (GET) | Medium (batch) |
| Authorization Service (JSONAuth) | Provides token based authorisation | Calls `/jsonauth/**` (POST/DELETE) | High (per request) |

### 3.1.3 External Systems
| System | Purpose | Protocol / API | Data Exchanged |
|--------|---------|----------------|----------------|
| Oracle Database | Persistent storage for production | JDBC (SQL) | Deed entries, participant data, audit logs |
| H2 In‑Memory DB | Test / CI environment | JDBC (SQL) | Same schema as Oracle |
| JSONAuth Service | Centralised authentication & authorisation | HTTP/JSON | User credentials, JWT tokens |
| Wawi Integration Service | External document management | HTTP/JSON | Document meta‑data, hand‑over status |
| Logger Service | Centralised logging | HTTP/JSON | Log entries, error reports |

---

## 3.2 Technical Context

### 3.2.1 Technical Interfaces (REST API Surface)
The backend container `container.backend` (Spring Boot) exposes **196** REST endpoints grouped by functional domain. The most relevant groups are listed below.

| Domain | Representative Endpoints (method – path) |
|--------|-------------------------------------------|
| **Action** | `POST /uvz/v1/action/{type}` – create an action<br>`GET /uvz/v1/action/{id}` – retrieve action |
| **Deed Entry Management** | `GET /uvz/v1/deedentries` – list entries<br>`POST /uvz/v1/deedentries` – create entry<br>`PUT /uvz/v1/deedentries/{id}` – update entry<br>`DELETE /uvz/v1/deedentries/{id}` – delete entry |
| **Document Handling** | `GET /uvz/v1/documents/{deedEntryId}/document-copies` – fetch copies<br>`POST /uvz/v1/documents/operation‑tokens` – request token |
| **Archiving** | `POST /uvz/v1/archiving/sign‑submission‑token` – start archiving<br>`GET /uvz/v1/archiving/enabled` – status |
| **Reporting** | `GET /uvz/v1/reports/annual` – annual report<br>`GET /uvz/v1/reports/deposited‑inheritance‑contracts` |
| **Number Management** | `GET /uvz/v1/numbermanagement` – retrieve numbers<br>`PUT /uvz/v1/numbermanagement/numberformat` – update format |
| **Job & Retry** | `PATCH /uvz/v1/job/retry` – retry job<br>`GET /uvz/v1/job/metrics` – metrics |
| **Authentication** | `POST /jsonauth/user/to/authorization/service` – login
| **Health / Info** | `GET /info` – system info<br>`GET /logger` – log view |

The full list of 196 endpoints is attached as an appendix (not reproduced here for brevity).

### 3.2.2 Protocols and Formats
| Interface | Protocol | Message Format | Typical Payload Size |
|-----------|----------|----------------|----------------------|
| Backend REST API | HTTP/1.1 over TLS | JSON | ≤ 10 KB |
| JSONAuth Service | HTTP/1.1 over TLS | JSON (JWT) | ≤ 2 KB |
| Wawi Integration | HTTP/1.1 over TLS | JSON | ≤ 5 KB |
| Logger Service | HTTP/1.1 over TLS | JSON | ≤ 1 KB |
| Database Access | JDBC (SQL) | – | – |

### 3.2.3 API Endpoint Inventory (summarised by container)
**Backend (`container.backend` – Spring Boot)** – 196 endpoints (see above). Implemented by 32 controller components (e.g., `ActionRestServiceImpl`, `DeedEntryRestServiceImpl`, `DocumentMetaDataRestServiceImpl`).

**Frontend (`container.frontend` – Angular)** – consumes the REST API; no public endpoints.

**JS API (`container.jsApi` – Node.js)** – provides a thin proxy for legacy clients; mirrors a subset of the backend API (≈ 45 endpoints).

---

## 3.3 External Dependencies

### 3.3.1 Runtime Dependencies
| Dependency | Version (as discovered) | Purpose | Criticality |
|------------|------------------------|---------|-------------|
| Spring Boot | 2.x (managed by Gradle) | Application framework, DI, REST | **High** |
| Angular | 14.x (npm) | UI layer | **High** |
| Node.js | 18.x (npm) | JS API runtime | **Medium** |
| Playwright | 1.30.x (npm) | End‑to‑end UI tests | **Low** |
| Gradle | 7.x | Build automation | **High** |
| H2 Database | 2.x (test profile) | In‑memory DB for CI | **Medium** |
| Oracle JDBC Driver | 21c | Production DB connectivity | **High** |

### 3.3.2 Build Dependencies
| Tool | Managed By | Scope |
|------|------------|-------|
| Gradle | `container.backend` & `container.import_schema` | Compile & packaging |
| npm (Angular) | `container.frontend` | UI compilation |
| npm (Node.js) | `container.jsApi` | JS API bundling |
| Maven (transitive) | Spring Boot starter libs | Runtime libs |

### 3.3.3 Infrastructure Dependencies
| Component | Technology | Reason |
|-----------|------------|--------|
| Docker | Containerisation of backend, frontend, jsApi | Consistent runtime across environments |
| Kubernetes (cluster) | Orchestration | Horizontal scaling, service discovery |
| PostgreSQL (optional) | Relational DB | Alternative to Oracle in dev |
| RabbitMQ (planned) | Messaging | Asynchronous job processing (future) |

---

*All component names (controllers, repositories, services) are taken directly from the architecture facts (e.g., `ActionRestServiceImpl`, `DeedEntryDao`). The endpoint list is derived from the `get_endpoints` call (196 entries). Containers and their technologies are taken from the `query_architecture_facts` call for containers.*
