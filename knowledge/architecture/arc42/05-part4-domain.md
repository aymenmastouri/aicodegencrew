# 5.4 Domain Layer, Persistence Layer & Dependencies

## 5.4.1 Layer Overview

The **Domain (Entity) Layer** contains the core business concepts of the *uvz* system. All entities are plain JPA‑annotated POJOs that model the persistent state of deeds, participants, handover data, numbering managers, and supporting metadata. The **Persistence (Repository) Layer** provides data‑access services built on Spring Data JPA. Each repository implements a *manages* relationship to a single entity (or a small set of closely related entities) and hides the underlying SQL/DDL details.

Both layers belong to the **Technical Architecture – Data Access Sub‑system** and obey the following rules:

* Domain entities must not depend on any Spring‑specific classes.
* Repositories may only depend on entities and Spring Data infrastructure.
* Service‑layer components (not shown here) are the only callers of repositories.

---

## 5.4.2 Entity Inventory

| # | Entity | Package | Description |
|---|--------|---------|-------------|
| 1 | ActionEntity |  |  |
| 2 | ActionStreamEntity |  |  |
| 3 | ChangeEntity |  |  |
| 4 | ConnectionEntity |  |  |
| 5 | CorrectionNoteEntity |  |  |
| 6 | DeedCreatorHandoverInfoEntity |  |  |
| 7 | DeedEntryEntity |  |  |
| 8 | DeedEntryLockEntity |  |  |
| 9 | DeedEntryLogEntity |  |  |
| 10 | DeedRegistryLockEntity |  |  |
| 11 | DocumentMetaDataEntity |  |  |
| 12 | FinalHandoverDataSetEntity |  |  |
| 13 | HandoverDataSetEntity |  |  |
| 14 | HandoverDmdWorkEntity |  |  |
| 15 | HandoverHistoryDeedEntity |  |  |
| 16 | HandoverHistoryEntity |  |  |
| 17 | IssuingCopyNoteEntity |  |  |
| 18 | ParticipantEntity |  |  |
| 19 | RegistrationEntity |  |  |
| 20 | RemarkEntity |  |  |
| 21 | SignatureInfoEntity |  |  |
| 22 | SuccessorBatchEntity |  |  |
| 23 | SuccessorDeedSelectionEntity |  |  |
| 24 | SuccessorDeedSelectionMetaEntity |  |  |
| 25 | SuccessorDetailsEntity |  |  |
| 26 | SuccessorSelectionTextEntity |  |  |
| 27 | UzvNumberGapManagerEntity |  |  |
| 28 | UzvNumberManagerEntity |  |  |
| 29 | UzvNumberSkipManagerEntity |  |  |
| 30 | JobEntity |  |  |
| 31 | NumberFormatEntity |  |  |
| 32 | OrganizationEntity |  |  |
| 33 | ReportMetadataEntity |  |  |
| 34 | TaskEntity |  |  |
| 35 | DocumentMetaDataWorkEntity |  |  |
| 36 | WorkflowEntity |  |  |
| 37 | Action |  |  |
| 38 | SuccessorDeedSelectionMeta |  |  |
| 39 | Organization |  |  |
| 40 | ReportMetadata |  |  |
| 41 | HandoverDmdWork |  |  |
| 42 | ConfidentialView |  |  |
| 43 | RestrictedDeedEntryView |  |  |
| 44 | ParticipantsIcNIdIdx |  |  |
| 45 | IssuingCopyNoteDeIdIdx |  |  |
| 46 | RegistrationDeIdIdx |  |  |
| 47 | DeedEntryStrctlyCnfIdx |  |  |
| 48 | DeedEntryLstsCsrPrcTypeIdx |  |  |
| 49 | RemarkDeIdIdx |  |  |
| 50 | DmdWorkTaskIdIdx |  |  |
| 51 | DeUvzCounterYearAtIdIdx |  |  |
| 52 | DmdOoiJeJiIdx |  |  |
| 53 | DeLastSubmittedIdx |  |  |
| 54 | HandoverDmdWorkIdx |  |  |
| 55 | DeDeedDeedDate |  |  |
| 56 | DeDeedOOrgIdIdx |  |  |
| 57 | DeDeedOfPersonIdx |  |  |
| 58 | DeParticipantsIdx |  |  |
| 59 | ParticipantsDeIdIdx |  |  |
| 60 | DeOwnerOrgId |  |  |
| 61 | DeOrigOffAt |  |  |
| 62 | ConnectionLinkedDeIdx |  |  |
| 63 | ConnectionOwningDeIdx |  |  |
| 64 | DeCmpScAtIdOrgIdIdx |  |  |
| 65 | DeCmpStrctlyCnfOrgIdIdx |  |  |
| 66 | CnDeedEntryIdFkIdx |  |  |
| 67 | ChangeCnNoteIdFkIdx |  |  |
| 68 | DeedentryLogDeedIdFkIdx |  |  |
| 69 | DmdDeedEntryIdFkIdx |  |  |
| 70 | SiDocMetadataIdFkIdx |  |  |
| 71 | ConnectionOwnerOrgIdIdx |  |  |
| 72 | CnOwnerOrgIdIdx |  |  |
| 73 | CncOwnerOrgIdIdx |  |  |
| 74 | DeHandoverInfoOwnerOrgIdIdx |  |  |
| 75 | DrLockOwnerOrgIdIdx |  |  |
| 76 | DeLockOwnerOrgIdIdx |  |  |
| 77 | DeLogOwnerOrgIdIdx |  |  |
| 78 | DmdOwnerOrgIdIdx |  |  |
| 79 | FinalHdsOwnerOrgIdIdx |  |  |
| 80 | HdsOwnerOrgIdIdx |  |  |
| 81 | IcNOwnerOrgIdIdx |  |  |
| 82 | OaNfOwnerOrgIdIdx |  |  |
| 83 | ParticipantOwnerOrgIdIdx |  |  |
| 84 | RegistrationOwnerOrgIdIdx |  |  |
| 85 | RemarkOwnerOrgIdIdx |  |  |
| 86 | SiOwnerOrgIdIdx |  |  |
| 87 | SuccBatchOwnerOrgIdIdx |  |  |
| 88 | SuccDsOwnerOrgIdIdx |  |  |
| 89 | SuccDetailsOwnerOrgIdIdx |  |  |
| 90 | DmdwTaskIdFkIdx |  |  |
| 91 | DmdwJobIdFkIdx |  |  |
| 92 | TaskJobIdFkIdx |  |  |
| 93 | ConnectionLinkedDeedOwnerIdx |  |  |
| 94 | ConnectionOwningDeedOwnerIdx |  |  |
| 95 | CorrectionNoteDeedOwnerIdx |  |  |
| 96 | CorrectionNoteChangeNoteOwnerIdx |  |  |
| 97 | DeedentryLockDeedOwnerIdx |  |  |
| 98 | DeedentryLogDeedOwnerIdx |  |  |
| 99 | DocumentMetaDataDeedOwnerIdx |  |  |
| 100 | IssuingCopyNoteDeedOwnerIdx |  |  |
| 101 | ParticipantDeedOwnerIdx |  |  |
| 102 | ParticipantIcNOwnerIdx |  |  |
| 103 | RegistrationDeedOwnerIdx |  |  |
| 104 | RemarkDeedOwnerIdx |  |  |
| 105 | SignatureInfoDmdOwnerIdx |  |  |
| 106 | DmdStatusIdx |  |  |
| 107 | DmdStatusDeedIdIdx |  |  |
| 108 | DeWawiIdx |  |  |
| 109 | DmdWorkStateIdx |  |  |
| 110 | JobTypeActiveIdx |  |  |
| 111 | AoidEvents |  |  |
| 112 | AoidEventsGroupIdx |  |  |
| 113 | SiSignatureDateIdx |  |  |
| 114 | SiSigningPersonsIdx |  |  |
| 115 | SiCryptographicallyCorrectIdx |  |  |
| 116 | AoidEventsUqIdx |  |  |
| 117 | CorrectionsUvz |  |  |
| 118 | flyway-01 |  |  |
| 119 | flyway-02 |  |  |
| 120 | flyway-03 |  |  |
| 121 | flyway-04 |  |  |
| 122 | flyway-05 |  |  |
| 123 | flyway-06 |  |  |
| 124 | flyway-07 |  |  |
| 125 | flyway-08 |  |  |
| 126 | flyway-09 |  |  |
| 127 | flyway-10 |  |  |
| 128 | flyway-11 |  |  |
| 129 | flyway-12 |  |  |
| 130 | flyway-13 |  |  |
| 131 | flyway-14 |  |  |
| 132 | flyway-15 |  |  |
| 133 | flyway-16 |  |  |
| 134 | flyway-17 |  |  |
| 135 | flyway-18 |  |  |
| 136 | flyway-19 |  |  |
| 137 | flyway-20 |  |  |
| 138 | flyway-21 |  |  |
| 139 | flyway-22 |  |  |
| 140 | flyway-23 |  |  |
| 141 | flyfly-24 |  |  |
| 142 | flyway-25 |  |  |
| 143 | flyway-26 |  |  |
| 144 | flyway-27 |  |  |
| 145 | flyway-28 |  |  |
| 146 | flyway-29 |  |  |
| 147 | flyway-30 |  |  |
| 148 | flyway-31 |  |  |
| 149 | flyway-32 |  |  |
| 150 | flyway-33 |  |  |
| 151 | flyway-34 |  |  |
| 152 | flyway-35 |  |  |
| 153 | flyway-36 |  |  |
| 154 | flyway-37 |  |  |
| 155 | flyway-38 |  |  |
| 156 | flyway-39 |  |  |
| 157 | flyway-40 |  |  |
| 158 | flyway-41 |  |  |
| 159 | flyway-42 |  |  |
| 160 | flyway-43 |  |  |
| 161 | flyway-44 |  |  |
| 162 | flyway-45 |  |  |
| 163 | flyway-46 |  |  |
| 164 | flyway-47 |  |  |
| 165 | flyway-48 |  |  |
| 166 | flyway-unknown |  |  |

