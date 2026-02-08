# Developer Knowledge Base

Strukturiertes Wissen für AI-Agenten in Entwicklungsphasen (Phase 5+).
Ergänzt die statische Architektur-Analyse um dynamisches Entwickler-Know-how.

---

## 1. Feature-Entwicklung E2E

### Backend-Flow
Entity → Repository → Service → Controller → DTO

### Frontend-Flow
Model → Service → Component → Template → Routing

### Test-Flow
Unit Test → Integration Test → E2E Test (Cucumber/Playwright)

### Deployment-Flow
Feature-Branch → Pull Request → CI Pipeline → Code Review → Merge → Staging → Production

### Typische Schritte für ein neues Feature
1. DB-Migration erstellen (Flyway/Liquibase)
2. JPA-Entity anlegen/erweitern
3. Repository-Interface definieren
4. Service-Logik implementieren
5. REST-Controller mit DTO erstellen
6. Frontend-Model und Service anlegen
7. Angular-Component mit Template erstellen
8. Unit-Tests schreiben
9. Integration-Tests ergänzen
10. E2E-Test (.feature) für Akzeptanz

---

## 2. Bug-Fixing-Patterns

### Root Cause Identifikation
- Fehlermeldung analysieren → Exception-Typ identifizieren
- Stacktrace lesen: Von unten nach oben → erste eigene Klasse finden
- Logging prüfen: `application.log`, Browser Console, Network-Tab
- Reproduzieren: Welcher Endpoint? Welche Eingabedaten?

### Logging-Strategie (Wo schauen?)
- Backend: `target/logs/`, Spring Boot Actuator `/actuator/health`
- Frontend: Browser Developer Tools → Console + Network
- E2E: Playwright Trace Viewer, Cucumber Report
- Datenbank: Slow Query Log, Connection Pool Metriken

### Häufige Fehlerquellen nach Stereotype
| Stereotype | Typische Fehler |
|---|---|
| Controller | Falsche HTTP-Methode, fehlende Validierung, falscher Status-Code |
| Service | Transaction-Boundary falsch, fehlende @Transactional |
| Repository | N+1 Queries, falsche JPQL/Native Query |
| Entity | Lazy Loading außerhalb Transaction, Mapping-Fehler |
| Component (Angular) | Change Detection, Subscription-Leak, async Pipe fehlt |
| Guard | Fehlende Rollenprüfung, Race Condition bei Auth |

---

## 3. Rollen & Rechte

### Typische Rollen-Struktur
- ADMIN: Vollzugriff auf alle Funktionen
- USER: Standard-Benutzerrechte
- READONLY: Nur lesender Zugriff
- SYSTEM: Interne Service-Kommunikation

### Security-Konfiguration identifizieren
1. `SecurityConfig` / `WebSecurityConfigurerAdapter` suchen
2. `@PreAuthorize`, `@Secured`, `@RolesAllowed` an Controllern prüfen
3. Angular Route Guards prüfen (`canActivate`)
4. `application.yml` → `spring.security.*` Konfiguration

### Method-Level Security Pattern
```java
@PreAuthorize("hasRole('ADMIN')")
public void deleteUser(Long id) { ... }

@PreAuthorize("hasRole('USER') or hasRole('ADMIN')")
public UserDTO getProfile() { ... }
```

---

## 4. Test-Strategien

### Unit Tests
- Framework: JUnit 5 + Mockito
- Pattern: `*Test.java` im `src/test/java`
- Fokus: Einzelne Service-Methode, isoliert mit Mocks
- Konvention: `given_when_then` Methodennamen

### Integration Tests
- Framework: `@SpringBootTest`, `@DataJpaTest`, `@WebMvcTest`
- Pattern: `*IT.java` oder `@SpringBootTest` annotiert
- Fokus: Zusammenspiel mehrerer Schichten mit echtem Context

### E2E Tests (Cucumber/Gherkin)
- Dateien: `*.feature` in `e2e-xnp/` und `frontend/e2e/`
- Tags: `@smoke`, `@regression`, `@wip`
- Sprache: Oft Deutsch (Gegeben/Wenn/Dann) oder Englisch (Given/When/Then)
- Step Definitions: TypeScript in `.ts` Dateien

