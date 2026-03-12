# Docker Release Guide

Anleitung zum Bauen, Verteilen und Starten des SDLC Pilot Dashboards.

---

## Teil 1: Release erstellen (für dich als Entwickler)

### Voraussetzungen

- Docker Desktop gestartet
- Du bist im Projektverzeichnis (`cd aicodegencrew`)

### Schritt 1: Images bauen

```bash
docker compose -f ui/docker-compose.ui.yml build
```

Das baut zwei Images:
- **Backend** (Python/FastAPI) — ca. 350 MB
- **Frontend** (Angular/nginx) — ca. 27 MB

Das Capgemini CA-Zertifikat (`certs/CapgeminiPKIRootCA.crt`) wird
automatisch in beide Images eingebacken, damit HTTPS zur Sovereign AI
Platform funktioniert.

### Schritt 2: Images taggen

```bash
docker tag ui-backend:latest  sdlc-pilot/backend:0.7.2
docker tag ui-backend:latest  sdlc-pilot/backend:latest
docker tag ui-frontend:latest sdlc-pilot/frontend:0.7.2
docker tag ui-frontend:latest sdlc-pilot/frontend:latest
```

> Version (`0.7.2`) an die aktuelle Version in `pyproject.toml` anpassen.

### Schritt 3: Images als Dateien exportieren

```bash
docker save sdlc-pilot/backend:latest sdlc-pilot/backend:0.7.2 \
  | gzip > dist/docker-release/sdlc-pilot-backend.tar.gz

docker save sdlc-pilot/frontend:latest sdlc-pilot/frontend:0.7.2 \
  | gzip > dist/docker-release/sdlc-pilot-frontend.tar.gz
```

### Schritt 4: Release-Paket zusammenstellen

Das Verzeichnis `dist/docker-release/` enthält bereits alle nötigen
Dateien. Nach dem Export der Images ist es komplett:

```
dist/docker-release/
├── start.bat                       ← Startskript (Windows CMD/PowerShell)
├── start.sh                        ← Startskript (Git Bash / Linux / macOS)
├── docker-compose.yml              ← Container-Konfiguration
├── .env.example                    ← Konfigurations-Vorlage
├── README.md                       ← Anleitung fuer Endbenutzer
├── config/
│   └── phases_config.yaml          ← Pipeline-Phasen-Konfiguration
├── sdlc-pilot-backend.tar.gz      ← Backend-Image (~350 MB)
└── sdlc-pilot-frontend.tar.gz     ← Frontend-Image (~27 MB)
```

### Schritt 5: ZIP erstellen und versenden

```bash
cd dist
zip -r sdlc-pilot-v0.7.2.zip docker-release/
```

Die ZIP-Datei (~375 MB) per Teams, SharePoint oder Netzlaufwerk teilen.

### Alles in einem Befehl

```bash
# Bauen + Taggen + Exportieren + Zippen
docker compose -f ui/docker-compose.ui.yml build \
  && docker tag ui-backend:latest sdlc-pilot/backend:latest \
  && docker tag ui-frontend:latest sdlc-pilot/frontend:latest \
  && mkdir -p dist/docker-release \
  && docker save sdlc-pilot/backend:latest | gzip > dist/docker-release/sdlc-pilot-backend.tar.gz \
  && docker save sdlc-pilot/frontend:latest | gzip > dist/docker-release/sdlc-pilot-frontend.tar.gz \
  && cd dist && zip -r sdlc-pilot-v0.7.2.zip docker-release/
```

---

## Teil 2: Dashboard starten (für Endbenutzer / Manager / Entwickler)

### Voraussetzung

**Docker Desktop** installieren und starten.
Download: https://www.docker.com/products/docker-desktop

Nach der Installation: Docker Desktop starten und warten bis das
blaue Wal-Icon in der Taskleiste (unten rechts) erscheint.

### Schritt 1: ZIP entpacken

Die Datei `sdlc-pilot-v0.7.2.zip` entpacken (Rechtsklick → "Alle extrahieren").

### Schritt 2: API-Key eintragen

Im entpackten Ordner:

1. `.env.example` kopieren und als `.env` speichern
   (oder im Terminal: `copy .env.example .env`)
