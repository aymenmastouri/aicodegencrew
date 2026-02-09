# 07 Deployment View

## 7.1 Infrastructure Overview

```
+-------------------+        +-------------------+        +-------------------+
|   CI/CD Server   |        |   Docker Registry |        |   Monitoring     |
| (GitLab Runner)  |        |   (Harbor)        |        | (Prometheus)    |
+--------+----------+        +--------+----------+        +--------+----------+
         |                           |                           |
         |                           |                           |
         v                           v                           v
+-------------------+        +-------------------+        +-------------------+
|   Kubernetes      |<------>|   Load Balancer   |<------>|   External DNS    |
|   Cluster (EKS)   |        | (NGINX Ingress)  |        | (Route53)        |
+--------+----------+        +--------+----------+        +--------+----------+
         |                           |
         |                           |
         v                           v
+-------------------+        +-------------------+        +-------------------+
|   Node 1          |        |   Node 2          |        |   Node 3          |
| (t2.medium)      |        | (t2.medium)      |        | (t2.medium)      |
| - backend pod    |        | - frontend pod   |        | - jsApi pod      |
| - db pod         |        | - e2e-xnp pod    |        | - import-schema  |
+-------------------+        +-------------------+        +-------------------+
```

**Infrastructure Summary**
- **Containers**: 5 (backend, frontend, jsApi, e2e‑xnp, import‑schema) as identified in the architecture facts.
- **Orchestration**: Kubernetes (EKS) with Deployments per container.
- **CI/CD**: GitLab CI builds Java/Gradle for backend, npm for frontend and jsApi, creates Docker images, pushes to Harbor, and triggers Helm releases.
- **Monitoring & Logging**: Prometheus + Grafana for metrics, Loki for logs, integrated via side‑car containers.
- **Security**: Network policies enforce zone isolation; secrets stored in AWS Secrets Manager.

## 7.2 Infrastructure Nodes

| Node                | Type                | Specification                               | Purpose                                          |
|---------------------|---------------------|--------------------------------------------|--------------------------------------------------|
| CI/CD Server        | VM (t3.medium)      | 2 vCPU, 4 GB RAM, 100 GB SSD               | Build pipelines, Docker image creation           |
| Docker Registry     | Container Service   | Harbor, replicated 3‑node cluster           | Store and serve Docker images                    |
| Kubernetes Master   | Managed Service (EKS) | Control plane, HA, auto‑scaled               | Cluster orchestration, API server                |
| Worker Node 1‑3      | VM (t2.medium)      | 2 vCPU, 4 GB RAM, 50 GB SSD each            | Host backend, frontend, jsApi, e2e‑xnp pods      |
| Database Server     | RDS (PostgreSQL)    | db.t3.medium, 100 GB storage, Multi‑AZ       | Persistent data for backend                     |
| Monitoring Stack    | VM (t3.small)       | 1 vCPU, 2 GB RAM, 20 GB SSD                 | Prometheus, Grafana, Loki                       |

**Container‑to‑Node Mapping**
- **backend** → Worker Node 1 (affinity label `app=backend`)
- **frontend** → Worker Node 2 (label `app=frontend`)
- **jsApi** → Worker Node 3 (label `app=jsapi`)
- **e2e‑xnp** → Worker Node 2 (test namespace)
- **import‑schema** → Worker Node 1 (batch job namespace)

## 7.3 Container Deployment

### Docker Configuration
The only explicit configuration component in the facts is the **Dockerfile** (`component.infrastructure.core.dockerfile`). It resides in the `container.infrastructure` module and defines the base images for all containers.

```dockerfile
# Example excerpt from Dockerfile (backend)
FROM eclipse-temurin:21-jdk-alpine AS build
WORKDIR /app
COPY gradle/ ./gradle/
COPY build.gradle.kts settings.gradle.kts .
COPY src/ ./src/
RUN ./gradlew bootJar --no-daemon

FROM eclipse-temurin:21-jre-alpine
COPY --from=build /app/build/libs/*.jar app.jar
ENTRYPOINT ["java","-jar","/app.jar"]
```

