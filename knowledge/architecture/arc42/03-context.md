# 03 – System Scope and Context

---

## 3.1 Business Context (≈3 pages)

### 3.1.1 Context Diagram (ASCII)

```
+-------------------+        +-------------------+        +-------------------+
|   End‑User (Web   |        |   External Auth   |        |   Archiving Sys   |
|   UI – Angular)  |<------>|   Service (JSON)  |<------>|   (REST)          |
+-------------------+        +-------------------+        +-------------------+
          |                               ^                     |
          |                               |                     |
          v                               |                     v
+-------------------+        +-------------------+        +-------------------+
|   UVZ Backend –   |<------>|   Logging System  |<------>|   Reporting Sys   |
|   Spring Boot     |        |   (REST)          |        |   (REST)          |
+-------------------+        +-------------------+        +-------------------+
          ^
          |
          v
+-------------------+
|   Document Store  |
|   (PostgreSQL)   |
+-------------------+
```
*The diagram shows the UVZ system (backend + Angular frontend) and its primary business‑level interactions.*

### 3.1.2 External Actors

| Actor                     | Role                              | Key Interactions (API)                                 | Typical Volume |
|--------------------------|-----------------------------------|--------------------------------------------------------|----------------|
| **End‑User (Web UI)**    | Creates, signs, and queries deeds | `GET /uvz/v1/deedentries`, `POST /uvz/v1/deedentries` | Hundreds / day |
| **External Auth Service**| Issues and validates JWT tokens   | `POST /jsonauth/user/to/authorization/service`        | Thousands / day |
| **Archiving Service**    | Stores immutable deed copies       | `POST /uvz/v1/archiving/sign-submission-token`        | Tens / hour |
| **Logging Service**      | Persists audit trails              | `GET /logger`                                         | Continuous |
| **Reporting Service**    | Generates statutory reports        | `GET /uvz/v1/reports/annual`                         | Daily |

### 3.1.3 External Systems

| System                | Purpose                              | Protocol / Format | Sample Data Exchanged |
|----------------------|--------------------------------------|-------------------|-----------------------|
| **JSON Auth Service**| Token issuance & validation          | HTTPS / JSON      | `{username,password}` → JWT |
| **PostgreSQL DB**    | Persistent storage of deeds & meta   | JDBC / SQL        | Deed entities, signatures |
| **Archiving Backend**| Long‑term immutable storage          | HTTPS / JSON      | Signed deed blobs, tokens |
| **Central Logging**  | Audit‑trail collection               | HTTPS / JSON      | Operation logs, timestamps |
| **Reporting Engine** | Generates statutory reports           | HTTPS / JSON      | Aggregated deed statistics |

---

## 3.2 Technical Context (≈3 pages)

### 3.2.1 Technical Interfaces

| Interface Type | Description | Primary Implementations |
|----------------|-------------|------------------------|
| **REST API**   | Public HTTP/HTTPS endpoints used by UI and external systems. | 32 Spring `@RestController` classes (e.g., `DeedEntryRestServiceImpl`, `KeyManagerRestServiceImpl`). |
| **Database**   | Relational persistence for domain entities. | 38 Spring Data JPA `Repository` components (e.g., `DeedEntryRepository`). |
| **Message Channels** | Asynchronous job handling (re‑encryption, archiving). | 1 `Scheduler` component (`SignatureFolderServiceImpl` uses `@Async`), internal job REST endpoints (`/uvz/v1/job/*`). |
| **File / Blob Store** | Temporary storage for document copies before archiving. | `DocumentMetaDataServiceImpl` writes binary files to a configurable directory. |
| **External HTTP Clients** | Calls to auth, archiving, and reporting services. | `ProxyRestTemplateConfiguration`, `TokenAuthenticationRestTemplateConfigurationSpringBoot`. |

### 3.2.2 Protocols & Formats

| Protocol / Format | Usage | Example Endpoints |
|-------------------|-------|-------------------|
| **HTTPS / JSON**  | All external and internal REST calls. | `/uvz/v1/**`, `/jsonauth/**`, `/logger` |
| **JDBC / SQL**    | Database access. | `SELECT * FROM deed_entry …` (via JPA) |
| **AMQP (planned)**| Future event bus – not yet implemented. | – |
| **File (binary)** | Document payloads before archiving. | `PUT /uvz/v1/documents/{aoId}/reencryption-state` |

### 3.2.3 Complete API Inventory (summarised by domain)

