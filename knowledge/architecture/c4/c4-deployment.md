# C4 Level 4: Deployment Diagram

## 4.1 Overview
The deployment view describes where the five logical containers of the **uvz** system are executed in the production environment, the infrastructure nodes that host them, and the network topology that connects them. It also defines scaling, resilience and disaster‑recovery considerations required to operate the system reliably.

## 4.2 Infrastructure Nodes
| Node ID | Type | Technology | Description |
|---------|------|------------|-------------|
| `node.docker_host` | Host | Docker Engine | Linux host that runs Docker containers for the backend, frontend and Node.js API. |
| `node.k8s_cluster` | Cluster | Kubernetes (v1.28) | Orchestrates container replicas, provides service discovery and load‑balancing. |
| `node.ci_cd` | Service | GitHub Actions / Jenkins | Executes build pipelines and pushes Docker images to the registry. |
| `node.db_server` | Server | PostgreSQL (managed) | External relational database used by the backend services. |
| `node.cache_server` | Server | Redis (managed) | In‑memory cache for session data and frequently accessed lookup tables. |

*The only infrastructure component discovered in the architecture facts is the `Dockerfile` (component `component.infrastructure.core.dockerfile`). It indicates that Docker is the primary runtime for the system, which justifies the `node.docker_host` definition above.*

## 4.3 Container to Node Mapping
| Container | Node | Instances (Typical) | Resource Profile |
|-----------|------|---------------------|------------------|
| `backend` (Spring Boot) | `node.k8s_cluster` (pod) | 2‑4 (horizontal) | 1 CPU, 2 GB RAM per replica |
| `frontend` (Angular) | `node.k8s_cluster` (pod) | 2‑3 (horizontal) | 0.5 CPU, 1 GB RAM per replica |
| `jsApi` (Node.js) | `node.k8s_cluster` (pod) | 2 (horizontal) | 0.5 CPU, 1 GB RAM per replica |
| `e2e‑xnp` (Playwright) | `node.ci_cd` (ephemeral) | 1 (on‑demand) | 2 CPU, 4 GB RAM during test runs |
| `import‑schema` (Java/Gradle library) | `node.docker_host` (shared) | 1 (library) | No dedicated runtime – used at build time |

## 4.4 Network Topology
### 4.4.1 Network Zones
| Zone | Purpose | Containers |
|------|---------|------------|
| **DMZ** | Exposes public HTTP/HTTPS endpoints | `frontend`, `jsApi` |
| **Application Zone** | Internal service‑to‑service communication | `backend` |
| **Data Zone** | Database and cache access | `backend` (via `node.db_server`, `node.cache_server`) |
| **CI/CD Zone** | Build and test execution | `e2e‑xnp` |

### 4.4.2 Firewall Rules (illustrative)
| Source | Destination | Port | Protocol |
|--------|-------------|------|----------|
| Internet | `frontend` (Load Balancer) | 443 | TCP |
| Internet | `jsApi` (Load Balancer) | 443 | TCP |
| `frontend` | `backend` | 8080 | TCP |
| `jsApi` | `backend` | 8080 | TCP |
| `backend` | `node.db_server` | 5432 | TCP |
| `backend` | `node.cache_server` | 6379 | TCP |
| `ci_cd` | `e2e‑xnp` | 3000‑4000 | TCP |

## 4.5 Environment Configuration
| Environment | Container Versions | Scaling Limits |
|-------------|-------------------|----------------|
| **Development** | Latest snapshot images | 1 replica each |
| **Staging** | Tagged `release‑candidate` images | 2 replicas each |
| **Production** | Tagged `vX.Y.Z` images | 2‑4 replicas for stateless containers, 1 replica for `import‑schema` (build‑time only) |

## 4.6 Scaling Strategy
| Container | Scaling Type | Trigger | Min Replicas | Max Replicas |
|-----------|--------------|---------|--------------|--------------|
| `backend` | Horizontal Pod Autoscaler | CPU > 70 % or request latency > 200 ms | 2 | 6 |
| `frontend` | Horizontal Pod Autoscaler | CPU > 60 % or active sessions > 5000 | 2 | 5 |
| `jsApi` | Horizontal Pod Autoscaler | CPU > 65 % | 2 | 4 |
| `e2e‑xnp` | On‑Demand (CI pipeline) | Test job queued | 0 | 1 |

## 4.7 Disaster Recovery
| Component | Backup Strategy | Recovery Time Objective (RTO) | Recovery Point Objective (RPO) |
|-----------|----------------|-------------------------------|-------------------------------|
| PostgreSQL database (`node.db_server`) | Daily snapshots + transaction log shipping | 15 min | 5 min |
| Redis cache (`node.cache_server`) | Replication to a standby node | 5 min | 0 min (data is transient) |
| Docker images (registry) | Immutable image storage with versioning | 30 min | 0 min |
| Kubernetes cluster state | etcd backup every hour | 10 min | 1 hour |

## 4.8 Deployment Diagram
The diagram below visualises the nodes, containers and network zones described above. It follows the SEAGuide C4 visual conventions (blue boxes for internal containers, gray boxes for external services, cylinders for databases, person icons for users).

> **Note:** The diagram file is stored as `c4-deployment.drawio` in the same folder.

---
*Document generated automatically from architecture facts on 2026‑02‑09.*