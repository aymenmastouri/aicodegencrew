# C4 Level 1 – System Context  
**System:** **UVZ Deed Management System** (`uvz`)  
**Documentation file:** `knowledge/architecture/c4/c4-context.md`  
**Diagram file:** `knowledge/architecture/c4/context.drawio`  

---  

## 1.1 Overview  

The UVZ Deed Management System is a web‑based platform that supports the full lifecycle of land‑registry deeds – from creation and hand‑over through archival and reporting.  It is consumed directly by notaries and other legal professionals through a rich Angular single‑page UI, and it also offers a REST API for integration with partner systems (e.g., municipal cadastral services, tax authorities).  Security is enforced centrally via Keycloak (OIDC) and all data is persisted in a PostgreSQL database.  

---  

## 1.2 The System  

| Attribute | Value |
|-----------|-------|
| **Name** | UVZ Deed Management System |
| **Type** | Web application & REST API |
| **Purpose** | Provide a compliant, auditable, and searchable environment for creating, editing, handing‑over, signing, archiving and reporting on land‑registry deeds. |
| **Domain** | Public‑sector land‑registry / notarial services |
| **Primary Value** | • Guarantees legal compliance and auditability.<br>• Reduces manual paperwork and processing time.<br>• Enables seamless data exchange with external authorities.<br>• Supplies configurable reporting for internal analytics and statutory requirements. |

---  

## 1.3 Actors and Users  

### 1.3.1 Human Actors  

| Actor | Role / Type | Main Interactions | Frequency | Priority |
|-------|-------------|-------------------|-----------|----------|
| **Notary / End‑User** | Primary user (person) | Uses the Angular UI to create, edit, view, hand‑over and sign deeds; runs ad‑hoc reports. | Daily (multiple sessions) | High |
| **System Administrator** | Operational staff (person) | Configures container runtime, monitors health, updates security policies, performs backups. | Weekly / on incidents | Medium |
| **Analyst / Auditor** | Business analyst (person) | Executes read‑only reporting UI, exports CSV / PDF, inspects audit logs. | Periodic (monthly/quarterly) | Low |
| **Scheduler / Batch Process** | Background process (personified) | Triggers recurring jobs (archiving, report generation, signature‑folder creation). | Hourly‑daily | Medium |

> **Interaction notes** – Each human actor accesses the system over **HTTPS** (TLS 1.2+).  The UI is a thin Angular SPA that talks to the backend via JSON‑encoded REST calls.  Administrators also use the Actuator endpoints (`/actuator/*`) for health checks.

### 1.3.2 System Actors  

| System | Role / Type | Protocol | Data Flow |
|--------|--------------|----------|-----------|
| **External Partner API** | Data provider / consumer (government services) | HTTPS / REST (JSON) | Inbound (requests) & outbound (responses) |
| **Pact Broker** | Contract‑testing artefact store (CI/CD) | HTTP / REST | Bidirectional (CI pushes contracts, services pull during test) |
| **Keycloak (Identity Provider)** | Authentication & authorisation | OIDC / OAuth2 (HTTPS) | Inbound token requests, outbound token validation |
| **SMTP / Notification Service** (optional) | Email / push notifications | SMTP / HTTPS | Outbound (email confirmations, audit alerts) |

---  

## 1.4 External Systems  

### 1.4.1 Databases  

| Database | Type | Technology | Purpose | Criticality |
|----------|------|------------|---------|-------------|
| **PostgreSQL** | Relational DBMS | PostgreSQL 13 | Persistent storage for deeds, audit logs, reference data, user‑role mappings. | **Critical** (single point of truth) |

### 1.4.2 Supporting Services  

| Service | Purpose | Technology | Protocol | SLA |
|---------|---------|------------|----------|-----|
| **Keycloak** | Centralised identity & access management | Keycloak (OpenID Connect) | HTTPS/OIDC | 99.9 % (authentication) |
| **Pact Broker** | Stores consumer‑provider contract files for CI | Pact‑Broker (Docker) | HTTP/REST | N/A (development artefact) |
| **SMTP / Notification** | Sends e‑mail confirmations & alerting | Postfix / external SaaS | SMTP / TLS | 99 % (delivery) |
| **External Partner API** | Provides cadastral data & receives deed status updates | Various (government) | HTTPS/REST | Contract‑defined |

---  

## 1.5 System Context Diagram  

The diagram below visualises the UVZ system in its environment.  