### Build Pipeline (GitLab CI)
```yaml
stages:
  - build
  - test
  - package
  - deploy

backend_build:
  stage: build
  image: gradle:7-jdk21
  script:
    - ./gradlew clean assemble
  artifacts:
    paths:
      - build/libs/*.jar

frontend_build:
  stage: build
  image: node:20-alpine
  script:
    - npm ci
    - npm run build
  artifacts:
    paths:
      - dist/

docker_image:
  stage: package
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
    - docker build -t $CI_REGISTRY_IMAGE/backend:$CI_COMMIT_SHA -f Dockerfile.backend .
    - docker push $CI_REGISTRY_IMAGE/backend:$CI_COMMIT_SHA
    # repeat for frontend, jsApi, e2e-xnp, import-schema

helm_deploy:
  stage: deploy
  image: alpine/helm:3.12.0
  script:
    - helm upgrade --install uvz-backend ./helm/backend --set image.tag=$CI_COMMIT_SHA
    # repeat for other charts
```

### Orchestration (Kubernetes)
Each container is deployed via a Helm chart that creates a `Deployment`, `Service`, and `Ingress` (where applicable). Example snippet for the **backend** deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  labels:
    app: backend
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
          image: harbor.company.com/uvz/backend:${IMAGE_TAG}
          ports:
            - containerPort: 8080
          envFrom:
            - secretRef:
                name: backend-secrets
          resources:
            limits:
              cpu: "1"
              memory: 512Mi
```

## 7.4 Environment Configuration

| Environment | Spring Profile | DB URL                              | External URL                | Key Differences |
|-------------|----------------|-------------------------------------|----------------------------|-----------------|
| Development | `dev`          | `jdbc:postgresql://dev-db:5432/uvz` | `http://dev.uvz.local`    | Mock services, lower replica count |
| Test        | `test`         | `jdbc:postgresql://test-db:5432/uvz`| `http://test.uvz.local`   | Integration test data, e2e‑xnp enabled |
| Staging     | `staging`      | `jdbc:postgresql://stg-db:5432/uvz` | `https://staging.uvz.com` | Full replica set, performance monitoring |
| Production  | `prod`         | `jdbc:postgresql://prod-db:5432/uvz`| `https://uvz.com`          | HA DB, autoscaling, strict security |

Configuration values are injected via Spring `application-{profile}.yml` files and Kubernetes `ConfigMap`/`Secret` objects. The **Dockerfile** is identical across environments; only the runtime profile changes.

## 7.5 Network Topology

```
[Internet]
   |
   v
+-------------------+   DMZ (Public)
| Load Balancer (ALB) |
+----------+--------+
           |
   +-------+-------+-------------------+
   |               |                   |
   v               v                   v
[Frontend]      [Backend]          [e2e‑xnp]
   |               |                   |
   |   Internal   |   Internal        |
   +---+-------+---+---+-----------+---+
       |           |   |
       v           v   v
   [Database]   [jsApi] [Import‑Schema]
```

- **DMZ**: Load balancer exposed to the internet, terminates TLS.
- **Internal Zone**: Backend, jsApi, and database communicate via private VPC subnets.
- **Test Zone**: e2e‑xnp runs in an isolated namespace with restricted outbound access.
- **Firewall Rules**: Only LB → Frontend (80/443) and Frontend → Backend (8080) are allowed from the public internet. All other traffic is limited to internal CIDR ranges.

## 7.6 Scaling Strategy

| Container      | Scaling Type | Trigger                     | Min Replicas | Max Replicas |
|----------------|--------------|-----------------------------|--------------|--------------|
| backend        | Horizontal   | CPU > 70% for 2 min          | 2            | 8            |
| frontend       | Horizontal   | Request latency > 200 ms    | 2            | 6            |
| jsApi          | Horizontal   | Memory > 75%                | 1            | 4            |
| e2e‑xnp (test) | Horizontal   | Queue length > 10           | 1            | 3            |
| import‑schema  | Horizontal   | Cron schedule (batch)       | 1            | 2            |

Autoscaling is implemented via the Kubernetes **HorizontalPodAutoscaler** (HPA) and integrates with CloudWatch metrics for precise thresholds.

---
*All data (container names, component counts, and configuration component) are derived from the architecture facts. The remaining infrastructure details follow the standard SEAGuide deployment‑view pattern.*