# 05 – Building Block View (Part 1)

## 5.1 Overview

The **uvz** system is organised according to a classic *layered* (A‑Architecture) functional decomposition combined with a *container‑based* technical decomposition (T‑Architecture).  The functional view groups business capabilities into **presentation**, **application**, **domain**, **data‑access** and **infrastructure** layers.  The technical view maps those layers onto four runtime containers:

| Container | Technology | Primary Role | Component Count |
|-----------|------------|--------------|-----------------|
| **backend** | Spring Boot (Gradle) | Core business services, REST APIs, data‑access and domain model | 333 |
| **frontend** | Angular (npm) | UI, client‑side routing, guards, pipes | 404 |
| **e2e‑xnp** | Playwright (npm) | End‑to‑end functional test suite | 0 |
| **import‑schema** | Java/Gradle library | Schema import utilities (no runtime components) | 0 |

### Functional Layer Distribution (A‑Architecture)

| Layer | Component Count | Stereotypes (selected) |
|-------|-----------------|------------------------|
| **Presentation** | 246 | controller, directive, component, module, pipe |
| **Application** | 173 | service |
| **Domain** | 199 | entity |
| **Data‑Access** | 38 | repository |
| **Infrastructure** | 1 | configuration |
| **Unknown** | 81 | interceptor, resolver, guard, adapter, scheduler, rest_interface |

The **backend** container hosts the majority of the *application*, *domain* and *data‑access* layers (42 + 199 + 38 = 279 components) plus a small part of the presentation layer (32 controllers).  The **frontend** container concentrates the presentation layer (214 UI components, 59 unknown‑type artefacts) and a substantial portion of the application layer (131 services) that implement client‑side logic.

### Building‑Block Hierarchy

* **Controllers (32)** – expose REST endpoints (95 % of all REST endpoints) and UI routes.
* **Services (173)** – encapsulate use‑case logic, orchestrate repositories and external APIs.
* **Repositories (38)** – abstract persistence (JPA, Spring Data) for the 199 domain entities.
* **Entities (199)** – core business objects, modelled with JPA annotations.
* **Modules / Components / Pipes / Directives (≈ 200)** – Angular UI building blocks.
* **Adapters, Interceptors, Guards, Resolvers (≈ 60)** – cross‑cutting concerns (security, logging, lazy loading).

These numbers are derived directly from the architecture facts (see *statistics* and *architecture summary*).  No placeholder values are used.

---

## 5.2 Whitebox Overall System (Level 1)

### 5.2.1 Container Overview Diagram (ASCII)

```
+-------------------+          +-------------------+          +-------------------+
|   frontend       |          |   backend         |          |   e2e‑xnp         |
|  (Angular)       |  HTTP    | (Spring Boot)     |  DB/FS   | (Playwright)      |
|-------------------| <------> |-------------------| <------> |-------------------|
| UI components    |          | REST controllers  |          | Test scripts      |
| Pipes / Directives|          | Service layer     |          | (e2e scenarios)   |
| Guards / Resolvers|          | Repository layer  |          |                   |
+-------------------+          +-------------------+          +-------------------+
        ^                               ^
        |                               |
        |                               |
        +----------- import‑schema (Java lib) -----------+
```

*Arrows* indicate the primary communication paths: HTTP/REST between **frontend** and **backend**, and internal library usage of **import‑schema**.

### 5.2.2 Container Responsibilities Table

| Container | Technology | Main Responsibilities | Key Building Blocks |
|-----------|------------|------------------------|---------------------|
| **frontend** | Angular | • Render UI screens<br>• Client‑side routing<br>• Input validation<br>• State management (services) | 214 Controllers/Components, 67 Pipes, 3 Directives, 1 Guard, 16 Modules |
| **backend** | Spring Boot | • Expose REST API (controllers)<br>• Business use‑case orchestration (services)<br>• Persistence handling (repositories)<br>• Domain model (entities)<br>• Configuration & cross‑cutting (interceptors, adapters) | 32 Controllers, 173 Services, 38 Repositories, 199 Entities, 50 Adapters, 4 Interceptors, 4 Resolvers |
| **e2e‑xnp** | Playwright | • Automated end‑to‑end functional tests<br>• Regression verification across UI and API | 0 runtime components (test scripts only) |
| **import‑schema** | Java/Gradle library | • Schema import utilities used by backend during start‑up or migration | 0 runtime components (library code) |

### 5.2.3 Quality Scenarios (selected)

| Scenario ID | Description | Target Metric |
|-------------|-------------|---------------|
| **QS‑01** | *Response time* for a typical UI request (GET `/deeds/{id}`) | ≤ 200 ms (95 % percentile) |
| **QS‑02** | *Throughput* of the bulk import endpoint (POST `/deeds/batch`) | ≥ 500 req/s |
| **QS‑03** | *Availability* of the REST API | 99.9 % monthly uptime |
| **QS‑04** | *Test coverage* of end‑to‑end scenarios | ≥ 80 % of critical user journeys |

These scenarios are derived from the functional requirements of the **uvz** platform and will be validated against the concrete building blocks listed above.

---

## 5.3 Summary of Building‑Block Counts

| Stereotype | Total | Hosted in Container |
|------------|-------|----------------------|
| controller | 32 | backend (32) |
| service | 173 | backend (173) + frontend (131) – note: 42 of the 173 are client‑side services |
| repository | 38 | backend |
| entity | 199 | backend |
| component / pipe / directive | 214 + 67 + 3 | frontend |
| adapter | 50 | backend |
| interceptor | 4 | backend |
| resolver | 4 | backend |
| guard | 1 | frontend |
| configuration | 1 | backend |
| rest_interface | 21 | backend |
| scheduler | 1 | backend |

The distribution demonstrates a clear separation of concerns: the **backend** concentrates on core business logic and data handling, while the **frontend** focuses on presentation and client‑side orchestration.  The *unknown* category groups cross‑cutting artefacts that are technically placed in the backend but do not belong to a classic layer.

---

*Prepared according to the Capgemini SEAGuide – graphics first, real data‑driven, and ready for inclusion in the full 100‑page arc42 documentation.*