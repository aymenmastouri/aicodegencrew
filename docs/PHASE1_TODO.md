# Phase 1 - Architecture Facts Extraction - TODO

**Stand:** 2026-02-05  
**Letzter Lauf:** 733 components, 125 interfaces, 169 relations, 1005 evidence

---

## ✅ Erledigt

- [x] Progressive JSON Writing (jeder Collector schreibt sofort)
- [x] `architecture_facts.json` als kombinierte Datei am Ende
- [x] SpringRestCollector: Interfaces mit `@RequestMapping` erkennen
- [x] AngularServiceCollector: Endpoints, Adapters, Guards, Interceptors
- [x] JS API Pattern: `static ENDPOINT = '...'` erkennen
- [x] Alle Collector-Logs einheitlich (Found → DEBUG)
- [x] Generische Patterns (keine projektspezifischen Strings)
- [x] ModelBuilder: Alte/neue Attribute kompatibel

---

## 🔴 Kritisch

### 1. Relation Resolution (~46% Verlust)
**Problem:** 313 Relation Hints → nur 169 resolved  
**Ursache:** `from_id`/`to_id` können nicht auf Component IDs gemappt werden  
**Lösung:** Fuzzy Matching implementieren
- Name-basiertes Matching (case-insensitive)
- Klassen-Suffix ignorieren (`Impl`, `Service`, etc.)
- Container-Prefix matchen

### 2. Endpoint Flows: 0 gebaut
**Problem:** `implemented_by` in Interfaces ist leer  
**Ursache:** SpringRestCollector setzt `implemented_by` nicht  
**Lösung:** 
```python
# In SpringRestCollector bei Endpoint-Erstellung:
interface.implemented_by = controller_name  # z.B. "WorkflowRestServiceImpl"
```

---

## 🟡 Wichtig

### 3. Tables nicht im finalen Model
**Problem:** OracleTableCollector findet 177 Tables, aber `Tables: 0` im Output  
**Ursache:** DataModelCollector → CanonicalModel Mapping fehlt  
**Lösung:** `dimension_writers.py` oder `model_builder.py` erweitern

### 4. Migrations nicht gezählt
**Problem:** 54 Flyway Migrations erkannt, aber `Migrations: 0`  
**Ursache:** Gleiches Problem wie Tables  
**Lösung:** Migration-Facts ins Model übernehmen

### 5. Component Deduplication verbessern
**Problem:** 813 → 733 components (10% Verlust)  
**Frage:** Werden echte Duplikate entfernt oder gehen Infos verloren?  
**Aktion:** Dedup-Logik reviewen, evtl. Merge statt Drop

---

## 🟢 Nice-to-Have

### 6. Evidence Linking verbessern
- [ ] Evidence IDs konsistent über alle Collectors
- [ ] Chunk IDs für RAG-Integration vorbereiten

### 7. Mehr Interface-Typen
- [ ] GraphQL Endpoints
- [ ] gRPC Services  
- [ ] WebSocket Handlers
- [ ] Message Listeners (Kafka, RabbitMQ)

### 8. Cross-Container Relations
- [ ] Frontend → Backend API Calls erkennen
- [ ] Service → Service Calls über Container-Grenzen

### 9. Test Coverage
- [ ] Unit Tests für jeden Collector
- [ ] Integration Test für volle Pipeline
- [ ] Snapshot Tests für Output-Formate

---

## 📊 Metriken zum Tracken

| Metrik | Aktuell | Ziel |
|--------|---------|------|
| Relation Resolution Rate | 54% | >85% |
| Endpoint Flows | 0 | >50 |
| Tables im Model | 0 | 177 |
| Migrations im Model | 0 | 54 |

---

## 🏗️ Architektur-Notizen

### Collector → Model Pipeline
```
Collectors (10 Steps)
    ↓
Raw Facts (CollectedComponent, CollectedInterface, etc.)
    ↓
FactAdapter (Normalisierung)
    ↓
ModelBuilder (Dedup, ID-Generation, Relation Resolution)
    ↓
CanonicalModel (733 components, 125 interfaces, 169 relations)
    ↓
DimensionWriters (11 JSON files)
```

### ID-Mapping Problem
```
Raw: "backend_WorkflowRestServiceImpl"
Canonical: "component.backend.workflowrestserviceimpl"

Relation: from_id="WorkflowRestServiceImpl" → nicht gefunden!
```

**Fix:** Name-to-ID Index aufbauen vor Relation Resolution

---

## Nächste Session

1. **Relation Resolution fixen** - größter Impact
2. **implemented_by setzen** - Endpoint Flows enablen
3. **Tables/Migrations** ins Model bringen

---

## ❓ Evaluiert: Lokales Modell / Fine-Tuning / MCP

**Frage:** UVZ mit lokalem Modell trainieren und als MCP in Pipeline integrieren?

### Bewertung: ❌ Nicht empfohlen für Phase 1

| Aspekt | Analyse |
|--------|---------|
| **Phase 1 ist deterministisch** | Regex, Pattern Matching, AST - kein LLM nötig |
| **Aktuelle Probleme** | ID-Mapping, nicht Verständnis - technisch lösbar |
| **Training-Aufwand** | Wochen/Monate für marginalen Gewinn |
| **MCP Overhead** | HTTP-Roundtrips für etwas das in 0.1ms lokal läuft |

### Aktuelle Probleme sind keine LLM-Probleme:

```
❌ Lokales Modell hilft NICHT bei:
   - Relation Resolution → ist ein Index/Lookup Problem
   - implemented_by → ist ein Collector-Logik Problem  
   - Tables/Migrations → ist ein Mapping Problem

✅ Besser investierte Zeit:
   - Name-to-ID Index aufbauen (10 Zeilen Code)
   - Controller→Endpoint Mapping im Collector (20 Zeilen)
   - DataModel ins CanonicalModel bringen (50 Zeilen)
```

### Wo ein lokales/fine-tuned Modell SINN machen könnte:

| Phase | Nutzen | Empfehlung |
|-------|--------|------------|
| **Phase 2 (Synthese)** | Arc42/C4 Texte generieren | Generisches Modell reicht |
| **Code Generation** | UVZ-spezifischen Code generieren | Später evaluieren |
| **Domänen-QA** | Fragen zu Notariat/Workflow | RAG mit Facts effizienter |

### Empfohlene Alternative: RAG statt Fine-Tuning

```
Phase 1 Facts (733 components, 169 relations, etc.)
    ↓
Als Kontext für generisches LLM (GPT-4, Claude, etc.)
    ↓
Domänen-spezifische Antworten OHNE Training
```

**Vorteile RAG:**
- Kein Training nötig
- Immer aktuelle Daten
- Funktioniert mit jedem LLM
- Nachvollziehbare Quellen (Evidence)

**Fazit:** Erst Phase 1 technisch optimieren, dann RAG-basierte Phase 2. Fine-Tuning nur wenn RAG nicht ausreicht.
