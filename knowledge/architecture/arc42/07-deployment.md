# 7 Deployment View

## 7.1 Infrastructure Overview

```
+---------------------------+        +---------------------------+
|        Internet          |        |   CI/CD Platform (Jenkins) |
+------------+--------------+        +------------+--------------+
             |                                   |
             v                                   v
+---------------------------+        +---------------------------+
|   Load Balancer (NGINX)   |<------>|   Artifact Repository (Nexus) |
+------------+--------------+        +------------+--------------+
             |                                   |
   +---------+----------+                        |
   |                    |                        |
   v                    v                        v
+----------------+   +----------------+   +----------------+
| K8s Master     |   | K8s Worker #1  |   | K8s Worker #2  |
+----------------+   +----------------+   +----------------+
| - etcd         |   | - backend      |   | - frontend     |
| - API Server   |   | - jsApi        |   | - backend      |
| - Scheduler    |   | - import-schema|   | - jsApi        |
+----------------+   +----------------+   +----------------+
        |                     |                     |
        |                     |                     |
        v                     v                     v
+----------------+   +----------------+   +----------------+
|  Backend       |   |  Frontend      |   |  jsApi          |
|  (Spring Boot) |   |  (Angular)     |   |  (Node.js)      |
+----------------+   +----------------+   +----------------+
```

**Infrastructure Summary**
- **Kubernetes** cluster (1 master, 2 workers) hosts all runtime containers.
- **Load Balancer** (NGINX) distributes HTTP traffic to the `frontend` and `backend` services.
- **CI/CD** pipeline (Jenkins) builds Docker images from Gradle (backend) and npm (frontend, jsApi).
- **Artifact Repository** (Nexus) stores built Docker images and Maven artifacts.
- **Database** (PostgreSQL) runs on a dedicated VM in the internal zone (not shown in diagram).

## 7.2 Infrastructure Nodes

| Node                | Type                | Specification                              | Purpose                                          |
|---------------------|---------------------|--------------------------------------------|--------------------------------------------------|
| k8s-master          | Control Plane       | 4 vCPU, 8 GB RAM, SSD RAID                 | Cluster orchestration, API server, scheduler    |
| k8s-worker-1        | Worker Node         | 8 vCPU, 16 GB RAM, SSD                     | Hosts `backend`, `jsApi`, `import-schema`       |
| k8s-worker-2        | Worker Node         | 8 vCPU, 16 GB RAM, SSD                     | Hosts `frontend`, `jsApi`, `backend` (replica) |
| ci-server (Jenkins) | Build Server        | 4 vCPU, 8 GB RAM, Docker Engine            | CI pipelines, image builds, tests               |
| nexus-repo          | Artifact Repository | 2 vCPU, 4 GB RAM, 200 GB SSD storage        | Stores Maven artifacts and Docker images         |
| db-server            | Database VM         | 8 vCPU, 32 GB RAM, 500 GB SSD, PostgreSQL  | Persistent data store for all services          |
| nginx-lb            | Load Balancer       | 2 vCPU, 4 GB RAM, HAProxy/NGINX            | Entry point for external HTTP(S) traffic        |

**Container‑to‑Node Mapping**
- `backend` (Spring Boot) → `k8s-worker-1` (primary) & `k8s-worker-2` (replica)
- `frontend` (Angular) → `k8s-worker-2`
- `jsApi` (Node.js) → both workers (shared library)
- `import-schema` (Java/Gradle library) → `k8s-worker-1`
- `e2e-xnp` (Playwright) → executed on CI server during test stage

## 7.3 Container Deployment

### Docker Configuration
| Container      | Base Image                | Dockerfile Highlights |
|----------------|---------------------------|-----------------------|
| backend        | `eclipse-temurin:21-jdk`  | - Copy `build/libs/*.jar`<br>- `ENTRYPOINT ["java","-jar","/app.jar"]` |
| frontend       | `node:20-alpine`          | - `npm ci`<br>- `npm run build`<br>- Serve with `nginx` (multi‑stage) |
| jsApi          | `node:20-alpine`          | - Install dependencies<br>- Expose port 3000 |
| import-schema  | `gradle:8.5-jdk21` (builder) → `eclipse-temurin:21-jre` (runtime) | - Build library JAR<br>- No entry point (used as side‑car) |
| e2e-xnp        | `mcr.microsoft.com/playwright:focal` | - Install test scripts<br>- Run `npx playwright test` |

