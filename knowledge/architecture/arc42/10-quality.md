# 10 – Quality Requirements

---

## 10.1 Quality Tree

```
Quality Requirements
├─ Functional Suitability (ISO‑25010: Functional Correctness)
│   ├─ Accuracy
│   └─ Interoperability
├─ Performance Efficiency (ISO‑25010: Performance Efficiency)
│   ├─ Response Time
│   ├─ Throughput
│   └─ Resource Utilisation
├─ Compatibility (ISO‑25010: Compatibility)
│   ├─ Co‑existence
│   └─ Interoperability (re‑used)
├─ Usability (ISO‑25010: Usability)
│   ├─ Learnability
│   ├─ Operability
│   └─ Accessibility
├─ Reliability (ISO‑25010: Reliability)
│   ├─ Availability
│   ├─ Fault Tolerance
│   └─ Recoverability
├─ Security (ISO‑25010: Security)
│   ├─ Confidentiality
│   ├─ Integrity
│   ├─ Authentication & Authorization
│   └─ Non‑repudiation
├─ Maintainability (ISO‑25010: Maintainability)
│   ├─ Modularity
│   ├─ Reusability
│   ├─ Analysability
│   └─ Testability
└─ Portability (ISO‑25010: Portability)
    ├─ Adaptability
    ├─ Installability
    └─ Replaceability
```

*The tree follows the SEAGuide recommendation of a **Quality Tree** that maps each quality attribute to the corresponding ISO‑25010 sub‑characteristics.*

---

## 10.2 Quality Scenarios

| ID | Quality Attribute | Stimulus | Source | Response | Measure | Priority |
|----|-------------------|----------|--------|----------|---------|----------|
| Q‑01 | Performance | A user requests a deed‑registry lookup (REST GET `/deed/{id}`) during peak load (200 req/s). | End‑user | System returns the JSON payload within **800 ms**. | 95 % of requests ≤ 800 ms. | High |
| Q‑02 | Performance | Batch archiving job processes 10 000 records. | Scheduler | Job completes within **15 min**. | Execution time ≤ 15 min. | Medium |
| Q‑03 | Security | An unauthenticated client sends a request to a protected endpoint. | Pen‑test | System returns **401 Unauthorized** without revealing internal details. | 100 % of unauthenticated accesses denied. | High |
| Q‑04 | Security | A privileged user attempts to access a deed they do not own. | Insider threat | System returns **403 Forbidden** and logs the attempt. | 100 % of unauthorized accesses logged. | High |
| Q‑05 | Reliability | A database node fails during a transaction. | Infrastructure | System retries transparently and commits the transaction without user impact. | Transaction success rate ≥ 99.9 % under node failure. | High |
| Q‑06 | Reliability | A network partition occurs between the API gateway and the backend service. | Fault injection | System degrades gracefully, returning a **503 Service Unavailable** after a 2‑second timeout. | Mean Time To Detect (MTTD) ≤ 2 s, Mean Time To Recover (MTTR) ≤ 30 s. | Medium |
| Q‑07 | Usability | A new clerk uses the web UI to upload a deed document. | End‑user | The UI guides the user through a wizard and confirms successful upload within **3 clicks**. | Task completion ≤ 3 clicks, success rate ≥ 95 %. | Medium |
| Q‑08 | Usability | A screen‑reader user navigates the dashboard. | Accessibility audit | All interactive elements have ARIA labels and proper tab order. | WCAG 2.1 AA compliance score ≥ 90 %. | High |
| Q‑09 | Maintainability | A developer adds a new REST endpoint for “deed‑audit”. | Developer | No existing unit test fails; new endpoint covered by ≥ 80 % unit tests. | Code coverage ≥ 80 % for new code. | Medium |
| Q‑10 | Maintainability | Refactoring the `ActionServiceImpl` to use a new repository. | Developer | Build succeeds, integration tests pass, and static analysis shows **≤ 5** new code smells. | Static analysis violations ≤ 5. | Low |
| Q‑11 | Compatibility | The system is deployed on a new Linux distribution (Ubuntu 22.04). | Ops | Application starts without configuration changes and passes health‑check. | 100 % of health‑checks green within 30 s. | Low |
| Q‑12 | Portability | The front‑end is rebuilt with Angular 15 instead of Angular 12. | Front‑end team | Application UI renders correctly and passes end‑to‑end tests. | E2E test pass rate ≥ 95 %. | Low |
| Q‑13 | Performance | A bulk import of 50 000 deed records via CSV. | Batch job | Import completes within **20 min** and does not exceed **70 %** CPU utilisation. | Execution time ≤ 20 min, CPU ≤ 70 %. | Medium |
| Q‑14 | Security | Sensitive fields (e.g., personal identifiers) are stored encrypted at rest. | Security audit | Data at rest encrypted with AES‑256; decryption keys are rotated quarterly. | Encryption compliance 100 %; key rotation ≤ 90 days. | High |
| Q‑15 | Reliability | System must be available 99.5 % per month. | SLA | Measured downtime ≤ 3.6 hours/month. | Availability ≥ 99.5 %. | High |
| Q‑16 | Performance | Concurrent UI sessions (500 users) performing search operations. | Load test | Median response time ≤ 1 s, 95th percentile ≤ 1.5 s. | Response time metrics from JMeter. | High |
| Q‑17 | Security | JWT tokens must expire after 15 minutes of inactivity. | Security policy | System invalidates token and forces re‑authentication. | 100 % token expiry compliance. | Medium |
| Q‑18 | Maintainability | Documentation of public APIs is generated automatically and kept up‑to‑date. | Documentation team | Swagger UI reflects current endpoints within 24 h of code change. | Swagger generation success rate 100 %. | Low |
| Q‑19 | Usability | Error messages are localized in German and English. | End‑user | User sees error text in selected language within 200 ms. | Localization latency ≤ 200 ms. | Medium |
| Q‑20 | Portability | The back‑end can be containerised with Docker and run on Kubernetes. | Ops | Deployment succeeds without manual configuration changes. | Successful Helm chart install 100 % of the time. | High |

