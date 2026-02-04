# C4 Level 4 – Deployment View  
**System:** UVZ Deed Management System (`uvz`)  
**Documentation file:** `knowledge/architecture/c4/c4-deployment.md`  
**Diagram file:** `knowledge/architecture/c4/c4-deployment.drawio`  

---  

## 4.1 Overview  

The Deployment diagram shows **where** each container runs, the **physical / virtual infrastructure** that hosts them, and the **network topology** that connects the pieces.  
All containers are Dockerised and executed on a **single Ubuntu‑based Docker host** in the current baseline environment.  In production the host can be scaled to a cluster (Kubernetes, Swarm, or cloud‑managed nodes) without changing the logical deployment layout.  

The diagram follows the Capgemini SEAGuide C4 visual conventions:  

| Symbol | Meaning |
|--------|----------|
| **Blue rounded rectangle** | Application container (Frontend, Backend, Pact Broker) |
| **Gray rounded rectangle** | External system or infrastructure component (Keycloak, External Partner API) |
| **Cylinder** | Relational database (PostgreSQL) |
| **Person icon** | Human actor (Notary / End‑User, System Administrator) |
| **Dashed rectangle** | Network zone / logical boundary (DMZ, Application Zone, Data Zone) |
| **Arrow label** | Protocol / port used for the connection |

The diagram can be opened in **draw.io** (Diagrams.net) at the path above.

---  

## 4.2 Infrastructure Nodes  

### 4.2.1 Node Inventory  

| Node | Type | Specification / OS | Primary Purpose |
|------|------|--------------------|-----------------|
| **Docker Host** | Linux VM / physical server | Ubuntu 22.04, Docker Engine 20.10 | Hosts all Docker containers (frontend, backend, PostgreSQL, Pact Broker). |
| **Load Balancer** | Nginx (or cloud ALB) | Stateless reverse‑proxy, TLS termination | Distributes inbound HTTPS traffic to the Docker host (frontend & backend). |
| **Keycloak** | Identity Provider (container or managed service) | OIDC / OAuth2, TLS‑enabled | Central authentication & authorisation for the system. |
| **External Partner API** | Third‑party HTTP service (government / cadastral) | – | Supplies cadastral data and receives deed status updates. |
| **Internet** | External network | – | End‑users and external partners reach the system via the Load Balancer. |

> **Note:** In the current baseline the Docker host also runs the PostgreSQL and Pact Broker containers.  In a production‑grade deployment these data services can be moved to dedicated managed instances (e.g., Amazon RDS, Azure PostgreSQL) while keeping the same logical topology.

### 4.2.2 Container‑to‑Node Mapping  

| Container | Node (runtime) | Typical Instances | Resource Allocation (per instance) |
|-----------|----------------|-------------------|------------------------------------|
| **Frontend** (Angular) | Docker Host | 1 – 3 (horizontal) | 256 MiB – 512 MiB RAM, 0.2 vCPU |
| **Backend API** (Spring Boot) | Docker Host | 2 – 10 (horizontal) | 512 MiB – 2 GiB RAM, 0.5 – 2 vCPU |
| **PostgreSQL DB** | Docker Host (or managed DB) | 1 (primary) | 2 GiB – 8 GiB RAM, 2 vCPU, persistent volume |
| **Pact Broker** | Docker Host | 1 (singleton) | 256 MiB – 512 MiB RAM, 0.2 vCPU |
| **Keycloak (IdP)** | Separate container or managed service | 1 – 2 (HA) | 512 MiB RAM, 1 vCPU |
| **External Partner API** | Outside our control | – | – |

---  

## 4.3 Network Topology  

### 4.3.1 Network Zones  

| Zone | Description | Contained Elements |
|------|-------------|--------------------|
| **Internet** | Public exposure | Users, external partners |
| **DMZ** | Edge zone, TLS termination | Load Balancer (nginx/ALB) |
| **Application Zone** | Business logic & UI | Docker Host (frontend, backend, broker), Keycloak (if co‑located) |
| **Data Zone** | Persistence & contract store | PostgreSQL DB, Pact Broker (data‑store), optional cache (future) |

### 4.3.2 Firewall / Security Rules  

| Source | Destination | Port(s) | Protocol | Comment |
|--------|-------------|---------|----------|---------|
| **Internet** → **Load Balancer** | 443 | TCP | HTTPS (TLS termination) |
| **Load Balancer** → **Docker Host (frontend)** | 80 / 443 | TCP | HTTP/HTTPS static assets |
| **Load Balancer** → **Docker Host (backend)** | 8080 | TCP | Backend REST API |
| **Docker Host (frontend)** → **Docker Host (backend)** | 8080 | TCP | Internal API calls (REST/JSON) |
| **Docker Host (backend)** → **PostgreSQL** | 5432 | TCP | JDBC |
| **Docker Host (backend)** → **Keycloak** | 443 | TCP | OIDC token validation |
| **Docker Host (backend)** → **External Partner API** | 443 | TCP | External data exchange (HTTPS/JSON) |
| **Docker Host (backend)** → **Pact Broker** | 80 / 443 | TCP | Contract publishing/lookup |
| **Admin workstation** → **Load Balancer** | 443 | TCP | Administrative UI access |
| **Monitoring / CI agents** → **Docker Host** | 22 (SSH) / 8080 (metrics) | TCP | Remote logging, health checks |

---  

## 4.4 Deployment Diagram  

The full **Deployment View** diagram is stored at:  

```
knowledge/architecture/c4/c4-deployment.drawio
```

It contains:

