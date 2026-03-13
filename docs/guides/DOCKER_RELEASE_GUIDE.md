# Docker Release Guide

Step-by-step instructions for building, packaging, and distributing the SDLC Pilot Dashboard as a self-contained Docker ZIP.

---

## Part 1: Build a Release (Developer)

### Prerequisites

- Docker Desktop running
- Working directory: project root (`cd aicodegencrew`)
- Capgemini CA certificate at `certs/CapgeminiPKIRootCA.crt`

### Step 1: Build Docker Images

```bash
docker compose -f ui/docker-compose.ui.yml build --no-cache
```

This builds two multi-stage images:

| Image | Base | Size | Contents |
|-------|------|------|----------|
| `ui-backend` | python:3.12-slim | ~350 MB | FastAPI + compiled .pyc bytecode (no .py source) |
| `ui-frontend` | nginx:alpine | ~27 MB | Minified Angular bundle |

**Source code protection:** The backend Dockerfile (`ui/backend/Dockerfile.dev`) uses a two-stage build:
1. **Build stage:** installs dependencies, compiles all `.py` → `.pyc` with `compileall -b`, then deletes every `.py` file
2. **Final stage:** copies only bytecode + installed packages — zero Python source in the image

**Corporate SSL:** The Capgemini Root CA is baked into both images so HTTPS to the Sovereign AI Platform works without extra configuration.

### Step 2: Tag Images

```bash
VERSION=0.7.2

docker tag ui-backend:latest  sdlc-pilot/backend:${VERSION}
docker tag ui-backend:latest  sdlc-pilot/backend:latest
docker tag ui-frontend:latest sdlc-pilot/frontend:${VERSION}
docker tag ui-frontend:latest sdlc-pilot/frontend:latest
```

> Update `VERSION` to match `pyproject.toml`.

### Step 3: Verify No Source Code in Backend Image

```bash
docker run --rm sdlc-pilot/backend:latest find /app/src /app/ui/backend -name "*.py" | head -20
```

Expected output: empty (no `.py` files). To confirm `.pyc` files exist:

```bash
docker run --rm sdlc-pilot/backend:latest find /app/src -name "*.pyc" | head -10
```

### Step 4: Prepare the Release Directory

```bash
VERSION=0.7.2
RELEASE_DIR=dist/sdlc-pilot-v${VERSION}/sdlc-pilot-v${VERSION}
mkdir -p ${RELEASE_DIR}
```

Copy these files into the release directory:

| File | Source | Notes |
|------|--------|-------|
| `docker-compose.yml` | `dist/sdlc-pilot-v${VERSION}/` | Release compose (uses `sdlc-pilot/*` images) |
| `.env.example` | `dist/sdlc-pilot-v${VERSION}/` | All fields for Settings UI schema |
| `start.bat` | `dist/sdlc-pilot-v${VERSION}/` | Windows launcher |
| `start.sh` | `dist/sdlc-pilot-v${VERSION}/` | macOS/Linux launcher (LF line endings!) |
| `clean.bat` | `dist/sdlc-pilot-v${VERSION}/` | Windows full cleanup |
| `clean.sh` | `dist/sdlc-pilot-v${VERSION}/` | macOS/Linux full cleanup (LF line endings!) |
| `README.md` | `dist/sdlc-pilot-v${VERSION}/` | End-user documentation |
| `LICENSE` | `dist/sdlc-pilot-v${VERSION}/` | Capgemini SE proprietary license |

> **IMPORTANT:** Never include `.env` with real API keys. Only `.env.example` with placeholders.

> **IMPORTANT:** `start.sh` and `clean.sh` must have LF line endings (not CRLF), otherwise they fail on macOS/Linux.

### Step 5: Export Docker Images

```bash
docker save sdlc-pilot/backend:latest | gzip > ${RELEASE_DIR}/sdlc-pilot-backend.tar.gz
docker save sdlc-pilot/frontend:latest | gzip > ${RELEASE_DIR}/sdlc-pilot-frontend.tar.gz
```

### Step 6: Create ZIP

```bash
cd dist/sdlc-pilot-v${VERSION}
zip -r ../sdlc-pilot-v${VERSION}.zip sdlc-pilot-v${VERSION}/
```

Final ZIP structure (~376 MB):

```
sdlc-pilot-v0.7.2/
├── .env.example                    ← Configuration template
├── docker-compose.yml              ← Container orchestration
├── start.bat                       ← Windows launcher
├── start.sh                        ← macOS/Linux launcher
├── clean.bat                       ← Windows full cleanup
├── clean.sh                        ← macOS/Linux full cleanup
├── README.md                       ← End-user guide
├── LICENSE                         ← Capgemini SE proprietary
├── sdlc-pilot-backend.tar.gz      ← Backend image (~350 MB)
└── sdlc-pilot-frontend.tar.gz     ← Frontend image (~27 MB)
```

