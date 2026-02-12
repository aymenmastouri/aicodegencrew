# C4 Level 4: Deployment Diagram

## 4.1 Overview
The Deployment View describes **where** the five logical containers of the *uvz* system are executed in the production environment, how they are grouped into infrastructure nodes, and how they communicate over the network. It provides the basis for operations, capacity planning, scaling, and disaster‑recovery decisions.

## 4.2 Infrastructure Nodes
| Node ID | Type | Specification | Purpose |
|---------|------|---------------|---------|
| `k8s-master` | Kubernetes Master | 4 vCPU / 16 GB RAM | Orchestrates container scheduling, service discovery and health‑checking. |
| `k8s-worker-01` | Kubernetes Worker | 8 vCPU / 32 GB RAM | Hosts the *backend* Spring‑Boot service and the *import‑schema* library. |
| `k8s-worker-02` | Kubernetes Worker | 8 vCPU / 32 GB RAM | Hosts the *frontend* Angular SPA and the *jsApi* Node.js service. |
| `k8s-worker-03` | Kubernetes Worker | 4 vCPU / 16 GB RAM | Executes the *e2e‑xnp* Playwright test suite (CI/CD pipeline). |
| `load‑balancer` | HAProxy / Nginx | 2 vCPU / 4 GB RAM | Terminates TLS, distributes HTTP traffic to the frontend and backend services. |
| `postgres‑db` | PostgreSQL (managed) | 4 vCPU / 16 GB RAM, 500 GB SSD | Persists domain data accessed by the backend container. |

## 4.3 Container‑to‑Node Mapping
| Container | Node(s) | Instances (replicas) | Resource Requests |
|-----------|--------|----------------------|-------------------|
| `backend` (Spring Boot) | `k8s-worker-01` | 3 (horizontal pod autoscaler) | 500 mCPU / 512 MiB per pod |
| `frontend` (Angular) | `k8s-worker-02` | 2 (static assets served via Nginx side‑car) | 250 mCPU / 256 MiB |
| `jsApi` (Node.js) | `k8s-worker-02` | 2 | 300 mCPU / 300 MiB |
| `import‑schema` (Java library) | `k8s-worker-01` | 1 (run as init‑container) | 200 mCPU / 256 MiB |
| `e2e‑xnp` (Playwright) | `k8s-worker-03` | 1 (CI job) | 1 CPU / 1 GiB |
| `postgres‑db` | `postgres‑db` (external) | 1 (primary) + 1 (standby) | – |

## 4.4 Network Topology
### 4.4.1 Network Zones
| Zone | CIDR | Purpose | Containers |
|------|------|---------|------------|
| `dmz` | 10.0.0.0/24 | Public‑facing services (HTTPS) | `load‑balancer` |
| `app‑internal` | 10.0.1.0/24 | Application traffic only | `backend`, `frontend`, `jsApi`, `import‑schema` |
| `db‑internal` | 10.0.2.0/24 | Database traffic | `postgres‑db` |
| `ci‑pipeline` | 10.0.3.0/24 | Test execution | `e2e‑xnp` |

### 4.4.2 Firewall Rules
| Source Zone | Destination Zone | Port(s) | Protocol | Comment |
|-------------|------------------|---------|----------|---------|
| `dmz` | `app‑internal` | 443 | TCP | HTTPS inbound to load‑balancer, then to frontend/backend |
| `app‑internal` | `db‑internal` | 5432 | TCP | Backend DB access |
| `ci‑pipeline` | `app‑internal` | 443 | TCP | End‑to‑end test execution |
| `app‑internal` | `dmz` | 80,443 | TCP | Health‑check callbacks |

## 4.5 Environment Configuration
| Environment | Namespace | Scaling Policy | Notes |
|-------------|-----------|----------------|------|
| Development | `uvz-dev` | Manual replica count | Uses lightweight in‑memory DB for fast feedback |
| Staging | `uvz-staging` | Autoscaling (min 2 / max 5) | Mirrors production traffic patterns |
| Production | `uvz-prod` | Autoscaling (min 3 / max 10) | High‑availability, zero‑downtime deployments |

## 4.6 Scaling Strategy
| Container | Scaling Type | Trigger | Min Replicas | Max Replicas |
|-----------|--------------|---------|--------------|--------------|
| `backend` | Horizontal Pod Autoscaler | CPU > 70 % for 2 min | 3 | 10 |
| `frontend` | Horizontal Pod Autoscaler | HTTP request latency > 200 ms | 2 | 6 |
| `jsApi` | Horizontal Pod Autoscaler | CPU > 65 % | 2 | 5 |
| `import‑schema` | Fixed | N/A (run on startup) | 1 | 1 |
| `e2e‑xnp` | On‑Demand | CI pipeline trigger | 0 | 1 |

## 4.7 Disaster Recovery
| Component | Backup Strategy | RTO (Recovery Time Objective) | RPO (Recovery Point Objective) |
|-----------|----------------|--------------------------------|--------------------------------|
| PostgreSQL primary | Daily physical backup + WAL archiving, standby replica in another AZ | 5 min | 15 min |
| Backend service configuration (Spring profiles) | Git‑ops versioned in repository, Helm chart stored in artifact repo | 2 min | N/A |
| Frontend static assets | Stored in object storage (S3‑compatible) with versioning | 1 min | N/A |
| CI test results (`e2e‑xnp`) | Retained 30 days in artifact store | – | – |

## 4.8 Deployment Diagram
The diagram below visualises the nodes, containers, and network zones described above. It follows the **C4‑SEAGuide** visual conventions (blue boxes for internal containers, gray boxes for external services, cylinders for databases, person icons for users, dashed lines for security boundaries).

> **Note**: The actual Draw.io file is stored as `c4-deployment.drawio` in the repository.

---
*Document generated on 2026‑02‑12 using real architecture facts.*
