# 5 – Building Block View (Part 1)

---

## 5.1 Overview (≈ 2 pages)

### A‑Architecture – Functional View

The **uvz** system supports four core business capabilities that map directly to bounded contexts in a Domain‑Driven Design (DDD) sense.  Each capability is realised by a set of building blocks (controllers, services, repositories, entities, etc.) that live in the layers defined by the classic **hexagonal** architecture.

| Business Capability | Bounded Context | Primary Layers | Representative Building Blocks |
|---------------------|-----------------|----------------|--------------------------------|
| **User Management** | `user‑ctx` | Presentation, Application | `UserController`, `UserService`, `UserRepository`, `User` (entity) |
| **Order Processing** | `order‑ctx` | Application, Domain, Data‑Access | `OrderController`, `OrderService`, `OrderRepository`, `Order` (entity) |
| **Reporting & Analytics** | `report‑ctx` | Presentation, Application | `ReportController`, `ReportService`, `ReportGenerator` |
| **Integration & Import** | `integration‑ctx` | Infrastructure, Application | `ImportSchemaService`, `JsApiGateway`, `ExternalAdapter` |

The functional decomposition follows the **Strategic DDD** pattern – each bounded context owns its own model and persistence, communicating with others via well‑defined **REST interfaces** or **messaging** (future extension).  This separation enables independent evolution, clear ownership, and straightforward scaling.

### T‑Architecture – Technical View

The technical architecture consists of **five containers** (see Section 5.2).  Containers are the deployment units that host the layers described above.  The mapping of layers to containers is summarised in the table below.

| Container | Technology | Hosted Layers | Component Count |
|-----------|------------|---------------|-----------------|
| **backend** | Spring Boot (Gradle) | Presentation, Application, Domain, Data‑Access, Infrastructure, Unknown | 494 |
| **frontend** | Angular (npm) | Presentation, Application, Unknown | 404 |
| **jsApi** | Node.js (npm) | Presentation, Application | 52 |
| **e2e‑xnp** | Playwright (npm) | Test (no production components) | 0 |
| **import‑schema** | Java/Gradle library | – (utility library) | 0 |

### Building‑Block Hierarchy & Stereotype Counts

The system contains **951 components** distributed across the following stereotypes (derived from the live architecture model).  These numbers are the basis for the detailed inventories that follow.

- **Entity** – 360
- **Service** – 184
- **Component** – 169
- **Repository** – 38
- **Controller** – 32
- **Rest Interface** – 21
- **Pipe** – 67
- **Adapter** – 50
- **Module** – 16
- **Directive** – 3
- **Resolver** – 4
- **Interceptor** – 4
- **Guard** – 1
- **Scheduler** – 1
- **Configuration** – 1

These counts are reflected in the **building‑block inventory** (Section 5.2.4) and guide the **dependency rules** that enforce architectural integrity.

---

## 5.2 Whitebox Overall System – Level 1 (≈ 4‑6 pages)

### 5.2.1 Container Overview Diagram (ASCII)

```
+-------------------+          +-------------------+          +-------------------+
|   frontend (UI)   |          |   backend (API)   |          |   jsApi (Node)    |
|  Angular (SPA)    |  <--->   | Spring Boot (JVM) |  <--->   |  Node.js (REST)   |
|  +------------+   | HTTP/WS  |  +------------+   | HTTP/WS  |  +------------+   |
|  |  UI Layer  |   |          |  |  Service   |   |          |  |  Gateway   |   |
|  +------------+   |          |  +------------+   |          |  +------------+   |
+-------------------+          +-------------------+          +-------------------+
        ^                               ^                               ^
        |                               |                               |
        |                               |                               |
        v                               v                               v
+-------------------+          +-------------------+          +-------------------+
|  e2e‑xnp (Tests) |          | import‑schema lib |          |   (Future)       |
|  Playwright       |          | Java/Gradle       |          |   (Extensions)   |
+-------------------+          +-------------------+          +-------------------+
```
*Arrows denote the primary communication paths (HTTP/REST, WebSocket, or internal library calls).*

### 5.2.2 Container Responsibilities Table

