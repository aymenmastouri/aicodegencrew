# 03 – System Scope and Context

## 3.1 Business Context  

| Business actor | Interaction with **uvz** | Relevant interface(s) |
|----------------|--------------------------|----------------------|
| **End‑user (web browser)** | Uses the single‑page Angular UI to create, view and process deeds, numbers, workflows and related reports. | All REST endpoints exposed by the backend, e.g. <br>• `GET /uvz/v1/deedentries` (`DeedEntryRestServiceImpl`) <br>• `POST /uvz/v1/action/{type}` (`ActionRestServiceImpl`) <br>• `POST /uvz/v1/archiving/sign-submission-token` (`ArchivingRestServiceImpl`) |
| **External XNP platform** | Provides authentication, document handling, notifications and other services that are consumed by the **uvz** back‑end. | XNP adapters are implemented in the back‑end (e.g. `XnpAuthenticationAdapter`, `XnpDocumentsEndpoint`) – they are invoked from the service layer but are not exposed as public REST endpoints. |
| **Operations / DevOps** | Deploys, monitors and maintains the containerised system; runs health‑checks, metrics and contract‑testing pipelines. | Actuator health endpoints (e.g. `/actuator/health`), Pact‑Broker interaction (`broker_app`). |
| **Business owners / product managers** | Define and prioritize the core capabilities (deed management, number management, workflow management, reporting, etc.). | Not a technical interface, but they drive the use‑cases realised by the REST API. |

*No additional business actors are present in the factual model; the above list captures all identified external consumers of the system.*  

---

## 3.2 Technical Context  

### 3.2.1 Internal components (containers)  

| Container | Technology | Primary role |
|-----------|------------|--------------|
| **backend** | Spring Boot (Java 17) | Hosts the layered application (controllers → services → repositories) and implements all 30 + REST interfaces listed below. |
| **frontend** | Angular v18‑lts (TypeScript 5.4.5) | Provides the SPA UI; communicates with the backend over HTTP/REST. |
| **postgres** | PostgreSQL | Relational database storing the 37 domain entities and supporting 258 SQL scripts. |
| **broker_app** | Pact‑Broker | Holds contract‑testing specifications; used by CI/CD pipelines, not part of the runtime architecture. |
| **docker** | Ubuntu (base OS) | Underlies all container images. |

### 3.2.2 External interfaces (REST)  

| Interface ID | HTTP method | Path | Implemented by (controller) |
|--------------|-------------|------|-----------------------------|
| `api_action_rest_service_impl_0` | POST | `/uvz/v1/action/{type}` | `ActionRestServiceImpl` |
| `api_action_rest_service_impl_1` | GET | `/uvz/v1/action/{id}` | `ActionRestServiceImpl` |
| `api_static_content_controller_2‑5` | GET | `/web`, `/web/`, `/web/index.html`, `/web/uvz/` | `StaticContentController` |
| `api_key_manager_rest_service_impl_6` | GET | `/uvz/v1/keymanager/{groupId}/reencryptable` | `KeyManagerRestServiceImpl` |
| `api_key_manager_rest_service_impl_7` | GET | `/uvz/v1/keymanager/cryptostate` | `KeyManagerRestServiceImpl` |
| `api_archiving_rest_service_impl_8‑10` | POST / GET | `/uvz/v1/archiving/sign-submission-token`<br>`/uvz/v1/archiving/sign-reencrytion-token`<br>`/uvz/v1/archiving/enabled` | `ArchivingRestServiceImpl` |
| `api_business_purpose_rest_service_impl_11` | GET | `/businesspurposes` | `BusinessPurposeRestServiceImpl` |
| `api_deed_entry_connection_rest_service_impl_12` | GET | `/uvz/v1/deedentries/problem-connections` | `DeedEntryConnectionRestServiceImpl` |
| `api_deed_entry_log_rest_service_impl_13` | GET | `/uvz/v1/deedentries/{id}/logs` | `DeedEntryLogRestServiceImpl` |
| `api_deed_entry_rest_service_impl_14‑29` | GET / POST / PUT | Various `/uvz/v1/deedentries…` endpoints (list, create, update, bulk capture, signature folder, handover, etc.) | `DeedEntryRestServiceImpl` |

*All 30 interfaces are **synchronous REST** services; the API version (`/uvz/v1/`) is part of the URL, confirming the path‑based versioning strategy.*  

### 3.2.3 Communication protocols & data formats  

| Direction | Protocol / technology | Data format |
|-----------|-----------------------|------------|
| **Frontend → Backend** | HTTP 1.1 / HTTP 2 (REST) | JSON payloads (request bodies, responses) |
| **Backend → Database** | JDBC (PostgreSQL driver) | SQL / relational tables (executed by the 258 `sql_script` components) |
| **Backend → XNP platform** | HTTP REST (custom adapters) | JSON / proprietary XNP payloads (handled by classes in `de.bnotk.uvz.module.adapters.xnp…`) |
| **Backend → Pact‑Broker** | HTTP REST (contract testing) | Pact JSON contracts |
| **Operations → Backend (health/metrics)** | HTTP REST (Actuator) | JSON (e.g., `/actuator/health`, `/actuator/metrics`) |
| **Frontend → External static resources** | HTTP GET (served by `StaticContentController`) | HTML, CSS, JavaScript assets |

---

## 3.3 External Dependencies  

| External system | Role for **uvz** | Interaction point | Protocol |
|-----------------|------------------|-------------------|----------|
| **XNP platform** | Provides authentication, document handling, notifications and other enterprise services used by the **uvz** business logic. | Invoked from service layer through adapter classes (e.g. `XnpAuthenticationAdapter`, `XnpDocumentsEndpoint`). | HTTP REST (JSON) |
| **PostgreSQL database** | Persistent storage for all domain entities (37 entities) and supporting tables. | Accessed via Spring Data/JDBC repositories (`*DaoImpl`). | JDBC (SQL) |
| **Pact‑Broker (`broker_app` container)** | Stores consumer‑provider contract definitions; used during CI/CD to verify API compatibility. | Calls made by the test suite, not by production code. | HTTP REST (Pact JSON) |
| **Browser / End‑user devices** | Consume the Angular SPA and issue HTTP requests to the back‑end API. | Requests to `/uvz/v1/...` endpoints. | HTTP REST (JSON) |
| **Docker / container runtime** | Provides isolated execution environments for all containers. | Container orchestration via Docker‑Compose. | Docker Engine API (local) |

*All external dependencies are directly reflected in the architecture facts (containers, interfaces and design‑pattern components). No additional third‑party systems are referenced.*  