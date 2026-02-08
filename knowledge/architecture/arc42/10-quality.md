# 10 - Quality Requirements

## 10.1 Quality Tree

```
Quality Requirements
├─ Performance
│   ├─ Response Time
│   └─ Throughput
├─ Scalability
│   ├─ Horizontal Scaling
│   └─ Load Balancing
├─ Security
│   ├─ Authentication & Authorization
│   ├─ Data Protection
│   └─ Auditing
├─ Reliability
│   ├─ Availability
│   └─ Fault Tolerance
├─ Maintainability
│   ├─ Modularity (184 services, 32 controllers, 38 repositories)
│   └─ Testability (226 interfaces, 196 REST endpoints)
└─ Usability
    ├─ UI Responsiveness (Angular front‑end)
    └─ Accessibility
```

The tree reflects the primary quality attributes identified for **uvz**, a deed‑entry management platform built with Angular, Spring Boot, and Node.js. The numbers in parentheses are taken from the architecture statistics (951 total components, 184 services, 32 controllers, 38 repositories, 196 REST endpoints).

---

## 10.2 Quality Scenarios

| ID | Quality Attribute | Scenario | Expected Response | Priority |
|----|-------------------|----------|-------------------|----------|
| Q1 | Performance | A user submits a deed entry via the Angular UI. The request travels through the REST controller to the `DeedEntryServiceImpl` and persists via `DeedEntryRepository`. | System returns **HTTP 200** within **200 ms** for 95 % of requests under a load of 500 concurrent users. | High |
| Q2 | Scalability | Traffic spikes to 2 000 requests per minute during a batch import. | Auto‑scaling adds additional Spring Boot instances; load balancer distributes traffic; average response time stays ≤ 300 ms. | High |
| Q3 | Security | An external attacker attempts to access `/api/deed/**` without a valid JWT. | Gateway rejects the request with **HTTP 401**; audit log records the attempt. | Critical |
| Q4 | Reliability | A Spring Boot instance crashes during a long‑running batch job. | Remaining instances detect failure via health checks, take over the job, and system availability remains **≥ 99.9 %**. | High |
| Q5 | Maintainability | A new business rule requires validation of the deed title length. | Developer adds a validator in the `deed-entry` module (one of 16 modules) and runs unit tests; build passes without affecting other modules. | Medium |
| Q6 | Usability | A user on a mobile device opens the deed‑search page. | Page renders within **1 s** and UI elements adapt to the viewport (responsive design). | Medium |
| Q7 | Performance | Bulk export of 10 000 deeds is requested via the `ExportController`. | Streaming response starts within **500 ms** and completes within **5 s**. | High |
| Q8 | Security | Sensitive personal data must be encrypted at rest. | All `entity` objects (360 total) are persisted with AES‑256 encryption; decryption occurs only in the service layer. | Critical |
| Q9 | Reliability | Database connection loss occurs for 30 seconds. | Application retries, switches to a standby replica, and no user request fails; error rate stays < 0.1 %. | High |
| Q10 | Maintainability | A new micro‑service `NotificationService` is added. | It registers as a Spring bean, communicates via REST (one of 196 endpoints), and does not increase the total number of `uses` relations beyond the current 131 % threshold. | Medium |

---

## 10.3 Quality Metrics

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| Average HTTP response time (GET/POST) | ≤ 200 ms for 95 % of requests | Application Performance Monitoring (APM) – New Relic/Prometheus |
| Throughput | ≥ 1 000 requests / second under peak load | Load‑testing tool (JMeter, k6) with 500 concurrent virtual users |
| Error rate | ≤ 0.1 % of total requests | Aggregated logs and APM error counters |
| Availability | 99.9 % monthly uptime | Synthetic health‑check pings and SLA dashboards |
| Security incidents | 0 critical incidents per quarter | Security Information & Event Management (SIEM) reports |
| Test coverage | ≥ 80 % of services, ≥ 70 % of controllers | JaCoCo (Java) and Karma/Jest (Angular) coverage reports |
| Mean Time to Recovery (MTTR) | ≤ 5 minutes after failure detection | Incident management system (PagerDuty) metrics |
| UI load time (first paint) | ≤ 1 s on 3G network | Lighthouse performance audit |

The metrics are derived from the concrete size of the system (951 components, 196 REST endpoints) and reflect realistic, measurable targets for the **uvz** platform.

---

*Prepared according to the SEAGuide arc42 quality‑requirements view.*