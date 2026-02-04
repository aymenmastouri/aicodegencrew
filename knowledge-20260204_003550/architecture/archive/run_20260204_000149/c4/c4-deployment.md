**File:** `c4/c4-deployment.md`

# UVZ System – C4 Deployment Diagram (Level 4)

## 1. Deployment Overview  

The UVZ System is deployed on a **single Ubuntu host** that runs a Docker Engine. All runtime units are packaged as Docker containers and started via a Docker‑Compose file (the same file that defines the `postgres` and `broker_app` services).  

The deployment consists of the following containers (exact names taken from **architecture_facts.json**):

| Container ID | Technology | Role |
|--------------|------------|------|
| **backend** | Spring Boot (Java, Gradle) | Hosts the public REST API, contains the full business‑logic layer (controllers, services, repositories) and connects to the database and the Pact broker. |
| **frontend** | Angular (TypeScript, npm) | Serves the single‑page application to end‑users. |
| **postgres** | PostgreSQL | Relational database storing all domain entities. |
| **broker_app** | pact‑broker | Holds consumer‑provider contract definitions used in CI/CD pipelines. |
| **docker** (host) | Ubuntu (docker‑engine) | The underlying OS that runs Docker and therefore all containers. |

## 2. Physical Layout & Network Zones  

```
+-----------------------------------------------------------+
|                      Ubuntu Host (docker)                |
|  +-------------------+  +------------------------------+ |
|  | Docker Engine     |  | Host OS (Ubuntu)             | |
|  |                   |  |                              | |
|  |  +-------------+  |  |  Network Zones               | |
|  |  |  Frontend   |  |  |  ------------------------   | |
|  |  |  (frontend) |  |  |  DMZ – exposed to browsers | |
|  |  +-------------+  |  |                              | |
|  |                   |  |  +------------------------+  | |
|  |  +-------------+  |  |  |  Backend (backend)   |  | |
|  |  |  Backend    |  |  |  (REST API, internal) |  | |
|  |  |  (backend)  |  |  +------------------------+  | |
|  |  +-------------+  |  |                              | |
|  |                   |  |  +------------------------+  | |
|  |  +-------------+  |  |  |  PostgreSQL (postgres) |  | |
|  |  |  Broker     |  |  |  (internal DB)         |  | |
|  |  |  (broker_app) | |  +------------------------+  | |
|  |  +-------------+  |  +------------------------------+ |
|  +-------------------+                                   |
+-----------------------------------------------------------+
```

* **DMZ (Demilitarized Zone)** – The `frontend` container is the only component reachable from the Internet (or from the corporate intranet). It serves static files over HTTPS and calls the `backend` REST API.  
* **Internal Zone** – `backend`, `postgres`, and `broker_app` reside in a protected internal network. They communicate only with each other and are not exposed directly to external clients.  
* **Host OS** – Provides the Docker Engine, networking and storage (volumes for PostgreSQL data and Pact‑Broker persistence).  

## 3. Container Placement & Inter‑Container Communication  

| Source → Target | Protocol / Transport | Reason |
|-----------------|----------------------|--------|
| **frontend → backend** | HTTPS / REST (JSON) | UI consumes public API endpoints (e.g., `/uvz/v1/deedentries`). |
| **backend → postgres** | JDBC / SQL | Persists and queries domain entities via Spring Data JPA. |
| **backend → broker_app** | HTTP | Retrieves / publishes contract definitions during CI/CD runs. |
| **Docker Engine → each container** | Docker‑Compose orchestration | Starts containers, manages lifecycle, networking, and volume mounting. |
| **Host → Docker Engine** | System‑level (docker daemon) | Host runs Docker Engine; containers share the host kernel. |

All containers share a Docker bridge network defined in the `docker‑compose.yml` (implicit from the evidence). No port‑mapping is required for internal traffic; only the `frontend` (port 80/443) and optionally the `backend` (if external debugging is needed) are published to the host.

## 4. Scaling Strategy  

* **Vertical scaling (primary)** – The architecture analysis (`analyzed_architecture.json`) indicates a **vertical** scalability approach. Increasing CPU, memory, or I/O resources on the Ubuntu host will directly benefit all containers.  

* **Horizontal scaling (optional)** – While not present in the current Docker‑Compose setup, the container images are stateless (except for PostgreSQL).  
  * **Backend** – Could be replicated behind a load‑balancer (e.g., Nginx or HAProxy) to distribute HTTP traffic. Session‑state is stored in the database or external cache, so multiple instances are feasible.  
  * **Frontend** – Static assets can be served from multiple containers or moved to a CDN for better scalability.  
  * **PostgreSQL** – Requires a dedicated clustering solution (e.g., Patroni, streaming replication) to scale reads; write‑scaling would need sharding – outside the current monolithic design.  

* **Container orchestration** – For production, replacing Docker‑Compose with Kubernetes or Docker Swarm would simplify scaling, health‑checking and rolling updates. The existing `Dockerfile`s and images are already compatible.

## 5. Operational Concerns  

| Concern | Current Status | Recommendations |
|---------|----------------|-----------------|
| **Health checks** | Implemented via Spring Boot Actuator (`HealthCheck` service) | Expose `/actuator/health` and `/actuator/metrics` to the orchestration layer; configure Docker health‑check directives. |
| **Logging & Monitoring** | Basic SLF4J/Logback; Actuator metrics present | Forward logs to a centralized system (ELK/EFK) and scrape metrics with Prometheus; add dashboards in Grafana. |
| **Configuration** | Externalized via Spring `@ConfigurationProperties` and Angular environment files | Store secrets in a vault (e.g., HashiCorp Vault) and inject via Docker secrets or environment variables. |
| **Backup & Recovery** | PostgreSQL data persisted via Docker volume | Implement scheduled logical/physical backups and test restore procedures. |
| **Security** | Spring Security enabled; mock authentication present for dev | Replace mock auth with production‑grade provider (OAuth2/JWT); enforce TLS termination at the host or a reverse‑proxy. |

## 6. Summary  

The deployment diagram (see `c4/c4-deployment.drawio`) visualises a **single‑host Docker‑based deployment** with five containers, clear network zoning, and straightforward vertical scaling. The design aligns with the **Modular Monolith** style identified in the analysis and provides a solid foundation for future horizontal scaling and migration to a more sophisticated orchestration platform if required.