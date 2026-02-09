# C4 Level 1: System Context

## 1.1 Overview
The **UVZ** platform is a comprehensive digital service for managing deed entries, document archiving, cryptographic operations and workflow orchestration. At the System Context level the platform is treated as a black‑box that exposes a rich set of REST APIs and a web UI. It is consumed by internal users (administrators, operators) and external client applications.

## 1.2 The System
| Attribute | Value |
|-----------|-------|
| **Name** | UVZ (Unified Virtual Zentrale) |
| **Type** | Enterprise Java/Spring Boot backend with Angular/Node.js front‑ends |
| **Purpose** | Secure handling of deed entries, cryptographic key management, document archiving and workflow execution |
| **Domain** | Unknown (public sector / legal document processing) |
| **Technology Stack** | Spring Boot (Java/Gradle), Angular, Node.js, Playwright (E2E), PostgreSQL (implicit DB) |
| **Containers** | 5 (backend, frontend, jsApi, e2e‑xnp, import‑schema) |
| **Components** | 951 (including 184 services, 32 controllers, 38 repositories, 360 entities) |
| **Interfaces** | 226 REST endpoints |
| **Relations** | 190 (uses, manages, imports, references) |

## 1.3 Actors and Users
### 1.3.1 Human Actors
| Actor | Role | Primary Interactions |
|-------|------|----------------------|
| **End‑User** | Business user that creates, signs and queries deed entries via the web UI | Uses Angular SPA, triggers REST calls (e.g. `GET /uvz/v1/deedentries`, `POST /uvz/v1/deedentries`) |
| **Administrator** | System operator responsible for configuration, monitoring and key‑management | Calls admin APIs (`GET /uvz/v1/keymanager/...`, `POST /uvz/v1/archiving/...`) |
| **External Service Consumer** | Third‑party system that integrates with UVZ for document exchange | Consumes public REST endpoints (`POST /jsonauth/user/to/authorization/service`, `GET /uvz/v1/documents/...`) |

### 1.3.2 System Actors
| System | Role | Protocol | Data Flow |
|--------|------|----------|----------|
| **Frontend Angular SPA** | Presentation layer for end‑users | HTTPS/REST | Calls backend APIs under `/uvz/v1/**` |
| **Node.js jsApi** | Lightweight API gateway for internal micro‑services | HTTPS/REST | Forwards selected calls to backend |
| **Playwright e2e‑xnp** | Automated UI test harness | N/A (internal) | Executes end‑to‑end scenarios against the UI |
| **Import‑Schema Library** | Shared Java library for schema handling | In‑process | Used by backend services |

## 1.4 External Systems
### 1.4.1 Databases (implicit)
| Database | Type | Purpose | Criticality |
|----------|------|---------|------------|
| **Primary Relational DB** (e.g. PostgreSQL) | SQL | Persists deed entries, documents, cryptographic keys, workflow state | High |

### 1.4.2 External Services
| Service | Purpose | Protocol | SLA |
|---------|---------|----------|-----|
| **Authorization Service** | User authentication & token issuance | HTTPS/REST (`/jsonauth/**`) | Business‑critical |
| **Notary Representation Service** | Provides notary data for legal processes | HTTPS/REST (`/uvz/v1/notaryrepresentations`) | Business‑critical |
| **Reporting Service** (external consumer) | Retrieves annual reports | HTTPS/REST (`/uvz/v1/reports/**`) | Business‑critical |

## 1.5 Communication Protocols
| From | To | Protocol | Data Format |
|------|----|----------|-------------|
| **Browser** | Angular SPA | HTTPS | JSON |
| **Angular SPA** | Backend (`container.backend`) | HTTPS/REST | JSON |
| **Node.js jsApi** | Backend | HTTPS/REST | JSON |
| **Backend** | Database | JDBC (SQL) | Relational tables |
| **Backend** | External Authorization Service | HTTPS/REST | JSON |
| **Backend** | Notary Representation Service | HTTPS/REST | JSON |

## 1.6 Container Inventory (C4 Container View)
| Container ID | Name | Type | Technology | Component Count |
|--------------|------|------|------------|-----------------|
| `container.backend` | backend | Application | Spring Boot (Java/Gradle) | 494 |
| `container.frontend` | frontend | Application | Angular (npm) | 404 |
| `container.js_api` | jsApi | Application | Node.js (npm) | 52 |
| `container.e2e_xnp` | e2e‑xnp | Test | Playwright (npm) | 0 |
| `container.import_schema` | import‑schema | Library | Java/Gradle | 0 |

## 1.7 REST API Surface (selected representative endpoints)
| HTTP Method | Path | Description |
|-------------|------|-------------|
| **POST** | `/uvz/v1/action/{type}` | Execute a domain‑specific action (e.g., create, sign) |
| **GET** | `/uvz/v1/deedentries` | List all deed entries |
| **POST** | `/uvz/v1/deedentries` | Create a new deed entry |
| **GET** | `/uvz/v1/deedentries/{id}` | Retrieve a specific deed entry |
| **PUT** | `/uvz/v1/deedentries/{id}` | Update an existing deed entry |
| **DELETE** | `/uvz/v1/deedentries/{id}` | Delete a deed entry |
| **GET** | `/uvz/v1/documents/{deedEntryId}/document-copies` | Fetch document copies for a deed |
| **POST** | `/jsonauth/user/to/authorization/service` | Authenticate user and obtain token |
| **GET** | `/uvz/v1/keymanager/cryptostate` | Query cryptographic key state |
| **GET** | `/uvz/v1/reports/annual` | Generate annual report |
| **PATCH** | `/uvz/v1/job/retry` | Retry failed background jobs |
| **GET** | `/keep/alive` | Health‑check endpoint |

> **Note** – The full list contains 196 REST endpoints covering CRUD operations, cryptographic services, archiving, reporting, workflow orchestration and administrative functions.

## 1.8 Context Diagram
The diagram below visualises the System Context (C4 Level 1). It shows the UVZ system as a black‑box, its primary containers, external actors and the main communication protocols.

> **Diagram file**: `c4-context.drawio` (generated separately).

---
*Document generated automatically from architecture facts (statistics, containers, endpoints) on 2026‑02‑09.*
