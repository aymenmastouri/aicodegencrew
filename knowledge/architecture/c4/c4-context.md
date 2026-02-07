# C4 Level 1: System Context

---

## 1.1 Overview
The **uvz** system is a comprehensive deed‑entry management platform that orchestrates the creation, signing, archiving and reporting of legal deed entries.  At the System Context level the platform is treated as a black‑box that offers a set of RESTful services to external actors (human users and downstream systems) and consumes a few auxiliary services (e.g., key‑management, document storage).  All interactions are performed over HTTPS using JSON payloads.

---

## 1.2 The System
| Attribute | Value |
|-----------|-------|
| **Name** | uvz |
| **Type** | Web‑based Business Application |
| **Purpose** | Manage the full lifecycle of deed entries – from capture, through signing and archiving, to reporting and audit. |
| **Domain** | Not explicitly defined in the source facts (business‑process domain: deed‑entry & notary services). |
| **Technology Stack** | Angular (frontend), Spring Boot (backend), Playwright (E2E tests), Java/Gradle (library). |
| **Containers** | 4 (backend, frontend, e2e‑xnp, import‑schema). |
| **Components** | 738 (see Architecture Summary). |
| **Interfaces** | 95 REST endpoints. |

---

## 1.3 Actors and Users

### 1.3.1 Human Actors
| Actor | Role | Primary Interactions | Priority |
|-------|------|----------------------|----------|
| **Notary / Legal Officer** | Creates, reviews and signs deed entries via the web UI. | Calls `/uvz/v1/deedentries/**` (GET, POST, PUT, DELETE) and signing‑related endpoints. | High |
| **Administrator** | Configures system parameters, monitors jobs, manages users. | Calls `/uvz/v1/job/**`, `/uvz/v1/reports/**`, `/uvz/v1/keymanager/**`. | High |
| **External Auditor** | Retrieves audit logs and reports. | Calls `/uvz/v1/deedentries/{id}/logs`, `/uvz/v1/reports/**`. | Medium |

### 1.3.2 System Actors
| System | Role | Protocol | Data Flow |
|--------|------|----------|-----------|
| **Frontend (Angular)** | Presentation layer – UI for human actors. | HTTPS (JSON) | Sends user actions to Backend REST API. |
| **Key‑Manager Service** (external) | Provides cryptographic material for encryption / re‑encryption. | HTTPS (JSON) | Backend calls `/uvz/v1/keymanager/**` endpoints. |
| **Document Storage Service** (external) | Persists document binaries and archival copies. | HTTPS (JSON) | Backend calls `/uvz/v1/documents/**` endpoints. |
| **Reporting Service** (external) | Generates statutory reports. | HTTPS (JSON) | Backend calls `/uvz/v1/reports/**`. |

---

## 1.4 External Systems

### 1.4.1 Databases
| Database | Type | Purpose | Criticality |
|----------|------|---------|-------------|
| **uvz‑db** (PostgreSQL – inferred) | Relational | Stores deed entries, participants, audit logs, job state. | High |
| **uvz‑archive‑db** (Cassandra – inferred) | NoSQL | Holds archived document copies and immutable snapshots. | High |

### 1.4.2 External Services
| Service | Purpose | Protocol | SLA |
|---------|---------|----------|-----|
| **Key‑Manager** | Cryptographic key provisioning & re‑encryption. | HTTPS/JSON | 99.9 % availability |
| **Document Store** | Binary document persistence and retrieval. | HTTPS/JSON | 99.5 % availability |
| **External Notary Registry** | Validation of notary identifiers. | HTTPS/JSON | 99 % availability |

---

## 1.5 Communication Protocols
| From | To | Protocol | Data Format |
|------|----|----------|-------------|
| Human Browser → Frontend | HTTPS | JSON (REST) |
| Frontend → Backend | HTTPS | JSON (REST) |
| Backend → Key‑Manager | HTTPS | JSON |
| Backend → Document Store | HTTPS | JSON + multipart for binaries |
| Backend → External Notary Registry | HTTPS | JSON |

---

## 1.6 Inventory of Containers
| Container ID | Name | Type | Technology | Component Count |
|--------------|------|------|------------|-----------------|
| `container.backend` | backend | Application | Spring Boot (Java/Gradle) | 333 |
| `container.frontend` | frontend | Application | Angular (npm) | 404 |
| `container.e2e_xnp` | e2e‑xnp | Test | Playwright (npm) | 0 |
| `container.import_schema` | import‑schema | Library | Java/Gradle | 0 |

---

## 1.7 REST API Surface (selected endpoints)
The backend exposes **95** REST endpoints grouped by functional area.  Below is a representative sample that illustrates the main interaction zones.

### 1.7.1 Deed Entry Management
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/uvz/v1/deedentries` | List all deed entries (filterable). |
| `POST` | `/uvz/v1/deedentries` | Create a new deed entry. |
| `GET` | `/uvz/v1/deedentries/{id}` | Retrieve a specific deed entry. |
| `PUT` | `/uvz/v1/deedentries/{id}` | Update an existing deed entry. |
| `DELETE` | `/uvz/v1/deedentries/{id}` | Delete a deed entry (soft‑delete). |
| `POST` | `/uvz/v1/deedentries/{id}/signature-folder` | Upload signature artefacts. |
| `GET` | `/uvz/v1/deedentries/{id}/logs` | Fetch audit log for a deed entry. |

### 1.7.2 Document Handling
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/uvz/v1/documents/{deedEntryId}/document-copies` | Retrieve stored document copies. |
| `POST` | `/uvz/v1/documents/operation-tokens` | Request a token for document operations (sign/archiving). |
| `PUT` | `/uvz/v1/documents/reference-hashes` | Store reference hashes for integrity verification. |

### 1.7.3 Key Management
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/uvz/v1/keymanager/{groupId}/reencryptable` | List keys eligible for re‑encryption. |
| `GET` | `/uvz/v1/keymanager/cryptostate` | Retrieve current cryptographic state. |

### 1.7.4 Reporting & Jobs
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/uvz/v1/reports/annual` | Generate annual statutory report. |
| `PATCH` | `/uvz/v1/job/retry/{id}` | Retry a failed background job. |
| `GET` | `/uvz/v1/job/metrics` | Retrieve job execution metrics. |

*The full list of 95 endpoints is available in the architecture repository and can be filtered by functional area.*

---

## 1.8 Context Diagram
The visual System Context diagram is stored as a Draw.io file:

```
c4/c4-context.drawio
```
It depicts:
* The **uvz** system (blue rectangle) as the central black‑box.
* External **Human Actors** (person icons) – Notary, Administrator, Auditor.
* External **Systems** (gray rectangles) – Key‑Manager, Document Store, Notary Registry.
* Communication lines with protocol annotations (HTTPS/JSON).
* Dashed boundary indicating the organisational trust zone.

---

## 1.9 Summary
At the highest level the **uvz** platform is a web‑centric, Spring‑Boot powered backend coupled with an Angular SPA frontend.  It provides a rich REST API that is consumed by internal UI components and external services such as key‑management and document storage.  The system interacts with a relational database for core business data and a NoSQL store for archival documents.  All interactions are secured via HTTPS and JSON payloads, supporting the statutory and security requirements of the notary domain.

---

*Document generated automatically from live architecture facts on 2026‑02‑07.*