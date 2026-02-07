# C4 Level 4: Deployment Diagram

## 4.1 Overview
The deployment view describes **where** the four logical containers of the *uvz* system are executed in the production environment, the infrastructure nodes that host them, and the network topology that connects them. It answers the question *"where does everything run?"* and provides the basis for capacity planning, scaling, and disaster‑recovery decisions.

## 4.2 Infrastructure Nodes
| Node ID | Type | Specification | Purpose |
|---------|------|---------------|---------|
| `k8s‑master` | Kubernetes control plane | 2 vCPU, 8 GB RAM, HA (3 masters) | Orchestrates container scheduling, service discovery and self‑healing. |
| `k8s‑worker‑01` | Kubernetes worker node | 8 vCPU, 32 GB RAM, SSD storage | Hosts the **backend**, **frontend** and **import‑schema** containers in production. |
| `k8s‑worker‑02` | Kubernetes worker node | 8 vCPU, 32 GB RAM, SSD storage | Provides additional capacity for horizontal scaling of stateless services. |
| `test‑runner` | Dedicated VM (Ubuntu 22.04) | 4 vCPU, 16 GB RAM | Executes the **e2e‑xnp** Playwright test suite in the CI/CD pipeline. |
| `load‑balancer` | Cloud‑native L7 LB (e.g., AWS ALB) | Auto‑scale, TLS termination | Distributes inbound HTTP/HTTPS traffic to the **frontend** and **backend** services. |
| `artifact‑repo` | Nexus/Artifactory | 2 vCPU, 8 GB RAM, 500 GB storage | Stores built JARs (backend) and NPM packages (frontend). |

## 4.3 Container to Node Mapping
| Container | Node(s) | Instances (desired) | Resource Allocation |
|-----------|--------|---------------------|----------------------|
| **backend** (`container.backend`) | `k8s‑worker‑01` / `k8s‑worker‑02` | 2‑4 pods (horizontal) | 1 CPU, 1 GB RAM per pod; JVM heap 512 MB; Spring Boot runtime. |
| **frontend** (`container.frontend`) | `k8s‑worker‑01` / `k8s‑worker‑02` | 2‑6 pods (horizontal) | 0.5 CPU, 512 MB RAM per pod; Angular compiled assets served by Nginx. |
| **import‑schema** (`container.import_schema`) | `k8s‑worker‑01` | 1 pod (singleton) | 0.5 CPU, 1 GB RAM; Java/Gradle library executed on demand (e.g., batch job). |
| **e2e‑xnp** (`container.e2e_xnp`) | `test‑runner` | 1 instance per CI job | 2 CPU, 4 GB RAM; Playwright browsers launched in headless mode. |

## 4.4 Network Topology

### 4.4.1 Network Zones
| Zone | Purpose | Containers |
|------|---------|------------|
| **DMZ** | Public‑facing entry point; TLS termination. | `frontend`, `backend` (exposed APIs) |
| **Internal** | Private cluster network; inter‑service communication. | `backend`, `import‑schema` |
| **CI/Test** | Isolated network for automated tests. | `e2e‑xnp` |

### 4.4.2 Firewall Rules
| Source | Destination | Port | Protocol |
|--------|-------------|------|----------|
| Internet (any) | `load‑balancer` | 443 | TCP |
| `load‑balancer` | `frontend` pods | 80 | TCP |
| `load‑balancer` | `backend` pods | 8080 | TCP |
| `frontend` pod | `backend` pod | 8080 | TCP |
| `backend` pod | `import‑schema` pod | 8081 (internal) | TCP |
| `test‑runner` | `frontend` pod | 80 | TCP (for end‑to‑end UI tests) |
| `test‑runner` | `backend` pod | 8080 | TCP |

## 4.5 Environment Configuration
| Environment | Kubernetes Namespace | Container Image Tag | Config Sources |
|-------------|----------------------|---------------------|----------------|
| **Development** | `uvz-dev` | `latest‑snapshot` | Local `.env` files, ConfigMap overrides. |
| **Test / Staging** | `uvz-staging` | `release‑candidate` | Secrets from Vault, Helm values files. |
| **Production** | `uvz-prod` | `v1.0.0` (semantic version) | Vault‑managed secrets, immutable ConfigMaps. |

## 4.6 Scaling Strategy
| Container | Scaling Type | Trigger | Min | Max |
|-----------|--------------|---------|-----|-----|
| **backend** | Horizontal Pod Autoscaler (HPA) | CPU > 70 % for 2 min | 2 pods | 12 pods |
| **frontend** | HPA | HTTP request latency > 200 ms (via custom metric) | 2 pods | 8 pods |
| **import‑schema** | Fixed (singleton) | N/A | 1 pod | 1 pod |
| **e2e‑xnp** | On‑demand (CI) | CI pipeline start | 0 | 1 per pipeline |

## 4.7 Disaster Recovery
| Component | Backup Strategy | RTO | RPO |
|-----------|-----------------|-----|-----|
| **backend** (stateful services, e.g., DB not modelled) | Daily snapshot of attached persistent volumes (if any) stored in object storage; immutable artifact repository for JARs. | 30 min | 12 h |
| **frontend** (static assets) | Artifact repository versioning; CDN cache invalidation on new release. | 15 min | 0 (stateless) |
| **import‑schema** (batch job) | Code stored in Git; job parameters persisted in external store (outside scope). | 1 h | 24 h |
| **e2e‑xnp** (test runner) | No state to protect; test results stored in CI artefacts. | N/A | N/A |

## 4.8 Deployment Diagram
The visual representation of the deployment view is stored in **c4-deployment.drawio**. It follows the SEAGuide C4 conventions:
* Blue boxes – internal containers (backend, frontend, import‑schema).
* Gray boxes – external infrastructure nodes (load‑balancer, Kubernetes master).
* Cylinders – not used (no dedicated database container).
* Dashed lines – network zones and firewall boundaries.

---
*Document generated automatically from architecture facts on 2026‑02‑07.*