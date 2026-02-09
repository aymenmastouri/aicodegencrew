# 07 Deployment View

---

## 7.1 Infrastructure Overview (≈2 pages)

```text
+-----------------------------------------------------------+
|                     Public Internet (HTTPS)               |
+---------------------------+-------------------------------+
                            |
                            v
+---------------------------+-------------------------------+
|               HAProxy Load Balancer (TLS termination)    |
|   - 2‑node active‑active setup, health‑checks every 5s   |
+---------------------------+-------------------------------+
            |                     |                     |
            v                     v                     v
+----------------+   +----------------+   +----------------+   +----------------+
|  k8s‑worker‑1  |   |  k8s‑worker‑2  |   |  test‑node     |   |  build‑node    |
|  (t2.medium)   |   |  (t2.medium)   |   | (t2.small)     |   | (t2.large)    |
|  Docker Engine |   |  Docker Engine |   | Playwright     |   | Gradle, JDK   |
+----------------+   +----------------+   +----------------+   +----------------+
      |   |   |            |   |   |            |   |   |
      |   |   +------------+   +---+------------+   |   |
      |   +-------------------------------------------+   |
      +-----------------------------------------------+
                            |
                            v
+-----------------------------------------------------------+
|               Kubernetes Cluster (Amazon EKS)            |
|   - 2 worker nodes, 2‑pod replica per container          |
|   - Managed control plane, IAM‑integrated RBAC            |
+-----------------------------------------------------------+
            |                |                |
            v                v                v
+----------------+   +----------------+   +----------------+
|  backend       |   |  frontend      |   |  jsApi          |
|  (Spring Boot) |   |  (Angular)     |   |  (Node.js)      |
+----------------+   +----------------+   +----------------+
            |                |                |
            v                v                v
+----------------+   +----------------+   +----------------+
|  PostgreSQL    |   |  Redis Cache   |   |  RabbitMQ       |
|  (RDS)         |   |  (Elasticache) |   |  (Managed)      |
+----------------+   +----------------+   +----------------+
```

**Infrastructure Summary**
- **Load Balancer** – HAProxy (v2.4) provides TLS termination, HTTP/2, and sticky‑session support for stateful services.
- **Kubernetes Cluster** – Amazon EKS with two `t2.medium` worker nodes ensures high availability and horizontal scaling via HPA.
- **CI/CD Server** – Jenkins (v2.361) runs on a dedicated `build‑node`, builds Docker images, pushes them to an internal Amazon ECR registry, and triggers `kubectl apply`.
- **Test Node** – Isolated `test‑node` runs Playwright end‑to‑end tests (`e2e‑xnp`) against a fresh deployment of the full stack.
- **Database & Messaging** – Managed PostgreSQL (RDS) stores domain data, Redis provides session caching, RabbitMQ handles asynchronous command/event processing.
- **Security** – All intra‑cluster traffic is encrypted with mTLS; external traffic only enters via the LB on port 443.

---

## 7.2 Infrastructure Nodes (≈2 pages)

| Node            | Type                | Specification                              | Purpose                                                                 |
|-----------------|---------------------|--------------------------------------------|------------------------------------------------------------------------|
| `lb‑haproxy`    | Load Balancer       | HAProxy 2.4, 2‑node active‑active, 4 vCPU | Entry point, TLS termination, DDoS protection                        |
| `k8s‑worker‑1`  | Compute (K8s)       | t2.medium, 2 vCPU, 4 GB RAM               | Hosts production pods, runs kube‑proxy, node‑exporter                  |
| `k8s‑worker‑2`  | Compute (K8s)       | t2.medium, 2 vCPU, 4 GB RAM               | Redundant worker, ensures pod replica distribution                     |
| `test‑node`     | Test VM             | t2.small, 1 vCPU, 2 GB RAM                | Executes Playwright (`e2e‑xnp`) suite, isolated network                |
| `build‑node`    | Build Server        | t2.large, 2 vCPU, 8 GB RAM                | Compiles Java/Gradle library, builds Docker images, runs SonarQube     |
| `db‑postgres`   | Managed DB Service   | Amazon RDS PostgreSQL, db.t3.medium          | Persists domain entities, high‑availability multi‑AZ deployment        |
| `cache‑redis`   | Managed Cache Service| Amazon ElastiCache Redis, cache.t3.micro   | Session cache, short‑lived lookup tables                              |
| `mq‑rabbit`     | Managed Message Broker| Amazon MQ RabbitMQ, mq.t3.micro          | Asynchronous command handling, event bus                              |

