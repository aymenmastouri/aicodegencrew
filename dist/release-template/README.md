# SDLC Pilot - Dashboard

AI-powered Software Development Lifecycle assistant. Runs entirely in Docker — no Python, Node.js, or other tools required.

## Prerequisites

**Docker** — one of the following:

| Environment | Installation |
|-------------|-------------|
| **WSL2 (Windows, no license needed)** | Inside WSL2 (Ubuntu): `sudo apt-get install -y docker.io docker-compose-plugin` |
| **Linux** | Install Docker Engine via your package manager |
| **Docker Desktop (if licensed)** | Download from https://www.docker.com/products/docker-desktop |

> **WSL2 setup (one-time):**
> ```bash
> sudo apt-get update
> sudo apt-get install -y docker.io docker-compose-plugin
> sudo usermod -aG docker $USER
> # Close and reopen WSL, then:
> sudo service docker start
> ```

## Quick Start

### 1. Configure

Copy the example configuration:

| OS | Command |
|----|---------|
| Windows CMD | `copy .env.example .env` |
| WSL2 / Linux | `cp .env.example .env` |

Open `.env` in any text editor and set **at minimum** these two values:

```
# Windows (CMD / PowerShell):
PROJECT_PATH=C:\projects\myapp

# WSL2 / Linux:
PROJECT_PATH=/mnt/c/projects/myapp        # or /home/user/projects/myapp

OPENAI_API_KEY=sk-your-actual-key          # your API key
```

> **Note:** `PROJECT_PATH` is your repository path on your machine.
> In Docker mode, the container mounts it automatically as a read-only volume.
> Changing this value requires a restart (`start.bat stop` then `start.bat`, or `./start.sh stop` then `./start.sh`).

#### LLM Model Configuration

The `.env` file contains model settings that map to the Sovereign AI Platform. Each model serves a specific purpose:

| Variable | Default | Used by | Purpose |
|----------|---------|---------|---------|
| `MODEL` | `openai/complex_tasks` | Analyze, Document, Plan, Verify, Deliver | Deep reasoning, architecture analysis (large context) |
| `FAST_MODEL` | `openai/chat` | Triage, classification | Fast, lightweight tasks |
| `CODEGEN_MODEL` | `openai/code` | Implement | Code generation, tool use |
| `VISION_MODEL` | `openai/vision` | OCR, document analysis | Multimodal (images + text) |
| `EMBED_MODEL` | `embed` | Discover (indexing) | Vector embeddings for semantic search |

> **Note:** All models are accessed via `API_BASE` (Sovereign AI Platform). No local Ollama or GPU required. The default values work out of the box — only change them if your platform uses different model aliases.

### 2. Start the Dashboard

| OS | Command |
|----|---------|
| Windows | Double-click **`start.bat`** or run it from CMD |
| WSL2 / Linux | `chmod +x start.sh clean.sh && ./start.sh` |

On first launch, Docker images are loaded from the included `.tar.gz` files (~1-2 minutes). Subsequent starts take ~5 seconds.

### 3. Open the Dashboard

Open **http://localhost** in your browser.

## Commands

| Action | Windows | WSL2 / Linux |
|--------|---------|-------------|
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
| "Docker is not running" | **WSL2:** `sudo service docker start` — **Docker Desktop:** Start app, wait for tray icon |
| "API key not configured" | Open `.env` and set `OPENAI_API_KEY` |
| "Repository path not configured" | Open `.env` and set `PROJECT_PATH` to your repo |
| Browser shows nothing | Wait 30 seconds, reload http://localhost |
| Port 80 already in use | Stop other web servers (IIS, XAMPP, Apache, Skype) |
| `start.bat` closes instantly | Right-click > "Run as administrator" |
| WSL2: permission denied on `start.sh` | `chmod +x start.sh clean.sh` then `./start.sh` |
| WSL2: Docker daemon not running | `sudo service docker start` |
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
