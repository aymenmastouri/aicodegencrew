# 01 – Introduction and Goals

## 1.1 Requirements Overview

| Aspect | Details |
|--------|---------|
| **System name / domain** | *uvz* – a UVZ (Umsatz‑Verzeichnis‑Zuständigkeit) management system. |
| **Purpose** | Provides a fully‑featured back‑office for deed life‑cycle management, UVZ number handling, workflow orchestration, reporting and deep integration with the external **XNP** platform. |
| **Key capabilities** | <ul><li>Deed Management – creation, typing, archiving, re‑encryption and signing of deed entries.</li><li>Number Management – UVZ number generation, formatting and gap handling.</li><li>Workflow Management – job / task coordination via a custom state‑machine implementation.</li><li>Reporting – metadata exposure for downstream report generators.</li><li>XNP Integration – authentication, document handling, notifications, storage and signature services.</li></ul> |
| **Component statistics** | <ul><li>Containers (deployment units): **5** (backend, frontend, docker host, PostgreSQL, pact‑broker).</li><li>Software components: **826**.</li><li>Interfaces (public contracts): **108**.</li><li>Relations (uses‑edges): **120**.</li></ul> |
| **Component distribution by stereotype** | <ul><li>Architecture styles: **2** – `modular_monolith_architecture`, `layered_architecture`.</li><li>Controllers: **24**.</li><li>Services: **233**.</li><li>Repositories: **4**.</li><li>Entities: **37**.</li><li>Angular components (frontend): **163**.</li><li>Other notable stereotypes: `design_pattern` (6), `module` (18), `pipe` (67), `directive` (5), `sql_script` (258).</li></ul> |
| **Technologies (derived from containers)** | • **Backend:** Spring Boot (Java)  <br>• **Frontend:** Angular (TypeScript)  <br>• **Database:** PostgreSQL  <br>• **Contract testing:** pact‑broker  <br>• **Runtime OS:** Ubuntu (Docker base) |

## 1.2 Quality Goals

The quality goals are directly derived from the **architectural style** and the **design patterns** identified in the code base.

| Quality Goal | Rationale (pattern / style) |
|--------------|----------------------------|
| **Maintainability** | The **layered_architecture** enforces a clear separation (Controller → Service → Repository). Combined with the **repository_pattern** and **factory_pattern**, new features can be added by extending a single layer without affecting others. |
| **Extensibility** | The **adapter_pattern** isolates external XNP services, allowing them to be replaced or extended without touching core business logic. |
| **Testability** | The **factory_pattern** enables easy creation of test doubles; the **observer_pattern** decouples event production from consumption, simplifying unit and integration tests. |
| **Reusability** | The **builder_pattern** is used for constructing complex domain objects (e.g., request payloads) in an immutable, readable way, encouraging reuse across services. |
| **Performance (low coupling)** | The **singleton_pattern** is employed only where a single shared instance is truly required (e.g., configuration helpers), avoiding unnecessary object creation and keeping the runtime footprint small. |
| **Reliability** | The strict three‑tier layering together with the **repository_pattern** ensures that data‑access concerns are isolated, reducing the risk of cascading failures. |
| **Scalability (vertical)** | The **modular_monolith_architecture** concentrates all business logic in one JVM, making vertical scaling (adding CPU / memory) straightforward while still retaining modular source‑code boundaries for future refactoring. |

## 1.3 Stakeholders

| Stakeholder | Interest / Concern |
|-------------|--------------------|
| **Business Owners / Product Management** | Ensure the system delivers the required deed‑processing and number‑management capabilities within regulatory time‑frames. |
| **End‑users (Operators, Administrators)** | Need a reliable UI (Angular SPA) and responsive APIs to perform daily operational tasks and monitor system health. |
| **External XNP Platform Team** | Requires stable adapters for authentication, document handling and notification services; expects clear contract boundaries. |
| **Developers / Maintenance Team** | Focus on maintainability, extensibility and low technical debt; rely on the layered architecture and documented design patterns. |
| **Security & Compliance Team** | Demands robust authentication/authorization (Spring Security) and eventual input validation & audit logging. |
| **Operations / DevOps** | Responsible for containerised deployment (Docker), health‑checking (Actuator), monitoring and scaling of the monolith. |
| **QA / Test Engineers** | Need well‑defined interfaces (108) and contract‑testing artefacts (pact‑broker) to validate behavior across releases. |

---  

*Prepared by the Software Architect using the exact component names, counts and patterns extracted from the architecture facts and the analysis of the system.*