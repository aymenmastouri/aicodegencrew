# C4 Level 3: Component Diagram

---

## 3.1 Overview

The **uvz** system follows a layered, Spring‑Boot based backend exposing a rich set of REST APIs.  The component diagram focuses on the **backend container** (`container.backend`) and shows the four main architectural layers:

| Layer | Purpose | Component Count | Key Pattern |
|-------|---------|-----------------|-------------|
| Controllers | HTTP request handling, request validation, response mapping | 32 | Spring `@RestController` / `@Controller` |
| Services | Business logic, orchestration, integration with external systems | 173 | Service layer (`@Service`) |
| Repositories | Data‑access abstraction, JPA / JDBC implementations | 38 | Repository pattern (`@Repository`) |
| Entities | Domain model, JPA‑mapped tables | 199 | JPA `@Entity` |

The diagram (see **c4-component.drawio**) groups components by these layers and uses the C4 visual conventions (blue boxes for internal components, cylinders for databases, etc.).

---

## 3.2 Backend API Components

### 3.2.1 Presentation Layer – Controllers
**Count:** 32 controllers

| Controller | Primary Endpoints | Responsibility |
|------------|-------------------|----------------|
| ActionRestServiceImpl | `/api/actions/**` | Exposes CRUD operations for actions |
| IndexHTMLResourceService | `/` (root) | Serves the SPA entry point |
| StaticContentController | `/static/**` | Delivers static assets |
| JsonAuthorizationRestServiceImpl | `/api/auth/**` | Handles JSON‑based auth tokens |
| KeyManagerRestServiceImpl | `/api/keys/**` | Key management operations |
| ArchivingRestServiceImpl | `/api/archive/**` | Archive creation & retrieval |
| DeedEntryRestServiceImpl | `/api/deed‑entries/**` | Deed entry CRUD |
| DeedRegistryRestServiceImpl | `/api/registry/**` | Registry queries |
| ReportRestServiceImpl | `/api/reports/**` | Report generation |
| NumberManagementRestServiceImpl | `/api/numbers/**` | Number allocation & management |

*The full list of 32 controllers is available in the architecture repository.*

### 3.2.2 Business Layer – Services
**Count:** 173 services

| Service | Responsibility | Key Dependencies |
|---------|----------------|-------------------|
| ActionServiceImpl | Business rules for actions | ActionDao, ActionDaoImpl |
| ArchiveManagerServiceImpl | Coordinates archiving workflow | ArchivingServiceImpl, Repository layer |
| MockKmService | Mock key‑manager for tests | – |
| XnpKmServiceImpl | Integration with external KM system | RestTemplate, Security config |
| DeedEntryServiceImpl | Core deed‑entry processing | DeedEntryDao, Validation components |
| DeedRegistryServiceImpl | Registry specific logic | DeedRegistryDao |
| DocumentMetaDataServiceImpl | Handles document metadata CRUD | DocumentMetaDataDao |
| HandoverDataSetServiceImpl | Handover dataset creation | HandoverDataSetDao |
| ReportServiceImpl | Report data aggregation | ReportMetadataDao |
| NumberManagementServiceImpl | Number gap & skip management | UzvNumberManagerDao, UzvNumberGapManagerDao |

*Only a representative subset is shown; the remaining 163 services follow the same pattern.*

### 3.2.3 Data Access Layer – Repositories
**Count:** 38 repositories

| Repository | Managed Entity | Notable Custom Queries |
|------------|----------------|------------------------|
| ActionDao | ActionEntity | findByStatus, findRecent |
| DeedEntryDao | DeedEntryEntity | findByNumber, findActive |
| DeedEntryLockDao | DeedEntryLockEntity | lockById |
| DocumentMetaDataDao | DocumentMetaDataEntity | searchByTitle |
| HandoverDataSetDao | HandoverDataSetEntity | findPending |
| ParticipantDao | ParticipantEntity | findByRole |
| SignatureInfoDao | SignatureInfoEntity | findValidSignatures |
| UzvNumberManagerDao | UzvNumberEntity | nextAvailableNumber |
| ReportMetadataDao | ReportMetadataEntity | findByReportId |
| JobDao | JobEntity | findPendingJobs |

*The remaining 28 repositories provide similar CRUD and query capabilities for the rest of the domain model.*

### 3.2.4 Domain Layer – Entities
**Count:** 199 JPA entities (e.g., `ActionEntity`, `DeedEntryEntity`, `ParticipantEntity`, `SignatureInfoEntity`, …).  They map to relational tables in the PostgreSQL database (cylinder symbol in the diagram).

---

## 3.3 Component Dependencies

### 3.3.1 Layer Interaction Rules
| From Layer | To Layer | Allowed |
|------------|----------|---------|
| Controllers | Services | ✅ |
| Services | Repositories | ✅ |
| Services | Other Services | ✅ (via dependency injection) |
| Repositories | Entities | ✅ |
| Controllers | Repositories | ❌ (should go through Services) |
| Controllers | Entities | ❌ |

These rules are enforced by the Spring container and static code analysis (e.g., ArchUnit).

### 3.3.2 Typical Request Flow
```
HTTP Request → Controller (e.g., DeedEntryRestServiceImpl)
    → Service (DeedEntryServiceImpl)
        → Repository (DeedEntryDao)
            → Database (PostgreSQL)
        ← Service aggregates domain objects (Entities)
    ← Controller builds REST response (DTO)
```

---

## 3.4 Diagram Reference
The **C4 Component diagram** is stored as a Draw.io file:

- **File:** `c4/c4-component.drawio`
- **Legend:** Uses blue rectangles for internal components, gray for external systems, cylinders for the PostgreSQL database, and dashed lines for container boundaries.

---

## 3.5 Summary
The component view gives stakeholders a clear picture of the backend’s internal structure, the distribution of responsibilities across layers, and the interaction patterns that underpin the uvz system’s functional capabilities.  It serves as a basis for impact analysis, performance tuning, and future evolution (e.g., migration to micro‑services or cloud‑native deployment).

---

*Document generated on 2026‑02‑07.*