### Orchestration (Kubernetes)
- **Deployments**: `backend-deployment` (replicas: 2), `frontend-deployment` (replicas: 2), `jsapi-deployment` (replicas: 2), `import-schema-deployment` (replica: 1).
- **Services**:
  - `backend-svc` – ClusterIP, port 8080.
  - `frontend-svc` – NodePort (exposed via LB), port 80.
  - `jsapi-svc` – ClusterIP, port 3000.
- **ConfigMaps** & **Secrets** store environment‑specific properties (DB URL, JWT secret).
- **Ingress** (NGINX) routes `/api/**` to `backend-svc` and `/` to `frontend-svc`.

### Build Pipeline (Jenkins)
```
pipeline {
    agent any
    stages {
        stage('Checkout') { steps { git 'https://repo.example.com/project.git' } }
        stage('Build Backend') {
            steps { sh './gradlew :backend:bootJar' }
        }
        stage('Docker Build Backend') {
            steps { sh 'docker build -t registry.example.com/backend:${BUILD_NUMBER} backend/' }
        }
        stage('Build Frontend') {
            steps { sh 'npm ci && npm run build' }
        }
        stage('Docker Build Frontend') {
            steps { sh 'docker build -t registry.example.com/frontend:${BUILD_NUMBER} frontend/' }
        }
        stage('Push Images') {
            steps { sh 'docker push registry.example.com/backend:${BUILD_NUMBER}'
                    sh 'docker push registry.example.com/frontend:${BUILD_NUMBER}' }
        }
        stage('Deploy to K8s') {
            steps { sh 'kubectl set image deployment/backend-deployment backend=registry.example.com/backend:${BUILD_NUMBER}'
                    sh 'kubectl set image deployment/frontend-deployment frontend=registry.example.com/frontend:${BUILD_NUMBER}' }
        }
    }
}
```

## 7.4 Environment Configuration

| Environment | Config Source               | Key Differences |
|-------------|-----------------------------|-----------------|
| Development | `application-dev.yml` (ConfigMap) | H2 in‑memory DB, debug logging, mock external services |
| Test        | `application-test.yml` (ConfigMap) | PostgreSQL test DB, shortened time‑outs, test‑specific feature flags |
| Staging     | `application-staging.yml` (ConfigMap) | Same DB as prod (read‑only replica), feature toggles enabled for QA |
| Production  | `application-prod.yml` (Secret + ConfigMap) | PostgreSQL prod DB, TLS enabled, full logging, rate‑limit settings |

All environments share the same Docker images; only the ConfigMap/Secret values differ. The CI pipeline injects the appropriate profile (`-Dspring.profiles.active=prod`) during the production deployment stage.

## 7.5 Network Topology

```
[Internet] --> [NGINX LB (DMZ)] --> [K8s Ingress] --> [Cluster Internal Network]

Cluster Internal Network:
  - Service Mesh (Istio) optional
  - Backend ↔ DB (private subnet)
  - Frontend ↔ Backend (HTTP/2)
  - jsApi ↔ Backend (REST)

Firewall Rules:
  - DMZ → LB: allow 80/443
  - LB → Workers: allow 80/443
  - Workers → DB: allow 5432 from backend pods only
  - CI Server → Registry: allow 5000 (Docker) and 8081 (Nexus)
```

**Load‑Balancing Strategy**
- External traffic terminates at NGINX LB (round‑robin across worker nodes).
- Inside the cluster, Kubernetes Service objects provide client‑side load balancing (IPVS mode).
- Horizontal Pod Autoscaler (HPA) drives scaling based on CPU and request latency.

## 7.6 Scaling Strategy

| Container      | Scaling Type | Trigger                         | Min | Max |
|----------------|--------------|---------------------------------|-----|-----|
| backend        | Horizontal   | CPU > 70 % or avg latency > 200 ms | 2   | 8   |
| frontend       | Horizontal   | CPU > 65 % or concurrent users > 500 | 2   | 6   |
| jsApi          | Horizontal   | Queue length > 1000 messages    | 1   | 4   |
| import-schema  | Vertical     | Heap usage > 75 %                | 1   | 2   |
| e2e-xnp (test) | On‑Demand    | CI pipeline trigger             | 0   | 1   |

The scaling policies are defined as Kubernetes **HorizontalPodAutoscaler** resources (for horizontal) and **VerticalPodAutoscaler** for the `import-schema` side‑car. Autoscaling thresholds are monitored by Prometheus and visualised in Grafana dashboards.

---
*Document generated according to SEAGuide arc42 Deployment View guidelines.*