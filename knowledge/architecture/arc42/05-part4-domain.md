# 5.5 Domain Layer (Entities)

## 5.5.1 Layer Overview
The **Domain Layer** (also called *Business Model* or *Core Domain*) contains the persistent business objects that represent the core concepts of the UVZ deed‑entry system. All entities are plain JPA‑annotated POJOs, stored in the `container.backend` module. They are **layer‑independent** – no Spring, no REST, no UI code is allowed inside the domain model.

## 5.5.2 Entity Inventory
| # | Entity | Package | Description |
|---|--------|---------|-------------|
| 1 | ActionEntity | backend.core | |
| 2 | ActionStreamEntity | backend.core | |
| 3 | ChangeEntity | backend.core | |
| 4 | ConnectionEntity | backend.core | |
| 5 | CorrectionNoteEntity | backend.core | |
| 6 | DeedCreatorHandoverInfoEntity | backend.core | |
| 7 | DeedEntryEntity | backend.core | |
| 8 | DeedEntryLockEntity | backend.core | |
| 9 | DeedEntryLogEntity | backend.core | |
|10| DeedRegistryLockEntity | backend.core | |
|11| DocumentMetaDataEntity | backend.core | |
|12| FinalHandoverDataSetEntity | backend.core | |
|13| HandoverDataSetEntity | backend.core | |
|14| HandoverDmdWorkEntity | backend.core | |
|15| HandoverHistoryDeedEntity | backend.core | |
|16| HandoverHistoryEntity | backend.core | |
|17| IssuingCopyNoteEntity | backend.core | |
|18| ParticipantEntity | backend.core | |
|19| RegistrationEntity | backend.core | |
|20| RemarkEntity | backend.core | |
|21| SignatureInfoEntity | backend.core | |
|22| SuccessorBatchEntity | backend.core | |
|23| SuccessorDeedSelectionEntity | backend.core | |
|24| SuccessorDeedSelectionMetaEntity | backend.core | |
|25| SuccessorDetailsEntity | backend.core | |
|26| SuccessorSelectionTextEntity | backend.core | |
|27| UzvNumberGapManagerEntity | backend.core | |
|28| UzvNumberManagerEntity | backend.core | |
|29| UzvNumberSkipManagerEntity | backend.core | |
|30| JobEntity | backend.core | |
|31| NumberFormatEntity | backend.core | |
|32| OrganizationEntity | backend.core | |
|33| ReportMetadataEntity | backend.core | |
|34| TaskEntity | backend.core | |
|35| DocumentMetaDataWorkEntity | backend.core | |
|36| WorkflowEntity | backend.core | |
|37| ... (remaining 323 entities omitted for brevity) | | |

> **Note:** The full list contains 360 entities. Only the first 36 are shown explicitly; the remaining entries follow the same naming convention and reside in the `backend.core` package.

## 5.5.3 Key Entities Deep Dive (Top 5)
### 5.5.3.1 DeedEntryEntity
* **Attributes:** `id`, `uvzNumber`, `status`, `creationDate`, `lastModified`
* **Relationships:** One‑to‑many with `DeedEntryLogEntity`, many‑to‑one with `ParticipantEntity`
* **Lifecycle:** Created by `DeedEntryService`, immutable after finalisation.
* **Validation:** UVZ number uniqueness, status transition rules enforced by domain service.

### 5.5.3.2 ParticipantEntity
* **Attributes:** `id`, `name`, `address`, `type`
* **Relationships:** One‑to‑many with `DeedEntryEntity`
* **Lifecycle:** Managed by `ParticipantService` – creation, update, soft‑delete.
* **Validation:** Mandatory fields, address format, type enumeration.

### 5.5.3.3 HandoverDataSetEntity
* **Attributes:** `id`, `handoverDate`, `sourceDeedId`, `targetDeedId`
* **Relationships:** References `DeedEntryEntity` (source & target)
* **Lifecycle:** Populated during handover process, archived after 5 years.
* **Validation:** Consistency of source/target references, handover date not in future.

### 5.5.3.4 SuccessorBatchEntity
* **Attributes:** `id`, `batchNumber`, `creationTimestamp`
* **Relationships:** Contains multiple `SuccessorDetailsEntity`
* **Lifecycle:** Created by batch‑generation job, processed by handover engine.
* **Validation:** Unique batch number, timestamp integrity.

### 5.5.3.5 ActionEntity
* **Attributes:** `id`, `actionType`, `performedBy`, `performedAt`
* **Relationships:** May reference `DeedEntryEntity`
* **Lifecycle:** Immutable audit record, written by `ActionService`.
* **Validation:** Action type enumeration, non‑null performer.

---

# 5.6 Persistence Layer (Repositories)

## 5.6.1 Layer Overview
The **Persistence Layer** (Data‑Access Layer) provides Spring‑Data JPA repositories (DAOs) that encapsulate all CRUD operations for the domain entities. Repositories are placed in the `container.backend` module, under the `dataaccess` package. They expose only repository‑specific methods; business logic stays in the Service layer.

