# 05 – Building Block View (Part 1)

## 5.1 Overview (≈ 2 pages)

### A‑Architecture – Functional View

The **A‑Architecture** captures the business capabilities of the *uvz* system and maps them to logical layers.  The layers follow a classic DDD‑inspired stack:

| Layer | Business Capability | Typical Building Blocks |
|-------|----------------------|--------------------------|
| **Presentation** | UI interaction, client‑side validation | Controllers (REST), Angular components, Directives, Pipes |
| **Application** | Orchestration of use‑cases, transaction handling | Services, Schedulers, Guards, Interceptors |
| **Domain** | Core business rules, invariants | Entities, Value Objects, Domain Services |
| **Data‑Access** | Persistence, repository pattern | Repositories, DAOs, Mappers |
| **Infrastructure** | Cross‑cutting concerns, external system adapters | Adapters, Configuration, Modules |

The functional decomposition is deliberately **thin** – the diagram below shows the high‑level flow of a typical request (e.g. *Create Deed*):

```
[Client] → Controller → Service → Domain Entity → Repository → DB
```

Only the *building blocks* (controllers, services, entities, repositories) are shown; the underlying technical details are covered in the T‑Architecture.

### T‑Architecture – Technical View

The **T‑Architecture** describes the runtime containers that host the building blocks.  Five containers have been identified (see Section 5.2).  Their purpose, technology stack and component counts are summarised in the table below.

| Container | Technology | Primary Purpose | Component Count |
|-----------|------------|-----------------|-----------------|
| **backend** | Spring Boot (Java/Gradle) | Core business logic, REST API, persistence | 494 |
| **frontend** | Angular | Rich client UI, SPA, routing | 404 |
| **jsApi** | Node.js | Auxiliary JavaScript API for legacy integrations | 52 |
| **e2e‑xnp** | Playwright | End‑to‑end UI test harness | 0 |
| **import‑schema** | Java/Gradle (library) | Schema import utilities, code generation | 0 |

### Building Block Hierarchy – Stereotype Counts

The following table aggregates the **building‑block hierarchy** across the whole system.  Numbers are taken from the architecture facts and verified by the stereotype‑specific queries.

| Stereotype | Total Count |
|------------|-------------|
| adapter | 50 |
| component | 169 |
| configuration | 1 |
| controller | 32 |
| directive | 3 |
| entity | 360 |
| guard | 1 |
| interceptor | 4 |
| module | 16 |
| pipe | 67 |
| repository | 38 |
| resolver | 4 |
| rest_interface | 21 |
| scheduler | 1 |
| service | 184 |

These counts give a quick impression of the system’s **complexity** and **distribution** of responsibilities.  The majority of components belong to the *domain* (entities) and *application* (services) layers, which is typical for a data‑centric business platform.

---

## 5.2 Whitebox Overall System – Level 1 (≈ 4‑6 pages)

### Container Overview Diagram (ASCII)

```
+-------------------+      +-------------------+      +-------------------+
|   frontend       |      |   backend         |      |   jsApi           |
|   (Angular)      |<---->|   (Spring Boot)   |<---->|   (Node.js)       |
|   UI/SPA         | HTTP |   REST & Services | HTTP |   Helper API      |
+-------------------+      +-------------------+      +-------------------+
        ^   ^                     ^   ^                     ^   ^
        |   |                     |   |                     |   |
        |   +---------------------+   +---------------------+   |
        |            Playwright (e2e‑xnp)                |
        +-------------------------------------------------+
```

*Arrows denote the primary communication direction (HTTP/REST).  The **e2e‑xnp** container consumes the public API for UI tests; it does not host business code.

### Container Responsibilities Table

| Container | Technology | Purpose | Component Count |
|-----------|------------|---------|-----------------|
| **backend** | Spring Boot | Implements the core domain model, application services, REST controllers, persistence layer and cross‑cutting concerns. | 494 |
| **frontend** | Angular | Provides the single‑page application, client‑side routing, UI components, pipes and guards. | 404 |
| **jsApi** | Node.js | Exposes lightweight helper endpoints used by legacy systems and batch jobs. | 52 |
| **e2e‑xnp** | Playwright | Executes automated end‑to‑end UI tests against the public API. | 0 |
| **import‑schema** | Java/Gradle | Supplies schema‑import utilities and code‑generation helpers for build pipelines. | 0 |

### Layer Dependency Rules (Diagram)

```
+-------------------+   uses   +-------------------+   uses   +-------------------+
| Presentation      | ------> | Application       | ------> | Domain            |
+-------------------+          +-------------------+          +-------------------+
        ^                               ^                         |
        |                               |                         |
        |                               |                         v
        +--------------------------- uses --------------------------+
                              Data‑Access
```

*Rules*
- **Presentation** may only depend on **Application** services (no direct DB access).
- **Application** may call **Domain** entities and **Data‑Access** repositories.
- **Data‑Access** must not reference **Presentation** or **Application** layers.
- Cross‑cutting concerns (adapters, interceptors) are allowed to be used by any layer but are physically placed in the **Infrastructure** package.

### Component Distribution Across Containers

The container‑level breakdown of components by architectural layer (derived from the container facts) is shown below.

| Container | Presentation | Application | Domain | Data‑Access | Unknown |
|-----------|--------------|-------------|--------|-------------|---------|
| **backend** | 32 | 42 | 360 | 38 | 22 |
| **frontend** | 214 | 131 | – | – | 59 |
| **jsApi** | 41 | 11 | – | – | – |

*Observations*
- The **backend** container hosts the full stack (presentation controllers, services, domain entities, repositories) – it is the *heart* of the system.
- The **frontend** container is purely presentation‑oriented; it contains Angular components, pipes and guards.
- The **jsApi** container contains a small set of presentation‑like endpoints (41) and a handful of services (11) that act as thin wrappers around backend functionality.

### Summary of Key Building Blocks

| Stereotype | Example (Backend) | Example (Frontend) |
|------------|-------------------|--------------------|
| controller | `ActionRestServiceImpl` | – |
| service | `ArchivingServiceImpl` | – |
| entity | `DeedEntryEntity` | – |
| repository | `DeedEntryDao` | – |
| component | – | `ActionComponent` (Angular) |
| pipe | – | `DateFormatPipe` |
| directive | – | `HighlightDirective` |

The table illustrates the **distribution of responsibilities**: the backend concentrates on business logic, while the frontend focuses on UI composition.

---

*The next part of the Building Block View (Part 2) will drill down to Level 2, detailing the internal structure of each container and the interaction patterns between individual building blocks.*
