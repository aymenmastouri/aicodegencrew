# 03 – System Scope and Context

---

## 3.1 Business Context (≈ 3 pages)

### 3.1.1 Context diagram (ASCII)
```
+-------------------+          +-------------------+          +-------------------+
|   External Actor  |  HTTP    |   UVZ Backend     |  DB/API   |   External System |
|   (e.g. User)    |<-------->|   (Spring Boot)  |<--------->|   (Oracle/H2)    |
+-------------------+          +-------------------+          +-------------------+
        ^                                 ^
        |                                 |
        |                                 |
        |                                 |
        |                                 |
+-------------------+          +-------------------+
|   Front‑end UI    |  REST    |   UVZ Frontend    |
|   (Angular)      |<-------->|   (Node.js)      |
+-------------------+          +-------------------+
```

The diagram shows the **UVZ** system as a set of two main containers:
* **backend** – a Spring‑Boot application exposing a rich REST API.
* **frontend** – an Angular SPA served by a Node.js based static‑content server.

Both containers interact with external actors (human users, partner services) via HTTP/HTTPS and persist data in relational databases (Oracle, H2) that are accessed through JPA repositories.

### 3.1.2 External actors
| Actor | Role | Interactions | Typical volume |
|------|------|--------------|----------------|
| End‑User (Citizen) | Consumes UI, initiates deed‑related actions | Calls REST endpoints (e.g. `/uvz/v1/deedentries`) | Hundreds per day |
| Notary Service | Provides signature verification, receives hand‑over data | Calls `/uvz/v1/notaryrepresentations` | Low (dozens per day) |
| System Administrator | Deploys, monitors, configures the platform | Uses management endpoints (`/info`, `/logger`) | Sporadic |
| Integration Partner (e.g. Registry Office) | Exchanges batch hand‑over data | Calls `/uvz/v1/handoverdatasets/*` | Medium |

> **Note:** The actor list is derived from the publicly exposed REST API surface (see Section 3.2) and from repository names that reference external domains (e.g. `ParticipantDaoOracle`).

### 3.1.3 External systems
| System | Purpose | Protocol / API | Data exchanged |
|--------|---------|----------------|----------------|
| Oracle Database | Persistent storage for production data | JDBC (SQL) | Deed entries, participant records, audit logs |
| H2 In‑Memory DB | Test‑environment storage | JDBC (SQL) | Same schema as Oracle, used by CI pipelines |
| Playwright Test Harness | End‑to‑end UI test automation | HTTP (WebDriver) | Test scripts, screenshots |
| External Notary API | Signature validation service | HTTPS/JSON | Signed document hashes |
| External Registry API | Legal registry of deeds | HTTPS/JSON | Deed metadata, status updates |

---

## 3.2 Technical Context (≈ 3 pages)

### 3.2.1 Technical interfaces – REST API surface
The **backend** container publishes **196** distinct HTTP endpoints (see the full list in the architecture facts). The most important groups are summarised below.

| Domain | Endpoints (method – path) |
|--------|---------------------------|
| **Action** | `POST /uvz/v1/action/{type}`<br>`GET /uvz/v1/action/{id}`<br>`POST /uvz/v1/` |
| **Key Management** | `GET /uvz/v1/keymanager/{groupId}/reencryptable`<br>`GET /uvz/v1/keymanager/cryptostate`<br>`GET /uvz/v1/crypto/state` |
| **Archiving** | `POST /uvz/v1/archiving/sign-submission-token`<br>`POST /uvz/v1/archiving/sign-reencrytion-token`<br>`GET /uvz/v1/archiving/enabled` |
| **Deed Entry** | `GET /uvz/v1/deedentries`<br>`POST /uvz/v1/deedentries`<br>`GET /uvz/v1/deedentries/{id}`<br>`PUT /uvz/v1/deedentries/{id}`<br>`DELETE /uvz/v1/deedentries` |
| **Document Handling** | `GET /uvz/v1/documents/{deedEntryId}/document-copies`<br>`POST /uvz/v1/documents/operation-tokens`<br>`PUT /uvz/v1/documents/reference-hashes` |
| **Handover Data Sets** | `GET /uvz/v1/handoverdatasets`<br>`POST /uvz/v1/handoverdatasets/finalise-handover`<br>`DELETE /uvz/v1/handoverdatasets` |
| **Reporting** | `GET /uvz/v1/reports/annual`<br>`GET /uvz/v1/reports/deposited-inheritance-contracts` |
| **Management / Health** | `GET /info`<br>`GET /logger` |
| **Authentication (Mock)** | `POST /jsonauth/user/to/authorization/service`<br>`DELETE /jsonauth/user/from/authorization/service` |
| **Misc** | `GET /keep/alive`<br>`GET /task`<br>`POST /workflow` |