*File location:* `knowledge/architecture/c4/context.drawio`  

**Key visual conventions (SEAGuide C4 style)**  

| Symbol | Meaning |
|--------|---------|
| **Blue rounded rectangle** | The UVZ Deed Management System (internal boundary) |
| **Gray rounded rectangle** | External systems (Keycloak, PostgreSQL, External Partner API, Pact Broker) |
| **Cylinder** | Database (PostgreSQL) |
| **Person icon** | Human actors (Notary, Administrator, Analyst, Scheduler) |
| **Solid arrow** | Synchronous request/response (e.g., HTTPS) |
| **Dashed line** | System boundary (container) |

> **Diagram excerpt (ASCII fallback)**  

```
   +-------------------+            +-------------------+
   |  Notary / End‑User|            |   Administrator   |
   +--------+----------+            +--------+----------+
            |                               |
            | HTTPS/JSON                     |
            v                               v
   +---------------------------------------------------+
   |               UVZ Deed Management System          |
   |  (Angular SPA + Spring‑Boot REST API)             |
   +-------------------+-------------------------------+
           |           |            |               |
   HTTPS/JSON   HTTPS/JSON   JDBC (PostgreSQL)   HTTP (Pact)
   |                |            |               |
   v                v            v               v
+------+      +-----------+  +-----------+   +--------------+
|Keycloak|    |External   |  |PostgreSQL|   |Pact Broker   |
| (OIDC) |    |Partner API|  | (cylinder) | (gray box)    |
+------+      +-----------+  +-----------+   +--------------+
```

---  

## 1.6 Context Boundaries  

| In‑Scope (inside the blue box) | Out‑of‑Scope (outside the blue box) |
|--------------------------------|--------------------------------------|
| • Angular frontend (SPA) <br>• Spring‑Boot backend (REST, business logic) <br>• PostgreSQL schema (deed tables, audit logs) <br>• Keycloak integration (authentication) <br>• Pact‑Broker usage in CI <br>• Scheduler jobs (archiving, reporting) | • Physical hardware / network infrastructure (routers, firewalls) <br>• External partner services (cadastral data source) <br>• Email / SMS gateway (only used for optional notifications) <br>• Third‑party cloud services (e.g., CDN) |

---  

## 1.7 Communication Patterns  

| From | To | Protocol | Sync / Async | Typical Payload |
|------|----|----------|--------------|-----------------|
| **User (Notary)** → **System (UI → API)** | HTTPS / REST | **Sync** | JSON request/response (CRUD operations) |
| **System (Backend)** → **PostgreSQL** | JDBC (SQL) | **Sync** | SQL statements (INSERT/UPDATE/SELECT) |
| **System (Backend)** → **Keycloak** | OIDC / OAuth2 | **Sync** | Token request / validation |
| **System (Backend)** → **External Partner API** | HTTPS / REST | **Sync** | JSON payloads (deed status, cadastral lookup) |
| **System (Backend)** → **Pact Broker** (CI only) | HTTP / REST | **Sync** | Contract files (JSON) |
| **Scheduler** → **Backend Services** | Internal method call (Spring) | **Sync** (or async via Spring @Async) | POJO parameters |
| **System** → **SMTP / Notification Service** | SMTP (TLS) | **Async** (fire‑and‑forget) | Plain‑text / HTML e‑mail |

---  

## 1.8 References  

| Source | Description |
|--------|-------------|
| `architecture_facts.json` | Container list (backend, frontend, docker, postgres, broker_app) and component counts (826 components). |
| `list_components_by_stereotype` | Used to confirm number of controllers/services for sizing the diagram. |
| `query_architecture_facts (relations)` | Shows key `uses` relationships that shape the interaction description. |
| **SEAGuide – C4 Documentation Standards** | Styling guidelines for colours, shapes and legends (draw.io). |
| **Keycloak OIDC docs** | Protocol details for authentication flow. |
| **Pact‑Broker documentation** | Contract‑testing integration notes. |

---  

### Appendix – How to view the diagram  

Open the file `knowledge/architecture/c4/context.drawio` with the Draw.io (diagrams.net) editor.  The diagram follows the Capgemini SEAGuide C4 visual conventions (blue internal system, gray externals, cylinder for DB, person icons for actors, labelled arrows for protocols).  

---  

*Prepared by:* **Senior Software Architect – C4 Model Expert**  
*Date:* **2026‑02‑03**  