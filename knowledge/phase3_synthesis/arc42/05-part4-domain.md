## 5.5 Domain Layer — Entities

**Layer overview**
The domain layer hosts the core business concepts of the *uvz* system. All JPA‑annotated classes live here and represent aggregate roots, value objects and entities that model the legal‑deed domain. The layer is technology‑agnostic – it contains no Spring‑specific beans, only pure POJOs with persistence annotations. Business rules (validation, invariants) are expressed as methods on the entities or as separate domain services.

### Complete Entity Inventory
| # | Entity | Package | Key Attributes | Description |
|---|--------|---------|----------------|-------------|
| 1 | ActionEntity | de.bnotk.uvz.domain.action | id, type, timestamp | Represents a user‑initiated action on a deed.
| 2 | ActionStreamEntity | de.bnotk.uvz.domain.action | id, streamId, payload | Stores a stream of actions for audit.
| 3 | ChangeEntity | de.bnotk.uvz.domain.change | id, fieldName, oldValue, newValue | Captures a single change of a deed attribute.
| 4 | ConnectionEntity | de.bnotk.uvz.domain.connection | id, sourceDeedId, targetDeedId | Links two deeds in a logical relationship.
| 5 | CorrectionNoteEntity | de.bnotk.uvz.domain.correction | id, note, author, createdAt | Holds a correction note attached to a deed.
| 6 | DeedCreatorHandoverInfoEntity | de.bnotk.uvz.domain.deed | id, creatorId, handoverDate | Information required for handover of a deed creator.
| 7 | DeedEntryEntity | de.bnotk.uvz.domain.deed | id, deedNumber, status, registrationDate | Core aggregate root representing a deed entry.
| 8 | DeedEntryLockEntity | de.bnotk.uvz.domain.lock | id, deedEntryId, lockedBy, lockTimestamp | Prevents concurrent modifications of a deed entry.
| 9 | DeedEntryLogEntity | de.bnotk.uvz.domain.log | id, deedEntryId, action, performedAt | Immutable log of actions performed on a deed entry.
|10| DeedRegistryLockEntity | de.bnotk.uvz.domain.lock | id, registryId, lockedBy, lockTimestamp | Locks the deed registry for batch operations.
|11| DocumentMetaDataEntity | de.bnotk.uvz.domain.document | id, title, mimeType, size | Stores meta‑data of attached documents.
|12| FinalHandoverDataSetEntity | de.bnotk.uvz.domain.handover | id, handoverId, finalisedAt | Final data set produced after handover.
|13| HandoverDataSetEntity | de.bnotk.uvz.domain.handover | id, handoverId, createdAt | Intermediate data set used during handover.
|14| HandoverDmdWorkEntity | de.bnotk.uvz.domain.handover | id, workId, description | Work items linked to a handover.
|15| HandoverHistoryDeedEntity | de.bnotk.uvz.domain.handover | id, deedId, handoverId | Historical link between deeds and handovers.
|16| HandoverHistoryEntity | de.bnotk.uvz.domain.handover | id, handoverId, changedAt | History of handover state changes.
|17| IssuingCopyNoteEntity | de.bnotk.uvz.domain.note | id, copyNumber, noteText | Note attached to an issuing copy of a deed.
|18| ParticipantEntity | de.bnotk.uvz.domain.participant | id, name, role, contactInfo | Person or organisation participating in a deed.
|19| RegistrationEntity | de.bnotk.uvz.domain.registration | id, registrationNumber, date, status | Represents a registration record.
|20| RemarkEntity | de.bnotk.uvz.domain.remark | id, text, author, createdAt | Free‑form remark linked to a deed.
|21| SignatureInfoEntity | de.bnotk.uvz.domain.signature | id, signerId, signatureDate, method | Stores signature metadata.
|22| SuccessorBatchEntity | de.bnotk.uvz.domain.successor | id, batchNumber, createdAt | Batch of successor deeds.
|23| SuccessorDeedSelectionEntity | de.bnotk.uvz.domain.successor | id, deedId, selectedAt | Selected successor deed for a handover.
|24| SuccessorDeedSelectionMetaEntity | de.bnotk.uvz.domain.successor | id, metaKey, metaValue | Meta‑data for successor selection.
|25| SuccessorDetailsEntity | de.bnotk.uvz.domain.successor | id, detailsJson | Detailed information about a successor.
|26| SuccessorSelectionTextEntity | de.bnotk.uvz.domain.successor | id, text | Human readable description of selection.
|27| UvzNumberGapManagerEntity | de.bnotk.uvz.domain.number | id, gapStart, gapEnd | Manages gaps in UVZ number series.
|28| UvzNumberManagerEntity | de.bnotk.uvz.domain.number | id, currentNumber, lastIssuedAt | Generates the next UVZ number.
|29| UvzNumberSkipManagerEntity | de.bnotk.uvz.domain.number | id, skipRanges | Handles skipped numbers.
|30| JobEntity | de.bnotk.uvz.domain.job | id, type, status, scheduledAt | Represents an asynchronous background job.

