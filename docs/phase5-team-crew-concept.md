# Phase 5 Redesign: Team-Based CrewAI Architecture (FROM SCRATCH)

## Context

Phase 5 (Implement) wird komplett neu gebaut. Der bisherige Ansatz — eine deterministische Pipeline mit 8+ Stages, die den LLM wie ein Code-Template-Engine behandelt — war zu starr und zu fragil. Das Grundproblem: der Pipeline-Ansatz versucht, den LLM zu "kontrollieren", statt ihn als das einzusetzen, was er ist: einen Entwickler, der Werkzeuge benutzt.

**Neuer Ansatz**: CrewAI-Agenten arbeiten als echtes Entwicklerteam. Sie bekommen ALLE Werkzeuge, lesen die Aufgabe selbst, entscheiden selbst was zu tun ist, implementieren, bauen, testen. Der Development Plan (Phase 4) ist nur der Input — nicht die Steuerung.

**GPT-Findings die adressiert werden**:
1. ImportIndex mischt Sprachen (TS bekommt Java-Imports) — Fix: Language-Filter
2. Build Verification wird oft uebersprungen — Fix: Preflight Gate + keine Skip-Logik
3. Dokumentation hinkt Code hinterher — Nicht in Scope (Phase 5 != Docs)
4. Config zeigt altes Modell — Fix: Dual-Model Routing (Coder + Analysis)

---

## Architektur-Uebersicht

```
Phase 4 Output (Development Plan JSON)
         |
         v
+---------------------------------------------+
|         IMPLEMENT CREW (Phase 5)            |
|                                             |
|  +-------------------------------------+   |
|  |        MANAGER AGENT (120B)         |    |
|  |  Liest Task, versteht Scope,        |    |
|  |  verteilt Arbeit, validiert Output   |    |
|  +------+----------+----------+--------+    |
|         |          |          |              |
|    +----v---+ +----v---+ +---v-----+        |
|    |DEVELOPER| | TESTER | | BUILDER |       |
|    |(Coder  | |(Coder  | | (120B)  |       |
|    | 14B)   | | 14B)   | |         |       |
|    +--------+ +--------+ +---------+       |
|                                             |
|  Shared: Staging Dict + Tool Suite          |
+---------------------------------------------+
         |
         v
   Stage 5: Output Writer (unchanged)
```

### Prozess: `Process.hierarchical`

- **Manager Agent** koordiniert, delegiert, validiert
- **Worker Agents** (Developer, Tester, Builder) fuehren aus
- Agents kommunizieren ueber CrewAI Delegation + Shared Staging
- KEIN sequenzielles Pipeline-Forcing — Manager entscheidet Reihenfolge

---

## Agenten-Design

### 1. Manager Agent (Projekt-Manager)

| Eigenschaft | Wert |
|-------------|------|
| **LLM** | `MODEL` (gpt-oss-120B) — gut im Verstehen, Planen, Koordinieren |
| **Rolle** | Technischer Projektleiter |
| **allow_delegation** | `True` |
| **Tools** | Alle READ-Tools (CodeReader, FactsQuery, RAGQuery, MCP) + ImportIndex-Lookup |

**Aufgaben**:
1. Development Plan JSON lesen und verstehen
2. Betroffene Dateien gruppieren (nach Container: backend/frontend)
3. Arbeit an Developer delegieren (pro Datei oder Dateigruppe)
4. Nach Code-Generierung -> Builder delegieren fuer Build-Check
5. Bei Build-Fehlern -> Developer delegieren fuer Fix
6. Nach erfolgreichem Build -> Tester delegieren fuer Unit-Tests
7. Qualitaetskontrolle: Ergebnis validieren bevor "fertig"

**Warum 120B fuer Manager**: Versteht komplexe Task-Beschreibungen, kann priorisieren, muss aber keinen Code schreiben.

### 2. Developer Agent (Senior-Entwickler)

| Eigenschaft | Wert |
|-------------|------|
| **LLM** | `CODEGEN_MODEL` (Qwen2.5-Coder-14B) — spezialisiert auf Code |
| **Rolle** | Senior Full-Stack Developer |
| **allow_delegation** | `False` |
| **Tools** | CodeReader, CodeWriter, ImportIndexTool, FactsQuery, RAGQuery, MCP |

