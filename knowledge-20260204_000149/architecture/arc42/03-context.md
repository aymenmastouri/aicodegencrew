# 03 – System Scope and Context

## 3.1 Business Context

| Business driver | Description |
|-----------------|-------------|
| **Deed processing** | The core of *uvz* is to create, type, archive, re‑encrypt and sign deed entries. |
| **Number management** | Generates, formats and fills gaps in UVZ numbers that are required for every deed. |
| **Workflow orchestration** | Coordinates jobs, tasks and overall workflow steps (e.g., approval, signing). |
| **Reporting** | Supplies meta‑data for the generation of statutory and operational reports. |
| **Action handling** | Exposes a set of action‑related endpoints (e.g., creating an action, retrieving its state). |
| **Business‑purpose management** | Provides a lightweight REST interface for business‑purpose data. |
| **External XNP integration** | Calls the external **XNP** platform for authentication, document handling, notifications and other ancillary services. |

### Primary Actors  

| Actor | Role / Interaction |
|-------|--------------------|
| **Client** (web browser, mobile app, other HTTP consumer) | Consumes the public REST API (path‑based version `/uvz/v1/...`) to perform deed‑related operations, query numbers, start workflows, etc. |
| **XNP platform** | Acts as an external service provider; *uvz* invokes XNP adapters (e.g., `XnpAuthenticationAdapter`, `XnpArchiveManagerEndpoint`) to delegate authentication, document storage and notification tasks. |
| **Ops / DevOps tooling** | Interacts with the **Pact‑Broker** (container `broker_app`) to retrieve contract definitions during CI/CD runs. |

The system therefore sits between internal public‑sector users (the *Client*), an external XNP ecosystem, and the operational infrastructure that supports testing and deployment.

---

## 3.2 Technical Context

| Aspect | Details |
|--------|---------|
| **Public interface** | A versioned **REST** API (`/uvz/v1/...`) exposed by the 24 Spring Boot controllers (e.g., `ActionRestServiceImpl`, `DeedEntryRestServiceImpl`, `ArchivingRestServiceImpl`). |
| **Communication protocol** | HTTP/HTTPS with JSON payloads. All endpoints are documented as `type: REST` in the architecture facts. |
| **Data format** | JSON for request and response bodies (e.g., `GET /uvz/v1/deedentries`, `POST /uvz/v1/action/{type}`). |
| **Internal integration** | Controllers delegate to services (`*ServiceImpl`) which use the **repository_pattern** to access the persistence layer.  The **adapter_pattern** is used for XNP calls, isolating external protocol details. |
| **Security** | Spring Security protects every endpoint; authentication is performed via the XNP platform (mock adapters are present for testing only). |
| **Error handling** | Centralised `DefaultExceptionHandler` converts exceptions to a consistent JSON error object (`errorCode`, `message`, `timestamp`). |
| **Versioning strategy** | Path‑based (`/uvz/v1/`); a breaking change requires a new major path segment. |
| **Deployment topology** | Distributed containers orchestrated by Docker‑Compose (backend, frontend, PostgreSQL, Pact‑Broker, Ubuntu base). |
| **Observability** | Spring Actuator provides health‑check and metrics endpoints (e.g., `/actuator/health`). |

---

## 3.3 External Dependencies

| Dependency | Type | Purpose in *uvz* |
|------------|------|------------------|
| **PostgreSQL** | Relational database (container `postgres`) | Persists all domain entities (37 entities across 5 core bounded contexts). |
| **XNP platform** | External service ecosystem (authentication, document handling, notifications) | Integrated via the 24 `Xnp*` services (e.g., `XnpAuthenticationAdapter`, `XnpArchiveManagerEndpoint`). |
| **Pact‑Broker** | Contract‑testing broker (container `broker_app`) | Stores consumer‑driven contract definitions; used during CI/CD to verify API compatibility. |
| **Ubuntu** | Base OS for Docker images (container `docker`) | Provides the underlying Linux environment for all other containers. |
| **Angular runtime (Node.js)** | Front‑end runtime (container `frontend`) | Executes the SPA; communicates with the backend REST API over HTTP. |

These external components are required at runtime (PostgreSQL, XNP) or during development / CI (Pact‑Broker, Ubuntu base). All interactions are defined through well‑known interfaces, keeping the overall system loosely coupled while satisfying the business and technical objectives.