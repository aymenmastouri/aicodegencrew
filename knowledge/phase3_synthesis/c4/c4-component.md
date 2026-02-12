# C4 Level 3: Component Diagram

## 3.1 Overview

- **System**: `uvz`
- **Primary Containers**:
  - `container.backend` – Spring Boot backend (REST API, business logic)
  - `container.frontend` – Angular SPA (not detailed in this component view)
  - `container.js_api` – Node.js API (auxiliary, omitted here)
  - `container.e2e_xnp` – Playwright end‑to‑end test harness (outside scope)
  - `container.import_schema` – Java/Gradle library (outside scope)
- **Technology Stack**: Spring Boot, Java, JPA/Hibernate, REST, Angular, Node.js, Playwright
- **Total Components**: **951** (across all containers)
- **Component Breakdown (Backend container)**:
  - Controllers: **32**
  - Services: **184**
  - Repositories: **38**
  - Entities: **360**
  - Other (adapters, directives, guards, interceptors, modules, pipes, etc.): remaining components

---

## 3.2 Backend API Components

### 3.2.1 Layer Overview

| Layer          | Purpose                              | Component Count | Typical Pattern / Technology |
|----------------|--------------------------------------|-----------------|------------------------------|
| Controllers    | HTTP request handling, routing      | **32**          | Spring `@RestController`     |
| Services       | Business logic, orchestration        | **184**         | Spring `@Service`            |
| Repositories   | Data‑access, persistence abstraction | **38**          | Spring Data JPA, `@Repository` |
| Entities       | Domain model, JPA mappings           | **360**         | JPA `@Entity`                |

---

### 3.2.2 Controllers (Presentation Layer)

**Total Controllers:** 32 (30 listed below – the remaining two are internal health‑check endpoints).

| Controller | Primary Endpoint(s) | Responsibility |
|------------|--------------------|----------------|
| ActionRestServiceImpl | `/api/actions/**` | CRUD operations for actions |
| IndexHTMLResourceService | `/` | Serves the SPA entry point |
| StaticContentController | `/static/**` | Serves static assets |
| CustomMethodSecurityExpressionHandler | – | Custom security expressions |
| JsonAuthorizationRestServiceImpl | `/api/auth/**` | JSON‑based auth handling |
| ProxyRestTemplateConfiguration | – | Configures outbound HTTP proxy |
| TokenAuthenticationRestTemplateConfigurationSpringBoot | – | Token‑based RestTemplate config |
| KeyManagerRestServiceImpl | `/api/keys/**` | Key management API |
| ArchivingRestServiceImpl | `/api/archive/**` | Archive related operations |
| BusinessPurposeRestServiceImpl | `/api/business‑purpose/**` | Business purpose CRUD |
| DeedEntryConnectionRestServiceImpl | `/api/deed‑connection/**` | Deed connection handling |
| DeedEntryLogRestServiceImpl | `/api/deed‑log/**` | Deed log CRUD |
| DeedEntryRestServiceImpl | `/api/deed/**` | Deed CRUD |
| DeedRegistryRestServiceImpl | `/api/registry/**` | Registry operations |
| DeedTypeRestServiceImpl | `/api/deed‑type/**` | Deed type CRUD |
| DocumentMetaDataRestServiceImpl | `/api/document‑metadata/**` | Document metadata CRUD |
| HandoverDataSetRestServiceImpl | `/api/handover‑dataset/**` | Handover data set handling |
| ReportRestServiceImpl | `/api/report/**` | Reporting API |
| OpenApiConfig | – | OpenAPI/Swagger configuration |
| OpenApiOperationAuthorizationRightCustomizer | – | Swagger operation security customizer |
| ResourceFactory | – | Factory for REST resources |
| DefaultExceptionHandler | – | Global exception handling |
| JobRestServiceImpl | `/api/job/**` | Job management |
| ReencryptionJobRestServiceImpl | `/api/reencryption‑job/**` | Re‑encryption job handling |
| NotaryRepresentationRestServiceImpl | `/api/notary‑representation/**` | Notary representation API |
| NumberManagementRestServiceImpl | `/api/number‑management/**` | Number management CRUD |
| OfficialActivityMetadataRestServiceImpl | `/api/official‑activity/**` | Official activity metadata |
| ReportMetadataRestServiceImpl | `/api/report‑metadata/**` | Report metadata CRUD |

---

### 3.2.3 Services (Business Layer)

**Total Services:** 184 (30 representative entries shown).

