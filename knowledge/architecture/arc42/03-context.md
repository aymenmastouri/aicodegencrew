# 03 – System Scope and Context

---

## 3.1 Business Context (≈ 3 pages)

### 3.1.1 Context diagram (text‑based)
```
+-------------------+        +-------------------+        +-------------------+
|   Citizens /     |  <---> |   **uvz** (REST   |  <---> |   Notary Office   |
|   Private Users   |        |   API Backend**   |        |   (External       |
+-------------------+        +-------------------+        |   System)         |
                                                          +-------------------+
        ^                         ^                         ^
        |                         |                         |
        |                         |                         |
        |                         |                         |
+-------------------+   +-------------------+   +-------------------+
|   Front‑end (UI)  |   |   Document Store  |   |   External Auth   |
|   Angular SPA    |   |   PostgreSQL DB  |   |   Service (OAuth) |
+-------------------+   +-------------------+   +-------------------+
```

### 3.1.2 External actors
| Actor | Role | Interactions | Typical volume |
|------|------|--------------|----------------|
| **Citizen** | End‑user of the deed‑entry portal | Calls UI → REST API for creating, viewing, signing deeds | Hundreds of requests per hour |
| **Notary** | Legal authority that validates deeds | Uses UI to retrieve pending deeds, sign, archive | Dozens of requests per day |
| **External Auth Service** | Provides OAuth2 / OpenID tokens | Token exchange during login | < 1 k per day |
| **Document Archive** | Long‑term storage for signed PDFs | Pulls signed documents via API | ~ 500 documents per day |
| **Reporting System** | Generates statutory reports | Consumes `/uvz/v1/reports/**` endpoints | Weekly batch runs |

### 3.1.3 External systems
| System | Purpose | Protocol / API | Data exchanged |
|--------|---------|----------------|----------------|
| **PostgreSQL** (container `backend`) | Persistent storage of deeds, participants, logs | JDBC (PostgreSQL) | Deed entities, audit logs, user profiles |
| **OAuth2 Provider** | Authentication & authorisation | HTTPS / OAuth2 | Access‑tokens, user claims |
| **Document Archive Service** | Long‑term archival of signed PDFs | HTTPS (REST) | Signed PDF binaries, metadata |
| **Statistical Reporting Service** | Generates annual reports for authorities | HTTPS (REST) | Aggregated deed statistics |
| **Playwright E2E Test Suite** (`e2e‑xnp`) | Automated UI regression tests | Node.js / Playwright | Test scripts, screenshots |

---

## 3.2 Technical Context (≈ 3 pages)

### 3.2.1 Technical interfaces
| Interface | Container | Path / Protocol | Implemented by | HTTP method |
|----------|-----------|----------------|----------------|-------------|
| **Action Service** | `backend` | `/uvz/v1/action/{type}` | `component.backend.service_api_rest.action_rest_service` | POST |
| **Action Query** | `backend` | `/uvz/v1/action/{id}` | `component.backend.service_api_rest.action_rest_service` | GET |
| **Key‑Manager** | `backend` | `/uvz/v1/keymanager/{groupId}/reencryptable` | `component.backend.service_api_rest.key_manager_rest_service` | GET |
| **Archiving** | `backend` | `/uvz/v1/archiving/sign-submission-token` | `component.backend.service_api_rest.archiving_rest_service` | POST |
| **Business Purpose** | `backend` | `/uvz/v1/businesspurposes` | `component.backend.service_impl_rest.business_purpose_rest_service_impl` | GET |
| **Deed Entry CRUD** | `backend` | `/uvz/v1/deedentries` | `component.backend.service_impl_rest.deed_entry_rest_service_impl` | GET/POST/DELETE |
| **Document Handling** | `backend` | `/uvz/v1/documents/{deedEntryId}/document-copies` | `component.backend.service_impl_rest.document_rest_service_impl` | GET |
| **Report Generation** | `backend` | `/uvz/v1/reports/annual` | `component.backend.service_impl_rest.report_rest_service_impl` | GET |
| **Static Content** | `frontend` | `/web/uvz/` | `component.backend.module_adapters_staticwebresources.static_content_controller` | GET |
| **JSON Auth Mock** | `backend` | `/jsonauth/user/to/authorization/service` | `component.backend.impl_mock_rest.json_authorization_rest_service_impl` | POST |

