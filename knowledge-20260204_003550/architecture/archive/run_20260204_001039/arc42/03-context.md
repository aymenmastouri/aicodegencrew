# 03 – System Scope and Context

## 3.1 Business Context

| External Actor | Touch‑point | Primary Concern |
|----------------|-------------|-----------------|
| **Client applications (web browsers, mobile apps, other services)** | HTTP / REST endpoints (e.g., `POST /uvz/v1/deedentries`, `GET /uvz/v1/action/{type}`) | Consume the public API to create, read, update, and process deeds, actions, numbers, workflows, reports and XNP‑related services. |
| **Operators / Administrators** | Angular SPA (served by `StaticContentController` at `/web/**`) and Actuator health endpoints | Perform day‑to‑day administration, monitor system health (`/actuator/health`, `/actuator/metrics`), and run reports. |
| **XNP Platform** (external partner) | Integration adapters (`XnpAuthenticationAdapter`, `XnpArchiveManagerEndpoint`, …) | Provides authentication, document handling, notifications, storage and signature services that the UVZ system consumes. |
| **Contract‑testing Consumers** | Pact‑Broker (`broker_app` container) | Retrieve and verify consumer‑driven contract expectations during CI/CD. |

### Key Business Interfaces (selected)

| Interface ID | HTTP Method | Path | Implemented by | Business Function |
|--------------|-------------|------|----------------|-------------------|
| `api_action_rest_service_impl_0` | POST | `/uvz/v1/action/{type}` | `ActionRestServiceImpl` | Create a new action of the given type. |
| `api_action_rest_service_impl_1` | GET | `/uvz/v1/action/{id}` | `ActionRestServiceImpl` | Retrieve details of a specific action. |
| `api_deed_entry_rest_service_impl_14‑21` | GET / POST | Various `/uvz/v1/deedentries…` | `DeedEntryRestServiceImpl` | Full CRUD (list, create, retrieve, update) for deed entries and related bulk operations. |
| `api_archiving_rest_service_impl_8‑10` | POST / GET | `/uvz/v1/archiving/*` | `ArchivingRestServiceImpl` | Sign tokens, check archiving enablement. |
| `api_key_manager_rest_service_impl_6‑7` | GET | `/uvz/v1/keymanager/*` | `KeyManagerRestServiceImpl` | Retrieve key‑manager‑related metadata. |
| `api_static_content_controller_2‑5` | GET | `/web/*` | `StaticContentController` | Serve static UI assets for the Angular SPA. |
| `api_business_purpose_rest_service_impl_11` | GET | `/businesspurposes` | `BusinessPurposeRestServiceImpl` | Expose business‑purpose reference data. |
| … (remaining 20+ endpoints) | … | … | … | Provide the remaining REST‑ful operations for XNP integration, reporting, workflow, number management, etc. |

All interfaces use **JSON** payloads over **HTTP/HTTPS** and follow a **path‑based versioning** strategy (`/uvz/v1/…`), guaranteeing a stable contract for external consumers.

---

## 3.2 Technical Context

| System Component | Technology / Container | Role / Interaction |
|------------------|------------------------|--------------------|
| **Backend** | Spring Boot (Java) – `backend` container | Hosts the 24 controller components, 233 services, 4 repositories, and the XNP adapters. Exposes the REST API described above. |
| **Frontend** | Angular (TypeScript) – `frontend` container | SPA that consumes the backend API, served via `StaticContentController`. Implements lazy‑loaded routing, services‑based state handling, and UI built with ng‑bootstrap/Bootstrap 5.2.3. |
| **Database** | PostgreSQL – `postgres` container | Persists the 37 JPA‑annotated entity definitions (e.g., `DeedEntryEntity`, `WorkflowEntity`). Accessed through Spring Data repositories. |
| **Contract Repository** | Pact‑Broker – `broker_app` container | Stores consumer‑driven contract files; used by CI pipelines to verify API compatibility. |
| **Container Host** | Ubuntu base – `docker` container | Provides the OS layer for all Docker images; orchestrated by Docker Compose. |
| **Actuator & Health** | Spring Boot Actuator (built‑in) | Exposes `/actuator/health`, `/actuator/metrics`, liveness and readiness endpoints for operational monitoring. |

### Communication Protocols & Formats

* **REST/HTTP + JSON** – Primary protocol for all external and internal API calls (backend ↔ frontend, backend ↔ XNP adapters, backend ↔ external consumers).  
* **HTTPS** – Assumed for production deployments (not explicit in code but required for secure transport).  
* **JDBC** – Backend connects to PostgreSQL using standard JDBC drivers.  
* **Docker networking** – Containers communicate over Docker’s virtual network; ports are exposed per Docker‑Compose configuration.  
* **Pact contract files** – JSON‑based contract definitions exchanged with the Pact‑Broker.

---

## 3.3 External Dependencies

| Dependency | Type | Access Method | Reason for Inclusion |
|------------|------|----------------|----------------------|
| **XNP Platform** | External service ecosystem | Invoked via `XnpAuthenticationAdapter`, `XnpArchiveManagerEndpoint`, `XnpFileApiAdapter`, etc. (Spring beans in the `backend` container) | Provides authentication, document handling, notification, storage and signature capabilities required by UVZ business processes. |
| **PostgreSQL Database** | External data store | JDBC connection defined in Spring `application.yml` (container `postgres`) | Persists domain entities (37 JPA‑mapped tables) and supports transactional operations. |
| **Pact‑Broker** | Contract‑testing artifact repository | HTTP API accessed by CI pipelines (container `broker_app`) | Enables consumer‑driven contract verification; ensures backward‑compatible API evolution. |
| **Operating System (Ubuntu)** | Base OS for Docker images | Dockerfile builds on `ubuntu` base image | Provides a consistent, lightweight runtime environment for all containers. |
| **Node.js / npm** | Build tool for Angular SPA | Executed inside the `frontend` container during image build | Compiles TypeScript to JavaScript, bundles the SPA, and produces static assets served by the backend. |

These dependencies are *external* to the core UVZ codebase but are integral to the system’s functioning and must be accounted for in deployment, versioning, and risk management activities.