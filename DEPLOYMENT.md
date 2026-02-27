# AICodeGenCrew — Deployment Guide

## Übersicht

Dieses Dokument beschreibt, wie AICodeGenCrew als geschütztes Docker-Image an Entwickler verteilt wird.
Der Source Code (Python + Angular) ist im finalen Image **nicht lesbar** — nur kompilierter Bytecode und minified JS.

---

## Die beiden Docker-Compose-Dateien

| Datei | Zweck | Source Code sichtbar? |
|-------|-------|-----------------------|
| `ui/docker-compose.ui.yml` | **Deine lokale Entwicklung** — mounted Source als Volume, Live-Änderungen | Ja |
| `ui/docker-compose.secure.yml` | **Für die Entwickler** — fertiges Image, kein Source Code | Nein |

Du behältst beide. Die alte für dich lokal, die neue zum Verteilen.

---

## Schritt-für-Schritt-Anleitung

### Schritt 1 — Voraussetzung

Docker Desktop muss installiert sein:

```bash
docker --version
```

### Schritt 2 — Sichere Images bauen

Vom Projekt-Root aus:

```bash
cd /c/projects/aicodegencrew

# Backend bauen (kompiliert Python → Bytecode, löscht alle .py)
docker build -f ui/backend/Dockerfile.secure -t aicodegencrew-backend:latest .

# Frontend bauen (kompiliert Angular → minified JS)
docker build -f ui/frontend/Dockerfile -t aicodegencrew-frontend:latest ui/frontend/
```

Oder mit dem Build-Script:

```bash
cd /c/projects/aicodegencrew
bash ui/build-secure.sh --verify
```

### Schritt 3 — Verifizieren: kein Source Code im Image?

```bash
# Darf keine .py Dateien finden (sollte leer sein)
docker run --rm aicodegencrew-backend:latest find /app -name "*.py"

# Darf keine .ts Dateien finden (sollte leer sein)
docker run --rm aicodegencrew-frontend:latest find /usr/share/nginx/html -name "*.ts"
```

### Schritt 4 — Lokal testen

```bash
cd ui/

# .env aus Template erstellen
cp deploy.env.example .env

# .env editieren — mindestens diese Werte setzen:
#   LLM_PROVIDER=onprem
#   MODEL=gpt-oss-120b
#   API_BASE=https://llm-server.firma.internal:4000

# Container starten
docker compose -f docker-compose.secure.yml up -d

# Browser öffnen: http://localhost
```

### Schritt 5 — Private Docker Registry einrichten

Die Entwickler brauchen einen Ort, um die Images zu holen. Optionen:

| Registry | Kosten | Typ |
|----------|--------|-----|
| GitLab Container Registry | Kostenlos (bei GitLab) | Self-hosted |
| Harbor | Open Source | Self-hosted |
| Nexus | Open Source | Self-hosted |
| AWS ECR | Pay-per-use | Cloud |
| Azure ACR | Pay-per-use | Cloud |

### Schritt 6 — Images in die Registry pushen

```bash
# Bei der Registry einloggen
docker login registry.firma.internal

# Taggen
docker tag aicodegencrew-backend:latest registry.firma.internal/aicodegencrew-backend:latest
docker tag aicodegencrew-frontend:latest registry.firma.internal/aicodegencrew-frontend:latest

# Pushen
docker push registry.firma.internal/aicodegencrew-backend:latest
docker push registry.firma.internal/aicodegencrew-frontend:latest
```

### Schritt 7 — Was die Entwickler bekommen

Du verteilst an die Entwickler **nur diese 3 Dateien** (kein Source Code!):

1. `docker-compose.secure.yml`
2. `deploy.env.example`
3. Diese Kurzanleitung (siehe unten)

### Schritt 8 — Updates verteilen

Wenn du eine neue Version veröffentlichst:

```bash
# Neu bauen mit Version-Tag
docker build -f ui/backend/Dockerfile.secure -t aicodegencrew-backend:v2.0 .
docker build -f ui/frontend/Dockerfile -t aicodegencrew-frontend:v2.0 ui/frontend/

# Taggen und pushen
docker tag aicodegencrew-backend:v2.0 registry.firma.internal/aicodegencrew-backend:v2.0
docker tag aicodegencrew-frontend:v2.0 registry.firma.internal/aicodegencrew-frontend:v2.0
docker push registry.firma.internal/aicodegencrew-backend:v2.0
docker push registry.firma.internal/aicodegencrew-frontend:v2.0
```

Entwickler aktualisieren mit:

```bash
docker compose -f docker-compose.secure.yml pull
docker compose -f docker-compose.secure.yml up -d
```

---

## Kurzanleitung für Entwickler

> Diese Anleitung an die Entwickler weitergeben.

### AICodeGenCrew installieren

**Voraussetzung:** Docker Desktop

```bash
# 1. Dateien in einen Ordner legen:
#    - docker-compose.secure.yml
#    - .env (kopiert aus deploy.env.example)

# 2. .env konfigurieren:
#    LLM_PROVIDER=onprem
#    MODEL=gpt-oss-120b
#    API_BASE=https://llm-server.firma.internal:4000

# 3. Starten:
docker compose -f docker-compose.secure.yml up -d

# 4. Browser öffnen:
#    http://localhost

# 5. Stoppen:
docker compose -f docker-compose.secure.yml down

# 6. Aktualisieren:
docker compose -f docker-compose.secure.yml pull
docker compose -f docker-compose.secure.yml up -d
```

---

## Sicherheit — Was ist geschützt?

| Angriffsvektor | Geschützt? | Wie? |
|----------------|------------|------|
| Python Source lesen | Ja | Nur .pyc Bytecode im Image, alle .py gelöscht |
| TypeScript Source lesen | Ja | Nur minified + tree-shaken JS im Image |
| `docker exec` ins Image | Eingeschränkt | wget/curl entfernt, non-root User |
| Image-Layer inspizieren | Ja | Multi-Stage Build — Source nur in Build-Stage |
| .env / Secrets auslesen | Ja | .env wird nie ins Image kopiert |
| JavaScript reverse-engineering | Praktisch ja | Minified + Hashing durch Angular Production Build |

---

## Architektur

```
Entwickler-Laptop                     Euer Server
┌─────────────────────────┐          ┌──────────────┐
│  Docker                 │          │              │
│  ┌───────────────────┐  │          │  Ollama /    │
│  │ Frontend (nginx)  │  │          │  LLM Server  │
│  │ Port 80           │  │          │              │
│  └───────┬───────────┘  │          └──────▲───────┘
│          │ /api/        │                 │
│  ┌───────▼───────────┐  │                 │
│  │ Backend (FastAPI)  │──┼── API Call ─────┘
│  │ Port 8001         │  │
│  └───────────────────┘  │
└─────────────────────────┘

Frontend: Nur minified JS + CSS + HTML
Backend:  Nur .pyc Bytecode
LLM:      Läuft auf eurem zentralen GPU-Server
```

---

## Zusammenfassung

```
DU (einmalig)                          ENTWICKLER (2000-5000x)
─────────────                          ────────────────────────
1. docker build (2 Images)             1. docker pull (2 Images)
2. docker push → Registry              2. .env konfigurieren
3. 3 Dateien verteilen                 3. docker compose up
                                       4. http://localhost öffnen

Dein Source Code bleibt bei dir.
Entwickler sehen nur die Web-Oberfläche.
```
