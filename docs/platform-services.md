# On-Prem Platform Services — Integration Guide

AICodeGenCrew integrates with the Sovereign AI Platform services at `*.bnotk.sovai-de.apps.ce.capgemini.com`. All services are **optional** — disabled by default, enabled via environment variables, with graceful fallback when unavailable.

## Service Overview

| # | Service | Status | URL | Purpose |
|---|---------|--------|-----|---------|
| 1 | **Langfuse** | Active | `https://langfuse.bnotk.sovai-de.apps.ce.capgemini.com` | LLM Observability — traces every LLM call (prompts, responses, latency, tokens, costs) |
| 2 | **Qdrant** | Active | `https://qdrant.bnotk.sovai-de.apps.ce.capgemini.com` | Vector Store — replaces local ChromaDB for semantic search |
| 3 | **Neo4J** | Active | `neo4j+s://neo4j-bolt.bnotk.sovai-de.apps.ce.capgemini.com:443` | Knowledge Graph — exports architecture facts as nodes/edges |
| 4 | **MLflow** | Active | `https://mlflow.bnotk.sovai-de.apps.ce.capgemini.com` | Experiment Tracking — tracks pipeline runs, phase metrics, artifacts |
| 5 | **Grafana** | Active | `https://grafana.bnotk.sovai-de.apps.ce.capgemini.com` | Monitoring Dashboards — visualizes Prometheus metrics |
| 6 | **Prometheus** | Active | Backend `/metrics` endpoint | Metrics Export — phase duration, status counts, token usage |
| 7 | **Authentik** | Pending | `https://authentik.bnotk.sovai-de.apps.ce.capgemini.com` | OIDC Authentication — requires admin access to configure |
| 8 | **MCPO** | Ready | `https://mcpo.bnotk.sovai-de.apps.ce.capgemini.com` | MCP HTTP Proxy — no MCP servers registered yet, using stdio |
| 9 | **Docling** | Not tested | TBD | Document Conversion (PDF/DOCX/PPTX to Markdown) |
| 10 | **SovAI-MCP** | Not tested | TBD | Platform MCP tools for architecture analysis |

---

## 1. Langfuse — LLM Observability

**What it does:** Automatically traces every LLM call made through LiteLLM — prompts, completions, latency, token usage, and costs. View traces in the Langfuse UI to debug prompt quality and optimize token spend.

**How it works:** On module import, `llm_factory.py` registers `"langfuse"` on `litellm.success_callback` and `litellm.failure_callback`. LiteLLM's native Langfuse integration sends trace data automatically.

**Dashboard:** https://langfuse.bnotk.sovai-de.apps.ce.capgemini.com
- Organization: `bnotk-aicodegencrew`
- Project: `aicodegencrew`

**Env vars:**
```env
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://langfuse.bnotk.sovai-de.apps.ce.capgemini.com
```

**Disable:** Remove or comment out `LANGFUSE_PUBLIC_KEY`. No code changes needed.

**Files:**
- `src/aicodegencrew/shared/utils/llm_factory.py` — `_configure_langfuse()` function

---

## 2. Qdrant — Vector Store

**What it does:** Replaces local ChromaDB with a centralized Qdrant instance for semantic code search. All embeddings are stored remotely — no local SQLite database needed.

**How it works:** `VECTOR_DB=qdrant` activates the Qdrant backend via `vector_store.py` factory. The `QdrantVectorClient` implements the same `VectorStoreProtocol` as the ChromaDB wrapper, so all callers (indexing, RAG queries) work unchanged.

**Dashboard:** https://qdrant.bnotk.sovai-de.apps.ce.capgemini.com/dashboard

**When data is populated:** The `discover` phase (Phase 0) creates the `repo_docs` collection and upserts embeddings on first run. No manual migration needed — just run discover with the new config.

**Env vars:**
```env
VECTOR_DB=qdrant
QDRANT_URL=https://qdrant.bnotk.sovai-de.apps.ce.capgemini.com
QDRANT_API_KEY=<your-api-key>
QDRANT_COLLECTION=repo_docs
```

**Rollback to ChromaDB:** Set `VECTOR_DB=chroma` or remove the variable. Re-run discover to re-index locally.

**SSL Note:** The Qdrant client uses `httpx` internally. The client is configured with `host`+`port` (not full URL) and an explicit `ssl.SSLContext` from `truststore` to handle the platform's self-signed CA certificates.