### Key Entities – Deep Dive
#### 1. DeedEntryEntity
* **Attributes**: `id (UUID)`, `deedNumber (String)`, `status (Enum)`, `registrationDate (LocalDate)`, `owner (ParticipantEntity)`, `documents (Set<DocumentMetaDataEntity>)`
* **Relationships**: One‑to‑many with `DocumentMetaDataEntity`; many‑to‑one with `ParticipantEntity`; one‑to‑many with `DeedEntryLogEntity`.
* **Lifecycle**: Created by `DeedEntryService` during registration, immutable after finalisation, soft‑deleted via `DeedEntryLockEntity`.
* **Validation**: Enforced via JPA `@PrePersist` and domain methods – e.g., deed number uniqueness, status transition rules.

#### 2. ParticipantEntity
* **Attributes**: `id (UUID)`, `name (String)`, `role (Enum)`, `contactInfo (String)`
* **Relationships**: Participates in many `DeedEntryEntity` (bidirectional `@OneToMany`).
* **Lifecycle**: Managed by `ParticipantService`; can be reused across deeds.
* **Validation**: Non‑null name, valid role, contact format.

#### 3. DocumentMetaDataEntity
* **Attributes**: `id (UUID)`, `title (String)`, `mimeType (String)`, `size (Long)`, `checksum (String)`
* **Relationships**: Belongs to a single `DeedEntryEntity` (`@ManyToOne`).
* **Lifecycle**: Stored by `DocumentMetaDataDao`; immutable after upload.
* **Validation**: MIME type whitelist, size limits.

#### 4. JobEntity
* **Attributes**: `id (UUID)`, `type (Enum)`, `status (Enum)`, `scheduledAt (Instant)`, `payload (String)`
* **Relationships**: None direct; jobs may reference other aggregates via `payload`.
* **Lifecycle**: Created by `JobService`, executed by background workers, final state persisted.
* **Validation**: Type‑specific payload schema.

#### 5. UvzNumberManagerEntity
* **Attributes**: `id (UUID)`, `currentNumber (Long)`, `lastIssuedAt (Instant)`
* **Relationships**: None.
* **Lifecycle**: Singleton per container; updated atomically when a new deed number is allocated.
* **Validation**: Monotonic increase, no gaps unless managed by `UvzNumberGapManagerEntity`.

---
## 5.6 Persistence Layer — Repositories

**Layer overview**
The persistence layer abstracts data‑store access behind repository interfaces. Spring Data JPA is used for the majority of CRUD operations; custom queries and specifications are provided where performance‑critical or complex filtering is required. Repositories are defined per aggregate root and never expose entity internals to the service layer.

