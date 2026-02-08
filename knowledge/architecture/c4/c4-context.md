# C4 Level 1 – System Context

---

## 1.1 Overview
The **uvz** system is a comprehensive deed‑entry management platform that orchestrates the lifecycle of deed entries, document handling, archiving, re‑encryption, and reporting.  It is built as a set of Spring‑Boot micro‑services (backend), an Angular SPA (frontend), a Node.js API (jsApi) and a Playwright based end‑to‑end test suite (e2e‑xnp).  From a C4 **System Context** perspective the system is a black‑box that interacts with human users, external authentication services, document storage, and downstream reporting tools.

---

## 1.2 The System
| Attribute | Value |
|-----------|-------|
| **Name** | uvz |
| **Type** | Business Application (Deed‑Entry Management) |
| **Purpose** | Manage creation, modification, signing, hand‑over and archival of deed entries and associated documents. |
| **Domain** | Not explicitly defined – core domain is *Deed Entry & Document Lifecycle*. |
| **Technology Stack** | Angular, Spring Boot, Node.js, Playwright, Gradle, npm |
| **Containers** | backend (Spring Boot), frontend (Angular), jsApi (Node.js), e2e‑xnp (Playwright), import‑schema (Java library) |
| **Components** | 951 total (≈494 backend, 404 frontend, 52 jsApi) |
| **Interfaces** | 196 REST endpoints |
| **Relations** | 190 uses / manages / imports / references |

---

## 1.3 Actors and Users
### 1.3.1 Human Actors
| Actor | Role | Primary Interactions | Priority |
|-------|------|----------------------|----------|
| **Business User** | Creates, reviews and signs deed entries via the web UI. | Calls REST endpoints under `/uvz/v1/deedentries/**` (GET, POST, PUT, DELETE). | High |
| **Administrator** | Configures archiving, re‑encryption, and system health monitoring. | Calls `/uvz/v1/archiving/**`, `/uvz/v1/keymanager/**`, `/uvz/v1/job/**`. | High |
| **Auditor** | Reads logs and reports for compliance. | Calls `/uvz/v1/reports/**` and `/uvz/v1/deedentries/{id}/logs`. | Medium |
| **External Signer Service** (system) | Provides digital signatures for documents. | Invoked via `/uvz/v1/documents/signing-info` (PUT). | High |
| **External Document Store** (system) | Persists document copies and archival blobs. | Accessed through `/uvz/v1/documents/**` (GET/PUT/POST). | High |

### 1.3.2 System Actors
| System | Role | Protocol | Data Flow |
|--------|------|----------|----------|
| **Authentication Provider** (e.g., Keycloak) | Issues JWT tokens for UI and API calls. | HTTP / HTTPS (Bearer token) | Token → UI / API |
| **Reporting Engine** | Consumes report‑metadata and generates PDF/CSV. | HTTP / HTTPS (REST) | Report metadata → `/uvz/v1/report-metadata/**` |
| **Legacy Notary Service** | Supplies notary representation data. | HTTP / HTTPS (REST) | `/uvz/v1/notaryrepresentations` |
| **External Email Service** | Sends notifications for hand‑over and archiving events. | SMTP / HTTP API | Notification payloads from backend |

---

## 1.4 External Systems
### 1.4.1 Databases
| Database | Type | Purpose | Criticality |
|----------|------|---------|------------|
| **uvz‑postgres** | Relational (PostgreSQL) | Stores deed entries, logs, business purposes, document metadata, hand‑over datasets. | Critical |
| **uvz‑archive‑store** | Object storage (S3‑compatible) | Holds archived document copies and signed PDFs. | High |
| **uvz‑audit‑log** | Relational (PostgreSQL) | Immutable audit trail for compliance. | High |

### 1.4.2 External Services
| Service | Purpose | Protocol | SLA |
|---------|---------|----------|-----|
| **Key Management Service (KMS)** | Provides encryption keys and re‑encryption capabilities. | HTTPS (REST) | 99.9 % |
| **Document Signature Service** | Generates digital signatures for deed documents. | HTTPS (REST) | 99.5 % |
| **Reporting Service** | Generates annual and custom reports. | HTTPS (REST) | 99 % |
| **Email / Notification Service** | Sends status e‑mails to users. | SMTP / HTTP API | 99 % |

---

## 1.5 Communication Protocols
| From | To | Protocol | Data Format |
|------|----|----------|-------------|
| **Browser (User)** | Frontend (Angular) | HTTPS (TLS) | JSON / HTML |
| Frontend | Backend (Spring Boot) | HTTPS (TLS) | JSON (REST) |
| Frontend | jsApi (Node.js) | HTTP (REST) | JSON |
| Backend | Database (PostgreSQL) | JDBC (TLS) | SQL |
| Backend | KMS / Signature Service | HTTPS (TLS) | JSON |
| Backend | Object Store (S3) | HTTPS (REST) | Binary (PDF, ZIP) |
| Backend | Reporting Engine | HTTPS (REST) | JSON |
| Backend | Email Service | SMTP / HTTP API | MIME / JSON |

---

## 1.6 Context Diagram
The diagram below visualises the **uvz** system (blue box) together with its external actors (people icons) and external systems (gray boxes).  The diagram is stored as a Draw.io file `c4-context.drawio`.

```
[Diagram placeholder – see c4-context.drawio]
```

---

## 1.7 Interaction Summary (selected use‑cases)
| Use‑Case | Primary Actor | Backend Services Involved | Key Endpoints |
|----------|--------------|--------------------------|--------------|
| **Create Deed Entry** | Business User | DeedEntryRestServiceImpl, DocumentMetaDataServiceImpl | `POST /uvz/v1/deedentries` |
| **Sign Document** | External Signer Service | SignatureFolderServiceImpl | `POST /uvz/v1/deedentries/{id}/signature-folder` |
| **Archive Document** | Administrator | ArchivingServiceImpl, DocumentMetaDataServiceImpl | `POST /uvz/v1/archiving/sign-submission-token` |
| **Generate Report** | Auditor | ReportServiceImpl, ReportMetadataServiceImpl | `GET /uvz/v1/reports/annual` |
| **Re‑encrypt Keys** | Administrator | KeyManagerServiceImpl | `GET /uvz/v1/keymanager/{groupId}/reencryptable` |
| **Run End‑to‑End Tests** | CI/CD Pipeline | Playwright test suite (e2e‑xnp) | – |

---

*All tables and lists are derived from the live architecture facts (951 components, 196 REST endpoints, 5 containers) and reflect the current state of the uvz platform.*
