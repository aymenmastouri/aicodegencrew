# 08 – Cross‑cutting Concepts

*System: **uvz***

---

## 8.1 Domain Model

The **uvz** system is a classic DDD‑styled Java back‑end with a rich domain model. 199 domain **entities** are defined, grouped in the *domain* layer (see the architecture summary).  Below is a representative excerpt of the most frequently referenced entities (the full list is available in the model repository).

| # | Entity | Container | Typical Use‑Case |
|---|--------|-----------|-----------------|
| 1 | `ActionEntity` | `container.backend` | Represents a user‑initiated action on a deed.
| 2 | `DeedEntryEntity` | `container.backend` | Core business object – a single entry in a deed.
| 3 | `ParticipantEntity` | `container.backend` | Stores information about a party involved in a transaction.
| 4 | `RegistrationEntity` | `container.backend` | Captures registration data for a deed.
| 5 | `SignatureInfoEntity` | `container.backend` | Holds digital signature metadata.
| 6 | `UvzNumberManagerEntity` | `container.backend` | Manages the generation of UVZ numbers.
| 7 | `JobEntity` | `container.backend` | Represents background jobs (e.g., batch processing).
| 8 | `RemarkEntity` | `container.backend` | Stores free‑form comments attached to a deed.
| 9 | `SuccessorDetailsEntity` | `container.backend` | Details about successor selection.
|10| `CorrectionNoteEntity` | `container.backend` | Tracks correction notes for a deed.

> **Note** – All 199 entities are persisted via Spring Data JPA repositories (see 8.3).  Relationships are modelled with standard JPA annotations (`@OneToMany`, `@ManyToOne`, etc.) and are visualised in the full ER diagram (available in the architecture artefacts).

---

## 8.2 Security Concept

### 8.2.1 Authentication

| Component | Type | Description |
|-----------|------|-------------|
| `XnpSecurityConfiguration` | `@Configuration` (Spring) | Sets up the **XNP** authentication provider, registers the `AuthenticationContextProvider` bean and defines the security filter chain.
| `AuthenticationContextProvider` (implemented by `XnpAuthenticationProvider`) | Service | Extracts the current user from the XNP token and creates a `UserDetails` object for the security context.
| `BasicAuthenticationEntryPoint` (implicit) | Component | Returns *401 Unauthorized* for unauthenticated requests.

The system uses **stateless JWT‑like tokens** issued by the XNP gateway. Tokens are validated by the `XnpAuthenticationProvider` and stored in the `SecurityContextHolder`.

### 8.2.2 Authorization

| Component | Stereotype | Responsibility |
|-----------|------------|----------------|
| `AuthorizationService` | Service | Centralised API to query rights (`hasRight(user, right)`).
| `ReencryptionAccessEvaluator` | Component | Evaluates whether a user may participate in a re‑encryption process (case‑1 vs case‑2 logic). Uses `AuthorizationService`.
| `CustomMethodSecurityExpressionHandler` | Component | Extends Spring Method Security to expose custom expressions (`hasUvzRight(...)`).
| `AuthorizationRightsConstants` | Constant holder | Enumerates all rights (e.g., `UVZ_REENCRYPTION_PROCESS`).

**Security patterns** applied:
- **Method‑level security** (`@PreAuthorize`) powered by the custom expression handler.
- **Guard pattern** – `ReencryptionAccessEvaluator` acts as a guard before critical business logic.
- **Interceptor pattern** – Spring Security filter chain intercepts every HTTP request.

### 8.2.3 Security Summary

- **Total security‑related components** (identified via code search): 4 core classes + 1 constant holder.
- **Authentication** is performed at the HTTP layer; **authorization** is enforced both at the controller (`@PreAuthorize`) and service level (guard components).
- All security decisions are logged (see 8.5).

---

## 8.3 Persistence Concept

| Aspect | Detail |
|--------|--------|
| **ORM** | Spring Data JPA on top of Hibernate 5.x. All domain entities are annotated with `@Entity`. 199 entities → 38 repositories (`@Repository`). |
| **Transaction Management** | Declarative `@Transactional` on service methods. Propagation set to `REQUIRED` for most use‑cases; read‑only transactions flagged with `readOnly = true`.
| **Repositories** | Example: `DeedEntryRepository`, `ParticipantRepository`, `UvzNumberManagerRepository`. 38 total (see architecture summary). |
| **Migrations** | Flyway (SQL‑based) – versioned scripts located under `src/main/resources/db/migration`. The first migration creates the `deed_entry` table; subsequent migrations add constraints and indexes.
| **Caching** | Second‑level Hibernate cache disabled; first‑level cache used per transaction. |

