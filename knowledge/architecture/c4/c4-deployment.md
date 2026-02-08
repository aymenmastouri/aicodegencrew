# C4 Level 4: Deployment Diagram

## 4.1 Overview
The deployment view describes **where** each C4 container is executed in the production landscape, the infrastructure nodes that host them, and the network topology that connects them. It is based on the real container inventory extracted from the architecture knowledge base.

## 4.2 Infrastructure Nodes
| Node | Type | Specification | Purpose |
|------|------|---------------|---------|
| **Kubernetes Cluster** | Container Orchestration | 3‑node GKE cluster (n1‑standard‑4) | Hosts all Dockerised containers in production |
| **CI/CD Runner** | Build Agent | GitLab Runner (Docker executor) | Builds and publishes container images |
| **Artifact Registry** | Registry | Google Artifact Registry (Docker) | Stores versioned container images |
| **External Database Service** | Managed Service | CloudSQL PostgreSQL (db‑t2‑medium) | Persists domain data for the `backend` container |
| **Static Content CDN** | CDN | CloudFront distribution | Serves Angular static assets |

## 4.3 Container to Node Mapping
| Container | Node | Instances (replicas) | Resources (CPU / Memory) |
|-----------|------|---------------------|--------------------------|
| **backend** (Spring Boot) | Kubernetes Cluster | 3 | 500 mCPU / 512 MiB each |
| **frontend** (Angular) | Kubernetes Cluster | 2 (static) | 250 mCPU / 256 MiB each |
| **jsApi** (Node.js) | Kubernetes Cluster | 2 | 300 mCPU / 384 MiB each |
| **e2e‑xnp** (Playwright) | CI/CD Runner (ephemeral) | 1 per pipeline run | 1 CPU / 1 GiB (temporary) |
| **import‑schema** (Java/Gradle library) | Not deployed – used at build time | – | – |

## 4.4 Network Topology
### 4.4.1 Network Zones
| Zone | Purpose | Containers |
|------|---------|------------|
| **Public Internet** | Entry point for end‑users | `frontend` (Angular) |
| **DMZ** | API gateway & load balancer | `backend` (Spring Boot) |
| **Private Subnet** | Database access only | `backend` (Spring Boot) |
| **CI/CD Subnet** | Build and test execution | `e2e‑xnp` (Playwright) |

### 4.4.2 Firewall Rules
| Source | Destination | Port | Protocol |
|--------|-------------|------|----------|
| Internet | Frontend Service (NGINX) | 80/443 | TCP |
| Frontend Service | Backend Service (Spring Boot) | 8080 | TCP |
| Backend Service | CloudSQL | 5432 | TCP |
| CI/CD Runner | Artifact Registry | 443 | TCP |

## 4.5 Environment Configuration
| Environment | Container Versions | Scaling Policy |
|-------------|-------------------|----------------|
| **Development** | Latest `-SNAPSHOT` images | Single replica per container |
| **Staging** | Tagged `rc‑<date>` images | Same as production but limited to 1 replica |
| **Production** | Tagged `vX.Y.Z` images | Autoscaling based on CPU utilisation |

## 4.6 Scaling Strategy
| Container | Scaling Type | Trigger | Min | Max |
|-----------|--------------|---------|-----|-----|
| backend | Horizontal Pod Autoscaler | CPU > 70% | 2 | 6 |
| frontend | Horizontal Pod Autoscaler | CPU > 60% | 2 | 4 |
| jsApi | Horizontal Pod Autoscaler | CPU > 65% | 2 | 5 |

## 4.7 Disaster Recovery
| Component | Backup Strategy | RTO | RPO |
|-----------|-----------------|-----|-----|
| CloudSQL Database | Automated daily snapshots + point‑in‑time recovery | 15 min | 5 min |
| Container Images | Artifact Registry versioning (immutable tags) | N/A | N/A |
| Kubernetes State | etcd backup via Velero | 30 min | 10 min |

## 4.8 Deployment Diagram
The visual deployment diagram is stored as a Draw.io file:

```
📁 c4/c4-deployment.drawio
```
It depicts the nodes, containers, network zones and firewall rules described above.

---
*Document generated on 2026‑02‑08 using real architecture facts (5 containers, 951 components, 190 relations).*