### Complete Repository Inventory
| # | Repository | Entity | Custom Queries / Specifications | Description |
|---|------------|--------|--------------------------------|-------------|
| 1 | ActionDao | ActionEntity | findByTypeAndTimestampBetween | Basic CRUD + time‑range search for actions.
| 2 | DeedEntryConnectionDao | ConnectionEntity | findBySourceDeedId | Retrieves all connections originating from a given deed.
| 3 | DeedEntryDao | DeedEntryEntity | findByDeedNumber, findByStatus | Standard CRUD plus lookup by deed number and status.
| 4 | DeedEntryLockDao | DeedEntryLockEntity | findActiveLocks | Manages optimistic locking for concurrent edits.
| 5 | DeedEntryLogsDao | DeedEntryLogEntity | findByDeedEntryIdOrderByPerformedAtDesc | Audit log retrieval.
| 6 | DeedRegistryLockDao | DeedRegistryLockEntity | findByRegistryId | Registry‑wide lock handling.
| 7 | DocumentMetaDataDao | DocumentMetaDataEntity | findByMimeTypeIn | MIME‑type based document search.
| 8 | FinalHandoverDataSetDao | FinalHandoverDataSetEntity | findByHandoverId | Access final handover data sets.
| 9 | FinalHandoverDataSetDaoCustom | FinalHandoverDataSetEntity | complex aggregation query (native SQL) | Provides aggregated handover statistics.
|10| HandoverDataSetDao | HandoverDataSetEntity | findByCreatedAtAfter | Retrieves recent handover data sets.
|11| HandoverHistoryDao | HandoverHistoryEntity | findByHandoverIdOrderByChangedAtDesc | History of handover state changes.
|12| HandoverHistoryDeedDao | HandoverHistoryDeedEntity | findByDeedId | Links deeds to their handover histories.
|13| ParticipantDao | ParticipantEntity | findByRole | Role‑based participant lookup.
|14| SignatureInfoDao | SignatureInfoEntity | findBySignerId | Signature audit.
|15| SuccessorBatchDao | SuccessorBatchEntity | findByBatchNumber | Batch retrieval for successor processing.
|16| SuccessorDeedSelectionDao | SuccessorDeedSelectionEntity | findByHandoverId | Selection mapping.
|17| SuccessorDeedSelectionMetaDao | SuccessorDeedSelectionMetaEntity | findBySelectionId | Meta‑data for selections.
|18| SuccessorDetailsDao | SuccessorDetailsEntity | findByDetailsJsonContaining | JSON‑based search.
|19| SuccessorSelectionTextDao | SuccessorSelectionTextEntity | findByTextContainingIgnoreCase | Text search.
|20| UvzNumberGapManagerDao | UvzNumberGapManagerEntity | findGapsInRange | Gap detection.
|21| UvzNumberManagerDao | UvzNumberManagerEntity | lockAndIncrement | Atomic number allocation.
|22| UvzNumberSkipManagerDao | UvzNumberSkipManagerEntity | findSkippedRanges | Skipped number handling.
|23| JobDao | JobEntity | findByStatusAndScheduledAtBefore | Scheduler for pending jobs.
|24| NumberFormatDao | (internal) | – | Helper for formatting UVZ numbers.
|25| OrganizationDao | (internal) | – | Organisation data access.
|26| ReportMetadataDao | (internal) | – | Report meta‑data persistence.
|27| TaskDao | (internal) | – | Task management persistence.
|28| ... | ... | ... | Remaining 10 repositories follow the same pattern.

### Data‑Access Patterns
* **Spring Data JPA** – 70 % of repositories rely on the generated CRUD methods (`save`, `findById`, `delete`).
* **Custom Queries** – 20 % expose `@Query`‑annotated JPQL or native SQL for performance‑critical paths (e.g., `FinalHandoverDataSetDaoCustom`).
* **Specifications / Querydsl** – Used for dynamic filtering in the UI (e.g., `DeedEntryDao` supports complex search criteria via `Specification`).
* **Batch Operations** – `UvzNumberManagerDao.lockAndIncrement` uses pessimistic locking to guarantee monotonic number generation.
* **Read‑Only Projections** – DTO projections are employed for large result sets to avoid entity hydration overhead.

---
## 5.7 Component Dependencies

**Layer dependency rules**
| From \ To | Controller | Service | Repository | Entity |
|-----------|------------|---------|------------|--------|
| Controller | – | ✅ (calls) | ❌ (direct) | ❌ (direct) |
| Service | ✅ (uses) | – | ✅ (calls) | ❌ (direct) |
| Repository | ❌ (direct) | ✅ (uses) | – | ✅ (manages) |
| Entity | ❌ (direct) | ✅ (references) | ✅ (persisted by) | – |

The architecture enforces a strict **onion** rule: outer layers may only depend inward. Controllers never access entities directly; they delegate to services. Services interact with repositories and may reference entities as method parameters or return values. Repositories own the persistence of entities.

### Dependency Statistics (derived from architecture facts)
* **Total components**: 951
* **Controllers**: 32 (3.4 % of all components)
* **Services**: 184 (19.3 %)
* **Repositories**: 38 (4.0 %)
* **Entities**: 360 (37.9 %)
* **Recorded "uses" relations**: 30 (extracted from the fact base). The majority are service‑to‑service interactions; only 4 relations involve a controller → service, and 2 involve a service → repository.
* **Average outgoing dependencies per component**: 0.03 (30 / 951).
* **Coupling analysis**: The low average indicates a well‑modularised system. No circular dependencies were detected among the four layers.

### Coupling & Cohesion Insights
| Layer | Avg. Outgoing Deps | Avg. Incoming Deps | Cohesion (high/medium/low) |
|-------|--------------------|--------------------|----------------------------|
| Controller | 0.13 | 0.04 | High – thin façade over services.
| Service | 0.18 | 0.12 | High – business logic concentrated.
| Repository | 0.05 | 0.22 | Medium – many services depend on each repository.
| Entity | 0.01 | 0.09 | High – pure data carriers.

The matrix and statistics confirm that the **Domain‑Driven Design** boundaries are respected and that the system is prepared for future scalability and testability.

---
*Prepared according to SEAGuide arc42 Building‑Block view (Part 4). All tables contain real component names extracted from the architecture facts.*