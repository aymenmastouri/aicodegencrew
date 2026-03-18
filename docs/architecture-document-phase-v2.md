# Architecture V2: Document Phase — Pipeline + LLM Hybrid

## Design-Prinzipien

1. **Deterministic Data, Creative Text** — Code sammelt Daten, LLM interpretiert sie
2. **Single Call, Full Chapter** — 1 LLM-Call pro Chapter, kein Loop möglich
3. **Validate Before Write** — Output wird geprüft bevor er auf Disk geht
4. **Few-Shot Quality** — Beispiele zeigen dem LLM was "gut" aussieht
5. **Chain-of-Thought** — LLM denkt erst nach, dann schreibt es
6. **Fail Fast, Retry Smart** — Bei schlechtem Output: neuer Call mit Feedback

## Aktuell vs. V2

```
V1 (AKTUELL — CrewAI Agent):
┌─────────────────────────────────────────────────┐
│ CrewAI Agent (max_iter=30)                      │
│   → denkt nach (Token-Verschwendung)            │
│   → ruft query_facts auf                        │
│   → denkt nach                                  │
│   → ruft rag_query auf                          │
│   → denkt nach                                  │
│   → ruft nochmal query_facts auf (redundant)    │
│   → baut Content im Kopf                        │
│   → ruft doc_writer auf                         │
│   → Tool sagt "Erfolg"                          │
│   → Agent versteht es nicht → LOOP              │
│   → 15-30 Iterationen, 5-10 Min pro Chapter     │
└─────────────────────────────────────────────────┘

V2 (NEU — Template-First + LLM Enrichment):
┌─────────────────────────────────────────────────┐
│ 1. DataCollector (Python, deterministisch)       │
│    → query_facts, rag_query, list_components    │
│    → Alles in 1 Dict, <2 Sekunden              │
│                                                  │
│ 1b. TemplateBuilder (Python, deterministisch)    │
│    → Markdown-Skelett mit Fakten-Tabellen       │
│    → LLM_ENRICH Platzhalter fuer Enrichment     │
│    → 100% Fakten-basiert, 0% LLM               │
│                                                  │
│ 2. PromptBuilder (Template + Few-Shot)           │
│    → Template-Kontext + Daten + Beispiel        │
│    → 1 strukturierter Prompt                    │
│                                                  │
│ 3. LLM Generate (1 Call, temperature=0.5)        │
│    → Fuellt NUR die Platzhalter                 │
│    → Kontrollierter, kleinerer Output           │
│    → 30-90 Sekunden                             │
│                                                  │
│ 4. Validator (Python, deterministisch)            │
│    → Struktur + Template-Integritaet pruefen    │
│    → FactGrounder: Halluzinationen erkennen     │
│    → Bei Fehler: Eskalierendes Retry (max 2x)   │
│    → Temperature sinkt pro Attempt              │
│                                                  │
│ 5. Writer (Python, deterministisch)              │
│    → Datei schreiben, Checkpoint                │
│    → quality_score fuer Pipeline-Aggregation    │
└─────────────────────────────────────────────────┘
```

## Architektur

