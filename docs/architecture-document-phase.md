# Architecture: Document Phase (Phase 3 — Architecture Synthesis)

## Overview

Phase 3 generiert C4-Diagramme und arc42-Dokumentation aus den Architektur-Facts (Phase 1) und der Analyse (Phase 2). Es ist die komplexeste Phase — 24 Mini-Crews, 30+ Tool-Calls pro Chapter, und die einzige Phase die sowohl Markdown als auch DrawIO-Diagramme produziert.

## Execution Flow

```
ArchitectureSynthesisCrew.run()
  │
  ├─ _validate_prerequisites()
  │    └─ Prüft: architecture_facts.json + analyzed_architecture.json existieren
  │
  ├─ Phase 3a: C4Crew.run()
  │    ├─ 5 Mini-Crews: context, container, component, deployment, quality
  │    ├─ Jede Mini-Crew: 1 Agent, 2-3 Tasks (doc + diagram + quality gate)
  │    └─ Output: c4/*.md + c4/*.drawio
  │
  └─ Phase 3b: Arc42Crew.run()
       ├─ 19 Mini-Crews: 13 Chapters + Quality Gate
       │    (ch05, ch06, ch08 sind in Sub-Chapters gesplittet)
       ├─ Jede Mini-Crew: 1 Agent, 1 Task (frischer LLM-Context)
       ├─ Merge-Step: Sub-Chapters → finale Kapitel
       └─ Output: arc42/*.md + quality/arc42-report.md
```

## Mini-Crew Pattern

### Problem das gelöst wurde
Ursprünglich: 44 Tasks in 1 Crew → Context-Overflow nach ~10 Tasks. Agent verliert Kontext, halluziniert, wiederholt sich.

### Lösung
1 Task pro Mini-Crew. Jede Mini-Crew bekommt:
- Frischen LLM-Context (kein Zustandsübertrag)
- Eigenen Agent mit allen Tools
- Template-Variables mit vorberechneten Summaries (nicht Inter-Task-Context)
- Checkpoint nach Abschluss (Resume möglich)

### Trade-Off
- Mehr API-Calls (jede Mini-Crew braucht Setup)
- Kein Kontext-Sharing zwischen Chapters (muss alles per Tools neu laden)
- Aber: Zero Context-Interference, jedes Chapter unabhängig

## Agent Configuration

```python
Agent(
    role="...",
    goal="...",
    backstory="...",
    llm=create_llm(),           # Qwen3-Coder-Next (oder FAST_MODEL für einfache Chapters)
    tools=[query_facts, rag_query, list_components_by_stereotype,
           doc_writer, create_drawio_diagram, safe_file_read, chunked_writer],
    mcps=get_phase3_mcps(),     # Sequential Thinking MCP
    verbose=True,
    max_iter=30,                # Max Iterationen pro Task
    max_retry_limit=10,         # Max Retries bei Connection-Errors
)
```

### Fast Model Optimization
Einfache, formularische Chapters nutzen FAST_MODEL (billiger, schneller):
- `introduction`, `constraints`, `glossary`

## TOOL_INSTRUCTION Protocol

Jede doc-writing Task beginnt mit diesem Protokoll:

```
EXECUTION PATTERN — follow these steps for every chapter:

1. GATHER: Call information-gathering tools to collect real data
   - query_facts(category="...")
   - list_components_by_stereotype(stereotype="...")
   - rag_query(query="...")

2. BUILD: Assemble complete markdown document in memory

3. WRITE: Call doc_writer() EXACTLY ONCE
   - If content > 15000 chars: use chunked_writer instead

4. CONFIRM: Respond with only "Chapter completed."

CONSTRAINTS:
- Maximum 25 tool calls per task
- Never call same tool with identical arguments more than once
- All content goes into doc_writer content parameter
```

## Tool Ecosystem

| Tool | Quelle | Zweck |
|------|--------|-------|
| `query_facts` | `knowledge/extract/*.json` (Dimension-Dateien) | Architektur-Fakten: Components, Relations, Interfaces, Containers |
| `rag_query` | Qdrant (Phase 0 Index) | Semantische Code-Suche: Patterns, Annotations, Config |
| `list_components_by_stereotype` | `architecture_facts.json` | Inventar: alle Controller, Services, Entities etc. |
| `doc_writer` | Schreibt auf Disk | Markdown-Datei erstellen (1 Call pro Chapter) |
| `create_drawio_diagram` | Generiert XML | DrawIO-Diagramm mit Nodes + Edges |
| `safe_file_read` | JSON-Dateien lesen | Facts/Analyzed-Daten mit Token-Budget |
| `chunked_writer` | Schreibt auf Disk | Große Dokumente (>15K chars) in Chunks |

