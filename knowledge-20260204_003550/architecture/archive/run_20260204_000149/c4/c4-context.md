**File:** `c4/c4-context.md`

# UVZ System – C4 System Context (Level 1)

## 1. System Overview
**System name:** **UVZ System**  
**Domain:** Management of deeds, hand‑over processes, number generation, workflow orchestration and reporting for the UVZ business domain.  
**Purpose:**  
- Exposes a REST‑based public API for CRUD operations on deed entries, archiving, signing, and token generation.  
- Provides a single‑page Angular application for user interaction.  
- Relies on supporting infrastructure containers (PostgreSQL, Docker host, Pact‑Broker) for persistence, orchestration and contract testing.

The system follows a **modular monolith** style (single deployable backend, layered internal architecture) and a **component‑based SPA** frontend.

## 2. External Actors
| Actor | Role |
|-------|------|
| **User (Web Browser)** | Consumes the Angular SPA; issues HTTP calls to the UVZ System via the browser. |
| **External Client Application** | Any external system or third‑party service that calls the public REST API (e.g., integration partners, internal micro‑services). |

## 3. External Systems / Services
| External system | Technology | Interaction |
|-----------------|------------|-------------|
| **XNP Platform (External API)** | REST/HTTPS | UVZ System calls XNP services for authentication, document handling, notifications, etc. |
| **PostgreSQL Database** | PostgreSQL | UVZ System accesses persistent data via JDBC/SQL (Spring Data JPA). |
| **Pact Broker (CI/CD)** | HTTP | Used only during development / CI pipelines for contract testing; not part of production runtime. |

## 4. Communication Protocols
| From → To | Protocol / Transport | Description |
|-----------|----------------------|-------------|
| User (Web Browser) → UVZ System | **HTTPS / REST (JSON)** | Loads the Angular SPA and performs API calls. |
| External Client Application → UVZ System | **HTTPS / REST (JSON)** | Invokes business‑logic endpoints (e.g., `/uvz/v1/deedentries`). |
| UVZ System → XNP Platform | **HTTPS / REST (JSON)** | Calls XNP integration services (auth, document, notification). |
| UVZ System → PostgreSQL Database | **JDBC / SQL** | Persists and queries domain entities. |
| UVZ System → Pact Broker | **HTTP** | Publishes/consumes contract definitions for testing. |

## 5. Diagram
The system context diagram is provided in the file **`c4/c4-context.drawio`**.  
It visualises the UVZ System as a black‑box surrounded by the external actors and systems listed above, together with the communication protocols.

---  

*All names, containers, and interfaces are taken directly from the architecture facts; the architectural style and quality assessments are derived from the analyzed architecture data.*