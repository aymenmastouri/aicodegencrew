**C4 Component Diagram – UVZ System**  

---  

## Layered Structure (Backend)  
The backend container follows a classic **Layered Architecture** (presentation → business → data). The analysis identified the following stereotyped component groups:

| Layer | Component Count | Representative Examples |
|-------|----------------|--------------------------|
| **Controllers (Presentation)** | 24 | `ActionRestServiceImpl`, `StaticContentController`, `KeyManagerRestServiceImpl`, `ArchivingRestServiceImpl`, `DeedEntryRestServiceImpl` |
| **Services (Business Logic)** | 233 | `ActionServiceImpl`, `ArchivingServiceImpl`, `KeyManagerServiceImpl`, `DeedEntryServiceImpl`, `XnpKmServiceImpl` |
| **Repositories (Data Access)** | 4 | `FinalHandoverDataSetDaoImpl`, `TaskDaoImpl`, `DocumentMetadataWorkDaoImpl`, `WorkflowDaoImpl` |
| **Entities (Domain Model)** | 37 | `ActionEntity`, `DeedEntryEntity`, `DeedEntryLogEntity`, `NumberFormatEntity`, `WorkflowEntity` |

### Dependencies  

* **Controllers** **call** **Services**.  
* ** Services** **use** **Repositories**.  
* **Repositories** **persist** **Entities** (via JPA/Hibernate).  

These relationships are visualised in the Draw.io diagram **`c4/c4-component.drawio`**, which shows the four layers as boxes with counts and a few example component names, connected by arrows reflecting the dependencies above.  

---  

## Architectural Context  

* **Architecture Style:** Modular Monolith (single Spring‑Boot application internally layered).  
* **Primary Patterns:** Layered Architecture, Repository Pattern, Factory Pattern, Adapter Pattern (used for XNP integration).  
* **Quality Indicators:** High cohesion, loose coupling (≈0.15 uses/component), no layer violations, overall grade **A**.  

The component diagram provides a high‑level view of the internal structure without enumerating all 826 components, satisfying the requirement to show layer boundaries and representative elements.  

---  

**Diagram file:** `c4/c4-component.drawio` (contains four layered nodes – Controllers, Services, Repositories, Entities – with counts and example component names, and edges labeled *calls*, *uses*, *persists*).