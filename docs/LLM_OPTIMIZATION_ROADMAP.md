# LLM Optimization Roadmap

## Current State (February 2026)

**Model**: `gpt-oss-120b` (on-prem, OpenAI-compatible API)

**Problems observed**:
- Agent ignores `TOOL_INSTRUCTION` and writes document content in response text instead of using `doc_writer` tool
- Agent loops on MCP tools (calls `get_architecture_summary` 30+ times without progress)
- Agent returns raw `ChatCompletionMessageToolCall` objects instead of text when hitting `max_iter`
- Missing output files despite crew marked as "completed"

**Root cause analysis** (updated):

The root cause is **not only the model**. Two factors contribute:

1. **Weak function calling** — On-prem model has poor tool-use compared to commercial models (GPT-4o, Claude). It struggles with when to call tools, when to stop, and output formatting.
2. **Missing orchestrator guardrails** — Even models with perfect tool-use need enforcement. CrewAI's default "agent decides everything" pattern allows the model to skip tools, loop forever, or declare success without writing files.

> Key insight: Symptoms like loops, wrong channel, raw ToolCall objects, and "completed but no files" are **orchestration/stop-condition/contract enforcement** problems — not purely model quality. These can be fixed **before** any model upgrade.

---

## Phase 0.5: Guardrails & Stop Conditions — IMPLEMENTED

> **Status**: Fully implemented in `src/aicodegencrew/shared/utils/tool_guardrails.py`
> Integrated into `base_crew.py` (Phase 3) and `crew.py` (Phase 2) via `install_guardrails()` / `uninstall_guardrails()`.
> Fixes "completed but no files" and MCP loops immediately, regardless of model.

### 1. Tool-Contract Enforcement (hart, nicht nur Prompt)

The agent must not be **able** to skip `doc_writer` — not just told not to.

| Guardrail | Implementation | Location |
|-----------|----------------|----------|
| **Output-Gate** | If `doc_writer` was not called during task → mark task as **failed**, not completed | `base_crew.py` `_run_mini_crew()` |
| **Response Sanitizer** | If model returns raw `ChatCompletionMessageToolCall` object → convert to error text, mark as failed/retry | `base_crew.py` `_extract_content()` |
| **File-exists check** | After crew completes → verify expected output files exist on disk with min size | `base_crew.py` `_run_mini_crew()` |

```python
# Output-Gate: after crew.kickoff(), check tool was actually used
def _validate_tool_usage(self, crew_output, expected_files):
    """Fail task if doc_writer was never called."""
    if not any(f.exists() and f.stat().st_size > 100 for f in expected_files):
        raise RuntimeError(
            f"Task completed but output files missing: {expected_files}. "
            "Agent likely wrote content in response instead of using doc_writer."
        )
```

### 2. Loop-Breaker gegen MCP-Spam

| Guardrail | Rule | Implementation |
|-----------|------|----------------|
| **Identical-call budget** | Max 2 identical tool calls in sequence (same tool + same args) | CrewAI `step_callback` or wrapper |
| **Tool-call TTL** | Max N tool calls per task (e.g. 12), then force "synthesize + doc_writer" | Agent `max_iter` + callback |
| **Result caching** | Tool results cached in task context → repeated calls rejected with "already have this data" | MCP tool wrapper |

```python
# Loop-breaker: track tool calls per task
class ToolCallTracker:
    def __init__(self, max_identical=2, max_total=12):
        self.calls = []
        self.max_identical = max_identical
        self.max_total = max_total

    def check(self, tool_name, args) -> str | None:
        """Returns error message if call should be blocked, None if OK."""
        key = f"{tool_name}:{json.dumps(args, sort_keys=True)}"
        identical_count = sum(1 for c in self.calls[-3:] if c == key)
        if identical_count >= self.max_identical:
            return f"Already called {tool_name} with same args {identical_count}x. Use the data you have."
        if len(self.calls) >= self.max_total:
            return f"Reached {self.max_total} tool calls. Synthesize your findings and call doc_writer now."
        self.calls.append(key)
        return None
```

### 3. Central Tool-Policy im System Prompt

Add a **hard rule** (not just example) to all agents:

```
MANDATORY RULES:
1. If you are about to write more than 200 characters in assistant content, STOP and call doc_writer instead.
2. Your final assistant message MUST be a one-liner confirmation (e.g. "File arc42/05-building-blocks.md written successfully.").
3. You MUST call doc_writer exactly once per task. Tasks without doc_writer calls are FAILED.
4. Do NOT call the same MCP tool more than twice with identical arguments.
```

