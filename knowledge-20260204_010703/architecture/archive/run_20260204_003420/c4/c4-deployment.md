**C4 Deployment Diagram – UVZ System**

---

## Overview
The UVZ system is deployed as a set of Docker containers running on a single **Ubuntu** host. The host resides in a **DMZ (Public Zone)** that is exposed to the Internet for end‑users. All containers are orchestrated by Docker (docker‑compose) and communicate over the internal Docker network.

## Infrastructure Topology

| Element | Type | Technology / Image | Role |
|---------|------|--------------------|------|
| **Internet** | external network | – | Entry point for users. |
| **End‑User (Browser)** | actor | – | Accesses the UI via HTTPS. |
| **DMZ (Public Zone)** | network zone | – | Hosts the Docker host and exposes the UI and API to the Internet. |
| **Docker Host** | server node | Ubuntu (docker base) | Runs all containers (frontend, backend, postgres, broker_app). |
| **frontend** | container | Angular (built into an Nginx/Node image) | Serves the Angular SPA, reachable via HTTPS. |
| **backend** | container | Spring Boot (Java) | Implements the business logic and REST API (`/uvz/v1/**`). |
| **postgres** | container | PostgreSQL | Relational database for all domain entities. |
| **broker_app** | container | pact‑broker | Stores consumer‑provider contracts for contract‑testing pipelines. |

### Container Placement
All five containers (`frontend`, `backend`, `postgres`, `broker_app`, and the Docker runtime itself) are **run on the same Docker host** (`docker`). The host provides the Linux kernel, network stack and storage volumes. Docker‑compose defines the network so that:
- `frontend` ↔ `backend` communicate over HTTP/REST.  
- `backend` ↔ `postgres` communicate over JDBC/SQL.  
- `backend` ↔ `broker_app` communicate over HTTP for contract retrieval.

### Network Zones & Communication
- **External traffic**: Internet → HTTPS → `frontend` (exposed via a reverse‑proxy or directly from the container).  
- **Internal traffic**: All inter‑container traffic stays inside the Docker bridge network, isolated from the public Internet.  
- **Database access**: `backend` connects to `postgres` on the internal network; the database is not exposed externally.  
- **Contract testing**: `backend` accesses `broker_app` over HTTP on the internal network.

### Scaling Strategy
The architecture follows a **vertical scaling** approach (as indicated in the analysis). To increase capacity:
1. **Scale the Docker host** – allocate more CPU/memory to the Ubuntu VM or physical server.  
2. **Scale individual containers** (if needed) by increasing replica count in Docker‑compose/Kubernetes (future migration path). The backend, being a modular monolith, can handle higher load by adding more JVM resources.  
3. **Database scaling** – PostgreSQL can be scaled vertically or horizontally (read replicas) outside the current container setup.  
4. **Stateless frontend** – can be horizontally scaled behind a load balancer without code changes.

## Diagram
The deployment topology is visualised in the Draw.io diagram **`c4/c4-deployment.drawio`**. It shows:
- The Internet and end‑user actor.  
- The DMZ containing the Ubuntu Docker host.  
- Placement of each container inside the host.  
- Communication arrows labelled (HTTPS, HTTP/REST, JDBC/SQL, HTTP contracts).

## Architectural Context
- **Architecture Style**: *Modular Monolith* (single Spring Boot application internally layered).  
- **Primary Patterns**: Layered Architecture, Repository Pattern, Adapter Pattern (XNP integration).  
- **Quality**: High cohesion, loose coupling (≈0.15 uses/component), no layer violations, overall grade **A**.

This deployment view captures the current production‑like setup and provides a basis for future scaling or migration to a more distributed model.