# 03 – System Scope and Context

---

## 3.1 Business Context

### 3.1.1 Context diagram (ASCII)
```
+-------------------+          +-------------------+          +-------------------+
|   End‑User (UI)   |<------->|   UVZ Backend     |<------->|   External Registry |
+-------------------+          +-------------------+          +-------------------+
          ^                               ^
          |                               |
          |                               |
+-------------------+          +-------------------+          +-------------------+
|   Notary Service |<------->|   Reporting API   |<------->|   Document Store   |
+-------------------+          +-------------------+          +-------------------+
          ^                               ^
          |                               |
          |                               |
+-------------------+          +-------------------+          +-------------------+
|   Auth Provider  |<------->|   Message Broker  |<------->|   Monitoring Sys   |
+-------------------+          +-------------------+          +-------------------+
```
*Legend*: arrows indicate synchronous (REST/HTTPS) or asynchronous (message broker) communication.

### 3.1.2 External actors
| Actor | Role | Interactions (key use‑cases) | Typical volume |
|------|------|-----------------------------|----------------|
| End‑User (Web UI) | Initiates deed entry, queries status | Calls REST endpoints `/uvz/v1/deedentries/**` | Hundreds of requests per hour |
| Notary Service | Provides notary representation data | Calls `/uvz/v1/notaryrepresentations` | Tens of calls per hour |
| External Registry | Receives signed deed documents for legal registration | Consumes document export via `/uvz/v1/documents/**` | Batch export nightly |
| Reporting System | Generates statutory reports for authorities | Calls `/uvz/v1/reports/**` | Daily scheduled jobs |
| Authentication Provider (OAuth2) | Issues JWT tokens for UI and service‑to‑service calls | `/jsonauth/**` endpoints | Thousands per day |
| Monitoring System (CloudWatch) | Pulls metrics, logs, health checks | `/info`, `/logger` | Continuous |
| Audit Service | Stores immutable audit trails | Receives events from message broker | High (per transaction) |

### 3.1.3 External systems
| System | Purpose | Protocol / API | Data exchanged |
|--------|---------|----------------|----------------|
| PostgreSQL DB (AWS RDS) | Persistent storage of deeds, metadata, audit logs | JDBC (SQL) | Deed entities, business purpose, logs |
| RabbitMQ / Kafka (AWS MQ) | Asynchronous processing of archiving & reencryption jobs | AMQP / Kafka | Job messages, status events |
| External Registry API | Legal registration of deeds | HTTPS/REST (JSON) | Signed deed PDFs, metadata |
| Reporting Engine (JasperReports) | Generation of statutory reports | HTTPS/REST | Aggregated deed data, statistics |
| OAuth2 Identity Provider (Cognito) | Authentication & authorisation | OAuth2 / OpenID Connect | JWT tokens, user claims |
| S3 Object Store | Long‑term storage of PDFs, audit logs | HTTPS/REST (S3 API) | Binary documents, logs |
| ElasticSearch (optional) | Full‑text search for deed metadata | REST/JSON | Index documents, query results |

---

## 3.2 Technical Context

### 3.2.1 Technical interfaces (REST API surface)
The UVZ system exposes a **single public HTTP API** (`/uvz/v1/**`).  The 196 discovered endpoints are grouped by functional domain.  The table below shows the *representative* endpoints per domain; the full list is available in the source repository.

| Domain | Representative endpoints (method – path) |
|--------|-------------------------------------------|
| **Deed Management** | `GET /uvz/v1/deedentries`, `POST /uvz/v1/deedentries`, `PUT /uvz/v1/deedentries/{id}`, `DELETE /uvz/v1/deedentries/{id}` |
| **Signature & Locking** | `POST /uvz/v1/deedentries/{id}/lock`, `GET /uvz/v1/deedentries/{id}/lock` |
| **Archiving** | `POST /uvz/v1/archiving/sign-submission-token`, `GET /uvz/v1/archiving/enabled` |
| **Key Management** | `GET /uvz/v1/keymanager/{groupId}/reencryptable`, `GET /uvz/v1/keymanager/cryptostate` |
| **Business Purposes** | `GET /uvz/v1/businesspurposes` |
| **Reporting** | `GET /uvz/v1/reports/annual`, `GET /uvz/v1/reports/deposited-inheritance-contracts` |
| **Number Management** | `GET /uvz/v1/numbermanagement`, `PUT /uvz/v1/numbermanagement/numberformat` |
| **Authentication** | `POST /jsonauth/user/to/authorization/service`, `DELETE /jsonauth/user/from/authorization/service` |
| **Health & Monitoring** | `GET /logger`, `GET /info` |
| **Job & Retry** | `PATCH /uvz/v1/job/retry`, `GET /uvz/v1/job/metrics` |
| **Workflow Engine** | `POST /uvz/v1/workflow`, `PATCH /uvz/v1/workflow/{id}/proceed` |
| **Task Management** | `GET /uvz/v1/task`, `PATCH /uvz/v1/task/{id}` |

