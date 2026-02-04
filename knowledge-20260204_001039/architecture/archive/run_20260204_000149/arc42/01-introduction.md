# 01 – Introduction and Goals

## 1.1 Requirements Overview  

### System domain and purpose  
The **uvz** system is a back‑office application that supports the full life‑cycle of deed processing and related administrative tasks. Its core purpose is to enable:

* creation, typing, archiving, reencryption and signing of deed entries,  
* management of UVZ number generation and formatting,  
* orchestration of workflow jobs and tasks,  
* generation of reports and handling of action‑related operations, and  
* integration with the external **XNP** platform for authentication, document handling and notifications.  

### Component statistics  

| Element | Count |
|---------|-------|
| Containers | 5 |
| Components | 826 |
| Interfaces | 108 |
| Relations (uses) | 120 |

### Key capabilities  

| Capability | Description | Primary service implementations |
|------------|-------------|---------------------------------|
| **Deed Management** | Handles creation, typing, archiving, reencryption and signing of deed entries. | `DeedEntryRestServiceImpl`, `DeedEntryServiceImpl`, `DeedEntryRepository` |
| **Number Management** | Generates, formats and fills gaps in UVZ numbers. | `NumberManagementRestServiceImpl`, `NumberManagementServiceImpl`, `NumberManagementRepository` |
| **Workflow Management** | Coordinates jobs, tasks and overall workflow orchestration. | `WorkflowRestServiceImpl`, `JobRestServiceImpl`, `TaskRestServiceImpl` |
| **Reporting** | Provides metadata for report generation and handling. | `ReportRestServiceImpl`, `ReportMetadataRestServiceImpl` |
| **Action Handling** | Exposes configuration for action‑related API endpoints. | `ActionRestServiceImpl`, `ActionServiceImpl` |
| **Business‑Purpose Management** | Manages business‑purpose related data via REST. | `BusinessPurposeRestServiceImpl` |
| **XNP Integration** | Connects to the external XNP platform (authentication, document handling, notifications, etc.). | 24 `Xnp*` services (e.g., `XnpAuthenticationAdapter`, `XnpArchiveManagerEndpoint`) |
| **Infrastructure Support** | Supplies generic utilities such as health checks, adapters, storage, authentication and UI helpers. | `HealthCheck`, `CustomMethodSecurityExpressionHandler`, `JsonAuthorizationRestServiceImpl`, `KeyManagerRestServiceImpl` |

---

## 1.2 Quality Goals  

The quality goals are derived from the **architectural style** and the **design patterns** identified in the code base.

| Quality attribute | Goal (derived from style / patterns) |
|-------------------|--------------------------------------|
| **Maintainability** | The **modular monolith** combined with the **layered architecture** enforces strict separation (Controller → Service → Repository). This yields high cohesion, low coupling and zero layer violations (grade A). |
| **Reliability** | Use of the **builder_pattern** (for immutable objects) and **observer_pattern** (for event propagation) increases robustness and simplifies error handling. |
| **Scalability** | While the primary style is vertical scaling of the monolith, the **factory_pattern** and **repository_pattern** make it straightforward to extract services later if horizontal scaling becomes necessary. |
| **Extensibility** | The **adapter_pattern** isolates external XNP dependencies, enabling replacement or extension without affecting core business logic. |
| **Testability** | The **singleton_pattern** (used for shared utilities) and **factory_pattern** facilitate deterministic unit‑test setups and mock injection. |
| **Security** | Spring Security provides authentication & authorization, and the clear layered boundaries prevent direct repository access from controllers, reducing attack surface. |

---

## 1.3 Stakeholders  

| Stakeholder | Interest / Concern |
|-------------|-------------------|
| **Business owners / Product managers** | Ensure the system delivers core deed‑processing capabilities and complies with domain regulations. |
| **End‑users (public‑service employees, clerks)** | Need a reliable, responsive UI (Angular SPA) for creating and managing deeds and related data. |
| **Developers / Maintenance team** | Require a clear modular structure, low coupling and good test coverage to evolve the system efficiently. |
| **Operations / DevOps** | Want straightforward Docker‑Compose deployment, health‑check endpoints and metrics for monitoring. |
| **Security & Compliance officers** | Expect solid authentication/authorization, input validation and audit logging. |
| **External partners (XNP platform)** | Need stable, well‑defined integration points (the 24 XNP services) and versioned REST contracts. |
| **Quality assurance** | Relies on contract tests (Pact Broker) and automated UI tests to guarantee functional correctness. |