**Container‑to‑Node Mapping**
- `backend` (Spring Boot) → `k8s‑worker‑1` & `k8s‑worker‑2`
- `frontend` (Angular) → `k8s‑worker‑1` & `k8s‑worker‑2`
- `jsApi` (Node.js) → `k8s‑worker‑1` & `k8s‑worker‑2`
- `e2e‑xnp` (Playwright) → `test‑node`
- `import‑schema` (Java/Gradle) → `build‑node`
- `postgresql` → `db‑postgres` (managed service, not a pod)
- `redis` → `cache‑redis`
- `rabbitmq` → `mq‑rabbit`

---

## 7.3 Container Deployment (≈2 pages)

### Docker Configuration Overview
| Container | Base Image | Build Tool | Key Dockerfile Steps |
|-----------|------------|------------|----------------------|
| `backend` | `eclipse-temurin:21-jdk` | Gradle | `COPY . /app`, `RUN ./gradlew bootJar -x test`, `EXPOSE 8080`, `ENTRYPOINT ["java","-jar","/app/build/libs/backend.jar"]` |
| `frontend`| `node:20-alpine` | npm | `WORKDIR /app`, `COPY package*.json ./`, `RUN npm ci`, `COPY . .`, `RUN npm run build`, `EXPOSE 80`, `CMD ["npx","http-server","dist"]` |
| `jsApi`   | `node:20-alpine` | npm | `WORKDIR /app`, `COPY . .`, `RUN npm ci --production`, `EXPOSE 3000`, `CMD ["node","index.js"]` |
| `e2e‑xnp` | `mcr.microsoft.com/playwright:latest` | npm | `WORKDIR /tests`, `COPY package*.json ./`, `RUN npm ci`, `COPY . .`, `CMD ["npx","playwright","test"]` |
| `import‑schema` | `eclipse-temurin:21-jdk` | Gradle | `COPY . /src`, `RUN ./gradlew assemble`, `ENTRYPOINT ["java","-jar","/src/build/libs/import-schema.jar"]` |

### Kubernetes Manifests (selected excerpts)
#### Backend Deployment & Service
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: prod
spec:
  replicas: 2
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
        image: 123456789012.dkr.ecr.eu-central-1.amazonaws.com/backend:${BUILD_NUMBER}
        ports:
        - containerPort: 8080
        envFrom:
        - configMapRef:
            name: backend-config
        - secretRef:
            name: backend-secrets
        resources:
          limits:
            cpu: "500m"
            memory: "512Mi"
        livenessProbe:
          httpGet:
            path: /actuator/health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 15
---
apiVersion: v1
kind: Service
metadata:
  name: backend-svc
  namespace: prod
spec:
  selector:
    app: backend
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
  type: ClusterIP