```
ChapterPipeline
├── DataCollector          # Sammelt alle Daten pro Chapter
│   ├── FactsCollector     # query_facts() fuer jede benoetigte Kategorie
│   ├── RAGCollector       # rag_query() fuer Code-Evidenz
│   └── ComponentCollector # list_components_by_stereotype()
│
├── TemplateBuilder        # NEU: Deterministisches Markdown-Skelett
│   ├── build_chapter_template() # Fakten-Tabellen + LLM_ENRICH Platzhalter
│   ├── _format_containers()     # Markdown-Tabelle aus Containern
│   ├── _format_interfaces()     # Markdown-Tabelle aus Interfaces
│   ├── _format_relations()      # Markdown-Tabelle aus Relationen
│   └── _format_technology_stack() # Technologie-Stack Tabelle
│
├── PromptBuilder          # Baut den LLM-Prompt
│   ├── ChapterTemplate    # arc42/c4 spezifisches Template
│   ├── FewShotExamples    # 1-2 Beispiele pro Chapter-Typ
│   ├── DataFormatter      # Strukturiert die gesammelten Daten
│   └── InstructionBuilder # Chain-of-Thought + Qualitaetskriterien
│
├── LLMGenerator           # Einzelner LLM-Call (phase_id="document")
│   ├── generate()         # litellm.completion() — temperature=0.5
│   └── retry_with_feedback(attempt=N)  # Eskalierendes Retry
│       ├── attempt=1: "Please fix..."  (temp=0.30)
│       ├── attempt=2: "CRITICAL..."    (temp=0.25)
│       └── attempt=3: "FINAL..."       (temp=0.20)
│
├── Validator              # Prueft Output vor dem Schreiben
│   ├── StructureCheck     # Hat alle erwarteten Sections?
│   ├── LengthCheck        # Min/Max Zeichenzahl pro Chapter
│   ├── FactGrounder       # NEU: Shared Utility — prueft gegen architecture_facts
│   ├── BannedPhraseCheck  # Keine Platzhalter/Halluzinationen?
│   ├── MarkdownCheck      # Valides Markdown?
│   ├── TemplateIntegrity  # NEU: Platzhalter gefuellt?
│   └── FactTablesIntact   # NEU: Fakten-Tabellen erhalten?
│
└── Writer                 # Schreibt auf Disk
    ├── write_chapter()    # Markdown-Datei
    ├── write_diagram()    # DrawIO-Datei (deterministisch aus Daten)
    ├── checkpoint()       # Resume-Punkt
    └── quality_score      # NEU: Fuer Pipeline Quality Score
```

## Prompt-Strategie

### Aufbau (pro Chapter)

```xml
<system>
You are a senior software architect writing professional arc42 documentation.
Write in the language of the input data. Be specific, reference real component
names and patterns. Never invent components that are not in the provided data.
</system>

<instructions>
Write arc42 Chapter {chapter_number}: {chapter_title}.

Think step by step:
1. First, analyze the provided architecture data
2. Identify key patterns, decisions, and relationships
3. Interpret what these mean for the system's quality and maintainability
4. Write the chapter with concrete evidence from the data

Quality criteria:
- Every claim must reference a real component or pattern from the data
- Include tables for inventories (components, interfaces, decisions)
- Add interpretation: not just WHAT but WHY and WHAT IT MEANS
- Minimum {min_length} characters, maximum {max_length} characters
- Use Mermaid diagrams where architecture flows need visualization
</instructions>

<context>
{chapter_specific_context_description}
</context>

<architecture_data>
{formatted_facts_and_rag_results}
</architecture_data>

<example>
{few_shot_example_for_this_chapter_type}
</example>

<output_format>
Write the complete chapter in Markdown. Start with # {chapter_number} - {title}.
Include all subsections as specified in the arc42 template.
</output_format>
```

### Warum dieser Aufbau?

| Element | Zweck | Research-Basis |
|---------|-------|---------------|
| `<system>` | Rolle + Sprache | Role-Prompting: +15% Qualität |
| `<instructions>` + CoT | Schritt-für-Schritt-Denken | Chain-of-Thought: -40% Halluzination |
| `<context>` | Chapter-spezifische Anleitung | Task-Decomposition |
| `<architecture_data>` | Alle Fakten gebündelt | RAG Best Practice: Context vor der Frage |
| `<example>` | 1 Beispiel pro Chapter-Typ | Few-Shot: konsistentes Format |
| `<output_format>` | Erwartetes Markdown-Format | Structured Output: +30% Compliance |

## Daten-Sammlung pro Chapter

Jedes Chapter hat eine feste **Data Recipe** — welche Daten es braucht:

