# 06 – Runtime View (Part 1): API Flows

---

## 6.1 Runtime View Overview

**Purpose** – This section describes the dynamic behaviour of the UVZ system when a client invokes any of its public REST endpoints. It shows how the Angular front‑end, the Spring Boot back‑end and the underlying persistence layer collaborate to fulfil a request.

**How to read the sequence diagrams** – All diagrams are expressed in a compact PlantUML‑like syntax that can be rendered with any PlantUML tool.

| Symbol | Meaning |
|--------|---------|
| **actor** | External client (browser, mobile app, other service) |
| **[Component]** | Concrete Spring bean – controller, service or repository – exactly as named in the architecture facts |
| **→** | Synchronous call (HTTP request, method invocation) |
| **←** | Return value or HTTP response |
| **alt / opt** | Conditional or optional flow |
| **note right** | Additional explanatory text |

The diagrams deliberately omit infrastructure details (load‑balancer, TLS termination) because they are covered in the deployment view (chapter 8).

---

## 6.2 Authentication Flow

### 6.2.1 Login Sequence (≈ 2 pages)

```plantuml
@startuml
actor Browser
participant JsonAuthorizationRestServiceImpl as AuthCtrl
participant TokenAuthenticationRestTemplateConfigurationSpringBoot as TokenCfg
participant ActionServiceImpl as AuthSrv
participant ActionDao as AuthRepo

Browser -> AuthCtrl : POST /jsonauth/user/to/authorization/service (credentials)
activate AuthCtrl
AuthCtrl -> TokenCfg : create RestTemplate (client‑cert)
AuthCtrl -> AuthSrv : validateCredentials(username,password)
activate AuthSrv
AuthSrv -> AuthRepo : findByUsername(username)
activate AuthRepo
AuthRepo --> AuthSrv : Optional<UserEntity>
deactivate AuthRepo
alt user found & password ok
    AuthSrv -> TokenCfg : generate JWT (claims, expiry)
    AuthSrv --> AuthCtrl : AuthResult (JWT)
else authentication failure
    AuthSrv --> AuthCtrl : AuthenticationException
end
deactivate AuthSrv
AuthCtrl --> Browser : 200 OK + JWT / 401 Unauthorized
deactivate AuthCtrl
@enduml
```

*Key points*
- **`JsonAuthorizationRestServiceImpl`** is the only public entry point for authentication.
- Credential validation is delegated to **`ActionServiceImpl`**, which reads the user record via **`ActionDao`**.
- A **`TokenAuthenticationRestTemplateConfigurationSpringBoot`** bean creates a `RestTemplate` that signs outgoing calls with the client certificate required by downstream services.
- On success a signed JWT is returned; on failure the controller advice (`DefaultExceptionHandler`) maps the exception to **401**.

### 6.2.2 Token Refresh / Session Management (≈ 1 page)

```plantuml
@startuml
actor Browser
participant JsonAuthorizationRestServiceImpl as AuthCtrl
participant TokenAuthenticationRestTemplateConfigurationSpringBoot as TokenCfg
participant ActionServiceImpl as AuthSrv

Browser -> AuthCtrl : POST /jsonauth/user/to/authorization/service (refresh token)
activate AuthCtrl
AuthCtrl -> TokenCfg : parse JWT, verify signature & expiry
alt token still valid
    AuthCtrl --> Browser : 200 OK + new JWT (extended expiry)
else token expired
    AuthCtrl -> AuthSrv : re‑authenticate (username from token)
    activate AuthSrv
    AuthSrv -> ActionDao : findByUsername(username)
    activate ActionDao
    ActionDao --> AuthSrv : UserEntity
    deactivate ActionDao
    AuthSrv -> TokenCfg : generate new JWT
    AuthSrv --> AuthCtrl : AuthResult (new JWT)
    deactivate AuthSrv
    AuthCtrl --> Browser : 200 OK + new JWT
end
deactivate AuthCtrl
@enduml
```

The same controller handles both login and refresh. If the presented JWT is still within its validity window, a fresh token is issued without hitting the database. Otherwise the user is re‑authenticated via the service layer.

---

## 6.3 CRUD Operation Flows (≈ 3 pages)

### 6.3.1 CREATE – DeedEntry (≈ 1 page)

