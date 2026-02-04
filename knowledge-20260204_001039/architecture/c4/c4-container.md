**C4 Container Documentation – UVZ System**

---

### Container Diagram – Markdown (`c4/c4-container.md`)

```markdown
# Container Diagram – UVZ System

## Overview
The UVZ system is composed of five deployable containers. The diagram shows how they interact through various protocols.

## Containers
| Container | Type | Technology | Evidence |
|-----------|------|------------|----------|
| `backend`   | application | Spring Boot   | `ev_container_0001` |
| `frontend`  | application | Angular       | `ev_container_0002` |
| `docker`    | application | Ubuntu        | `ev_docker_0001` |
| `postgres`  | database    | PostgreSQL    | `ev_compose_0002` |
| `broker_app`| application | pact‑broker   | `ev_compose_0003` |

## External Services
| Service | Technology | Relationship |
|---------|------------|--------------|
| **XNP Platform** | REST/HTTP (External API) | Called by `backend` for authentication, document handling, notifications. |

## Communication Protocols
- **Frontend ↔ Backend:** HTTP/HTTPS (REST API) – Angular SPA consumes Spring Boot controllers.  
- **Backend ↔ PostgreSQL:** JDBC over TCP.  
- **Backend ↔ Pact Broker:** HTTP – contract‑testing artefacts.  
- **Backend ↔ XNP Platform:** REST over HTTP – external integration.

## Diagram
The container diagram visualising these relationships is stored as **`c4/c4-container.drawio`**.
```

---

### DrawIO Diagram (`c4/c4-container.drawio`)

The diagram file has been generated and saved at:

```
knowledge/architecture/c4/c4-container.drawio
```

It contains the following elements:

- **Nodes**
  - `backend` (Spring Boot) – hexagon shape
  - `frontend` (Angular) – hexagon shape
  - `postgres` (PostgreSQL) – database shape
  - `broker_app` (pact‑broker) – component shape
  - `XNP Platform` (External API) – component shape

- **Edges**
  - Frontend → Backend: **HTTP/HTTPS REST API**
  - Backend → PostgreSQL: **JDBC**
  - Backend → Pact‑Broker: **HTTP**
  - Backend → XNP Platform: **REST**

These artifacts constitute the complete C4 **Container** level documentation for the UVZ system.