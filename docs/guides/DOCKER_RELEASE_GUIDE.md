# Docker Release Guide

Step-by-step instructions for building, packaging, and distributing the SDLC Pilot Dashboard as a self-contained Docker ZIP.

---

## Part 1: Build a Release (Developer)

### Prerequisites

- **Docker Engine** installed and running (WSL2, Linux, or Docker Desktop)
- Working directory: project root (`cd aicodegencrew`)
- Corporate CA certificate at `certs/CorporateRootCA.crt` (optional)

**WSL2 setup (if not yet installed):**

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin
sudo usermod -aG docker $USER
sudo service docker start
```

> **WSL2 note:** If your project is on the Windows filesystem, access it via `/mnt/c/projects/aicodegencrew`.

---

### Step 1: Build Docker Images

```bash
docker compose -f ui/docker-compose.ui.yml build --no-cache
```

This builds two images:

| Image | Base | Size | Contents |
|-------|------|------|----------|
| `ui-backend` | python:3.12-slim | ~350 MB | FastAPI + compiled .pyc bytecode (no .py source) |
| `ui-frontend` | nginx:alpine | ~27 MB | Minified Angular bundle |

---

### Step 2: Tag Images

```bash
docker tag ui-backend:latest sdlc-pilot/backend:latest
docker tag ui-frontend:latest sdlc-pilot/frontend:latest
```

---

### Step 3: Prepare the Release Directory

```bash
VERSION=0.7.3
RELEASE_DIR=dist/sdlc-pilot-v${VERSION}

