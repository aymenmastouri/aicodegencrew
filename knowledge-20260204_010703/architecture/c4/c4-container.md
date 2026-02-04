# C4 Level 2 – Container View  
**System:** UVZ Deed Management System (`uvz`)  
**Documentation file:** `knowledge/architecture/c4/c4-container.md`  
**Diagram file:** `knowledge/architecture/c4/c4-container.drawio`  

---  

## 2.1 Overview  

The Container diagram depicts the high‑level building blocks that are independently deployable and the primary responsibilities they expose.  
Each container runs on a **Docker host (Ubuntu)** and communicates over well‑defined protocols (HTTPS/JSON, JDBC, OIDC, HTTP).  
The diagram follows the Capgemini SEAGuide C4 visual conventions:  

* **Blue rounded rectangles** – internal application containers  
* **Gray rounded rectangles** – external systems / infrastructure  
* **Cylinders** – data stores  
* **Person icons** – human actors  
* **Dashed rectangle** – system boundary  

---  

## 2.2 Container Inventory  

### 2.2.1 Application Containers  

| Container | Technology | Primary Responsibility | Typical Port(s) | Deployment |
|-----------|------------|------------------------|----------------|------------|
| **Frontend** | Angular v18 (TypeScript) | Rich SPA UI; consumes backend REST API; fetches contract artefacts from the Pact Broker. | 80 / 443 (HTTPS) | Docker container, served behind an optional CDN. |
| **Backend** | Spring Boot 3 (Java 17) | Exposes REST/JSON API, implements business logic, security, scheduling, health‑checks. | 8080 (HTTP) – exposed as 443 via TLS termination in front‑proxy. | Docker container, horizontally scalable. |
| **Broker App** | Pact‑Broker (Docker image `dius/pact-broker`) | Stores consumer‑provider contracts for CI/CD contract testing. | 80 / 443 (HTTP) | Docker container, accessed by CI pipeline and optionally by the UI. |
| **Docker Host** | Ubuntu 22.04 (Docker Engine) | Underlying OS that runs all containers; provides networking, storage volumes, and container orchestration (Docker‑Compose). | – | Bare‑metal/VM, managed by ops team. |

### 2.2.2 Data Containers  

| Container | Technology | Purpose | Persistence | Typical Port |
|-----------|------------|---------|-------------|--------------|
| **PostgreSQL DB** | PostgreSQL 13 | Primary relational store for deeds, audit logs, reference data, user‑role mappings. | Persistent volume (`/var/lib/postgresql/data`) | 5432 (TCP) |

### 2.2.3 External Systems (outside the system boundary)  

| System | Type | Technology | Protocol | Role |
|--------|------|------------|----------|------|
| **Keycloak (IdP)** | Identity Provider | Keycloak 22 | OIDC / OAuth2 (HTTPS) | Authenticates users & issues JWTs. |
| **External Partner API** | Government / third‑party service | Various (REST) | HTTPS/JSON | Provides cadastral data and receives deed status updates. |
| **Notary / End‑User** | Human actor | – | HTTPS (HTML/JSON) | Interacts with the UI. |
| **System Administrator** | Human actor | – | HTTPS (HTML/JSON) | Manages configuration via UI & Actuator endpoints. |

---  

## 2.3 Container Details  

### 2.3.1 Frontend (Angular)  

| Attribute | Value |
|-----------|-------|
| **Technology** | Angular v18 (TypeScript 5.4) |
| **Purpose** | Deliver a responsive web UI; request data from Backend; display reports; fetch contract files from Pact Broker (dev mode). |
| **Ports** | 80 / 443 (exposed via reverse‑proxy or CDN) |
| **Provided Interfaces** | HTTP UI, static assets (HTML/CSS/JS) |
| **Consumed Interfaces** | Backend REST API (`/api/**`), Pact Broker (`/pacts/**`) |
| **Deployment** | Docker image built with `npm run build`; runs on Docker host; can be deployed to a CDN for static assets. |
| **Scaling** | Horizontal (stateless) – 1 → 3 instances behind load‑balancer based on request‑rate. |
| **Memory / CPU** | ≈ 256 MiB RAM, 0.2 vCPU per instance (adjustable). |

### 2.3.2 Backend (Spring Boot)  