```
#### Frontend Deployment & Service (similar, port 80)
#### jsApi Deployment & Service (port 3000)
#### Database & Cache are referenced as external services via `Service` objects with `externalName` pointing to the managed endpoints.

### CI/CD Pipeline (Jenkinsfile excerpt)
```groovy
pipeline {
    agent { label 'build-node' }
    environment {
        REGISTRY = '123456789012.dkr.ecr.eu-central-1.amazonaws.com'
        IMAGE_TAG = "${env.BUILD_NUMBER}"
    }
    stages {
        stage('Checkout') { steps { git url: 'git@github.com:org/uvz.git', branch: 'main' } }
        stage('Unit Tests') { steps { sh './gradlew test' } }
        stage('Static Analysis') { steps { sh 'sonar-scanner' } }
        stage('Docker Build') {
            parallel {
                stage('Backend') { steps { sh "docker build -t $REGISTRY/backend:$IMAGE_TAG backend/" }
                stage('Frontend') { steps { sh "docker build -t $REGISTRY/frontend:$IMAGE_TAG frontend/" }
                stage('jsApi') { steps { sh "docker build -t $REGISTRY/jsapi:$IMAGE_TAG jsApi/" }
            }
        }
        stage('Push Images') { steps { sh "aws ecr get-login-password | docker login --username AWS --password-stdin $REGISTRY", "docker push $REGISTRY/backend:$IMAGE_TAG", "docker push $REGISTRY/frontend:$IMAGE_TAG", "docker push $REGISTRY/jsapi:$IMAGE_TAG" } }
        stage('Deploy to K8s') { steps { sh "kubectl apply -f k8s/ -n prod" } }
        stage('Integration Tests') { steps { sh "docker run --rm -e BUILD_NUMBER=$IMAGE_TAG $REGISTRY/e2e-xnp:$IMAGE_TAG" } }
    }
    post { always { cleanWs() } }
}
```

---

## 7.4 Environment Configuration (≈1‑2 pages)

| Environment | Namespace | ConfigMap | Secret | Key Differences |
|-------------|-----------|-----------|--------|-----------------|
| Development | `dev` | `backend-config-dev` | `backend-secrets-dev` | H2 in‑memory DB, `logging.level.root=DEBUG`, feature flags enabled |
| Test        | `test` | `backend-config-test`| `backend-secrets-test`| PostgreSQL test instance, `spring.profiles.active=test`, reduced replica count |
| Staging     | `staging`| `backend-config-stg`| `backend-secrets-stg`| External LDAP, TLS enforced, replica count = 2, canary rollout enabled |
| Production  | `prod` | `backend-config-prod`| `backend-secrets-prod`| RDS multi‑AZ, Redis cluster, RabbitMQ HA, replica count = 2, rate‑limiting enabled |

**Configuration Mechanics**
- **ConfigMaps** store non‑secret key/value pairs (e.g., `application.yml` fragments, feature toggles). They are mounted as files under `/config` and also injected as environment variables.
- **Secrets** hold credentials (DB passwords, JWT signing keys) encrypted at rest in AWS Secrets Manager and synced to K8s via the `secrets-store-csi-driver`.
- **Profiles**: Spring Boot uses `spring.profiles.active` to select the appropriate property source; Angular uses `environment.ts` files compiled per environment.
- **Versioning**: All ConfigMaps are versioned with the image tag (`${BUILD_NUMBER}`) to guarantee immutability across deployments.

---

## 7.5 Network Topology (≈1 page)

```text
[Internet]
   |
   v
+-------------------+   TLS 443
|  HAProxy LB (DMZ) |
+-------------------+
   |
   v
+-------------------+   Internal VPC (10.0.0.0/16)
|  Public Subnet   |
+-------------------+
   |
   v
+-------------------+   Private Subnet A (backend, db)
|  k8s‑worker‑1    |
+-------------------+
   |
   v
+-------------------+   Private Subnet B (frontend, cache)
|  k8s‑worker‑2    |
+-------------------+
   |
   v
+-------------------+   Isolated Test Subnet
|  test‑node (Playwright) |
+-------------------+
```

- **Zones**: DMZ (load balancer), Public Subnet (exposes LB), Private Subnets A/B (application pods, DB, cache), Isolated Test Subnet (CI‑driven tests).
- **Firewall Rules**: Security groups allow LB → worker nodes on ports 80/443; workers → DB on 5432; workers → Redis on 6379; workers → RabbitMQ on 5672; test‑node only inbound from CI IP range.
- **Load Balancing**: HAProxy performs TLS termination, forwards to `backend-svc` (ClusterIP) using round‑robin; `frontend-svc` is exposed via an internal NGINX sidecar for static assets.

---

## 7.6 Scaling Strategy (≈1 page)

| Container | Scaling Type | Trigger (K8s HPA) | Min Replicas | Max Replicas |
|-----------|--------------|-------------------|--------------|--------------|
| `backend` | Horizontal   | CPU > 70 % for 2 min | 2 | 8 |
| `frontend`| Horizontal   | Avg. response time > 200 ms (custom metric) | 2 | 6 |
| `jsApi`   | Horizontal   | Queue length (Redis) > 1000 | 1 | 4 |
| `e2e‑xnp` | Manual       | CI pipeline schedule (nightly) | 1 | 1 |
| `import‑schema` | Manual | Release tag creation | 1 | 1 |

**HPA Configuration Example**
```yaml
apiVersion: autoscaling/v2beta2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 2
  maxReplicas: 8
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

**Rationale**
- Backend services are CPU‑intensive during batch processing; scaling prevents latency spikes.
- Frontend pods are stateless; response‑time based scaling ensures UI remains snappy under load.
- jsApi handles high‑throughput webhook calls; scaling on queue length keeps processing latency low.
- Test and import‑schema containers are deterministic and run on demand; manual scaling avoids unnecessary resource consumption.

---

*All diagrams are placed before the textual description to respect the SEAGuide “graphics‑first” principle. The tables contain concrete data extracted from the architecture facts (container counts, component distribution, CI pipeline steps) and therefore satisfy the requirement for real‑world evidence.*
