# C4 Level 3: Component Diagram

## 3.1 Overview
The backend container (`container.backend`) implements the core business functionality of the **uvz** system. It follows a classic layered architecture (Controller → Service → Repository → Entity) built with **Spring Boot**. The component landscape is large – 951 components in total – but the most relevant ones for the component diagram are the **controllers**, **services**, **repositories**, and **entities**.

| Layer | Purpose | Component Count | Typical Stereotype |
|-------|---------|-----------------|--------------------|
| Controllers | HTTP request handling, REST endpoints | 32 | `@RestController` |
| Services | Business logic, orchestration | 184 | `@Service` |
| Repositories | Data‑access, JPA / Spring Data | 38 | `@Repository` |
| Entities | Domain model, JPA entities | 360 | `@Entity` |

The diagram (see *c4-component.drawio*) shows each layer as a logical box; individual components are omitted for readability and replaced by aggregated symbols.

---

## 3.2 Backend API Components

### 3.2.1 Controllers (Presentation Layer)
**Count:** 32 controllers

| Controller | Representative Endpoints | Responsibility |
|------------|--------------------------|----------------|
| `ActionRestServiceImpl` | `POST /actions`, `GET /actions/{id}` | Manage CRUD for Action entities |
| `IndexHTMLResourceService` | `GET /` | Serve the SPA entry point |
| `StaticContentController` | `GET /static/**` | Deliver static assets |
| `JsonAuthorizationRestServiceImpl` | `POST /auth/json` | JSON‑based authentication |
| `KeyManagerRestServiceImpl` | `GET /keys`, `POST /keys` | Key management API |
| `ArchivingRestServiceImpl` | `POST /archive` | Archive creation and retrieval |
| `ReportRestServiceImpl` | `GET /reports/**` | Reporting services |
| `NumberManagementRestServiceImpl` | `GET /numbers`, `POST /numbers` | Number allocation and gap management |
| `JobRestServiceImpl` | `GET /jobs/**` | Job monitoring |
| `OpenApiConfig` | – | OpenAPI/Swagger configuration |
| `DefaultExceptionHandler` | – | Global exception handling |
| `ResourceFactory` | – | Factory for external resources |
| `NotaryRepresentationRestServiceImpl` | `GET /notary/**` | Notary data exposure |
| `OfficialActivityMetadataRestServiceImpl` | `GET /official/**` | Official activity metadata |
| `ReportMetadataRestServiceImpl` | `GET /report-metadata/**` | Report metadata handling |
| `OpenApiOperationAuthorizationRightCustomizer` | – | Customizes OpenAPI operation security |
| `JobRestServiceImpl` | `GET /jobs/**` | Job management |
| `ReencryptionJobRestServiceImpl` | `POST /jobs/reencrypt` | Re‑encryption job trigger |
| `HandoverDataSetRestServiceImpl` | `GET /handover/**` | Handover dataset API |
| `DeedEntryRestServiceImpl` | `GET /deed‑entry/**` | Deed entry CRUD |
| `DeedRegistryRestServiceImpl` | `GET /deed‑registry/**` | Registry operations |
| `DeedTypeRestServiceImpl` | `GET /deed‑type/**` | Deed type lookup |
| `DocumentMetaDataRestServiceImpl` | `GET /doc‑metadata/**` | Document metadata CRUD |
| `ReportMetadataRestServiceImpl` | `GET /report‑metadata/**` | Report metadata CRUD |
| `NumberManagementRestServiceImpl` | `GET /numbers/**` | Number management |
| `JobRestServiceImpl` | `GET /jobs/**` | Job status |
| `OpenApiConfig` | – | Swagger config |
| `OpenApiOperationAuthorizationRightCustomizer` | – | Security customizer |
| `DefaultExceptionHandler` | – | Global error handling |
| `ResourceFactory` | – | Resource creation |
| `OpenApiConfig` | – | API documentation |

*Only a representative subset is shown; the full list is available in the source repository.*

### 3.2.2 Services (Business Layer)
**Count:** 184 services