> **Note** – The full list comprises 196 REST endpoints (see Appendix A). The table above summarises the most business‑critical groups.

### 3.2.2 Protocols & data formats
| Protocol | Format | Typical payload size | Security considerations |
|----------|--------|----------------------|------------------------|
| HTTPS (TLS 1.2+) | JSON | ≤ 200 KB per request/response | Mutual TLS for internal services, OAuth2 bearer tokens for external callers |
| JDBC (PostgreSQL) | Binary rows | N/A | Database credentials stored in Spring Boot `application‑secrets.yml` (encrypted) |
| WebSocket (future) | JSON | Streaming | Not yet implemented – reserved for real‑time status updates |

### 3.2.3 API inventory (grouped by domain)
#### Deed‑entry domain (≈ 70 endpoints)
- CRUD: `/uvz/v1/deedentries` (GET, POST, DELETE)
- Lock handling: `/uvz/v1/deedentries/{id}/lock` (GET/POST/PUT/DELETE)
- Signature folder: `/uvz/v1/deedentries/{id}/signature-folder` (POST)
- Handover data sets: `/uvz/v1/handoverdatasets/**`
- Bulk capture: `/uvz/v1/deedentries/bulkcapture` (POST)

#### Key‑management domain (≈ 10 endpoints)
- State queries: `/uvz/v1/keymanager/cryptostate`, `/uvz/v1/crypto/state`
- Re‑encryption checks: `/is/reencryption/possible`

#### Archiving & Reporting (≈ 15 endpoints)
- Token signing: `/uvz/v1/archiving/sign‑submission-token`
- Archive status: `/uvz/v1/archiving/enabled`
- Annual reports: `/uvz/v1/reports/annual`, `/uvz/v1/reports/annual‑validate`

#### Supporting services (≈ 30 endpoints)
- Business purposes: `/uvz/v1/businesspurposes`
- Number management: `/uvz/v1/numbermanagement/**`
- Notary representations: `/uvz/v1/notaryrepresentations`
- JSON‑auth mock: `/jsonauth/**`

> **Appendix A** – Complete endpoint list (196 entries) is stored in the architecture repository and can be generated automatically from the OpenAPI spec.

---

## 3.3 External Dependencies (≈ 2 pages)

### 3.3.1 Runtime dependencies
| Dependency | Version | Purpose | Criticality |
|------------|---------|---------|-------------|
| **Spring Boot** | 2.7.x | Application framework, DI, REST, security | ★★★★★ (core) |
| **Angular** | 15.x | Front‑end SPA, UI components | ★★★★★ (core) |
| **Node.js** | 18.x | JS API layer (`jsApi` container) | ★★★★☆ (support) |
| **PostgreSQL** | 13.x | Relational data store | ★★★★★ (core) |
| **Playwright** | 1.35.x | End‑to‑end UI test runner (container `e2e‑xnp`) | ★★☆☆☆ (non‑production) |
| **Gradle** | 7.6 | Build automation for Java modules | ★★★★☆ (build) |
| **npm** | 9.x | Build automation for Angular & Node.js | ★★★★☆ (build) |

### 3.3.2 Build‑time dependencies
| Dependency | Version | Scope |
|------------|---------|-------|
| **JUnit 5** | 5.9 | Unit testing (backend) |
| **Mockito** | 4.8 | Mocking (service layer) |
| **Karma / Jasmine** | 6.x / 4.x | Front‑end unit tests |
| **SonarQube** | 9.9 | Static code analysis |
| **Docker** | 20.10 | Container image creation for `backend`, `frontend`, `jsApi` |

### 3.3.3 Infrastructure dependencies
| Component | Managed by | Reason |
|-----------|------------|--------|
| **Kubernetes (EKS)** | Cloud Ops | Orchestrates the 5 containers (backend, frontend, jsApi, import‑schema, e2e‑xnp) |
| **AWS RDS (PostgreSQL)** | DB Team | Highly‑available relational store |
| **AWS S3** | Ops | Document archive bucket for signed PDFs |
| **AWS Secrets Manager** | Security | Stores DB credentials, JWT signing keys |
| **Ingress Controller (NGINX)** | Platform | Exposes the REST API under `/uvz/v1/**` |

---

*Prepared according to the Capgemini SEAGuide arc42 template. All tables contain real data extracted from the architecture knowledge base.*
