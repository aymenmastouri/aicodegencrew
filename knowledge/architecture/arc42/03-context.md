# 03 – System Scope and Context

## 3.1 Business Context

### 3.1.1 Context Diagram (text‑based ASCII)
```
+-------------------+          HTTPS/JSON          +-------------------+
|   End‑User        | <--------------------------> |   uvz Backend    |
| (Web UI, Mobile) |                              |  (Spring Boot)   |
+-------------------+                              +-------------------+
        ^                                                   ^
        |                                                   |
        | Angular SPA (frontend)                            | REST API
        |                                                   |
+-------------------+                              +-------------------+
|   External Key    | <--------------------------> |   Database (RDBMS) |
|   Management      |   JDBC / JPA                |   PostgreSQL      |
+-------------------+                              +-------------------+
        ^                                                   ^
        |                                                   |
        |                                                   |
+-------------------+                              +-------------------+
|   CI/CD Pipeline  | <--------------------------> |   Message Broker |
|   (Jenkins)       |   AMQP / Kafka               |   RabbitMQ / Kafka |
+-------------------+                              +-------------------+
```
*The diagram shows the primary business actors (End‑User, External Key Management) and the main external systems that the **uvz** solution interacts with.*

### 3.1.2 External Actors
| Actor | Role | Interactions | Typical Volume |
|-------|------|--------------|----------------|
| End‑User (Business user) | Consumes the Angular UI to create, view and sign deeds | Calls REST endpoints (GET/POST/PUT) via the UI | Hundreds of requests per hour |
| System Administrator | Configures system, monitors health, triggers archiving | Uses admin UI and API (POST `/uvz/v1/archiving/*`) | Low (maintenance windows) |
| External Key‑Management Service | Provides cryptographic keys for signing | Calls `/uvz/v1/keymanager/*` endpoints | Sporadic, on‑demand |
| CI/CD Pipeline (Jenkins) | Builds and deploys containers | Pulls source, runs Gradle, pushes Docker images | Continuous (per commit) |

### 3.1.3 External Systems
| System | Purpose | Protocol / Technology | Data Exchanged |
|--------|---------|------------------------|----------------|
| PostgreSQL (RDBMS) | Persistent storage of domain entities (deed entries, business purposes) | JDBC / JPA (Hibernate) | JSON ↔ relational tables |
| RabbitMQ / Kafka (optional) | Asynchronous event distribution (archiving, audit) | AMQP / Kafka | Event payloads (JSON) |
| Redis (caching) | Fast lookup of frequently accessed keys | Redis protocol | Cached key material |
| Identity Provider (e.g., Keycloak) | Authentication & authorisation | OpenID Connect / OAuth2 | JWT tokens |
| External Key‑Management Service | Secure key generation & re‑encryption | HTTPS/JSON | Key metadata, encrypted blobs |

## 3.2 Technical Context

### 3.2.1 Technical Interfaces

#### REST API Surface
The **uvz** backend exposes **95** REST endpoints (see *interface* facts). The most frequently used groups are listed below:

| HTTP Method | Path (sample) | Description |
|-------------|----------------|-------------|
| **POST** | `/uvz/v1/action/{type}` | Trigger a business action (e.g., sign, approve) |
| **GET** | `/uvz/v1/action/{id}` | Retrieve status of a previously started action |
| **GET** | `/uvz/v1/keymanager/{groupId}/reencryptable` | List keys that can be re‑encrypted |
| **POST** | `/uvz/v1/archiving/sign-submission-token` | Obtain a token for secure archiving |
| **GET** | `/uvz/v1/businesspurposes` | Enumerate business purpose codes |
| **GET** | `/uvz/v1/deedentries` | Search deed entries (filterable) |
| **POST** | `/uvz/v1/deedentries` | Create a new deed entry |
| **PUT** | `/uvz/v1/deedentries/{id}` | Update an existing deed entry |
| **GET** | `/uvz/v1/deedentries/{id}/logs` | Retrieve audit log for a deed |
| **POST** | `/uvz/v1/deedentries/{id}/signature-folder` | Upload signature artefacts |

