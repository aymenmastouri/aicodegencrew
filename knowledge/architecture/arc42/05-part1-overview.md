# 05 – Building Block View

## 5.1 Overview

The **uvz** system is organised according to the SEAGuide A‑Architecture (functional) and T‑Architecture (technical) decomposition.

### Functional (A‑Architecture) Layering
| Layer | Business Concern | Stereotype(s) | Component Count |
|-------|-------------------|---------------|-----------------|
| Presentation | UI interaction, client‑side validation | `controller`, `pipe`, `directive`, `module`, `component` | 287 |
| Application   | Orchestration of use‑cases, transaction boundaries | `service` | 184 |
| Domain        | Core business concepts, invariants | `entity` | 360 |
| Data‑Access   | Persistence, repository pattern | `repository` | 38 |
| Infrastructure| Cross‑cutting configuration, adapters | `configuration`, `adapter`, `guard`, `interceptor`, `resolver`, `scheduler`, `rest_interface` | 81 |

The functional view shows **5 logical building‑block groups** that together implement the complete set of business capabilities.  The distribution reflects a classic **Domain‑Driven Design** approach: a rich domain model (360 entities) surrounded by thin application services (184) that expose the behaviour to the presentation layer (287 UI components).

### Technical (T‑Architecture) Containerisation
The system is deployed into **five runtime containers** that map directly to the technology stack used by the development teams:

| Container | Technology | Role in the System |
|-----------|------------|--------------------|
| **backend** | Spring Boot (Java/Gradle) | Hosts the Application, Domain, Data‑Access and Infrastructure layers. Provides REST APIs, business logic and persistence. |
| **frontend** | Angular | Implements the Presentation layer – UI components, routing, client‑side validation and state management. |
| **jsApi** | Node.js | Exposes auxiliary JavaScript APIs (e.g., file conversion, lightweight data services) that are consumed by the frontend and external partners. |
| **e2e‑xnp** | Playwright | Executes end‑to‑end UI tests; runs in a dedicated container to keep test tooling isolated from production services. |
| **import‑schema** | Java/Gradle (CLI) | Provides a command‑line tool for importing and validating external data schemas; runs as a batch job in CI pipelines. |

These containers constitute the **technical building blocks** of the system.  All functional layers (except the UI) are packaged inside the *backend* container, which therefore contains the majority of components (≈ **667** components – sum of Application, Domain, Data‑Access and Infrastructure counts).  The *frontend* container holds the 287 presentation components.  The remaining three containers host a small, well‑defined set of supporting artefacts (≈ 30 components total).

## 5.2 Whitebox Overall System (Level 1)

### 5.2.1 Container Overview Diagram (ASCII)
```
+-------------------+          +-------------------+          +-------------------+
|   frontend       |          |    backend        |          |      jsApi        |
|  (Angular)       |  HTTP    | (Spring Boot)     |  REST    |   (Node.js)       |
|  +------------+  | <------> | +-------------+   | <------> | +-------------+   |
|  | UI Layer   |  |          | | Service     |   |          | | API Layer   |   |
|  +------------+  |          | | Domain      |   |          | +-------------+   |
+-------------------+          | | Repository  |   |          +-------------------+
                               | +-------------+   |
                               +-------------------+
        ^                                 ^
        |                                 |
        |                                 |
        |                                 |
+-------------------+          +-------------------+
|  e2e‑xnp          |          | import‑schema     |
| (Playwright)      |  Selenium| (Java CLI)        |
|  +------------+   | <------> | +-------------+   |
|  | Test Suite |   |          | | Batch Jobs  |   |
|  +------------+   |          | +-------------+   |
+-------------------+          +-------------------+
```
The diagram visualises the **runtime communication paths**:
* UI components call the backend via HTTP/REST.
* The backend exposes its services to the *jsApi* container for lightweight consumption.
* End‑to‑end tests in *e2e‑xnp* drive the UI and verify the full request‑response chain.
* The *import‑schema* container is invoked by CI pipelines to pre‑process data before it reaches the backend.

### 5.2.2 Container Responsibilities Table
| Container | Primary Responsibilities | Key Stereotypes Inside | Approx. #Components |
|-----------|---------------------------|------------------------|---------------------|
| **frontend** | • Render UI screens<br>• Client‑side routing<br>• Form validation<br>• State management (NgRx) | `controller`, `pipe`, `directive`, `module`, `component` | 287 |
| **backend** | • Expose REST endpoints (`rest_interface`)<br>• Execute business use‑cases (`service`)<br>• Manage domain entities (`entity`)<br>• Persist data (`repository`)<br>• Provide cross‑cutting concerns (`configuration`, `adapter`, `interceptor`, `guard`, `resolver`, `scheduler`) | `service`, `entity`, `repository`, `configuration`, `adapter`, `interceptor`, `guard`, `resolver`, `scheduler`, `rest_interface` | 667 |
| **jsApi** | • Lightweight data transformation<br>• Public JavaScript SDK for partners | `component`, `module` | ~12 |
| **e2e‑xnp** | • Automated UI acceptance tests<br>• Regression suite executed on each build | `component`, `service` (test helpers) | ~9 |
| **import‑schema** | • Schema validation and import tooling<br>• Batch processing of external data feeds | `component`, `service` | ~9 |

### 5.2.3 Quality Scenarios Reflected in the Whitebox
| Scenario ID | Description | Architectural Decision Supporting It |
|-------------|-------------|---------------------------------------|
| Q‑001 | **Response time ≤ 200 ms for UI‑initiated CRUD operations** | Services are co‑located with repositories inside the *backend* container, eliminating network hops between application and data‑access layers. |
| Q‑002 | **Zero‑downtime deployment of UI** | The *frontend* container is stateless and can be replaced behind a load‑balancer without affecting the *backend*. |
| Q‑003 | **Automated regression testing on every commit** | Dedicated *e2e‑xnp* container runs Playwright tests in isolation, guaranteeing repeatable test environments. |
| Q‑004 | **Scalable API layer** | REST endpoints are exposed via Spring Boot’s embedded Tomcat, which can be horizontally scaled behind an API gateway. |
| Q‑005 | **Secure external data import** | The *import‑schema* CLI runs in a separate container with limited network access, reducing attack surface. |

---

### 5.2.4 Summary
The white‑box view demonstrates a **clear separation of concerns**: UI concerns reside in the Angular *frontend* container, core business logic and persistence live in the Spring‑Boot *backend* container, and auxiliary concerns (testing, schema import, lightweight APIs) are isolated in their own containers.  This decomposition satisfies the functional layering required by the A‑Architecture while providing the deployment flexibility and resilience demanded by the T‑Architecture.

The next chapter will drill down into each functional building block, presenting the **Level‑2** decomposition (controllers, services, repositories, entities) together with the most important runtime interaction sequences.
