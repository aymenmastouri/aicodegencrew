# C4 Level 3 – Component View  
**System:** UVZ Deed Management System (`uvz`)  
**Documentation file:** `knowledge/architecture/c4/c4-component.md`  
**Diagram file:** `knowledge/architecture/c4/c4-component.drawio`  

---  

## 3.1 Overview  

The **Component diagram** describes the internal structure of the **Backend API container** (Spring Boot).  
Because the backend contains **826 individual source artefacts**, we present the architecture as **layered swim‑lanes** with component counts rather than drawing every class.  

*The diagram follows the Capgemini SEAGuide C4 visual conventions:*  

| Symbol | Meaning |
|--------|----------|
| **Blue rounded rectangle** | A logical layer inside the Backend container (e.g., Presentation, Business, Data‑Access, Domain). |
| **Cylinder** | The PostgreSQL database (external persistent store). |
| **Dashed rectangle** | The container boundary (“Backend API Container [Spring Boot]”). |
| **Legend** | Shows colour/shape meaning and component counts. |

The diagram can be opened in **draw.io** (Diagrams.net) from the path above.

---  

## 3.2 Backend API Components – Layer Overview  

| Layer | Primary Purpose | Component Count | Dominant Design Pattern |
|-------|-----------------|----------------|------------------------|
| **Presentation (Controllers)** | HTTP request handling, request validation, response mapping. | **24** | Spring MVC → REST Controller |
| **Business (Services)** | Core domain logic, orchestration, transaction management. | **233** | Service‑layer pattern |
| **Data‑Access (Repositories)** | CRUD & custom queries against the relational store. | **4** | Repository pattern (Spring Data JPA) |
| **Domain (Entities)** | JPA‑mapped persistence objects representing the business model. | **37** | Entity/DTO pattern |
| **Infrastructure / Integration** | External system adapters, HTTP client wrappers, database connection beans. | **12** (incl. `rest_client_integration`, `h2_connection`, `oracle_connection`×4, …) | Adapter / Proxy pattern |
| **Cross‑cutting** | Security, exception handling, logging, metrics, AOP aspects. | **9** (e.g., `SecurityConfig`, `DefaultExceptionHandler`, `ExecutionTimingAspect`, `HealthCheck`) | Aspect‑Oriented Programming |
| **Modules / Packages** | Logical grouping of related features (e.g., `deedentry`, `action`, `workflow`). | **18** (module‑level classes such as `DeedEntryModule`, `ActionModule`, `ReportMetadataModule`) | Modular monolith |
| **Pipes (Angular UI helpers)** – *Frontend* (shown for context) | Transformations on client‑side data streams. | **67** | Functional pipe pattern |
| **SQL Scripts** – *Database initialisation* | DML/DDL used for test data, acceptance, performance sets. | **258** | Script‑based data loading |
| **Design‑Pattern Stubs** | Declared pattern descriptors (e.g., `factory_pattern`, `singleton_pattern`). | **6** | – |
| **Directive Layer (Angular)** | UI behaviour directives (client side). | **5** | – |
| **Dockerfile Layer** | Build artefact for the Docker image. | **1** | – |
| **Architecture‑Style Layer** | High‑level architectural style descriptors. | **2** (e.g., `layered_architecture`, `modular_monolith_architecture`) | – |

> **Note:** Only the *Backend* layers are rendered in the component diagram. Front‑end layers (Pipes, Directives) are listed for completeness but are not part of the container boundary.

---  

## 3.3 Detailed Layer Tables  

### 3.3.1 Presentation Layer – Controllers  

| Stereotype | # Components | Representative Examples |
|------------|--------------|--------------------------|
| `controller` | **24** | `ActionRestServiceImpl`, `StaticContentController`, `DeedEntryRestServiceImpl`, `ReportRestServiceImpl`, `WorkflowRestServiceImpl`, `JobRestServiceImpl`, `TaskRestServiceImpl` |
| `exception_handler` | 1 | `DefaultExceptionHandler` |
| `security_expression_handler` | 1 | `CustomMethodSecurityExpressionHandler` |

*All controllers expose REST endpoints under `/api/**` and are secured via Spring Security (OIDC tokens from Keycloak).*

### 3.3.2 Business Layer – Services  

| Stereotype | # Components | Representative Examples |
|------------|--------------|--------------------------|
| `service` | **233** | `ActionServiceImpl`, `DeedEntryServiceImpl`, `KeyManagerServiceImpl`, `ArchiveManagerServiceImpl`, `JobServiceImpl`, `ReportServiceImpl`, `WaWiServiceImpl` |
| `component` (cross‑cutting) | 9 | `ExecutionTimingAspect`, `HealthCheck`, `LiveHealthIndicator`, `ReadyHealthIndicator`, `ReencryptionAccessEvaluator` |

### 3.3.3 Data‑Access Layer – Repositories  

| Stereotype | # Components | Representative Examples |
|------------|--------------|--------------------------|
| `service` (used as DAO) | **4** | `DeedEntryConnectionDaoImpl`, `DeedEntryLogsDaoImpl`, `DocumentMetaDataCustomDaoImpl`, `HandoverDataSetDaoImpl` |

*Implemented using Spring Data JPA interfaces; each repository maps to a specific JPA entity.*

### 3.3.4 Domain Layer – Entities  

| Stereotype | # Components | Representative Examples |
|------------|--------------|--------------------------|
| `entity` | **37** | `ActionEntity`, `ActionStreamEntity`, `DeedEntryEntity`, `DeedRegistryEntity`, `ReportMetadataEntity`, `NumberManagementEntity` |

