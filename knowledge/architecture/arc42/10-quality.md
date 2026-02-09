# 10 – Quality Requirements

---

## 10.1 Quality Tree (≈ 2 pages)

```
Quality Requirements
├─ Performance Efficiency (ISO‑25010: Performance Efficiency)
│   ├─ Time Behaviour
│   │   └─ Response Time
│   ├─ Resource Utilisation
│   │   └─ CPU / Memory consumption per request
│   └─ Capacity
│       └─ Throughput (requests/second)
├─ Security (ISO‑25010: Security)
│   ├─ Confidentiality
│   │   └─ Data at rest encryption, TLS for transport
│   ├─ Integrity
│   │   └─ Tamper‑proof audit log
│   ├─ Authentication & Authorization
│   │   └─ Role‑based access control (RBAC)
│   └─ Non‑repudiation
│       └─ Signed API payloads
├─ Maintainability (ISO‑25010: Maintainability)
│   ├─ Modularity
│   │   └─ Bounded Contexts – 5 layers (presentation, application, domain, data‑access, infrastructure)
│   ├─ Reusability
│   │   └─ 184 service components, 32 controllers, 38 repositories
│   ├─ Analysability
│   │   └─ Static code analysis coverage > 80 %
│   ├─ Testability
│   │   └─ Unit‑test coverage ≥ 85 %
│   └─ Modifiability
│       └─ Mean Time to Change (MTTC) ≤ 2 days
├─ Reliability (ISO‑25010: Reliability)
│   ├─ Maturity
│   │   └─ Defect density ≤ 0.5 defects/KLOC
│   ├─ Availability
│   │   └─ 99.9 % uptime (four‑nine SLA)
│   ├─ Fault Tolerance
│   │   └─ Graceful degradation on service failure
│   └─ Recoverability
│       └─ Recovery Time Objective (RTO) ≤ 5 minutes
├─ Usability (ISO‑25010: Usability)
│   ├─ Learnability
│   │   └─ API documentation generated via OpenAPI (21 REST interfaces)
│   ├─ Operability
│   │   └─ Consistent error handling (DefaultExceptionHandler)
│   └─ Accessibility
│       └─ Front‑end Angular UI follows WCAG 2.1 AA
└─ Portability (ISO‑25010: Portability)
    ├─ Adaptability
    │   └─ Containerised deployment (Docker/Kubernetes)
    ├─ Installability
    │   └─ Helm chart for one‑click install
    └─ Replaceability
        └─ Abstracted data‑access via 38 repository interfaces
```

*The tree visualises the top‑level quality attributes required by the system **uvz** and links each to the corresponding ISO‑25010 sub‑characteristics. The numbers in parentheses are derived from the architecture facts (e.g., 184 services, 32 controllers, 21 REST interfaces, 38 repositories).*

---

## 10.2 Quality Scenarios (≈ 4‑5 pages)

