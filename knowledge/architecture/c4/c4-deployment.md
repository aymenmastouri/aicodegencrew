# C4 Level 4: Deployment Diagram

## 4.1 Overview
The deployment view describes **where** the four logical containers of the *uvz* system are executed in the production environment, the infrastructure nodes that host them, and the network topology that connects them. It answers the question *"Where does everything run?"* and provides the basis for capacity planning, security hardening, and disaster‑recovery design.

---

## 4.2 Infrastructure Nodes
| Node ID | Type | Specification | Purpose |
|---------|------|----------------|---------|
| `k8s-master` | Kubernetes control plane | 2 vCPU, 8 GB RAM, HA (3 masters) | Orchestrates container scheduling, service discovery and rolling updates |
| `k8s-worker-app` | Kubernetes worker | 4 vCPU, 16 GB RAM, SSD | Hosts the **backend** Spring‑Boot microservice (stateless) |
| `k8s-worker-web` | Kubernetes worker | 2 vCPU, 8 GB RAM, SSD | Hosts the **frontend** Angular SPA behind an NGINX reverse‑proxy |
| `db-node` | Managed PostgreSQL (RDS) | 8 vCPU, 32 GB RAM, 500 GB storage, Multi‑AZ | Persists domain data (entities) used by the backend |
| `ci-runner` | GitLab CI/CD runner | 4 vCPU, 8 GB RAM, Docker | Executes the **e2e‑xnp** Playwright test suite on each merge request |
| `artifact-repo` | Nexus/Artifactory | 2 vCPU, 4 GB RAM, 200 GB storage | Stores built JARs (`backend`) and NPM packages (`frontend`) |

---

## 4.3 Container‑to‑Node Mapping
| Container | Node(s) | Instances (replicas) | Resource Requests |
|-----------|--------|----------------------|-------------------|
| **backend** (Spring Boot) | `k8s-worker-app` | 3 (horizontal pod autoscaler) | CPU = 500 m, Memory = 512 Mi per pod |
| **frontend** (Angular) | `k8s-worker-web` | 2 (stateless) | CPU = 250 m, Memory = 256 Mi per pod |
| **e2e‑xnp** (Playwright) | `ci-runner` (ephemeral) | 1 per pipeline run | CPU = 1, Memory = 2 Gi (Docker container) |
| **import‑schema** (Java library) | Not deployed – used at build time by `backend` CI job | – | – |

---

## 4.4 Network Topology
### 4.4.1 Network Zones
| Zone | CIDR | Purpose | Hosted Containers |
|------|------|---------|-------------------|
| **DMZ** | 10.0.0.0/24 | Public‑facing services, load‑balancer termination | `frontend` (NGINX), external API gateway |
| **App‑Internal** | 10.0.1.0/24 | Private cluster network, service‑to‑service traffic | `backend`, `frontend` pods |
| **Database** | 10.0.2.0/24 | Isolated DB subnet, no direct internet access | `db-node` |
| **CI** | 10.0.3.0/24 | Build & test execution environment | `ci-runner` |

### 4.4.2 Firewall / Security Groups
| Source | Destination | Port(s) | Protocol | Comment |
|--------|-------------|--------|----------|---------|
| Internet (any) | DMZ (NGINX) | 80,443 | TCP | Public HTTP/HTTPS entry point |
| DMZ | App‑Internal | 8080 | TCP | Frontend proxies API calls to backend |
| App‑Internal | Database | 5432 | TCP | Backend accesses PostgreSQL (restricted to pod CIDR) |
| CI | App‑Internal | 8080 | TCP | Integration tests hit backend endpoints |
| CI | Database | 5432 | TCP | Schema validation during CI |

---

## 4.5 Environment Configuration
| Environment | Kubernetes Namespace | Config Sources | Notable Differences |
|-------------|----------------------|----------------|----------------------|
| **Development** | `dev` | Local `.env` files, Minikube | Debug logging enabled, lower replica count |
| **Staging** | `staging` | Helm values from `values‑staging.yaml` | Uses a read‑replica of the production DB, feature‑flags off |
| **Production** | `prod` | Helm values from `values‑prod.yaml`, AWS Parameter Store | Autoscaling enabled, strict CSP, TLS termination at ALB |

---

## 4.6 Scaling Strategy
| Container | Scaling Type | Trigger | Min Replicas | Max Replicas |
|-----------|--------------|---------|--------------|--------------|
| **backend** | Horizontal Pod Autoscaler (CPU‑based) | CPU > 70 % for 2 min | 2 | 10 |
| **frontend** | Horizontal Pod Autoscaler (request‑based) | Avg. QPS > 500 | 2 | 6 |
| **e2e‑xnp** | On‑demand (CI pipeline) | One run per merge request | 0 (no persistent pods) | 1 |

---

## 4.7 Disaster Recovery
| Component | Backup Strategy | RTO (Recovery Time Objective) | RPO (Recovery Point Objective) |
|-----------|----------------|--------------------------------|--------------------------------|
| **PostgreSQL DB** | Automated snapshots (daily) + point‑in‑time recovery (PITR) | 15 min | 5 min |
| **Backend JARs** | Artifact repository versioning (Nexus) | < 5 min (redeploy from repo) | N/A |
| **Frontend assets** | CDN cache + S3 versioned bucket | < 5 min | N/A |
| **CI configuration** | GitLab repository (mirrored) | < 1 min | N/A |

---

## 4.8 Deployment Diagram
The visual representation of the deployment view is stored as a Draw.io file:

```
📁 c4/c4-deployment.drawio
```
It follows the SEAGuide C4 conventions (blue boxes for internal nodes, gray for external, cylinders for the PostgreSQL database, and dashed boundaries for network zones).

---

*Document generated on 2026‑02‑07. All tables reflect the current architecture facts extracted from the knowledge base.*