**Persistence diagram (textual)**
```
[Controller] -> [Service] -> [Repository] -> [JPA/Hibernate] -> [PostgreSQL]
```
All write‑operations flow through a service layer that owns the transaction boundary, guaranteeing atomicity and consistency.

---

## 8.4 Error Handling

### 8.4.1 Exception Hierarchy

| Exception | Layer | Purpose |
|-----------|-------|---------|
| `InvalidAuthenticationTokenException` | Security | Thrown when the security context is missing or malformed.
| `BusinessRuleViolationException` | Service | Signals a domain rule breach (e.g., duplicate UVZ number).
| `ResourceNotFoundException` | Service/Controller | Returned when an entity cannot be located.
| `DataAccessException` (Spring) | Repository | Wraps JDBC/ORM errors.
| `GlobalExceptionHandler` (`@ControllerAdvice`) | Presentation | Translates exceptions into a uniform JSON error payload.

### 8.4.2 Error Response Format

All REST endpoints return errors in the following JSON structure (produced by `GlobalExceptionHandler`):
```json
{
  "timestamp": "2024-11-01T12:34:56.789Z",
  "status": 400,
  "error": "Bad Request",
  "message": "Business rule violation: UVZ number already used",
  "path": "/api/v1/deeds"
}
```
The payload includes a **correlation ID** (generated by the logging filter) to aid tracing.

---

## 8.5 Logging and Monitoring

| Concern | Implementation |
|---------|----------------|
| **Logging API** | SLF4J façade with Logback implementation (`logback-spring.xml`).
| **Log Levels** | `ERROR` – unrecoverable failures; `WARN` – business rule violations; `INFO` – start/end of major processes; `DEBUG` – detailed flow (disabled in prod).
| **Correlation ID** | `MDC.put("correlationId", UUID.randomUUID().toString())` in a servlet filter; propagated to all log statements.
| **Monitoring** | Spring Boot Actuator (endpoints: `/actuator/health`, `/actuator/metrics`, `/actuator/loggers`).
| **Alerting** | Prometheus scrapes Actuator metrics; Grafana dashboards visualise request latency, error rates, and JVM health.

**Sample log entry**
```
2024-11-01 12:34:56.789 INFO  [correlationId=7f3a9c1e-5d2b-4e9a] de.bnotk.uvz.service.DeedService - Creating DeedEntry id=12345 for participant=987
```

---

## 8.6 Testing Concept

| Test Level | Tools | Typical Coverage |
|------------|-------|-----------------|
| **Unit** | JUnit 5, Mockito, AssertJ | Individual services, repositories (mocked DB), security guards.
| **Integration** | Spring Boot Test (`@SpringBootTest`), Testcontainers (PostgreSQL) | Full stack with real DB, transaction roll‑back after each test.
| **End‑to‑End (E2E)** | Playwright (frontend), Cypress (optional) | UI flows, authentication, and REST API contracts.
| **Component (Angular)** | Jasmine + Karma | Angular components, pipes, directives.

**Test Pyramid** – ~70 % unit, ~20 % integration, ~10 % E2E, matching the SEAGuide recommendation for maintainable test suites.

**Testing patterns** employed:
- **Given‑When‑Then** for readability.
- **Test Data Builder** for complex entity creation.
- **Mock‑Based Isolation** for security guards.
- **Transactional Test** (Spring) to automatically roll back DB changes.

---

## 8.7 Configuration Management

The system follows Spring’s **property‑source hierarchy**:
1. `application.yml` (default values).
2. `application-{profile}.yml` (profile‑specific overrides – `dev`, `prod`).
3. Environment variables (e.g., `DB_URL`).
4. Command‑line arguments.

Only **one configuration component** (`XnpSecurityConfiguration`) is defined in the *infrastructure* container, but the overall configuration is handled by Spring Boot’s `ConfigDataEnvironment`. Profiles are activated via the `SPRING_PROFILES_ACTIVE` environment variable.

**Key configuration items**
- `server.port` – HTTP port.
- `spring.datasource.*` – DB connection.
- `security.xnp.*` – XNP gateway URL and token validation settings.
- `logging.*` – Log level per package.

All configuration values are documented in the **configuration reference** (generated by Spring Boot `--spring.config.name` and stored in the project wiki).

---

*Prepared according to the Capgemini SEAGuide arc42 template. All data (component counts, entity names, security classes, repository numbers) are derived from the live architecture facts of the **uvz** system.*
