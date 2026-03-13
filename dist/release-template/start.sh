#!/usr/bin/env bash
# =============================================================================
# SDLC Pilot — One-Click Start (Docker)
#
# Usage:
#   ./start.sh                    # start Dashboard
#   ./start.sh stop               # stop Dashboard
#   ./start.sh logs               # show logs
#
# Prerequisites: Docker Desktop (Windows/macOS) or Docker Engine (Linux/WSL).
# =============================================================================

set -e

cd "$(dirname "$0")"

# ── Detect docker compose command (v2 preferred, v1 fallback) ────────────────
if docker compose version &> /dev/null; then
    DC="docker compose"
elif command -v docker-compose &> /dev/null; then
    DC="docker-compose"
else
    echo "[ERROR] Neither 'docker compose' nor 'docker-compose' found."
    echo "        Install Docker Desktop: https://www.docker.com/products/docker-desktop"
    exit 1
fi

# ── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ── Stop ─────────────────────────────────────────────────────────────────────
if [ "${1}" = "stop" ]; then
    echo "Stopping SDLC Pilot..."
    $DC down
    info "Dashboard stopped."
    exit 0
fi

# ── Logs ─────────────────────────────────────────────────────────────────────
if [ "${1}" = "logs" ]; then
    $DC logs -f
    exit 0
fi

# ── Pre-flight checks ───────────────────────────────────────────────────────
echo ""
echo "========================================="
echo "  SDLC Pilot — Dashboard Startup"
echo "========================================="
echo ""

# Check Docker daemon
if ! docker info &> /dev/null 2>&1; then
    error "Docker is not running."
    error "Please start Docker Desktop (or 'sudo systemctl start docker' on Linux)."
    exit 1
fi
info "Docker is running."

# Check .env
if [ ! -f ".env" ]; then
    cp .env.example .env
    warn ".env created from template."
    warn ""
    warn "Please edit .env and set your API key:"
    warn "  OPENAI_API_KEY=sk-your-actual-key"
    warn ""
    warn "Then run ./start.sh again."
    exit 1
fi

# Check if API key is still placeholder
if grep -q "sk-your-api-key-here" .env; then
    error "API key not configured!"
    error ""
    error "Open .env in a text editor and replace:"
    error "  OPENAI_API_KEY=sk-your-api-key-here"
    error "with your actual API key."
    error ""
    error "Then run ./start.sh again."
    exit 1
fi
info ".env configured."

# Check if PROJECT_PATH is still placeholder
if grep -q "path/to/your/repo\|path\\to\\your\\repo" .env; then
    error "Repository path not configured!"
    error ""
    error "Open .env and set PROJECT_PATH to your repository, e.g.:"
    error "  PROJECT_PATH=/home/user/projects/myapp"
    error ""
    error "Then run ./start.sh again."
    exit 1
fi
info "Repository path configured."

# ── Load Docker images on first run ──────────────────────────────────────────
if ! docker image inspect sdlc-pilot/backend:latest &> /dev/null; then
    echo ""
    echo "Loading Docker images — this only happens once..."
    docker load -i sdlc-pilot-backend.tar.gz
    docker load -i sdlc-pilot-frontend.tar.gz
    info "Images loaded."
fi

# ── Start ────────────────────────────────────────────────────────────────────
echo ""
echo "Starting Dashboard..."
echo ""

$DC up -d

echo ""
info "========================================="
info "  Dashboard is ready!"
info ""
info "  Open: http://localhost"
info ""
info "  Backend API: http://localhost/api/health"
info "========================================="
echo ""
echo "Commands:"
echo "  ./start.sh logs     Show live logs"
echo "  ./start.sh stop     Stop the Dashboard"
echo ""