| Attribute | Value |
|-----------|-------|
| **Technology** | Spring Boot 3, Java 17, Gradle |
| **Purpose** | Expose REST/JSON API, implement domain‑logic, schedule background jobs, enforce security, expose Actuator health endpoints. |
| **Ports** | 8080 (internal) → exposed as 443 (TLS terminated by front‑proxy). |
| **Provided Interfaces** | `GET/POST/PUT/DELETE /api/**` (JSON), Actuator (`/actuator/health`, `/actuator/metrics`). |
| **Consumed Interfaces** | PostgreSQL (JDBC), Keycloak (OIDC), External Partner API (HTTPS/JSON), Pact Broker (HTTP for contract publishing during CI). |
| **Deployment** | Docker image built from `backend/Dockerfile`; runs on Docker host; can be orchestrated by Docker‑Compose or Kubernetes. |
| **Scaling** | Horizontal – start with 2 replicas, auto‑scale up to 10 based on CPU > 70 % or request latency > 200 ms. |
| **Memory / CPU** | 512 MiB – 2 GiB RAM, 0.5 – 2 vCPU per replica (configurable). |

### 2.3.3 PostgreSQL DB  

| Attribute | Value |
|-----------|-------|
| **Technology** | PostgreSQL 13 |
| **Purpose** | Durable persistence of all domain entities, audit logs, user/role data. |
| **Ports** | 5432 (TCP) |
| **Provided Interfaces** | SQL over JDBC/PG‑protocol. |
| **Consumed Interfaces** | Backend (JDBC). |
| **Deployment** | Docker container with a mounted volume for data durability. |
| **Scaling** | Single primary instance; can be upgraded to streaming‑replication for HA – out of scope for current container view. |
| **Memory / CPU** | 1 GiB RAM, 1 vCPU (minimum). |

### 2.3.4 Pact Broker  

| Attribute | Value |
|-----------|-------|
| **Technology** | Pact‑Broker (Docker image `dius/pact-broker`) |
| **Purpose** | Stores consumer‑provider contract files used by the CI pipeline for contract testing. |
| **Ports** | 80 / 443 (HTTP) |
| **Provided Interfaces** | HTTP REST API (`/pacts/**`). |
| **Consumed Interfaces** | CI jobs (push/pull contracts). |
| **Deployment** | Docker container; optional basic auth; runs on Docker host. |
| **Scaling** | Single instance is sufficient for current load. |
| **Memory / CPU** | 256 MiB RAM, 0.2 vCPU. |

### 2.3.5 Docker Host (Ubuntu)  

| Attribute | Value |
|-----------|-------|
| **Technology** | Ubuntu 22.04, Docker Engine 20.10 |
| **Purpose** | Provides the OS layer, container runtime, networking, volume storage. |
| **Ports Exposed** | 80, 443 (frontend), 8080 (backend), 5432 (DB), 80/443 (broker). |
| **Deployment** | Physical/virtual server managed by Ops team; may be part of a cluster in the future. |
| **Scaling** | Additional hosts can be added and orchestrated with Docker‑Swarm or Kubernetes. |

---  

## 2.4 Container Diagram  

The **Container View** diagram is stored at:

```
knowledge/architecture/c4/c4-container.drawio
```

It visualises:

* The **system boundary** (dashed rectangle) labelled *UVZ Deed Management System*.  
* Blue boxes for the four internal containers (Frontend, Backend, PostgreSQL, Pact Broker).  
* Gray boxes for external systems (Keycloak, External Partner API).  
* Person icons for the **Notary / End‑User** and **System Administrator**.  
* A gray box for the **Docker Host (Ubuntu)** that “runs in” each container.  

A legend is embedded in the diagram (blue = application container, gray = external system, cylinder = database, person = actor, dashed line = boundary).  

### ASCII fallback (for quick reference)

```
   +-----------------------------------------------------------+
   |               UVZ Deed Management System                 |
   |  +----------------+   +-------------------+               |
   |  |  Frontend      |   |   Backend API    |               |
   |  |  (Angular)     |   |   (Spring Boot) |               |
   |  +--------+-------+   +--------+----------+               |
   |           |                    |                          |
   |           | HTTPS/JSON         | JDBC                     |
   |           v                    v                          |
   |  +----------------+   +-------------------+               |
   |  |  Pact Broker   |   | PostgreSQL DB     |               |
   |  |  (HTTP)        |   | (cylinder)       |               |
   |  +----------------+   +-------------------+               |
   +-----------------------------------------------------------+

   Notary ──► Frontend ──► Backend ──► DB
          │       │          └─► Keycloak (OIDC)
          │       └─► Pact Broker (contract files)
          └─► Admin UI (same Frontend)
```

