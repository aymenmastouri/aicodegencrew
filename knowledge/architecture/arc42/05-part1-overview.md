# 05 – Building Block View (Part 1)

## 5.1 Overview

### A‑Architecture – Functional View

The **A‑Architecture** captures the *business capabilities* that the system delivers.  In the UVZ solution the capabilities are organised in the classic **onion‑style** layers that map directly to the DDD bounded‑contexts used during development.

| Layer | Primary Business Capability | Example Use‑Cases |
|-------|----------------------------|-------------------|
| **Presentation** | User interaction & UI orchestration | Search deeds, view reports, manage hand‑over data sets |
| **Application** | Coordination of use‑cases, transaction handling | Start archiving job, trigger number‑gap management |
| **Domain** | Core business rules & invariants | Validate deed entry, enforce signature rights |
| **Data‑Access** | Persistence & retrieval of aggregates | Store `DeedEntryEntity`, query `UvzNumberManagerEntity` |
| **Infrastructure** | Cross‑cutting services (security, logging, scheduling) | JWT validation, audit logging, background job scheduler |

The functional view is deliberately *technology‑agnostic* – it only describes **what** the system does, not **how** it is realised.

---

### T‑Architecture – Technical View

The **T‑Architecture** shows the concrete *technical containers* that host the building blocks defined above.  The containers are deployed as separate artefacts (Docker images, JVM processes, or static web assets) and communicate via well‑defined interfaces (REST, WebSocket, internal Java calls).

#### Container Overview (ASCII diagram)

```
+-------------------+      +-------------------+      +-------------------+
|   frontend       |      |   backend         |      |   jsApi           |
|   (Angular)      |<---->|   (Spring Boot)   |<---->|   (Node.js)       |
|   HTTP/HTTPS     | REST |   REST + gRPC     | RPC  |   HTTP/HTTPS      |
+-------------------+      +-------------------+      +-------------------+
        ^   ^                     ^   ^                     ^   ^
        |   |                     |   |                     |   |
        |   +---------------------+   +---------------------+   |
        |            Playwright e2e‑xnp (test)                |
        +------------------------------------------------------+
```

* **frontend** – Angular SPA serving the UI.  Deployed as a static web‑app behind an NGINX reverse‑proxy.
* **backend** – Spring‑Boot application containing the bulk of the business logic, data‑access and REST endpoints.
* **jsApi** – Node.js library exposing a thin JavaScript façade for legacy integrations.
* **e2e‑xnp** – Playwright based end‑to‑end test harness (non‑functional container).
* **import‑schema** – Java/Gradle library used at build‑time to generate database schemas (no runtime components).

---

### Building Block Hierarchy – Counts per Stereotype

The following table summarises the *building blocks* (components) that have been identified by the static analysis of the code base.  Numbers are taken from the architecture facts and verified by the stereotype‑specific queries.

| Stereotype | Total Count |
|------------|------------:|
| **controller** | 32 |
| **service** | 184 |
| **repository** | 38 |
| **entity** | 360 |
| **adapter** | 50 |
| **component** | 169 |
| **module** | 16 |
| **pipe** | 67 |
| **directive** | 3 |
| **guard** | 1 |
| **interceptor** | 4 |
| **resolver** | 4 |
| **rest_interface** | 21 |
| **scheduler** | 1 |
| **configuration** | 1 |
| **configuration** (duplicate entry removed) |
| **total components** | 951 |

These numbers give a quick impression of the *complexity* of the system and are the basis for the subsequent white‑box analysis.

---

## 5.2 Whitebox Overall System (Level 1)

### Container Overview Diagram (ASCII – Level 1)

```
+---------------------------------------------------------------+
|                         UVZ System                           |
|                                                               |
|  +-------------------+   +-------------------+   +-----------+ |
|  |   frontend        |   |   backend         |   |   jsApi   | |
|  |   (Angular)       |   |   (Spring Boot)   |   | (Node.js) | |
|  +-------------------+   +-------------------+   +-----------+ |
|          |                       |                     |      |
|          |   REST / JSON API    |   RPC / HTTP       |      |
|          v                       v                     v      |
|  +-------------------------------------------------------+   |
|  |               e2e‑xnp (Playwright) – Test Suite       |   |
|  +-------------------------------------------------------+   |
|                                                               |
|  +-------------------------------------------------------+   |
|  |               import‑schema (Java/Gradle) – Library    |   |
|  +-------------------------------------------------------+   |
+---------------------------------------------------------------+
```

### Container Responsibilities Table

| Container | Technology | Primary Purpose | Component Count |
|-----------|------------|-----------------|----------------:|
| **backend** | Spring Boot (Java, Gradle) | Core business logic, REST API, data‑access, scheduling | 494 |
| **frontend** | Angular (TypeScript, npm) | User interface, client‑side validation, routing | 404 |
| **jsApi** | Node.js (npm) | Lightweight façade for legacy JavaScript callers | 52 |
| **e2e‑xnp** | Playwright (npm) | End‑to‑end functional testing | 0 |
| **import‑schema** | Java/Gradle | Build‑time schema generation library | 0 |

*The component count reflects the number of classes/objects that belong to the container (as reported by the static analysis).*

---

### Layer Dependency Rules (ASCII diagram)

```
+-------------------+   uses   +-------------------+   uses   +-------------------+
| Presentation      | ------> | Application       | ------> | Domain            |
+-------------------+          +-------------------+          +-------------------+
        ^                               |                               |
        |                               | uses                          |
        |                               v                               v
+-------------------+          +-------------------+          +-------------------+
| Infrastructure   | <------ | Data‑Access       | <------ | Infrastructure   |
+-------------------+          +-------------------+          +-------------------+
```

*Rules enforced by the architecture:*  
1. **Presentation** may only call **Application** services.  
2. **Application** may call **Domain** objects and **Data‑Access**.  
3. **Domain** must not depend on any outer layer.  
4. **Infrastructure** may be used by any layer but must not depend on them.

---

### Component Distribution Across Containers

| Container | Total Components | Presentation | Application | Domain | Data‑Access | Infrastructure |
|-----------|-----------------:|------------:|------------:|-------:|------------:|----------------:|
| **backend** | 494 | 32 | 42 | 360 | 38 | 22 |
| **frontend** | 404 | 214 | 131 | – | – | 59 |
| **jsApi** | 52 | 41 | 11 | – | – | – |
| **e2e‑xnp** | 0 | – | – | – | – | – |
| **import‑schema** | 0 | – | – | – | – | – |

The distribution shows that the **backend** container holds the overwhelming majority of *domain* and *data‑access* components, while the **frontend** concentrates the *presentation* logic.  The **jsApi** container is a thin glue layer exposing a subset of the backend functionality to external JavaScript consumers.

---

## Summary

* The **A‑Architecture** defines five logical layers that map directly to the business capabilities of the UVZ system.
* The **T‑Architecture** consists of five technical containers, each with a clear responsibility and technology stack.
* A total of **951** building blocks have been identified, with the most significant counts in the **entity (360)**, **service (184)** and **controller (32)** stereotypes.
* Dependency rules enforce a strict onion‑style layering, preventing leakage of domain logic into outer layers.
* Component distribution confirms the expected separation: domain‑centric code lives in the Spring‑Boot backend, UI code lives in the Angular frontend, and auxiliary artefacts are isolated in dedicated containers.

*All numbers are derived from the live architecture facts (statistics, container queries and stereotype listings).*
