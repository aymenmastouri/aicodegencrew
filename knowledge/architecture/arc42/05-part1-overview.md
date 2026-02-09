# 5 – Building Block View (Part 1)

## 5.1 Overview

### A‑Architecture (Functional View)

| Layer | Business Capability | Typical Stereotypes |
|-------|---------------------|----------------------|
| **Presentation** | User interaction, UI composition, client‑side validation | `directive`, `module`, `component`, `controller`, `pipe` |
| **Application** | Orchestration of use‑cases, transaction handling, application services | `service` |
| **Domain** | Core business rules, data model, invariants | `entity` |
| **Data‑Access** | Persistence, repository abstraction, data mapping | `repository` |
| **Infrastructure** | Configuration, cross‑cutting concerns (e.g., scheduling) | `configuration` |
| **Unknown / Technical** | Technical glue, adapters, guards, interceptors, resolvers, REST interfaces, schedulers | `adapter`, `guard`, `interceptor`, `resolver`, `rest_interface`, `scheduler` |

The functional decomposition follows a classic **DDD‑inspired layered architecture**.  Each layer only depends on the layers directly below it, enforcing a strict direction of knowledge flow.

### T‑Architecture (Technical View)

| Container | Technology | Primary Role |
|-----------|------------|--------------|
| **backend** | Spring Boot (Gradle) | Core business services, REST API, data‑access, domain model |
| **frontend** | Angular (npm) | Rich client UI, SPA, routing, state management |
| **jsApi** | Node.js (npm) | Auxiliary JavaScript API for legacy integrations |
| **e2e‑xnp** | Playwright (npm) | End‑to‑end UI test harness |
| **import‑schema** | Java/Gradle library | Schema import utilities (no runtime components) |

### Building Block Hierarchy (Counts per Stereotype)

| Stereotype | Count |
|------------|-------|
| `rest_interface` | 21 |
| `controller` | 32 |
| `service` | 184 |
| `repository` | 38 |
| `module` | 16 |
| `component` | 169 |
| `pipe` | 67 |
| `directive` | 3 |
| `adapter` | 50 |
| `resolver` | 4 |
| `guard` | 1 |
| `interceptor` | 4 |
| `entity` | 360 |
| `scheduler` | 1 |
| `configuration` | 1 |

**Total components:** 951 &nbsp;&nbsp;| **Total interfaces:** 226 &nbsp;&nbsp;| **Total relations:** 190

---

## 5.2 Whitebox Overall System (Level 1)

### Container Overview Diagram (ASCII)

```
+-------------------+        +-------------------+        +-------------------+
|   frontend       |        |   backend         |        |   jsApi           |
|  (Angular)       | <----> | (Spring Boot)     | <----> | (Node.js)         |
+-------------------+        +-------------------+        +-------------------+
        ^                               ^
        |                               |
        |                               |
+-------------------+        +-------------------+
| e2e‑xnp (Playwright) |    | import‑schema (Java) |
+-------------------+        +-------------------+
```

*Arrows denote HTTP/REST communication (frontend ↔ backend) and internal module calls (backend ↔ jsApi). The test container (`e2e‑xnp`) interacts only with the frontend during automated UI tests.*

### Container Responsibilities

| Container | Technology | Purpose | Component Count |
|-----------|------------|---------|-----------------|
| **backend** | Spring Boot | Exposes REST API, hosts application & domain logic, data‑access, configuration | 494 |
| **frontend** | Angular | SPA UI, client‑side routing, state management, presentation layer | 404 |
| **jsApi** | Node.js | Helper API for legacy systems, thin façade for backend services | 52 |
| **e2e‑xnp** | Playwright | Automated end‑to‑end UI tests, regression suite | 0 |
| **import‑schema** | Java/Gradle | Build‑time schema import utilities, code generation | 0 |

### Layer Dependency Rules (ASCII)

```
Presentation  -->  Application  -->  Domain  -->  Data‑Access  -->  Infrastructure
      ^                ^               ^                ^
      |                |               |                |
   (frontend)      (backend)       (backend)        (backend)
```

*Only downward dependencies are allowed.  The `unknown/technical` stereotypes (adapters, guards, etc.) reside in the **Application** or **Infrastructure** layers depending on their role.*

### Component Distribution Across Containers

| Container | Presentation | Application | Domain | Data‑Access | Unknown/Technical |
|-----------|--------------|-------------|--------|-------------|-------------------|
| **backend** | 32 | 42 | 360 | 38 | 22 |
| **frontend** | 214 | 131 | – | – | 59 |
| **jsApi** | 41 | 11 | – | – | – |
| **e2e‑xnp** | – | – | – | – | – |
| **import‑schema** | – | – | – | – | – |

The **backend** container holds the majority of the domain model (360 entities) and all data‑access components. The **frontend** concentrates the presentation artefacts (214 components) and a substantial share of application‑level services (131). The **jsApi** provides a lightweight bridge for legacy integrations.

---

*All numbers are derived from the architecture facts extracted from the code base (see Section 5.1). The diagrams follow the SEAGuide principle of “graphics first” – they convey the essential structure without textual duplication.*