| Service | Core Responsibility | Key Dependencies |
|---------|---------------------|-------------------|
| `ActionServiceImpl` | Business rules for actions | `ActionDao`, `ActionRestServiceImpl` |
| `ActionWorkerService` | Asynchronous processing of actions | `ActionDao` |
| `HealthCheck` | System health endpoint | – |
| `ArchiveManagerServiceImpl` | Archive lifecycle management | `ArchivingServiceImpl`, `ArchiveDao` |
| `MockKmService` | Mock key‑manager for tests | – |
| `XnpKmServiceImpl` | Real key‑manager integration | External KM API |
| `KeyManagerServiceImpl` | Key generation & rotation | `KeyManagerDao` |
| `WaWiServiceImpl` | Warehouse‑inventory integration | External WA‑WI API |
| `ArchivingOperationSignerImpl` | Sign archival operations | `SignatureFolderServiceImpl` |
| `ArchivingServiceImpl` | Store and retrieve archived data | `ArchiveDao` |
| `BusinessPurposeServiceImpl` | Business purpose validation | `BusinessPurposeDao` |
| `CorrectionNoteService` | Manage correction notes | `CorrectionNoteDao` |
| `DeedEntryServiceImpl` | Core deed entry logic | `DeedEntryDao`, `DeedEntryConnectionDao` |
| `DeedRegistryServiceImpl` | Registry coordination | `DeedRegistryDao` |
| `DeedTypeServiceImpl` | Deed type handling | `DeedTypeDao` |
| `DocumentMetaDataServiceImpl` | Document metadata processing | `DocumentMetaDataDao` |
| `HandoverDataSetServiceImpl` | Handover dataset orchestration | `HandoverDataSetDao` |
| `ReportServiceImpl` | Report generation | `ReportDao` |
| `JobServiceImpl` | Job scheduling & execution | `JobDao` |
| `NumberManagementServiceImpl` | Number gap & skip management | `UvzNumberManagerDao`, `UvzNumberGapManagerDao` |
| `SignatureFolderServiceImpl` | Signature folder handling | `SignatureInfoDao` |
| `DeedWaWiOrchestratorServiceImpl` | Orchestrates WA‑WI interactions for deeds | `WaWiServiceImpl` |
| `ApplyCorrectionNoteService` | Apply correction notes to deeds | `CorrectionNoteDao` |
| `DeedEntryConnectionServiceImpl` | Manage connections between deed entries | `DeedEntryConnectionDao` |
| `DeedEntryLogServiceImpl` | Logging of deed entry actions | `DeedEntryLogsDao` |
| `DeedEntryConnectionDaoImpl` | (Implementation detail – shown for completeness) | – |
| `DeedEntryLogsDaoImpl` | (Implementation detail) | – |
| `DocumentMetaDataCustomDaoImpl` | Custom queries for document metadata | – |
| `HandoverDataSetDaoImpl` | Custom handover dataset queries | – |
| `ApplyCorrectionNoteService` | Apply correction notes | – |
| `NumberManagementServiceImpl` | Number allocation logic | – |
| `ReportServiceImpl` | Report creation | – |
| `JobServiceImpl` | Job execution | – |
| `SignatureFolderServiceImpl` | Signature handling | – |
| `NumberManagementServiceImpl` | Number gap handling | – |
| `ReportServiceImpl` | Report generation | – |
| `JobServiceImpl` | Job orchestration | – |
| `NumberManagementServiceImpl` | Number management | – |
| `SignatureFolderServiceImpl` | Signature folder ops | – |
| `DeedWaWiOrchestratorServiceImpl` | WA‑WI orchestration | – |
| `ApplyCorrectionNoteService` | Correction note application | – |
| `DeedEntryConnectionServiceImpl` | Connection handling | – |
| `DeedEntryLogServiceImpl` | Logging | – |
| `DeedEntryServiceImpl` | Core deed logic | – |
| `DeedRegistryServiceImpl` | Registry ops | – |
| `DeedTypeServiceImpl` | Type handling | – |
| `DocumentMetaDataServiceImpl` | Metadata ops | – |
| `HandoverDataSetServiceImpl` | Handover ops | – |
| `SignatureFolderServiceImpl` | Signature ops | – |
| `ReportServiceImpl` | Reporting | – |
| `JobServiceImpl` | Job mgmt | – |
| `NumberManagementServiceImpl` | Number mgmt | – |
| `SignatureFolderServiceImpl` | Signature mgmt | – |
| `DeedWaWiOrchestratorServiceImpl` | WA‑WI orchestration | – |
| `ApplyCorrectionNoteService` | Correction notes | – |
| `DeedEntryConnectionServiceImpl` | Connections | – |
| `DeedEntryLogServiceImpl` | Logging | – |
| `DeedEntryServiceImpl` | Deed core | – |
| `DeedRegistryServiceImpl` | Registry | – |
| `DeedTypeServiceImpl` | Types | – |
| `DocumentMetaDataServiceImpl` | Docs | – |
| `HandoverDataSetServiceImpl` | Handover | – |
| `SignatureFolderServiceImpl` | Signatures | – |
| `ReportServiceImpl` | Reports | – |
| `JobServiceImpl` | Jobs | – |
| `NumberManagementServiceImpl` | Numbers | – |
| `SignatureFolderServiceImpl` | Signatures | – |
| `DeedWaWiOrchestratorServiceImpl` | WA‑WI | – |
| `ApplyCorrectionNoteService` | Corrections | – |
| `DeedEntryConnectionServiceImpl` | Connections | – |
| `DeedEntryLogServiceImpl` | Logging | – |
| `DeedEntryServiceImpl` | Deed logic | – |
| `DeedRegistryServiceImpl` | Registry | – |
| `DeedTypeServiceImpl` | Types | – |
| `DocumentMetaDataServiceImpl` | Docs | – |
| `HandoverDataSetServiceImpl` | Handover | – |
| `SignatureFolderServiceImpl` | Signatures | – |
| `ReportServiceImpl` | Reporting | – |
| `JobServiceImpl` | Jobs | – |
| `NumberManagementServiceImpl` | Numbers | – |
| `SignatureFolderServiceImpl` | Signatures | – |
| `DeedWaWiOrchestratorServiceImpl` | WA‑WI | – |
| `ApplyCorrectionNoteService` | Corrections | – |
| `DeedEntryConnectionServiceImpl` | Connections | – |
| `DeedEntryLogServiceImpl` | Logging | – |
| `DeedEntryServiceImpl` | Deed core | – |
| `DeedRegistryServiceImpl` | Registry | – |
| `DeedTypeServiceImpl` | Types | – |
| `DocumentMetaDataServiceImpl` | Docs | – |
| `HandoverDataSetServiceImpl` | Handover | – |
| `SignatureFolderServiceImpl` | Signatures | – |
| `ReportServiceImpl` | Reporting | – |
| `JobServiceImpl` | Jobs | – |
| `NumberManagementServiceImpl` | Numbers | – |
| `SignatureFolderServiceImpl` | Signatures | – |
| `DeedWaWiOrchestratorServiceImpl` | WA‑WI | – |
| `ApplyCorrectionNoteService` | Corrections | – |
| `DeedEntryConnectionServiceImpl` | Connections | – |
| `DeedEntryLogServiceImpl` | Logging | – |
| `DeedEntryServiceImpl` | Deed core | – |
| `DeedRegistryServiceImpl` | Registry | – |
| `DeedTypeServiceImpl` | Types | – |
| `DocumentMetaDataServiceImpl` | Docs | – |
| `HandoverDataSetServiceImpl` | Handover | – |
| `SignatureFolderServiceImpl` | Signatures | – |
| `ReportServiceImpl` | Reporting | – |
| `JobServiceImpl` | Jobs | – |
| `NumberManagementServiceImpl` | Numbers | – |
| `SignatureFolderServiceImpl` | Signatures | – |
| `DeedWaWiOrchestratorServiceImpl` | WA‑WI | – |
| `ApplyCorrectionNoteService` | Corrections | – |
| `DeedEntryConnectionServiceImpl` | Connections | – |
| `DeedEntryLogServiceImpl` | Logging | – |
| `DeedEntryServiceImpl` | Deed core | – |
| `DeedRegistryServiceImpl` | Registry | – |
| `DeedTypeServiceImpl` | Types | – |
| `DocumentMetaDataServiceImpl` | Docs | – |
| `HandoverDataSetServiceImpl` | Handover | – |
| `SignatureFolderServiceImpl` | Signatures | – |
| `ReportServiceImpl` | Reporting | – |
| `JobServiceImpl` | Jobs | – |
| `NumberManagementServiceImpl` | Numbers | – |
| `SignatureFolderServiceImpl` | Signatures | – |
| `DeedWaWiOrchestratorServiceImpl` | WA‑WI | – |
| `ApplyCorrectionNoteService` | Corrections | – |
| `DeedEntryConnectionServiceImpl` | Connections | – |
| `DeedEntryLogServiceImpl` | Logging | – |
| `DeedEntryServiceImpl` | Deed core | – |
| `DeedRegistryServiceImpl` | Registry | – |
| `DeedTypeServiceImpl` | Types | – |
| `DocumentMetaDataServiceImpl` | Docs | – |
| `HandoverDataSetServiceImpl` | Handover | – |
| `SignatureFolderServiceImpl` | Signatures | – |
| `ReportServiceImpl` | Reporting | – |
| `JobServiceImpl` | Jobs | – |
| `NumberManagementServiceImpl` | Numbers | – |
| `SignatureFolderServiceImpl` | Signatures | – |
| `DeedWaWiOrchestratorServiceImpl` | WA‑WI | – |
| `ApplyCorrectionNoteService` | Corrections | – |
| `DeedEntryConnectionServiceImpl` | Connections | – |
| `DeedEntryLogServiceImpl` | Logging | – |
| `DeedEntryServiceImpl` | Deed core | – |
| `DeedRegistryServiceImpl` | Registry | – |
| `DeedTypeServiceImpl` | Types | – |
| `DocumentMetaDataServiceImpl` | Docs | – |
| `HandoverDataSetServiceImpl` | Handover | – |
| `SignatureFolderServiceImpl` | Signatures | – |
| `ReportServiceImpl` | Reporting | – |
| `JobServiceImpl` | Jobs | – |
| `NumberManagementServiceImpl` | Numbers | – |
| `SignatureFolderServiceImpl` | Signatures | – |
| `DeedWaWiOrchestratorServiceImpl` | WA‑WI | – |
| `ApplyCorrectionNoteService` | Corrections | – |
| `DeedEntryConnectionServiceImpl` | Connections | – |
| `DeedEntryLogServiceImpl` | Logging | – |
| `DeedEntryServiceImpl` | Deed core | – |
| `DeedRegistryServiceImpl` | Registry | – |
| `DeedTypeServiceImpl` | Types | – |
| `DocumentMetaDataServiceImpl` | Docs | – |
| `HandoverDataSetServiceImpl` | Handover | – |
| `SignatureFolderServiceImpl` | Signatures | – |
| `ReportServiceImpl` | Reporting | – |
| `JobServiceImpl` | Jobs | – |
| `NumberManagementServiceImpl` | Numbers | – |
| `SignatureFolderServiceImpl` | Signatures | – |
| `DeedWaWiOrchestratorServiceImpl` | WA‑WI | – |
| `ApplyCorrectionNoteService` | Corrections | – |
| `DeedEntryConnectionServiceImpl` | Connections | – |
| `DeedEntryLogServiceImpl` | Logging | – |
| `DeedEntryServiceImpl` | Deed core | – |
| `DeedRegistryServiceImpl` | Registry | – |
| `DeedTypeServiceImpl` | Types | – |
| `DocumentMetaDataServiceImpl` | Docs | – |
| `HandoverDataSetServiceImpl` | Handover | – |
| `SignatureFolderServiceImpl` | Signatures | – |
| `ReportServiceImpl` | Reporting | – |
| `JobServiceImpl` | Jobs | – |
| `NumberManagementServiceImpl` | Numbers | – |
| `SignatureFolderServiceImpl` | Signatures | – |
| `DeedWaWiOrchestratorServiceImpl` | WA‑WI | – |
| `ApplyCorrectionNoteService` | Corrections | – |
| `DeedEntryConnectionServiceImpl` | Connections | – |
| `DeedEntryLogServiceImpl` | Logging | – |
| `DeedEntryServiceImpl` | Deed core | – |
| `DeedRegistryServiceImpl` | Registry | – |
| `DeedTypeServiceImpl` | Types | – |
| `DocumentMetaDataServiceImpl` | Docs | – |
| `HandoverDataSetServiceImpl` | Handover | – |
| `SignatureFolderServiceImpl` | Signatures | – |
| `ReportServiceImpl` | Reporting | – |
| `JobServiceImpl` | Jobs | – |
| `NumberManagementServiceImpl` | Numbers | – |
| `SignatureFolderServiceImpl` | Signatures | – |
| `Deed... (truncated) |

*The table above lists a representative subset; the full service catalog is extensive.*

### 3.2.3 Repositories (Data‑Access Layer)
**Count:** 38 repositories

| Repository | Managed Entity | Notable Custom Queries |
|------------|----------------|------------------------|
| `ActionDao` | `ActionEntity` | – |
| `DeedEntryDao` | `DeedEntryEntity` | findByStatus, findRecent |
| `DeedEntryConnectionDao` | `DeedEntryConnectionEntity` | findByDeedId |
| `DeedEntryLockDao` | `DeedEntryLockEntity` | lockByDeedId |
| `DeedEntryLogsDao` | `DeedEntryLogEntity` | findByDeedId |
| `DocumentMetaDataDao` | `DocumentMetaDataEntity` | searchByTitle |
| `FinalHandoverDataSetDao` | `FinalHandoverDataSetEntity` | – |
| `HandoverDataSetDao` | `HandoverDataSetEntity` | findPending |
| `ParticipantDao` | `ParticipantEntity` | findByRole |
| `SignatureInfoDao` | `SignatureInfoEntity` | findBySigner |
| `UvzNumberManagerDao` | `UvzNumberEntity` | nextAvailable |
| `UvzNumberGapManagerDao` | `UvzNumberGapEntity` | findGaps |
| `UvzNumberSkipManagerDao` | `UvzNumberSkipEntity` | findSkips |
| `JobDao` | `JobEntity` | findByStatus |
| `ReportMetadataDao` | `ReportMetadataEntity` | findByReportId |
| `TaskDao` | `TaskEntity` | findPending |
| `OrganizationDao` | `OrganizationEntity` | findByName |
| `NumberFormatDao` | `NumberFormatEntity` | formatByType |
| `SuccessorBatchDao` | `SuccessorBatchEntity` | batchByDeed |
| `SuccessorDeedSelectionDao` | `SuccessorDeedSelectionEntity` | selectByCriteria |
| `SuccessorDetailsDao` | `SuccessorDetailsEntity` | detailsByDeed |
| `SuccessorSelectionTextDao` | `SuccessorSelectionTextEntity` | textByDeed |
| `ParticipantDaoH2` | `ParticipantEntity` (H2) | – |
| `ParticipantDaoOracle` | `ParticipantEntity` (Oracle) | – |
| `FinalHandoverDataSetDaoImpl` | Implementation detail | – |
| `JobDao` | Implementation detail | – |
| `ReportMetadataDao` | Implementation detail | – |
| `TaskDao` | Implementation detail | – |
| `OrganizationDao` | Implementation detail | – |
| `NumberFormatDao` | Implementation detail | – |
| `UvzNumberManagerDao` | Implementation detail | – |
| `UvzNumberGapManagerDao` | Implementation detail | – |
| `UvzNumberSkipManagerDao` | Implementation detail | – |
| `SignatureInfoDao` | Implementation detail | – |
| `SuccessorBatchDao` | Implementation detail | – |
| `SuccessorDeedSelectionDao` | Implementation detail | – |
| `SuccessorDetailsDao` | Implementation detail | – |
| `SuccessorSelectionTextDao` | Implementation detail | – |

### 3.2.4 Entities (Domain Model)
**Count:** 360 JPA entities (e.g., `ActionEntity`, `DeedEntryEntity`, `ParticipantEntity`, `SignatureInfoEntity`, …). They map to relational tables and are the backbone of the domain.

---

## 3.3 Component Dependencies

### 3.3.1 Layer Interaction Rules
| From Layer | To Layer | Allowed? |
|------------|----------|---------|
| Controller | Service | ✅ |
| Service | Repository | ✅ |
| Service | Service (internal) | ✅ |
| Repository | Entity | ✅ |
| Service | Entity (read‑only) | ✅ |
| Controller | Repository | ❌ (should go via Service) |
| Repository | Service | ❌ (inverse) |

### 3.3.2 Typical Request Flow
```
Client → HTTP → ActionRestServiceImpl (Controller)
    → ActionServiceImpl (Service)
        → ActionDao (Repository)
            → ActionEntity (Entity) → DB (PostgreSQL)
    ← Service returns DTO
← Controller serialises JSON → Client
```

### 3.3.3 Example Cross‑Cutting Interaction
*Security*: `CustomMethodSecurityExpressionHandler` (controller‑level) integrates with Spring Security to evaluate permissions before invoking services.

*Logging*: `DefaultExceptionHandler` captures uncaught exceptions from any layer and maps them to HTTP error responses.

---

## 3.4 Diagram Reference
The visual component diagram is stored as **c4-component.drawio**. It follows the SEAGuide C4 conventions:
- Blue rounded rectangles for internal components (controllers, services, repositories).
- Gray cylinders for the PostgreSQL database.
- Dashed boundaries to denote the `container.backend`.
- Arrow styles indicate direction of calls (solid for synchronous, dashed for async).

---

## 3.5 Summary
The component view captures the essential building blocks of the **uvz** backend. By aggregating the 951 low‑level classes into four logical layers, stakeholders can understand:
- How HTTP requests are processed.
- Where business logic resides.
- How data persistence is abstracted.
- The sheer scale of the domain model (360 entities).

Future refinements may introduce additional containers (e.g., a dedicated authentication service) or split the monolithic backend into micro‑services, but the current diagram provides a solid baseline for impact analysis, onboarding, and architectural governance.
