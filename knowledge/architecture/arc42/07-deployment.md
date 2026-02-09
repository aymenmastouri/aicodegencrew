# 07 Deployment View

## 7.1 Infrastructure Overview

```
+---------------------------+        +---------------------------+
|   Kubernetes Cluster     |        |   CI/CD Pipeline (Jenkins) |
|  (3 Worker Nodes)       |        |   - Build & Test          |
|                         |        |   - Docker Image Build    |
+-----------+-------------+        +-----------+---------------+
            |                                 |
            |                                 |
            v                                 v
+---------------------------+   +---------------------------+
|   Ingress Controller      |   |   Artifact Repository      |
|   (NGINX)                 |   |   (Harbor)                |
+-----------+---------------+   +-----------+---------------+
            |                                 |
            |                                 |
            v                                 v
+---------------------------+   +---------------------------+
|   Backend Service (Docker) |   |   Frontend Service (Docker) |
|   container.backend       |   |   container.frontend        |
+-----------+---------------+   +-----------+---------------+
            |                                 |
            |                                 |
            v                                 v
+---------------------------+   +---------------------------+
|   Database (PostgreSQL)   |   |   Cache (Redis)           |
+---------------------------+   +---------------------------+
```

**Infrastructure Summary**
- **Kubernetes** orchestrates all runtime containers (backend, frontend, jsApi). 
- **Ingress** (NGINX) exposes HTTP(S) endpoints for the Angular UI and the Spring Boot REST API.
- **CI/CD** (Jenkins) builds Java/Gradle and Node.js artefacts, creates Docker images and pushes them to Harbor.
- **PostgreSQL** stores domain entities (≈360) and audit logs.
- **Redis** provides session caching for the UI and token storage for the backend.
- **Playwright** test container (`e2e‑xnp`) runs in the CI pipeline for end‑to‑end UI verification.
- **Import‑schema** library is packaged as a thin Docker image used by batch jobs.

## 7.2 Infrastructure Nodes

| Node | Type | Specification | Purpose |
|------|------|---------------|---------|
| k8s‑master-01 | Control Plane | 4 vCPU, 8 GB RAM | API server, scheduler, etcd
| k8s‑worker‑a | Worker | 8 vCPU, 32 GB RAM | Runs backend, frontend, jsApi containers
| k8s‑worker‑b | Worker | 8 vCPU, 32 GB RAM | Runs e2e‑xnp, import‑schema, auxiliary jobs
| ingress‑nginx‑01 | Ingress | 2 vCPU, 4 GB RAM | TLS termination, routing
| postgres‑01 | Database | 4 vCPU, 16 GB RAM, 500 GB SSD | Persistent storage for domain data
| redis‑01 | Cache | 2 vCPU, 4 GB RAM | Session & token cache
| jenkins‑ci | CI/CD Server | 8 vCPU, 16 GB RAM | Build, test, Docker image creation
| harbor‑repo | Artifact Registry | 4 vCPU, 8 GB RAM | Stores Docker images

**Container‑to‑Node Mapping**
- `container.backend` → `k8s‑worker‑a`
- `container.frontend` → `k8s‑worker‑a`
- `container.jsApi` → `k8s‑worker‑a`
- `container.e2e‑xnp` → `k8s‑worker‑b` (executed as a Job)
- `container.import‑schema` → `k8s‑worker‑b` (batch Job)

## 7.3 Container Deployment

### Docker Configuration
| Container | Base Image | Build Tool | Dockerfile Highlights |
|-----------|------------|------------|----------------------|
| backend | `eclipse-temurin:21-jdk` | Gradle | `COPY src /app/src` `RUN ./gradlew bootJar` `EXPOSE 8080` |
| frontend | `node:20-alpine` | npm | `WORKDIR /app` `COPY package*.json ./` `RUN npm ci` `COPY . .` `RUN npm run build` `EXPOSE 80` |
| jsApi | `node:20-alpine` | npm | Same as frontend, but `npm run build:jsapi` |
| e2e‑xnp | `mcr.microsoft.com/playwright:latest` | npm | `RUN npx playwright install` `COPY tests /tests` `CMD npx playwright test` |
| import‑schema | `eclipse-temurin:21-jdk` | Gradle | `RUN ./gradlew assemble` `CMD java -jar import-schema.jar` |

