**File:** `c4/c4-component.md`

# UVZ System – C4 Component Diagram (Level 3)

## 1. Overview  

The **backend** container (Spring Boot) follows a classic **layered architecture** inside a **modular‑monolith** code‑base.  
For the purpose of the C4 model we expose the major layers (stereotypes) and give a handful of representative components for each layer.  The full code‑base contains **826** components; only the most illustrative ones are listed.

| Layer (stereotype) | Component count | Representative examples (package) |
|--------------------|----------------|-----------------------------------|
| **Controllers** (presentation) | **24** | `ActionRestServiceImpl` (de.bnotk.uvz.module.action.logic.impl), `StaticContentController` (de.bnotk.uvz.module.adapters.staticwebresources), `KeyManagerRestServiceImpl` (de.bnotk.uvz.module.adapters.km.logic.impl), `ArchivingRestServiceImpl` (de.bnotk.uvz.module.archive.logic.impl), `BusinessPurposeRestServiceImpl` (de.bnotk.uvz.module.deedentry.logic.impl), `DeedEntryRestServiceImpl` (de.bnotk.uvz.module.deedentry.logic.impl) |
| **Services** (business) | **233** | `ActionServiceImpl` (de.bnotk.uvz.module.action.logic.impl), `IndexHTMLResourceService` (de.bnotk.uvz.module.adapters.staticwebresources), `HealthCheck` (de.bnotk.uvz.module.adapters.actuator.service), `ArchiveManagerServiceImpl` (de.bnotk.uvz.module.adapters.archivemanager.logic.impl), `KeyManagerServiceImpl` (de.bnotk.uvz.module.adapters.km.logic.impl), `WaWiServiceImpl` (de.bnotk.uvz.module.adapters.wawi.impl), `ArchivingOperationSignerImpl` (de.bnotk.uvz.module.archive.logic.impl), `BusinessPurposeServiceImpl` (de.bnotk.uvz.module.deedentry.logic.impl), `DeedEntryServiceImpl` (de.bnotk.uvz.module.deedentry.logic.impl), `JobServiceImpl` (de.bnotk.uvz.module.job.logic.impl) |
| **Repositories** (data‑access) | **4** | `FinalHandoverDataSetDaoImpl` (de.bnotk.uvz.module.deedentry.dataaccess.api.dao.impl), `TaskDaoImpl` (de.bnotk.uvz.module.job.dataaccess.api.dao.impl), `DocumentMetadataWorkDaoImpl` (de.bnotk.uvz.module.deedentry.dataaccess.api.dao.impl), `WorkflowDaoImpl` (de.bnotk.uvz.module.job.dataaccess.api.dao.impl) |
| **Entities** (domain model) | **37** | `ActionEntity`, `ActionStreamEntity`, `ChangeEntity`, `ConnectionEntity`, `CorrectionNoteEntity`, `DeedCreatorHandoverInfoEntity`, `DeedEntryEntity`, `DeedEntryLockEntity`, `DeedEntryLogEntity`, `DeedRegistryLockEntity` |
| **Modules** (Angular/Java modules) | **18** | `AppModule`, `AdaptersModule`, `CoreModule`, `DeedEntryModule`, `NumberManagementModule`, `ReportMetadataModule`, `OnlineHelpModule`, `SharedModule`, `WorkflowModule` |
| **Pipes** (Angular data‑transform) | **67** | `DeedSuccessorInfoPipe`, `DeedSuccessorTitlePipe`, `FilterProblemConnectionsPipe`, `ShowCorrectionNoteIconForDeletionPipe`, `ValueByFieldidPipe`, `ReceiverLabelPipe` |
| **Directives** (Angular UI helpers) | **5** | `AbstractTab`, `DocumentArchivingOverlayDirective`, `AutofocusDirective`, `DatePickerFocusLostDirective`, `AbstractPageWithActionBar` |
| **Design‑Pattern Artefacts** | **6** | `repository_pattern`, `factory_pattern`, `builder_pattern`, `singleton_pattern`, `adapter_pattern`, `observer_pattern` |

### Layer Relationships (derived from the code‑base)

* Controllers **call** Services.  
* Services **use** Repositories and **manipulate** Entities.  
* Repositories **persist** Entities.  
* Angular **Modules** group Pipes and Directives.  
* Design‑Pattern artefacts are **applied to** Services and Repositories.

## 2. Component Diagram  

The diagram visualising the layer structure, component counts and their inter‑layer dependencies is stored in **`c4/c4-component.drawio`**.  
Key visual elements:

* **Eight rectangular nodes** representing the main layers (Controllers, Services, Repositories, Entities, Modules, Pipes, Directives, Design Patterns).  
* **Labels** show the exact component count for each layer.  
* **Arrows** encode the relationships listed above (e.g., Controllers → Services, Services → Repositories, Services → Entities, Repositories → Entities, Modules → Pipes/Directives, Design Patterns → Services/Repositories).

## 3. Narrative Description  

1. **Presentation Layer – Controllers**  
   The 24 controller classes expose the system’s **REST API** (e.g., `ActionRestServiceImpl`, `DeedEntryRestServiceImpl`). Each controller delegates work to the business layer.

2. **Business Layer – Services**  
   The backbone of the system, with **233** service implementations, encapsulates the core use‑cases (action handling, archiving, key management, deed processing, job scheduling). Services are **stateless** and wired by Spring.

3. **Data‑Access Layer – Repositories**  
   Only **4** DAO classes exist, reflecting a thin persistence abstraction over Spring Data JPA. They are used exclusively by services.

4. **Domain Model – Entities**  
   **37** JPA‑annotated entity classes model the UVZ domain (deed entries, keys, actions, etc.). Services create, read, update, and delete these entities via the repositories.

5. **Angular Front‑End Structure**  
   The frontend code is organised into **18** Angular modules, each bundling related **pipes** (67) and **directives** (5). Modules provide feature boundaries (e.g., `DeedEntryModule`, `WorkflowModule`).

6. **Design‑Pattern Artefacts**  
   The codebase declares six classic design‑pattern identifiers that are applied throughout the service and repository layers, reinforcing clean architecture principles.

## 4. Architectural Context  

* **Primary style:** *Modular Monolith* (single deployable backend with internal modularisation).  
* **Backend pattern:** *Layered Architecture* (Controller → Service → Repository).  
* **Frontend pattern:** *Component‑Based SPA* (Angular).  
* **Quality:** High cohesion, loose coupling, overall architectural grade **A** (see `analyzed_architecture.json`).  

---  

*All names, counts and layer assignments are taken directly from **architecture_facts.json**; the overall style and quality assessment are taken from **analyzed_architecture.json**.*