### Frontend Tests (Playwright/Jasmine)
- Dateien: `*.spec.ts`, `*.e2e-spec.ts`
- Framework: Playwright für E2E, Jasmine/Jest für Unit
- Fokus: Component-Rendering, User-Interaktion, HTTP-Mocking

### XNP Tests
- Fachliche Akzeptanztests
- Prüfen Business-Szenarien end-to-end
- Oft domänenspezifische Sprache in .feature-Dateien

---

## 5. Konzepte & Solution-Strategien

### Job-Aktionen
- Batch-Jobs: Spring Batch / Quartz Scheduler
- Async-Verarbeitung: `@Async`, `CompletableFuture`
- Scheduled Tasks: `@Scheduled(cron = "...")` für periodische Aufgaben
- Event-basiert: `@EventListener`, `ApplicationEventPublisher`

### Handover-Prozesse
- Workflow-Status-Änderungen über State Machine oder Enum-basiert
- Typischer Flow: DRAFT → SUBMITTED → IN_REVIEW → APPROVED → COMPLETED
- Benachrichtigungen bei Statuswechsel (E-Mail, Notification-Service)
- Audit-Trail: Wer hat wann welchen Status gesetzt?

### Fachliche Prozesse identifizieren
1. Status-Enums suchen → definieren den Workflow
2. `*WorkflowService`, `*ProcessService` → Orchestrierung
3. BPMN-Dateien (`.bpmn`) → visueller Prozessflow
4. Cucumber-Features → fachliche Akzeptanzkriterien

### Daten-Import/Export
- Import: CSV/XML → Validierung → Transformation → Persistierung
- Export: DB-Query → Transformation → CSV/PDF/Excel
- Batch-Verarbeitung für große Datenmengen
- Error-Handling: Partial Success, Fehler-Report

### Konfigurationsmanagement
- `application.yml` / `application-{profile}.yml` für Spring
- `environment.ts` für Angular
- Feature-Flags für schrittweise Aktivierung
- Secrets in Vault/Environment-Variablen, NICHT im Code

---

## 6. Häufige Pitfalls & Lösungen

### Transaction-Management
- **Problem**: `@Transactional` fehlt → Lazy Loading Exception
- **Lösung**: Service-Methoden mit `@Transactional` annotieren
- **Achtung**: `@Transactional` auf private Methoden wirkt NICHT (Proxy-basiert)

### N+1 Query-Problem
- **Problem**: JPA lädt Relationen einzeln → 100 Entities = 101 Queries
- **Lösung**: `@EntityGraph`, `JOIN FETCH` in JPQL, `@BatchSize`

### Angular Change Detection
- **Problem**: View aktualisiert sich nicht nach async Operation
- **Lösung**: `ChangeDetectorRef.detectChanges()`, async Pipe, OnPush-Strategie

### Circular Dependencies
- **Problem**: Service A → Service B → Service A
- **Lösung**: Event-basierte Kommunikation, Mediator-Pattern, `@Lazy`

### CORS-Fehler
- **Problem**: Frontend (localhost:4200) → Backend (localhost:8080) blockiert
- **Lösung**: `@CrossOrigin` oder globale CORS-Config in `SecurityConfig`

### Memory Leaks (Frontend)
- **Problem**: Subscriptions werden nicht aufgeräumt
- **Lösung**: `takeUntil(destroy$)`, async Pipe, `ngOnDestroy`

---

## 7. Kontextidentifikation für AI-Agent

### Wie finde ich den richtigen Code zu einem Ticket?
1. **Endpoint identifizieren**: URL aus Frontend-Network-Tab → Controller finden
2. **Service-Kette verfolgen**: Controller → Service → Repository
3. **Entity identifizieren**: Welche Tabelle ist betroffen?
4. **Tests finden**: `*Test.java` mit gleichem Präfix wie betroffene Klasse
5. **E2E-Feature finden**: `.feature`-Datei mit relevantem Szenario-Name

### Wie identifiziere ich betroffene Dateien bei einer Änderung?
1. **Vertikaler Schnitt**: Entity → Repository → Service → Controller → DTO → Frontend
2. **Tests**: Unit-Test + Integration-Test + ggf. E2E-Feature anpassen
3. **Konfiguration**: `application.yml`, Security-Config, DB-Migration
4. **Dokumentation**: API-Docs (Swagger), Architektur-Docs (arc42)