**Files:**
- `src/aicodegencrew/shared/utils/vector_store.py` — `VectorStoreProtocol` + factory
- `src/aicodegencrew/shared/utils/qdrant_client.py` — `QdrantVectorClient` singleton
- `src/aicodegencrew/pipelines/indexing/chroma_index_tool.py` — uses `get_vector_store()`
- `src/aicodegencrew/shared/tools/rag_query_tool.py` — uses `get_vector_store()` for Qdrant

---

## 3. Neo4J — Knowledge Graph

**What it does:** Exports architecture facts (components, interfaces, dependencies) as a graph database after the `extract` phase. Enables dependency analysis queries like "what depends on ComponentX?"

**How it works:** After the `extract` phase completes successfully, the orchestrator calls `Neo4jClient.export_architecture_facts()` with the cached facts JSON. This creates/updates nodes and edges in Neo4J using Cypher MERGE statements (idempotent).

**Browser:** https://neo4j.bnotk.sovai-de.apps.ce.capgemini.com (Neo4J Browser UI)
- Connect URL: `neo4j+s://neo4j-bolt.bnotk.sovai-de.apps.ce.capgemini.com:443`

**Graph Model:**
```
(:Component {name, stereotype, layer, module, file_path})
(:Interface {name, type, path, method})
(:Component)-[:DEPENDS_ON {type, evidence}]->(:Component)
(:Component)-[:IMPLEMENTS]->(:Interface)
```

**Example Cypher queries:**
```cypher
-- All components
MATCH (c:Component) RETURN c.name, c.layer, c.stereotype

-- Dependencies of a component
MATCH (a:Component {name: "UserService"})-[r:DEPENDS_ON]->(b:Component)
RETURN a.name, r.type, b.name

-- Components with most dependencies
MATCH (c:Component)-[r:DEPENDS_ON]->() RETURN c.name, count(r) ORDER BY count(r) DESC
```

**Env vars:**
```env
NEO4J_URI=neo4j+s://neo4j-bolt.bnotk.sovai-de.apps.ce.capgemini.com:443
NEO4J_USER=neo4j
NEO4J_PASSWORD=<your-password>
```

**Disable:** Remove or comment out `NEO4J_URI`. Export is skipped silently.

**Files:**
- `src/aicodegencrew/shared/utils/neo4j_client.py` — `Neo4jClient` class
- `src/aicodegencrew/orchestrator.py` — export call after extract phase

---

## 4. MLflow — Experiment Tracking

**What it does:** Tracks each pipeline run as an MLflow experiment. Logs phase duration, token usage, and status as metrics. Logs key artifacts (e.g., `architecture_facts.json`).

**How it works:** The orchestrator creates an `MLflowTracker` on init. On `run()`, it calls `start_run()`. After each phase, it logs metrics. On pipeline completion, it logs artifacts and ends the run.

**Dashboard:** https://mlflow.bnotk.sovai-de.apps.ce.capgemini.com
- Experiment: `aicodegencrew`

**What gets logged per run:**
- Parameters: `pipeline_run_id`, `{phase}_status` for each phase
- Metrics: `{phase}_duration_seconds`, `{phase}_tokens` for each phase
- Artifacts: `architecture_facts.json` (when available)
- Final: `pipeline_outcome` (success/partial/failed)

**Env vars:**
```env
MLFLOW_TRACKING_URI=https://mlflow.bnotk.sovai-de.apps.ce.capgemini.com
MLFLOW_EXPERIMENT_NAME=aicodegencrew
```

**Disable:** Remove or comment out `MLFLOW_TRACKING_URI`. All tracker methods become no-ops.

**Files:**
- `src/aicodegencrew/shared/utils/mlflow_tracker.py` — `MLflowTracker` class
- `src/aicodegencrew/orchestrator.py` — tracker integration in `run()` and `_build_result()`

---

## 5. Grafana + Prometheus — Monitoring

**What it does:** Exposes SDLC pipeline metrics in Prometheus text format at the `/metrics` endpoint. Grafana scrapes these metrics for dashboards.

**Metrics exposed:**
| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `sdlc_phase_duration_seconds` | Histogram | `phase_id` | Duration of each phase execution |
| `sdlc_phase_status_total` | Counter | `phase_id`, `status` | Count of phase completions by status |
| `sdlc_tokens_total` | Counter | `phase_id`, `token_type` | Total LLM tokens consumed |

