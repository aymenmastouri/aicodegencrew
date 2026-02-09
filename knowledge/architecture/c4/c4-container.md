# C4 Level 2: Container Diagram

## 2.1 Overview
The system **uvz** is composed of five deployable containers. Each container represents a logical runtime unit that can be independently built, deployed and scaled. The diagram follows the SEAGuide C4 conventions (blue boxes for internal containers, gray for external, cylinders for databases, person icons for users, dashed lines for boundaries).

## 2.2 Container Inventory

| Container ID | Name | Type | Technology | Primary Responsibility |
|--------------|------|------|------------|--------------------------|
| `container.backend` | Backend | Application | Spring Boot (Java/Gradle) | Exposes REST APIs, business logic, data access and security. |
| `container.frontend` | Frontend | Application | Angular (npm) | SPA UI for end‑users, consumes Backend APIs. |
| `container.js_api` | jsApi | Application | Node.js (npm) | Server‑side JavaScript façade, provides auxiliary HTTP endpoints for legacy integrations. |
| `container.import_schema` | Import‑Schema | Library | Java/Gradle | Shared domain model and schema import utilities used by Backend. |
| `container.e2e_xnp` | e2e‑xnp | Test | Playwright (npm) | End‑to‑end UI test suite exercising Frontend and Backend. |

## 2.3 Container Details

### 2.3.1 Backend (`container.backend`)
- **Technology**: Spring Boot, Gradle build system.
- **Key Packages**: Controllers, Services, Repositories, Security, Configuration.
- **Main Components** (excerpt):
  - Controllers (REST entry points): `ActionRestServiceImpl`, `StaticContentController`, `JsonAuthorizationRestServiceImpl`, `ReportRestServiceImpl`, `OpenApiConfig` … (total 32 listed).
  - Services (business logic): `ActionServiceImpl`, `ArchiveManagerServiceImpl`, `KeyManagerServiceImpl`, `DeedEntryServiceImpl`, `ReportServiceImpl` … (total 30 listed).
  - Repositories / DAOs: `RestrictedDeedEntryDaoImpl`, `DeedEntryConnectionDaoImpl`, `DocumentMetaDataCustomDaoImpl`.
- **Ports / Protocols**: HTTP/HTTPS (REST/JSON), optional gRPC (future). 
- **External Interfaces**: Consumes `jsApi` (internal HTTP), accesses database (not modelled as separate container – embedded via JPA).

### 2.3.2 Frontend (`container.frontend`)
- **Technology**: Angular, TypeScript, npm.
- **Responsibility**: Provides the user‑facing single‑page application, handles routing, state management and UI rendering.
- **Key Modules**: Authentication, Dashboard, Deed Management, Reporting.
- **Communication**: Calls Backend REST endpoints over HTTPS; loads static assets from Backend (`StaticContentController`).

### 2.3.3 jsApi (`container.js_api`)
- **Technology**: Node.js, npm.
- **Responsibility**: Lightweight HTTP façade exposing legacy‑compatible endpoints and utility scripts used by external partners.
- **Interaction**: Calls Backend services via internal HTTP; may be called directly by Frontend for specific features.

### 2.3.4 Import‑Schema (`container.import_schema`)
- **Technology**: Java library built with Gradle.
- **Responsibility**: Supplies shared domain model classes and schema import logic used by Backend at compile‑time.
- **Deployment**: Packaged as a JAR and included in Backend classpath.

### 2.3.5 e2e‑xnp (`container.e2e_xnp`)
- **Technology**: Playwright test framework.
- **Responsibility**: Executes automated end‑to‑end UI tests against the deployed Frontend and Backend.
- **Scope**: Not part of production runtime; runs in CI/CD pipeline.

## 2.4 Container Interactions

### 2.4.1 Synchronous Communication (HTTP/REST)
| Source | Target | Protocol | Data Format | Typical Use |
|--------|--------|----------|-------------|-------------|
| Frontend | Backend | HTTPS/REST | JSON | UI actions → business operations |
| Frontend | jsApi | HTTPS/REST | JSON | Legacy integration calls |
| jsApi | Backend | HTTP/REST | JSON | Service façade forwarding |
| Backend | Import‑Schema (library) | Compile‑time JAR | Java classes | Shared domain model |

### 2.4.2 Asynchronous / Event‑Driven (Future)
| Source | Target | Mechanism | Purpose |
|--------|--------|-----------|---------|
| Backend | (External) Message Broker | Kafka / JMS (planned) | Publish domain events (e.g., DeedCreated) |
| Frontend | – | – | – |

## 2.5 Technology Stack Summary
| Layer | Technology | Version (example) |
|-------|------------|-------------------|
| Presentation (UI) | Angular | 15.x |
| Presentation (JS façade) | Node.js | 18.x |
| Application (Backend) | Spring Boot | 3.1.x |
| Build System | Gradle / npm | 8.x / 9.x |
| Testing | Playwright | 1.35 |
| Shared Library | Java (JDK 17) | 17 |

## 2.6 Diagram Reference
The visual container diagram is stored as a Draw.io file:

```
📁 c4/c4-container.drawio
```
It depicts the five containers, their technology icons, and the communication arrows described above. The diagram follows the SEAGuide colour palette (blue for internal containers, gray for test container, dashed boundary for the system).

---
*Document generated on 2026‑02‑08 using real architecture facts.*