* **Internet** → **Load Balancer** → **Docker Host** (frontend & backend)  
* **Backend** connects to **PostgreSQL**, **Pact Broker**, **Keycloak**, and **External Partner API**.  
* **Actors** (Notary / End‑User, System Administrator) linked to the Frontend.  
* **Dashed rectangles** marking **DMZ**, **Application Zone**, and **Data Zone**.  
* A **legend** explaining colour/shape conventions.

### ASCII fallback (quick visual)

```
   Internet
      |
   HTTPS 443
      v
+-------------------+
|    Load Balancer  |
|   (nginx / ALB)   |
+-------------------+
      |  (HTTP/HTTPS)
  -------------------------
  |                       |
  v                       v
+-----------+       +-----------+
| Frontend  |       | Backend   |
| (Angular) | <---> | (Spring) |
+-----------+       +-----------+
        |                 |
        | JDBC            | OIDC, HTTP
        v                 v
  +-----------+     +-----------+
  | PostgreSQL|     | Keycloak  |
  +-----------+     +-----------+
        |
        | HTTP/JSON
        v
+---------------------+
| External Partner API|
+---------------------+

(Containers run on a single Docker host; zones are indicated by dashed rectangles in the diagram.)
```

---  

## 4.5 Environment Configuration  

| Environment | Infrastructure | Container Count | Scaling | Logging / Monitoring |
|-------------|----------------|-----------------|---------|----------------------|
| **Development** | Local Docker‑Compose (single host) | 1 × frontend, 1 × backend, 1 × PostgreSQL, 1 × Pact Broker | Single instance each | Console output, DEBUG level |
| **Test / Staging** | Kubernetes cluster (3‑node) or Docker‑Swarm | Same as prod but with test‑only data sets | 2 × backend, 1 × frontend, managed PostgreSQL | Centralised ELK / Grafana, INFO level |
| **Production** | Cloud VM / Managed Kubernetes (autoscaling) | 2‑10 × backend, 1‑3 × frontend, managed PostgreSQL, High‑availability Keycloak | Auto‑scale backend on CPU > 70 %; frontend on request rate; DB vertical scaling only | Centralised log aggregation, Prometheus + Alertmanager, WARN/ERROR level |

---  

## 4.6 Scaling Strategy  

| Container | Scaling Type | Trigger | Minimum Instances | Maximum Instances |
|-----------|--------------|---------|-------------------|-------------------|
| **Backend API** | Horizontal (stateless) | CPU > 70 % or average latency > 200 ms | 2 | 10 |
| **Frontend** | Horizontal (static assets) | Requests per second > 300 rps | 1 | 3 |
| **PostgreSQL** | Vertical (single primary) | Storage / I/O pressure | 1 | 1 (scale‑out via read‑replicas in future) |
| **Pact Broker** | Fixed (low load) | – | 1 | 1 |
| **Keycloak** | Horizontal (HA) | Auth request volume > 5 k rps | 1 | 2 |

Scaling is orchestrated via the container runtime (Docker‑Compose for dev, Kubernetes HPA for prod) and monitored by Prometheus metrics exposed via Spring Actuator.

---  

## 4.7 Disaster Recovery (DR)  

| Component | Backup / Replication Strategy | Recovery Time Objective (RTO) | Recovery Point Objective (RPO) |
|-----------|------------------------------|------------------------------|--------------------------------|
| **PostgreSQL DB** | Daily automated snapshots + WAL archiving; optional streaming replica in another AZ | ≤ 4 hours (fail‑over to replica) | 24 hours (last snapshot) |
| **Docker Containers (frontend, backend, broker)** | Immutable Docker images stored in a private registry; containers can be recreated from source code in minutes | ≤ 15 minutes (container redeploy) | N/A (stateless) |
| **Keycloak** | Configuration stored in Git; state (sessions) in DB – restored from DB backup | ≤ 30 minutes | 15 minutes (session DB) |
| **Configuration / Infrastructure as Code** | All Terraform / Helm manifests version‑controlled | ≤ 10 minutes | N/A |
| **Logging / Monitoring Data** | Centralised log store with retention policy; backups to object storage | ≤ 1 hour for index recovery | 1 hour (log ingestion) |

---  

## 4.8 Summary of Key Deployment Facts  

| Item | Value |
|------|-------|
| **Containers (total)** | 5 (frontend, backend, PostgreSQL, Pact Broker, Docker host) |
| **Physical nodes** | 1 Docker host (Ubuntu 22.04) + optional external services (Keycloak, Partner API) |
| **Network zones** | DMZ → Application Zone → Data Zone |
| **Primary protocols** | HTTPS (443), HTTP (80/8080), JDBC (5432) |
| **Scaling limits** | Backend 2‑10 instances, Frontend 1‑3 instances |
| **DR coverage** | Daily DB snapshots, immutable container images, IaC versioning |

---  

## 4.9 References  

| Source | Used For |
|--------|----------|
| `architecture_facts.json` | Container definitions, tech stack, evidence of Docker‑Compose definitions. |
| `list_components_by_stereotype` (controller) | Confirmed that no additional containers are required beyond the five identified. |
| SEAGuide – C4 documentation patterns | Visual conventions, legend, zone representation. |
| Spring Boot & Angular official docs | Protocols (REST/JSON, OIDC) and typical deployment practices. |
| Docker & Kubernetes best‑practice guides | Suggested scaling & HA patterns. |

---  

*Prepared by:* **Senior Software Architect – C4 Model Expert**  
*Date:* **2026‑02‑03**