```python
CHAPTER_DATA_RECIPES = {
    "01-introduction": {
        "facts": [
            ("all", {}),              # System-Übersicht
            ("containers", {}),        # Architektur-Style
            ("interfaces", {}),        # API-Endpunkte
        ],
        "components": ["controller", "service", "entity"],
        "rag_queries": [
            "business domain terminology purpose",
            "quality goals non-functional requirements",
        ],
    },
    "03-context": {
        "facts": [
            ("containers", {}),
            ("interfaces", {}),
            ("relations", {"query": "external"}),
        ],
        "components": [],
        "rag_queries": [
            "external system integration API client",
            "authentication authorization SSO",
        ],
    },
    "05-building-blocks": {
        "facts": [
            ("components", {"stereotype": "controller"}),
            ("components", {"stereotype": "service"}),
            ("components", {"stereotype": "repository"}),
            ("components", {"stereotype": "entity"}),
            ("relations", {}),
        ],
        "components": ["controller", "service", "repository", "entity"],
        "rag_queries": [
            "architecture pattern repository service layer",
            "dependency injection Spring autowired",
        ],
    },
    # ... für alle 12 Chapters
}
```

## Validation Pipeline

```python
class ChapterValidator:
    """Validiert LLM-Output bevor er auf Disk geschrieben wird."""

    def validate(self, content: str, chapter_id: str, data: dict) -> ValidationResult:
        checks = [
            self._check_structure(content, chapter_id),
            self._check_length(content, chapter_id),
            self._check_fact_grounding(content, data),
            self._check_banned_phrases(content),
            self._check_markdown(content),
        ]
        return ValidationResult(
            passed=all(c.passed for c in checks),
            issues=[c.message for c in checks if not c.passed],
        )

    def _check_structure(self, content, chapter_id):
        """Prüft ob alle erwarteten Sections vorhanden sind."""
        expected = CHAPTER_SECTIONS[chapter_id]  # ["## 3.1 Business Context", "## 3.2 Technical Context"]
        missing = [s for s in expected if s not in content]
        return Check(passed=len(missing) == 0, message=f"Missing sections: {missing}")

    def _check_fact_grounding(self, content, data):
        """Prüft ob der Content echte Komponentennamen referenziert."""
        component_names = {c["name"] for c in data.get("components", [])}
        # Mindestens 30% der Komponentennamen müssen im Text vorkommen
        found = sum(1 for name in component_names if name in content)
        ratio = found / max(len(component_names), 1)
        return Check(passed=ratio >= 0.3, message=f"Fact grounding: {ratio:.0%} ({found}/{len(component_names)})")

    def _check_banned_phrases(self, content):
        """Keine Platzhalter oder Halluzinationen."""
        banned = [
            "UNKNOWN", "placeholder", "TODO", "TBD",
            "as an AI", "I cannot", "I don't have",
            "auto-generated as a stub",
        ]
        found = [p for p in banned if p.lower() in content.lower()]
        return Check(passed=len(found) == 0, message=f"Banned phrases: {found}")
```

## Retry mit Feedback

Wenn der Validator Probleme findet → **eskalierendes Feedback** (nicht blind wiederholen):

**Attempt 1** (temperature=0.30):
```xml
<feedback severity='1'>
Your previous output had these specific issues. Please fix them:
- Missing section: "## 3.2 Technical Context"
- Fact grounding only 15% — you mentioned 3 of 20 components
- Banned phrase found: "TBD"
Output the complete corrected result.
</feedback>
```

**Attempt 2** (temperature=0.25):
```xml
<feedback severity='2'>
CRITICAL: Your previous attempt still had problems. Fix ONLY these specific issues — do not change anything else:
- Fact grounding still low
Output the complete corrected result.
</feedback>
```

**Attempt 3** (temperature=0.20):
```xml
<feedback severity='3'>
FINAL ATTEMPT: Focus exclusively on fixing these exact problems. Do not change anything else:
- Missing section
Output the complete corrected result.
</feedback>
```

Max 2 Retries. Nach dem 3. Versuch: Output nehmen wie er ist + Degradation markieren.

## DrawIO-Diagramme

