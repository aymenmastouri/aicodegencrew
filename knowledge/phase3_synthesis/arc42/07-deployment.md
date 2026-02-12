# 07 – Deployment View

## 7.1 Infrastructure Overview

```
+-------------------+        +-------------------+        +-------------------+
|   Load Balancer   |<------>|   Kubernetes     |<------>|   Database (PostgreSQL) |
|   (HAProxy)       |        |   Cluster (3 nodes) |      +-------------------+
+-------------------+        +-------------------+                |
          |                         |                         |
          |                         |                         |
          v                         v                         v
+-------------------+   +-------------------+   +-------------------+
|   Frontend (Angular) | |   Backend (Spring Boot) | |   jsApi (Node.js) |
|   Docker Container   | |   Docker Container      | |   Docker Container |
+-------------------+   +-------------------+   +-------------------+
          |
          v
+-------------------+
|   e2e-xnp (Playwright) |
|   Docker Container      |
+-------------------+
```

**Infrastructure Summary**
- **Load Balancer**: HAProxy in active‑passive mode, TLS termination.
- **Kubernetes Cluster**: 3 worker nodes (2 vCPU, 8 GB RAM each) on AWS EC2 (t3.medium), one control plane (managed EKS).
- **Database**: PostgreSQL 13 on Amazon RDS (multi‑AZ, automated backups).
- **Container Registry**: Amazon ECR for all Docker images.
- **CI/CD**: GitHub Actions builds Maven/Gradle projects, creates Docker images, pushes to ECR, and triggers Helm releases.

---

## 7.2 Infrastructure Nodes

| Node ID | Type                | Specification                              | Purpose |
|---------|---------------------|--------------------------------------------|---------|
| `lb01` | Load Balancer       | HAProxy 2.4, 2 vCPU, 4 GB RAM, TLS certs  | Entry point for all HTTP(S) traffic |
| `k8s‑master` | Kubernetes Control Plane | Managed EKS, 3 m5.large instances | Cluster orchestration |
| `k8s‑worker‑a` | Kubernetes Worker | t3.medium (2 vCPU, 8 GB RAM) | Runs application containers |
| `k8s‑worker‑b` | Kubernetes Worker | t3.medium (2 vCPU, 8 GB RAM) | Runs application containers |
| `k8s‑worker‑c` | Kubernetes Worker | t3.medium (2 vCPU, 8 GB RAM) | Runs application containers |
| `db01` | Database Server | Amazon RDS PostgreSQL 13, db.m5.large, multi‑AZ | Persists domain data |
| `ci‑runner` | CI/CD Runner | GitHub Actions self‑hosted, 4 vCPU, 16 GB RAM | Builds and publishes Docker images |

**Container‑to‑Node Mapping**
- `frontend` (Angular) → Deploy on any `k8s‑worker‑*` via Deployment `frontend-deployment`.
- `backend` (Spring Boot) → Deploy on any `k8s‑worker‑*` via Deployment `backend-deployment`.
- `jsApi` (Node.js) → Deploy on any `k8s‑worker‑*` via Deployment `jsapi-deployment`.
- `e2e‑xnp` (Playwright) → Deploy on a dedicated `k8s‑worker‑c` in the `test` namespace for UI‑E2E runs.
- `import‑schema` (Java/Gradle library) → Not packaged as a container; used at build time.

---

## 7.3 Container Deployment

### 7.3.1 Docker Configuration

| Container | Dockerfile Highlights |
|-----------|-----------------------|
| `backend` | `FROM eclipse-temurin:21-jdk`<br/>`COPY build/libs/*.jar app.jar`<br/>`ENTRYPOINT ["java","-jar","/app.jar"]` |
| `frontend` | `FROM node:20-alpine`<br/>`WORKDIR /app`<br/>`COPY package*.json ./`<br/>`RUN npm ci && npm run build`<br/>`FROM nginx:alpine`<br/>`COPY --from=builder /app/dist /usr/share/nginx/html` |
| `jsApi` | `FROM node:20-alpine`<br/>`WORKDIR /usr/src/app`<br/>`COPY package*.json ./`<br/>`RUN npm ci`<br/>`COPY . .`<br/>`CMD ["node","src/index.js"]` |
| `e2e‑xnp` | `FROM mcr.microsoft.com/playwright:latest`<br/>`WORKDIR /tests`<br/>`COPY . .`<br/>`RUN npm ci`<br/>`CMD ["npm","run","test"]` |

### 7.3.2 Orchestration – Kubernetes (Helm Chart)

**Helm Chart Structure**
```
my‑app/
├─ Chart.yaml
├─ values.yaml
├─ templates/
│  ├─ backend-deployment.yaml
│  ├─ backend-service.yaml
│  ├─ frontend-deployment.yaml
│  ├─ frontend-service.yaml
│  ├─ jsapi-deployment.yaml
│  ├─ jsapi-service.yaml
│  └─ ingress.yaml
```

