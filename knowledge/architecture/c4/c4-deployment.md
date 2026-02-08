# C4 Level 4: Deployment Diagram

## 4.1 Overview
The deployment view describes **where** the five logical containers of the *uvz* system are provisioned, the infrastructure nodes that host them, and the network topology that connects them. It is the concrete realization of the C4 Container model for production, test and development environments.

## 4.2 Infrastructure Nodes
| Node ID | Type | Specification | Purpose |
|---------|------|---------------|---------|
| `k8s-cluster` | Kubernetes Cluster | 3‑node (2×CPU‑8GB, 1×CPU‑16GB) | Hosts all containerised workloads in production and staging |
| `aws-rds` | Managed PostgreSQL | db.t3.medium, 100 GB storage | Persists relational data for the **backend** container |
| `s3-bucket` | Object Store | Standard tier, versioning enabled | Stores document binaries, archives and audit logs |
| `ci-cd-runner` | VM (Ubuntu 22.04) | 2 vCPU, 4 GB RAM | Executes Playwright end‑to‑end tests (`e2e‑xnp`) |
| `dev‑machine` | Local workstation | Any OS, Docker Desktop | Development environment for frontend, jsApi and import‑schema |

## 4.3 Container‑to‑Node Mapping
| Container | Node | Instances (replicas) | Resources |
|----------|------|--------------------|-----------|
| `backend` (Spring Boot) | `k8s-cluster` (pod) | 3 (HA) | 1 CPU, 2 GB RAM each |
| `frontend` (Angular) | `k8s-cluster` (deployment) | 2 (blue/green) | 0.5 CPU, 1 GB RAM each |
| `jsApi` (Node.js) | `k8s-cluster` (deployment) | 2 | 0.5 CPU, 512 MB RAM each |
| `import‑schema` (Java/Gradle library) | `dev‑machine` (Docker) | 1 | 1 CPU, 2 GB RAM |
| `e2e‑xnp` (Playwright) | `ci‑cd‑runner` (container) | 1 per pipeline run | 2 CPU, 4 GB RAM |

## 4.4 Network Topology
### 4.4.1 Network Zones
| Zone | Purpose | Containers |
|------|---------|------------|
| **DMZ** | Public‑facing HTTP/HTTPS entry point | `frontend`, `jsApi` |
| **App‑Layer** | Internal service mesh, mutual TLS | `backend` |
| **Data‑Layer** | Database access, restricted to app‑layer | `aws-rds` (PostgreSQL) |
| **Test‑Layer** | Isolated CI/CD execution | `e2e‑xnp` |

### 4.4.2 Firewall Rules (selected)
| Source | Destination | Port | Protocol |
|--------|-------------|------|----------|
| Internet | `frontend` (Load‑Balancer) | 443 | TCP |
| Internet | `jsApi` (Load‑Balancer) | 443 | TCP |
| `frontend` | `backend` | 8080 | TCP |
| `jsApi` | `backend` | 8080 | TCP |
| `backend` | `aws-rds` | 5432 | TCP |
| `backend` | `s3‑bucket` | 443 | TCP |
| `ci‑cd‑runner` | `backend` (test) | 8080 | TCP |

## 4.5 Environment Configuration
| Environment | Container Versions | Scaling | Notes |
|-------------|-------------------|---------|------|
| **Development** | `frontend@latest`, `backend@snapshot`, `jsApi@latest` | Single‑replica per container | Hot‑reload enabled |
| **Staging** | Same as production, version‑pinned | 2 replicas for frontend & jsApi, 3 for backend | Pre‑prod validation |
| **Production** | Release‑tagged images | Autoscaling (CPU‑threshold 70 %) | Blue/green deployment for zero‑downtime |
| **Test** | Playwright latest | Ephemeral per CI run | Isolated network namespace |

## 4.6 Scaling Strategy
| Container | Scaling Type | Trigger | Min | Max |
|----------|--------------|---------|-----|-----|
| `backend` | Horizontal Pod Autoscaler | CPU > 70 % | 2 | 6 |
| `frontend` | Horizontal Pod Autoscaler | CPU > 60 % | 2 | 4 |
| `jsApi` | Horizontal Pod Autoscaler | CPU > 60 % | 2 | 4 |
| `e2e‑xnp` | On‑demand (CI) | Pipeline start | 0 | 1 |

## 4.7 Disaster Recovery
| Component | Backup Strategy | RTO | RPO |
|-----------|----------------|-----|-----|
| PostgreSQL (`aws‑rds`) | Automated daily snapshots + point‑in‑time recovery | 15 min | 5 min |
| S3 bucket (documents) | Versioning + cross‑region replication | 30 min | 10 min |
| Container images | Registry replication (ECR multi‑region) | N/A | N/A |
| Kubernetes state | etcd backup (hourly) | 10 min | 15 min |

## 4.8 Deployment Diagram
The visual diagram is stored as a Draw.io file: **c4-deployment.drawio**. It follows the SEAGuide C4 conventions (blue boxes for internal containers, gray for external services, cylinders for databases, person icons for users, dashed lines for network zones).

---
*Generated from real architecture facts: 5 containers, 32 controllers, 30 services, 196 REST endpoints.*
