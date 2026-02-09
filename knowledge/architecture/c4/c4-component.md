# C4 Level 3: Component Diagram

## 3.1 Overview
The backend container **container.backend** implements the core business capabilities of the *uvz* system. It follows a classic **hexagonal / layered architecture** with the following logical layers (as identified by the architecture statistics):

| Layer | Purpose | Component Count |
|-------|---------|-----------------|
| Presentation (Controllers) | HTTP request handling, REST endpoints | **32** |
| Application (Services) | Business logic orchestration | **184** |
| Domain (Entities) | JPA entity model | **360** |
| Data Access (Repositories) | Persistence abstraction, DAO layer | **38** |
| Infrastructure | Cross‑cutting concerns (security, scheduling, configuration) | see below |

The diagram below (see `c4-component.drawio`) visualises these layers as grouped components inside the backend container.

---

## 3.2 Backend API Components
### 3.2.1 Presentation Layer – Controllers
**Total Controllers:** 32

| Controller | Representative Endpoints | Responsibility |
|------------|--------------------------|----------------|
| `ActionRestServiceImpl` | `/api/actions/**` | Exposes CRUD for Action entities |
| `KeyManagerRestServiceImpl` | `/api/keys/**` | Key management operations |
| `ArchivingRestServiceImpl` | `/api/archiving/**` | Archive creation and retrieval |
| `DeedEntryRestServiceImpl` | `/api/deed‑entries/**` | Deed entry lifecycle |
| `ReportRestServiceImpl` | `/api/reports/**` | Report generation |
| `StaticContentController` | `/static/**` | Serves static UI assets |
| `JsonAuthorizationRestServiceImpl` | `/api/auth/**` | JSON‑based auth handling |
| `OpenApiConfig` | `/v3/api-docs/**` | OpenAPI documentation |
| `DefaultExceptionHandler` | – | Global exception mapping |
| `JobRestServiceImpl` | `/api/jobs/**` | Job scheduling API |

*(list truncated – full list available in source)*

### 3.2.2 Application Layer – Services
**Total Services:** 184 (sample shown)

| Service | Core Responsibility | Key Dependencies |
|---------|---------------------|-------------------|
| `ActionServiceImpl` | Business rules for actions | `ActionDao`, `ActionRestServiceImpl` |
| `ArchiveManagerServiceImpl` | Archive lifecycle management | `ArchivingServiceImpl`, `DocumentMetaDataServiceImpl` |
| `HealthCheck` | System health endpoint | – |
| `MockKmService` | Mock key‑manager for tests | – |
| `KeyManagerServiceImpl` | Cryptographic key handling | `KeyManagerRestServiceImpl` |
| `BusinessPurposeServiceImpl` | Business purpose validation | `BusinessPurposeRestServiceImpl` |
| `ReportServiceImpl` | Report data aggregation | `ReportMetadataDao` |
| `NumberManagementServiceImpl` | UVZ number allocation | `UvzNumberManagerDao` |
| `SignatureFolderServiceImpl` | Signature folder orchestration | `SignatureInfoDao` |
| `JobServiceImpl` | Background job execution | `JobDao` |

### 3.2.3 Data Access Layer – Repositories
**Total Repositories:** 38 (sample shown)

| Repository | Managed Entity | Notable Custom Queries |
|------------|----------------|------------------------|
| `ActionDao` | `ActionEntity` | findByStatus, findRecent |
| `DeedEntryDao` | `DeedEntryEntity` | findByDeedNumber |
| `DocumentMetaDataDao` | `DocumentMetaDataEntity` | searchByMetadata |
| `UvzNumberManagerDao` | `UvzNumberEntity` | nextAvailableNumber |
| `SignatureInfoDao` | `SignatureInfoEntity` | findPendingSignatures |
| `JobDao` | `JobEntity` | findDueJobs |
| `ReportMetadataDao` | `ReportMetadataEntity` | findByReportId |
| `ParticipantDao` | `ParticipantEntity` | findActiveParticipants |
| `SuccessorBatchDao` | `SuccessorBatchEntity` | batchProcessingStatus |
| `FinalHandoverDataSetDao` | `FinalHandoverDataSetEntity` | findByHandoverId |

### 3.2.4 Domain Layer – Entities
**Total Entities:** 360 (excerpt)

| Entity | Table | Primary Relationships |
|--------|-------|-----------------------|
| `ActionEntity` | `action` | `ActionStreamEntity` (one‑to‑many) |
| `DeedEntryEntity` | `deed_entry` | `DeedRegistryEntity`, `DeedTypeEntity` |
| `DocumentMetaDataEntity` | `document_metadata` | `SignatureInfoEntity` (one‑to‑many) |
| `UvzNumberEntity` | `uvz_number` | – |
| `ReportMetadataEntity` | `report_metadata` | `ReportEntity` (one‑to‑many) |
| `ParticipantEntity` | `participant` | `DeedEntryEntity` (many‑to‑many) |
| `SignatureInfoEntity` | `signature_info` | `DocumentMetaDataEntity` |
| `SuccessorBatchEntity` | `successor_batch` | `SuccessorDeedSelectionEntity` |
| `HandoverDataSetEntity` | `handover_dataset` | `DeedEntryEntity` |
| `JobEntity` | `job` | – |

---

## 3.3 Component Dependencies & Interaction Rules
### 3.3.1 Layer Interaction Matrix
| From \ To | Presentation | Application | Domain | Data Access | Infrastructure |
|-----------|--------------|-------------|--------|-------------|----------------|
| Presentation | – | **uses** | – | **uses** | – |
| Application | – | – | **uses** | **uses** | **uses** |
| Domain | – | – | – | **uses** | – |
| Data Access | – | – | – | – | **uses** |
| Infrastructure | – | – | – | – | – |

*Only upward dependencies are allowed (no circular calls).*

### 3.3.2 Typical Request Flow
```
Client → HTTP → Controller (e.g., ActionRestServiceImpl)
    → Service (ActionServiceImpl)
        → Repository (ActionDao)
            → Database (PostgreSQL)
    ← Service returns DTO
← Controller serialises JSON
Client receives response
```

### 3.3.3 Cross‑Cutting Concerns
* **Security** – `AuthGuard` and `AuthenticationHttpInterceptor` intercept all controller calls.
* **Logging** – `BusinessLoggingResolverService` is injected into services for audit trails.
* **Error Handling** – `DefaultExceptionHandler` maps exceptions to HTTP status codes.
* **Rate Limiting** – `RateLimitingInterceptor` applied at the controller layer.

---

## 3.4 Diagram Reference
The full C4 Component diagram is stored as a Draw.io file:

- **File:** `c4/c4-component.drawio`
- **Legend:**
  - Blue boxes – internal components (controllers, services, repositories, entities)
  - Gray cylinders – external databases (PostgreSQL, H2 for tests)
  - Dashed lines – dependency boundaries between layers
  - Arrowheads – direction of usage

---

## 3.5 Summary
The component landscape of the *uvz* backend is deliberately modular:
* **32** REST controllers expose a clean API surface.
* **184** services encapsulate business rules, keeping controllers thin.
* **38** repositories abstract persistence, enabling easy swapping of the underlying RDBMS.
* **360** JPA entities model the rich domain of deeds, numbers, and signatures.
* Strict layer‑wise dependencies enforce maintainability and testability.

This documentation, together with the accompanying Draw.io diagram, satisfies the SEAGuide C4 Level‑3 requirements for the *uvz* system.