### Erwartete Verbesserung
- "Completed but no files": ~20% → ~2%
- MCP loops: eliminated (hard budget of 25 calls + 3 identical max)
- Tool-Compliance: ~60% → ~75% (before any prompt changes)
- Aufwand: 1-2 Tage — **DONE**

---

## Phase 1: Few-Shot Prompting (0 Aufwand, sofort umsetzbar)

### Was
Erfolgreiche Tool-Use-Sequenzen als Beispiele direkt in die Task-Descriptions einbauen.

**Status: IMPLEMENTED** — See `base_crew.py` `_TOOL_INSTRUCTION` and per-task `EXECUTION EXAMPLE` blocks.

### Wie
In jeder Task-Description ein konkretes Beispiel:

```
EXAMPLE of correct execution:
Step 1: get_statistics() -> {"components": 738, "relations": 169, ...}
Step 2: list_components_by_stereotype("service") -> [ServiceA, ServiceB, ...]
Step 3: get_endpoints() -> [{path: "/api/...", method: "GET"}, ...]
Step 4: doc_writer(file_path="arc42/05-building-blocks.md", content="# 05 - Building Block View\n\n## 5.1 Overview\n...")
Step 5: Respond ONLY with: "File arc42/05-building-blocks.md written successfully."

WRONG: Writing the full document in your response.
RIGHT: Using doc_writer tool to write the file.
```

### Erwartete Verbesserung
- Tool-Use Compliance: ~75% → ~85% (combined with Phase 0.5 guardrails)
- Kosten: 0 (nur Prompt-Aenderung)
- Aufwand: 2-4 Stunden

---

## Phase 2: Modellwechsel (1 Tag Aufwand)

### Empfohlene On-Prem Modelle mit nativem Function Calling

| Modell | Parameter | Tool-Use | VRAM | Bemerkung |
|--------|-----------|----------|------|-----------|
| **Qwen2.5-72B-Instruct** | 72B | Sehr gut | ~80 GB | Bestes Open-Source Tool-Use, structured output/JSON |
| **Llama 3.1 70B Instruct** | 70B | Gut | ~80 GB | Meta, breit getestet |
| **Mistral Large 2 (123B)** | 123B | Sehr gut | ~140 GB | Function Calling nativ trainiert, sequential+parallel calls |
| **DeepSeek-V2.5** | 236B MoE | Sehr gut | ~80 GB (aktiv) | MoE = weniger VRAM als erwartet |
| **Command R+ (104B)** | 104B | Sehr gut | ~120 GB | Cohere, tool-use/RAG fokussiert |

### Aenderung
Nur `.env` anpassen:
```env
MODEL=qwen2.5-72b-instruct
# oder
MODEL=meta-llama/Llama-3.1-70B-Instruct
```

### Wichtig: Nicht nur `.env` aendern!

"Nur .env aendern" stimmt nur, wenn:
- **Chat template** + **tool schema** exakt zum Modell passen (sonst killt das Tool-Use)
- **Tool-call Formatierung** pro Modell korrekt ist (gerade Command R+ ist template-sensitiv)
- vLLM **garantiert parsable tool calls** — aber nicht "high-quality". Guardrails (Phase 0.5) bleiben noetig

Checkliste bei Modellwechsel:
1. Chat template in vLLM/LiteLLM pruefen
2. Tool-schema Format verifizieren (OpenAI vs. Anthropic vs. native)
3. `tool_choice` Parameter testen (`auto` vs. `required`)
4. Testlauf mit 1 Mini-Crew vor vollem Run

### Erwartete Verbesserung
- Tool-Use Compliance: ~85% → ~95%
- Output-Qualitaet: Deutlich bessere Dokumentation
- Kosten: Modell-Download + vLLM Setup

---

## Phase 3: LoRA Fine-Tuning (1-2 Wochen Aufwand)

### Was
Ein LoRA-Adapter (Low-Rank Adaptation) auf dem gewaehlten Base-Model, trainiert auf die spezifischen Tool-Use-Patterns dieses Projekts.

### Trainingsziele (praezisiert)

> Nicht "repo-spezifisches Wissen" (schwer zu generalisieren), sondern:

| Ziel | Warum |
|------|-------|
| **Tool-use policy** | Wann welches Tool aufrufen, in welcher Reihenfolge |
| **Loop avoidance** | Nicht 30x dasselbe Tool aufrufen |
| **Correct finish conditions** | Nach doc_writer sofort stoppen, kurze Bestaetigung |
| **Doc chunking pattern** | Bei grossen Kapiteln: Outline zuerst, dann Abschnitte einzeln |