**Aufgaben** (vom Manager delegiert):
- Quelldatei lesen (`CodeReader`)
- Architektur-Kontext abfragen (`FactsQuery`, `RAGQuery`, MCP)
- Korrekte Imports nachschlagen (`ImportIndexTool`)
- Code generieren und in Staging schreiben (`CodeWriter`)
- Build-Fehler fixen (wenn Manager es delegiert)

**Warum Coder-14B**: Schreibt besseren Code als 120B bei deutlich weniger Tokens. Versteht Code-Patterns, Imports, Syntax nativ.

### 3. Tester Agent (Test-Ingenieur)

| Eigenschaft | Wert |
|-------------|------|
| **LLM** | `CODEGEN_MODEL` (Qwen2.5-Coder-14B) — Tests sind auch Code |
| **Rolle** | Senior Test Engineer |
| **allow_delegation** | `False` |
| **Tools** | CodeReader, TestWriter, TestPattern, RAGQuery, MCP |

**Aufgaben** (vom Manager delegiert):
- Geaenderte Datei lesen
- Bestehende Test-Patterns abfragen (`TestPattern`)
- Unit-Tests generieren und schreiben (`TestWriter`)

### 4. Builder Agent (DevOps-Ingenieur)

| Eigenschaft | Wert |
|-------------|------|
| **LLM** | `MODEL` (gpt-oss-120B) — Build-Output analysieren, nicht Code schreiben |
| **Rolle** | DevOps & Build Engineer |
| **allow_delegation** | `False` |
| **Tools** | BuildRunner, BuildErrorParser, FactsQuery |

**Aufgaben** (vom Manager delegiert):
- Build ausfuehren (`BuildRunner`)
- Fehler parsen (`BuildErrorParser`)
- Strukturierten Fehlerbericht an Manager zurueckgeben

**Warum 120B fuer Builder**: Muss Build-Output VERSTEHEN und erklaeren, nicht Code schreiben. 120B besser im Analysieren von langen Texten.

---

## Tool-Suite

### Bestehende Tools (BEHALTEN)

| Tool | Agent(en) | Funktion |
|------|-----------|----------|
| `CodeReaderTool` | Developer, Tester | Quelldateien lesen (max 12K chars) |
| `CodeWriterTool` | Developer | Code in Staging schreiben |
| `TestWriterTool` | Tester | Tests in Staging schreiben |
| `BuildRunnerTool` | Builder | Container-Build ausfuehren |
| `BuildErrorParserTool` | Builder | Build-Fehler strukturiert parsen |
| `TestPatternTool` | Tester | Test-Patterns aus Facts abfragen |
| `FactsQueryTool` | Alle | Architektur-Facts abfragen |
| `RAGQueryTool` | Developer, Tester | ChromaDB Codebase-Suche |
| MCP Server (7 Tools) | Alle | Komponenten, Relationen, Endpoints |

### Neue Tools (NEU ERSTELLEN)

#### `ImportIndexTool` (NEU)
**Fuer**: Developer Agent
**Zweck**: Exakte Import-Statements nachschlagen statt raten lassen

```
Input:  symbol="CoreModule", from_file="app.module.ts", language="typescript"
Output: "import { CoreModule } from './core/core.module';"
```

**Intern**: Nutzt die bestehende `ImportIndex`-Klasse aus `stage2a_import_index_builder.py` (wird zum Tool umgebaut).

**Fix fuer GPT-Finding #1**: Der `resolve()`-Call filtert jetzt nach Language — TS-Dateien bekommen NUR TS-Imports, Java-Dateien NUR Java-Imports.

#### `DependencyLookupTool` (NEU)
**Fuer**: Developer, Manager
**Zweck**: Abhaengigkeiten einer Datei verstehen

```
Input:  file_path="app.module.ts"
Output: {
  "depends_on": ["core.module.ts", "shared.module.ts"],
  "depended_by": ["main.ts"],
  "generation_tier": 1
}
```

**Intern**: Nutzt `DependencyGrapher` aus `stage2b_dependency_grapher.py`.

