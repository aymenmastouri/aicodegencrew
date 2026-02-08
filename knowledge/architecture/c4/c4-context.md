# C4 Level 1 – System Context

## 1.1 Overview
The **uvz** system is a comprehensive deed‑entry management platform.  It exposes a rich set of REST APIs (≈ 196 endpoints) that support creation, modification, signing, archiving and reporting of deed entries.  The system is built with a **Spring Boot** backend, an **Angular** frontend, a **Node.js** JavaScript API and a Playwright based end‑to‑end test suite.

## 1.2 The System
| Attribute | Value |
|-----------|-------|
| **Name** | uvz |
| **Type** | Enterprise application (backend + frontend) |
| **Purpose** | Manage deed entries, signatures, hand‑over processes and related reporting |
| **Domain** | Not explicitly defined in the source facts |
| **Technology Stack** | Spring Boot, Angular, Node.js, Playwright, Gradle, npm |
| **Containers** | backend, frontend, jsApi, e2e‑xnp, import‑schema |

## 1.3 Actors and Users
### 1.3.1 Human Actors
| Actor | Role | Primary Interactions |
|-------|------|----------------------|
| **Deed Clerk** | Creates, updates and signs deed entries via the web UI | Uses the Angular frontend (HTTPS) to call the backend REST API |
| **Administrator** | Configures system, monitors jobs, manages security | Accesses management endpoints (e.g. `/uvz/v1/job/metrics`) |
| **External Notary** | Consumes signed deed documents | Calls public REST endpoints (e.g. `/uvz/v1/documents/{deedEntryId}/document-copies`) |

### 1.3.2 System Actors
| System | Role | Protocol |
|--------|------|----------|
| **Frontend (Angular)** | Presentation layer for human users | HTTPS/REST |
| **JavaScript API (Node.js)** | Provides auxiliary services to the frontend | HTTPS/REST |
| **Playwright Test Suite** | Automated end‑to‑end verification | Internal HTTP calls |

## 1.4 External Systems
| External System | Purpose | Protocol |
|----------------|---------|----------|
| **Document Archive Service** (not part of the code base) | Stores archived deed documents | HTTPS/REST |
| **Authentication Provider** (e.g. OAuth2) | Issues JWT tokens for API access | HTTPS/OAuth2 |

> *No database containers are defined as external systems in the available facts; the backend persists data internally.*

## 1.5 Communication Protocols
| From | To | Protocol | Data Format |
|------|----|----------|------------|
| Human (Web UI) | Frontend (Angular) | HTTPS | JSON |
| Frontend (Angular) | Backend (Spring Boot) | HTTPS/REST | JSON |
| Backend (Spring Boot) | JavaScript API (Node.js) | HTTPS/REST | JSON |
| Backend | External Document Archive | HTTPS/REST | JSON |
| Backend | Authentication Provider | HTTPS/OAuth2 | JWT |

## 1.6 Context Diagram
The visual System Context diagram is stored as a Draw.io file:

- **File:** `c4/c4-context.drawio`
- **Diagram name:** *uvz – System Context*

The diagram follows the SEAGuide C4 conventions:
- Blue boxes – internal containers (backend, frontend, jsApi, e2e‑xnp, import‑schema)
- Gray boxes – external systems (Document Archive, Authentication Provider)
- Person icons – human actors (Deed Clerk, Administrator, External Notary)
- Dashed lines – trust boundaries

---
*Generated from real architecture facts (951 components, 5 containers, 196 REST endpoints).*