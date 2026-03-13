# SDLC Pilot

> **Proprietary Software** — Aymen Mastouri (Capgemini).
> Keine Nutzung ohne schriftliche Genehmigung.

**AI-Powered Development Lifecycle Automation**

[![Version](https://img.shields.io/badge/version-0.7.2-blue.svg)](#changelog)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Angular 21](https://img.shields.io/badge/dashboard-Angular%2021-red.svg)](#3-sdlc-dashboard-web-ui)
[![Tests](https://img.shields.io/badge/tests-745%20passed-brightgreen.svg)](#10-testing)
[![On-Premises](https://img.shields.io/badge/deployment-on--premises-purple.svg)](#9-deployment)

SDLC Pilot automatisiert den gesamten Software Development Lifecycle — von
Architektur-Analyse bis Code-Generierung. Läuft komplett auf eurer Infrastruktur.
Keine Daten verlassen das Netzwerk.

| Komponente | Beschreibung |
|------------|-------------|
| **SDLC Dashboard** (Web UI) | Pipelines starten, Aufgaben hochladen, Ergebnisse ansehen |
| **Core Pipeline** (CLI) | Kann auch ohne Dashboard über die Kommandozeile laufen |

---

## Inhalt

1. [Quick Start — Docker (empfohlen)](#1-quick-start--docker-empfohlen)
2. [Quick Start — Entwickler (Python + Node)](#2-quick-start--entwickler-python--node)
3. [SDLC Dashboard (Web UI)](#3-sdlc-dashboard-web-ui)
4. [Core Pipeline (CLI)](#4-core-pipeline-cli)
5. [Konfiguration (.env)](#5-konfiguration-env)
6. [Architektur & Phasen](#6-architektur--phasen)
7. [Troubleshooting](#7-troubleshooting)
8. [Scripts](#8-scripts)
9. [Deployment](#9-deployment)
10. [Testing](#10-testing)
11. [Dokumentation](#11-dokumentation)

---

## 1. Quick Start — Docker (empfohlen)

> Für alle die schnell loslegen wollen — Manager, Entwickler, Demo.
> Kein Python, kein Node, kein npm nötig. Nur **Docker Desktop**.

### Voraussetzungen

| Was | Download | Hinweis |
|-----|----------|---------|
| **Git** | https://git-scm.com/downloads | Bei Capgemini meist vorinstalliert |
| **Docker Desktop** | https://www.docker.com/products/docker-desktop | Windows, macOS oder Linux |

### Docker Desktop installieren

<details>
<summary><strong>Windows</strong></summary>

1. https://www.docker.com/products/docker-desktop → "Download for Windows"
2. `Docker Desktop Installer.exe` ausführen, Voreinstellungen beibehalten
3. Falls gefragt: **WSL2 installieren** → Ja
4. Rechner neu starten (wenn gefordert)
5. Docker Desktop öffnen (Startmenü → "Docker Desktop")
6. Warten bis das blaue Wal-Icon in der Taskleiste (unten rechts) erscheint
</details>

<details>
<summary><strong>macOS</strong></summary>

1. https://www.docker.com/products/docker-desktop → "Download for Mac"
2. Richtige Version wählen: **Apple Silicon** (M1/M2/M3) oder **Intel**
3. `.dmg` öffnen, Docker in Applications ziehen
4. Docker aus Applications starten
5. Warten bis das Wal-Icon in der Menüleiste (oben rechts) erscheint
</details>

<details>
<summary><strong>Linux (Ubuntu/Debian)</strong></summary>

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Ausloggen und wieder einloggen, dann:
docker info
```
</details>

### Terminal öffnen

| Betriebssystem | So geht's |
|----------------|-----------|
| **Windows 11** | Rechtsklick auf Start-Button → "Terminal" |
| **Windows 10** | Startmenü → `cmd` eingeben → "Eingabeaufforderung" |
| **macOS** | Spotlight (Cmd+Leertaste) → `Terminal` eingeben → Enter |
| **Linux** | Strg+Alt+T |

### Schritt 1: Repository herunterladen

```
git clone https://bnotkca.pl.s2-eu.capgemini.com/gitlab/ai-group/aicodegencrew.git
cd aicodegencrew
```

### Schritt 2: Konfiguration

| Windows (CMD/PowerShell) | macOS / Linux / Git Bash |
|--------------------------|--------------------------|
| `copy .env.example .env` | `cp .env.example .env` |

Dann `.env` mit einem Texteditor öffnen:

- **Windows:** Rechtsklick auf `.env` → "Öffnen mit" → Notepad
- **macOS:** Rechtsklick → "Öffnen mit" → TextEdit
- **Linux:** `nano .env`

Die Zeile suchen:
```
OPENAI_API_KEY=sk-your-api-key-here
```

`sk-your-api-key-here` durch den echten API-Key ersetzen.
Speichern (Windows: Strg+S, macOS: Cmd+S) und schließen.

> Den API-Key findest du im internen Wiki oder frage im Team-Channel.

### Schritt 3: Starten

Stelle sicher, dass **Docker Desktop läuft** (Wal-Icon sichtbar).

| Windows CMD / PowerShell | Git Bash / macOS / Linux |
|--------------------------|--------------------------|
| `start.bat` | `./start.sh` |

Beim **ersten Mal** dauert es 2-3 Minuten (Docker Images werden gebaut).
Danach startet es in Sekunden.

### Schritt 4: Dashboard öffnen

Öffne im Browser (Chrome, Edge, Firefox):

**http://localhost**

Fertig!

### Stoppen / Logs / Neustarten

| Aktion | Windows CMD/PowerShell | Git Bash / macOS / Linux |
|--------|------------------------|--------------------------|
| Stoppen | `start.bat stop` | `./start.sh stop` |
| Logs anzeigen | `start.bat logs` | `./start.sh logs` |
| Neustarten | `start.bat stop` dann `start.bat` | `./start.sh stop` dann `./start.sh` |

---

## 2. Quick Start — Entwickler (Python + Node)

> Nur nötig wenn du am **Source-Code** mitarbeiten willst.
> Für Demo / Testen reicht Docker (siehe oben).

### Voraussetzungen

| Was | Version | Prüfen mit | Wofür |
|-----|---------|------------|-------|
| **Python** | 3.10 - 3.12 | `python --version` | Core Pipeline |
| **Node.js** | 18+ | `node --version` | Dashboard Frontend |
| **Ollama** | beliebig | `curl http://127.0.0.1:11434/api/tags` | Nur für Pipeline (Embeddings) |

> Ollama und LLM-API werden **nicht** zum Starten des Dashboards gebraucht.
> Nur für das Ausführen der Pipeline-Phasen.

### Setup — Windows

```powershell
git clone https://bnotkca.pl.s2-eu.capgemini.com/gitlab/ai-group/aicodegencrew.git
cd aicodegencrew

python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev,parsers]"

copy .env.example .env
# .env öffnen und API-Key eintragen

cd ui\frontend
npm install
cd ..\..
npm install

npm run dev
```

Dashboard: http://localhost:4200

### Setup — macOS / Linux

```bash
git clone https://bnotkca.pl.s2-eu.capgemini.com/gitlab/ai-group/aicodegencrew.git
cd aicodegencrew

python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,parsers]"

cp .env.example .env
# .env öffnen und API-Key eintragen

cd ui/frontend && npm install && cd ../..
npm install

npm run dev
```

Dashboard: http://localhost:4200

### Setup prüfen

Nach `npm run dev`:

| URL | Erwartet |
|-----|----------|
| http://localhost:4200 | Dashboard UI |
| http://localhost:8001/api/health | `{"status":"ok"}` |
| http://localhost:8001/api/health/setup-status | Setup-Status mit Fehlermeldungen |

### Dashboard starten / stoppen (Entwickler)

| Aktion | Befehl |
|--------|--------|
| Starten (Backend + Frontend) | `npm run dev` |
| Starten (Git Bash) | `./scripts/dev.sh` |
| Stoppen | Strg+C oder `npm run stop` |
| Stoppen (Git Bash) | `./scripts/dev.sh stop` |
| Status prüfen | `./scripts/dev.sh status` |

> **Wichtig:** Immer `npm start` für das Frontend verwenden, nie `ng serve` direkt.
> `npm start` aktiviert den Proxy (`proxy.conf.json`) der `/api/*` ans Backend weiterleitet.
> Ohne Proxy kommen API-Anfragen als Angular-HTML zurück.

---

## 3. SDLC Dashboard (Web UI)

Das Dashboard besteht aus **FastAPI Backend** (Port 8001) + **Angular Frontend** (Port 4200 dev / Port 80 Docker).

### Seiten

| Seite | Beschreibung |
|-------|-------------|
| **Dashboard** | System-Status, Phase-Karten, aktiver Pipeline-Banner |
| **Run Pipeline** | Preset oder einzelne Phasen starten, Live-Logs (SSE) |
| **Input Files** | Drag-and-Drop Upload (JIRA XML, DOCX, Excel, PDF) |
| **Phases** | Phasen-Konfiguration, einzelne Phasen starten/zurücksetzen |
| **Knowledge** | Ergebnisse durchsuchen (JSON, Markdown, HTML, Confluence, DrawIO) |
| **Reports** | Plan-Viewer, Code-Diff-Viewer, Git-Branch-Management |
| **Metrics** | LLM-Nutzung, Token-Verbrauch, Event-Explorer |
| **Logs** | Echtzeit-Pipeline-Logs mit farbcodierten Levels |
| **Collectors** | Architektur-Fakten-Collector-Konfiguration |
| **History** | Vergangene Runs mit Statistiken und KPI-Karten |
| **Settings** | Umgebungsvariablen konfigurieren |
| **Onboarding** | Geführte Erstkonfiguration |

### Docker Deployment

```bash
docker compose -f ui/docker-compose.ui.yml up --build    # http://localhost
```

---

## 4. Core Pipeline (CLI)

Die Pipeline kann **ohne Dashboard** direkt über die Kommandozeile laufen.

### Beispiele

```bash
aicodegencrew index --force                              # Repository indexieren
aicodegencrew plan                                       # Entwicklungsplanung
aicodegencrew codegen                                    # Vollständige Pipeline
aicodegencrew run --phases plan implement --index-mode off --no-clean
```

### Befehle

| Befehl | Beschreibung |
|--------|-------------|
| `index` | Repository in ChromaDB indexieren |
| `plan` | Entwicklungsplanung (Discover → Plan) |
| `codegen` | Code-Generierung (Discover → Implement) |
| `run --preset <name>` | Preset ausführen |
| `run --phases <p1> <p2>` | Bestimmte Phasen ausführen |
| `list` | Verfügbare Phasen und Presets anzeigen |

### Presets

| Preset | Phasen | Anwendungsfall |
|--------|--------|----------------|
| `index` | Discover | Nur Indexierung |
| `scan` | Discover + Extract | Deterministische Fakten (kein LLM) |
| `analyze` | Discover → Analyze | AI-Analyse |
| `document` | Discover → Document | C4 + arc42 Dokumentation |
| `plan` | Discover → Plan | Entwicklungsplanung (häufigster) |
| `develop` | Discover → Implement | Planung + Code-Generierung |
| `full` | Alle Phasen | End-to-End |

### Index-Modi

| Modus | Beschreibung |
|-------|-------------|
| `auto` | Nur indexieren wenn Repo geändert (Standard) |
| `off` | Indexierung überspringen |
| `force` | Komplett neu indexieren |
| `smart` | Inkrementell — nur geänderte Dateien |

### Optionen

```bash
aicodegencrew run --preset plan \
  --repo-path C:\other\repo \         # Anderes Repo analysieren
  --index-mode off \                  # Indexierung überspringen
  --no-clean \                        # Vorherige Ergebnisse behalten
  --git-url https://... \             # Von URL klonen
  --branch feature/xyz               # Bestimmter Branch
```

### Pipeline zurücksetzen

```bash
# Via Dashboard: Phases → Reset All
# Via API:
curl -X POST http://localhost:8001/api/reset
# Archiviert knowledge/ nach knowledge/archive/reset_YYYYMMDD_HHMMSS/
```

---

## 5. Konfiguration (.env)

`.env.example` → `.env` kopieren und anpassen:

### Wichtigste Variablen

| Variable | Beschreibung | Beispiel |
|----------|-------------|---------|
| `PROJECT_PATH` | Zu analysierendes Repository | `C:\repos\my-project` |
| `TASK_INPUT_DIR` | JIRA/DOCX/Excel Aufgaben | `C:\projects\inputs\tasks` |
| `LLM_PROVIDER` | `local` (Ollama) oder `onprem` (API) | `onprem` |
| `MODEL` | LLM-Modell | `openai/complex_tasks` |
| `API_BASE` | LLM-API-Endpunkt | `https://litellm.bnotk.sovai-de...` |
| `OPENAI_API_KEY` | API-Key | `sk-...` |
| `EMBED_MODEL` | Embedding-Modell | `embed` |

### Modell-Routing

| Variable | Modell | Verwendet für |
|----------|--------|---------------|
| `MODEL` | Kimi-K2.5 | Analyse, Triage, Docs, Planung, Reviews |
| `FAST_MODEL` | GPT-OSS-120B | Schnelle Tasks (Klassifizierung, Reviews) |
| `CODEGEN_MODEL` | Qwen3-Coder-Next | Code-Generierung, Tests |
| `VISION_MODEL` | Mistral-Small-3.1-24B | OCR, Diagramme, Screenshots |

> Vollständige Referenz: [.env.example](.env.example) und [LLM Selection Guide](docs/guides/LLM_SELECTION_GUIDE.md)

### Task Inputs

| Modus | Wie |
|-------|-----|
| **Dashboard** | Drag-and-Drop auf der "Input Files"-Seite |
| **Manuell** | `TASK_INPUT_DIR`, `REQUIREMENTS_DIR`, `LOGS_DIR`, `REFERENCE_DIR` in `.env` setzen |

| Kategorie | Formate |
|-----------|---------|
| Tasks | `.xml` `.docx` `.pdf` `.txt` `.json` |
| Requirements | `.xlsx` `.docx` `.pdf` `.txt` `.csv` |
| Logs | `.log` `.txt` `.xlsx` `.csv` |
| Reference | `.png` `.jpg` `.svg` `.pdf` `.drawio` `.md` |

---

## 6. Architektur & Phasen

```
KNOWLEDGE (kein LLM)        REASONING (hybrid)           EXECUTION (hybrid)
Discover                ->  Analyze                  ->  Implement
Extract                 ->  Document (C4 + arc42)    ->  Verify
                             Plan                     ->  Deliver (geplant)
```

| # | Phase | LLM | Beschreibung |
|---|-------|:---:|-------------|
| 0 | Discover | Nein | Codebase in ChromaDB indexieren, Symbole extrahieren |
| 1 | Extract | Nein | 16 Architektur-Dimensionen deterministisch extrahieren |
| 2 | Analyze | Ja | Multi-Agent-Analyse (Domain, Workflow, Qualität) |
| 3 | Document | Ja | C4-Diagramme + arc42-Kapitel + DrawIO |
| 4 | Plan | Hybrid | 4 deterministische Stufen + 1 LLM-Call |
| 5 | Implement | Hybrid | CrewAI Code-Generierung + Build-Verifikation mit Self-Healing |
| 6 | Verify | Ja | Test-Generierung pro Datei (JUnit 5 / Angular TestBed) |
| 7 | Deliver | — | Geplant |

### Datenfluss

```
Repository --> Discover   --> knowledge/discover/    (ChromaDB + Symbole)
               Extract    --> knowledge/extract/     (architecture_facts.json)
               Analyze    --> knowledge/analyze/     (analyzed_architecture.json)
               Document   --> knowledge/document/    (C4 + arc42 + DrawIO)
               Plan       --> knowledge/plan/        ({task_id}_plan.json)
               Implement  --> Git Branch codegen/*   + knowledge/implement/
               Verify     --> knowledge/verify/      ({task_id}_verify.json)
```

> Vollständige Spezifikation: [SDLC Architecture](docs/SDLC_ARCHITECTURE.md)

---

## 7. Troubleshooting

### Docker-Probleme

| Problem | Lösung |
|---------|--------|
| "Docker ist nicht gestartet" | Docker Desktop öffnen, auf Wal-Icon warten |
| Container startet nicht | `start.bat logs` oder `docker compose logs` prüfen |
| Port 80 belegt | IIS, XAMPP, Apache, Skype stoppen |
| Port 8001 belegt | `./scripts/dev.sh stop` oder `node scripts/stop-dev.js` |

### Entwickler-Probleme

| Problem | Lösung |
|---------|--------|
| API gibt HTML statt JSON zurück | Frontend mit `npm start` starten (nicht `ng serve`) |
| LLM-Verbindungsfehler | `curl $API_BASE/v1/models` prüfen (401 = OK, refused = kein Netz) |
| SSL CERTIFICATE_VERIFY_FAILED | Siehe [Corporate SSL Guide](docs/guides/CORPORATE_SSL_GUIDE.md) |
| Ollama läuft nicht | `ollama serve` dann `curl http://127.0.0.1:11434/api/tags` |
| Indexierung hängt | `rm knowledge/discover/.index.lock` |
| Orphan uvicorn Prozesse | `./scripts/dev.sh stop` (killt auch Orphans) |
| Pipeline-Crash | Dashboard läuft weiter (Subprocess-Isolation). `logs/current.log` prüfen |

---

## 8. Scripts

| Script | Beschreibung |
|--------|-------------|
| `start.bat` / `start.sh` | Dashboard starten/stoppen (Docker) |
| `scripts/dev.sh` | Dashboard Dev-Server starten/stoppen |
| `scripts/stop-dev.js` | Dev-Server stoppen + Orphan-Prozesse killen |
| `scripts/push-docker-images.sh` | Docker Images bauen + in Registry pushen |
| `scripts/build_release.py` | Release-Paket erstellen (Wheel + Changelog) |

### dev.sh

```bash
./scripts/dev.sh              # Neustart (stop + start)
./scripts/dev.sh start        # Nur starten
./scripts/dev.sh stop         # Stoppen + Orphans killen
./scripts/dev.sh status       # Prüfen ob es läuft
```

### build_release.py

```bash
python scripts/build_release.py                         # aktuelle Version bauen
python scripts/build_release.py --bump patch            # 0.7.2 -> 0.7.3
python scripts/build_release.py --bump minor --tag      # 0.7.2 -> 0.8.0 + Git Tag
```

---

## 9. Deployment

| Modus | Befehl | Source-Code sichtbar |
|-------|--------|:--------------------:|
| **Docker** (empfohlen) | `start.bat` / `./start.sh` | Nein |
| **Docker Release ZIP** | ZIP verteilen, `start.bat` | Nein |
| **Wheel** | `pip install aicodegencrew-X.Y.Z.whl` | Nein |
| **Dev** | `pip install -e .` | Ja (intern) |

> Details: [Delivery Guide](docs/guides/DELIVERY_GUIDE.md) und [Docker Release Guide](docs/guides/DOCKER_RELEASE_GUIDE.md)

---

## 10. Testing

745+ Tests, kein LLM oder Netzwerk nötig (außer `tests/e2e/`).

```bash
pip install -e ".[dev]"

# Vollständig (ohne bekannte Langläufer)
pytest tests/ -q --ignore=tests/test_delivery.py

# Nur Unit + Integration
pytest tests/ --ignore=tests/e2e

# Nur Collector-Unit-Tests (~5s)
pytest tests/unit/collectors/ -v

# Linting
ruff check src/ tests/ ui/backend
```

---

## 11. Dokumentation

| Dokument | Beschreibung |
|----------|-------------|
| [SDLC Architecture](docs/SDLC_ARCHITECTURE.md) | Gesamtarchitektur + Links zu allen Phasen |
| [LLM Selection Guide](docs/guides/LLM_SELECTION_GUIDE.md) | Welches Modell für welche Phase |
| [Docker Release Guide](docs/guides/DOCKER_RELEASE_GUIDE.md) | Images bauen, verteilen, starten |
| [Corporate SSL Guide](docs/guides/CORPORATE_SSL_GUIDE.md) | Zertifikate im Corporate-Netzwerk |
| [Delivery Guide](docs/guides/DELIVERY_GUIDE.md) | Release-Prozess und Deployment |
| [MCP Knowledge Server](docs/guides/MCP_KNOWLEDGE_SERVER.md) | MCP Server für CrewAI Tools |
| [Phase 5 — Implement](docs/phases/phase-5-implement/README.md) | Code-Generierung + Build-Verify |
| [.env.example](.env.example) | Alle konfigurierbaren Variablen |

---

## Projektstruktur

```
aicodegencrew/
├── start.bat / start.sh            # Dashboard starten (Docker)
├── ui/                             # SDLC Dashboard
│   ├── frontend/                   #   Angular 21 (Port 80 Docker / 4200 Dev)
│   ├── backend/                    #   FastAPI (Port 8001)
│   └── docker-compose.ui.yml      #   Docker Compose
├── src/aicodegencrew/              # Core Pipeline
│   ├── cli.py                      #   CLI Entry Point
│   ├── orchestrator.py             #   Phasen-Orchestrierung
│   ├── pipelines/                  #   Discover, Extract
│   ├── crews/                      #   Analyze, Document, Verify
│   ├── hybrid/                     #   Plan, Implement
│   ├── shared/                     #   Utilities, Tools, Validation
│   │   └── utils/llm_factory.py    #   LLM-Erstellung (alle Modelle)
│   └── mcp/                        #   MCP Knowledge Server
├── certs/                          # Capgemini CA-Zertifikat
├── config/phases_config.yaml       # Phasen-Definitionen + Presets
├── scripts/                        # Dev-Scripts
├── tests/                          # 745+ Tests
├── docs/                           # Architektur-Docs + Guides
├── knowledge/                      # Pipeline-Ergebnisse (auto-generiert)
├── dist/                           # Release-Artefakte (Docker Images, ZIP)
└── .env                            # Konfiguration
```

---

## Lizenz

**Copyright 2026 Aymen Mastouri** — Proprietär und vertraulich.

---

<p align="center">
  <strong>SDLC Pilot</strong> &mdash; Built with <a href="https://crewai.com/">CrewAI</a> · Powered by Sovereign AI · Made for Enterprise<br>
  <sub>&copy; 2026 Aymen Mastouri / Capgemini AI Group. All rights reserved.</sub>
</p>
