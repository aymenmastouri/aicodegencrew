# C4 Level 4: Deployment Diagram

## 4.1 Overview
The Deployment View describes **where** the five logical containers of the *uvz* system are hosted, how they are network‑connected, and which infrastructure nodes (servers, clusters, cloud services) are used in the three main environments – Development, Test/Staging and Production.  It complements the Container diagram (C4‑L2) by adding concrete runtime locations, scaling characteristics and disaster‑recovery provisions.

---

## 4.2 Infrastructure Nodes
| Node ID | Type | Technology / Platform | Typical Specification | Role |
|---------|------|-----------------------|----------------------|------|
| `k8s‑cluster‑prod` | Kubernetes Cluster | Amazon EKS (K8s 1.27) | 3‑node m5.large (2 vCPU, 8 GB) + autoscaling group | Hosts all production containers (backend, frontend, jsApi) |
| `k8s‑cluster‑stage` | Kubernetes Cluster | Amazon EKS (K8s 1.27) | 2‑node t3.medium (2 vCPU, 4 GB) | Hosts staging containers; mirrors production topology |
| `ci‑runner‑e2e` | CI Runner | GitHub Actions / self‑hosted runner (Ubuntu 22.04) | 4 vCPU, 16 GB RAM | Executes the `e2e‑xnp` Playwright test suite on each PR |
| `static‑cdn‑frontend` | CDN / Edge | Amazon CloudFront + S3 bucket | Global edge locations | Serves the compiled Angular SPA (`frontend` container) |
| `db‑postgres‑prod` | Managed Database | Amazon RDS PostgreSQL 15 | db.m5.large (2 vCPU, 8 GB) | Persists domain data for the `backend` container |

---

## 4.3 Container‑to‑Node Mapping
| Container | Deployed Node | Instances (replicas) | Resource Limits |
|-----------|---------------|----------------------|-----------------|
| **backend** (`container.backend`) | `k8s‑cluster‑prod` (namespace `uvz-prod`) | 3 (horizontal pod autoscaler) | CPU ≤ 500 m, Memory ≤ 1 Gi |
| **frontend** (`container.frontend`) | `static‑cdn‑frontend` (S3 bucket) | 1 (static files) | N/A – served by CDN |
| **jsApi** (`container.js_api`) | `k8s‑cluster‑prod` (namespace `uvz-prod`) | 2 (HA) | CPU ≤ 300 m, Memory ≤ 512 Mi |
| **import‑schema** (`container.import_schema`) | Bundled inside `backend` image (no separate runtime) | 0 (library) | N/A |
| **e2e‑xnp** (`container.e2e_xnp`) | `ci‑runner‑e2e` (GitHub Actions) | 1 per pipeline run | CPU ≤ 2 vCPU, Memory ≤ 4 Gi |

*The same mapping is reproduced for the **Staging** environment, using `k8s‑cluster‑stage` and a separate S3 bucket (`staging‑frontend`).*

---

## 4.4 Network Topology
### 4.4.1 Network Zones
| Zone | CIDR (example) | Purpose | Containers |
|------|----------------|---------|------------|
| `public‑web` | 0.0.0.0/0 (Internet) | Ingress for users | `frontend` (CDN), `jsApi` (Node.js API) |
| `app‑private` | 10.0.1.0/24 | Internal service mesh | `backend`, `jsApi` |
| `db‑private` | 10.0.2.0/24 | Database isolation | `db‑postgres‑prod` |
| `ci‑private` | 10.0.3.0/24 | CI runner isolation | `ci‑runner‑e2e` |

### 4.4.2 Firewall / Security Group Rules
| Source | Destination | Port(s) | Protocol | Comment |
|--------|-------------|--------|----------|---------|
| Internet (any) | `frontend` CDN | 80, 443 | TCP | Public HTTP/HTTPS access |
| Internet (any) | `jsApi` Service (Load Balancer) | 443 | TCP | Public API entry point |
| `app‑private` | `db‑private` | 5432 | TCP | Backend DB access (encrypted) |
| `ci‑private` | `app‑private` | 443 | TCP | Test runner calls backend APIs |
| `app‑private` | `app‑private` | 8080 | TCP | Inter‑service communication (backend ↔ jsApi) |

---

## 4.5 Environment Configuration
| Environment | Config Store | Key Differences |
|-------------|--------------|-----------------|
| **Development** | Local `.env` files + Docker Compose | Uses SQLite (embedded) instead of RDS, lower replica counts |
| **Test / Staging** | AWS Parameter Store (stage) | Feature flags disabled, API rate limits lowered |
| **Production** | AWS Secrets Manager & Parameter Store (prod) | Full‑scale replica counts, strict IAM roles, TLS‑only traffic |

---

## 4.6 Scaling Strategy
| Container | Scaling Type | Trigger | Min Replicas | Max Replicas |
|-----------|--------------|---------|--------------|--------------|
| `backend` | Horizontal Pod Autoscaler (CPU‑based) | CPU > 70 % for 2 min | 2 | 8 |
| `jsApi` | Horizontal Pod Autoscaler (Request‑rate) | Avg > 200 rps | 2 | 6 |
| `frontend` | CDN edge cache (auto‑scale) | N/A – CDN handles traffic |
| `e2e‑xnp` | On‑demand (CI) | CI pipeline start | 1 | 1 |

---

## 4.7 Disaster Recovery & Backup
| Component | Backup Strategy | Recovery Time Objective (RTO) | Recovery Point Objective (RPO) |
|-----------|----------------|------------------------------|------------------------------|
| `db‑postgres‑prod` | Automated daily snapshots + point‑in‑time recovery (PITR) | ≤ 15 min | ≤ 5 min |
| `backend` image | Stored in Amazon ECR with immutability; can be redeployed instantly | ≤ 5 min | N/A |
| `frontend` static assets | Versioned in S3 with cross‑region replication | ≤ 10 min | N/A |
| `jsApi` image | Same as backend (ECR) | ≤ 5 min | N/A |

---

## 4.8 Deployment Diagram (Draw.io)
The diagram below visualises the nodes, containers, network zones and external actors (users, external payment gateway).  It follows the **C4‑Level 4** visual conventions (blue boxes for internal containers, gray cylinders for databases, person icons for users, dashed boundaries for zones).

> **Note:** The actual `.drawio` file is stored alongside this document as `c4-deployment.drawio`.

---

## 4.9 Interaction Summary
| Actor / System | Interaction | Protocol |
|----------------|-------------|----------|
| End‑User (Browser) | Loads Angular SPA from CDN | HTTPS |
| End‑User (Browser) | Calls REST API on `jsApi` | HTTPS/JSON |
| `jsApi` Service | Calls backend business services | HTTP/JSON (internal) |
| `backend` Service | Persists / reads domain entities | JDBC over TLS |
| CI Runner | Executes Playwright end‑to‑end tests against staging URL | HTTPS |
| External Payment Gateway | Webhook callbacks to `backend` | HTTPS |

---

## 4.10 Summary
The deployment architecture is **cloud‑native**, leveraging managed services (EKS, RDS, CloudFront) for high availability and scalability.  All containers are containerised Docker images stored in a private ECR repository, orchestrated by Kubernetes.  The static frontend is off‑loaded to a CDN, reducing load on the application layer.  Security is enforced through network segmentation, security groups, and TLS‑only communication.  Backup and recovery mechanisms ensure that the production environment can be restored within minutes, meeting the required RTO/RPO.

---

*Document generated on 2026‑02‑08 using real architecture facts from the knowledge base.*