2. `.env` mit Notepad öffnen (Rechtsklick → Öffnen mit → Notepad)
3. Diese Zeile suchen:
   ```
   OPENAI_API_KEY=sk-your-api-key-here
   ```
4. `sk-your-api-key-here` mit dem echten API-Key ersetzen
5. Speichern (Strg+S) und schließen

> Den API-Key bekommst du vom Team-Lead.

### Schritt 3: Starten

Doppelklick auf **`start.bat`**.

Was passiert:
1. Skript prüft ob Docker läuft → falls nicht, Fehlermeldung
2. Skript prüft ob `.env` existiert und API-Key gesetzt → falls nicht, Fehlermeldung
3. Beim ersten Mal: Images werden geladen (~1-2 Minuten)
4. Container werden gestartet (~5 Sekunden)
5. Meldung: "Dashboard ist bereit!"

### Schritt 4: Dashboard öffnen

Im Browser: **http://localhost**

---

## Bedienung

| Aktion | Windows CMD/PowerShell | Git Bash / Linux |
|--------|------------------------|------------------|
| Starten | `start.bat` | `./start.sh` |
| Stoppen | `start.bat stop` | `./start.sh stop` |
| Logs anzeigen | `start.bat logs` | `./start.sh logs` |
| Neustarten | `start.bat stop` dann `start.bat` | `./start.sh stop` dann `./start.sh` |

---

## Update auf neue Version

1. Neue ZIP-Datei erhalten (`sdlc-pilot-vX.Y.Z.zip`)
2. Dashboard stoppen: `start.bat stop`
3. Neue Images laden:
   ```
   docker load -i sdlc-pilot-backend.tar.gz
   docker load -i sdlc-pilot-frontend.tar.gz
   ```
4. Dashboard starten: `start.bat`

> Die `.env` Konfiguration bleibt erhalten — nur die Images werden ersetzt.

---

## Problembehebung

| Problem | Lösung |
|---------|--------|
| "Docker ist nicht gestartet" | Docker Desktop öffnen, warten bis Wal-Icon erscheint |
| "API-Key nicht eingetragen" | `.env` Datei mit Notepad öffnen, Key eintragen |
| Browser zeigt nichts | 30 Sekunden warten, http://localhost neu laden |
| Port 80 belegt | Anderen Webserver stoppen (IIS, XAMPP, Skype) |
| `start.bat` schließt sofort | Rechtsklick → "Als Administrator ausführen" |
| Images laden scheitert | Prüfen ob .tar.gz Dateien im gleichen Ordner liegen |

---

## Technische Details

### Architektur

```
Browser (http://localhost)
    │
    ▼
┌─────────────────────┐
│  Frontend (nginx)    │  Port 80
│  Angular 21 SPA      │
│  Proxy: /api/* ──────┼──► Backend
└─────────────────────┘
                            │
                       ┌────▼────────────────┐
                       │  Backend (FastAPI)   │  Port 8001
                       │  Python 3.12         │
                       │  + Capgemini CA      │
                       │  + truststore        │
                       └──────────┬──────────┘
                                  │ HTTPS
                                  ▼
                       Sovereign AI Platform
                       (LLM API)
```

### SSL/Zertifikate

Das Capgemini Root-CA-Zertifikat (`CapgeminiPKIRootCA.crt`) ist in
beide Docker Images eingebacken:

- **Backend:** `update-ca-certificates` + `truststore.inject_into_ssl()`
- **Frontend:** `NODE_EXTRA_CA_CERTS` (für npm ci während Build)

Dadurch funktionieren HTTPS-Verbindungen zur Sovereign AI Platform
ohne zusätzliche Konfiguration.

### Ports

| Port | Service | Zweck |
|------|---------|-------|
| 80 | Frontend (nginx) | Dashboard UI + API-Proxy |
| 8001 | Backend (FastAPI) | REST API (intern, muss nicht exponiert werden) |

### Volumes (persistente Daten)

| Pfad im Container | Lokaler Pfad | Zweck |
|--------------------|-------------|-------|
| `/app/knowledge` | `./knowledge/` | Pipeline-Ergebnisse |
| `/app/logs` | `./logs/` | Log-Dateien |
| `/app/config` | `./config/` | Pipeline-Konfiguration |
| `/app/.env` | `./.env` | API-Keys und Einstellungen |
