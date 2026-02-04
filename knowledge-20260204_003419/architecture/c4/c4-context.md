**C4 System Context – UVZ System**

# C4 System Context – UVZ System

## System (Black‑Box)
- **Name:** UVZ System  
- **Domain / Business Purpose:** Deed‑Entry Management Platform (creation, typing, archiving, re‑encryption, signing, hand‑over, reporting). Also provides number‑management, workflow orchestration and integration with the external **XNP** platform.

## External Actors
| Actor | Description | Interaction |
|-------|-------------|-------------|
| **End‑User (Browser)** | Human user of the application | Uses the Angular SPA via **HTTP/HTTPS** (Web UI) |
| **Other Systems** | Systems that need to integrate (e.g., reporting tools) | Calls the UVZ REST API via **HTTP (REST)** |
| **XNP Platform** | External service used for authentication, document handling, notifications, etc. | Invoked by the backend via **HTTP** adapters |

## External Systems (treated as neighbours of the black‑box)
- **PostgreSQL DB** – accessed by the backend over **JDBC/SQL**.  
- **Pact Broker** – contract‑testing repository accessed over **HTTP**.

## Communication Protocols
- **Web UI → UVZ System** – HTTP/HTTPS (Angular SPA).  
- **UVZ System → External Systems** –  
  - REST/JSON over HTTP (frontend ⇆ backend, backend ⇆ XNP).  
  - JDBC/SQL for database persistence.  
  - HTTP for contract retrieval from Pact Broker.

## Containers (Level 2) – deployed units referenced in the context diagram
| Container | Technology | Role |
|-----------|------------|------|
| **backend** | Spring Boot (Java) | Implements all business capabilities and exposes the REST API. |
| **frontend** | Angular (TypeScript) | SPA that presents the UI to end‑users. |
| **docker** | Ubuntu | Host OS for container orchestration (runtime environment). |
| **postgres** | PostgreSQL | Relational database storing domain entities. |
| **broker_app** | Pact‑Broker | Stores consumer‑provider contracts for contract testing. |

The system context diagram is available at **`c4/c4-context.drawio`**, visualising the UVZ System as a black‑box with the actors and external systems listed above.