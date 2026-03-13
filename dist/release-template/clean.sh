#!/usr/bin/env bash
# =============================================================================
# SDLC Pilot - Full Cleanup
# Stops containers, removes volumes, and deletes Docker images.
# Your .env and uploaded files are NOT deleted.
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

# 1. Stop containers and remove volumes
echo "[1/3] Stopping containers..."
$DC down -v 2>/dev/null || true
echo "[OK] Containers stopped."

# 2. Remove Docker images
echo "[2/3] Removing Docker images..."
docker rmi sdlc-pilot/backend:latest 2>/dev/null || true
docker rmi sdlc-pilot/frontend:latest 2>/dev/null || true
echo "[OK] Images removed."

# 3. Clean up data directories
echo "[3/3] Cleaning data directories..."
rm -rf knowledge logs inputs config
echo "[OK] Data directories removed."

echo ""
echo "========================================="
echo ""
echo "  Cleanup complete!"
echo ""
echo "  Your .env and .env.example are preserved."
echo "  To reinstall, run ./start.sh again."
echo ""
echo "========================================="
echo ""
