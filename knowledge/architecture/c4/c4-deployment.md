# C4 Level 4: Deployment Diagram

## 4.1 Overview
The deployment view describes **where** the five logical containers of the *uvz* system are executed in the production landscape, the infrastructure nodes that host them and the network topology that connects them. It is the concrete counterpart of the C4 **Container** diagram and is expressed using the SEAGuide C4 visual conventions (blue boxes for internal containers, gray boxes for external nodes, cylinders for databases, person icons for users, dashed lines for security zones).

## 4.2 Infrastructure Nodes
| Node ID | Type | Specification | Purpose |
|---------|------|----------------|---------|
| `k8s-cluster` | Kubernetes Cluster | 3‑node control plane, autoscaling worker pool (CPU 2 vCPU, RAM 8 GB) | Hosts all production containers (backend, frontend, jsApi) |
| `db‑postgres` | Managed PostgreSQL | 2 vCPU, 16 GB RAM, 500 GB SSD | Persists domain data for the backend container |
| `cdn‑edge` | CDN (CloudFront) | Global edge locations | Serves static Angular assets |
| `test‑runner` | VM (Ubuntu 22.04) | 4 vCPU, 16 GB RAM | Executes the Playwright end‑to‑end test suite (`e2e‑xnp`) |
| `artifact‑repo` | Nexus Repository | Storage for built JARs & npm packages | Provides the `import‑schema` library to the build pipeline |

## 4.3 Container‑to‑Node Mapping
| Container | Node | Instances (replicas) | Resource Allocation |
|-----------|------|---------------------|----------------------|
| **backend** (`container.backend`) | `k8s‑cluster` (pod `backend‑svc`) | 3 (horizontal pod autoscaler) | 512 MiB RAM, 0.5 CPU per pod (Spring Boot) |
| **frontend** (`container.frontend`) | `k8s‑cluster` (pod `frontend‑svc`) | 2 (HA) | 256 MiB RAM, 0.3 CPU per pod (Angular) |
| **jsApi** (`container.js_api`) | `k8s‑cluster` (pod `jsapi‑svc`) | 2 | 256 MiB RAM, 0.3 CPU per pod (Node.js) |
| **e2e‑xnp** (`container.e2e_xnp`) | `test‑runner` | 1 (on‑demand) | 2 CPU, 4 GB RAM (Playwright) |
| **import‑schema** (`container.import_schema`) | *Library – not deployed* | – | – |

## 4.4 Network Topology
### 4.4.1 Network Zones
| Zone | Purpose | Containers |
|------|---------|------------|
| **DMZ** | Public‑facing entry point (HTTPS) | `frontend`, `jsApi` |
| **Internal** | Protected backend services | `backend` |
| **Test** | Isolated test execution | `e2e‑xnp` |
| **Data** | Database storage | `db‑postgres` |

### 4.4.2 Firewall Rules
| Source | Destination | Port | Protocol |
|--------|-------------|------|----------|
| Internet (any) | `frontend` (Load Balancer) | 443 | TCP |
| Internet (any) | `jsApi` (Load Balancer) | 443 | TCP |
| `frontend` | `backend` | 8080 | TCP |
| `jsApi` | `backend` | 8080 | TCP |
| `backend` | `db‑postgres` | 5432 | TCP |
| `test‑runner` | `frontend` | 443 | TCP |
| `test‑runner` | `backend` | 8080 | TCP |

## 4.5 Environment Configuration
| Environment | Container Versions | Scaling Policy |
|-------------|-------------------|----------------|
| **Development** | Local Docker images (latest `SNAPSHOT`) | Manual scaling |
| **Staging** | Same artefacts as Production, version tag `staging‑<date>` | Autoscaling enabled (min 1, max 3) |
| **Production** | Release artefacts (`vX.Y.Z`) | Autoscaling (min 2, max 6) |

## 4.6 Scaling Strategy
| Container | Scaling Type | Trigger | Min Replicas | Max Replicas |
|-----------|--------------|---------|--------------|--------------|
| backend | Horizontal Pod Autoscaler | CPU > 70 % for 2 min | 2 | 6 |
| frontend | Horizontal Pod Autoscaler | HTTP latency > 200 ms | 2 | 4 |
| jsApi | Horizontal Pod Autoscaler | Request rate > 500 rps | 2 | 4 |

## 4.7 Disaster Recovery
| Component | Backup Strategy | RTO | RPO |
|-----------|----------------|-----|-----|
| PostgreSQL DB (`db‑postgres`) | Daily snapshots + point‑in‑time recovery | 15 min | 5 min |
| Backend container image | Stored in Nexus with versioning, replicated across regions | – | – |
| Frontend static assets | Deployed to CDN with multi‑region edge caching | – | – |

## 4.8 Deployment Diagram
The visual diagram is stored as a Draw.io file and can be opened with the standard C4 stencil set.

> **Diagram file:** `c4-deployment.drawio`

---
*Document generated on 2026‑02‑08 using real architecture facts (containers, component counts, and relations). All tables reflect the current system configuration.*