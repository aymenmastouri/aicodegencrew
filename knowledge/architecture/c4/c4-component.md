# C4 Level 3: Component Diagram

## 3.1 Overview

The **uvz** system is a Spring‑Boot based backend that implements the core business functionality for deed‑entry management.  All runtime code lives in the `container.backend` container (Spring Boot).  The component diagram focuses on the internal structure of this container.

| Layer | Purpose | Component Count |
|-------|----------|-----------------|
| Controllers | HTTP request handling (REST) | 32 |
| Services | Business logic, orchestration | 184 |
| Repositories | Data‑access (JPA) | 38 |
| Entities | Domain model (JPA entities) | 360 |

The diagram does **not** show every individual component (that would be unreadable).  Instead it aggregates by layer and highlights representative samples.

---

## 3.2 Backend API Components

### 3.2.1 Layer Overview

| Layer | Key Stereotype | Typical Technology |
|-------|----------------|--------------------|
| Controllers | `@RestController` | Spring MVC, Spring WebFlux |
| Services | `@Service` | Spring Service Layer, Transaction Management |
| Repositories | `@Repository` / Spring Data JPA | JPA, Hibernate |
| Entities | `@Entity` | JPA, Hibernate |

### 3.2.2 Controllers (sample)

| Controller | Primary Endpoint(s) | Responsibility |
|------------|--------------------|----------------|
| `ActionRestServiceImpl` | `/api/actions/**` | CRUD for Action domain objects |
| `IndexHTMLResourceService` | `/` (root) | Serves static index page |
| `StaticContentController` | `/static/**` | Serves static assets |
| `JsonAuthorizationRestServiceImpl` | `/api/auth/**` | JSON‑based authentication/authorization |
| `KeyManagerRestServiceImpl` | `/api/keys/**` | Management of cryptographic keys |
| `ArchivingRestServiceImpl` | `/api/archive/**` | Archive creation and retrieval |
| `DeedEntryRestServiceImpl` | `/api/deed‑entries/**` | Full CRUD for deed entries |
| `ReportRestServiceImpl` | `/api/reports/**` | Generation of various reports |
| `NumberManagementRestServiceImpl` | `/api/numbers/**` | Number allocation and gap management |
| `JobRestServiceImpl` | `/api/jobs/**` | Background job control |

### 3.2.3 Services (sample)

| Service | Responsibility |
|---------|----------------|
| `ActionServiceImpl` | Business rules for actions |
| `HealthCheck` | Liveness / readiness probes |
| `ArchiveManagerServiceImpl` | Coordination of archive lifecycle |
| `MockKmService` | Mock implementation for key‑manager integration |
| `KeyManagerServiceImpl` | Cryptographic key handling |
| `WaWiServiceImpl` | Integration with external WaWi system |
| `DeedEntryServiceImpl` | Core deed‑entry processing |
| `DeedRegistryServiceImpl` | Registry‑wide operations |
| `ReportServiceImpl` | Report data aggregation |
| `NumberManagementServiceImpl` | Number range allocation logic |

### 3.2.4 Repositories (sample)

| Repository | Managed Entity |
|------------|----------------|
| `ActionDao` | `ActionEntity` |
| `DeedEntryDao` | `DeedEntryEntity` |
| `DeedEntryLockDao` | `DeedEntryLockEntity` |
| `DocumentMetaDataDao` | `DocumentMetaDataEntity` |
| `HandoverDataSetDao` | `HandoverDataSetEntity` |
| `ParticipantDao` | `ParticipantEntity` |
| `SignatureInfoDao` | `SignatureInfoEntity` |
| `UvzNumberManagerDao` | `UvzNumberManagerEntity` |
| `JobDao` | `JobEntity` |
| `ReportMetadataDao` | `ReportMetadataEntity` |

### 3.2.5 Entities (sample)

| Entity | Table (approx.) |
|--------|-----------------|
| `ActionEntity` | `action` |
| `DeedEntryEntity` | `deed_entry` |
| `DeedEntryLogEntity` | `deed_entry_log` |
| `DocumentMetaDataEntity` | `document_metadata` |
| `HandoverDataSetEntity` | `handover_dataset` |
| `ParticipantEntity` | `participant` |
| `SignatureInfoEntity` | `signature_info` |
| `UvzNumberManagerEntity` | `uvz_number_manager` |
| `JobEntity` | `job` |
| `ReportMetadataEntity` | `report_metadata` |

---

## 3.3 Component Dependencies

### 3.3.1 Layer Rules

| From \ To | Controllers | Services | Repositories | Entities |
|-----------|------------|----------|--------------|----------|
| Controllers | ✅ (self) | ✅ (calls) | ❌ (should not) | ❌ |
| Services | ❌ | ✅ (self) | ✅ (uses) | ❌ |
| Repositories | ❌ | ✅ (uses) | ✅ (self) | ✅ (maps) |
| Entities | ❌ | ❌ | ✅ (persisted by) | ✅ (self) |

### 3.3.2 Typical Request Flow

```
HTTP Request → Controller (REST) → Service (business) → Repository (JPA) → Database
```

### 3.3.3 Example Interaction (Deed Entry Creation)
1. **POST** `/api/deed‑entries` hits `DeedEntryRestServiceImpl`.
2. Controller validates input and forwards to `DeedEntryServiceImpl`.
3. Service performs domain checks, invokes `DeedEntryDao` to persist a new `DeedEntryEntity`.
4. Repository returns the persisted entity; service enriches with generated numbers via `NumberManagementServiceImpl`.
5. Service returns DTO; controller serialises to JSON response.

---

## 3.4 Diagram

The full component diagram is stored as a Draw.io file:

- **File:** `c4/c4-component.drawio`
- The diagram follows the SEAGuide C4 visual conventions (blue boxes for internal components, gray for external systems, cylinders for databases, person icons for users, dashed lines for boundaries).

> **Note:** The diagram aggregates the 32 controllers, 184 services, 38 repositories and 360 entities into the four logical layers shown above.  Individual component boxes are omitted for readability; the sample tables provide concrete examples.

---

*Document generated automatically from architecture facts (statistics, component listings, and repository data).*