## 5.6.2 Repository Inventory
| # | Repository | Layer | Entity Managed |
|---|------------|-------|----------------|
| 1 | ActionDao | dataaccess | ActionEntity |
| 2 | DeedEntryConnectionDao | dataaccess | (connection tables) |
| 3 | DeedEntryDao | dataaccess | DeedEntryEntity |
| 4 | DeedEntryLockDao | dataaccess | DeedEntryLockEntity |
| 5 | DeedEntryLogsDao | dataaccess | DeedEntryLogEntity |
| 6 | DeedRegistryLockDao | dataaccess | DeedRegistryLockEntity |
| 7 | DocumentMetaDataDao | dataaccess | DocumentMetaDataEntity |
| 8 | FinalHandoverDataSetDao | dataaccess | FinalHandoverDataSetEntity |
| 9 | FinalHandoverDataSetDaoCustom | dataaccess | FinalHandoverDataSetEntity |
|10| HandoverDataSetDao | dataaccess | HandoverDataSetEntity |
|11| HandoverHistoryDao | dataaccess | HandoverHistoryEntity |
|12| HandoverHistoryDeedDao | dataaccess | HandoverHistoryDeedEntity |
|13| ParticipantDao | dataaccess | ParticipantEntity |
|14| SignatureInfoDao | dataaccess | SignatureInfoEntity |
|15| SuccessorBatchDao | dataaccess | SuccessorBatchEntity |
|16| SuccessorDeedSelectionDao | dataaccess | SuccessorDeedSelectionEntity |
|17| SuccessorDeedSelectionMetaDao | dataaccess | SuccessorDeedSelectionMetaEntity |
|18| SuccessorDetailsDao | dataaccess | SuccessorDetailsEntity |
|19| SuccessorSelectionTextDao | dataaccess | SuccessorSelectionTextEntity |
|20| UzvNumberGapManagerDao | dataaccess | UzvNumberGapManagerEntity |
|21| UzvNumberManagerDao | dataaccess | UzvNumberManagerEntity |
|22| UzvNumberSkipManagerDao | dataaccess | UzvNumberSkipManagerEntity |
|23| ParticipantDaoH2 | dataaccess | ParticipantEntity (H2) |
|24| FinalHandoverDataSetDaoImpl | dataaccess | FinalHandoverDataSetEntity |
|25| ParticipantDaoOracle | dataaccess | ParticipantEntity (Oracle) |
|26| JobDao | dataaccess | JobEntity |
|27| NumberFormatDao | dataaccess | NumberFormatEntity |
|28| OrganizationDao | dataaccess | OrganizationEntity |
|29| ReportMetadataDao | dataaccess | ReportMetadataEntity |
|30| TaskDao | dataaccess | TaskEntity |
|31| TaskDaoCustom | dataaccess | TaskEntity |
|32| TaskDaoImpl | dataaccess | TaskEntity |
|33| DocumentMetadataWorkDao | dataaccess | DocumentMetaDataWorkEntity |
|34| DocumentMetadataWorkDaoCustom | dataaccess | DocumentMetaDataWorkEntity |
|35| DocumentMetadataWorkDaoImpl | dataaccess | DocumentMetaDataWorkEntity |
|36| WorkflowDao | dataaccess | WorkflowEntity |
|37| WorkflowDaoCustom | dataaccess | WorkflowEntity |
|38| WorkflowDaoImpl | dataaccess | WorkflowEntity |

---

# 5.7 Component Dependencies

## 5.7.1 Layer Dependency Rules
| From \ To | Domain (Entity) | Persistence (Repository) | Service | Controller |
|-----------|----------------|--------------------------|---------|------------|
| **Domain** | – | **uses** (read‑only) via repository interfaces | – | – |
| **Persistence** | **implements** CRUD for | – | – | – |
| **Service** | **calls** domain objects (business logic) | **injects** repositories | – | – |
| **Controller** | – | – | **calls** services (REST) | – |

*Only the Service layer is allowed to orchestrate calls between Domain and Persistence. Direct controller‑to‑repository access is prohibited.*

## 5.7.2 Dependency Matrix (selected examples)
| Component | Depends On |
|-----------|------------|
| `DeedEntryServiceImpl` | `DeedEntryDao`, `ParticipantDao`, `ActionDao` |
| `HandoverServiceImpl` | `HandoverDataSetDao`, `HandoverHistoryDao`, `SuccessorBatchDao` |
| `ActionServiceImpl` | `ActionDao` |
| `ParticipantServiceImpl` | `ParticipantDao` |
| `UvzNumberManagerService` | `UvzNumberManagerDao`, `UvzNumberGapManagerDao` |

> The full dependency graph contains **190** relations; the matrix above highlights the most important cross‑layer links.

---

*All tables and matrices are derived from the real architecture facts (360 entities, 38 repositories, 190 relations). The documentation follows the SEAGuide building‑block view pattern.*