```plantuml
@startuml
actor Browser
participant DeedEntryRestServiceImpl as DeedCtrl
participant DeedEntryServiceImpl as DeedSrv
participant DeedEntryDao as DeedRepo

Browser -> DeedCtrl : POST /uvz/v1/deedentries (DeedDTO)
activate DeedCtrl
DeedCtrl -> DeedSrv : createDeedEntry(DeedDTO)
activate DeedSrv
DeedSrv -> DeedRepo : save(entity)
activate DeedRepo
DeedRepo --> DeedSrv : persisted Entity (id, version=0)
deactivate DeedRepo
DeedSrv --> DeedCtrl : DeedDTO (id, version)
deactivate DeedSrv
DeedCtrl --> Browser : 201 Created + Location: /uvz/v1/deedentries/{id}
deactivate DeedCtrl
@enduml
```

*Notes*
- The controller (`DeedEntryRestServiceImpl`) is the only entry point; it performs **`@Valid`** DTO validation before delegating.
- `DeedEntryServiceImpl` contains the business rule that a newly created deed must have a generated UUID and an initial version of **0**.
- Persistence is handled by `DeedEntryDao` (Spring Data JPA repository).

### 6.3.2 READ – Single Item & Paginated List (≈ 1 page)

```plantuml
@startuml
actor Browser
participant DeedEntryRestServiceImpl as DeedCtrl
participant DeedEntryServiceImpl as DeedSrv
participant DeedEntryDao as DeedRepo

Browser -> DeedCtrl : GET /uvz/v1/deedentries/{id}
activate DeedCtrl
DeedCtrl -> DeedSrv : getDeedEntry(id)
activate DeedSrv
DeedSrv -> DeedRepo : findById(id)
activate DeedRepo
DeedRepo --> DeedSrv : Optional<Entity>
deactivate DeedRepo
DeedSrv --> DeedCtrl : DeedDTO
deactivate DeedSrv
DeedCtrl --> Browser : 200 OK + JSON
deactivate DeedCtrl

Browser -> DeedCtrl : GET /uvz/v1/deedentries?page=0&size=20&sort=id,desc
activate DeedCtrl
DeedCtrl -> DeedSrv : findAll(Pageable)
activate DeedSrv
DeedSrv -> DeedRepo : findAll(Pageable)
activate DeedRepo
DeedRepo --> DeedSrv : Page<Entity>
deactivate DeedRepo
DeedSrv --> DeedCtrl : Page<DeedDTO>
deactivate DeedSrv
DeedCtrl --> Browser : 200 OK + {content, totalElements, totalPages, size, number}
deactivate DeedCtrl
@enduml
```

*Key aspects*
- Pagination is implemented with Spring Data `Pageable`. The response contains the standard pagination envelope.
- Sorting parameters are passed through the query string and mapped automatically by Spring MVC.

### 6.3.3 UPDATE – Optimistic Locking (≈ 1 page)

```plantuml
@startuml
actor Browser
participant DeedEntryRestServiceImpl as DeedCtrl
participant DeedEntryServiceImpl as DeedSrv
participant DeedEntryDao as DeedRepo

Browser -> DeedCtrl : PUT /uvz/v1/deedentries/{id} (DeedDTO with version)
activate DeedCtrl
DeedCtrl -> DeedSrv : updateDeedEntry(id, DeedDTO)
activate DeedSrv
DeedSrv -> DeedRepo : findById(id)
activate DeedRepo
DeedRepo --> DeedSrv : Entity (currentVersion)
deactivate DeedRepo
opt version matches
    DeedSrv -> DeedRepo : save(entity with ++version)
    activate DeedRepo
    DeedRepo --> DeedSrv : persisted Entity
    deactivate DeedRepo
    DeedSrv --> DeedCtrl : DeedDTO (new version)
else version mismatch
    DeedSrv --> DeedCtrl : OptimisticLockException
end
deactivate DeedSrv
DeedCtrl --> Browser : 200 OK (new version) or 409 Conflict
deactivate DeedCtrl
@enduml
```

*Explanation*
- The JPA `@Version` column guarantees that concurrent updates are detected.
- The service checks the incoming version against the persisted one; a mismatch triggers an `OptimisticLockException` which the global exception handler maps to **409 Conflict**.

### 6.3.4 DELETE – Cascade Behaviour (≈ 1 page)

