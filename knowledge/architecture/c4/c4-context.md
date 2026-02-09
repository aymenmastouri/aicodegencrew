# C4 Level 1: System Context

## 1.1 Overview
The **uvz** system is a comprehensive back‑office solution for managing deed entries, documents, handover data sets and related business processes. It exposes a rich set of REST APIs and a modern Angular UI. The system is built with a **Spring Boot** backend, an **Angular** frontend, a **Node.js** API layer and supporting test and library containers.

## 1.2 System Attributes
| Attribute | Value |
|-----------|-------|
| **Name** | uvz |
| **Domain** | UNKNOWN |
| **Purpose** | Manage deed lifecycle, document archiving, handover processes and reporting via REST services and a web UI |
| **Technology Stack** | Angular, Spring Boot, Node.js, Playwright, Java/Gradle |
| **Containers (Deployable Units)** | 5 |
| **Components** | 951 |
| **Interfaces (REST endpoints)** | 196 |
| **Relations** | 190 |

## 1.3 Actors and Users
### 1.3.1 Human Actors
| Actor | Role | Primary Interactions |
|-------|------|----------------------|
| **Business User** | Operates the web UI to create, view, and manage deed entries and documents | Uses Angular frontend (HTTPS) |
| **System Administrator** | Deploys, monitors and configures the platform | Accesses backend management endpoints (HTTPS) |
| **External Service Consumer** | Calls public REST APIs for integration (e.g., document archiving) | Calls Node.js `jsApi` and Spring Boot backend (HTTPS) |

### 1.3.2 System Actors (External Systems)
| System | Role | Protocol |
|--------|------|----------|
| **Authentication Service** | Provides JWT tokens for API calls | HTTPS/REST |
| **Reporting Service** | Consumes reporting endpoints for annual reports | HTTPS/REST |
| **Document Storage** | Persists archived documents | HTTPS/REST |

## 1.4 Containers (Deployable Units)
| Container ID | Name | Type | Technology |
|--------------|------|------|------------|
| `container.backend` | backend | Application | Spring Boot (Java/Gradle) |
| `container.e2e_xnp` | e2e‑xnp | Test | Playwright |
| `container.frontend` | frontend | Application | Angular |
| `container.js_api` | jsApi | Application | Node.js |
| `container.import_schema` | import‑schema | Library | Java/Gradle |

## 1.5 External Systems & Databases
| External System | Type | Purpose |
|----------------|------|---------|
| *None explicitly modelled* | – | – |

> **Note:** The current architecture does not expose dedicated external database containers in the C4 Context view; persistence is encapsulated inside the backend.

## 1.6 Communication Protocols
| From | To | Protocol | Data Format |
|------|----|----------|-------------|
| Human Actor → Frontend | `container.frontend` | HTTPS (TLS) | JSON/HTML |
| Frontend → Backend API | `container.backend` | HTTPS (TLS) | JSON |
| Frontend → Node.js API | `container.js_api` | HTTPS (TLS) | JSON |
| Backend → Test Container | `container.e2e_xnp` | HTTP (internal) | JSON |
| Backend → Library | `container.import_schema` | Java method calls | – |

## 1.7 REST API Surface (selected endpoints)
| Method | Path |
|--------|------|
| POST | `/uvz/v1/action/{type}` |
| GET | `/uvz/v1/action/{id}` |
| POST | `/uvz/v1/archiving/sign-submission-token` |
| GET | `/uvz/v1/deedentries` |
| POST | `/uvz/v1/deedentries` |
| PUT | `/uvz/v1/deedentries/{id}` |
| DELETE | `/uvz/v1/deedentries/{id}` |
| GET | `/uvz/v1/documents/{deedEntryId}/document-copies` |
| POST | `/uvz/v1/documents/operation-tokens` |
| PATCH | `/uvz/v1/job/retry` |
| GET | `/uvz/v1/reports/annual` |
| … | *(total 196 endpoints)* |

## 1.8 System Context Diagram
The diagram is stored as a Draw.io file: **c4-context.drawio**. It visualises the system as a black‑box surrounded by the actors and external services listed above, using the standard C4 colour conventions (blue for internal containers, gray for external systems, person icons for human actors).

---
*Document generated automatically from architecture facts (statistics, containers, controllers and REST endpoints).*