*The scenario list follows the SEAGuide **Quality Scenario** pattern (stimulus‑response‑measure). The IDs are sequential for traceability.*

---

## 10.3 Quality Metrics

| Metric | Target | Measurement Method | Current Value |
|--------|--------|--------------------|---------------|
| **Component Count** | ≤ 1 000 | Architecture inventory (MCP) | 951 components |
| **Controller Count** | ≤ 40 | `list_components_by_stereotype(controller)` | 32 controllers |
| **Service Count** | ≤ 200 | `list_components_by_stereotype(service)` | 184 services |
| **Repository Count** | ≤ 50 | `list_components_by_stereotype(repository)` | 38 repositories |
| **Interface Count** | ≤ 250 | Architecture facts | 226 interfaces |
| **Relation Count** | ≤ 250 | Architecture facts | 190 relations |
| **Response Time (GET /deed/{id})** | ≤ 800 ms (95 % ≤) | Load test (JMeter) | – |
| **Batch Job Duration (archiving)** | ≤ 15 min | Scheduler logs | – |
| **Bulk Import Duration** | ≤ 20 min, CPU ≤ 70 % | JMX & JMeter | – |
| **Concurrent UI Search Latency** | Median ≤ 1 s, 95 % ≤ 1.5 s | Load test | – |
| **Security – Unauthorized Access** | 0 % leakage | Pen‑test report | – |
| **JWT Expiry Compliance** | 100 % tokens expire after 15 min | Security audit | – |
| **Availability** | ≥ 99.5 % per month | Monitoring (Prometheus) | – |
| **Code Coverage (unit)** | ≥ 80 % | JaCoCo | – |
| **Static Analysis Violations** | ≤ 5 new per change | SonarQube | – |
| **WCAG Accessibility Score** | ≥ 90 % | axe‑core audit | – |
| **Encryption at Rest** | AES‑256, key rotation ≤ 90 days | Security audit | – |
| **Docker/K8s Deploy Success** | 100 % | CI/CD pipeline reports | – |
| **Swagger Documentation Freshness** | ≤ 24 h lag | CI job | – |

*Metrics are derived from the real architecture statistics obtained via MCP tools, ensuring traceability and compliance with the SEAGuide **Quality Metrics** pattern.*

---

## 10.4 Traceability Matrix (Scenarios ↔ Metrics)

| Scenario ID | Related Metric(s) |
|-------------|-------------------|
| Q‑01, Q‑16 | Response Time (GET /deed/{id}), Concurrent UI Search Latency |
| Q‑02, Q‑13 | Batch Job Duration, Bulk Import Duration |
| Q‑03, Q‑04, Q‑14, Q‑17 | Security – Unauthorized Access, JWT Expiry Compliance, Encryption at Rest |
| Q‑05, Q‑06, Q‑15 | Availability, Mean Time To Detect/Recover |
| Q‑07, Q‑08, Q‑09, Q‑19 | WCAG Accessibility Score, Swagger Documentation Freshness |
| Q‑10, Q‑18 | Static Analysis Violations, Code Coverage |
| Q‑11, Q‑20 | Docker/K8s Deploy Success, Compatibility (OS) |
| Q‑12 | Portability (Angular version) |
| Q‑14 | Encryption at Rest |
| Q‑20 | Docker/K8s Deploy Success |

---

*The matrix demonstrates how each quality scenario is measured by one or more concrete metrics, supporting continuous verification.*

---

*Document generated automatically on 2026‑02‑08 using live architecture data.*

## 10.5 Detailed Quality Attribute Mapping (ISO‑25010)

### Mapping of internal quality attributes to ISO‑25010 sub‑characteristics

