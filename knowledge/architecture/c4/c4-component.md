# C4 Level 3: Component Diagram

## 3.1 Overview

The **uvz** system is implemented as a Spring Boot backend exposing a rich set of REST APIs. The backend follows a classic **Layered Architecture** with four main layers:

| Layer | Purpose | Component Count | Typical Pattern |
|-------|---------|-----------------|-----------------|
| Controllers | HTTP request handling, mapping to REST endpoints | 32 | Spring `@RestController` |
| Services | Business logic, orchestration of use‑cases | 173 | Service layer (`@Service`) |
| Repositories | Data‑access, persistence abstraction | 38 | Spring Data JPA repositories |
| Entities | Domain model, JPA‑mapped tables | 199 | `@Entity` classes |

The diagram below (see **c4-component.drawio**) visualises these layers and the allowed dependencies between them.

---

## 3.2 Backend API Components

### 3.2.1 Layer Overview
*(see table above)*

### 3.2.2 Presentation Layer – Controllers
**Count:** 32 controllers

| Controller | Representative Endpoints | Responsibility |
|------------|--------------------------|----------------|
| `ActionRestServiceImpl` | `POST /actions`, `GET /actions/{id}` | Manage CRUD for actions |
| `IndexHTMLResourceService` | `GET /` | Serve the SPA entry point |
| `StaticContentController` | `GET /static/**` | Deliver static assets |
| `JsonAuthorizationRestServiceImpl` | `POST /auth/json` | JSON‑based authentication |
| `KeyManagerRestServiceImpl` | `GET /keys`, `POST /keys` | Key management |
| `ArchivingRestServiceImpl` | `POST /archive` | Archive operations |
| `ReportRestServiceImpl` | `GET /reports/**` | Generate and retrieve reports |
| `JobRestServiceImpl` | `GET /jobs`, `POST /jobs` | Job scheduling |
| `NumberManagementRestServiceImpl` | `GET /numbers`, `POST /numbers` | Number allocation |
| `OpenApiConfig` | – | OpenAPI/Swagger configuration |

### 3.2.3 Business Layer – Services
**Count:** 173 services

| Service | Responsibility | Typical Dependencies |
|---------|----------------|----------------------|
| `ActionServiceImpl` | Core action processing | Controllers, Repositories |
| `ArchiveManagerServiceImpl` | Archive lifecycle | Repositories, Entities |
| `HealthCheck` | System health endpoint | – |
| `MockKmService` | Mock key‑manager for tests | – |
| `KeyManagerServiceImpl` | Cryptographic key handling | Repositories |
| `WaWiServiceImpl` | External WA‑WI integration | – |
| `BusinessPurposeServiceImpl` | Business purpose validation | Repositories |
| `DocumentMetaDataServiceImpl` | Document metadata handling | Repositories |
| `SignatureFolderServiceImpl` | Signature folder orchestration | Repositories |
| `ReportServiceImpl` | Report generation logic | Repositories |

### 3.2.4 Data Access Layer – Repositories
**Count:** 38 repositories

| Repository | Backing Entity | Custom Queries |
|------------|----------------|----------------|
| `ActionDao` | `ActionEntity` | – |
| `DeedEntryDao` | `DeedEntryEntity` | Complex JPQL for deed lookup |
| `DeedEntryLockDao` | `DeedEntryLockEntity` | Lock‑management queries |
| `DocumentMetaDataDao` | `DocumentMetaDataEntity` | Metadata search |
| `HandoverDataSetDao` | `HandoverDataSetEntity` | Batch fetches |
| `ParticipantDao` | `ParticipantEntity` | Participant lookup |
| `SignatureInfoDao` | `SignatureInfoEntity` | Signature retrieval |
| `UvzNumberManagerDao` | `UvzNumberManagerEntity` | Number allocation |
| `JobDao` | `JobEntity` | Job persistence |
| `ReportMetadataDao` | `ReportMetadataEntity` | Report metadata queries |

### 3.2.5 Domain Layer – Entities
**Count:** 199 entities

| Entity | Table | Notable Relationships |
|--------|-------|-----------------------|
| `ActionEntity` | `action` | Many‑to‑One `User`
| `DeedEntryEntity` | `deed_entry` | One‑to‑Many `DeedEntryLog`
| `DocumentMetaDataEntity` | `document_meta` | One‑to‑One `SignatureInfo`
| `HandoverDataSetEntity` | `handover_dataset` | One‑to‑Many `HandoverHistory`
| `ParticipantEntity` | `participant` | Many‑to‑Many `DeedEntry`
| `SignatureInfoEntity` | `signature_info` | One‑to‑One `DocumentMetaData`
| `SuccessorBatchEntity` | `successor_batch` | One‑to‑Many `SuccessorDetails`
| `UvzNumberManagerEntity` | `uvz_number_manager` | Unique constraint on `number`
| `JobEntity` | `job` | Scheduler linkage |
| `ReportMetadataEntity` | `report_metadata` | One‑to‑Many `Report`

---

## 3.3 Component Dependencies

### 3.3.1 Layer Rules
| From | To | Allowed |
|------|----|---------|
| Controllers | Services | ✅ |
| Services | Repositories | ✅ |
| Repositories | Entities | ✅ |
| Services | Entities | ❌ (access only via Repositories) |
| Controllers | Repositories | ❌ (must go through Services) |

### 3.3.2 Request Flow Example
```
HTTP Request → Controller (e.g. ActionRestServiceImpl)
    → Service (ActionServiceImpl)
        → Repository (ActionDao)
            → Entity (ActionEntity) → Database
```

---

## Component Diagram
The full C4 Component diagram is stored in **c4-component.drawio**. It visualises the four layers, sample components, and the allowed directional dependencies.

---

*Document generated automatically from architecture facts (32 controllers, 173 services, 38 repositories, 199 entities).*