## Checkpoint System

```json
// knowledge/document/.checkpoint_Arc42.json
{
  "crew_name": "Arc42",
  "checkpoints": [
    {"crew": "introduction", "status": "completed", "duration_seconds": 45.3, "total_tokens": 1850},
    {"crew": "constraints", "status": "completed", "duration_seconds": 38.1, "total_tokens": 1200}
  ],
  "completed_crews": ["introduction", "constraints"]
}
```

- **Resume:** Überspringe abgeschlossene Mini-Crews bei erneutem Lauf
- **Fresh Run:** Checkpoint wird gelöscht, alle Outputs bereinigt
- **Partial:** Checkpoint bleibt erhalten bei Degradation

## Quality Gate

Nach allen Chapters läuft ein Quality-Gate Mini-Crew:
1. Liest alle generierten Dateien
2. Prüft: Alle Chapters vorhanden? Inhalt basiert auf echten Facts?
3. Banned Phrases: "UNKNOWN (no evidence extracted)" → Failure
4. Output: `quality/arc42-report.md` / `quality/c4-report.md`

## Output-Struktur

```
knowledge/document/
├── c4/
│   ├── c4-context.md + c4-context.drawio
│   ├── c4-container.md + c4-container.drawio
│   ├── c4-component.md + c4-component.drawio
│   └── c4-deployment.md + c4-deployment.drawio
├── arc42/
│   ├── 01-introduction.md
│   ├── 02-constraints.md
│   ├── 03-context.md
│   ├── 04-solution-strategy.md
│   ├── 05-building-blocks.md    (merged aus 4 Parts)
│   ├── 06-runtime-view.md       (merged aus 2 Parts)
│   ├── 07-deployment.md
│   ├── 08-crosscutting.md       (merged aus 3 Parts)
│   ├── 09-decisions.md
│   ├── 10-quality.md
│   ├── 11-risks.md
│   └── 12-glossary.md
└── quality/
    ├── arc42-report.md
    └── c4-report.md
```

---

## Bekannte Probleme

### P1: Agent-Loop bei doc_writer (KRITISCH)

**Symptom:** Agent ruft `doc_writer` mit identischem Content wiederholt auf. CrewAI blockt den zweiten Call ("I tried reusing the same input"). Agent loopt bis `max_iter=30` erreicht.

**Root Cause Analyse:**

1. **CrewAI Duplikat-Erkennung:** CrewAI vergleicht Tool-Inputs als String. Wenn der Agent denselben Content nochmal sendet → Block. Der Agent interpretiert den Block-Text als Fehler und versucht es erneut.

2. **Fehlende Erfolgs-Erkennung:** Der Agent erkennt nicht dass `doc_writer` beim ersten Call erfolgreich war. Die Erfolgs-Response ("Successfully wrote 10654 characters to ...") wird vom Agent nicht als "Task done" interpretiert.

3. **TOOL_INSTRUCTION nicht befolgt:** Das Protokoll sagt "Respond with only 'Chapter completed.'" — aber der Agent versucht stattdessen den Tool-Call zu wiederholen.

4. **Token-Budget:** Bei langen Chapters (>15K chars) wird der Content im Agent-Context gespeichert. Der zweite identische Call verbraucht nochmal denselben Token-Raum → beschleunigt Context-Overflow.

**Impact:** Chapter wird geschrieben (erster Call erfolgreich), aber Agent verschwendet 20+ Iterationen mit Retries → verlangsamt die Phase um 5-10 Minuten pro betroffenes Chapter.

### P2: Fallback-Stubs statt echtem Content

**Symptom:** Einige Chapters werden als Stubs geschrieben ("auto-generated as a stub") wenn der Agent `doc_writer` nicht aufruft.

**Root Cause:** Agent schreibt den Content in seine Response statt in den Tool-Call. Das Fallback-System extrahiert den Content aus der Response und schreibt ihn als Stub.

### P3: RAG-Ergebnisse ohne Qdrant-Treffer