| Service | Core Responsibility | Key Dependencies |
|---------|---------------------|-------------------|
| ActionServiceImpl | Business rules for actions | ActionDao, ActionRestServiceImpl |
| ActionWorkerService | Asynchronous processing of actions | ActionServiceImpl |
| HealthCheck | Liveness / readiness probes | – |
| ArchiveManagerServiceImpl | Coordination of archiving workflow | ArchivingServiceImpl, ArchiveDao |
| MockKmService | Mock key‑manager for tests | – |
| XnpKmServiceImpl | Real key‑manager integration | KeyManagerDao |
| KeyManagerServiceImpl | Key lifecycle management | KeyManagerDao |
| WaWiServiceImpl | WA‑WI specific business logic | WaWiDao |
| ArchivingOperationSignerImpl | Digital signing of archive ops | SignatureInfoDao |
| ArchivingServiceImpl | Core archiving operations | ArchivingDao |
| DeedEntryConnectionServiceImpl | Manage connections between deeds | DeedEntryConnectionDao |
| DeedEntryLogServiceImpl | Log handling for deed entries | DeedEntryLogDao |
| DeedEntryServiceImpl | Deed CRUD and validation | DeedEntryDao |
| DeedRegistryServiceImpl | Registry specific logic | DeedRegistryLockDao |
| DeedTypeServiceImpl | Deed type handling | DeedTypeDao |
| DeedWaWiOrchestratorServiceImpl | Orchestrates WA‑WI processes | DeedWaWiServiceImpl |
| DeedWaWiServiceImpl | WA‑WI specific deed processing | DeedWaWiDao |
| DocumentMetaDataServiceImpl | Document metadata business rules | DocumentMetaDataDao |
| HandoverDataSetServiceImpl | Handover dataset orchestration | HandoverDataSetDao |
| SignatureFolderServiceImpl | Signature folder management | SignatureInfoDao |
| ReportServiceImpl | Report generation logic | ReportMetadataDao |
| JobServiceImpl | Job scheduling and execution | JobDao |
| NumberManagementServiceImpl | Number allocation & gap handling | UzvNumberManagerDao, UzvNumberGapManagerDao |
| ApplyCorrectionNoteService | Apply correction notes to deeds | CorrectionNoteDao |
| BusinessPurposeServiceImpl | Business purpose validation | BusinessPurposeDao |
| CorrectionNoteService | CRUD for correction notes | CorrectionNoteDao |
| DeedEntryConnectionDaoImpl | Data‑access for deed connections | – |
| DeedEntryLogsDaoImpl | Data‑access for deed logs | – |
| DocumentMetaDataCustomDaoImpl | Custom queries for document metadata | – |
| HandoverDataSetDaoImpl | Data‑access for handover datasets | – |

---

### 3.2.4 Repositories (Data‑Access Layer)

**Total Repositories:** 38 (30 listed).

| Repository | Managed Entity | Notable Custom Queries |
|------------|----------------|------------------------|
| ActionDao | ActionEntity | findByStatus, findRecent |
| DeedEntryConnectionDao | DeedEntryConnectionEntity | findByDeedId |
| DeedEntryDao | DeedEntryEntity | findActive, findByNumber |
| DeedEntryLockDao | DeedEntryLockEntity | lockById |
| DeedEntryLogsDao | DeedEntryLogEntity | recentLogs |
| DeedRegistryLockDao | DeedRegistryLockEntity | lockRegistry |
| DocumentMetaDataDao | DocumentMetaDataEntity | findByDocumentId |
| FinalHandoverDataSetDao | FinalHandoverDataSetEntity | findCompleted |
| FinalHandoverDataSetDaoCustom | FinalHandoverDataSetEntity | complexAggregation |
| HandoverDataSetDao | HandoverDataSetEntity | findPending |
| HandoverHistoryDao | HandoverHistoryEntity | historyByDeed |
| HandoverHistoryDeedDao | HandoverHistoryDeedEntity | findByHistoryId |
| ParticipantDao | ParticipantEntity | findActiveParticipants |
| SignatureInfoDao | SignatureInfoEntity | findBySignatureId |
| SuccessorBatchDao | SuccessorBatchEntity | batchByDate |
| SuccessorDeedSelectionDao | SuccessorDeedSelectionEntity | selectionByCriteria |
| SuccessorDeedSelectionMetaDao | SuccessorDeedSelectionMetaEntity | metaBySelectionId |
| SuccessorDetailsDao | SuccessorDetailsEntity | detailsByBatch |
| SuccessorSelectionTextDao | SuccessorSelectionTextEntity | textBySelection |
| UzvNumberGapManagerDao | UzvNumberGapManagerEntity | gapsBySeries |
| UzvNumberManagerDao | UzvNumberManagerEntity | nextNumber |
| UzvNumberSkipManagerDao | UzvNumberSkipManagerEntity | skipsBySeries |
| ParticipantDaoH2 | ParticipantEntity | H2‑specific queries |
| ParticipantDaoOracle | ParticipantEntity | Oracle‑specific queries |
| JobDao | JobEntity | findPendingJobs |
| NumberFormatDao | – | formatByLocale |
| OrganizationDao | – | findByName |
| ReportMetadataDao | – | findByReportId |
| TaskDao | – | tasksByOwner |
| ActionDaoImpl | ActionEntity | – |
| DeedEntryConnectionDaoImpl | DeedEntryConnectionEntity | – |
| DeedEntryDaoImpl | DeedEntryEntity | – |
| DeedEntryLockDaoImpl | DeedEntryLockEntity | – |
| DeedEntryLogsDaoImpl | DeedEntryLogEntity | – |
| DeedRegistryLockDaoImpl | DeedRegistryLockEntity | – |
| DocumentMetaDataDaoImpl | DocumentMetaDataEntity | – |
| FinalHandoverDataSetDaoImpl | FinalHandoverDataSetEntity | – |
| HandoverDataSetDaoImpl | HandoverDataSetEntity | – |
| JobDaoImpl | JobEntity | – |

