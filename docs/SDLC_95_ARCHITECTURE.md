# SDLC 95% Automation - Architektur & Strategie

**Ziel:** 95% der Software-Entwicklungsaufgaben durch KI-gestützte Automatisierung  
**Stand:** 2026-02-05  
**Autor:** Architecture Session with Claude Opus

---

## 🎯 Vision

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SDLC 95% AUTOMATION                                 │
│                                                                             │
│   Ticket/Anforderung                                                        │
│          ↓                                                                  │
│   ┌─────────────────────────────────────────────────────────┐              │
│   │              KNOWLEDGE LAYER                             │              │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐              │              │
│   │  │ Code     │  │ Domain   │  │ History  │              │              │
│   │  │ Facts    │  │ Rules    │  │ Patterns │              │              │
│   │  └──────────┘  └──────────┘  └──────────┘              │              │
│   └─────────────────────────────────────────────────────────┘              │
│          ↓                                                                  │
│   ┌─────────────────────────────────────────────────────────┐              │
│   │              REASONING LAYER (LLM + RAG)                 │              │
│   │  • Verstehen was zu tun ist                             │              │
│   │  • Entscheiden wie es zu tun ist                        │              │
│   │  • Generieren von Code/Tests/Doku                       │              │
│   └─────────────────────────────────────────────────────────┘              │
│          ↓                                                                  │
│   ┌─────────────────────────────────────────────────────────┐              │
│   │              EXECUTION LAYER                             │              │
│   │  • Code schreiben                                        │              │
│   │  • Tests ausführen                                       │              │
│   │  • Review durchführen                                    │              │
│   │  • Deployment triggern                                   │              │
│   └─────────────────────────────────────────────────────────┘              │
│          ↓                                                                  │
│   ┌─────────────────────────────────────────────────────────┐              │
│   │              FEEDBACK LAYER                              │              │
│   │  • Aus Fehlern lernen                                   │              │
│   │  • Patterns erkennen                                    │              │
│   │  • Knowledge Base updaten                               │              │
│   └─────────────────────────────────────────────────────────┘              │
│          ↓                                                                  │
│   Fertiges Feature / Bugfix                                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Architektur-Komponenten

### Layer 1: Knowledge Layer (Wissen)

| Komponente | Funktion | Status |
|------------|----------|--------|
| **Code Facts** | Struktur, Components, Relations | ✅ Phase 1 (80%) |
| **Domain Rules** | Business-Logik, Validierungen | ❌ Fehlt |
| **History Patterns** | Wie wurden ähnliche Bugs gefixt? | ❌ Fehlt |
| **Test Patterns** | Bestehende Test-Strukturen | ❌ Fehlt |
| **Code Templates** | Bewährte Code-Muster | ❌ Fehlt |

#### Was fehlt für 95%:

```yaml
Domain Knowledge Base:
  - Business Rules aus Code extrahieren
  - Validierungen dokumentieren
  - Workflow-Regeln erfassen
  - Fachliche Constraints

History Knowledge:
  - Git History analysieren
  - Bug-Fix Patterns erkennen
  - "Wie wurde X das letzte Mal gelöst?"
  - Code Review Feedback

Template Library:
  - REST Controller Template
  - Service Template
  - Repository Template
  - Test Templates (Unit, Integration, E2E)
  - Angular Component Templates
```

### Layer 2: Reasoning Layer (Denken)

| Komponente | Funktion | Status |
|------------|----------|--------|
| **Task Understanding** | Was soll gemacht werden? | ❌ Fehlt |
| **Impact Analysis** | Was ist betroffen? | 🔶 Teilweise (Relations) |
| **Solution Planning** | Wie lösen wir das? | ❌ Fehlt |
| **Code Generation** | Code schreiben | ❌ Fehlt |
| **Test Generation** | Tests generieren | ❌ Fehlt |

#### Reasoning Pipeline:

```
Input: "Füge Validierung für IBAN hinzu"
                    ↓
┌─────────────────────────────────────────────────────────┐
│ 1. TASK UNDERSTANDING                                   │
│    - Was ist eine IBAN Validierung?                     │
│    - Welche Felder sind betroffen?                      │
│    - Gibt es ähnliche Validierungen im Code?            │
│    → RAG: Suche "validation", "IBAN", "BIC"            │
└─────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────┐
│ 2. IMPACT ANALYSIS                                      │
│    - Welche Services nutzen IBAN?                       │
│    - Welche DTOs haben IBAN Felder?                     │
│    - Welche Tests müssen angepasst werden?              │
│    → Facts: Components + Relations durchsuchen          │
└─────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────┐
│ 3. SOLUTION PLANNING                                    │
│    - Backend: Validator Klasse erstellen                │
│    - DTO: @Valid Annotation hinzufügen                  │
│    - Frontend: Validation Message anzeigen              │
│    - Tests: Unit + Integration Tests                    │
│    → Templates + Patterns verwenden                     │
└─────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────┐
│ 4. CODE GENERATION                                      │
│    - IbanValidator.java generieren                      │
│    - DTO aktualisieren                                  │
│    - Angular Validator hinzufügen                       │
│    - Tests generieren                                   │
│    → LLM + Templates + Context                          │
└─────────────────────────────────────────────────────────┘
```

### Layer 3: Execution Layer (Handeln)

| Komponente | Funktion | Status |
|------------|----------|--------|
| **File Writer** | Code in Dateien schreiben | ✅ Vorhanden |
| **Git Operations** | Branch, Commit, Push | 🔶 Basis vorhanden |
| **Test Runner** | Tests ausführen | ❌ Fehlt |
| **Build Trigger** | CI/CD anstoßen | ❌ Fehlt |
| **Review Bot** | Code Review | ❌ Fehlt |

#### Execution Pipeline:

```yaml
Execution Steps:
  1. Branch erstellen:
     - git checkout -b feature/TICKET-123-iban-validation
  
  2. Code schreiben:
     - Generierte Dateien speichern
     - Bestehende Dateien modifizieren
  
  3. Tests ausführen:
     - Unit Tests lokal
     - Bei Fehler: Fix generieren
  
  4. Commit & Push:
     - Semantic Commit Message
     - Push to remote
  
  5. MR/PR erstellen:
     - Description generieren
     - Reviewer zuweisen
  
  6. CI/CD abwarten:
     - Pipeline Status überwachen
     - Bei Fehler: Fix generieren
```

### Layer 4: Feedback Layer (Lernen)

| Komponente | Funktion | Status |
|------------|----------|--------|
| **Error Analysis** | Warum ist Test fehlgeschlagen? | ❌ Fehlt |
| **Fix Learning** | Wie wurde es manuell gefixt? | ❌ Fehlt |
| **Pattern Mining** | Wiederkehrende Lösungen | ❌ Fehlt |
| **Quality Metrics** | Erfolgsrate tracken | ❌ Fehlt |

#### Feedback Loop:

```
Generated Code
      ↓
   Tests Run
      ↓
  ┌───────┐
  │ Pass? │──Yes──→ Done ✅
  └───────┘
      │
      No
      ↓
┌─────────────────────────────────────┐
│ AUTOMATIC FIX ATTEMPT               │
│ - Error analysieren                 │
│ - Fix generieren                    │
│ - Tests erneut laufen               │
│ - Max 3 Versuche                    │
└─────────────────────────────────────┘
      │
      ↓ (nach 3 Fehlschlägen)
┌─────────────────────────────────────┐
│ HUMAN REVIEW REQUIRED               │
│ - Entwickler fixt manuell           │
│ - Fix wird in Knowledge Base        │
│   aufgenommen für nächstes Mal      │
└─────────────────────────────────────┘
```

---

## 📊 Phasen-Roadmap

### Phase 1: Foundation (Aktuell - 80%)
```
✅ Code Extraktion (733 Components)
✅ Relations (169)
✅ Interfaces (125)
🔶 Relation Resolution (54% → Ziel 85%)
🔶 Endpoint Flows (0 → Ziel 50+)
```

### Phase 2: Documentation (Next)
```
❌ Arc42 Generation
❌ C4 Diagrams
❌ API Documentation
❌ Component Documentation
```

### Phase 3: Understanding (Reasoning)
```
❌ Task Parser (Ticket → Aufgaben)
❌ Impact Analyzer (Was ist betroffen?)
❌ Solution Planner (Wie lösen?)
❌ RAG Integration (Context finden)
```

### Phase 4: Generation
```
❌ Code Templates
❌ Code Generator
❌ Test Generator
❌ Migration Generator
```

### Phase 5: Execution
```
❌ Git Automation
❌ Test Runner Integration
❌ CI/CD Integration
❌ MR/PR Automation
```

### Phase 6: Learning
```
❌ Error Analysis
❌ Fix Pattern Mining
❌ Quality Dashboard
❌ Continuous Improvement
```

---

## 🔧 Technische Anforderungen

### 1. Knowledge Storage