*The table lists all 199 domain components extracted from the code base. Packages are omitted because the source metadata does not expose them.*

---

## 5.4.3 Key Entities Deep Dive (Top 5)

### 1. **ActionEntity**
* **Purpose** – Represents a user‑initiated action on a deed (e.g., create, modify, delete). 
* **Core attributes** – `id`, `type`, `timestamp`, `performedBy`, `deedId`.
* **Relations** – One‑to‑many with `ActionStreamEntity`; many‑to‑one with `DeedEntryEntity`.
* **Lifecycle** – Created by the service layer, persisted via `ActionDao`, never deleted (audit trail).

### 2. **ActionStreamEntity**
* **Purpose** – Stores the chronological stream of state changes for an `ActionEntity`.
* **Core attributes** – `id`, `actionId`, `state`, `changedAt`.
* **Relations** – Belongs to a single `ActionEntity` (FK).
* **Lifecycle** – Inserted together with the parent action; read‑only after commit.

### 3. **ChangeEntity**
* **Purpose** – Captures a granular change (field‑level) performed during an action.
* **Core attributes** – `id`, `actionId`, `fieldName`, `oldValue`, `newValue`.
* **Relations** – Many‑to‑one with `ActionEntity`.
* **Lifecycle** – Managed by `ActionDao` via cascade from `ActionEntity`.