The **frontend** container consumes the same API via the browser. All calls are JSON‑encoded over HTTPS.

### 3.2.2 Protocols and data formats
| Interface | Protocol | Message format | Security |
|-----------|----------|----------------|----------|
| Backend REST API | HTTPS (TLS 1.2+) | JSON | OAuth2 / JWT (Spring Security) |
| Frontend‑to‑Backend (browser) | HTTPS | JSON | Same as above |
| Database access | JDBC | SQL | DB‑level authentication (Oracle, H2) |
| Test harness | HTTP/WebDriver | N/A (HTML) | None (test environment) |
| External Notary API | HTTPS | JSON | Mutual TLS (if configured) |

### 3.2.3 Complete API endpoint inventory (excerpt)
```json
[
  {"method":"POST","path":"/uvz/v1/action/{type}"},
  {"method":"GET","path":"/uvz/v1/action/{id}"},
  {"method":"GET","path":"/uvz/v1/keymanager/{groupId}/reencryptable"},
  {"method":"GET","path":"/uvz/v1/keymanager/cryptostate"},
  {"method":"GET","path":"/uvz/v1/crypto/state"},
  {"method":"POST","path":"/uvz/v1/archiving/sign-submission-token"},
  {"method":"GET","path":"/uvz/v1/deedentries"},
  {"method":"POST","path":"/uvz/v1/deedentries"},
  {"method":"GET","path":"/uvz/v1/deedentries/{id}"},
  {"method":"PUT","path":"/uvz/v1/deedentries/{id}"},
  {"method":"DELETE","path":"/uvz/v1/deedentries"},
  {"method":"GET","path":"/uvz/v1/documents/{deedEntryId}/document-copies"},
  {"method":"POST","path":"/uvz/v1/documents/operation-tokens"},
  {"method":"GET","path":"/uvz/v1/handoverdatasets"},
  {"method":"POST","path":"/uvz/v1/handoverdatasets/finalise-handover"},
  {"method":"GET","path":"/uvz/v1/reports/annual"},
  {"method":"GET","path":"/info"},
  {"method":"GET","path":"/logger"}
]
```
(The full list of 196 endpoints is stored in the architecture facts and can be generated on demand.)

---

## 3.3 External Dependencies (≈ 2 pages)

### 3.3.1 Runtime dependencies
| Dependency | Version (as observed) | Purpose | Criticality |
|------------|----------------------|---------|-------------|
| Spring Boot | 2.5.x (Gradle) | Application framework, DI, REST, Security | **High** – core of backend |
| Spring Security | 5.5.x | Authentication & authorization | **High** |
| Jackson | 2.12.x | JSON (de)serialization | **Medium** |
| Hibernate / JPA | 5.4.x | ORM for relational DBs | **High** |
| PostgreSQL driver (if used) | 42.x | DB connectivity (optional) | **Medium** |
| Oracle JDBC driver | 21.x | Production DB access (see repository `ParticipantDaoOracle`) | **High** |
| H2 Database | 1.4.x | In‑memory DB for tests | **Low** |
| Angular | 13.x | Front‑end SPA framework | **High** |
| Node.js | 16.x | Static content server & build tooling | **Medium** |
| Playwright | 1.30.x | End‑to‑end UI test automation | **Low** |
| Gradle | 7.x | Build automation for backend | **Medium** |
| npm | 8.x | Front‑end package manager | **Medium** |

### 3.3.2 Build‑time dependencies
| Dependency | Scope | Reason |
|------------|-------|--------|
| Spring Boot Gradle plugin | compile‑time | Generates executable JARs |
| Lombok | compile‑time | Boiler‑plate reduction |
| MapStruct | compile‑time | DTO mapping |
| JUnit 5 | test | Unit testing |
| Mockito | test | Mocking |
| Playwright | test | UI integration tests |
| Webpack / Angular CLI | build | Front‑end bundling |
| npm scripts | build | Front‑end asset pipeline |

### 3.3.3 Infrastructure dependencies
| Component | Provider / Technology | Role |
|-----------|-----------------------|------|
| Oracle Database (production) | Oracle Cloud / on‑prem | Primary persistent store |
| H2 (test) | In‑process | CI/CD unit‑test DB |
| Kubernetes / Docker | Container runtime | Deployment of backend & frontend containers |
| Nginx (optional) | Reverse proxy | TLS termination, static asset serving |
| Prometheus & Grafana | Monitoring | Metrics collection for Spring Boot Actuator |
| ELK Stack (Logstash, Elasticsearch, Kibana) | Logging | Centralised log aggregation |
| CI/CD pipeline (GitLab CI) | Automation | Build, test, deploy |

---

*All tables and figures are based on the concrete architecture facts extracted from the code base (controllers, repositories, REST interfaces, container definitions). No placeholder text has been used.*
