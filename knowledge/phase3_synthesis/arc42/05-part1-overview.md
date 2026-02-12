# 05 – Building Block View (Part 1)

## 5.1 Overview

### A‑Architecture (Functional view)

The **A‑Architecture** groups the system’s business capabilities into logical layers that reflect the domain‑driven design of the *uvz* solution.  The most relevant functional blocks have been identified from the concrete component names (controllers, services, repositories and entities) that exist in the code base.

| Functional Block | Primary Domain Concepts | Mapped Layer(s) | Representative Components |
|------------------|------------------------|----------------|---------------------------|
| **Action Management** | `ActionEntity`, `ActionServiceImpl`, `ActionRestServiceImpl` | Domain, Application | `ActionEntity`, `ActionServiceImpl`, `ActionRestServiceImpl` |
| **Deed Entry & Registry** | `DeedEntryEntity`, `DeedRegistryServiceImpl`, `DeedEntryRestServiceImpl` | Domain, Application, Data‑Access | `DeedEntryEntity`, `DeedEntryDao`, `DeedEntryServiceImpl` |
| **Handover Processing** | `HandoverDataSetEntity`, `HandoverDataSetServiceImpl`, `HandoverHistoryEntity` | Domain, Application, Data‑Access | `HandoverDataSetEntity`, `HandoverDataSetDao`, `HandoverDataSetServiceImpl` |
| **Number Management** | `UvzNumberManagerEntity`, `NumberManagementServiceImpl` | Domain, Application | `UvzNumberManagerEntity`, `NumberManagementServiceImpl` |
| **Reporting & Statistics** | `ReportEntity`, `ReportServiceImpl`, `ReportRestServiceImpl` | Application, Presentation | `ReportServiceImpl`, `ReportRestServiceImpl` |
| **Security & Authentication** | `CustomMethodSecurityExpressionHandler`, `TokenAuthenticationRestTemplateConfigurationSpringBoot` | Presentation, Application | `CustomMethodSecurityExpressionHandler`, `TokenAuthenticationRestTemplateConfigurationSpringBoot` |
| **Job Scheduling & Orchestration** | `JobEntity`, `JobServiceImpl`, `JobRestServiceImpl` | Application, Presentation | `JobEntity`, `JobServiceImpl`, `JobRestServiceImpl` |
| **Document Metadata** | `DocumentMetaDataEntity`, `DocumentMetaDataServiceImpl` | Domain, Application | `DocumentMetaDataEntity`, `DocumentMetaDataServiceImpl` |
| **Successor Management** | `SuccessorBatchEntity`, `SuccessorDetailsServiceImpl` | Domain, Application | `SuccessorBatchEntity`, `SuccessorDetailsServiceImpl` |
| **Infrastructure & Configuration** | Spring Boot configuration classes, OpenAPI config | Presentation, Application | `OpenApiConfig`, `DefaultExceptionHandler` |

The functional view follows the classic **four‑layer DDD stack**:

1. **Presentation** – REST controllers, OpenAPI configuration, exception handling.
2. **Application** – Service façade, job orchestration, security helpers.
3. **Domain** – Core entities and business rules.
4. **Data‑Access** – JPA repositories / DAOs.

All components are placed in the *backend* container; the *frontend* container hosts the Angular UI, while the *jsApi* container provides a thin Node.js façade for legacy integrations.

### T‑Architecture (Technical view)

The **T‑Architecture** describes the physical deployment topology (containers) and the technologies that host the building blocks identified above.

| Container | Technology | Role |
|----------|------------|------|
| `backend` | Spring Boot (Java 17, Gradle) | Core business logic, REST API, persistence layer |
| `frontend` | Angular (TypeScript, npm) | Rich client UI, SPA, consumes backend REST services |
| `jsApi` | Node.js (npm) | Lightweight façade for external scripts, legacy API bridge |
| `e2e‑xnp` | Playwright (npm) | End‑to‑end UI test suite (non‑functional) |
| `import‑schema` | Java/Gradle library | Schema import utilities (build‑time only) |

### Building Block Hierarchy (Counts per Stereotype)

| Stereotype | Total Count |
|------------|-------------|
| controller | 32 |
| service | 184 |
| repository | 38 |
| entity | 360 |
| adapter | 50 |
| component | 169 |
| configuration | 1 |
| directive | 3 |
| guard | 1 |
| interceptor | 4 |
| module | 16 |
| pipe | 67 |
| rest_interface | 21 |
| scheduler | 1 |
| resolver | 4 |
| **Overall components** | **951** |

These numbers are derived directly from the architecture facts repository and reflect the actual source‑code artefacts.

---

## 5.2 Whitebox Overall System (Level 1)

### Container Overview Diagram (ASCII)

```
+-------------------+        +-------------------+        +-------------------+
|   frontend       |        |    backend        |        |      jsApi        |
| (Angular)        | <----> | (Spring Boot)     | <----> | (Node.js)         |
+-------------------+        +-------------------+        +-------------------+
        ^                               ^
        |                               |
        |                               |
+-------------------+        +-------------------+
|  e2e‑xnp          |        | import‑schema      |
| (Playwright)      |        | (Java/Gradle)      |
+-------------------+        +-------------------+
```

*Arrows indicate synchronous HTTP/REST communication. The test container (`e2e‑xnp`) and the helper library (`import‑schema`) do not host business components.*

### Container Responsibilities Table

| Container | Technology | Primary Purpose | Component Count |
|-----------|------------|-----------------|-----------------|
| **backend** | Spring Boot | Core business services, REST API, persistence | 494 |
| **frontend** | Angular | User interface, SPA, consumes backend APIs | 404 |
| **jsApi** | Node.js | Thin façade for legacy scripts, auxiliary endpoints | 52 |
| **e2e‑xnp** | Playwright | End‑to‑end UI test execution (non‑functional) | 0 |
| **import‑schema** | Java/Gradle | Build‑time schema import utilities | 0 |

### Layer Dependency Rules (ASCII)

```
+-------------------+   uses   +-------------------+   uses   +-------------------+   uses   +-------------------+
| Presentation      | ------> | Application       | ------> | Domain            | ------> | Data‑Access       |
+-------------------+          +-------------------+          +-------------------+          +-------------------+
```

*All dependencies flow downwards; higher layers must not call lower layers directly.*

### Component Distribution Across Containers

#### Backend Container (`container.backend`)

| Layer | Stereotype | Count |
|-------|------------|-------|
| Presentation | controller | 32 |
| Application | service | 184 |
| Domain | entity | 360 |
| Data‑Access | repository | 38 |
| Miscellaneous (adapters, components, etc.) | – | 50 |

#### Frontend Container (`container.frontend`)

| Layer | Stereotype | Count |
|-------|------------|-------|
| Presentation | component | 169 |
| Presentation | module | 16 |
| Presentation | pipe | 67 |
| Presentation | directive | 3 |
| Miscellaneous (configuration, guard) | – | 5 |

#### jsApi Container (`container.jsApi`)

| Layer | Stereotype | Count |
|-------|------------|-------|
| Presentation | component | 16 |
| Application | service | 10 |
| Miscellaneous | – | 26 |

The distribution mirrors the functional decomposition: the **backend** holds the full DDD stack, the **frontend** concentrates on UI artefacts, and the **jsApi** provides a lightweight integration layer.

---

*All tables, counts and component names are taken directly from the architecture facts repository; no placeholders are used.*