```plantuml
@startuml
actor Browser
participant DeedEntryRestServiceImpl as DeedCtrl
participant DeedEntryServiceImpl as DeedSrv
participant DeedEntryDao as DeedRepo
participant DeedEntryConnectionDao as ConnRepo

Browser -> DeedCtrl : DELETE /uvz/v1/deedentries/{id}
activate DeedCtrl
DeedCtrl -> DeedSrv : deleteDeedEntry(id)
activate DeedSrv
DeedSrv -> ConnRepo : deleteByDeedId(id)   "cascade"
activate ConnRepo
ConnRepo --> DeedSrv : void
deactivate ConnRepo
DeedSrv -> DeedRepo : deleteById(id)
activate DeedRepo
DeedRepo --> DeedSrv : void
deactivate DeedRepo
DeedSrv --> DeedCtrl : void
deactivate DeedSrv
DeedCtrl --> Browser : 204 No Content
deactivate DeedCtrl
@enduml
```

*Rationale*
- `DeedEntry` has a one‑to‑many relationship with `DeedEntryConnection`. The service explicitly removes child rows before deleting the parent to satisfy foreign‑key constraints.
- The controller returns **204 No Content** to indicate successful deletion without a payload.

---

## 6.4 REST API Request Lifecycle (≈ 2 pages)

### 6.4.1 Validation, Serialization, Error Mapping

1. **HTTP request** arrives at a `*RestServiceImpl` controller (e.g., `DeedEntryRestServiceImpl`).
2. Spring MVC binds the JSON payload to a DTO and triggers **Bean Validation** (`@Valid`).
3. Validation errors raise `MethodArgumentNotValidException`.
4. `DefaultExceptionHandler` (a `@ControllerAdvice`) catches the exception and produces a **400 Bad Request** with a JSON body containing field‑level error messages.
5. If validation succeeds, the controller forwards the DTO to the corresponding *Service* bean.
6. Business‑logic exceptions (`EntityNotFoundException`, `OptimisticLockException`, custom `BusinessException`) are also handled by `DefaultExceptionHandler` and mapped to **404**, **409**, or **422** respectively.
7. The service returns a DTO; Spring **Jackson** serializes it to JSON (or XML when `Accept: application/xml`).
8. The response is sent with the appropriate `Content‑Type` header.

### 6.4.2 HTTP Status Code Strategy & Content Negotiation

| Situation | Status Code | Reason |
|-----------|-------------|--------|
| Resource created | **201** | `Location` header points to new URI |
| Successful read | **200** | Standard OK |
| Successful update (return body) | **200** | Updated representation returned |
| Successful update (no body) | **204** | No Content |
| Successful delete | **204** | No Content |
| Validation error | **400** | Bad request, details in error payload |
| Authentication failure | **401** | Missing/invalid JWT |
| Authorization failure | **403** | Insufficient rights |
| Not found | **404** | Entity does not exist |
| Conflict (optimistic lock) | **409** | Version mismatch |
| Unprocessable entity (business rule) | **422** | Domain‑specific validation |
| Server error | **500** | Unexpected exception |

**Content Negotiation**
- Controllers declare `produces = {"application/json", "application/xml"}`.
- Spring selects the representation based on the `Accept` header.
- The same DTO classes are annotated with `@JsonInclude` and `@XmlRootElement` to guarantee identical field sets for both formats.
- If the client requests an unsupported media type, the framework returns **406 Not Acceptable**.

---

## 6.5 Component Inventory (Supporting Table)

| Stereotype | Example Component | Package (if known) | Primary Responsibility |
|------------|-------------------|--------------------|------------------------|
| **controller** | `DeedEntryRestServiceImpl` | – | Exposes CRUD REST endpoints for deed entries |
|  | `JsonAuthorizationRestServiceImpl` | – | Handles login / token refresh |
| **service** | `DeedEntryServiceImpl` | – | Business rules, optimistic locking, cascade delete |
|  | `ActionServiceImpl` | – | User authentication & authority lookup |
| **repository** | `DeedEntryDao` | – | JPA repository for `DeedEntry` entity |
|  | `ActionDao` | – | Access to user table for authentication |
| **entity** | `DeedEntry` (360 entities total) | – | Domain object representing a deed |
| **configuration** | `TokenAuthenticationRestTemplateConfigurationSpringBoot` | – | Configures RestTemplate with client certificate |

The table lists a representative subset; the full list (32 controllers, 184 services, 38 repositories) is available in the architecture facts.

---

*All component names, relationships and endpoint paths are taken directly from the architecture facts and the generated REST endpoint list. The diagrams therefore reflect the exact runtime behaviour of the UVZ system.*
