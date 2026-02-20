# LLM Selection Guide — AICodeGenCrew

> **Ziel**: Welches LLM für welche Phase, und warum das Modell den größten
> Einfluss auf die Output-Qualität hat.

---

## 1. Anforderungsprofil der Pipeline

Die Pipeline stellt je nach Phase unterschiedliche Anforderungen an das LLM:

| Anforderung | Betroffene Phasen | Warum kritisch |
|-------------|------------------|----------------|
| **Tool Use / Function Calling** | Alle Crews | Agents rufen 10+ Tools auf (rag_query, doc_writer, list_components_by_stereotype, …) |
| **Langer Output** | Phase 3 (Docs), Phase 5 (Code-Gen) | Arc42-Kapitel = 6–12 Seiten; Code-Gen = ganze Quelldateien |
| **JSON Schema Following** | Phase 4 (Plan) | ImplementationPlan-Objekt muss exaktem Schema entsprechen |
| **Code-Verständnis** | Phase 5 (Implement) | Code lesen, Imports auflösen, Build-Errors selbst heilen |
| **Instruction Following** | Alle Phasen | Golden Rules, Execution Examples, Section-Reihenfolge |

---

## 2. Aktuelle Schwächen des on-prem Modells (gpt-oss-120b)

| Problem | Ursache | Konsequenz |
|---------|---------|------------|
| Output-Truncation | 4 000-Token Output-Cap | LLM schreibt z. B. Sections 8.1–8.2, bricht dann ab |
| JSON-Schema-Verletzungen | Schwächeres Instruction-Following | Phase 4 gibt Strings statt Dicts zurück → Repair-Code nötig |
| Stub-Outputs | Max-Iter erschöpft, falsche Tool-Calls | LLM versucht nicht-existente Tools, scheitert, gibt leeren Stub zurück |
| Schwache Planqualität | Schwächeres Reasoning | Implementation Steps ohne File Paths, vage Beschreibungen |
| Schlechte Selbstheilung | Schwaches Code-Verständnis | Build-Errors werden nicht immer korrekt interpretiert |

> **Wichtig**: Das LLM ist nicht die einzige Variable. Die Pipeline hat
> zwei Engpässe — LLM-Qualität **und** Kontext-Qualität (was als Input
> übergeben wird). Beide müssen stimmen.

---

## 3. Modell-Empfehlungen

### 3.1 Cloud-Modelle (beste Qualität)

| Modell | Stärken | Empfohlene Rolle |
|--------|---------|-----------------|
| **Claude Opus 4.6** | Bestes Reasoning, bestes Instruction-Following, langer Output | `MODEL` (Planung, Docs, Manager-Agent) |
| **Claude Sonnet 4.6** | Sehr gute Code-Qualität, schnell, gutes Tool-Use | `CODEGEN_MODEL` (Developer, Tester) |
| **GPT-4o** | Stärkstes Tool-Use, JSON-Schema zuverlässig, EU-Hosting möglich | `MODEL` oder `CODEGEN_MODEL` |
| **GPT-4o-mini** | Schnell, günstig, ausreichend für einfache Code-Gen-Tasks | `CODEGEN_MODEL` (kostengünstige Option) |

### 3.2 On-Prem Open-Source-Modelle (wenn Cloud nicht möglich)

| Modell | Stärken | Empfohlene Rolle |
|--------|---------|-----------------|
| **Llama 3.3 70B** (gut quantisiert) | Besseres Tool-Use als 120B-Quantisiert, geringere Quantisierungsverluste | `MODEL` |
| **Qwen2.5-Coder 72B** | Speziell für Code-Gen trainiert, sehr stark bei Code-Verständnis | `CODEGEN_MODEL` |
| **Mistral Large 2** | Gutes Instruction-Following, on-prem deploybar | `MODEL` |

> **Hinweis zur Quantisierung**: Ein 70B-Modell mit Q8-Quantisierung
> übertrifft oft ein 120B-Modell mit Q4-Quantisierung. Weniger Parameter,
> aber höhere Präzision = bessere Ausgaben.

---

## 4. Konkrete Konfigurationsempfehlung

### Option A — Azure OpenAI (empfohlen für Capgemini)

```env
LLM_PROVIDER=azure
MODEL=gpt-4o
CODEGEN_MODEL=gpt-4o-mini
```

**Vorteile**: Enterprise-approved, EU-Data-Residency möglich,
kein VPN-Problem, höherer Rate-Limit.

---

### Option B — Anthropic Claude (beste Qualität)

```env
LLM_PROVIDER=anthropic
MODEL=claude-opus-4-6
CODEGEN_MODEL=claude-sonnet-4-6
```

**Vorteile**: Bestes Instruction-Following, höchster Output-Token-Limit,
hervorragendes Code-Verständnis für Phase 5.

---

### Option C — On-Prem Upgrade (wenn Cloud nicht genehmigt)

```env
LLM_PROVIDER=onprem
MODEL=llama-3.3-70b          # statt gpt-oss-120b
CODEGEN_MODEL=qwen2.5-coder-72b
```

**Vorteile**: Kein Datenschutzproblem, kein VPN-Konflikt mit Builds.
**Nachteil**: Schlechtere Qualität als Cloud-Modelle.

---

## 5. Erwarteter Qualitätsgewinn pro Phase

| Phase | Aktuell (120B on-prem) | Mit GPT-4o / Claude |
|-------|----------------------|---------------------|
| Phase 3 — Arc42-Docs | Stubs, abgebrochene Kapitel | Vollständige 6–12-Seiten-Kapitel |
| Phase 4 — Plan | File Paths fehlen, vage Steps | Konkrete Steps mit Pfaden, vollständige JSON-Objekte |
| Phase 5 — Code-Gen | ~3/10 bei VPN-Drop, Repair nötig | 9–10/10, bessere Selbstheilung |
| Phase 6 — Tests | Generische Tests | Framework-spezifische Tests (JUnit, Jasmine) |

---

## 6. VPN-Konflikt (spezifisch für aktuelle Umgebung)

Das aktuelle Setup hat einen strukturellen Konflikt:

- **VPN an** → LLM-API erreichbar, aber Gradle-Builds schlagen fehl
- **VPN aus** → Builds funktionieren, aber LLM-API nicht erreichbar

**Lösung mit Azure OpenAI**: Kein VPN nötig (Azure ist direkt erreichbar).
Das eliminiert diesen Konflikt vollständig und ermöglicht stabiles
Code-Gen + Build-Verify in einem Durchlauf.

---

## 7. Fazit

```
Besseres LLM + aktuelle Prompt-Verbesserungen = größter möglicher Qualitätssprung.
```

Priorität:

1. **Azure OpenAI GPT-4o** — realistischster Upgrade-Pfad, löst gleichzeitig
   das VPN-Problem
2. **Anthropic Claude** — beste reine Qualität, falls Zugang genehmigbar
3. **Qwen2.5-Coder on-prem** — wenn nur on-prem möglich, speziell für
   Code-Gen deutlich besser als das aktuelle Modell