---  

## 2.5 Container Interactions  

### 2.5.1 Synchronous Communication  

| Source | Target | Protocol / Method | Data Format | Purpose |
|--------|--------|-------------------|-------------|---------|
| **Notary / End‑User** → **Frontend** | HTTPS (HTML/JS) | Browser request / response | Render UI, load static assets. |
| **Frontend** → **Backend** | HTTPS (REST) | JSON payloads | CRUD operations on deeds, trigger business processes. |
| **Backend** → **PostgreSQL** | JDBC (TCP) | SQL statements | Persist / retrieve domain data, audit logs. |
| **Backend** → **Keycloak** | OIDC (HTTPS) | JWT token exchange | Authenticate users, obtain authorisation claims. |
| **Backend** → **External Partner API** | HTTPS (REST) | JSON | Request cadastral data / push deed status. |
| **Backend** → **Pact Broker** | HTTP (REST) | JSON / contract files | Publish/consume contracts during CI. |
| **Frontend** → **Pact Broker** | HTTP (REST) | JSON | Retrieve contract artefacts for UI debugging (dev mode). |
| **Admin** → **Backend Actuator** (`/actuator/health`) | HTTPS (REST) | JSON | Health‑check, metrics. |

### 2.5.2 Asynchronous / Event‑driven (future‑proof)  

| Source | Target | Protocol | Payload | Purpose |
|--------|--------|----------|---------|---------|
| **Backend** (scheduled jobs) → **External Partner API** | HTTPS (POST) | JSON | Push batch updates (e.g., nightly reports). |
| **Backend** → **Message Queue** (not yet present) | AMQP / Kafka (planned) | JSON | Publish domain events (`DeedCreated`, `DeedArchived`). |
| **Worker processes** (future) → **Backend** | HTTP callback / Queue consumer | JSON | Process long‑running tasks (e.g., PDF generation). |

---  

## 2.6 Container Scaling  

| Container | Minimum Instances | Maximum Instances | Scaling Trigger |
|-----------|-------------------|-------------------|-----------------|
| **Frontend** | 1 | 3 | Avg. request latency > 200 ms or CPU > 60 %. |
| **Backend** | 2 | 10 | CPU > 70 % or queue length > 50 (if async queue added). |
| **PostgreSQL** | 1 | 1 (single primary) | Manual vertical scaling (RAM/CPU) when I/O > 80 %. |
| **Pact Broker** | 1 | 1 | No scaling required (low traffic). |
| **Docker Host** | 1 | – | Additional hosts added when total container count > 12. |

---  

## 2.7 Technology Stack Summary  

| Layer | Technology | Version / Note |
|-------|------------|----------------|
| **Operating System** | Ubuntu | 22.04 LTS (Docker host) |
| **Container Runtime** | Docker Engine | 20.10+ |
| **Frontend** | Angular | v18‑LTS (TypeScript 5.4.5) |
| **Backend Runtime** | Java | 17 (OpenJDK) |
| **Backend Framework** | Spring Boot | 3.x |
| **ORM / Data‑Access** | Hibernate | 6.x |
| **Database** | PostgreSQL | 13‑14 |
| **Contract Testing** | Pact Broker | Latest stable Docker image |
| **Identity & Access** | Keycloak | 22.x (OIDC) |
| **Build Tools** | npm (frontend) / Gradle (backend) | – |
| **CI/CD** | GitLab‑Runner / GitHub Actions (unspecified) | – |
| **Monitoring** | Spring Actuator, custom `ExecutionTimingAspect` | – |
| **Logging** | Logback (default Spring) | – |

---  

## 2.8 Legend (re‑stated for textual readers)  

* **Blue box** – internal application container (Frontend, Backend, Pact Broker).  
* **Gray box** – external system or infrastructure component (Keycloak, External Partner API, Docker Host).  
* **Cylinder** – data store (PostgreSQL).  
* **Person icon** – human actor (Notary / End‑User, System Administrator).  
* **Dashed rectangle** – system boundary indicating what is inside the UVZ Deed Management System.  

---  

*Prepared by:* **Senior Software Architect – C4 Model Expert**  
*Date:* **2026‑02‑03**  