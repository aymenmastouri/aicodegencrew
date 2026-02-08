# C4 Level 3: Component Diagram (uvz System)

## 3.1 Overview
The backend container (`container.backend`) implements the core business functionality of the **uvz** deed‑entry management platform.  It follows a classic **Layered Architecture** (Presentation → Application → Data‑Access → Domain) built with **Spring Boot**.

## 3.2 Layer Summary
| Layer | Purpose | Component Count | Typical Pattern |
|-------|---------|-----------------|-----------------|
| Presentation (Controllers) | HTTP request handling, REST endpoints | 32 | Spring `@RestController` |
| Application (Services) | Business logic, orchestration | 184 | Service layer, Transactional | 
| Data‑Access (Repositories) | Persistence, JPA/SQL access | 38 | Repository pattern, Spring Data JPA |
| Domain (Entities) | JPA entity model | 360 | `@Entity` with relationships |

## 3.3 Controllers (Presentation Layer)
| Controller | Primary Endpoint(s) | Responsibility |
|------------|-------------------|----------------|
| ActionRestServiceImpl | `/api/actions/**` | CRUD for Action entities |
| IndexHTMLResourceService | `/` (root) | Serves static index page |
| StaticContentController | `/static/**` | Serves static resources |
| CustomMethodSecurityExpressionHandler | – | Security expression handling |
| JsonAuthorizationRestServiceImpl | `/api/auth/**` | JSON‑based auth handling |
| ProxyRestTemplateConfiguration | – | Configures outbound REST templates |
| TokenAuthenticationRestTemplateConfigurationSpringBoot | – | Token auth for outbound calls |
| KeyManagerRestServiceImpl | `/api/keymanager/**` | Key management API |
| ArchivingRestServiceImpl | `/api/archiving/**` | Archive operations |
| BusinessPurposeRestServiceImpl | `/api/business‑purpose/**` | Business purpose CRUD |
| DeedEntryConnectionRestServiceImpl | `/api/deed‑connection/**` | Manage deed connections |
| DeedEntryLogRestServiceImpl | `/api/deed‑log/**` | Deed log access |
| DeedEntryRestServiceImpl | `/api/deed‑entry/**` | Core deed entry CRUD |
| DeedRegistryRestServiceImpl | `/api/deed‑registry/**` | Registry operations |
| DeedTypeRestServiceImpl | `/api/deed‑type/**` | Deed type management |
| DocumentMetaDataRestServiceImpl | `/api/document‑meta/**` | Document metadata API |
| HandoverDataSetRestServiceImpl | `/api/handover‑dataset/**` | Handover data set handling |
| ReportRestServiceImpl | `/api/report/**` | Reporting API |
| OpenApiConfig | `/v3/api-docs/**` | OpenAPI documentation |
| OpenApiOperationAuthorizationRightCustomizer | – | Secures OpenAPI ops |
| ResourceFactory | – | Helper for resource creation |
| DefaultExceptionHandler | – | Global exception handling |
| JobRestServiceImpl | `/api/job/**` | Job management |
| ReencryptionJobRestServiceImpl | `/api/reencryption‑job/**` | Re‑encryption jobs |
| NotaryRepresentationRestServiceImpl | `/api/notary‑representation/**` | Notary representation API |
| NumberManagementRestServiceImpl | `/api/number‑management/**` | Number management API |
| OfficialActivityMetadataRestServiceImpl | `/api/official‑activity/**` | Official activity metadata |
| ReportMetadataRestServiceImpl | `/api/report‑metadata/**` | Report metadata API |
| TaskRestServiceImpl | `/api/task/**` | Task management |
| WorkflowRestServiceImpl | `/api/workflow/**` | Workflow orchestration |
| … (remaining controllers omitted for brevity) |