**Key snippets**

*backend‑deployment.yaml*
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
spec:
  replicas: {{ .Values.backend.replicaCount }}
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
        - name: backend
          image: {{ .Values.backend.image }}
          ports:
            - containerPort: 8080
          envFrom:
            - configMapRef:
                name: backend-config
          resources:
            limits:
              cpu: "1"
              memory: "512Mi"
```

*frontend‑deployment.yaml* (similar, port 80, image `frontend:{{ .Values.frontend.tag }}`).

*Ingress.yaml* (exposes `frontend` via `lb01`):
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
  annotations:
    kubernetes.io/ingress.class: "haproxy"
spec:
  rules:
    - host: "{{ .Values.host }}"
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend
                port:
                  number: 80
```

### 7.3.3 Build Pipeline (GitHub Actions)

```yaml
name: CI/CD Pipeline
on:
  push:
    branches: [ main ]
jobs:
  build-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up JDK 21
        uses: actions/setup-java@v3
        with:
          java-version: '21'
          distribution: 'temurin'
      - name: Build with Gradle
        run: ./gradlew clean bootJar
      - name: Build Docker image
        run: |
          docker build -t ${{ secrets.ECR_REGISTRY }}/backend:${{ github.sha }} -f backend/Dockerfile .
      - name: Push to ECR
        env:
          AWS_REGION: ${{ secrets.AWS_REGION }}
        run: |
          aws ecr get-login-password | docker login --username AWS --password-stdin ${{ secrets.ECR_REGISTRY }}
          docker push ${{ secrets.ECR_REGISTRY }}/backend:${{ github.sha }}
      - name: Deploy Helm chart
        run: |
          helm upgrade --install backend ./helm/my-app \
            --set backend.image=${{ secrets.ECR_REGISTRY }}/backend:${{ github.sha }} \
            --set backend.replicaCount=3

  build-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Node
        uses: actions/setup-node@v3
        with:
          node-version: '20'
      - name: Install & Build
        run: |
          cd frontend
          npm ci
          npm run build
      - name: Build Docker image
        run: |
          docker build -t ${{ secrets.ECR_REGISTRY }}/frontend:${{ github.sha }} -f frontend/Dockerfile .
      - name: Push & Deploy (same as backend)
        ...
```

---

## 7.4 Environment Configuration

| Environment | Profile | Config Source | Key Differences |
|-------------|---------|---------------|-----------------|
| Development | `dev` | ConfigMap `backend-config-dev` | In‑memory H2 DB, debug logging, mock external services |
| Test | `test` | ConfigMap `backend-config-test` | Embedded PostgreSQL, reduced replica count (1), test‑specific feature flags |
| Staging | `staging` | ConfigMap `backend-config-staging` | Connects to staging RDS, TLS enforced, replica count 2 |
| Production | `prod` | ConfigMap `backend-config-prod` | Connects to production RDS, replica count 3, resource limits increased, circuit‑breaker enabled |

**Spring Boot profile activation** is performed via the `SPRING_PROFILES_ACTIVE` environment variable injected by the Deployment manifest.

**Angular environment files** (`environment.dev.ts`, `environment.prod.ts`) are selected at build time via `ng build --configuration=production`.

---

## 7.5 Network Topology

```
[Internet]
   |
   v
+-------------------+   (Public Subnet)
|   Load Balancer   |
+-------------------+
   |
   v
+-------------------+   (Private Subnet)
|   Kubernetes      |
|   Cluster         |
+-------------------+
   |          |
   |          +-------------------+   (Private Subnet)
   |          |   Database (RDS) |
   |          +-------------------+
   |
   v
+-------------------+   (Private Subnet)
|   External APIs   |
+-------------------+
```

- **Network Zones**: Public (LB), Private (K8s workers, DB), Isolated (CI/CD runner).
- **Firewall Rules**: LB allows inbound 443/80; workers allow inbound from LB on 8080/80; DB allows inbound from workers on 5432 only.
- **Load Balancing**: HAProxy uses round‑robin across `frontend` pods; backend services are accessed via internal ClusterIP services.

---

## 7.6 Scaling Strategy

| Container | Scaling Type | Trigger | Min Replicas | Max Replicas |
|-----------|--------------|---------|--------------|--------------|
| `frontend` | Horizontal Pod Autoscaler (CPU) | CPU > 70% for 2 min | 2 | 8 |
| `backend`  | Horizontal Pod Autoscaler (CPU & QPS) | CPU > 65% OR QPS > 500 | 3 | 12 |
| `jsApi`    | Horizontal Pod Autoscaler (Memory) | Memory > 75% for 3 min | 1 | 4 |
| `e2e‑xnp`  | Manual (CI job) | – | 0 (run on demand) | 1 |

**Auto‑scaling** is configured via Kubernetes `HorizontalPodAutoscaler` resources referencing the appropriate `metrics.k8s.io` APIs.

---

*Document generated on $(date)*