```yaml
ChromaDB (Vorhanden):
  - Code Chunks
  - Embeddings für Suche

Neue Datenstrukturen:
  - Domain Rules (JSON/YAML)
  - Code Templates (Jinja2/Mustache)
  - Fix History (SQLite/JSON)
  - Quality Metrics (Prometheus?)
```

### 2. LLM Integration

```yaml
Aktuell:
  - GPT via API (gpt-4o-mini default)
  - CrewAI für Orchestration

Für 95%:
  - Größeres Context Window (128K+)
  - Function Calling für Tools
  - Structured Output (JSON Mode)
  - Streaming für lange Generierungen
```

### 3. Tool Integration (MCP)

```yaml
Benötigte MCP Server:
  
  jira-mcp:
    - Tickets lesen
    - Status updaten
    - Kommentare schreiben
  
  gitlab-mcp:
    - Branches erstellen
    - MRs erstellen
    - Pipeline Status
    - Code Review
  
  test-runner-mcp:
    - Unit Tests ausführen
    - Coverage Report
    - Test Results parsen
  
  build-mcp:
    - Gradle/Maven build
    - npm build
    - Build Errors parsen
```

### 4. Human-in-Loop

```yaml
Review Points:
  - Nach Solution Planning (vor Code Gen)
  - Nach Code Generation (vor Commit)
  - Nach Test Failures (wenn Auto-Fix scheitert)
  - Nach MR Approval Request

Approval Modes:
  - MANUAL: Alles manuell approven
  - SEMI: Nur bei Unsicherheit
  - AUTO: Nur bei Fehlern stoppen
```

---

## 📈 Erfolgsmetriken

| Metrik | Aktuell | Ziel Phase 2 | Ziel 95% |
|--------|---------|--------------|----------|
| Code Understanding | 80% | 90% | 98% |
| Impact Analysis | 20% | 60% | 90% |
| Code Generation | 0% | 30% | 85% |
| Test Generation | 0% | 20% | 80% |
| Auto-Fix Rate | 0% | 10% | 60% |
| End-to-End Automation | 0% | 5% | 50% |
| **Gesamt Effizienz** | **20%** | **40%** | **95%** |

### Definition "95% Automation":

```
95% bedeutet NICHT:
  ❌ Kein Mensch mehr nötig
  ❌ Alles vollautomatisch
  ❌ Perfekter Code

95% bedeutet:
  ✅ 95% weniger manuelle Tipparbeit
  ✅ 95% der Routine-Tasks automatisiert
  ✅ Mensch reviewed und approved
  ✅ KI macht Vorschläge, Mensch entscheidet
```

---

## 🚀 Nächste Schritte

### Kurzfristig (Diese Woche)
1. Phase 1 Relation Resolution fixen (54% → 85%)
2. Endpoint Flows enablen
3. Tables/Migrations ins Model

### Mittelfristig (Nächste 2 Wochen)
1. Phase 2 starten (Arc42/C4 Generation)
2. RAG Pipeline mit Facts aufbauen
3. Erste Code Templates erstellen

### Langfristig (Nächster Monat)
1. Task Understanding (Ticket → Aufgaben)
2. Code Generation Pipeline
3. Test Generation
4. GitLab MCP Integration

---

## 💡 Architektur-Entscheidungen

### ADR-001: Deterministisch vor LLM
**Entscheidung:** Phase 1 bleibt 100% deterministisch (Regex, AST)
**Begründung:** Reproduzierbar, schnell, keine API-Kosten
**Status:** Accepted ✅

### ADR-002: RAG vor Fine-Tuning
**Entscheidung:** Facts als Context für generisches LLM statt Custom Model
**Begründung:** Flexibler, keine Trainingskosten, immer aktuelle Daten
**Status:** Accepted ✅

### ADR-003: Human-in-Loop
**Entscheidung:** Mensch reviewed/approved in kritischen Punkten
**Begründung:** 95% Automation ≠ 0% Human, Qualitätssicherung
**Status:** Accepted ✅

### ADR-004: MCP für externe Tools
**Entscheidung:** MCP Server für Jira, GitLab, CI/CD
**Begründung:** Standardisiert, erweiterbar, VS Code integriert
**Status:** Proposed 📋

---

## 📚 Referenzen

- [AI_SDLC_ARCHITECTURE.md](AI_SDLC_ARCHITECTURE.md) - Ursprüngliche Architektur
- [PHASE1_TODO.md](PHASE1_TODO.md) - Aktuelle Phase 1 TODOs
- [SCALING_STRATEGIES.md](SCALING_STRATEGIES.md) - Skalierungsstrategien