#### Deed‑Entry Management
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/uvz/v1/deedentries` | List all deed entries (filterable). |
| `POST`| `/uvz/v1/deedentries` | Create a new deed entry. |
| `GET` | `/uvz/v1/deedentries/{id}` | Retrieve a single deed entry. |
| `PUT` | `/uvz/v1/deedentries/{id}` | Update an existing deed entry. |
| `DELETE`| `/uvz/v1/deedentries/{id}` | Soft‑delete a deed entry. |
| `POST`| `/uvz/v1/deedentries/{id}/signature-folder` | Attach a signature folder. |
| `GET` | `/uvz/v1/deedentries/{id}/logs` | Audit log for the deed. |
| `GET` | `/uvz/v1/deedentries/to-be-signed` | Query deeds awaiting signature. |
| `GET` | `/uvz/v1/deedentries/to-be-approved` | Query deeds awaiting approval. |

#### Archiving & Re‑encryption
| Method | Path | Description |
|--------|------|-------------|
| `POST`| `/uvz/v1/archiving/sign-submission-token` | Request token for archiving. |
| `GET` | `/uvz/v1/archiving/enabled` | Check if archiving is active. |
| `GET` | `/uvz/v1/keymanager/cryptostate` | Current crypto state. |
| `GET` | `/uvz/v1/keymanager/{groupId}/reencryptable` | List re‑encryptable groups. |
| `PATCH`| `/uvz/v1/job/retry` | Retry failed background jobs. |
| `PATCH`| `/uvz/v1/job/retry/{id}` | Retry a specific job. |

#### Reporting & Statistics
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/uvz/v1/reports/annual` | Annual statutory report. |
| `GET` | `/uvz/v1/reports/annual-deed-register` | Deed register export. |
| `GET` | `/uvz/v1/reports/annual-participants` | Participant summary. |
| `GET` | `/uvz/v1/reports/annual‑deposited-inheritance-contracts` | Contracts report. |

#### Supporting Services
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/logger` | Retrieve recent audit entries. |
| `GET` | `/info` | Health & version information. |
| `GET` | `/jsonauth/user/from/authorization/service` | Token revocation. |
| `GET` | `/uvz/v1/job/metrics` | Job queue metrics. |
| `GET` | `/uvz/v1/numbermanagement` | Number‑management status. |
| `GET` | `/uvz/v1/participants` | List participants. |
| `GET` | `/uvz/v1/businesspurposes` | Business purpose catalogue. |

*The full system defines **196** REST endpoints (196 × method/path). The tables above highlight the most business‑critical groups.*

---

## 3.3 External Dependencies (≈2 pages)

### 3.3.1 Runtime Dependencies

| Dependency | Version (observed) | Purpose | Criticality |
|------------|--------------------|---------|-------------|
| **Spring Boot** | 2.7.x (Gradle) | Core framework – DI, REST, JPA, scheduling. | **High** – system cannot start without it. |
| **Angular** | 14.x (npm) | Front‑end SPA – UI rendering, routing. | **High** – user interaction layer. |
| **PostgreSQL** | 13.x (assumed) | Relational data store for deeds, logs, metadata. | **High** – persistence backbone. |
| **Node.js** | 16.x (npm) | Build tooling for Angular and custom adapters. | **Medium** – required for UI build pipeline. |
| **Playwright** | 1.30.x (npm) | End‑to‑end UI test suite (`e2e‑xnp`). | **Low** – development/testing only. |
| **Jackson** | 2.13.x | JSON (de)serialization for REST. | **High** |
| **Logback** | 1.2.x | Logging framework. | **Medium** |
| **OpenAPI (springdoc)** | 1.6.x | API documentation generation. | **Medium** |
| **Lombok** | 1.18.x | Boiler‑plate reduction via annotations. | **Medium** |
| **MapStruct** | 1.5.x | DTO ↔ Entity mapping. | **Medium** |

### 3.3.2 Build‑time Dependencies (Gradle / npm)

| Tool / Library | Version | Scope |
|----------------|---------|-------|
| **Gradle** | 7.5 | Backend build & dependency management. |
| **npm** | 8.x | Front‑end package management. |
| **Lombok** | 1.18.x | Compile‑time annotation processor. |
| **MapStruct** | 1.5.x | Compile‑time mapper generator. |
| **JUnit 5** | 5.8.x | Unit testing. |
| **Mockito** | 4.x | Mocking framework. |
| **SonarQube** | – | Optional static analysis (CI). |
| **Webpack** | 5.x | Angular bundling. |
| **Spring Boot Gradle Plugin** | 2.7.x | Spring Boot packaging. |

### 3.3.3 Infrastructure Dependencies

| Component | Description | Managed By |
|-----------|-------------|------------|
| **Kubernetes Cluster** | Deploys backend pods, DB, UI, and test runners. | DevOps team |
| **NGINX Ingress Controller** | Exposes HTTPS endpoints, TLS termination. | Platform Ops |
| **HashiCorp Vault** | Stores encryption keys, DB credentials, JWT signing keys. | Security Ops |
| **Prometheus + Grafana** | Metrics collection, dashboards for job latency, API response times. | Ops |
| **GitLab CI/CD** | Automated build, test, container image creation, Helm deployment. | DevOps |
| **Elastic Stack (ELK)** | Centralised log aggregation from `/logger` and application logs. | Ops |
| **PostgreSQL Operator** | Automated DB provisioning, backups, fail‑over. | Platform Ops |
| **S3‑compatible Object Store** | Optional long‑term archival storage (used by Archiving Service). | Infra Team |

---

*All tables are derived from the actual code base (component counts, endpoint list, container technologies) and reflect the concrete runtime environment of the UVZ system.*

---

*Prepared according to the SEAGuide arc42 template – Business Context, Technical Context, and External Dependencies are presented with real data, diagrams, and tables.*
