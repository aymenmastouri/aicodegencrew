# Feature Plan: Expert-Level RAG Architecture

## Ziel

Die RAG-Suche (Retrieval-Augmented Generation) von "funktioniert" auf "Production-Grade Expert-Level" heben. Aktuell nutzen 6 von 8 Phasen die RAG-Suche — jede Verbesserung hier wirkt sich direkt auf die Qualität aller Analyse-, Dokumentations- und Code-Generierungs-Ergebnisse aus.

---

## Status Quo

| Aspekt | Aktuell | Bewertung |
|--------|---------|-----------|
| **Chunking** | Fix 1800 Zeichen | Schneidet Methoden/Klassen durch |
| **Embedding** | Single Dense Vector (Ollama/Platform) | Findet keine exakten Keywords |
| **Suche** | Cosine Similarity Top-K | Keine Keyword-Suche, kein Reranking |
| **Query** | 1 Query → 1 Ergebnis-Set | Schmale Recall bei komplexen Fragen |
| **Zugang** | CrewAI BaseTool only | Nicht nutzbar außerhalb von Agents |
| **Backend** | Qdrant (neu) | Gute Basis, Features ungenutzt |

---

## Feature 1: Hybrid Search (Dense + Sparse Vectors)

### Problem
Agent sucht `"@PreAuthorize"` → Dense Embedding versteht die Semantik ("security annotation"), findet aber den exakten String nicht zuverlässig. Ergebnis: Agent bekommt irrelevante Snippets, halluziniert oder gibt auf.

### Lösung
Qdrant unterstützt **Named Vectors** — pro Chunk zwei Vektoren:
- **Dense Vector** (Embedding): semantische Ähnlichkeit ("Sicherheits-Konfiguration")
- **Sparse Vector** (BM25/SPLADE): exakte Keyword-Matches ("@PreAuthorize")

Query kombiniert beide via **Reciprocal Rank Fusion (RRF)** — das Beste aus beiden Welten.

### Beispiel
```
Query: "@PreAuthorize security role check"

Dense only:  SecurityConfig.java (0.82), AuthFilter.java (0.79), LoginController.java (0.75)
Sparse only: UserController.java:@PreAuthorize (0.95), AdminService.java:@PreAuthorize (0.90)
Hybrid RRF:  UserController.java (0.93), AdminService.java (0.88), SecurityConfig.java (0.82)
```

### Benefit
- **+30-40% Precision** bei Keyword-lastigen Queries (Annotations, Klassennamen, Config-Keys)
- Kein Qualitätsverlust bei semantischen Queries
- Nativ in Qdrant — keine externe Dependency

### Aufwand
Klein — Qdrant API unterstützt es, Änderungen nur in `qdrant_client.py` und `rag_query_tool.py`.

---

## Feature 2: AST-basiertes Chunking

### Problem
Fixer 1800-Zeichen-Chunk schneidet eine 2500-Zeichen Java-Methode in zwei Teile. Agent bekommt die erste Hälfte einer Methode → versteht den Kontext nicht → falsche Analyse.

### Lösung
Code-aware Chunking basierend auf Abstract Syntax Tree (AST):
- **Java/Kotlin**: Klasse → Methode → Inner Class (tree-sitter oder javalang)
- **TypeScript/JS**: Module → Function → Class Method
- **Python**: Module → Class → Function
- **Config (YAML/XML/properties)**: Logische Blöcke

Hierarchisches Parent-Child Schema:
```
Chunk: UserService.createUser()
├── Parent: UserService (Klassen-Signatur + Felder)
├── Content: Methoden-Body komplett
├── Children: [aufgerufene private Methoden]
└── Overlap: Import-Statements + Annotations
```

### Benefit
- **Semantisch vollständige Einheiten** — keine durchgeschnittenen Methoden
- **Parent-Context** — Agent versteht zu welcher Klasse ein Snippet gehört
- **Bessere Embeddings** — semantisch kohärente Chunks ergeben bessere Vektoren

### Aufwand
Mittel — neuer Chunker neben dem bestehenden, konfigurierbar via env var.

