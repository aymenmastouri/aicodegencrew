# C4 Level 3: Component Diagram

---

## 3.1 Overview
The **backend** container (`container.backend`) implements the core business capabilities of the *uvz* system. It follows a classic **hexagonal / layered architecture** with the following logical layers:

| Layer | Purpose | Component Count |
|-------|---------|-----------------|
| Presentation (Controllers) | Expose REST/HTTP endpoints, translate requests to domain calls | **32** |
| Application (Services) | Business logic, orchestration, transaction management | **184** |
| Data Access (Repositories) | Persistence abstraction, JPA/Hibernate data access | **38** |
| Domain (Entities) | Rich domain model, JPA entities, validation rules | **360** |

The component counts are derived from the architecture knowledge base (see `get_statistics`).

---

## 3.2 Presentation Layer – Controllers
### 3.2.1 Sample Controllers (Top 10)
| Controller | Container | Description |
|------------|-----------|-------------|
| ActionRestServiceImpl | container.backend | Handles CRUD for `Action` domain objects |
| IndexHTMLResourceService | container.backend | Serves static HTML entry point |
| StaticContentController | container.backend | Provides static resources (JS/CSS) |
| CustomMethodSecurityExpressionHandler | container.backend | Custom security expressions for method-level security |
| JsonAuthorizationRestServiceImpl | container.backend | Authorization checks for JSON APIs |
| ProxyRestTemplateConfiguration | container.backend | Configures proxy-aware RestTemplate |
| TokenAuthenticationRestTemplateConfigurationSpringBoot | container.backend | Token based authentication for outbound calls |
| KeyManagerRestServiceImpl | container.backend | Key management REST API |
| ArchivingRestServiceImpl | container.backend | Archive related operations |
| RestrictedDeedEntryEntity | container.backend | (Note: Entity exposed via controller for restricted access) |

*The full list of 32 controllers is available in the architecture repository.*

---

## 3.3 Application Layer – Services
### 3.3.1 Sample Services (Top 10)
| Service | Container | Description |
|---------|-----------|-------------|
| ActionServiceImpl | container.backend | Core business logic for `Action` entities |
| ActionWorkerService | container.backend | Asynchronous processing of actions |
| HealthCheck | container.backend | Liveness and readiness probes |
| ArchiveManagerServiceImpl | container.backend | Coordinates archiving workflow |
| MockKmService | container.backend | Mock implementation for key manager (test) |
| XnpKmServiceImpl | container.backend | Production key manager integration |
| KeyManagerServiceImpl | container.backend | Service façade for key management |
| WaWiServiceImpl | container.backend | Integration with external WaWi system |
| ArchivingOperationSignerImpl | container.backend | Cryptographic signing of archive operations |
| ArchivingServiceImpl | container.backend | High‑level archiving service API |

---

## 3.4 Data Access Layer – Repositories
### 3.4.1 Sample Repositories (Top 10)
| Repository | Container | Description |
|------------|-----------|-------------|
| ActionDao | container.backend | JPA repository for `ActionEntity` |
| DeedEntryConnectionDao | container.backend | Handles connections between deed entries |
| DeedEntryDao | container.backend | CRUD for `DeedEntryEntity` |
| DeedEntryLockDao | container.backend | Lock management for deed entries |
| DeedEntryLogsDao | container.backend | Persistence of deed entry logs |
| DeedRegistryLockDao | container.backend | Registry lock handling |
| DocumentMetaDataDao | container.backend | Document metadata persistence |
| FinalHandoverDataSetDao | container.backend | Final handover data set storage |
| HandoverDataSetDao | container.backend | Handover data set CRUD |
| ParticipantDao | container.backend | Participant information persistence |

---

## 3.5 Domain Layer – Entities
### 3.5.1 Sample Entities (Top 10)
| Entity | Container | Description |
|--------|-----------|-------------|
| ActionEntity | container.backend | Represents an action performed in the system |
| ActionStreamEntity | container.backend | Stream of actions for audit purposes |
| ChangeEntity | container.backend | Change tracking for domain objects |
| ConnectionEntity | container.backend | Links between domain objects |
| CorrectionNoteEntity | container.backend | Notes for corrections on deeds |
| DeedCreatorHandoverInfoEntity | container.backend | Handover info for deed creators |
| DeedEntryEntity | container.backend | Core deed entry data |
| DeedEntryLockEntity | container.backend | Lock state for a deed entry |
| DeedEntryLogEntity | container.backend | Log entries for deed modifications |
| DeedRegistryLockEntity | container.backend | Registry lock representation |

---

## 3.6 Component Interaction Rules
| From Layer | To Layer | Allowed? |
|------------|----------|---------|
| Controllers | Services | ✅ |
| Services | Repositories | ✅ |
| Services | Other Services (via interfaces) | ✅ |
| Repositories | Entities | ✅ |
| Controllers | Repositories | ❌ (should go through Services) |
| Controllers ↔ Entities | ❌ (direct access prohibited) |

### 3.6.1 Typical Request Flow
```
HTTP Request → Controller → Service → Repository → Database (Entity) → Service → Controller → HTTP Response
```

---

## 3.7 Component Diagram
A **C4 Component diagram** visualising the layers and sample components is stored as a Draw.io file:

- **File:** `c4/c4-component.drawio`
- The diagram follows SEAGuide C4 conventions (blue boxes for internal components, gray for external, cylinders for databases, person icons for users, dashed boundaries for layers).

---

## 3.8 Summary
* The backend container hosts **951** components across six logical layers.
* Controllers, Services, Repositories, and Entities are the primary building blocks.
* Interaction rules enforce a clean separation of concerns, supporting maintainability and testability.
* The component diagram (see above) provides a high‑level visual reference for architects, developers, and reviewers.

---

*Document generated on 2026‑02‑09 using automated architecture extraction tools.*