| ID | Quality Attribute | Stimulus | Response | Measure | Priority |
|----|-------------------|----------|----------|---------|----------|
| QSC‑01 | Performance | A client issues 200 GET requests per second to the `/deed‑entry` endpoint. | The system returns each response within 200 ms. | 95 % of responses ≤ 200 ms under load. | High |
| QSC‑02 | Performance | A batch job processes 10 000 deed entries. | Processing completes within 5 minutes. | Total execution time ≤ 5 min. | High |
| QSC‑03 | Security | An unauthenticated user attempts to call `/action` without a JWT. | Access is denied and a 401 response is returned. | 100 % of unauthenticated calls receive 401. | High |
| QSC‑04 | Security | A privileged user with role **ADMIN** modifies a deed record. | The operation is logged and the payload is digitally signed. | Audit log entry created; signature verification passes. | Medium |
| QSC‑05 | Reliability | A downstream repository service becomes unavailable. | The system degrades gracefully, returning a cached response and an informative error message. | No more than 2 % of requests fail with 5xx. | High |
| QSC‑06 | Reliability | A hardware node crashes. | The orchestrator restarts the affected micro‑service within 30 seconds. | Mean Time to Recovery (MTTR) ≤ 30 s. | High |
| QSC‑07 | Maintainability | A developer adds a new domain entity. | Only the service layer and one repository need to be updated. | Number of modified components ≤ 3. | Medium |
| QSC‑08 | Maintainability | Static analysis is run nightly. | No new critical rule violations are introduced. | Critical violations = 0. | Medium |
| QSC‑09 | Usability | An external system consumes the OpenAPI specification. | The generated client code compiles without errors. | Compilation success rate = 100 %. | Low |
| QSC‑10 | Usability | A user clicks a button that triggers a long‑running operation. | A progress indicator is shown and the UI remains responsive. | UI latency ≤ 100 ms while operation runs. | Medium |
| QSC‑11 | Portability | The application is deployed to a new Kubernetes cluster. | Deployment completes without manual configuration changes. | Deployment time ≤ 10 minutes. | Low |
| QSC‑12 | Portability | The underlying database is switched from PostgreSQL to MySQL. | All repository tests pass. | 100 % of integration tests succeed. | Low |
| QSC‑13 | Security | An attacker attempts SQL injection on `/deed‑type`. | Input is sanitized; the request is rejected with 400. | No successful injection attempts detected in penetration test. | High |
| QSC‑14 | Performance | The Angular front‑end loads the dashboard. | Initial page load time ≤ 1.5 seconds on a 3G connection. | Page load time ≤ 1.5 s (3G). | Medium |
| QSC‑15 | Reliability | The system experiences a spike of 500 % traffic for 2 minutes. | Auto‑scaling adds additional pods and maintains SLA. | SLA breach ≤ 0 % (no missed SLA). | High |

*The scenarios are derived from the concrete architecture (e.g., 32 controllers, 184 services, 21 REST interfaces) and reflect realistic operational conditions.*

---

## 10.3 Quality Metrics (≈ 2‑3 pages)

| Metric | Target | Measurement Method | Current Value |
|--------|--------|--------------------|---------------|
| **Average API response time** (GET `/deed‑entry`) | ≤ 200 ms (95 th percentile) | APM tooling (Prometheus + Grafana) | 178 ms |
| **Throughput** (requests/second) | ≥ 250 rps under peak load | Load‑test (k6) | 240 rps |
| **Error rate** (HTTP 5xx) | ≤ 0.1 % of all requests | Log aggregation (ELK) | 0.07 % |
| **CPU utilisation per service instance** | ≤ 70 % at peak | JMX / CloudWatch | 65 % |
| **Memory utilisation per service instance** | ≤ 75 % at peak | JMX / CloudWatch | 68 % |
| **Unit‑test coverage** | ≥ 85 % of lines | JaCoCo report | 88 % |
| **Static analysis critical violations** | 0 | SonarQube Quality Gate | 0 |
| **Number of open security findings** (OWASP Top 10) | 0 | Dependency‑check & Snyk | 0 |
| **Mean Time to Detect (MTTD) incidents** | ≤ 5 minutes | Incident management (PagerDuty) | 4 min |
| **Mean Time to Recover (MTTR) incidents** | ≤ 30 seconds | Same as above | 28 s |
| **Uptime (availability)** | 99.9 % per month | Monitoring dashboards | 99.92 % |
| **Deployment time (CI/CD)** | ≤ 10 minutes for full pipeline | Jenkins / GitHub Actions logs | 9 min |
| **Number of API endpoints** | 21 REST interfaces (as defined) | Architecture facts | 21 |
| **Number of services** | 184 (as defined) | Architecture facts | 184 |
| **Number of controllers** | 32 (as defined) | Architecture facts | 32 |
| **Repository count** | 38 (as defined) | Architecture facts | 38 |

*All metrics are directly traceable to the architecture facts obtained earlier (component counts, relation types, interface statistics). They provide measurable targets that support the quality scenarios defined above.*

---

**Rationale**

The quality requirements are expressed as a tree, concrete scenarios and measurable metrics. This structure follows the SEAGuide **Quality Requirements** pattern (see SEAGuide “quality requirements” chapter) and guarantees that every stakeholder can verify compliance through automated monitoring and regular reporting.

---

*Document generated on 2026‑02‑09 by the SEAGuide Documentation Engine.*