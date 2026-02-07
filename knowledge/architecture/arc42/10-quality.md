# 10 - Quality Requirements

## 10.1 Quality Tree

```
Quality Requirements
├─ Performance
│   ├─ Response Time
│   └─ Throughput
├─ Availability
│   ├─ Uptime
│   └─ Recovery Time
├─ Security
│   ├─ Authentication
│   ├─ Authorization
│   └─ Data Protection
├─ Maintainability
│   ├─ Modularity
│   ├─ Testability
│   └─ Documentation
├─ Scalability
│   ├─ Horizontal Scaling
│   └─ Load Balancing
├─ Usability
│   ├─ Accessibility
│   └─ Internationalisation
```

The tree reflects the most critical quality attributes for the **uvz** system, derived from the architectural style (layered) and the technology stack (Angular, Spring Boot, Playwright). Each leaf node is later refined into concrete scenarios and measurable metrics.

---

## 10.2 Quality Scenarios

| ID | Quality Attribute | Scenario (Given‑When‑Then) | Expected Response | Priority |
|----|-------------------|---------------------------|-------------------|----------|
| QSC‑01 | Performance | **Given** the system is under a load of 500 concurrent users requesting the *order list* endpoint, **When** a request is processed, **Then** the response time shall be ≤ 200 ms for 95 % of the requests. | ≤ 200 ms (95 % percentile) | High |
| QSC‑02 | Performance | **Given** a batch import of 10 000 records, **When** the import job runs, **Then** the system shall process at least 200 records per second. | ≥ 200 records/s | Medium |
| QSC‑03 | Availability | **Given** a failure of one application server instance, **When** traffic is redirected, **Then** the service shall remain available with ≤ 1 % error rate. | ≤ 1 % error rate | High |
| QSC‑04 | Availability | **Given** a planned maintenance window, **When** the system is taken offline, **Then** the downtime shall not exceed 15 minutes and the system shall recover within 2 minutes after restart. | Downtime ≤ 15 min, MTTR ≤ 2 min | Medium |
| QSC‑05 | Security | **Given** an unauthenticated request to a protected REST endpoint, **When** the request is received, **Then** the system shall reject it with HTTP 401 and log the attempt. | HTTP 401, audit log entry | High |
| QSC‑06 | Security | **Given** a user with role *ADMIN* accesses the *user‑management* UI, **When** the UI renders, **Then** all admin‑only controls shall be visible and functional, while a *USER* role shall see them hidden. | Role‑based UI rendering verified | High |
| QSC‑07 | Maintainability – Modularity | **Given** a new payment provider must be integrated, **When** a developer adds a new *PaymentAdapter* module, **Then** existing services shall compile without modification and unit tests shall pass. | Zero compile errors, 100 % existing test pass | Medium |
| QSC‑08 | Maintainability – Testability | **Given** the UI test suite runs nightly, **When** the suite finishes, **Then** code coverage of UI components shall be ≥ 80 % and end‑to‑end coverage (Playwright) ≥ 70 %. | UI coverage ≥ 80 %, E2E coverage ≥ 70 % | High |
| QSC‑09 | Scalability | **Given** the system is deployed on a Kubernetes cluster with auto‑scaling enabled, **When** CPU usage exceeds 70 % on two pods, **Then** the cluster shall add an additional pod within 30 seconds. | New pod added ≤ 30 s | Medium |
| QSC‑10 | Usability – Accessibility | **Given** a visually impaired user accesses the web UI, **When** the page is rendered, **Then** all interactive elements shall have appropriate ARIA labels and pass WCAG 2.1 AA checks. | WCAG 2.1 AA compliance verified | Low |
| QSC‑11 | Reliability | **Given** a network glitch drops 5 % of packets, **When** a client retries the request, **Then** the system shall successfully complete the operation on the second attempt without data loss. | Successful retry, no data loss | Medium |

The scenarios are expressed in the **Given‑When‑Then** format recommended by SEAGuide for clarity and testability. Priorities are aligned with business impact and technical risk.

---

## 10.3 Quality Metrics

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| Average Response Time (GET /orders) | ≤ 200 ms (95 % percentile) | Application Performance Monitoring (APM) – New Relic/Prometheus metrics collected over 30‑day window |
| Throughput (Batch Import) | ≥ 200 records/s | Load‑test tool (JMeter) with recorded throughput logs |
| System Uptime | 99.9 % per month | Infrastructure monitoring (Grafana) – downtime aggregated from incident logs |
| Mean Time To Recover (MTTR) | ≤ 2 minutes after pod restart | Kubernetes event timestamps and incident tickets |
| Security Incident Rate | 0 critical incidents per quarter | Security Information & Event Management (SIEM) reports |
| Authentication Failure Log Rate | ≤ 5 failed attempts per user per day | Audit log analysis (ELK stack) |
| Code Coverage – Unit Tests | ≥ 80 % of Java classes | JaCoCo reports generated on CI pipeline |
| Code Coverage – UI Components | ≥ 80 % of Angular components | Karma/Jest coverage reports |
| End‑to‑End Test Coverage | ≥ 70 % of user journeys | Playwright test suite execution metrics |
| Documentation Completeness | ≥ 90 % of public APIs documented in OpenAPI spec | OpenAPI validator against generated spec |
| Accessibility Score | ≥ 90 % (Axe Core) | Automated accessibility scans on CI |

These metrics are directly traceable to the quality scenarios above and can be measured continuously. The numbers are realistic for a system of **738** components, **125** interfaces, and **169** relations, and they leverage the existing toolchain (Spring Boot Actuator, Angular CLI, Playwright, Prometheus, Grafana, JaCoCo, etc.).

---

### Alignment with Architecture

* **Performance** – The large number of *rest_interface* (21) and *controller* (32) components creates many entry points; the response‑time metric ensures the layered architecture does not introduce unacceptable latency.
* **Availability** – With **4 containers** (frontend, backend, database, test runner) the system can tolerate the loss of a single container; the availability scenarios validate this resilience.
* **Security** – The presence of **guard** (1) and **interceptor** (4) components indicates a dedicated security layer; the authentication/authorization scenarios test its effectiveness.
* **Maintainability** – The high count of **service** (173) and **repository** (38) components demands strict modularity; the modularity scenario guarantees that new adapters can be added without ripple effects.
* **Scalability** – The **adapter** (50) and **module** (16) counts show extensibility; auto‑scaling metrics confirm the system can grow horizontally.
* **Usability** – The **directive** (3) and **pipe** (67) components are UI‑centric; accessibility metrics ensure the UI meets user expectations.

---

*Prepared for the uvz system – Phase 2 Architecture Review – 2026.*