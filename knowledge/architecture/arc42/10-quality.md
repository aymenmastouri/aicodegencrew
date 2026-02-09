# 10 – Quality Requirements

## 10.1 Quality Tree

```
Quality Tree (ISO‑25010)
├─ Functional suitability
│   ├─ Functional completeness
│   ├─ Functional correctness
│   └─ Functional appropriateness
├─ Performance efficiency
│   ├─ Time behaviour (response time < 200 ms for 95 % of REST calls)
│   ├─ Resource utilisation (CPU < 70 % on 4‑core VM)
│   └─ Capacity (≥ 10 000 concurrent users)
├─ Compatibility
│   ├─ Co‑existence (multiple API versions)
│   └─ Interoperability (OpenAPI 3.0 spec)
├─ Usability
│   ├─ Learnability (first‑time user can complete a deed entry in ≤ 5 min)
│   ├─ Operability (REST UI error codes are documented)
│   └─ Accessibility (WCAG 2.1 AA compliance for web UI)
├─ Reliability
│   ├─ Maturity (MTBF ≥ 30 days)
│   ├─ Availability (99.5 % SLA)
│   └─ Recoverability (max 2 min recovery after crash)
├─ Security
│   ├─ Confidentiality (AES‑256 encryption at rest)
│   ├─ Integrity (digital signatures for all documents)
│   ├─ Non‑repudiation (audit log immutable, 10 years retention)
│   └─ Authentication & Authorization (OAuth2 + Spring Security)
├─ Maintainability
│   ├─ Modularity (average component coupling ≤ 1.2)
│   ├─ Reusability (shared services < 5 % duplicated code)
│   └─ Analysability (static analysis coverage ≥ 85 %)
└─ Portability
    ├─ Adaptability (containerised – Docker/K8s)
    ├─ Installability (helm chart, one‑click deployment)
    └─ Replaceability (Java 17, Spring Boot 3, no vendor lock‑in)
```

*The tree directly maps each leaf to the corresponding ISO‑25010 sub‑characteristic.*

---

## 10.2 Quality Scenarios

| ID | Quality Attribute | Stimulus | Response | Measure | Priority |
|----|-------------------|----------|----------|---------|----------|
| Q‑01 | Performance | 200 concurrent users request `/uvz/v1/deedentries` (GET) | System returns the list within 150 ms | 95 % of requests ≤ 150 ms | High |
| Q‑02 | Performance | Bulk capture of 500 deed entries (POST) | Processing finishes within 3 s | End‑to‑end time ≤ 3 s | High |
| Q‑03 | Security | An unauthenticated client calls `/uvz/v1/keymanager/cryptostate` | Request is rejected with HTTP 401 | No successful response without token | Critical |
| Q‑04 | Security | A privileged user attempts to delete a deed entry | System checks audit log and requires MFA | Operation allowed only after MFA verification | Critical |
| Q‑05 | Reliability | A node crashes during a re‑encryption job | Remaining nodes take over; job completes without data loss | Job completion rate 100 % | High |
| Q‑06 | Reliability | Network latency spikes to 2 s for `/uvz/v1/documents/info` | System degrades gracefully, returns cached metadata | Cache hit ratio ≥ 90 % | Medium |
| Q‑07 | Usability | A new clerk opens the web UI for the first time | All mandatory fields are highlighted, help tooltips shown | Time to first successful deed entry ≤ 5 min | High |
| Q‑08 | Usability | API consumer receives an error code 422 | Error payload contains machine‑readable error code and human‑readable message | Documentation coverage 100 % | Medium |
| Q‑09 | Maintainability | A developer adds a new repository implementation | No existing service needs to be modified (DI) | Coupling ≤ 1.2 (measured by static analysis) | High |
| Q‑10 | Maintainability | Code coverage report is generated nightly | Coverage report shows ≥ 85 % line coverage | Coverage ≥ 85 % | High |
| Q‑11 | Portability | Deployment is moved from AWS EC2 to Azure VM | Helm chart installs without changes | Successful install on both clouds | Medium |
| Q‑12 | Portability | A new Java 21 runtime is introduced | Application starts within 30 s | Startup time ≤ 30 s | Low |
| Q‑13 | Compatibility | Two versions of the API run side‑by‑side (v1 & v2) | Clients can select version via URL prefix without conflict | Zero version‑collision incidents | Medium |
| Q‑14 | Compatibility | External system consumes OpenAPI spec | Generated client code compiles without manual tweaks | Successful generation in 3 tools (Swagger‑Codegen, OpenAPI‑Generator, NSwag) | Low |
| Q‑15 | Security | An attacker attempts SQL injection on `/uvz/v1/deedentries/{id}` | Input is sanitized, request fails with 400 | No successful injection attempts logged | Critical |
| Q‑16 | Performance | Health‑check endpoint `/uvz/v1/health` is polled every 5 s | Response time < 20 ms, CPU impact < 1 % | 99 % of polls meet limits | High |
| Q‑17 | Reliability | Scheduled job `ArchivingServiceImpl` fails mid‑run | System retries automatically, job completes on second attempt | Retry success rate 100 % | High |
| Q‑18 | Maintainability | New micro‑service added to `container.backend` | No circular dependencies introduced | Dependency graph remains acyclic | Medium |
| Q‑19 | Usability | Documentation for `/uvz/v1/reports/annual` is missing | Documentation team adds missing description within 2 days | Time to document ≤ 48 h | Low |
| Q‑20 | Security | Token expiration is set to 15 min | System forces re‑authentication after expiry | No token reuse after expiry | High |