#### `PlanReaderTool` (NEU)
**Fuer**: Manager
**Zweck**: Development Plan JSON lesen und strukturiert zurueckgeben

```
Input:  task_id="BNUVZ-12529"
Output: { summary, task_type, affected_components, implementation_steps, upgrade_plan }
```

---

## Dual-Model Routing

```
+---------------------------------------------+
|              MODEL ROUTING                   |
|                                              |
|  Manager Agent  -> MODEL (gpt-oss-120B)      |
|  Builder Agent  -> MODEL (gpt-oss-120B)      |
|  Developer Agent -> CODEGEN_MODEL (Coder 14B)|
|  Tester Agent    -> CODEGEN_MODEL (Coder 14B)|
+---------------------------------------------+
```

**Implementierung**: `llm_factory.py` bekommt eine `create_codegen_llm()` Funktion neben `create_llm()`.

```python
# In llm_factory.py
def create_codegen_llm() -> LLM:
    """LLM for code-writing agents (Developer, Tester)."""
    model = os.getenv("CODEGEN_MODEL") or os.getenv("MODEL")
    api_base = os.getenv("CODEGEN_API_BASE") or os.getenv("API_BASE")
    api_key = os.getenv("CODEGEN_API_KEY") or os.getenv("OPENAI_API_KEY")
    ...
```

---

## Crew-Ablauf (Realistisch)

### Input
```python
crew.run(
    plan: CodegenPlanInput,       # Von Phase 4
    repo_path: str,               # Target-Repo
    facts_path: str,              # architecture_facts.json
)
```

### Preflight (Deterministisch, VOR Crew-Start)

Bevor die Crew startet, werden deterministische Vorbereitungen getroffen:

1. **ImportIndex aufbauen** (3-10s, 0 LLM-Tokens)
   - Scannt Target-Repo -> Symbol->Import Map
   - **Fix**: Language-Filter in `resolve()` (GPT-Finding #1)

2. **Dependency Graph aufbauen** (1-2s, 0 LLM-Tokens)
   - Topologische Sortierung der betroffenen Dateien
   - Wird dem Manager als Kontext mitgegeben

3. **Preflight Validation** (NEU, GPT-Finding #3)
   - Prueft: Alle affected_components existieren im Repo?
   - Prueft: Plan JSON vollstaendig und valide?
   - Prueft: Build-System fuer alle Container konfiguriert?
   - Bricht ab BEVOR LLM-Tokens verbrannt werden

### Crew Execution (CrewAI Hierarchical)

```python
crew = Crew(
    agents=[developer, tester, builder],
    tasks=[implement_task, build_task, test_task],
    process=Process.hierarchical,
    manager_agent=manager,
    verbose=True,
    memory=False,
    max_rpm=30,
)
result = crew.kickoff(inputs={
    "plan": plan_json,
    "dependency_order": dep_graph,
    "import_index_summary": top_symbols,
})
```

**Task-Definitionen** (als CrewAI Tasks):

**Task 1: Implement Code Changes**
```
Lese den Development Plan und implementiere alle Code-Aenderungen.
Fuer jede Datei:
1. Lies die Datei (CodeReader)
2. Schau Imports nach (ImportIndexTool)
3. Schau Abhaengigkeiten nach (DependencyLookupTool)
4. Generiere den neuen Code
5. Schreibe ihn (CodeWriter)

Bearbeite die Dateien in dieser Reihenfolge (Dependencies first):
{dependency_order}
```

**Task 2: Verify Build**
```
Ueberpruefe ob der generierte Code kompiliert.
1. Fuehre den Build aus (BuildRunner)
2. Parse Fehler falls vorhanden (BuildErrorParser)
3. Melde das Ergebnis strukturiert
```

**Task 3: Generate Tests**
```
Generiere Unit-Tests fuer alle geaenderten Dateien.
1. Schau bestehende Test-Patterns nach (TestPattern)
2. Lies die geaenderte Datei (CodeReader)
3. Generiere Tests
4. Schreibe sie (TestWriter)
```

**Manager koordiniert**:
- Task 1 zuerst -> Developer
- Task 2 danach -> Builder
- Bei Build-Fehler -> zurueck zu Developer (Heal-Loop, max 3x)
- Task 3 nach erfolgreichem Build -> Tester
- Abschluss: Zusammenfassung + Staging-Inhalt

### Post-Crew (Deterministisch)

1. **Import Fixer** (0 LLM-Tokens)
   - Deterministische Post-Korrektur aller Imports im Staging
   - Nutzt ImportIndex fuer fehlende/falsche Imports
   - **Fix**: Language-Filter aktiv (kein Cross-Language-Mixing)

2. **Safety Gate**
   - Prueft: >50% der Dateien fehlgeschlagen? -> Kein Commit
   - Prueft: Build war erfolgreich? -> Commit erlaubt

3. **Output Writer** (Stage 5, unveraendert)
   - Staging -> Disk schreiben
   - Git-Commit (wenn Safety Gate OK)
   - Report generieren

---

## Datei-Struktur (Phase 5 neu)

```
hybrid/code_generation/
|-- __init__.py
|-- crew.py                    <-- KOMPLETT NEU (Hierarchical Crew)
|-- agents.py                  <-- NEU (4 Agenten mit Dual-Model)
|-- tasks.py                   <-- NEU (3 Tasks, nicht 6)
|-- schemas.py                 <-- BEHALTEN + ImportIndex-Schemas
|-- pipeline.py                <-- ENTFERNEN (kein Pipeline-Pfad mehr)
|-- build_fixer_crew.py        <-- ENTFERNEN (in Crew integriert)
|
|-- preflight/                 <-- NEU
|   |-- __init__.py
|   |-- import_index.py        <-- Aus stage2a (wird Preflight-Modul)
|   |-- dependency_graph.py    <-- Aus stage2b (wird Preflight-Modul)
|   |-- import_fixer.py        <-- Aus stage3c (Post-Crew Fixer)
|   +-- validator.py           <-- NEU (Preflight Validation Gate)
|
|-- tools/                     <-- BEHALTEN + 3 neue Tools
|   |-- __init__.py
|   |-- code_reader_tool.py    <-- unveraendert
|   |-- code_writer_tool.py    <-- unveraendert
|   |-- build_runner_tool.py   <-- unveraendert
|   |-- build_error_parser_tool.py <-- unveraendert
|   |-- test_pattern_tool.py   <-- unveraendert
|   |-- test_writer_tool.py    <-- unveraendert
|   |-- import_index_tool.py   <-- NEU (wraps ImportIndex)
|   |-- dependency_tool.py     <-- NEU (wraps DependencyGraph)
|   +-- plan_reader_tool.py    <-- NEU (liest Plan JSON)
|
|-- strategies/                <-- ENTFERNEN (Agenten entscheiden selbst)
|
+-- stages/                    <-- ENTFERNEN (kein Stage-Konzept mehr)
```

### Was wegfaellt
- **Alle 8 Pipeline-Stages** (1, 2A, 2B, 2C, 3A, 3B, 3C, 4, 4b) -> Agenten uebernehmen
- **4 Strategy-Klassen** -> Agenten bekommen Task-Type-Instruktionen im Prompt
- **pipeline.py** -> Crew orchestriert alles
- **build_fixer_crew.py** -> In Hauptcrew integriert (Manager delegiert Heal an Developer)

### Was bleibt
- **Alle 8 bestehenden Tools** -> Agenten brauchen sie
- **ImportIndex + DependencyGraph** -> Werden Preflight-Module + Tool-Wrapper
- **ImportFixer** -> Deterministischer Post-Processor
- **Stage 5 (Output Writer)** -> Staging -> Disk + Git
- **schemas.py** -> Erweitert, nicht ersetzt
- **MCP Server** -> Alle Agenten nutzen ihn

---

## Fix: GPT-Findings

### Finding 1: ImportIndex Language-Mixing (HIGH)
**Problem**: `resolve("Service", "app.module.ts", "typescript")` koennte Java-Klasse zurueckgeben.
**Fix**: In `ImportIndex.resolve()` -> Filter `if entry.language != language: skip`
**Wo**: `preflight/import_index.py` (aus stage2a umbenannt)

### Finding 2: Build Verification Skipping (HIGH)
**Problem**: Stage 4b returned oft "skipped" ohne echten Build.
**Fix**: In neuem Konzept irrelevant — Builder Agent fuehrt IMMER Build aus. Kein Skip. Manager delegiert Build nach jeder Code-Aenderung.

### Finding 3: Preflight Gate (MEDIUM)
**Problem**: LLM-Tokens werden verbrannt bevor klar ist ob der Plan valide ist.
**Fix**: `preflight/validator.py` prueft VOR Crew-Start:
- Plan JSON Schema-Validierung
- Betroffene Dateien existieren im Repo
- Build-System pro Container vorhanden
- ImportIndex erfolgreich gebaut (>0 Symbole)

### Finding 4: Dual-Model Config
**Fix**: `CODEGEN_MODEL` + `CODEGEN_API_BASE` + `CODEGEN_API_KEY` in `.env` (bereits implementiert). `llm_factory.py` bekommt `create_codegen_llm()`.

---

## Risiken und Mitigationen

| Risiko | Mitigation |
|--------|-----------|
| Hierarchical Process ist weniger vorhersagbar als Sequential | Guardrails (max 50 Tool-Calls), Timeout pro Agent |
| Manager delegiert falsch | Klare Agent-Rollen, eindeutige Task-Beschreibungen |
| Coder-14B an bmf-ai hat SSL/Auth-Probleme | Fallback: beide Agents nutzen MODEL wenn CODEGEN nicht erreichbar |
| Agents in Endlos-Loop | Tool-Guardrails (max 3 identische Calls, max 50 total) |
| Build braucht VPN-off aber LLM braucht VPN-on | `-x test` an Gradle-Build -> kompiliert ohne VPN-Tests |

---

## Implementierungsreihenfolge

| # | Was | LOC (ca.) | Abhaengigkeiten |
|---|-----|-----------|-----------------|
| 1 | `preflight/import_index.py` — Aus stage2a extrahieren, Language-Filter fixen | ~280 | Keine |
| 2 | `preflight/dependency_graph.py` — Aus stage2b extrahieren | ~180 | Keine |
| 3 | `preflight/import_fixer.py` — Aus stage3c extrahieren | ~280 | #1 |
| 4 | `preflight/validator.py` — Preflight Gate (NEU) | ~100 | #1, #2 |
| 5 | `tools/import_index_tool.py` — CrewAI Tool Wrapper | ~60 | #1 |
| 6 | `tools/dependency_tool.py` — CrewAI Tool Wrapper | ~50 | #2 |
| 7 | `tools/plan_reader_tool.py` — Plan JSON Reader Tool | ~50 | Keine |
| 8 | `shared/utils/llm_factory.py` — `create_codegen_llm()` hinzufuegen | ~30 | Keine |
| 9 | `agents.py` — 4 Agenten mit Dual-Model (KOMPLETT NEU) | ~120 | #8 |
| 10 | `tasks.py` — 3 Tasks (KOMPLETT NEU) | ~150 | Keine |
| 11 | `crew.py` — Hierarchical Crew (KOMPLETT NEU) | ~350 | #4-#10 |
| 12 | Alte Dateien loeschen (stages/, strategies/, pipeline.py, build_fixer_crew.py) | — | #11 |
| 13 | Integration Test mit BNUVZ-12529 | — | Alles |

**Geschaetzte Gesamtarbeit**: ~1650 LOC neu/umgebaut, ~2000 LOC geloescht.

---

## Verifikation

1. **Preflight Test**: ImportIndex auf C:\uvz -> >2000 Symbole, Language-Filter aktiv
2. **Tool Test**: ImportIndexTool.resolve("CoreModule", "app.module.ts", "typescript") -> korrekter TS-Import
3. **Crew Dry-Run**: `dry_run=True` -> Manager delegiert korrekt, keine LLM-Calls
4. **Crew Real-Run**: BNUVZ-12529 (Angular 19 Upgrade) -> 10/10 Dateien, Build erfolgreich
5. **Regression**: Import-Fehler < 50% vs. alter Pipeline-Ansatz
6. **Metriken**: Token-Verbrauch pro Agent loggen, Heal-Attempts vergleichen