---

## Feature 3: Reranking (Two-Stage Retrieval)

### Problem
Top-10 aus Cosine Similarity enthält oft 3-4 irrelevante Treffer. Agent verschwendet Context-Window mit Noise.

### Lösung
Zwei-stufiges Retrieval:
1. **Stage 1 (Bi-Encoder)**: Schnell, holt Top-50 Kandidaten aus Qdrant
2. **Stage 2 (Cross-Encoder)**: Langsam aber präzise, rankt die 50 auf Top-10 um

Cross-Encoder vergleicht Query+Dokument als Paar (nicht separat wie Bi-Encoder) → versteht Nuancen besser.

```
Stage 1 (50 Ergebnisse, 20ms):
  1. SecurityConfig.java        0.85
  2. TestSecurityConfig.java     0.83  ← irrelevant (Test)
  3. UserController.java         0.82
  4. SecurityConstants.java      0.81  ← irrelevant (nur Konstanten)
  ...

Stage 2 (Top-10, 200ms):
  1. UserController.java         0.94  ← hochgestuft
  2. SecurityConfig.java         0.91
  3. AuthService.java            0.88  ← war Platz 7, jetzt Top-3
  ...
  (Tests und Konstanten rausgefiltert)
```

### Benefit
- **+20% Precision** in Top-10 Ergebnissen
- Weniger Noise im Agent-Context → weniger Halluzination
- Weniger Token-Verbrauch (relevantere Snippets = kürzere Prompts)

### Aufwand
Klein — wenn die Plattform ein Cross-Encoder Modell hat (z.B. `rerank` Endpoint auf LiteLLM). Sonst: lokales Modell via sentence-transformers.

---

## Feature 4: Query Expansion

### Problem
Agent fragt `"security annotations"` → findet Spring Security, aber verpasst Custom-Security-Pattern die anders benannt sind.

### Lösung
Vor der Suche: LLM generiert 3 Sub-Queries aus der Original-Query:
```
Original: "security annotations"
Expanded:
  1. "@PreAuthorize @Secured @RolesAllowed Spring Security"
  2. "authentication authorization filter middleware"
  3. "role-based access control RBAC permission check"
```

Alle 3 Queries → Qdrant → Ergebnisse mergen → Deduplizieren → Top-K.

### Benefit
- **+25% Recall** — findet relevante Snippets die eine einzelne Query verpasst
- Besonders wertvoll bei vagen Queries ("wie funktioniert der Login?")
- LLM-Kosten minimal (1 schneller Call mit FAST_MODEL)

### Aufwand
Klein — 20 Zeilen Code im RAG Query Tool, nutzt bestehende LLM-Factory.

---

## Feature 5: Named Vectors (Code + Summary)

### Problem
Query `"wie funktioniert der Login?"` matched schlecht auf Raw-Code, weil Code keine natürliche Sprache ist.

### Lösung
Zwei Embeddings pro Chunk:
- **`code`**: Embedding vom Raw-Code (für Code-Queries: "@PreAuthorize", "class UserService")
- **`summary`**: Embedding von LLM-generierter Zusammenfassung (für natürliche Queries: "Login-Flow", "Wie werden Benutzer authentifiziert?")

Summary wird einmalig beim Indexing generiert (Batch, FAST_MODEL):
```
Code:    public User authenticate(String username, String password) { ... }
Summary: "Authentifiziert einen Benutzer anhand Username und Passwort.
          Prüft Credentials gegen die Datenbank, erstellt JWT Token bei Erfolg,
          wirft AuthenticationException bei Fehler."
```

### Benefit
- **Bridging the Gap** zwischen natürlicher Sprache und Code
- Agent-Queries in natürlicher Sprache → deutlich bessere Treffer
- Qdrant Named Vectors = eine Collection, zwei Suchpfade

### Aufwand
Groß — Re-Indexing nötig (jeder Chunk braucht LLM-Call für Summary). Bei 10.000 Chunks = ca. 10.000 FAST_MODEL Calls. Einmalig.

---

## Feature 6: MCP Tool Interface