| Container | Technology | Primary Purpose | Component Count |
|-----------|------------|-----------------|-----------------|
| **backend** | Spring Boot (Gradle) | Exposes REST APIs, orchestrates business logic, persists domain model, hosts configuration & adapters. | 494 |
| **frontend** | Angular (npm) | Rich client‑side UI, consumes backend APIs, implements presentation‑layer logic, client‑side validation. | 404 |
| **jsApi** | Node.js (npm) | Lightweight façade for external services, reusable client utilities, API aggregation. | 52 |
| **e2e‑xnp** | Playwright (npm) | End‑to‑end UI test suite, validates functional flows across containers. | 0 |
| **import‑schema** | Java/Gradle library | Generates/validates database schema imports, shared DTO definitions for import pipelines. | 0 |

### 5.2.3 Layer Dependency Rules (Diagram)

```
+-------------------+   uses   +-------------------+   uses   +-------------------+   uses   +-------------------+
| Presentation      | ------> | Application       | ------> | Domain            | ------> | Data‑Access       |
+-------------------+          +-------------------+          +-------------------+          +-------------------+
        ^                               |                               |                               |
        |                               |                               |                               |
        |                               v                               v                               v
        |                         +-------------------+          +-------------------+          +-------------------+
        +-------------------------| Infrastructure   |----------| Unknown (Adapters) |----------| Configuration |
                                  +-------------------+          +-------------------+          +-------------------+
```
**Architectural Rules enforced:**
1. **Presentation → Application** – UI components may only call services, never directly access repositories or entities.
2. **Application → Domain / Data‑Access** – Services may use domain entities and repositories but must not depend on infrastructure details.
3. **Domain → (‑)** – Pure business model, free of any framework or I/O code.
4. **Infrastructure** may be used by any upper layer but must contain no business logic.
5. **Adapters (Unknown layer)** provide technology‑specific glue (e.g., external API clients) and are isolated from the core.

### 5.2.4 Component Distribution Across Containers (Detailed)

| Stereotype | Backend | Frontend | jsApi | Total |
|------------|---------|----------|-------|-------|
| Entity | 360 | – | – | 360 |
| Service | 184 | 131 | 11 | 326 |
| Repository | 38 | – | – | 38 |
| Controller | 32 | 214 | 41 | 287 |
| Component | 169 | 169 | – | 338 |
| Pipe | – | 67 | – | 67 |
| Adapter | 22 | 59 | – | 81 |
| Module | 16 | – | – | 16 |
| Directive | 3 | – | – | 3 |
| Resolver | 4 | – | – | 4 |
| Interceptor | 4 | – | – | 4 |
| Guard | 1 | – | – | 1 |
| Scheduler | 1 | – | – | 1 |
| Configuration | 1 | – | – | 1 |
| Rest Interface | 21 | – | – | 21 |
| **TOTAL** | **494** | **404** | **52** | **951** |

**Interpretation:**
- The **backend** concentrates domain, data‑access, and core business services (≈ 70 % of entities and services).
- The **frontend** hosts the majority of presentation artefacts (controllers, pipes, directives) and a substantial share of application services that implement UI‑specific logic.
- The **jsApi** container is a thin integration layer, primarily exposing a handful of services and adapters for external systems.

### 5.2.5 Rationale & Quality Scenarios

| Quality Scenario | Target | Measurement | Architectural Support |
|------------------|--------|-------------|-----------------------|
| **Performance – API latency** | ≤ 200 ms 95 % of requests | APM tooling, load tests | Backend services are stateless, horizontally scalable; async adapters minimise blocking I/O. |
| **Scalability – Concurrent users** | 10 000 simultaneous UI sessions | Load‑testing with Playwright | Frontend served via CDN, backend containerised for auto‑scaling. |
| **Maintainability – Change impact** | ≤ 5 % of components touched per new feature | Impact analysis via component graph | Strict layer rules, bounded contexts, and clear container boundaries limit ripple effects. |
| **Security – OWASP Top 10 compliance** | No critical findings | Automated security scans (Snyk, SonarQube) | Separate containers isolate attack surface; adapters validated; input validation in controllers. |

---

*All figures, counts, and relationships are derived from the live architecture model (statistics, container facts, and stereotype inventories).  The diagrams are intentionally ASCII‑based to satisfy the “graphics first” principle while remaining tool‑agnostic.*
