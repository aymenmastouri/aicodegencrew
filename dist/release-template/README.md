# SDLC Pilot - Dashboard

AI-powered Software Development Lifecycle assistant. Runs entirely in Docker — no Python, Node.js, or other tools required.

## Prerequisites

- **Docker Desktop** installed and running
  - Download: https://www.docker.com/products/docker-desktop
  - After installation, start Docker Desktop and wait until the whale icon appears in your system tray

## Quick Start

### 1. Configure

Copy the example configuration:

| OS | Command |
|----|---------|
| Windows CMD | `copy .env.example .env` |
| macOS / Linux | `cp .env.example .env` |

Open `.env` in any text editor and set **at minimum** these two values:

```
PROJECT_PATH=C:\projects\myapp             # path to the repo you want to analyze
OPENAI_API_KEY=sk-your-actual-key          # your API key
```

> **Note:** `PROJECT_PATH` is your repository path on your machine.
> In Docker mode, the container mounts it automatically as a read-only volume.
> Changing this value requires a restart (`start.bat stop` then `start.bat`).

### 2. Start the Dashboard

| OS | Command |
|----|---------|
| Windows | Double-click **`start.bat`** or run it from CMD |
| macOS / Linux | `./start.sh` |

On first launch, Docker images are loaded from the included `.tar.gz` files (~1-2 minutes). Subsequent starts take ~5 seconds.

### 3. Open the Dashboard

Open **http://localhost** in your browser.

## Commands

| Action | Windows | macOS / Linux |
|--------|---------|---------------|
| Start | `start.bat` | `./start.sh` |
| Stop | `start.bat stop` | `./start.sh stop` |
| View logs | `start.bat logs` | `./start.sh logs` |
| Restart | `start.bat stop` then `start.bat` | `./start.sh stop` then `./start.sh` |
| Full cleanup | `clean.bat` | `./clean.sh` |

> `clean.bat` / `clean.sh` stops everything, removes containers, volumes, images, and data directories. Your `.env` is preserved.

## Updating to a New Version

1. Stop the dashboard: `start.bat stop`
2. Extract the new ZIP
3. Copy your existing `.env` into the new folder
4. Start: `start.bat`

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Docker is not running" | Start Docker Desktop, wait for the system tray icon |
| "API key not configured" | Open `.env` and set `OPENAI_API_KEY` |
| "Repository path not configured" | Open `.env` and set `PROJECT_PATH` to your repo |
| Browser shows nothing | Wait 30 seconds, reload http://localhost |
| Port 80 already in use | Stop other web servers (IIS, XAMPP, Apache, Skype) |
| `start.bat` closes instantly | Right-click > "Run as administrator" |
| Image loading fails | Verify `.tar.gz` files are in the same folder |

## Architecture

```
Browser (http://localhost)
    |
    v
+---------------------+
|  Frontend (nginx)    |  Port 80
|  Angular SPA         |
|  Proxy: /api/* ------+--> Backend
+---------------------+
                            |
                       +----v--------------------+
                       |  Backend (FastAPI)       |  Port 8001 (internal)
                       |  Python 3.12             |
                       |  /project --> your repo  |
                       +-------------------------+
                                  |  HTTPS
                                  v
                       Sovereign AI Platform
                       (LLM API)
```

## Persistent Data

| Container Path | Local Path | Purpose |
|----------------|-----------|---------|
| `/project` | `PROJECT_PATH` from `.env` | Repository to analyze (read-only) |
| `/app/knowledge` | `./knowledge/` | Pipeline results |
| `/app/logs` | `./logs/` | Log files |
| `/app/inputs` | `./inputs/` | Uploaded task files, requirements, etc. |
| `/app/config` | `./config/` | Pipeline phase configuration |
| `/app/.env` | `./.env` | API keys and settings |