### Problem
RAG-Suche ist ein CrewAI `BaseTool` — nur nutzbar innerhalb von CrewAI-Agents. Deterministische Phasen, Dashboard, CLI und externe Tools können es nicht nutzen.

### Lösung
RAG als MCP Server Tools exposen (basierend auf tatsächlichen Nutzungsmustern im Code):

| MCP Tool | Beschreibung | Aktueller Caller |
|----------|-------------|------------------|
| `rag_search` | Semantische Suche mit query, limit, file_filter, content_type | 6 Phasen (analyze, document, triage, plan, implement, review) |
| `rag_index_status` | Collection Count + Fingerprint + letzte Indexierung | Dashboard, CLI |
| `rag_reindex` | Inkrementelles Re-Indexing triggern | Dashboard Run-Button |

Zugang über:
- **Agents** → MCP Tool direkt (statt CrewAI BaseTool)
- **Pipelines** → MCP Client Call
- **Dashboard** → über MCPO HTTP Proxy
- **Extern** → über MCPO HTTP (REST API)

### Benefit
- **Ein Interface für alle Consumer** — kein Doppelcode
- Remote-fähig via MCPO (HTTP)
- Testbar ohne CrewAI-Setup
- Dashboard kann RAG-Status anzeigen und Re-Indexing triggern

### Aufwand
Mittel — MCP Server existiert schon (`aicodegencrew-mcp`), Tools hinzufügen.

---

## Feature 7: Payload Indexes + Quantization (Qdrant Optimierung)

### Problem
Bei großen Repos (10.000+ Chunks) werden gefilterte Queries langsam, und der RAM-Verbrauch steigt.

### Lösung
Qdrant-spezifische Optimierungen:

**Payload Indexes** auf häufig gefilterte Felder:
```python
client.create_payload_index("repo_docs_uvz_master", "file_path", PayloadSchemaType.KEYWORD)
client.create_payload_index("repo_docs_uvz_master", "content_type", PayloadSchemaType.KEYWORD)
client.create_payload_index("repo_docs_uvz_master", "repo_path", PayloadSchemaType.KEYWORD)
```

**Scalar Quantization** für RAM-Einsparung:
```python
client.update_collection(
    "repo_docs_uvz_master",
    quantization_config=ScalarQuantization(type=ScalarType.INT8, always_ram=True)
)
```

### Benefit
- **10x schnellere gefilterte Queries** (file_path Filter)
- **4x weniger RAM** bei gleicher Qualität (INT8 Quantization)
- Kein Qualitätsverlust in der Praxis (< 1% Recall-Verlust)

### Aufwand
Klein — 5 Zeilen Code in `qdrant_client.py` nach Collection-Erstellung.

---

## Implementierungs-Reihenfolge

| Prio | Feature | Impact | Aufwand | Abhängigkeit |
|------|---------|--------|---------|-------------|
| 1 | **Payload Indexes + Quantization** | Hoch | Klein | Qdrant läuft ✅ |
| 2 | **Hybrid Search (Dense + Sparse)** | Hoch | Klein | Qdrant läuft ✅ |
| 3 | **Query Expansion** | Mittel | Klein | LLM Factory ✅ |
| 4 | **AST Chunking** | Hoch | Mittel | Keine |
| 5 | **Reranking** | Mittel | Klein | Rerank-Modell auf Plattform |
| 6 | **MCP Tool Interface** | Mittel | Mittel | MCP Server existiert ✅ |
| 7 | **Named Vectors (Code + Summary)** | Hoch | Groß | Re-Index nötig |

---

## Erwartete Gesamt-Verbesserung

| Metrik | Aktuell | Nach Features 1-4 | Nach allen Features |
|--------|---------|-------------------|-------------------|
| **Precision@10** | ~60% | ~80% | ~90% |
| **Recall@10** | ~50% | ~70% | ~85% |
| **Query-Latenz** | 200ms | 150ms | 250ms (Reranking) |
| **RAM (10K Chunks)** | 500MB | 125MB | 125MB |
| **Indexing-Zeit** | 5 min | 5 min | 8 min (Summaries) |