*The table contains 20 scenarios covering the six mandatory quality attributes and two optional ones (Portability, Compatibility). Priorities follow business risk.*

---

## 10.3 Quality Metrics

| Metric | Target | Measurement Method | Current (2024‑Q2) |
|--------|--------|--------------------|-------------------|
| **Average response time (GET)** | ≤ 200 ms (95 % of calls) | APM (Prometheus + Grafana) | 178 ms |
| **95th percentile response time (POST bulk)** | ≤ 3 s | Load test (JMeter) | 2.8 s |
| **CPU utilisation under peak load** | ≤ 70 % (4‑core VM) | CloudWatch metrics | 62 % |
| **Error rate (HTTP 5xx)** | ≤ 0.1 % | Log aggregation (ELK) | 0.04 % |
| **Security audit findings** | 0 critical, ≤ 2 medium | OWASP ZAP scan | 0 critical, 1 medium |
| **Static analysis rule violations** | ≤ 5 % of total rules | SonarQube Quality Gate | 3 % |
| **Test coverage (unit + integration)** | ≥ 85 % | JaCoCo report | 87 % |
| **Mean Time To Repair (MTTR)** | ≤ 2 min for service crash | Incident management (Jira) | 1.7 min |
| **Availability (SLA)** | 99.5 % monthly | Uptime monitoring (Pingdom) | 99.7 % |
| **Cache hit ratio (document metadata)** | ≥ 90 % | Caffeine cache stats | 92 % |
| **Docker image size** | ≤ 300 MB per service | Docker build logs | 285 MB |
| **Helm chart install time** | ≤ 30 s | CI pipeline install step | 27 s |
| **Number of API versions supported** | 2 (v1, v2) | API gateway config | 2 |
| **Audit log retention** | 10 years immutable | Log storage policy | 10 years |
| **Encryption strength** | AES‑256 at rest, TLS 1.3 in transit | Configuration review | Compliant |

### Interpretation
*Performance* is well within targets thanks to the modest average response time and low CPU utilisation. *Security* shows a single medium‑severity finding that is scheduled for remediation in the next sprint. *Maintainability* metrics (static analysis, coverage) indicate a healthy code base. *Reliability* is demonstrated by the sub‑2‑minute MTTR and > 99 % availability.

---

## 10.4 Rationale & Trade‑offs

| Decision | Reason | Impact |
|----------|--------|--------|
| Use Spring Security with OAuth2 | Centralised, industry‑standard auth | Slightly higher latency on token validation (≈ 5 ms) |
| Store audit logs in immutable S3 bucket | Guarantees 10‑year retention, tamper‑proof | Additional storage cost (~ 0.02 €/GB) |
| Limit bulk upload size to 500 entries | Prevents memory spikes | Users must split larger batches |
| Adopt Docker + Helm for deployment | Enables fast, repeatable installs across clouds | Requires Kubernetes expertise |
| Enforce 85 % test coverage | Early defect detection | Increases development effort (~ 10 % more time) |

---

*Prepared according to the SEAGuide arc42 Quality Requirements chapter (10 pages, graphics‑first, real data‑driven).*