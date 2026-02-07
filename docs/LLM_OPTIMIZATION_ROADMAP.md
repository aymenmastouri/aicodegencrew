# LLM Optimization Roadmap

## Current State (February 2026)

**Model**: `gpt-oss-120b` (on-prem, OpenAI-compatible API)
**Problems observed**:
- Agent ignores `TOOL_INSTRUCTION` and writes document content in response text instead of using `doc_writer` tool
- Agent loops on MCP tools (calls `get_architecture_summary` 30+ times without progress)
- Agent returns raw `ChatCompletionMessageToolCall` objects instead of text when hitting `max_iter`
- Missing output files despite crew marked as "completed"

**Root cause**: On-prem model has weak function calling / tool-use capabilities compared to commercial models (GPT-4o, Claude).

---

## Phase 1: Few-Shot Prompting (0 Aufwand, sofort umsetzbar)

### Was
Erfolgreiche Tool-Use-Sequenzen als Beispiele direkt in die Task-Descriptions einbauen.

### Wie
In jeder Task-Description (z.B. `CH05_BUILDING_BLOCKS`) ein konkretes Beispiel ergaenzen:

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
- Tool-Use Compliance: ~60% -> ~85%
- Kosten: 0 (nur Prompt-Aenderung)
- Aufwand: 2-4 Stunden

---

## Phase 2: Modellwechsel (1 Tag Aufwand)

### Empfohlene On-Prem Modelle mit nativem Function Calling

| Modell | Parameter | Tool-Use | VRAM | Bemerkung |
|--------|-----------|----------|------|-----------|
| **Qwen2.5-72B-Instruct** | 72B | Sehr gut | ~80 GB | Bestes Open-Source Tool-Use |
| **Llama 3.1 70B Instruct** | 70B | Gut | ~80 GB | Meta, breit getestet |
| **Mistral Large 2 (123B)** | 123B | Sehr gut | ~140 GB | Function Calling nativ trainiert |
| **DeepSeek-V2.5** | 236B MoE | Sehr gut | ~80 GB (aktiv) | MoE = weniger VRAM als erwartet |
| **Command R+ (104B)** | 104B | Sehr gut | ~120 GB | Cohere, tool-use fokussiert |

### Aenderung
Nur `.env` anpassen:
```env
MODEL=qwen2.5-72b-instruct
# oder
MODEL=meta-llama/Llama-3.1-70B-Instruct
```

Kein Code-Aenderung noetig — LiteLLM/vLLM kompatibel.

### Erwartete Verbesserung
- Tool-Use Compliance: ~85% -> ~95%
- Output-Qualitaet: Deutlich bessere Dokumentation
- Kosten: Modell-Download + vLLM Setup

---

## Phase 3: LoRA Fine-Tuning (1-2 Wochen Aufwand)

### Was
Ein LoRA-Adapter (Low-Rank Adaptation) auf dem gewaehlten Base-Model, trainiert auf die spezifischen MCP-Tool-Sequenzen dieses Projekts.

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

### Training-Script Skeleton

```python
from unsloth import FastLanguageModel

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="Qwen/Qwen2.5-72B-Instruct",
    max_seq_length=8192,
    load_in_4bit=True,
)

model = FastLanguageModel.get_peft_model(
    model,
    r=16,                   # LoRA rank
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_alpha=16,
    lora_dropout=0,
    use_gradient_checkpointing="unsloth",
)

# Train on tool-use sequences from successful runs
trainer = SFTTrainer(
    model=model,
    train_dataset=tool_use_dataset,  # From CrewAI logs
    max_seq_length=8192,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=4,
    num_train_epochs=3,
    learning_rate=2e-4,
)
trainer.train()
```

### Erwartete Verbesserung
- Tool-Use Compliance: ~95% -> ~99%
- Repo-spezifisches Wissen (UVZ Domain, MCP Tools)
- Weniger Tokens pro Task (Modell weiss was zu tun ist)
- ~50-100 Trainingbeispiele reichen

---

## Phase 4: Spezialisierter Tool-Router (optional, fortgeschritten)

### Was
Ein kleines Modell (7B-13B) das NUR Tool-Routing macht:
- Welches MCP Tool aufrufen?
- Mit welchen Parametern?
- Wann ist genug Daten gesammelt -> doc_writer aufrufen?

Das grosse Modell (70B+) macht dann NUR den Content fuer doc_writer.

### Architektur
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
- Router ist schnell + guenstig (7B)
- Writer hat vollen Context fuer Content-Qualitaet (70B)
- Separation of Concerns: Tool-Use vs. Text-Generierung

### Aufwand
- 2-3 Wochen Entwicklung
- Eigenes Orchestration-Layer (nicht mehr CrewAI)
- Separate Training-Pipeline fuer Router

---

## Empfohlener Pfad

```
Jetzt:      Few-Shot Prompting (Phase 1)
Woche 1:    Modellwechsel auf Qwen2.5-72B (Phase 2)
Monat 1-2:  LoRA Fine-Tuning mit eigenen Daten (Phase 3)
Spaeter:    Tool-Router wenn noetig (Phase 4)
```

## Metriken zum Tracken

| Metrik | Aktuell | Ziel Phase 1 | Ziel Phase 3 |
|--------|---------|--------------|--------------|
| Files geschrieben / Files erwartet | ~70% | ~85% | ~99% |
| Tool-Loops pro Crew | 1-2 | 0-1 | 0 |
| Crashes (Pydantic/max_iter) | ~20% | ~5% | ~0% |
| Tokens pro Chapter | ~35K | ~25K | ~15K |
| Durchschnittliche Crew-Dauer | ~80s | ~60s | ~40s |

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
```

### Schritt 4: Train
```bash
# LoRA auf gefilterten Traces
python train_lora.py --base-model qwen2.5-72b --data traces/filtered/ --epochs 3
```

---

*Erstellt: 2026-02-07*
*Projekt: AICodeGenCrew*
