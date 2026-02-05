# SDLC-Automatisierung mit CrewAI (On-Prem) – Enterprise Blueprint

> **Auch verfuegbar in:** [Englisch (English)](SDLC_BLUEPRINT.md)

## Vision

Einen moeglichst grossen Teil des **Software Development Lifecycle (SDLC)** mit **CrewAI** automatisieren – inklusive Ticket/Spec, Design/ADR, Implementierung, Tests, Review, Doku und Release Notes – **mit menschlichen Gates** fuer Qualitaet und Verantwortung.

> Realistische Erwartung: **Nicht 100% "autonom bis Prod"**, aber **80/20** ist machbar, wenn du LLM + deterministische Tools + Policies kombinierst.

---

## Kernprinzip: CrewAI orchestriert, Tools sichern Fakten

**CrewAI** ist die Orchestrierungsschicht (Rollen/Agents + Pipeline/Tasks).  
Fuer Verlaesslichkeit brauchst du **deterministische Tools** (Build, Tests, Lint, Repo-Scan, Security-Scan, Git Diff, Jira/Confluence APIs).  
Das LLM (z.B. **gpt-oss-120b**, GPT-4, Claude) wird primaer fuer **Synthese und Text/Code-Entwuerfe** genutzt.

---

## 4-Layer Architektur-Modell

> **Referenz:** [AI_SDLC_ARCHITECTURE.md](AI_SDLC_ARCHITECTURE.md) | [Diagramme](diagrams/)

| Layer | Phasen | Zweck | LLM benoetigt | Status |
|-------|--------|-------|---------------|--------|
| **KNOWLEDGE** | 0-1 | Deterministische Fakten-Extraktion | Nein | IMPLEMENTIERT |
| **REASONING** | 2-3 | LLM-gestuetzte Analyse und Synthese | Ja | TEILWEISE |
| **EXECUTION** | 4-6 | Code-Generierung und Deployment | Ja | GEPLANT |
| **FEEDBACK** | 7 | Kontinuierliches Lernen und Qualitaet | Ja | GEPLANT |

---

## Was sehr gut automatisierbar ist (80/20)

### 1) Intake - Ticket/Spec
- Aus Texten (Jira/Teams/Slack/Email): Problem, Scope, Out-of-scope
- **Akzeptanzkriterien (ACs)** + DoD-Vorschlag
- Risiko- und Abhaengigkeitsliste

### 2) Design & Architektur-Artefakte
- ADR-Entwurf (Optionen, Entscheidung, Konsequenzen)
- C4-Beschreibungen (Context/Container/Component)
- API-Contract-Draft (OpenAPI)
- Datenmodell-Draft (Tabellen/Beziehungen)

### 3) Implementierung
- Code-Gerueste, Feature-Implementierung in kleinen Inkrementen
- Refactoring-Vorschlaege
- Standardisierte Commit- und PR-Beschreibungen

### 4) Testing
- Unit-Tests, Contract-Tests, Testdaten
- Identifikation fehlender Edge-Cases

### 5) Code Review & Qualitaet
- Review-Kommentare, Risiken, "smells"
- Security-/Performance-Checklisten (Hinweise, keine Freigabe)

### 6) Dokumentation
- README, Confluence-Seiten, Architektur-Notizen
- Release Notes/Changelog-Entwuerfe

### 7) DevOps/CI
- Pipeline-YAML-Vorschlaege
- Helm/K8s-Manifeste (mit Regeln/Policies)
- Observability-Snippets (Health, Metrics, Logs)

---

## Was nur teilweise geht (und Gates braucht)

### Debugging mit echter Laufzeit
AI hilft stark **mit Logs/Traces/Metrics**, aber braucht echte Observability-Daten und Repro-Schritte.

### Security & Compliance
AI kann pruefen/flaggen – **Freigabe bleibt menschlich** (Governance, Audit).

### Fachlichkeit & Priorisierung
Requirements-Interpretation, Priorisierung und Risikoentscheidungen bleiben Team/PO-Verantwortung.

### Autonomes Mergen ohne Review
Nicht empfohlen. Nutze Policies/Gates (Tests gruen, Security-Scan, Review).

---

## Empfohlene End-to-End Pipeline