### Trainingsdaten-Quellen

Die Daten existieren bereits im Projekt:

1. **Erfolgreiche Runs** (Positive Beispiele):
   - `logs/metrics.jsonl` — welche Mini-Crews erfolgreich liefen
   - CrewAI verbose logs — exakte Tool-Call-Sequenzen
   - `knowledge/architecture/arc42/*.md` — erwartete Outputs

2. **Gescheiterte Runs** (Negative Beispiele):
   - Runs wo Agent Content in Response schrieb statt doc_writer
   - Runs mit Tool-Loops (30x get_architecture_summary)
   - Runs mit ChatCompletionMessageToolCall-Fehler

### Trainings-Format

```json
{
  "messages": [
    {"role": "system", "content": "You are a Senior Software Architect..."},
    {"role": "user", "content": "Create arc42 Chapter 05: Building Blocks..."},
    {"role": "assistant", "content": null, "tool_calls": [
      {"function": {"name": "get_statistics", "arguments": "{}"}}
    ]},
    {"role": "tool", "content": "{\"components\": 738, ...}"},
    {"role": "assistant", "content": null, "tool_calls": [
      {"function": {"name": "list_components_by_stereotype", "arguments": "{\"stereotype\": \"service\"}"}}
    ]},
    {"role": "tool", "content": "[{\"name\": \"DeedEntryService\", ...}]"},
    {"role": "assistant", "content": null, "tool_calls": [
      {"function": {"name": "doc_writer", "arguments": "{\"file_path\": \"arc42/05-building-blocks.md\", \"content\": \"# 05 - Building Block View\\n...\"}"}}
    ]},
    {"role": "tool", "content": "File written successfully."},
    {"role": "assistant", "content": "File arc42/05-building-blocks.md written successfully (12 pages)."}
  ]
}
```

### Tooling

| Tool | Zweck |
|------|-------|
| **Unsloth** | LoRA Training (2x schneller, 50% weniger VRAM) |
| **Axolotl** | Alternative zu Unsloth, YAML-Config basiert |
| **vLLM** | Serving des fine-tuned Modells |
| **Weights & Biases** | Experiment-Tracking |

### Erwartete Verbesserung
- Tool-Use Compliance: ~95% → ~99%
- Tool-use policy internalisiert (Reihenfolge, Stop-Condition)
- Weniger Tokens pro Task (Modell weiss was zu tun ist)
- ~50-100 Trainingbeispiele reichen (wenn gut kuratiert)

---

## Phase 4: Spezialisierter Tool-Router (optional, fortgeschritten)

### Was
Separation of Concerns: Ein Planner/Router entscheidet **welche Tools**, das grosse Modell schreibt **den Content**.

### Pragmatischer Ansatz (80% des Nutzens ohne extra Modell)

> Du kannst 80% des Tool-Router-Nutzens erreichen mit einem **deterministischen Planner** (Regeln + Heuristiken), ohne ein zweites Modell:

```python
# Deterministic Tool Planner (no LLM needed)
class ToolPlanner:
    PLANS = {
        "c4-context": ["get_statistics", "get_containers", "get_external_systems"],
        "c4-container": ["get_statistics", "get_containers", "get_relations"],
        "arc42-05": ["get_statistics", "list_components_by_stereotype:controller",
                     "list_components_by_stereotype:service", "get_endpoints"],
        # ... one plan per task
    }

    def get_plan(self, task_key: str) -> list[str]:
        return self.PLANS.get(task_key, ["get_statistics"])
```

### Volle Architektur (wenn deterministisch nicht reicht)

```
Task Description
      |
      v
[Tool Router 7B] ---> get_statistics()
      |                get_endpoints()
      |                list_components_by_stereotype("service")
      |                ...
      v
[Content Writer 70B] ---> doc_writer(file_path, content)
      |
      v
Output File
```

### Vorteil
- Router ist schnell + guenstig (7B oder deterministisch)
- Writer hat vollen Context fuer Content-Qualitaet (70B)
- Separation of Concerns: Tool-Use vs. Text-Generierung

### Aufwand
- Deterministischer Planner: 2-3 Tage
- LLM-basierter Router: 2-3 Wochen + eigenes Orchestration-Layer

---

## Empfohlener Pfad

