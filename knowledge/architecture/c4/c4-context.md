# C4 Level 1 – System Context

## 1.1 Overview
The **UVZ** platform is a Java‑Spring‑Boot based backend exposing a rich set of REST APIs for deed‑entry, document handling, archiving and reporting.  It is consumed by a web front‑end (Angular) and a Node.js API gateway, as well as by external integration partners (e.g., notary systems, reporting services).  In the System Context diagram the platform is shown as a single black‑box system.

## 1.2 System Attributes
| Attribute | Value |
|-----------|-------|
| **Name** | UVZ |
| **Domain** | UNKNOWN (public‑sector deed & document management) |
| **Purpose** | Manage deed entries, document lifecycle, archiving, reporting and integration with external notary/registry services |
| **Technology Stack** | Spring Boot (Java/Gradle), Angular, Node.js, Playwright (E2E) |
| **Containers** | 5 |
| **Components** | 951 |
| **Interfaces (REST endpoints)** | 196 |
| **Relations** | 190 |

## 1.3 Actors & Users
### 1.3.1 Human Actors
| Actor | Role | Primary Interactions |
|-------|------|----------------------|
| **End‑User (Citizen / Business)** | Initiates deed creation, uploads documents, checks status | Calls REST APIs via the Angular UI or external client applications |
| **Notary Representative** | Validates and signs deeds, retrieves reports | Consumes `/uvz/v1/notaryrepresentations` and related reporting endpoints |
| **System Administrator** | Deploys, monitors and configures the platform | Accesses management endpoints (e.g., `/uvz/v1/job/metrics`, `/uvz/v1/job/retry`) |
| **Integration Partner** | Exchanges data with external registries or archival services | Calls service‑to‑service APIs such as `/uvz/v1/documents/*` |

### 1.3.2 System Actors
| System | Role | Protocol | Typical Data |
|--------|------|----------|--------------|
| **Angular Front‑end** | UI client for end‑users | HTTPS/JSON | Deed entry requests, document uploads, status queries |
| **Node.js jsApi** | Lightweight API gateway for legacy callers | HTTPS/JSON | Simplified CRUD operations on deed entries |
| **Playwright E2E Tests** | Automated functional test runner | N/A (internal) | Test scripts exercising the public API |

## 1.4 External Systems
### 1.4.1 Databases (internal persistence)
| Database | Type | Purpose |
|----------|------|---------|
| **PostgreSQL (assumed)** | Relational | Stores deed entries, document metadata, audit logs |
| **File Store / Object Storage** | Binary | Holds document binaries, signatures, archival copies |

### 1.4.2 External Services
| Service | Purpose | Protocol |
|--------|---------|----------|
| **Notary Registry Service** | Registers signed deeds | HTTPS/JSON |
| **Archiving Service** | Long‑term storage of finalized documents | HTTPS/JSON |
| **Reporting Engine** | Generates annual and statutory reports | HTTPS/JSON |

## 1.5 Communication Protocols
| From | To | Protocol | Data Format |
|------|----|----------|-------------|
| External Client (Browser / Partner) | UVZ System | HTTPS | JSON payloads (REST) |
| UVZ System | PostgreSQL | JDBC | SQL |
| UVZ System | Object Store | HTTP/HTTPS | Binary streams |
| UVZ System | Notary Registry | HTTPS | JSON |
| UVZ System | Archiving Service | HTTPS | JSON |

## 1.6 Interaction Summary (selected high‑level flows)
1. **Deed Creation** – UI → `POST /uvz/v1/deedentries` → Backend stores entry, returns identifier.
2. **Document Upload** – UI → `POST /uvz/v1/documents/{deedEntryId}/document-copies` → Backend stores binary in object store.
3. **Signature Capture** – UI → `PUT /uvz/v1/documents/signing-info` → Backend updates signature state.
4. **Archiving** – Scheduler → `POST /uvz/v1/archiving/sign-submission-token` → Backend triggers archival service.
5. **Reporting** – Admin UI → `GET /uvz/v1/reports/annual` → Backend aggregates data and returns PDF/JSON.

## 1.7 System Context Diagram
The diagram below (generated with Draw.io) visualises the UVZ system as a black‑box surrounded by its actors and external systems.

> **Diagram file:** `c4/c4-context.drawio`

---
*Document generated on 2026‑02‑09 using real architecture facts (containers, components, REST endpoints, and controller list).*
