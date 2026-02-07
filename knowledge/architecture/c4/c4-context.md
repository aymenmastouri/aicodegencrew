# C4 Level 1: System Context

## 1.1 Overview
The **System Context** diagram presents the *uvz* system as a single black‑box component and identifies all external actors (people and systems) that interact with it. It clarifies **who** uses the system, **what** external services it depends on, and the **communication protocols** that bind them together. This level is the entry point for all stakeholders – business owners, developers, and operations – to understand the overall scope without being distracted by internal implementation details.

---

## 1.2 The System
| Attribute | Value |
|-----------|-------|
| **Name** | `uvz` |
| **Type** | Application (Spring Boot backend + Angular frontend) |
| **Purpose** | Provides a comprehensive REST API for deed entry, document handling, key‑management, archiving, reporting and workflow orchestration within the UVZ domain. |
| **Domain** | *Not explicitly defined in the source artefacts* |
| **Technology Stack** | Backend: Spring Boot (Java, Gradle)  \nFrontend: Angular (npm)  \nTest: Playwright (e2e‑xnp)  \nLibrary: Java/Gradle (`import‑schema`) |
| **Containers** | 4 (backend, frontend, e2e‑xnp, import‑schema) |
| **Components** | 738 (presentation, application, domain, data‑access, infrastructure, unknown) |
| **Interfaces** | 125 REST endpoints |
| **Relations** | 169 (uses, manages, imports, references) |

---

## 1.3 Actors and Users

### 1.3.1 Human Actors
| Actor | Role | Interactions | Priority |
|-------|------|--------------|----------|
| **UVZ End‑User** | Business user that creates, reviews and signs deeds | Consumes the Angular UI and invokes the `/uvz/v1/**` REST endpoints via the browser | High |
| **System Administrator** | Operates and monitors the platform | Accesses management UI, triggers job retries, views metrics (`/uvz/v1/job/**`) | Medium |
| **External Auditor** | Audits document lifecycle | Reads reports (`/uvz/v1/reports/**`) and document metadata | Low |

### 1.3.2 System Actors
| System | Role | Protocol | Data Flow |
|--------|------|----------|-----------|
| **Key Manager Service** | Provides cryptographic key material for encryption / re‑encryption | HTTP/HTTPS (REST) | Requests to `/uvz/v1/keymanager/**` retrieve key status and re‑encryption capabilities |
| **Document Storage Service** | Persists binary document payloads | HTTP/HTTPS (REST) | `/uvz/v1/documents/**` endpoints upload, retrieve and manage document copies |
| **External Notary Service** | Validates notary representations | HTTP/HTTPS (REST) | `/uvz/v1/notaryrepresentations` fetches notary data |
| **Job Scheduler / Worker** | Executes background jobs (archiving, re‑encryption, bulk capture) | Internal messaging (e.g., RabbitMQ, Kafka) – not exposed in source but implied by job endpoints | `/uvz/v1/job/**` triggers, monitors and retries asynchronous jobs |

---

## 1.4 External Systems

### 1.4.1 Databases
| Database | Type | Purpose | Criticality |
|----------|------|---------|-------------|
| **uvz‑db** (implicit) | Relational (PostgreSQL / MySQL) | Stores deed entries, participants, documents, workflow state, audit logs | Critical |
| **Key Manager DB** (external) | Relational | Holds encryption keys and re‑encryption state | High |
| **Reporting Data Warehouse** (external) | Columnar / OLAP | Supplies data for `/uvz/v1/reports/**` endpoints | Medium |

### 1.4.2 External Services
| Service | Purpose | Protocol | SLA |
|---------|---------|----------|-----|
| **Key Manager Service** | Cryptographic key provisioning & re‑encryption state | REST/HTTPS | 99.9% availability |
| **Document Storage Service** | Binary document persistence (PDF, XML, etc.) | REST/HTTPS | 99.5% availability |
| **Notary Representation Service** | Provides official notary data for validation | REST/HTTPS | 99.0% availability |
| **External Notification Service** (e.g., email/SMS) | Sends user notifications on workflow events | REST/HTTPS | 99.0% availability |

---

## 1.5 Communication Protocols
| From | To | Protocol | Data Format |
|------|----|----------|-------------|
| **Browser (Human Actor)** | **Frontend (Angular)** | HTTPS (TLS) | HTML/JSON (Angular SPA) |
| **Frontend** | **Backend (Spring Boot)** | HTTPS (TLS) | JSON (REST) |
| **Backend** | **Key Manager Service** | HTTPS (TLS) | JSON (REST) |
| **Backend** | **Document Storage Service** | HTTPS (TLS) | Multipart/form‑data, JSON |
| **Backend** | **Notary Representation Service** | HTTPS (TLS) | JSON |
| **Backend** | **Job Scheduler / Worker** | Internal messaging (e.g., AMQP, Kafka) | Binary / JSON payloads |
| **Backend** | **Reporting Data Warehouse** | JDBC / ODBC (SQL) | Tabular data |

---

## 1.6 Context Diagram
The diagram below visualises the *uvz* system (black box) together with its external actors and systems. It follows the **C4 visual conventions** defined in Capgemini’s SEAGuide:
* **Blue boxes** – internal system (uvz) – shown as a single container.
* **Gray boxes** – external systems.
* **Person icons** – human actors.
* **Dashed lines** – trust boundaries (e.g., external services).

> **Diagram file:** `c4-context.drawio`

---

## 1.7 Interaction Scenarios (selected)
| Scenario | Initiator | Steps | Primary Endpoints |
|----------|-----------|-------|-------------------|
| **Create Deed Entry** | UVZ End‑User (via UI) | 1. UI POSTs to `/uvz/v1/deedentries`  <br>2. Backend validates, stores entry, triggers `archiving` job | `POST /uvz/v1/deedentries` |
| **Sign Document** | UVZ End‑User | 1. UI GETs signing token via `/uvz/v1/archiving/sign-submission-token` <br>2. UI uploads signed document via `/uvz/v1/documents/operation‑tokens` | `POST /uvz/v1/archiving/sign-submission-token`, `POST /uvz/v1/documents/operation‑tokens` |
| **Retrieve Report** | External Auditor | GET `/uvz/v1/reports/annual` (or other report types) | `GET /uvz/v1/reports/**` |
| **Retry Failed Job** | System Administrator | PATCH `/uvz/v1/job/retry/{id}` | `PATCH /uvz/v1/job/retry/{id}` |

---

*Prepared by the Senior Software Architect – C4 Model expert (Capgemini SEAGuide).*