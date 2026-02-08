# C4 Level 3: Component Diagram

## 3.1 Overview
The backend container **container.backend** implements the UVZ system’s core business capabilities. It follows a classic **Layered Architecture** (Presentation → Application → Domain → Data‑Access) and is built with **Spring Boot** (Java/Gradle).

## 3.2 Layer Overview
| Layer | Purpose | Component Count | Key Pattern |
|-------|---------|-----------------|-------------|
| Presentation (Controllers) | HTTP request handling, REST endpoints | **32** | `@RestController` / `@Controller` |
| Application (Services) | Business logic, orchestration | **184** | Service‑layer pattern, `@Service` |
| Domain (Entities) | JPA domain model | **360** | `@Entity` with relationships |
| Data‑Access (Repositories) | Persistence abstraction, CRUD | **38** | Spring Data JPA repositories |

## 3.3 Presentation Layer – Controllers
**Total Controllers:** 32 (shown are the first 10 most frequently referenced)
| Controller | Package (if known) | Primary Responsibility |
|-----------|-------------------|-----------------------|
| ActionRestServiceImpl |  | Exposes CRUD for `Action` domain |
| IndexHTMLResourceService |  | Serves static index HTML |
| StaticContentController |  | Serves static assets (JS/CSS) |
| CustomMethodSecurityExpressionHandler |  | Provides custom security expressions |
| JsonAuthorizationRestServiceImpl |  | Handles JSON‑based authorisation |
| ProxyRestTemplateConfiguration |  | Configures RestTemplate proxy settings |
| TokenAuthenticationRestTemplateConfigurationSpringBoot |  | Token‑based authentication for outbound calls |
| KeyManagerRestServiceImpl |  | Key‑management REST API |
| ArchivingRestServiceImpl |  | Archive‑related operations |
| RestrictedDeedEntryEntity |  | REST façade for restricted deed entry |

## 3.4 Application Layer – Services
**Total Services:** 184 (first 10 representative services)
| Service | Package | Responsibility |
|---------|---------|----------------|
| ActionServiceImpl |  | Core business rules for `Action` |
| ActionWorkerService |  | Background processing of actions |
| HealthCheck |  | Liveness / readiness probes |
| ArchiveManagerServiceImpl |  | Coordinates archiving workflow |
| MockKmService |  | Mock implementation for key‑manager during tests |
| XnpKmServiceImpl |  | Real key‑manager integration |
| KeyManagerServiceImpl |  | High‑level key‑management operations |
| WaWiServiceImpl |  | Handles WaWi (land‑registry) specific logic |
| ArchivingOperationSignerImpl |  | Cryptographic signing of archiving ops |
| ArchivingServiceImpl |  | Business logic for archiving |

## 3.5 Data‑Access Layer – Repositories
**Total Repositories:** 38 (first 10 shown)
| Repository | Package | Managed Entity |
|------------|---------|----------------|
| ActionDao |  | `ActionEntity` |
| DeedEntryConnectionDao |  | `DeedEntryConnectionEntity` |
| DeedEntryDao |  | `DeedEntryEntity` |
| DeedEntryLockDao |  | `DeedEntryLockEntity` |
| DeedEntryLogsDao |  | `DeedEntryLogEntity` |
| DeedRegistryLockDao |  | `DeedRegistryLockEntity` |
| DocumentMetaDataDao |  | `DocumentMetaDataEntity` |
| FinalHandoverDataSetDao |  | `FinalHandoverDataSetEntity` |
| HandoverDataSetDao |  | `HandoverDataSetEntity` |
| ParticipantDao |  | `ParticipantEntity` |

## 3.6 Domain Layer – Entities
**Total Entities:** 360. They are JPA‑annotated classes representing the core UVZ domain (e.g., `ActionEntity`, `DeedEntryEntity`, `ParticipantEntity`, `SignatureInfoEntity`, …). Relationships are modelled with `@OneToMany`, `@ManyToOne`, etc.

## 3.7 Component Interaction Rules
| From Layer | To Layer | Allowed |
|------------|----------|---------|
| Controllers | Services | ✅ |
| Services | Repositories | ✅ |
| Services | Entities | ✅ (read/write) |
| Repositories | Entities | ✅ |
| Controllers | Repositories | ❌ (must go through Services) |

## 3.8 Typical Request Flow
```
Client → HTTP → Controller (REST) → Service (business) → Repository (JPA) → Database
```
The reverse flow (responses, exceptions) follows the same path back to the client.

## 3.9 Component Diagram
The full C4 Component diagram is stored as a Draw.io file:

- **File:** `c4/c4-component.drawio`
- **Legend:**
  - Blue boxes – internal components (controllers, services, repositories, entities)
  - Gray cylinders – external databases (PostgreSQL, H2)
  - Dashed lines – architectural boundaries (layer constraints)

> **Note:** The diagram aggregates components by layer (not every of the 951 components is shown individually) to keep it readable while still conveying the architectural structure.

---
*Document generated on 2026‑02‑08 using real architecture facts.*