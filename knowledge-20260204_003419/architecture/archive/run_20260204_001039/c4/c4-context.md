**C4 Level 1 – System Context Documentation**

The system‑context artifacts have been generated and stored in the repository:

- **Markdown description:** `knowledge/architecture/c4/c4-context.md`  
- **Draw.io diagram:** `knowledge/architecture/c4/c4-context.drawio`

Below is the complete content of the markdown file for quick reference.

---

# System Context – UVZ System

## System Boundary
- **System Name:** `uvz`
- **Description:** A domain‑centric application that manages deeds, hand‑overs, successor information, number allocation and workflow processing. It provides a comprehensive REST API for clients and integrates with an external XNP platform.
- **Architecture Style:** Modular Monolith (single Spring‑Boot backend, Angular SPA front‑end).

## External Actors
| Actor | Role |
|-------|------|
| **User (Web Browser)** | Interacts with the system via the Angular front‑end and the public REST API (HTTP/HTTPS). |
| **Admin** | Performs administrative tasks through the same REST API (HTTP/HTTPS). |
| **XNP Platform** | External service used for authentication, document handling and notifications (accessed via REST from the backend). |

## External Systems
| System | Technology | Relationship |
|--------|------------|--------------|
| **PostgreSQL Database** | PostgreSQL | Backend accesses data via JDBC. |
| **Pact Broker** | HTTP (pact‑broker) | Used for contract‑testing artefacts. |
| **XNP Platform** | REST/HTTP | Backend calls external APIs for integration. |

## Containers (Deployable Units)
| Container | Type | Technology | Evidence |
|-----------|------|------------|----------|
| `backend` | application | Spring Boot | `ev_container_0001` |
| `frontend` | application | Angular | `ev_container_0002` |
| `docker` | application | Ubuntu | `ev_docker_0001` |
| `postgres` | database | PostgreSQL | `ev_compose_0002` |
| `broker_app` | application | pact‑broker | `ev_compose_0003` |

## Communication Protocols
- **User ↔ System:** HTTP/HTTPS (REST API, served by Angular SPA and Spring Boot controllers).  
- **System ↔ PostgreSQL:** JDBC over TCP.  
- **System ↔ Pact Broker:** HTTP.  
- **System ↔ XNP Platform:** REST over HTTP.

## Diagram
The System Context diagram visualising the system as a black box with the actors, external systems and communication links is stored as **`c4/c4-context.drawio`**.

--- 

All artifacts are now ready for inclusion in the architecture documentation.