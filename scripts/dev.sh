#!/usr/bin/env bash
# ============================================================================
# dev.sh — Start/stop/restart the SDLC Dashboard dev servers
#
# Usage:
#   ./scripts/dev.sh          # restart (stop + start)
#   ./scripts/dev.sh start    # start only (fails if ports in use)
#   ./scripts/dev.sh stop     # stop only
#   ./scripts/dev.sh status   # check if running
# ============================================================================

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_PORT=8001
FRONTEND_PORT=4200
BACKEND_PID_FILE="$ROOT/logs/.backend.pid"
FRONTEND_PID_FILE="$ROOT/logs/.frontend.pid"
BACKEND_LOG="$ROOT/logs/backend-dev.log"
FRONTEND_LOG="$ROOT/logs/frontend-dev.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# ── Helpers ──────────────────────────────────────────────────────────────────

kill_port() {
    local port=$1
    local pids
    pids=$(netstat -ano 2>/dev/null | grep ":${port}.*LISTENING" | awk '{print $NF}' | sort -u)
    for pid in $pids; do
        if [ -n "$pid" ] && [ "$pid" != "0" ]; then
            taskkill //F //T //PID "$pid" >/dev/null 2>&1 || true
            echo -e "  ${YELLOW}Killed PID $pid on port $port${NC}"
        fi
    done
}

wait_port_free() {
    local port=$1
    local max_wait=10
    local i=0
    while [ $i -lt $max_wait ]; do
        if ! netstat -ano 2>/dev/null | grep -q ":${port}.*LISTENING"; then
            return 0
        fi
        sleep 1
        i=$((i + 1))
    done
    echo -e "${RED}Port $port still in use after ${max_wait}s${NC}"
    return 1
}

wait_port_up() {
    local port=$1
    local label=$2
    local max_wait=30
    local i=0
    while [ $i -lt $max_wait ]; do
        if netstat -ano 2>/dev/null | grep -q ":${port}.*LISTENING"; then
            echo -e "  ${GREEN}$label ready on :${port}${NC}"
            return 0
        fi
        sleep 1
        i=$((i + 1))
    done
    echo -e "  ${RED}$label failed to start on :${port} (waited ${max_wait}s)${NC}"
    return 1
}

check_port() {
    local port=$1
    local label=$2
    if netstat -ano 2>/dev/null | grep -q ":${port}.*LISTENING"; then
        local pid
        pid=$(netstat -ano 2>/dev/null | grep ":${port}.*LISTENING" | awk '{print $NF}' | head -1)
        echo -e "  ${GREEN}$label running on :${port} (PID $pid)${NC}"
        return 0
    else
        echo -e "  ${RED}$label not running${NC}"
        return 1
    fi
}

# ── Commands ─────────────────────────────────────────────────────────────────

do_stop() {
    echo -e "${CYAN}Stopping dev servers...${NC}"

    # Kill by PID file first (clean)
    for pidfile in "$BACKEND_PID_FILE" "$FRONTEND_PID_FILE"; do
        if [ -f "$pidfile" ]; then
            local pid
            pid=$(cat "$pidfile" 2>/dev/null || true)
            if [ -n "$pid" ]; then
                taskkill //F //T //PID "$pid" >/dev/null 2>&1 || true
            fi
            rm -f "$pidfile"
        fi
    done

    # Kill by port (catches orphans)
    kill_port $BACKEND_PORT
    kill_port $FRONTEND_PORT

    # Kill ALL uvicorn/python processes using our ports (brute force)
    taskkill //F //IM python.exe >/dev/null 2>&1 || true
    taskkill //F //IM python3.exe >/dev/null 2>&1 || true

    wait_port_free $BACKEND_PORT
    wait_port_free $FRONTEND_PORT

    echo -e "${GREEN}Stopped.${NC}"
}

do_start() {
    echo -e "${CYAN}Starting dev servers...${NC}"
    mkdir -p "$ROOT/logs"

    # Check ports are free
    if netstat -ano 2>/dev/null | grep -q ":${BACKEND_PORT}.*LISTENING"; then
        echo -e "${RED}Port $BACKEND_PORT already in use! Run: ./scripts/dev.sh stop${NC}"
        return 1
    fi
    if netstat -ano 2>/dev/null | grep -q ":${FRONTEND_PORT}.*LISTENING"; then
        echo -e "${RED}Port $FRONTEND_PORT already in use! Run: ./scripts/dev.sh stop${NC}"
        return 1
    fi

    # Start backend (use venv python if available)
    echo -e "  Starting backend..."
    cd "$ROOT"
    PYTHON="python"
    if [ -f "$ROOT/.venv/Scripts/python.exe" ]; then
        PYTHON="$ROOT/.venv/Scripts/python.exe"
    elif [ -f "$ROOT/.venv/bin/python" ]; then
        PYTHON="$ROOT/.venv/bin/python"
    fi
    "$PYTHON" -m uvicorn ui.backend.main:app --host 127.0.0.1 --port $BACKEND_PORT --reload \
        > "$BACKEND_LOG" 2>&1 &
    echo $! > "$BACKEND_PID_FILE"

    # Start frontend
    echo -e "  Starting frontend..."
    cd "$ROOT/ui/frontend"
    npm start > "$FRONTEND_LOG" 2>&1 &
    echo $! > "$FRONTEND_PID_FILE"
    cd "$ROOT"

    # Wait for both
    wait_port_up $BACKEND_PORT "Backend"
    wait_port_up $FRONTEND_PORT "Frontend"

    echo ""
    echo -e "${GREEN}Dev servers running:${NC}"
    echo -e "  Frontend:  ${CYAN}http://localhost:${FRONTEND_PORT}${NC}"
    echo -e "  Backend:   ${CYAN}http://localhost:${BACKEND_PORT}${NC}"
    echo -e "  Logs:      ${CYAN}$BACKEND_LOG${NC}"
    echo -e "             ${CYAN}$FRONTEND_LOG${NC}"
}

do_status() {
    echo -e "${CYAN}Dev server status:${NC}"
    check_port $BACKEND_PORT "Backend" || true
    check_port $FRONTEND_PORT "Frontend" || true
}

# ── Main ─────────────────────────────────────────────────────────────────────

CMD="${1:-restart}"

case "$CMD" in
    stop)
        do_stop
        ;;
    start)
        do_start
        ;;
    restart)
        do_stop
        do_start
        ;;
    status)
        do_status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
