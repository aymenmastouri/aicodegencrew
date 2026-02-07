# 10 - Quality Requirements

## 10.1 Quality Tree

```
Quality Requirements
├─ Performance
│   ├─ Response Time
│   └─ Throughput
├─ Availability
│   ├─ Uptime
│   └─ Fault Tolerance
├─ Security
│   ├─ Authentication & Authorization
│   ├─ Data Confidentiality
│   └─ Auditing & Logging
├─ Maintainability
│   ├─ Modularity (Component count: 738, Service count: 173)
│   ├─ Testability (Unit test coverage > 80%)
│   └─ Documentation (Arc42 compliance)
├─ Scalability
│   ├─ Horizontal scaling of 4 containers
│   └─ Elastic load balancing
└─ Usability
    ├─ UI responsiveness (Angular front‑end)
    └─ Accessibility (WCAG 2.1 AA)
```

The tree reflects the main quality attributes identified for the **uvz** system and their sub‑attributes.

## 10.2 Quality Scenarios

| ID | Quality Attribute | Scenario (Trigger → Stimulus → Response) | Expected Response | Priority |
|----|-------------------|------------------------------------------|-------------------|----------|
| QSC‑01 | Performance | User requests a deed‑entry creation (POST /deed) → System receives 200 concurrent requests → Must return a response within **2 s**. | 95 % of responses ≤ 2 s under load. | High |
| QSC‑02 | Availability | A container crashes (e.g., `container.backend`) → Health‑check detects failure → Orchestrator restarts container. | System restores full service within **30 s**. | High |
| QSC‑03 | Security | An unauthenticated user accesses a protected REST endpoint → Request without JWT token → System must reject with **401 Unauthorized**. | Immediate rejection, no data leakage. | High |
| QSC‑04 | Security | A privileged user attempts to delete a deed (DELETE /deed/{id}) → System checks role‑based access → User lacks `ADMIN` role. | Request denied with **403 Forbidden**. | Medium |
| QSC‑05 | Maintainability | A new business rule requires additional validation on `DeedEntryServiceImpl` → Developer adds unit test. | Build pipeline fails if coverage drops below 80 %. | Medium |
| QSC‑06 | Scalability | Traffic spikes to 500 req/s during peak hours → Auto‑scaler adds two additional backend containers. | System maintains average response time ≤ 2 s. | High |
| QSC‑07 | Fault Tolerance | Database connection loss → Service layer receives `SQLTransientConnectionException`. | Service retries up to 3 times, then returns a graceful error (503 Service Unavailable). | Medium |
| QSC‑08 | Usability | User navigates to the dashboard on a mobile device → Front‑end renders UI components. | All UI elements load within **1 s** and meet WCAG 2.1 AA criteria. | Low |
| QSC‑09 | Auditing | An administrator modifies a deed record → System logs the change with user ID, timestamp, and before/after values. | Log entry written to audit store within **200 ms**. | Medium |
| QSC‑10 | Data Integrity | Concurrent updates to the same deed by two services → Optimistic locking version mismatch. | System detects conflict and returns **409 Conflict**; client retries. | High |

### Rationale for Selected Scenarios
- **Performance** and **Scalability** scenarios are driven by the measured **95 % POST/GET** endpoints (95 REST endpoints) and the need to handle peak loads.
- **Security** scenarios reflect the presence of **21 REST interfaces** and the requirement to protect sensitive deed data.
- **Maintainability** leverages the high component count (738) and service count (173) to enforce modularity and test coverage.
- **Availability** uses the container count (4) and relation types (uses, manages) to define recovery objectives.

## 10.3 Quality Metrics

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| Average Response Time (GET) | ≤ 1.5 s | Application Performance Monitoring (APM) – rolling 5‑minute average.
| Average Response Time (POST) | ≤ 2 s | APM – rolling 5‑minute average.
| Throughput (GET) | ≥ 200 req/s | Load testing tool (e.g., JMeter) under sustained load.
| Uptime | 99.9 % per month | Infrastructure monitoring (Prometheus + Grafana).
| Mean Time to Recovery (MTTR) | ≤ 30 s | Incident management logs.
| Security Incident Rate | 0 critical incidents per quarter | Security audit reports.
| Test Coverage (unit) | ≥ 80 % | Code coverage tool (JaCoCo) aggregated per build.
| Documentation Completeness | 100 % of components documented in Arc42 | Manual checklist + automated doc‑gen validation.
| Accessibility Score | ≥ 90 % (aXe) | Automated accessibility testing on UI.
| Audit Log Latency | ≤ 200 ms | Log aggregation timestamps comparison.

### Measurement Cadence
- **Performance** and **Throughput** are measured continuously via APM dashboards and reviewed weekly.
- **Availability** and **MTTR** are tracked by the operations team and reported monthly.
- **Security** metrics are collected after each penetration test (quarterly).
- **Maintainability** metrics (coverage, documentation) are part of the CI pipeline and enforced on every pull request.
- **Usability** and **Accessibility** are evaluated in sprint reviews with stakeholder demos.

---

*This chapter follows the SEAGuide principle of “Graphics First” – the quality tree visualises the hierarchy, while the scenario table and metric table provide concise, measurable information without redundant narrative.*
