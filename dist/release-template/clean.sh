#!/usr/bin/env bash
# =============================================================================
# SDLC Pilot - Full Cleanup
# Stops containers, removes volumes, deletes Docker images,
# and wipes runtime data directories (knowledge, logs, inputs, reports).
# Preserved: .env, .env.example, config/ (contains release config files).
# =============================================================================
set -e

cd "$(dirname "$0")"

echo ""
echo "========================================="
echo "  SDLC Pilot - Full Cleanup"
echo "========================================="
echo ""

# Detect docker compose command
if docker compose version &> /dev/null; then DC="docker compose"
elif command -v docker-compose &> /dev/null; then DC="docker-compose"
else echo "[ERROR] Docker not found."; exit 1; fi

# 1. Clean data directories (via container to handle UID 999 ownership)
echo "[1/4] Cleaning data directories..."
if docker ps -q -f name=sdlc-pilot-backend | grep -q .; then
    docker exec sdlc-pilot-backend rm -rf /app/knowledge/* /app/logs/* /app/inputs/* 2>/dev/null || true
    echo "[OK] Data cleaned via container."
else
    echo "[!] Container not running — cleaning locally..."
fi

# 2. Stop containers, remove volumes and networks
echo "[2/4] Stopping containers..."
$DC down -v --remove-orphans 2>/dev/null || true
# Force-remove named containers in case compose context differs
docker rm -f sdlc-pilot-backend sdlc-pilot-frontend 2>/dev/null || true
# Remove associated volumes
docker volume ls -q --filter name=sdlc-pilot 2>/dev/null | xargs -r docker volume rm 2>/dev/null || true
echo "[OK] Containers and volumes removed."

# 3. Remove Docker images
echo "[3/4] Removing Docker images..."
docker rmi sdlc-pilot/backend:latest 2>/dev/null || true
docker rmi sdlc-pilot/frontend:latest 2>/dev/null || true
echo "[OK] Images removed."

# 4. Remove runtime data directories from host (config/ is preserved — it contains release files)
echo "[4/4] Removing data directories..."
rm -rf knowledge logs inputs reports 2>/dev/null || true
# Fallback for UID 999 owned files — use a temp container (no sudo needed)
if [ -d knowledge ] || [ -d logs ] || [ -d inputs ] || [ -d reports ]; then
    echo "      Some dirs owned by UID 999 — using Docker to remove..."
    docker run --rm -v "$(pwd):/work" alpine sh -c "rm -rf /work/knowledge /work/logs /work/inputs /work/reports" 2>/dev/null || true
fi
# Final fallback: ask for sudo only if dirs still exist
if [ -d knowledge ] || [ -d logs ] || [ -d inputs ] || [ -d reports ]; then
    echo "      Requesting sudo to remove remaining dirs..."
    sudo rm -rf knowledge logs inputs reports 2>/dev/null || true
fi
echo "[OK] Data directories removed."

echo ""
echo "========================================="
echo ""
echo "  Cleanup complete!"
echo ""
echo "  Your .env, .env.example, and config/ are preserved."
echo "  To reinstall, run ./start.sh again."
echo ""
echo "========================================="
echo ""