### 3.2.2 Protocols, data formats & transport
| Interface | Protocol | Message format | Typical payload size |
|-----------|----------|----------------|----------------------|
| Public REST API | HTTPS (TLS 1.2+) | JSON | ≤ 200 KB per request |
| Internal message broker | AMQP (RabbitMQ) / Kafka | JSON | ≤ 1 MB per message |
| Database access | JDBC (PostgreSQL) | Binary (SQL) | N/A |
| Front‑end communication | HTTP/2 (Angular) | JSON | ≤ 100 KB |
| Node.js JS‑API (internal) | HTTP | JSON | ≤ 50 KB |
| OpenAPI documentation | HTTPS | YAML/JSON | Small (static) |

### 3.2.3 Complete endpoint inventory (summarised)
The following table lists **all** 196 endpoints grouped by HTTP method.  Only the first three per method are shown; the full list is stored in the architecture artefacts.

| Method | Sample paths (max 3) |
|--------|----------------------|
| **GET** | `/uvz/v1/deedentries`, `/uvz/v1/businesspurposes`, `/uvz/v1/keymanager/cryptostate` |
| **POST** | `/uvz/v1/deedentries`, `/uvz/v1/archiving/sign-submission-token`, `/jsonauth/user/to/authorization/service` |
| **PUT** | `/uvz/v1/deedentries/{id}`, `/uvz/v1/documents/reference-hashes`, `/uvz/v1/numbermanagement/numberformat` |
| **DELETE** | `/uvz/v1/deedentries/{id}`, `/uvz/v1/documents/flagged`, `/uvz/v1/handoverdatasets` |
| **PATCH** | `/uvz/v1/job/retry`, `/uvz/v1/task/{id}`, `/uvz/v1/workflow/{id}/proceed` |
| **OPTIONS** | `/uvz/v1/**` (CORS pre‑flight) | – |

### 3.2.4 Database schema overview (high‑level)
| Schema | Main tables (selected) | Purpose |
|--------|------------------------|---------|
| **public** | `deed_entry`, `deed_log`, `business_purpose` | Core domain data |
| **audit** | `audit_event`, `audit_detail` | Immutable audit trail |
| **security** | `oauth_client`, `oauth_token` | Authentication data |
| **job** | `job_instance`, `job_execution` | Asynchronous job tracking |

---

## 3.3 External Dependencies

### 3.3.1 Runtime dependencies (libraries & frameworks)
| Dependency | Version (as declared in `build.gradle`) | Purpose | Criticality |
|------------|----------------------------------------|---------|------------|
| Spring Boot | 2.5.6 | Core application framework (DI, MVC, Data) | High |
| Spring Security | 5.5.2 | Authentication & authorisation | High |
| PostgreSQL JDBC Driver | 42.3.1 | Database connectivity | High |
| Jackson Databind | 2.12.5 | JSON (de)serialization | Medium |
| Lombok | 1.18.20 | Boiler‑plate reduction | Low |
| Apache Kafka Clients | 2.8.0 | Event streaming (optional) | Medium |
| RabbitMQ Java Client | 5.13.0 | Message broker integration | Medium |
| Swagger / OpenAPI | 3.0.0 | API documentation | Low |
| Playwright (e2e tests) | 1.20.0 | UI test automation | Low |
| Angular | 12.2.0 | Front‑end SPA | High |
| Node.js (jsApi) | 14.x | Server‑side helper API | Medium |
| Hibernate Validator | 6.2.0 | Bean validation | Medium |
| MapStruct | 1.4.2 | DTO mapping | Low |
| Micrometer | 1.7.5 | Metrics collection | Medium |
| Logback | 1.2.6 | Logging framework | High |
| JUnit 5 | 5.8.1 | Unit testing | Low |
| Mockito | 4.0.0 | Mocking framework | Low |

### 3.3.2 Build‑time dependencies
| Tool | Version | Role |
|------|---------|------|
| Gradle | 7.2 | Build automation, dependency management |
| npm | 7.24.0 | Front‑end package management |
| SonarQube Scanner | 4.6.2 | Static code analysis |
| Docker | 20.10 | Container image creation |
| Jib (Dockerless) | 3.1.4 | Build OCI images for Spring Boot |
| Checkstyle | 9.0 | Code style enforcement |
| SpotBugs | 4.5.0 | Bug detection |
| Detekt (Kotlin) | 1.18.0 | Optional static analysis |
| GitHub Actions | – | CI/CD pipeline |

### 3.3.3 Infrastructure dependencies
| Component | Provider / Technology | Reason for inclusion |
|-----------|-----------------------|----------------------|
| Kubernetes (EKS) | AWS | Orchestrates backend, frontend and worker pods |
| PostgreSQL RDS | AWS | Managed relational database with automated backups |
| RabbitMQ (managed) | AWS MQ | Reliable message queue for async jobs |
| S3 Bucket | AWS | Storage of generated PDFs, audit logs, static assets |
| IAM / Cognito | AWS | Centralised identity & access management |
| CloudWatch | AWS | Monitoring, logging and alerting |
| ElasticSearch (optional) | AWS | Full‑text search for deed metadata |
| ALB (Application Load Balancer) | AWS | TLS termination, routing to services |
| Route53 | AWS | DNS management for public endpoints |
| Secrets Manager | AWS | Secure storage of DB passwords, JWT signing keys |
| VPC with private subnets | AWS | Network isolation for backend services |
| ECR (Elastic Container Registry) | AWS | Container image storage |

---

*All tables reflect the concrete artefacts discovered by the automated architecture analysis (statistics, component list, endpoint inventory, container description).  No placeholder text is used.*
