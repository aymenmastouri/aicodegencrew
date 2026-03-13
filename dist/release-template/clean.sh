#!/usr/bin/env bash
# =============================================================================
# SDLC Pilot - Full Cleanup
# Stops containers, removes named volumes, deletes Docker images.
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

# 1. Stop containers and remove named volumes
echo "[1/2] Stopping containers and removing volumes..."
$DC down -v --remove-orphans 2>/dev/null || true
echo "[OK] Containers and volumes removed."

# 2. Remove Docker images
echo "[2/2] Removing Docker images..."
docker rmi sdlc-pilot/backend:latest 2>/dev/null || true
docker rmi sdlc-pilot/frontend:latest 2>/dev/null || true
echo "[OK] Images removed."

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