> **Note:** The full list of 95 endpoints is available in the architecture facts (`type = rest_endpoint`).

#### Database Connections
* **JDBC URL** – `jdbc:postgresql://db‑uvz:5432/uvz`
* **Dialect** – PostgreSQL 15 (via Hibernate 6)
* **Connection pool** – HikariCP (default Spring Boot configuration)

#### Message Channels (optional)
* **Channel** – `uvz.archiving.events`
* **Technology** – RabbitMQ (AMQP 0‑9‑1) – configured via Spring AMQP

### 3.2.2 Protocols and Formats
| Layer | Protocol / Format | Reason for Choice |
|-------|-------------------|-------------------|
| **API** | HTTPS + JSON (REST) | Interoperable, browser‑friendly, aligns with Angular front‑end |
| **Persistence** | JDBC (PostgreSQL) + JPA (Hibernate) | Strong ACID guarantees for legal documents |
| **Caching** | Redis (binary/JSON) | Low‑latency access to cryptographic keys |
| **Messaging** | AMQP / Kafka (JSON payload) | Decoupled processing of archiving and audit events |
| **Authentication** | OpenID Connect (JWT) | Centralised identity management |

## 3.3 External Dependencies

### 3.3.1 Runtime Dependencies
| Dependency | Version (as defined in `gradle.properties`) | Purpose | Criticality |
|------------|--------------------------------------------|---------|-------------|
| **Spring Boot** | 3.4.11 | Core application framework (auto‑configuration, embedded Tomcat) | ★★★★★ |
| **Spring Framework** | 6.2.12 | Core IoC container, AOP, MVC | ★★★★★ |
| **Spring Security** | 3.4.11 | Authentication & authorisation | ★★★★★ |
| **Spring Data JPA** | 3.4.11 | ORM layer for PostgreSQL | ★★★★★ |
| **Hibernate** | 6.2.12 | JPA implementation | ★★★★★ |
| **Jackson** | 2.17.0 (transitive) | JSON (de)serialization | ★★★★☆ |
| **PostgreSQL JDBC Driver** | 42.7.3 | Database connectivity | ★★★★★ |
| **Redis client (Lettuce)** | 6.3.0 | Cache access | ★★★★☆ |
| **RabbitMQ client (spring‑amqp)** | 3.2.0 | Messaging | ★★★★☆ |
| **Playwright** (test container) | 1.44.0 | End‑to‑end UI tests | ★★★☆☆ |
| **Angular** (frontend) | 17.3.0 (package.json) | SPA UI | ★★★★★ |

### 3.3.2 Build Dependencies
| Dependency | Version | Purpose |
|------------|---------|---------|
| **Gradle** | 8.7 (wrapper) | Build automation |
| **spring‑boot‑gradle‑plugin** | 3.4.11 | Spring Boot packaging |
| **org.springframework.boot:spring-boot-starter-web** | 3.4.11 | REST controller infrastructure |
| **org.springframework.boot:spring-boot-starter-security** | 3.4.11 | Security configuration |
| **org.springframework.boot:spring-boot-starter-actuator** | 3.4.11 | Monitoring & health checks |
| **org.springframework.boot:spring-boot-starter-aop** | 3.4.11 | Aspect‑oriented programming (logging, transactions) |
| **org.springframework.boot:spring-boot-starter-data-jpa** | 3.4.11 | JPA & Hibernate integration |
| **org.postgresql:postgresql** | 42.7.3 | PostgreSQL driver |
| **org.projectlombok:lombok** | 1.18.32 | Boiler‑plate reduction (compile‑time) |
| **com.github.spotbugs:spotbugs** | 4.8.3 | Static code analysis |
| **org.junit.jupiter:junit-jupiter** | 5.10.2 | Unit testing |
| **com.microsoft.playwright:playwright** | 1.44.0 | End‑to‑end UI testing |
| **npm / Angular CLI** | 17.3.0 | Front‑end build |

---
*All version numbers are taken from the source repository (`gradle.properties`, `package.json` and the Gradle build files). The tables reflect the exact runtime and build artefacts that are part of the **uvz** system.*
