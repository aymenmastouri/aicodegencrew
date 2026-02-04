# Component Diagram – UVZ System

## Overview  
The backend container follows a classic **layered architecture**. With **826 components** overall, they are grouped into logical layers (stereotypes) that reflect presentation, business, persistence and domain‑model concerns. The diagram (stored as `c4/c4-component.drawio`) shows these layers, component counts and a few representative examples.

## Layer Structure  

| Layer | Component Count | Representative Examples |
|-------|----------------|--------------------------|
| **Controllers** (Presentation) | 24 | `ActionRestServiceImpl`, `DeedEntryRestServiceImpl`, `ArchivingRestServiceImpl`, `BusinessPurposeRestServiceImpl`, `StaticContentController` |
| **Services** (Business) | 233 | `ActionServiceImpl`, `DeedEntryServiceImpl`, `ArchivingServiceImpl`, `KeyManagerServiceImpl`, `WaWiServiceImpl`, `XnpKmServiceImpl` |
| **Repositories** (Data Access) | 4 | `FinalHandoverDataSetDaoImpl`, `TaskDaoImpl`, `DocumentMetadataWorkDaoImpl`, `WorkflowDaoImpl` |
| **Entities** (Domain Model) | 37 | `ActionEntity`, `DeedEntryEntity`, `DeedEntryLogEntity`, `ChangeEntity`, `ConnectionEntity`, `CorrectionNoteEntity` |
| **Integration** (Infrastructure) | 1 | `rest_client_integration` |

## High‑Level Relationships  
- **Controllers** **call** **Services**.  
- **Services** **use** **Repositories** and **read** **Entities**.  
- **Repositories** **persist** **Entities**.  
- **Integration** component **provides** HTTP client functionality to **Services**.

## Diagram  
The component‑layer diagram is available at **`c4/c4-component.drawio`**. This DrawIO file contains five nodes representing the layers above, with edges illustrating the high‑level dependencies (controllers → services → repositories → entities; services also read entities and consume the integration component).