```
✅ DONE:      Phase 0.5 — Guardrails + Stop Conditions + Loop Breaker
              (tool_guardrails.py, TOOL_INSTRUCTION rules, output gate)

✅ DONE:      Phase 1 — Few-Shot + Tool-Policy zentral
              (TOOL_INSTRUCTION with examples, per-task EXECUTION EXAMPLE blocks)

✅ DONE:      Phase 1.5 — Output Quality Maximierung
              - Token limits: 32K→100K input, 4K→16K output, 32K→120K context
              - Tool guardrails: 10→25 max calls, 2→3 max identical
              - Chapter splitting: Ch06 (2 sub-crews), Ch08 (2 sub-crews)
              - Task descriptions: explicit sections, 8-12 pages target, more tool calls
              - MapReduce: dynamic patterns (no hardcoded strings), multi-dim quality
              - Arc42 mini-crews: 16→18 (4 new sub-crews, 2 old removed)
              - Expected: ~46 pages → 100-120 pages, pipeline ~45-60 min

Naechster:    Phase 4 — Deterministischer Tool-Planner
              (Pre-fetch MCP data in Python, agent only writes content)
              Hoechster ROI mit 120B model + guardrails

Spaeter:      Phase 2 — Modellwechsel (nur wenn Hardware-Upgrade verfuegbar)
              Phase 3 — LoRA Fine-Tuning (Trainingsdaten aus erfolgreichen Runs)
```

---

## Metriken zum Tracken

### Kern-Metriken

| Metrik | Aktuell | Ziel Ph 0.5 | Ziel Ph 1+2 | Ziel Ph 3 |
|--------|---------|-------------|-------------|-----------|
| Files geschrieben / erwartet | ~70% | ~90% | ~95% | ~99% |
| Tool-Loops pro Crew | 1-2 | 0 | 0 | 0 |
| Crashes (Pydantic/max_iter) | ~20% | ~5% | ~2% | ~0% |
| Tokens pro Chapter | ~35K | ~30K | ~25K | ~15K |
| Durchschnittliche Crew-Dauer | ~80s | ~70s | ~60s | ~40s |

### Neue Metrik: Tool-Compliance Rate (wichtigste Metrik!)

| Metrik | Beschreibung | Wie messen |
|--------|-------------|------------|
| **Tool-Compliance Rate pro Step** | % der Tasks die doc_writer innerhalb der ersten N Schritte aufrufen | Log-Analyse: erster doc_writer call / total steps |
| **Median Tool Calls before First Write** | Wie viele Tool-Calls braucht der Agent bis zum ersten doc_writer | CrewAI verbose logs parsen |
| **First-Write Latency** | Zeit bis zum ersten doc_writer call | timestamps aus logs |

> Diese Metrik korreliert extrem stark mit Stabilitaet + Tokenkosten. Ein Agent der nach 4 Tool-Calls schreibt ist 5x stabiler als einer der 15 braucht.

```python
# Tool-Compliance tracking (add to base_crew.py metrics)
def log_tool_compliance(task_name, tool_calls, doc_writer_called_at_step):
    log_metric("tool_compliance", {
        "task": task_name,
        "total_tool_calls": len(tool_calls),
        "doc_writer_step": doc_writer_called_at_step,  # None if never called
        "compliance": doc_writer_called_at_step is not None,
        "efficiency": doc_writer_called_at_step / len(tool_calls) if doc_writer_called_at_step else 0,
    })
```

---

## Daten-Pipeline fuer Training

### Schritt 1: Logs sammeln
```bash
# Erfolgreiche Runs produzieren Traces in:
logs/metrics.jsonl              # Strukturierte Events
logs/aicodegencrew.log          # Verbose CrewAI output mit Tool-Calls
```

### Schritt 2: Traces extrahieren
```python
# Aus CrewAI verbose logs Tool-Call-Sequenzen extrahieren:
# - Tool name + arguments
# - Tool result (truncated)
# - Final agent response
# -> Format als OpenAI chat completion mit tool_calls
```

### Schritt 3: Quality Filter
```python
# Nur Traces wo:
# 1. Erwartete Output-Files existieren
# 2. Files > 1000 Zeichen (kein leerer Output)
# 3. Keine Tool-Loops (max 5 gleiche Tool-Calls)
# 4. doc_writer wurde aufgerufen (nicht Response-Text)
# 5. doc_writer innerhalb der ersten 8 Steps (efficiency)
```

### Schritt 4: Train
```bash
# LoRA auf gefilterten Traces
python train_lora.py --base-model qwen2.5-72b --data traces/filtered/ --epochs 3
```

---

*Erstellt: 2026-02-07*
*Aktualisiert: 2026-02-08 (Phase 0.5 + Phase 1 + Phase 1.5 IMPLEMENTED)*
*Projekt: AICodeGenCrew*