*All entities are annotated with `@Entity` and participate in JPA relationships (One‑To‑Many, Many‑To‑One).*

### 3.3.5 Infrastructure / Integration  

| Stereotype | # Components | Representative Examples |
|------------|--------------|--------------------------|
| `integration` | 1 | `rest_client_integration` (provides a `RestTemplate` bean) |
| `database_connection` | 6 | `h2_connection`, `oracle_connection` × 4, `oracle_connection` (different profiles) |
| `component` (configuration) | 2 | `BackendMetadata` (holds Spring profiles), `Dockerfile-docker` (metadata) |

---  

## 3.4 Component Diagram  

The **Component diagram** (draw.io) visualises the four logical layers as swim‑lanes inside the **Backend API Container** and shows the dependency flow down to the PostgreSQL database.

```
+--------------------------------------------------------------+
|               Backend API Container [Spring Boot]            |
+--------------------------------------------------------------+
|  Presentation Layer (Controllers) – 24 components           |
|        └─► Business Layer (Services) – 233 components       |
|               └─► Data‑Access Layer (Repositories) – 4 comp |
|                       └─► PostgreSQL DB (cylinder)          |
|        └─► Domain Layer (Entities) – 37 components          |
+--------------------------------------------------------------+
```

*Arrows indicate the allowed direction of dependencies (see Section 3.5).  
The diagram file is `knowledge/architecture/c4/c4-component.drawio` and contains a legend: blue boxes = layers, cylinder = database, dashed rectangle = container boundary.*

---  

## 3.5 Component Dependencies  

### 3.5.1 Layer‑to‑Layer Rules  

| From → To | Allowed? | Rationale |
|-----------|----------|-----------|
| **Controller → Service** | ✅ | Classic MVC flow – controllers delegate business work to services. |
| **Controller → Repository** | ❌ | Controllers must not bypass services; repository access is encapsulated. |
| **Controller → Entity** | ❌ (only via DTO) | Entities are never exposed directly; DTOs map to/from entities. |
| **Service → Service** | ✅ | Services may call each other for orchestration. |
| **Service → Repository** | ✅ | Services own data‑access through repositories. |
| **Service → Entity** | ✅ | Services manipulate domain objects. |
| **Repository → Entity** | ✅ | Repositories persist/retrieve entities. |
| **Service → Integration (RestTemplate, DB connection)** | ✅ | External adapters are invoked from the service layer. |
| **Cross‑cutting (Aspect, ExceptionHandler) → All layers** | ✅ | Applied globally via Spring AOP / @ControllerAdvice. |

### 3.5.2 Cross‑Cutting Components  

| Component | Consumed By | Primary Responsibility |
|-----------|-------------|------------------------|
| `SecurityConfig` | All controllers & services | OIDC integration with Keycloak, role‑based authorisation. |
| `DefaultExceptionHandler` | All controllers | Centralised error mapping to HTTP status codes. |
| `ExecutionTimingAspect` | All services | Measures execution time, feeds metrics. |
| `HealthCheck` / `LiveHealthIndicator` / `ReadyHealthIndicator` | Actuator endpoints | Provides liveness/readiness data for orchestration. |
| `ReencryptionAccessEvaluator` | Security‑related services | Evaluates encryption permissions for sensitive data. |

---  

## 3.6 Component Communication Example  

**Scenario:** *Create a new deed (POST /api/deeds)*  

```
1. HTTP POST /api/deeds  (JSON payload)                <-- Notary UI
2. └─► DeedEntryRestServiceImpl (Controller)
       • @Valid, @Authenticated
3.      └─► DeedEntryServiceImpl (Service)
       • Business validation, transaction start
4.           └─► DeedEntryRepository (Repository)
       • save(entity) → JPA/Hibernate
5.                └─► PostgreSQL (INSERT)
6. After commit, Service returns DeedDTO
7. Controller maps DTO → JSON response (201 Created)
```

All steps respect the layer rules defined above; cross‑cutting aspects (timing, security) are applied automatically.

---  

## 3.7 Summary of Quantitative Metrics  

| Metric | Value |
|--------|-------|
| **Total components (all layers)** | **826** |
| **Backend‑only components** | **≈ 530** (Controllers 24 + Services 233 + Repositories 4 + Entities 37 + Infrastructure ≈ 90 + Cross‑cutting ≈ 30 + Modules ≈ 18) |
| **SQL script artefacts** | **258** |
| **Angular pipes (frontend)** | **67** |
| **Number of distinct layers** | **13** (Presentation, Business, Data‑Access, Domain, Integration, Cross‑cutting, Module, Design‑Pattern, Directive, Dockerfile, Architecture‑Style, SQL‑Script) |
| **Average components per layer** | ≈ 64 (but highly skewed – Services dominate) |

---  

## 3.8 References  

| Source | Used For |
|--------|----------|
| `architecture_facts.json` | Component counts, stereotypes, layer assignment. |
| `list_components_by_stereotype` (controller) | Exact list of 24 controller classes. |
| `query_architecture_facts` (service) | List of 233 service components. |
| SEAGuide – C4 documentation patterns | Visual conventions, legend, swim‑lane style. |
| Spring Boot & Angular official docs | Confirmation of technology versions and typical architecture patterns. |

---  

*Prepared by:* **Senior Software Architect – C4 Model Expert**  
*Date:* **2026‑02‑03**  