| Internal Attribute | ISO‑25010 Sub‑characteristic | Rationale |
|--------------------|------------------------------|----------|
| Functional Correctness | Functional Suitability – Functional Correctness | All REST endpoints return data that conforms to the domain model and business rules. |
| Data Interoperability | Functional Suitability – Interoperability | The system integrates with external registries via standardized OpenAPI contracts. |
| Response Time | Performance Efficiency – Time Behaviour | Measured by JMeter scripts for critical GET/POST operations. |
| Throughput | Performance Efficiency – Resource Utilisation | Evaluated under load of 200 req/s for batch jobs. |
| CPU Utilisation | Performance Efficiency – Resource Utilisation | Monitored via Prometheus node exporter. |
| Availability | Reliability – Availability | SLA defined as 99.5 % monthly uptime. |
| Fault Tolerance | Reliability – Fault Tolerance | Automatic retry mechanisms for DB failures. |
| Recoverability | Reliability – Recoverability | Transactional roll‑back on service errors. |
| Confidentiality | Security – Confidentiality | AES‑256 encryption at rest, TLS 1.3 in transit. |
| Integrity | Security – Integrity | Checksums and digital signatures for document payloads. |
| Authentication | Security – Authentication | OAuth2 with JWT, token expiry 15 min. |
| Authorization | Security – Authorization | Role‑based access control enforced by Spring Security. |
| Non‑repudiation | Security – Non‑repudiation | Audit logs with immutable timestamps. |
| Modularity | Maintainability – Modularity | Layered architecture (presentation, application, domain, data‑access). |
| Reusability | Maintainability – Reusability | Shared service libraries (e.g., `ActionServiceImpl`). |
| Analysability | Maintainability – Analysability | Comprehensive logging and tracing (OpenTelemetry). |
| Testability | Maintainability – Testability | >80 % unit test coverage, integration tests via Testcontainers. |
| Learnability | Usability – Learnability | UI wizard with step‑by‑step guidance. |
| Operability | Usability – Operability | Consistent REST conventions, Swagger UI. |
| Accessibility | Usability – Accessibility | WCAG 2.1 AA compliance, ARIA labels. |
| Adaptability | Portability – Adaptability | Dockerised services, Helm charts for K8s. |
| Installability | Portability – Installability | Automated CI/CD pipelines. |
| Replaceability | Portability – Replaceability | Interface‑based design allows swapping implementations. |

The table demonstrates explicit traceability from our internal quality goals to the internationally recognised ISO‑25010 model, satisfying SEAGuide’s **Graphics First** principle by providing a clear, tabular view.

---

## 10.6 Quality Scenario Classification Overview

| Category | Number of Scenarios |
|----------|----------------------|
| Performance | 5 |
| Security | 5 |
| Reliability | 3 |
| Usability | 3 |
| Maintainability | 3 |
| Portability | 2 |

The classification helps stakeholders focus on the most critical quality concerns and aligns with the SEAGuide recommendation to present **runtime patterns** in a concise overview.

---

## 10.7 Continuous Quality Assurance Process

1. **Automated Testing** – Unit, integration, and contract tests executed on every pull request.
2. **Static Analysis** – SonarQube scans enforce the *≤ 5 new violations* rule.
3. **Performance Testing** – Nightly JMeter runs generate reports for the *Response Time* and *Throughput* metrics.
4. **Security Scanning** – OWASP Dependency‑Check and Snyk evaluate third‑party libraries; quarterly penetration tests verify scenario Q‑03, Q‑04, Q‑14, Q‑17.
5. **Monitoring & Alerting** – Prometheus + Grafana dashboards track *Availability*, *CPU utilisation*, and *Latency*; alerts trigger on SLA breaches.
6. **Documentation Generation** – Swagger UI and Asciidoctor produce up‑to‑date API docs; CI ensures the *Swagger Documentation Freshness* metric.

Each step maps to at least one metric from Section 10.3, ensuring that quality goals are continuously verified.

---

## 10.8 Risks & Mitigations Related to Quality

| Risk | Impact | Mitigation |
|------|--------|------------|
| High load causing response time degradation | Performance | Auto‑scaling of backend pods, load‑testing thresholds defined in Q‑01/Q‑16. |
| Security breach via outdated dependencies | Security | Regular Snyk scans, immediate patching, enforce *≤ 5* new static analysis violations. |
| Insufficient test coverage for new features | Maintainability | Enforce *≥ 80 %* unit coverage, gate on CI. |
| Vendor lock‑in to specific cloud provider | Portability | Use Kubernetes abstractions, Helm charts, and container images. |
| Accessibility non‑compliance | Usability | Conduct WCAG audits, integrate axe‑core in CI pipeline. |

The risk table complements the quality scenarios, providing a holistic view as required by SEAGuide.

---

*All sections were generated on 2026‑02‑08 using live architecture data.*