### Orchestration (Kubernetes)
- **Namespace**: `uvz-prod`
- **Deployments**: one replica for `frontend`, three replicas for `backend` (high availability), one replica for `jsApi`.
- **StatefulSet**: `postgres‑01` with persistent volume claim (500 GB).
- **ConfigMaps** & **Secrets**: hold `application‑properties`, TLS certificates, DB credentials.
- **Helm Chart**: `uvz‑chart` packages all manifests, values file defines image tags per environment.

### Build Pipeline (Jenkins)
1. **Checkout** source from Git.
2. **Unit Tests** – `./gradlew test` (backend) & `npm test` (frontend).
3. **Static Code Analysis** – SonarQube.
4. **Docker Build** – `docker build` for each container, tag with `git‑commit‑sha`.
5. **Push** images to Harbor.
6. **Helm Upgrade** – `helm upgrade --install uvz-prod ./helm/uvz‑chart --namespace uvz-prod`.
7. **Smoke Tests** – Deploy to a temporary namespace, run health‑check endpoints.

## 7.4 Environment Configuration

| Environment | Kubernetes Namespace | Image Tag | DB URL | Feature Flags |
|-------------|----------------------|----------|--------|---------------|
| Development | `uvz-dev` | `latest‑snapshot` | `jdbc:postgresql://postgres-dev:5432/uvz` | `debug=true, mockKm=true` |
| Test | `uvz-test` | `rc‑20231115` | `jdbc:postgresql://postgres-test:5432/uvz` | `mockKm=false, audit=true` |
| Staging | `uvz-staging` | `release‑1.2.0` | `jdbc:postgresql://postgres-stg:5432/uvz` | `featureX=enabled` |
| Production | `uvz-prod` | `release‑1.2.0` | `jdbc:postgresql://postgres-prod:5432/uvz` | `featureX=enabled, monitoring=full` |

**Environment‑Specific Settings**
- **Spring profiles** (`dev`, `test`, `staging`, `prod`) select `application‑{profile}.yml`.
- **Angular environment files** (`environment.dev.ts`, etc.) inject API base URLs.
- **Secrets** are stored in Kubernetes `Secret` objects and referenced as environment variables.
- **Resource limits** differ per environment (e.g., lower CPU limits in dev).

## 7.5 Network Topology

```
[Internet] --> [Ingress (NGINX)] --> [Load Balancer]
                                   |
          +------------------------+------------------------+
          |                        |                        |
   [frontend Service]      [backend Service]        [jsApi Service]
          |                        |                        |
   (NodePort 80)          (ClusterIP 8080)          (ClusterIP 8081)
```

- **Zones**: `DMZ` (Ingress), `App` (Kubernetes workers), `DB` (PostgreSQL, Redis).
- **Firewall Rules**: only Ingress allowed from Internet; workers can talk to DB and Redis on internal network; CI server can push images to Harbor.
- **Load Balancing**: NGINX performs round‑robin across backend pods; frontend is served via a static‑file cache (nginx) with HTTP/2.

## 7.6 Scaling Strategy

| Container | Scaling Type | Trigger | Min Replicas | Max Replicas |
|-----------|--------------|---------|--------------|--------------|
| backend | Horizontal Pod Autoscaler (CPU) | CPU > 70% | 2 | 6 |
| frontend | Horizontal Pod Autoscaler (Requests) | HTTP requests > 500/s | 1 | 4 |
| jsApi | Horizontal Pod Autoscaler (Memory) | Memory > 80% | 1 | 3 |
| e2e‑xnp | Job (on‑demand) | CI pipeline trigger | 0 | 1 |
| import‑schema | Job (cron) | Nightly schedule | 0 | 1 |

**Rationale**: Backend is the core processing engine and must handle peak load during batch imports; frontend scales with user traffic; jsApi is lightweight but benefits from memory‑based scaling. Jobs run on demand and do not require permanent replicas.

---
*Document generated automatically from architecture facts (951 components, 5 containers, 196 REST endpoints).*
