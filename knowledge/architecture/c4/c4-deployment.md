# C4 Level 4: Deployment Diagram

## 4.1 Overview
The deployment view describes **where** the five logical containers of the *uvz* system are hosted, how they are network‑connected and which infrastructure nodes are used in the three typical environments (Development, Test/Staging, Production).  It complements the Container diagram (C4‑L2) by adding concrete runtime artefacts such as Kubernetes pods, Docker images, databases and load‑balancers.

## 4.2 Infrastructure Nodes
| Node ID | Type | Technology / Platform | Primary Purpose |
|---------|------|-----------------------|-----------------|
| `k8s-cluster` | Compute | Kubernetes (v1.28) on AWS EKS | Orchestrates all Dockerised containers |
| `postgres-db` | Data Store | PostgreSQL 15 (managed RDS) | Persists domain data for the *backend* container |
| `nginx-ingress` | Edge | NGINX Ingress Controller | Terminates external HTTPS traffic and routes to internal services |
| `s3-static` | Object Store | AWS S3 | Hosts static assets (Angular bundles, images) |
| `redis-cache` | Cache | Redis 7 (Elasticache) | Session store and short‑lived caching for the *frontend* and *jsApi* |

## 4.3 Container → Node Mapping
| Container (C4‑L2) | Container ID | Technology | Deployed on Node | Replicas (Prod) | Resource Profile |
|-------------------|--------------|------------|------------------|----------------|------------------|
| Backend | `container.backend` | Spring Boot (Java/Gradle) | `k8s-cluster` (pod `backend`) | 3 | 1 CPU / 2 GiB RAM |
| Frontend | `container.frontend` | Angular (npm) | `k8s-cluster` (pod `frontend`) | 2 | 0.5 CPU / 1 GiB RAM |
| jsApi | `container.js_api` | Node.js (npm) | `k8s-cluster` (pod `jsapi`) | 2 | 0.5 CPU / 1 GiB RAM |
| e2e‑xnp (test) | `container.e2e_xnp` | Playwright (npm) | `k8s-cluster` (job `e2e-xnp`) | 1 (on‑demand) | 1 CPU / 2 GiB RAM |
| import‑schema (library) | `container.import_schema` | Java/Gradle library | Not deployed (used at build time) | – | – |

## 4.4 Network Topology
### 4.4.1 Network Zones
| Zone | CIDR (example) | Purpose | Containers |
|------|----------------|---------|------------|
| `dmz` | 10.0.0.0/24 | Public entry point – HTTPS termination | `nginx-ingress` |
| `app` | 10.0.1.0/24 | Application tier – internal service mesh | `backend`, `frontend`, `jsapi` |
| `db` | 10.0.2.0/24 | Data tier – isolated database subnet | `postgres-db` |
| `cache` | 10.0.3.0/24 | In‑memory cache tier | `redis-cache` |
| `static` | 10.0.4.0/24 | Object‑store access (S3) – internet‑facing | `s3-static` |

### 4.4.2 Firewall / Security Rules
| Source Zone | Destination Zone | Port / Protocol | Reason |
|-------------|------------------|----------------|--------|
| Internet (DMZ) | `app` (via Ingress) | 443 / TCP | HTTPS API traffic to *frontend* and *jsApi* |
| `app` | `db` | 5432 / TCP | Backend DB access |
| `app` | `cache` | 6379 / TCP | Session / cache reads |
| `app` | `static` | 443 / TCP | Retrieve Angular bundles & assets |
| `app` | `app` | 8080 / TCP | Internal service‑to‑service calls (e.g., *frontend* → *backend*) |

## 4.5 Environment Configuration
| Environment | Kubernetes Namespace | Container Image Tag | Config Sources |
|-------------|----------------------|--------------------|----------------|
| Development | `uvz-dev` | `latest‑snapshot` | Local `.env` files, ConfigMap overrides |
| Test / Staging | `uvz-staging` | `release‑candidate` | Secrets Manager, Helm values |
| Production | `uvz-prod` | `v1.2.3` (semantic version) | AWS Parameter Store, encrypted Secrets |

## 4.6 Scaling Strategy
| Container | Scaling Type | Trigger | Min Replicas | Max Replicas |
|-----------|--------------|---------|--------------|--------------|
| Backend | Horizontal Pod Autoscaler (CPU) | CPU > 70 % for 2 min | 2 | 6 |
| Frontend | Horizontal Pod Autoscaler (Requests) | HTTP 5xx > 1 % | 2 | 4 |
| jsApi | Horizontal Pod Autoscaler (Memory) | Memory > 80 % for 2 min | 2 | 4 |
| e2e‑xnp | On‑Demand Job | CI pipeline trigger | 0 | 1 |

## 4.7 Disaster Recovery
| Component | Backup Strategy | RTO (Recovery Time Objective) | RPO (Recovery Point Objective) |
|-----------|----------------|--------------------------------|--------------------------------|
| PostgreSQL DB | Automated daily snapshots + point‑in‑time recovery | 15 min | 5 min |
| Kubernetes State (etcd) | Managed EKS backups (AWS Backup) | 30 min | 10 min |
| S3 Static Assets | Versioned bucket with cross‑region replication | 5 min | 0 min |
| Redis Cache | AOF persistence + replica in another AZ | 10 min | 1 min |

## 4.8 Deployment Diagram
The visual representation of the deployment view is stored in the Draw.io file **c4-deployment.drawio**.  It follows the SEAGuide C4‑L4 conventions (blue boxes for internal containers, gray cylinders for databases, person icons for external users, dashed boundaries for zones).

---
*Document generated on 2026‑02‑09 using real architecture facts from the knowledge base.*