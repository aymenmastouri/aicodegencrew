#!/usr/bin/env bash
# =============================================================================
# SDLC Pilot — Stop Dashboard
#
# Usage:  ./stop.sh
#
# Stops containers. Preserves all data (knowledge, logs, reports).
# To restart: ./start.sh
# To remove everything: ./clean.sh
# =============================================================================

set -e

cd "$(dirname "$0")"

# Detect docker compose command
if docker compose version &> /dev/null; then DC="docker compose"
elif command -v docker-compose &> /dev/null; then DC="docker-compose"
else echo "[ERROR] Docker not found."; exit 1; fi

echo ""
echo "Stopping SDLC Pilot..."
$DC down
echo ""
echo -e "\033[0;32m[OK]\033[0m Dashboard stopped. Data preserved."
echo ""
echo "Commands:"
echo "  ./start.sh     Restart the Dashboard"
echo "  ./clean.sh     Full cleanup (removes ALL data)"
echo ""