**Grafana Dashboard:** `config/grafana/dashboards/sdlc-overview.json` (import via Grafana UI)

**Env vars:**
```env
PROMETHEUS_ENABLED=true
```

**Disable:** Set `PROMETHEUS_ENABLED=false` or remove it. The `/metrics` endpoint is not registered.

**Files:**
- `ui/backend/routers/prometheus.py` — FastAPI router + `record_phase_metric()`
- `ui/backend/main.py` — conditional router registration
- `src/aicodegencrew/shared/utils/logger.py` — pushes metrics from `log_metric()`
- `config/grafana/dashboards/sdlc-overview.json` — Grafana dashboard JSON
- `config/grafana/datasources/prometheus.yaml` — Prometheus datasource config

---

## 6. Authentik — OIDC Authentication (Pending)

**Status:** Requires admin access to create an Application + Provider in Authentik. Currently skipped — dashboard runs without authentication.

**When configured, it will:**
- Protect all `/api/*` endpoints with JWT Bearer token validation
- Redirect unauthenticated users to Authentik login
- Set `request.state.user` with user info (sub, email, name, groups)
- Exempt: `/api/health`, `/metrics`, static files

**Env vars (when ready):**
```env
OIDC_ENABLED=true
OIDC_AUTHORITY=https://authentik.bnotk.sovai-de.apps.ce.capgemini.com/application/o/aicodegencrew
OIDC_CLIENT_ID=<from-authentik>
OIDC_CLIENT_SECRET=<from-authentik>
OIDC_SCOPES=openid profile email
```

**Files:**
- `ui/backend/middleware/auth.py` — `OIDCAuthMiddleware`
- `ui/backend/config.py` — OIDC settings
- `ui/frontend/src/app/services/auth.service.ts` — OIDC client
- `ui/frontend/src/app/services/auth.interceptor.ts` — Bearer token injection
- `ui/frontend/src/app/guards/auth.guard.ts` — Route protection

---

## 7. MCPO — MCP HTTP Transport (Ready)

**Status:** MCPO proxy is running but has no MCP servers registered yet. Using `stdio` transport (default).

**When MCP servers are registered on the platform**, switch to HTTP transport:
```env
MCP_TRANSPORT=http
MCPO_URL=https://mcpo.bnotk.sovai-de.apps.ce.capgemini.com
```

**Files:**
- `src/aicodegencrew/shared/mcp/mcp_http_adapter.py` — HTTP adapter
- `src/aicodegencrew/shared/mcp/mcp_manager.py` — transport switch logic

---

## Dependencies

All platform service clients are optional extras in `pyproject.toml`:

```bash
# Install individual extras
pip install -e ".[qdrant]"       # qdrant-client
pip install -e ".[neo4j]"        # neo4j driver
pip install -e ".[mlflow]"       # mlflow + boto3
pip install -e ".[prometheus]"   # prometheus-client
pip install -e ".[auth]"         # python-jose + httpx

# Install all platform extras at once
pip install -e ".[platform]"
```

## SSL / Corporate CA Certificates

The platform uses self-signed CA certificates. The `truststore` package injects the Windows/macOS system certificate store into Python's SSL stack at import time (`llm_factory.py`). This covers:
- `requests` library (Langfuse, Docling, MCPO)
- `urllib` (LLM connectivity check)
- `neo4j` driver (uses native SSL)
- `mlflow` (uses `requests`)

**Exception:** `qdrant-client` uses `httpx` which needs an explicit `ssl.SSLContext`. The `QdrantVectorClient` creates one after `truststore.inject_into_ssl()` and passes it via `verify=ssl_context`.

## Rollback

Every integration can be disabled independently:
- **Langfuse:** Remove `LANGFUSE_PUBLIC_KEY`
- **Qdrant:** Set `VECTOR_DB=chroma` (re-run discover to re-index locally)
- **Neo4J:** Remove `NEO4J_URI`
- **MLflow:** Remove `MLFLOW_TRACKING_URI`
- **Prometheus:** Set `PROMETHEUS_ENABLED=false`
- **Authentik:** Set `OIDC_ENABLED=false`
- **MCPO:** Set `MCP_TRANSPORT=stdio` (default)

No data migrations needed. No breaking changes. No code modifications required for rollback.
