# Deployment Diagram – UVZ System

## Overview
The UVZ system is deployed as a set of Docker containers running on an Ubuntu‑based host. The deployment is **distributed** (multiple host machines) but the logical topology is a single application server that hosts all containers.

## Infrastructure Topology
| Element | Type | Technology / Image | Role |
|---------|------|--------------------|------|
| **App Server** | Virtual/physical machine | Ubuntu (Docker host) | Runs the Docker engine that hosts the `backend`, `frontend`, `broker_app` containers. |
| **backend** | Container (application) | Spring Boot (Java) | Core business logic, REST API, service layer. |
| **frontend** | Container (application) | Angular (Node.js) | SPA that serves the UI and calls the backend API. |
| **broker_app** | Container (application) | pact‑broker | Stores contract‑testing artefacts, used by CI pipelines. |
| **Database Server** | Virtual/physical machine | PostgreSQL | Persists all domain entities. |
| **postgres** | Container (database) | PostgreSQL | Database instance accessed via JDBC. |
| **User / Browser** | External actor | – | Consumes the Angular UI over HTTPS. |
| **XNP Platform** | External system | – | External REST API used by the backend for authentication and document handling. |

## Container Placement & Network Zones
- All application containers (`backend`, `frontend`, `broker_app`) run inside the **same Docker network** on the App Server, allowing internal communication over the Docker bridge.  
- The **Database Server** is placed in a separate network zone (DMZ) and is reachable from the App Server only over a secured TCP port (5432) for JDBC.  
- **External traffic** enters through a reverse‑proxy (e.g., Nginx) that terminates TLS and routes:  
  * HTTPS → `frontend` (static assets & Angular SPA)  
  * HTTPS → `backend` (REST API)  
- The **XNP Platform** is accessed directly from the `backend` container over the public internet using HTTPS.

## Scaling Strategy
- **Vertical scaling** of the App Server (increase CPU / memory) is the primary method because the system is a **Modular Monolith**.  
- Docker allows horizontal scaling of stateless containers (`frontend`, `backend`) by increasing replica counts behind the reverse‑proxy; the database remains a single instance (PostgreSQL) but could be replaced with a clustered solution if needed.  
- The `broker_app` container is typically low‑traffic and runs as a single replica.

## Communication Protocols
- User ↔ Frontend: **HTTPS** (REST UI).  
- Frontend ↔ Backend: **HTTP/HTTPS** (REST API).  
- Backend ↔ PostgreSQL: **JDBC**.  
- Backend ↔ Pact‑Broker: **HTTP** (contract testing artefacts).  
- Backend ↔ XNP Platform: **REST over HTTPS**.

## Diagram
The deployment diagram illustrating the nodes, container placement and connections is stored at:

**`c4/c4-deployment.drawio`**  

(Generated diagram shows the App Server node containing the three application containers, the separate Database Server node with the PostgreSQL container, external actors — User/Browser and XNP Platform — and the communication edges described above.)