mkdir -p ${RELEASE_DIR}
cp -r dist/release-template/* ${RELEASE_DIR}/
cp dist/release-template/.env.example ${RELEASE_DIR}/
cp -r config ${RELEASE_DIR}/
cp LICENSE ${RELEASE_DIR}/
```

> **IMPORTANT:** Never include `.env` with real API keys — only `.env.example`.

---

### Step 4: Export Docker Images

```bash
docker save sdlc-pilot/backend:latest | gzip > ${RELEASE_DIR}/sdlc-pilot-backend.tar.gz
docker save sdlc-pilot/frontend:latest | gzip > ${RELEASE_DIR}/sdlc-pilot-frontend.tar.gz
```

---

### Step 5: Create ZIP

**WSL2 / Linux / macOS:**

```bash
cd dist && zip -r sdlc-pilot-v${VERSION}.zip sdlc-pilot-v${VERSION}/
```

**Windows (PowerShell):**

```powershell
cd dist
Compress-Archive -Path "sdlc-pilot-v0.7.3\*" -DestinationPath "sdlc-pilot-v0.7.3.zip" -Force
```

---

### Step 6: Verify (optional)

Check that no `.py` source code leaked into the backend image:

```bash
docker run --rm sdlc-pilot/backend:latest find /app/src /app/ui/backend -name "*.py" | head -20
```

Expected: empty output (no `.py` files).

---

### Complete One-Liner

Copy-paste this to do everything in one go (WSL2 / Linux / macOS):

```bash
VERSION=0.7.3 && \
RELEASE_DIR=dist/sdlc-pilot-v${VERSION} && \
docker compose -f ui/docker-compose.ui.yml build --no-cache && \
docker tag ui-backend:latest sdlc-pilot/backend:latest && \
docker tag ui-frontend:latest sdlc-pilot/frontend:latest && \
mkdir -p ${RELEASE_DIR} && \
cp -r dist/release-template/* ${RELEASE_DIR}/ && \
cp dist/release-template/.env.example ${RELEASE_DIR}/ && \
cp -r config ${RELEASE_DIR}/ && \
cp LICENSE ${RELEASE_DIR}/ && \
docker save sdlc-pilot/backend:latest | gzip > ${RELEASE_DIR}/sdlc-pilot-backend.tar.gz && \
docker save sdlc-pilot/frontend:latest | gzip > ${RELEASE_DIR}/sdlc-pilot-frontend.tar.gz && \
cd dist && zip -r sdlc-pilot-v${VERSION}.zip sdlc-pilot-v${VERSION}/
```

> **Bump version:** Only change `VERSION=0.7.3` — the rest works automatically.

---

### Final ZIP Structure (~376 MB)

```
sdlc-pilot-v0.7.3/
├── .env.example                    ← Configuration template
├── docker-compose.yml              ← Container orchestration
├── start.bat                       ← Windows launcher
├── start.sh                        ← macOS/Linux launcher
├── clean.bat                       ← Windows full cleanup
├── clean.sh                        ← macOS/Linux full cleanup
├── README.md                       ← End-user guide
├── LICENSE                         ← MIT License
├── config/
│   └── phases_config.yaml          ← Pipeline phase & preset configuration
├── sdlc-pilot-backend.tar.gz      ← Backend image (~350 MB)
└── sdlc-pilot-frontend.tar.gz     ← Frontend image (~27 MB)
```

### What's in `dist/release-template/` (versioned in git)

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Release compose (uses `sdlc-pilot/*` images) |
| `.env.example` | All config fields — drives the Settings UI schema |
| `README.md` | End-user documentation |
| `start.bat` / `start.sh` | Launchers (load images, check env, start containers) |
| `clean.bat` / `clean.sh` | Full cleanup scripts |

> **IMPORTANT:** `start.sh` and `clean.sh` must have **LF** line endings (not CRLF), otherwise they fail on macOS/Linux.

---

## Part 2: Install & Run (End Users)

### Prerequisite

**Docker Engine** — one of the following:

| Environment | How to install |
|-------------|----------------|
| **WSL2 (Windows, no license needed)** | `sudo apt-get install -y docker.io docker-compose-plugin` inside WSL2 |
| **Linux** | Install via package manager (apt, dnf, etc.) |
| **Docker Desktop (if licensed)** | Download from docker.com |

> **WSL2:** After installing, start Docker with `sudo service docker start` and add your user to the docker group: `sudo usermod -aG docker $USER` (then restart WSL).

---

### Step 1: Extract ZIP

**Windows:**
```
Right-click → "Extract All"
```

**WSL2 / Linux:**
```bash
unzip sdlc-pilot-v0.7.3.zip
cd sdlc-pilot-v0.7.3
```

---

### Step 2: Configure

```bash
cp .env.example .env
```

Open `.env` in a text editor and set at minimum:

```
PROJECT_PATH=/home/user/projects/myapp    # path to your repo
OPENAI_API_KEY=sk-your-actual-key         # your API key
```

> **Windows path example:** `PROJECT_PATH=C:\projects\myapp`
> **WSL2 path example:** `PROJECT_PATH=/mnt/c/projects/myapp`

---

### Step 3: Start

| OS | Command |
|----|---------|
| **Windows** | Double-click `start.bat` |
| **WSL2 / Linux** | `./start.sh` |

First launch loads Docker images from `.tar.gz` files (~1-2 minutes). Subsequent starts take ~5 seconds.

---

### Step 4: Open Dashboard

Open **http://localhost** in your browser.

---

### Commands

| Action | Windows | WSL2 / Linux |
|--------|---------|--------------|
| Start | `start.bat` | `./start.sh` |
| Stop | `start.bat stop` | `./start.sh stop` |
| View logs | `start.bat logs` | `./start.sh logs` |
| Restart | `start.bat stop` then `start.bat` | `./start.sh stop` then `./start.sh` |
| Full cleanup | `clean.bat` | `./clean.sh` |

> `clean` stops containers, removes volumes, deletes images, and clears data directories. Your `.env` is preserved.

---

### Updating to a New Version

1. Stop: `start.bat stop` (or `./start.sh stop`)
2. Extract the new ZIP
3. Copy your existing `.env` into the new folder
4. Start: `start.bat` (or `./start.sh`)

---

## Part 3: Troubleshooting

| Problem | Solution |
|---------|----------|
| "Docker is not running" | **WSL2:** `sudo service docker start` — **Desktop:** Start app, wait for tray icon |
| "API key not configured" | Open `.env` and set `OPENAI_API_KEY` |
| "Repository path not configured" | Open `.env` and set `PROJECT_PATH` |
| Browser shows nothing | Wait 30 seconds, reload http://localhost |
| Port 80 already in use | Stop other web servers (IIS, XAMPP, Apache, Skype) |
| `start.bat` closes instantly | Right-click → "Run as administrator" |
| WSL2: permission denied on `start.sh` | `chmod +x start.sh clean.sh` then `./start.sh` |
| WSL2: Docker daemon not running | `sudo service docker start` |
| WSL2: 500 error / permission denied | Run `sudo chown -R 999:999 knowledge logs inputs config` — `start.sh` does this automatically |
| Image loading fails | Verify `.tar.gz` files are in the same folder |

---

## Part 4: Architecture

```
Browser (http://localhost)
    │
    ▼
┌─────────────────────┐
│  Frontend (nginx)    │  Port 80
│  Angular SPA         │
│  Proxy: /api/* ──────┼──► Backend
└─────────────────────┘
                            │
                       ┌────▼────────────────────┐
                       │  Backend (FastAPI)        │  Port 8001 (internal)
                       │  Python 3.12              │
                       │  Bytecode only (.pyc)     │
                       │  + Corporate CA           │
                       │  + truststore             │
                       │  /project ──► user repo   │
                       └──────────────────────────┘
                                  │  HTTPS
                                  ▼
                       Sovereign AI Platform
                       (LLM API)
```

### Ports

| Port | Service | Purpose |
|------|---------|---------|
| 80 | Frontend (nginx) | Dashboard UI + API reverse proxy |
| 8001 | Backend (FastAPI) | REST API (internal only, not exposed to host) |

### Volumes (Persistent Data)

| Container Path | Local Path | Purpose |
|----------------|-----------|---------|
| `/project` | `PROJECT_PATH` from `.env` | Repository to analyze (read-only) |
| `/app/knowledge` | `./knowledge/` | Pipeline results |
| `/app/logs` | `./logs/` | Log files |
| `/app/inputs` | `./inputs/` | Uploaded task files, requirements, etc. |
| `/app/config` | `./config/` | Pipeline phase configuration |
| `/app/.env` | `./.env` | API keys and settings (read-write) |
| `/app/.env.example` | `./.env.example` | Schema template for Settings UI (read-only) |

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Multi-stage Dockerfile (bytecode only) | Protects proprietary source code — no `.py` files in shipped images |
| `env_file` + `environment` override | `.env` loads all user config; `PROJECT_PATH` is overridden to `/project` (Docker mount point) |
| `truststore` + baked-in CA cert | Corporate HTTPS works without user configuration |
| Non-root `appuser` | Security best practice |
| `curl` in backend image | Required for Docker healthcheck |
| `client_max_body_size 25m` in nginx | Supports file uploads up to 25 MB |
| `.env.example` mounted read-only | Backend reads it to generate Settings UI field schema |
| `start_period: 30s` healthcheck | Prevents false-negative on slow machines during startup |

---

## Part 5: Checklist Before Shipping

- [ ] Version in `pyproject.toml` updated
- [ ] `.env.example` has all fields (drives Settings UI schema)
- [ ] `.env` with real keys is **NOT** included in ZIP
- [ ] `start.sh` and `clean.sh` have **LF** line endings
- [ ] `start.bat` has no parentheses in echo lines inside if-blocks (CMD parser limitation)
- [ ] Backend image has 0 `.py` files (verify with Step 6)
- [ ] `LICENSE` has correct contact email and copyright year
- [ ] Footer in `app.component.ts` matches LICENSE copyright
- [ ] All scripts and README are in English
- [ ] Docker images load and start successfully from a clean state
- [ ] Dashboard accessible at http://localhost after `start.bat`
- [ ] Run Pipeline → "Select Preset" dropdown shows options (confirms `config/` is in ZIP)
- [ ] Settings UI shows all field groups (LLM, Indexing, Output, Logging, etc.)
- [ ] File uploads persist across container restarts (`inputs/` volume)
- [ ] WSL2/Linux: data dirs owned by UID 999 after first start
- [ ] `clean.bat` / `clean.sh` fully removes containers, images, and data