**Symptom:** `rag_query` gibt leere Ergebnisse zurück obwohl relevante Dateien indexiert sind.

**Root Cause:** (Gefixt) `qdrant-client` 1.17 hat `search()` durch `query_points()` ersetzt. Fix in diesem Commit.

### P4: Kein persistentes Pipeline-Log

**Symptom:** Pipeline-Subprocess-Output nur in-memory, nicht auf Disk.

**Root Cause:** (Gefixt) `_monitor_process()` schrieb nur in `self._log_lines`. Jetzt zusätzlich in `logs/pipeline.log`.

---

## Lösungsansätze für P1 (Agent-Loop)

### Option A: Tool-Response-Guardrail (Klein, Quick-Fix)

Nach dem ersten erfolgreichen `doc_writer` Call: Agent zwangsweise beenden.

```python
# In base_crew._run_mini_crew():
# After crew.kickoff(), check if doc_writer was called successfully
if doc_writer_tracker.was_called_successfully():
    # Don't rely on agent response — file is written, chapter done
    return "completed"
```

**Pro:** Einfach, sofort wirksam
**Contra:** Behandelt Symptom, nicht Ursache. Agent lernt nicht.

### Option B: Bessere Tool-Response (Mittel)

`doc_writer` gibt eine eindeutige Antwort die der Agent als "fertig" erkennt:

```python
def _run(self, file_path, content, **kwargs):
    # ... write file ...
    return (
        f"CHAPTER WRITTEN SUCCESSFULLY. File: {full_path} ({len(content)} chars). "
        f"YOUR TASK IS COMPLETE. Respond with 'Chapter completed.' now."
    )
```

**Pro:** Agent versteht Erfolg besser, weniger Loops
**Contra:** LLM-abhängig, keine Garantie

### Option C: Deterministic + LLM Hybrid (Groß, Best Practice)

Statt den Agent alles machen zu lassen: Daten deterministisch sammeln, nur die Textgenerierung dem LLM überlassen.

```python
# Deterministisch (kein Agent nötig):
facts = query_facts(category="components", stereotype="controller")
rag_results = rag_query("security annotations")
components = list_components_by_stereotype("service")

# Template vorbereiten:
prompt = CHAPTER_TEMPLATE.format(
    facts=facts,
    rag_results=rag_results,
    components=components,
)

# LLM-Call (kein Agent, kein Tool-Loop):
content = llm.complete(prompt)

# Deterministisch schreiben (kein doc_writer Tool nötig):
Path("knowledge/document/arc42/03-context.md").write_text(content)
```

**Pro:** Kein Agent-Loop möglich, deterministisch, reproduzierbar, schneller
**Contra:** Großer Umbau, verliert Agent-Flexibilität (aber brauchen wir die?)

### Option D: CrewAI Task-Level Control (Mittel)

CrewAI's `Task.callback` nutzen um nach dem ersten Tool-Call den Task zu beenden:

```python
Task(
    description="...",
    agent=agent,
    callback=lambda result: stop_if_file_written(result, expected_file),
)
```

**Pro:** Nutzt CrewAI-API, kein Custom-Code
**Contra:** Callback-API limitiert, nicht alle CrewAI-Versionen unterstützen es

---

## Empfehlung

**Kurzfristig (jetzt):** Option A + B kombinieren
- Tool-Response verbessern (Option B) → weniger Loops
- Guardrail nach erfolgreichem doc_writer → Loop-Breaker (Option A)

**Mittelfristig (nächster Sprint):** Option C für die kritischsten Chapters
- ch05 (Building Blocks, 4 Parts) und ch08 (Crosscutting, 3 Parts) sind am anfälligsten
- Deterministischer Data-Gather + LLM-Only-Generation

**Langfristig:** Vollständiger Hybrid-Ansatz (Option C für alle Chapters)
- Agent nur für Quality Gate und unstrukturierte Analyse
- Textgenerierung immer deterministisch + LLM

---

## Metriken (Baseline)

| Metrik | Aktuell | Ziel |
|--------|---------|------|
| Chapters mit Loop-Problem | ~30% | 0% |
| Durchschnittliche Iterationen pro Chapter | 15-20 | 5-10 |
| Phase 3 Gesamtdauer | 25-40 min | 15-20 min |
| Chapters als Stubs | ~10% | 0% |
| Quality Gate Pass-Rate | ~70% | >95% |