---

### 3.2.5 Entities (Domain Model)

**Total Entities:** 360 (30 representative examples shown).

| Entity | Corresponding Table | Key Relationships |
|--------|---------------------|--------------------|
| ActionEntity | `action` | Many‑to‑One `User`, One‑to‑Many `ActionLog` |
| ActionStreamEntity | `action_stream` | Linked to `ActionEntity` |
| ChangeEntity | `change` | References `DeedEntryEntity` |
| ConnectionEntity | `connection` | Connects `DeedEntryEntity` ↔ `DeedEntryEntity` |
| CorrectionNoteEntity | `correction_note` | Belongs to `DeedEntryEntity` |
| DeedCreatorHandoverInfoEntity | `deed_creator_handover_info` | One‑to‑One `DeedEntryEntity` |
| DeedEntryEntity | `deed_entry` | Core domain object, links to many other entities |
| DeedEntryLockEntity | `deed_entry_lock` | One‑to‑One `DeedEntryEntity` |
| DeedEntryLogEntity | `deed_entry_log` | Many‑to‑One `DeedEntryEntity` |
| DeedRegistryLockEntity | `deed_registry_lock` | One‑to‑One `DeedRegistryEntity` |
| DocumentMetaDataEntity | `document_metadata` | One‑to‑Many `SignatureInfoEntity` |
| FinalHandoverDataSetEntity | `final_handover_dataset` | Aggregates `HandoverDataSetEntity` |
| HandoverDataSetEntity | `handover_dataset` | Belongs to `DeedEntryEntity` |
| HandoverDmdWorkEntity | `handover_dmd_work` | Works with `HandoverDataSetEntity` |
| HandoverHistoryDeedEntity | `handover_history_deed` | Part of `HandoverHistoryEntity` |
| HandoverHistoryEntity | `handover_history` | Groups multiple `HandoverHistoryDeedEntity` |
| IssuingCopyNoteEntity | `issuing_copy_note` | References `DeedEntryEntity` |
| ParticipantEntity | `participant` | Many‑to‑Many `DeedEntryEntity` via join table |
| RegistrationEntity | `registration` | One‑to‑One `DeedEntryEntity` |
| RemarkEntity | `remark` | Linked to `DeedEntryEntity` |
| SignatureInfoEntity | `signature_info` | Belongs to `DocumentMetaDataEntity` |
| SuccessorBatchEntity | `successor_batch` | Groups `SuccessorDetailsEntity` |
| SuccessorDeedSelectionEntity | `successor_deed_selection` | References `DeedEntryEntity` |
| SuccessorDeedSelectionMetaEntity | `successor_deed_selection_meta` | Meta data for selection |
| SuccessorDetailsEntity | `successor_details` | Detail lines for a batch |
| SuccessorSelectionTextEntity | `successor_selection_text` | Textual description of selection |
| UzvNumberGapManagerEntity | `uvz_number_gap_manager` | Manages gaps in number series |
| UzvNumberManagerEntity | `uvz_number_manager` | Generates next numbers |
| UzvNumberSkipManagerEntity | `uvz_number_skip_manager` | Handles skipped numbers |
| JobEntity | `job` | Scheduler job definition |
| ... (additional 330 entities omitted for brevity) |

---

## 3.3 Component Dependencies

### 3.3.1 Layer Interaction Rules

| From Layer | To Layer | Allowed? |
|------------|----------|----------|
| Controllers | Services | ✅ |
| Services | Repositories | ✅ |
| Services | Other Services | ✅ (internal calls) |
| Repositories | Entities | ✅ |
| Controllers | Repositories | ❌ (should go via Services) |
| Controllers | Entities | ❌ (should not access directly) |

### 3.3.2 Typical Request Flow

```
HTTP Request → Controller (e.g., ActionRestServiceImpl)
    → Service (ActionServiceImpl)
        → Repository (ActionDao)
            → Entity (ActionEntity) ↔ Database
    ← Service returns DTO
← Controller serialises response → HTTP Response
```

---

## 3.4 Component Diagram

The full C4 Level‑3 component diagram is stored in the accompanying Draw.io file:

- **File:** `c4-component.drawio`
- **Diagram Name:** *C4 Component – uvz Backend*

The diagram follows the SEAGuide C4 visual conventions (blue boxes for internal components, gray for external systems, cylinders for databases, person icons for users, dashed lines for boundaries).

---

*Document generated automatically from architecture facts.*