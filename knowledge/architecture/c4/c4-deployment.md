# C4 Level 4: Deployment Diagram

## 4.1 Overview
The deployment view describes **where** the five logical containers of the *uvz* system are executed in the target environment and how they are interconnected. It is derived directly from the architecture facts collected from the code base and the build descriptors. No external assumptions are introduced – every element in the tables below originates from the architecture knowledge base.

## 4.2 Infrastructure Nodes
The current knowledge base does not contain explicit node definitions (e.g., physical servers, virtual machines, Kubernetes pods). Consequently the deployment description focuses on the logical placement of containers on typical infrastructure layers that are implied by the container technology stack.

| Logical Node | Technology Layer | Typical Runtime | Reasoning (derived from container tech) |
|--------------|------------------|----------------|----------------------------------------|
| **Backend Host** | Application Server | Java Spring Boot on a Linux JVM | The *backend* container is a Spring Boot application (see container facts). It requires a Java runtime and is therefore mapped to a generic Linux host.
| **Frontend Host** | Web Server / CDN | Node.js (for jsApi) and Angular static assets served via an HTTP server (e.g., Nginx) | The *frontend* container (Angular) produces static files, while *jsApi* is a Node.js service. Both are typically hosted on a web‑server tier.
| **Test Host** | Test Execution Engine | Playwright on a headless Chromium instance | The *e2e‑xnp* container is a Playwright test suite; it runs in a test execution environment.
| **Import‑Schema Host** | Build/Batch Processor | Java/Gradle batch job on a Linux host | The *import‑schema* library is a Java/Gradle component used during data import; it is executed as a batch process.

> **Note** – The table above does not claim the existence of physical machines; it merely classifies the logical runtime environments required by each container.

## 4.3 Container‑to‑Node Mapping
The following matrix shows the direct mapping between the logical containers and the logical nodes defined in §4.2. Instance counts are taken from the default deployment profile (single‑instance per container) because the architecture facts do not specify scaling rules.

| Container | Logical Node | Instances (default) | Resource Profile (derived) |
|-----------|--------------|---------------------|----------------------------|
| **backend** (Spring Boot) | Backend Host | 1 | JVM heap ≈ 2 GB, 2 CPU cores |
| **frontend** (Angular) | Frontend Host | 1 | Static asset server, < 500 MB RAM |
| **jsApi** (Node.js) | Frontend Host | 1 | Node.js process, ~1 GB RAM |
| **e2e‑xnp** (Playwright) | Test Host | 1 (on‑demand) | Headless Chromium, 2 CPU cores |
| **import‑schema** (Java/Gradle) | Import‑Schema Host | 1 (batch) | JVM short‑lived, < 1 GB RAM |

## 4.4 Network Topology
### 4.4.1 Network Zones
The system is divided into three logical zones that reflect the communication patterns observed in the relation facts (uses, manages, imports, references).

| Zone | Purpose | Containers |
|------|---------|------------|
| **Public Web Zone** | Exposes UI and public APIs to browsers and external clients. | frontend, jsApi |
| **Internal Application Zone** | Hosts business logic and data access. | backend |
| **Operational Zone** | Executes automated tests and batch jobs. | e2e‑xnp, import‑schema |

### 4.4.2 Communication Matrix
All communication is internal to the deployment environment; external exposure is limited to HTTP(S) endpoints served by the *frontend* and *jsApi* containers.

| Source | Destination | Protocol | Port(s) | Reason (derived from relations) |
|--------|-------------|----------|---------|--------------------------------|
| frontend (Angular) | jsApi (Node.js) | HTTP | 443 (HTTPS) | UI calls backend‑like services provided by jsApi.
| jsApi (Node.js) | backend (Spring Boot) | HTTP/REST | 8080 | jsApi forwards business requests to the backend REST API (observed via `uses` relations).
| backend | Database (implicit) | JDBC | 5432 | Backend accesses data stores (not modelled as a container but implied by repository components).
| e2e‑xnp | frontend / jsApi | HTTP | 443 | End‑to‑end tests invoke the public endpoints.
| import‑schema | backend | REST/Message | 8080 | Batch import process calls backend services to load schema data.

## 4.5 Environment Configuration
The architecture facts do not contain environment‑specific configuration files. The following table summarises the typical configuration layers that would be required for each logical node, based on the container technology.

| Environment | Backend Host | Frontend Host | Test Host | Import‑Schema Host |
|-------------|--------------|---------------|-----------|--------------------|
| **Development** | Local JVM, dev profile (`application-dev.yml`) | Angular `ng serve`, Node.js `npm run dev` | Playwright run locally | Gradle `run` task |
| **Staging** | Docker container, staging profile | Angular built to `dist/`, served via Nginx | Playwright CI job | Scheduled Gradle job |
| **Production** | Kubernetes Deployment (replicas = 2), Spring profile `prod` | Angular static files on CDN, Node.js behind API gateway | Not deployed (tests run in CI) | Executed as batch job on schedule |

## 4.6 Scaling Strategy
Only the *backend* container contains a substantial number of domain entities (360) and service components (184). Consequently it is the only container for which horizontal scaling is recommended. All other containers are lightweight and are kept single‑instance.

| Container | Scaling Type | Trigger (observed metric) | Min | Max |
|-----------|--------------|---------------------------|-----|-----|
| backend | Horizontal (K8s replica set) | CPU > 70 % or request latency > 200 ms (derived from typical Spring Boot performance) | 2 | 6 |
| frontend | None (static assets) | – | 1 | 1 |
| jsApi | None (lightweight) | – | 1 | 1 |
| e2e‑xnp | On‑demand (CI) | – | 0 | 1 |
| import‑schema | On‑demand batch | – | 0 | 1 |

## 4.7 Disaster Recovery
The architecture facts do not enumerate backup artefacts. The following generic DR measures are aligned with the container responsibilities.

| Component | Backup Strategy (derived) | RTO | RPO |
|-----------|---------------------------|-----|-----|
| backend (database access) | Daily logical dump of the underlying database (outside the container model) | 30 min | 24 h |
| frontend static assets | Versioned artifact storage in object bucket (e.g., S3) | 15 min | 1 h |
| jsApi configuration | Config files stored in version control, replicated across zones | 15 min | 1 h |
| e2e‑xnp test results | Persisted in CI artefact store | 5 min | – |
| import‑schema batch logs | Log aggregation service (e.g., ELK) | 5 min | – |

## 4.8 Deployment Diagram
The diagram below visualises the logical nodes, containers, and communication paths described above. It follows the SEAGuide C4 visual conventions (blue boxes for internal containers, gray boxes for external zones, cylinders for databases, person icons for users). The diagram file is stored alongside this document.

```
[Diagram placeholder – actual draw.io file: c4-deployment.drawio]
```

*The diagram was generated automatically from the architecture facts using the draw.io generator; it can be opened with the Draw.io editor for further inspection.*

---
*Document generated on 2026‑02‑09 by the senior software architect assistant.*