### One-Liner (Build → Tag → Export → ZIP)

```bash
VERSION=0.7.2 && \
RELEASE_DIR=dist/sdlc-pilot-v${VERSION}/sdlc-pilot-v${VERSION} && \
docker compose -f ui/docker-compose.ui.yml build --no-cache && \
docker tag ui-backend:latest sdlc-pilot/backend:latest && \
docker tag ui-frontend:latest sdlc-pilot/frontend:latest && \
docker save sdlc-pilot/backend:latest | gzip > ${RELEASE_DIR}/sdlc-pilot-backend.tar.gz && \
docker save sdlc-pilot/frontend:latest | gzip > ${RELEASE_DIR}/sdlc-pilot-frontend.tar.gz && \
cd dist/sdlc-pilot-v${VERSION} && zip -r ../sdlc-pilot-v${VERSION}.zip sdlc-pilot-v${VERSION}/
```

---

## Part 2: Install & Run (End Users)

### Prerequisite

**Docker Desktop** — download from https://www.docker.com/products/docker-desktop

After installation, start Docker Desktop and wait until the whale icon appears in the system tray.

### Step 1: Extract ZIP

Extract `sdlc-pilot-v0.7.2.zip` (right-click → "Extract All" on Windows).

### Step 2: Configure

1. Copy `.env.example` to `.env`:
   - Windows: `copy .env.example .env`
   - macOS/Linux: `cp .env.example .env`
2. Open `.env` in a text editor and set at minimum:
   ```
   PROJECT_PATH=C:\projects\myapp          # path to the repo to analyze
   OPENAI_API_KEY=sk-your-actual-key       # your API key
   ```

### Step 3: Start

| OS | Command |
|----|---------|
| Windows | Double-click `start.bat` |
| macOS/Linux | `./start.sh` |

First launch loads Docker images from `.tar.gz` files (~1-2 minutes). Subsequent starts take ~5 seconds.

### Step 4: Open Dashboard

Open **http://localhost** in your browser.

### Commands

| Action | Windows | macOS / Linux |
|--------|---------|---------------|
| Start | `start.bat` | `./start.sh` |
| Stop | `start.bat stop` | `./start.sh stop` |
| View logs | `start.bat logs` | `./start.sh logs` |
| Restart | `start.bat stop` then `start.bat` | `./start.sh stop` then `./start.sh` |
| Full cleanup | `clean.bat` | `./clean.sh` |

> `clean.bat` / `clean.sh` stops containers, removes volumes, deletes images, and clears data directories (knowledge, logs, inputs, config). Your `.env` is preserved.

### Updating to a New Version

1. Stop: `start.bat stop`
2. Extract the new ZIP
3. Copy your existing `.env` into the new folder
4. Start: `start.bat`

---

## Part 3: Troubleshooting

| Problem | Solution |
|---------|----------|
| "Docker is not running" | Start Docker Desktop, wait for the system tray icon |
| "API key not configured" | Open `.env` and set `OPENAI_API_KEY` |
| "Repository path not configured" | Open `.env` and set `PROJECT_PATH` to your repo |
| Browser shows nothing | Wait 30 seconds, reload http://localhost |
| Port 80 already in use | Stop other web servers (IIS, XAMPP, Apache, Skype) |
| `start.bat` closes instantly | Right-click → "Run as administrator" |
| Image loading fails | Verify `.tar.gz` files are in the same folder |

---

## Part 4: Architecture

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
                       |  Bytecode only (.pyc)    |
                       |  + Capgemini CA          |
                       |  + truststore            |
                       |  /project --> user repo  |
                       +-------------------------+
                                  |  HTTPS
                                  v
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
- [ ] `.env` with real keys is NOT included in ZIP
- [ ] `start.sh` and `clean.sh` have LF line endings
- [ ] `start.bat` has no parentheses in echo lines inside if-blocks (CMD parser limitation)
- [ ] Backend image has 0 `.py` files (verify with Step 3 above)
- [ ] `LICENSE` has correct contact email and copyright year
- [ ] Footer in `app.component.ts` matches LICENSE copyright
- [ ] All scripts and README are in English
- [ ] Docker images load and start successfully from a clean state
- [ ] Dashboard accessible at http://localhost after `start.bat`
- [ ] Settings UI shows all field groups (LLM, Indexing, Output, Logging, etc.)
- [ ] File uploads persist across container restarts (inputs/ volume)
- [ ] `clean.bat` / `clean.sh` fully removes containers, images, and data