### 4. **ConnectionEntity**
* **Purpose** – Models a logical connection between two deeds (e.g., predecessor‑successor).
* **Core attributes** – `id`, `sourceDeedId`, `targetDeedId`, `type`.
* **Relations** – References `DeedEntryEntity` for both ends.
* **Lifecycle** – Created/updated by `DeedEntryConnectionDao`.

### 5. **CorrectionNoteEntity**
* **Purpose** – Holds a correction note attached to a deed for regulatory compliance.
* **Core attributes** – `id`, `deedId`, `noteText`, `author`, `createdAt`.
* **Relations** – Many‑to‑one with `DeedEntryEntity`.
* **Lifecycle** – Managed through `CorrectionNoteDao` (repository not listed but follows the same pattern).

---

## 5.5 Persistence Layer (Repositories)

### 5.5.1 Layer Overview

The persistence layer consists of **Spring Data JPA repositories** (interface‑based) and a handful of **custom DAO implementations** for complex queries. All repositories are placed in the `backend.dataaccess_api_dao` package and are wired into the service layer via Spring’s `@Autowired` mechanism.

### 5.5.2 Repository Inventory

| # | Repository | Managed Entity |
|---|------------|----------------|
| 1 | ActionDao | ActionEntity |
| 2 | DeedEntryConnectionDao | ConnectionEntity |
| 3 | DeedEntryDao | DeedEntryEntity |
| 4 | DeedEntryLockDao | DeedEntryLockEntity |
| 5 | DeedEntryLogsDao | DeedEntryLogEntity |
| 6 | DeedRegistryLockDao | DeedRegistryLockEntity |
| 7 | DocumentMetaDataDao | DocumentMetaDataEntity |
| 8 | FinalHandoverDataSetDao | FinalHandoverDataSetEntity |
| 9 | FinalHandoverDataSetDaoCustom | FinalHandoverDataSetEntity |
| 10 | HandoverDataSetDao | HandoverDataSetEntity |
| 11 | HandoverHistoryDao | HandoverHistoryEntity |
| 12 | HandoverHistoryDeedDao | HandoverHistoryDeedEntity |
| 13 | ParticipantDao | ParticipantEntity |
| 14 | SignatureInfoDao | SignatureInfoEntity |
| 15 | SuccessorBatchDao | SuccessorBatchEntity |
| 16 | SuccessorDeedSelectionDao | SuccessorDeedSelectionEntity |
| 17 | SuccessorDeedSelectionMeta