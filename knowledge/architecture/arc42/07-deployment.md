# 07 - Deployment View

## 7.1 Infrastructure Overview

The **uvz** system is deployed as a set of four logical containers that run on a Kubernetes‑based cloud platform (or on‑premise VMs – the architecture is technology‑agnostic).  The containers are:

| Container ID | Technology | Role | Component Count |
|--------------|------------|------|-----------------|
| `container.backend` | Spring Boot (Java, Gradle) | Core business‑logic micro‑service – exposes 95 REST endpoints, hosts all controllers, services, repositories and the single configuration component. | 333 |
| `container.frontend` | Angular (npm) | Single‑page web UI – consumes the backend REST API, runs in the browser. | 404 |
| `container.e2e_xnp` | Playwright (npm) | End‑to‑end test harness – executes UI tests against the frontend and backend in CI pipelines. | 0 |
| `container.import_schema` | Java/Gradle library | Build‑time schema import utility – not part of the runtime but packaged with the backend. | 0 |

The deployment diagram (text‑based) shows the high‑level topology:

```
+-------------------+        +-------------------+        +-------------------+
|   Frontend (NG)   |  HTTPS |   Backend (SB)    |  JDBC  |   Database (RDB) |
| container.frontend| <----> | container.backend | <----> |   PostgreSQL      |
+-------------------+        +-------------------+        +-------------------+
        ^                         ^
        |                         |
        |   +-------------------+ |
        +---|   E2E Tests (PW)  | |
            container.e2e_xnp   |
            +-------------------+
```

*All containers are placed behind a TLS‑terminating ingress controller.  The backend connects to a managed PostgreSQL instance via a private network.  The e2e‑xnp container runs in a separate CI namespace and accesses the frontend through the same ingress.

---

## 7.2 Infrastructure Nodes

| Node | Type | Specification | Purpose |
|------|------|---------------|---------|
| **Ingress Controller** | Software (NGINX/Traefik) | 2 vCPU, 2 GB RAM, TLS termination, rate‑limiting | Exposes HTTPS endpoints for frontend and backend, routes traffic based on path prefixes. |
| **Kubernetes Worker** | VM (Linux) | 4 vCPU, 8 GB RAM, SSD storage | Hosts the four containers; provides pod scheduling, health‑checks, and auto‑scaling. |
| **PostgreSQL Instance** | Managed DB service | 8 vCPU, 32 GB RAM, 500 GB SSD, automated backups | Persists domain entities (199 entity classes) and audit logs. |
| **Object Storage** | S3‑compatible bucket | 5 TB capacity, versioning enabled | Stores archived document binaries used by the `ArchiveStorageService`. |
| **CI Runner** | Container host | 2 vCPU, 4 GB RAM | Executes the `container.e2e_xnp` Playwright tests on each pull request. |
| **Artifact Registry** | Docker registry | Unlimited | Holds Docker images for `backend`, `frontend`, and `import‑schema`. |

---

## 7.3 Container Deployment

### Docker Images

| Container | Image Repository | Tag | Build System |
|-----------|------------------|-----|--------------|
| `backend` | `registry.company.com/uvz/backend` | `{{git.sha}}` | Gradle (Spring Boot) |
| `frontend` | `registry.company.com/uvz/frontend` | `{{git.sha}}` | npm (Angular CLI) |
| `e2e_xnp` | `registry.company.com/uvz/e2e-xnp` | `latest` | npm (Playwright) |
| `import_schema` | `registry.company.com/uvz/import-schema` | `{{git.sha}}` | Gradle (library) |

