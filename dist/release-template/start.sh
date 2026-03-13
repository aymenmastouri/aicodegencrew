#!/usr/bin/env bash
# =============================================================================
# SDLC Pilot - One-Click Dashboard Launcher
#
# Usage:
#   ./start.sh              Start the dashboard
#   ./start.sh stop         Stop the dashboard
#   ./start.sh logs         Show live logs
# =============================================================================
set -e

cd "$(dirname "$0")"

if docker compose version &> /dev/null; then DC="docker compose"
elif command -v docker-compose &> /dev/null; then DC="docker-compose"
else echo "[ERROR] Docker not found. Please install Docker Desktop."; exit 1; fi

if [ "${1}" = "stop" ]; then $DC down; echo "[OK] Dashboard stopped."; exit 0; fi
if [ "${1}" = "logs" ]; then $DC logs -f; exit 0; fi

echo ""
echo "========================================="
echo "  SDLC Pilot - Dashboard"
echo "========================================="
echo ""

if ! docker info &> /dev/null; then
    echo "[ERROR] Docker is not running. Please start Docker Desktop."
    exit 1
fi
echo "[OK] Docker is running."

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "[!] .env file created from template."
    echo ""
    echo "  Please open .env and configure:"
    echo "    PROJECT_PATH=/path/to/your/repo"
    echo "    OPENAI_API_KEY=sk-your-actual-key"
    echo ""
    echo "  Then run ./start.sh again."
    exit 1
fi

if grep -q "sk-your-api-key-here" .env; then
    echo "[ERROR] API key not configured!"
    echo "  Open .env and replace sk-your-api-key-here with your actual key."
    exit 1
fi
echo "[OK] API key configured."

if grep -q "path.to.your.repo" .env; then
    echo "[ERROR] Repository path not configured!"
    echo "  Open .env and set PROJECT_PATH to your repository, e.g.:"
    echo "    PROJECT_PATH=/home/user/projects/myapp"
    exit 1
fi
echo "[OK] Repository path configured."

mkdir -p knowledge logs inputs config

if ! docker image inspect sdlc-pilot/backend:latest &> /dev/null; then
    echo ""
    echo "Loading Docker images -- this only happens once, ~1-2 minutes..."
    docker load -i sdlc-pilot-backend.tar.gz
    docker load -i sdlc-pilot-frontend.tar.gz
    echo "[OK] Images loaded."
fi

echo ""
echo "Starting dashboard..."
$DC up -d

echo ""
echo "========================================="
echo "  Dashboard is ready!"
echo "  Open in browser: http://localhost"
echo "========================================="
echo ""
echo "  ./start.sh stop    Stop the dashboard"
echo "  ./start.sh logs    Show live logs"
echo ""
