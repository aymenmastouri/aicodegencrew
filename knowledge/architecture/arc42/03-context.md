# 03 - System Scope and Context

## 3.1 Business Context

### 3.1.1 Context Diagram (text‑based)
```
+-------------------+        +-------------------+        +-------------------+
|   End‑User UI     |<----->|   UVZ Backend     |<----->|   External Notary |
|   (Angular)       |        |   (Spring Boot)  |        |   Service (REST) |
+-------------------+        +-------------------+        +-------------------+
        ^                               ^
        |                               |
        |                               |
+-------------------+        +-------------------+
|   Reporting UI   |<------|   Reporting API   |
|   (Angular)      |        |   (Spring Boot)   |
+-------------------+        +-------------------+
```

### 3.1.2 External Actors
| Actor | Role | Primary Interactions | Typical Volume |
|-------|------|----------------------|----------------|
| End‑User (Citizen) | Initiates deed entry, queries status | Calls UI → REST API (GET/POST) | Hundreds per day |
| Notary Officer | Validates and signs deeds | Consumes `/uvz/v1/archiving/*` endpoints | Dozens per shift |
| System Administrator | Manages configuration, monitors health | Calls `/uvz/v1/job/metrics`, `/uvz/v1/reports/*` | Low |
| External Audit Service | Retrieves audit logs | Calls `/uvz/v1/deedentries/{id}/logs` | Periodic |
| Third‑Party Document Store | Stores signed PDFs | Calls `/uvz/v1/documents/*` (PUT/GET) | High |

### 3.1.3 External Systems
| System | Purpose | Protocol / Format | Data Exchanged |
|--------|---------|--------------------|----------------|
| PostgreSQL Database | Persistent storage of entities, deeds, logs | JDBC / SQL | Deed entities, audit logs |
| Redis Cache | Session & short‑term data | Redis protocol (binary) | Authentication tokens, temporary locks |
| Kafka Message Bus | Asynchronous processing of archiving & re‑encryption jobs | Kafka (JSON) | Job payloads, status events |
| Identity Provider (Keycloak) | User authentication & authorisation | OpenID Connect / JWT | User claims, access tokens |
| External Notary API | Legal signing service | REST JSON over HTTPS | Signed artefacts, verification results |

## 3.2 Technical Context

### 3.2.1 Technical Interfaces
- **REST API Surface** – 196 endpoints (128 GET, 30 POST, 18 PUT, 14 DELETE, 6 PATCH, 1 PATCH for job retry). Full list is stored in the architecture facts.
- **Database Connections** – Spring Boot Data JPA to PostgreSQL (JDBC URL `jdbc:postgresql://…`).
- **Message Channels** – Kafka topics `uvz-archiving`, `uvz-reencryption` for background processing.
- **Cache Interface** – Redis client (`lettuce`) for lock handling and session caching.
- **External HTTP Clients** – RestTemplate/WebClient for Keycloak, Notary Service, and Document Store.

### 3.2.2 Protocols and Formats
| Interface | Protocol | Data Format |
|-----------|----------|-------------|
| Public REST API | HTTPS (TLS 1.2+) | JSON payloads (application/json) |
| Database | JDBC (PostgreSQL driver) | SQL / JPA entities |
| Messaging | Kafka (PLAINTEXT/TLS) | JSON messages |
| Cache | Redis (binary protocol) | Serialized Java objects |
| Authentication | OpenID Connect (OIDC) | JWT tokens |

## 3.3 External Dependencies

### 3.3.1 Runtime Dependencies
| Dependency | Version (as defined in container) | Purpose | Criticality |
|------------|-----------------------------------|---------|-------------|
| Spring Boot | 2.5.x (managed by Gradle) | Core application framework | High |
| Angular | 12.x (npm) | Front‑end UI | High |
| Node.js | 14.x (npm) | JS API layer (`jsApi` container) | Medium |
| Playwright | 1.20.x (npm) | End‑to‑end test suite (`e2e‑xnp`) | Low |
| PostgreSQL | 13.x (runtime) | Relational data store | High |
| Redis | 6.x | In‑memory cache & lock service | Medium |
| Kafka | 2.8.x | Event‑driven background jobs | Medium |

### 3.3.2 Build Dependencies
| Dependency | Version | Purpose |
|------------|---------|---------|
| Gradle | 7.3 | Build automation for backend & import‑schema library |
| npm | 7.x | Package manager for Angular, Node.js API and Playwright tests |
| Java | 11 | Language runtime for Spring Boot services |
| TypeScript | 4.x | Source language for `jsApi` container |

## 3.4 Quantitative Overview (derived from architecture facts)
- **Containers**: 5 (backend, frontend, jsApi, e2e‑xnp, import‑schema)
- **Components**: 951 total
  - Presentation layer: 287 (pipes, modules, controllers, directives, components)
  - Application layer: 184 services
  - Domain layer: 360 entities
  - Data‑access layer: 38 repositories
  - Infrastructure: 1 configuration
  - Unknown/technical: 81 (adapters, guards, rest_interfaces, interceptors, resolvers, scheduler)
- **Interfaces**: 226 (196 REST endpoints, 29 UI routes, 1 route guard)
- **Relations**: 190 (uses 131, manages 24, imports 15, references 20)

The above figures are directly extracted from the architecture facts and form the basis for the subsequent building‑block and runtime views.