### Kubernetes Manifests (simplified)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: uvz-backend
spec:
  replicas: 3            # scaling defined in 7.6
  selector:
    matchLabels:
      app: uvz-backend
  template:
    metadata:
      labels:
        app: uvz-backend
    spec:
      containers:
        - name: backend
          image: registry.company.com/uvz/backend:{{git.sha}}
          ports:
            - containerPort: 8080
          env:
            - name: SPRING_PROFILES_ACTIVE
              value: "${ENVIRONMENT}"
          resources:
            limits:
              cpu: "2"
              memory: "2Gi"
          livenessProbe:
            httpGet:
              path: /actuator/health
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 15
```

A similar `Deployment` exists for `frontend` (replicas 2) and `e2e_xnp` (run‑once Job).  The `import_schema` library is packaged inside the backend image and does not have its own deployment.

---

## 7.4 Environment Configuration

| Environment | Config Source | Key Differences |
|-------------|---------------|-----------------|
| **Development** | `.env.dev` (ConfigMap) | Uses an in‑memory H2 database, debug logging, `SPRING_PROFILES_ACTIVE=dev`. |
| **Test** | `.env.test` (ConfigMap) | Connects to a dedicated PostgreSQL test instance, enables Flyway migrations, `SPRING_PROFILES_ACTIVE=test`. |
| **Production** | Secrets Manager + ConfigMap | TLS certificates, connection to managed PostgreSQL with IAM authentication, `SPRING_PROFILES_ACTIVE=prod`, rate‑limiting enabled on ingress. |

All containers read their configuration via Spring Boot’s externalized configuration mechanism (environment variables, ConfigMaps, Secrets).  The Angular frontend consumes a `runtime-config.json` generated at container start‑up to point to the correct backend base URL.

---

## 7.5 Network Topology

```
[Internet] ── TLS ── Ingress (NGINX) ──+──► Frontend Pod (Angular)
                                      |
                                      +──► Backend Pod (Spring Boot) ──► PostgreSQL (private subnet)
                                      |
                                      +──► Object Storage (S3) (VPC endpoint)
                                      |
                                      +──► CI Runner (e2e_xnp) – accesses Ingress via internal DNS
```

* **Network Zones** – Public zone (Ingress), Private zone (backend, DB, storage).  Security groups allow only the Ingress to reach the backend on port 8080 and only the backend to reach the database on port 5432.
* **Firewall Rules** – Deny all inbound traffic except TLS 443 to the Ingress; backend pods accept traffic only from the Ingress IP range.
* **Service Mesh (optional)** – If a service mesh such as Istio is introduced, mutual TLS would be enforced between backend and database.

---

## 7.6 Scaling Strategy

| Container | Scaling Type | Trigger | Min Replicas | Max Replicas |
|-----------|--------------|---------|--------------|--------------|
| `backend` | Horizontal Pod Autoscaler (CPU‑based) | CPU > 70 % for 2 min | 2 | 10 |
| `frontend` | Horizontal Pod Autoscaler (request‑rate) | HTTP requests > 1500 rps | 2 | 6 |
| `e2e_xnp` | Job‑based (run‑on‑commit) | CI pipeline event | 0 | 1 |
| `import_schema` | N/A (library) | – | – | – |

The HPA uses the Kubernetes metrics server.  Scaling decisions are logged to Prometheus and visualised in Grafana dashboards.  Autoscaling respects pod disruption budgets to guarantee at least one healthy replica during rolling updates.

---

## 7.7 Deployment Pipeline (summary)

1. **Commit** → GitHub triggers CI.
2. **Build** – Gradle builds the backend JAR, npm builds the Angular bundle; Docker images are created and pushed to the internal registry.
3. **Test** – Unit tests, integration tests, and Playwright e2e tests (`container.e2e_xnp`) run.
4. **Release** – Helm chart is rendered with the new image tags and applied to the target cluster (dev → test → prod).
5. **Verification** – Smoke tests hit the health endpoint (`/actuator/health`) and a subset of public REST endpoints.
6. **Rollback** – Helm rollback to the previous release if health checks fail.

All steps are documented in the project’s `README.md` and enforced by the CI pipeline.

---

*The deployment view follows the SEAGuide “Graphics First” principle: the textual description complements the ASCII‑art diagram, the node table, and the scaling matrix, allowing stakeholders to grasp the physical layout, technology stack, and operational behaviour without redundant prose.*