Diagramme werden **deterministisch** aus Daten generiert — kein LLM nötig:

```python
def generate_c4_context_diagram(containers: list, interfaces: list) -> str:
    """Generiert DrawIO XML aus Architektur-Daten."""
    nodes = []
    edges = []
    for container in containers:
        nodes.append(Node(id=container["name"], label=container["name"], style="c4_container"))
    for iface in interfaces:
        if iface.get("external"):
            edges.append(Edge(source=iface["consumer"], target=iface["provider"]))
    return render_drawio(nodes, edges)
```

**Warum kein LLM für Diagramme?**
- Diagramme sind strukturiert (Nodes + Edges) — deterministisch ableitbar
- LLM generiert fehlerhaftes XML (häufiger Grund für Agent-Loops)
- Konsistente Formatierung über alle Diagramme

## Migration von V1 zu V2

### Was bleibt (aus V1 behalten):
- Checkpoint-System (Resume bei Abbruch)
- Quality Gate (als letzter Step)
- Mini-Crew-Pattern für Unabhängigkeit → wird zu Chapter-Pipeline
- Tool-Implementierungen (query_facts, rag_query)
- Output-Struktur (arc42/*.md, c4/*.md)
- Merge-Logic für Split-Chapters (ch05, ch06, ch08)

### Was sich ändert:
| V1 | V2 |
|----|----|
| CrewAI Agent pro Chapter | Python Pipeline + 1 LLM-Call |
| 30 max_iter, 10 retries | 1 Call + max 2 Retries mit Feedback |
| Agent entscheidet Tool-Reihenfolge | Feste Data Recipe pro Chapter |
| doc_writer als CrewAI Tool | Direkter `Path.write_text()` |
| Keine Validation vor Schreiben | Validator prüft Struktur + Grounding |
| Agent-Loop bei Duplikat | Nicht möglich (kein Agent) |
| ~5-10 Min pro Chapter | ~1-2 Min pro Chapter |
| ~25-40 Min gesamte Phase | ~10-15 Min gesamte Phase |

### Was NICHT geändert wird:
- Phase 2 (analyze) bleibt Agent-basiert — dort sind echte Entscheidungen nötig
- Phase 5 (implement) bleibt Agent-basiert — Code-Generierung braucht Iteration
- Phase 3 C4-Docs werden gleich behandelt wie arc42

## Implementierungs-Plan

### Phase 1: Prototyp (1 Chapter)
- Chapter 3 (Context) als Prototyp
- DataCollector + PromptBuilder + LLMGenerator + Validator
- Qualitätsvergleich V1 vs V2

### Phase 2: Alle Chapters
- Data Recipes für alle 12 arc42 Chapters
- Few-Shot Examples (1 pro Chapter-Typ)
- C4 Chapters (4 Levels)

### Phase 3: DrawIO deterministisch
- C4 Diagramme aus Daten generieren
- Kein LLM für XML/Diagramme

### Phase 4: Cleanup
- V1 Agent-Code entfernen (oder als Fallback behalten)
- Tests: Validation-Coverage, Output-Qualität
- Metriken: Dauer, Token-Verbrauch, Quality-Score

## Erwartete Verbesserungen

| Metrik | V1 (Agent) | V2 (Pipeline+LLM) |
|--------|-----------|-------------------|
| **Loop-Rate** | ~30% der Chapters | 0% (unmöglich) |
| **Stub-Rate** | ~10% | 0% (Validation) |
| **Dauer pro Chapter** | 5-10 Min | 1-2 Min |
| **Gesamte Phase 3** | 25-40 Min | 10-15 Min |
| **Token-Verbrauch** | ~50K pro Chapter | ~15K pro Chapter |
| **Reproduzierbarkeit** | Niedrig (Agent-Zufall) | Hoch (gleiche Daten → ähnlicher Output) |
| **Debugbarkeit** | Schwer (Agent-Logs) | Einfach (Prompt + Response) |
| **Quality Gate Pass** | ~70% | >95% |