## 3.4 Services (Application Layer)
The service layer contains **184** components.  Below is a representative subset (alphabetical):
- `ActionServiceImpl` – core action processing
- `ActionWorkerService` – async worker for actions
- `HealthCheck` – actuator health endpoint
- `ArchiveManagerServiceImpl` – archive lifecycle management
- `MockKmService` / `XnpKmServiceImpl` – mock / real key‑manager integration
- `KeyManagerServiceImpl` – key‑manager business logic
- `WaWiServiceImpl` – integration with external WaWi system
- `ArchivingOperationSignerImpl` – signs archive operations
- `ArchivingServiceImpl` – high‑level archiving API
- `DeedEntryConnectionServiceImpl` – connection handling
- `DeedEntryLogServiceImpl` – log handling
- `DeedEntryServiceImpl` – main deed entry CRUD
- `DeedRegistryServiceImpl` – registry functions
- `DeedTypeServiceImpl` – type management
- `DocumentMetaDataServiceImpl` – document metadata handling
- `HandoverDataSetServiceImpl` – handover data set processing
- `SignatureFolderServiceImpl` – signature folder ops
- `ReportServiceImpl` – report generation
- `JobServiceImpl` – background job execution
- `NumberManagementServiceImpl` – number allocation
- `OfficialActivityMetaDataServiceImpl` – official activity data
- `ReportMetadataServiceImpl` – report metadata handling
- `TaskServiceImpl` – task orchestration
- `WorkflowServiceImpl` – workflow engine
- `ReencryptionWorkflowStateMachine` – state machine for re‑encryption
- `WorkflowStateMachineProvider` – provides state machines
- *(frontend services omitted – they belong to the `container.frontend` and are not part of the backend component diagram)*

## 3.5 Repositories (Data‑Access Layer)
The data‑access layer consists of **38** Spring Data repositories.  Key examples:
| Repository | Managed Entity |
|------------|----------------|
| ActionDao | `ActionEntity` |
| DeedEntryDao | `DeedEntryEntity` |
| DeedEntryConnectionDao | `DeedEntryConnectionEntity` |
| DeedEntryLockDao | `DeedEntryLockEntity` |
| DeedEntryLogsDao | `DeedEntryLogEntity` |
| DeedRegistryLockDao | `DeedRegistryLockEntity` |
| DocumentMetaDataDao | `DocumentMetaDataEntity` |
| HandoverDataSetDao | `HandoverDataSetEntity` |
| ParticipantDao | `ParticipantEntity` |
| SignatureInfoDao | `SignatureInfoEntity` |
| SuccessorBatchDao | `SuccessorBatchEntity` |
| UvzNumberManagerDao | `UvzNumberManagerEntity` |
| JobDao | `JobEntity` |
| ReportMetadataDao | `ReportMetadataEntity` |
| TaskDao | `TaskEntity` |
| WorkflowDao | `WorkflowEntity` |
| … (others omitted) |

## 3.6 Domain Model (Entities)
The system defines **360** JPA entities (e.g., `ActionEntity`, `DeedEntryEntity`, `UvzNumberEntity`, `WorkflowEntity`).  They are grouped by bounded contexts (Action, DeedEntry, Archiving, NumberManagement, Workflow, etc.) and are persisted in the relational database used by the backend container.

## 3.7 Component Interaction Overview
```
HTTP Request → Controller (REST) → Service (Transactional) → Repository (Spring Data JPA) → Database
```
Typical call‑graph examples:
1. **Create Deed Entry**
   - `DeedEntryRestServiceImpl` receives `POST /api/deed-entry`
   - Delegates to `DeedEntryServiceImpl`
   - Calls `DeedEntryDao.save()`
   - Persists `DeedEntryEntity`
2. **Archive Deed**
   - `ArchivingRestServiceImpl` → `ArchiveManagerServiceImpl` → `ArchivingServiceImpl`
   - Uses `ArchivingOperationSignerImpl` and `DeedEntryDao` to mark archived
3. **Re‑encryption Workflow**
   - `WorkflowRestServiceImpl` → `WorkflowServiceImpl` → `ReencryptionWorkflowStateMachine`
   - Persists state via `WorkflowDao`

## 3.8 Diagram Reference
A Draw.io component diagram (`c4-component.drawio`) visualises the four layers, the major services, and their repository dependencies.  The diagram follows the SEAGuide C4 visual conventions (blue boxes for internal components, cylinders for databases, dashed boundaries for layers).

---
*Document generated automatically from architecture facts (32 controllers, 184 services, 38 repositories, 360 entities).*
