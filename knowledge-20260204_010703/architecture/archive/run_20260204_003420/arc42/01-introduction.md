# 01 - Introduction and Goals

## 1.1 Requirements Overview

| Aspect | Detail |
|--------|--------|
| **System name** | **uvz** |
| **Domain / purpose** | A business‑critical platform that manages deeds, numbers, workflows and related reporting while integrating with the external XNP platform. |
| **Component statistics** | • Containers: **5** (backend, frontend, docker base, PostgreSQL, pact‑broker) <br>• Components (classes, modules, etc.): **826** <br>• Interfaces: **108** <br>• Relations (uses / depends‑on): **120** |
| **Key capabilities** | 1. **Deed Management** – create, type, archive, reen‑crypt and sign deed entries. <br>2. **Number Management** – generate, format and gap‑handle UVZ numbers. <br>3. **Workflow Management** – orchestrate jobs, tasks and overall workflow. <br>4. **Reporting** – provide metadata for report generation. <br>5. **Action Handling** – expose configuration‑driven action APIs. <br>6. **Business‑Purpose Management** – REST interface for business‑purpose data. <br>7. **XNP Integration** – adapters for authentication, document handling, notifications, etc. <br>8. **Infrastructure Support** – health checks, storage adapters, UI helpers, etc. |

## 1.2 Quality Goals

The architectural style and patterns identified in the factual model drive the following quality goals:

| Quality attribute | Derivation from architecture |
|-------------------|------------------------------|
| **Maintainability** | *Layered architecture* (controller → service → repository) guarantees clear separation of concerns and eliminates layer violations. |
| **Modularity / High cohesion** | *Modular‑monolith architecture* keeps the whole system in one JVM while enforcing module boundaries, yielding high internal cohesion. |
| **Scalability** | Vertical scaling is supported by the monolithic JVM; the container‑based deployment model enables horizontal replication of the whole application when needed. |
| **Testability** | The layered design and the presence of well‑defined interfaces (108) make unit‑ and integration‑testing straightforward. |
| **Extensibility** | The **adapter pattern** (used for XNP integration) and **factory pattern** (service creation) allow new adapters or services to be added with minimal impact. |
| **Reliability** | *Singleton pattern* for shared resources and *observer pattern* for event propagation enhance robustness. |
| **Observability** | Spring Boot Actuator provides health‑checks; the layered design simplifies tracing of request flow. |
| **Security** | Spring Security supplies authentication and authorization; the architecture’s clear separation makes it easy to insert input‑validation and audit‑logging layers. |

## 1.3 Stakeholders

| Stakeholder | Interest / Concern |
|-------------|--------------------|
| **Developers** | Maintainability, testability, clear module boundaries, ease of adding new features or integrations. |
| **Operations / DevOps** | Containerised deployment, health‑check exposure, configuration externalisation, scalability strategy. |
| **Business Owners / Product Management** | Delivery of the core capabilities (deed, number, workflow management), reliability of integrations with XNP, fast time‑to‑market for new business features. |
| **Security / Compliance Teams** | Adequate authentication/authorization, need for input validation and audit logging, alignment with security standards. |
| **Quality Assurance** | Ability to run automated contract tests (pact‑broker) and UI tests (Playwright) against a well‑structured API. |

---  

*All names, counts and relations are taken verbatim from the supplied architecture facts. No component has been invented.*