```
+------------------------------------------------------------------+
|  LAYER 1: KNOWLEDGE (Deterministisch, Kein LLM)                  |
+------------------------------------------------------------------+
|  Phase 0: Indexing          Phase 1: Architecture Facts          |
|  - ChromaDB Vector Store    - 10 Collectors (Spring, Angular)    |
|  - File Discovery           - 733 Komponenten extrahiert         |
|  - Code Chunking            - 125 Interfaces, 169 Relationen     |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|  LAYER 2: REASONING (LLM-gestuetzt)                              |
+------------------------------------------------------------------+
|  Phase 2: Synthese          Phase 3: Task Understanding          |
|  - C4 Diagramme             - Issue-Analyse                      |
|  - arc42 Dokumentation      - Scope-Bestimmung                   |
|  - Qualitaetsbewertung      - Impact-Analyse                     |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|  LAYER 3: EXECUTION (LLM-gestuetzt)                              |
+------------------------------------------------------------------+
|  Phase 4: CodeGen    Phase 5: Testing    Phase 6: Deploy         |
|  - Pattern-konform   - Unit Tests        - PR-Erstellung         |
|  - Kleine Inkremente - Integration       - CI-Validierung        |
|  - Refactoring       - Edge Cases        - Merge-Vorbereitung    |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|  LAYER 4: FEEDBACK (Kontinuierlich)                              |
+------------------------------------------------------------------+
|  Phase 7: Learning                                               |
|  - Qualitaetsmetriken sammeln                                    |
|  - Pattern-Lernen aus erfolgreichen Aenderungen                  |
|  - Knowledge Base Updates                                        |
+------------------------------------------------------------------+
        |                                                    ^
        +----------------------------------------------------+
                         Feedback Loop
```

**Menschliches Gate**: Review/Approval - Merge/Release

---

## Agent-Struktur (Minimal-Setup: 5 Agents)

| Agent | Verantwortung | Layer |
|-------|---------------|-------|
| **Analyst** | Issue - Spec + ACs | Reasoning |
| **Engineer** | Code/Refactor | Execution |
| **Tester** | Tests/Regression | Execution |
| **Reviewer** | Review + Checklisten | Execution |
| **DocWriter** | Docs/Release Notes | Execution |

---

## Voraussetzungen fuer gute Ergebnisse

### 1) Kontext-Strategie (Repo ist zu gross)
- **RAG/Indexing** oder gezielte Code-Auszuege
- Tasks in kleine Schritte splitten (keine "mega prompts")

### 2) Guardrails / Policies
- "Keine APIs erfinden"
- Coding Standards / Architekturregeln
- "Nur Aenderungen innerhalb definiertem Scope"
- "Wenn unsicher: Frage stellen / TODO markieren"

### 3) Deterministische Qualitaetssignale
- `lint/format` muss gruen sein
- `unit/integration` Tests muessen gruen sein
- Security-Scan Ergebnisse dokumentieren
- PR-Template + Checkliste verpflichtend

---

## Tooling-Backbone

### Repo & Code
- Repo-Scanner (grep/AST), Git diff, Semgrep, Sonar (optional)
- Formatter/Linter (z.B. Spotless, ESLint)
- Build/Test Runner (Maven/Gradle, npm, Playwright)

### ALM/Docs
- Jira API (Issues/Kommentare/Status)
- Confluence API (Pages/Templates)
- GitLab/GitHub API (Branches/PRs/MRs)

### Runtime (optional)
- Logs/Traces/Metrics (OpenTelemetry, Loki, Prometheus, etc.)
- Kubernetes API (Deployments/Pods/Events)

---

## Quality Gates (empfohlen)

| Gate | Automatisiert | Menschlich |
|------|---------------|------------|
| Build erfolgreich | Ja | - |
| Unit/Integration Tests gruen | Ja | - |
| Lint/Format gruen | Ja | - |
| Security Findings bewertet | Teilweise | Ja |
| Code Review Approval | - | Ja (mind. 1) |

---

## Aktueller Implementierungs-Status (AICodeGenCrew)

| Komponente | Status | Notizen |
|------------|--------|---------|
| Phase 0: Indexing | FERTIG | ChromaDB, File Discovery |
| Phase 1: Facts | 80% | 733 Komponenten, Relation Resolution bei 54% |
| Phase 2: Synthese | FERTIG | C4, arc42 Generierung |
| Phase 3-7 | GEPLANT | Roadmap Q1 2026 |

### Ziel-Stack
- **Backend:** Spring Boot (Java)
- **Frontend:** Angular (TypeScript)
- **Infrastruktur:** On-Prem, GitLab, Jira/Confluence
- **LLM:** OpenAI-kompatible API (lokal oder Cloud)

---

## Ergebnis

Mit CrewAI + LLM kannst du den SDLC **stark automatisieren**, solange du:
- die Arbeit in **deterministische Schritte** zerlegst,
- **Tools** als "Source of Truth" nutzt,
- und **menschliche Gates** fuer Verantwortung/Qualitaet beibehaeltst.

---

## Referenzen

- [AI_SDLC_ARCHITECTURE.md](AI_SDLC_ARCHITECTURE.md) - Technische Architektur-Details
- [SDLC_95_ARCHITECTURE.md](SDLC_95_ARCHITECTURE.md) - Vollstaendige 95% Automatisierungs-Vision
- [diagrams/](diagrams/) - Professionelle draw.io Diagramme
