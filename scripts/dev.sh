#!/usr/bin/env bash
# ============================================================================
# dev.sh — Start/stop/restart the SDLC Dashboard dev servers
#
# Works in Git Bash on Windows AND Linux/macOS.
#
# Usage:
#   ./scripts/dev.sh          # restart (stop + start)
#   ./scripts/dev.sh start    # start only
#   ./scripts/dev.sh stop     # stop only
#   ./scripts/dev.sh status   # check if running
# ============================================================================

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_PORT=8001
FRONTEND_PORT=4200
BACKEND_LOG="$ROOT/logs/backend-dev.log"
FRONTEND_LOG="$ROOT/logs/frontend-dev.log"

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'
CYAN='\033[0;36m'; NC='\033[0m'

# ── Cross-platform helpers ───────────────────────────────────────────────────

is_windows() {
    [[ "$OSTYPE" == "msys" || "$OSTYPE" == "mingw"* || "$OSTYPE" == "cygwin" ]]
}

# Kill process by PID (cross-platform)
kill_pid() {
    local pid=$1
    if is_windows; then
        cmd.exe //C "taskkill /F /T /PID $pid" >/dev/null 2>&1 || true
    else
        kill -9 "$pid" 2>/dev/null || true
    fi
}

# Kill all processes on a port
kill_port() {
    local port=$1
    if is_windows; then
        # Use cmd.exe for netstat + taskkill (works in Git Bash)
        local pids
        pids=$(cmd.exe //C "netstat -ano 2>nul" 2>/dev/null | grep ":${port}" | grep "LISTENING" | awk '{print $NF}' | sort -u | tr -d '\r')
        for pid in $pids; do
            if [ -n "$pid" ] && [ "$pid" != "0" ]; then
                cmd.exe //C "taskkill /F /T /PID $pid" >/dev/null 2>&1 || true
                echo -e "  ${YELLOW}Killed PID $pid on port $port${NC}"
            fi
        done
    else
        local pids
        pids=$(lsof -ti ":$port" 2>/dev/null || true)
        for pid in $pids; do
            kill -9 "$pid" 2>/dev/null || true
            echo -e "  ${YELLOW}Killed PID $pid on port $port${NC}"
        done
    fi
}

# Check if port is listening
port_in_use() {
    local port=$1
    if is_windows; then
        cmd.exe //C "netstat -ano 2>nul" 2>/dev/null | grep -q ":${port}.*LISTENING"
    else
        lsof -ti ":$port" >/dev/null 2>&1
    fi
}

# Wait for port to be free
wait_port_free() {
    local port=$1 i=0
    while [ $i -lt 10 ]; do
        if ! port_in_use "$port"; then return 0; fi
        sleep 1; i=$((i + 1))
    done
    echo -e "${RED}Port $port still in use after 10s${NC}"
    return 1
}

# Wait for port to come up
wait_port_up() {
    local port=$1 label=$2 i=0
    while [ $i -lt 30 ]; do
        if port_in_use "$port"; then
            echo -e "  ${GREEN}$label ready on :${port}${NC}"
            return 0
        fi
        sleep 1; i=$((i + 1))
    done
    echo -e "  ${RED}$label failed to start on :${port} (waited 30s)${NC}"
    return 1
}

# ── Commands ─────────────────────────────────────────────────────────────────

do_stop() {
    echo -e "${CYAN}Stopping dev servers...${NC}"

    kill_port $BACKEND_PORT
    kill_port $FRONTEND_PORT

    # Second attempt: retry kill_port if still stuck (never kill by image name —
    # taskkill /IM python.exe would destroy unrelated processes like IDEs, Claude, etc.)
    if port_in_use $BACKEND_PORT; then
        echo -e "  ${YELLOW}Port $BACKEND_PORT still occupied — retrying...${NC}"
        sleep 2
        kill_port $BACKEND_PORT
    fi
    if port_in_use $FRONTEND_PORT; then
        echo -e "  ${YELLOW}Port $FRONTEND_PORT still occupied — retrying...${NC}"
        sleep 2
        kill_port $FRONTEND_PORT
    fi

    wait_port_free $BACKEND_PORT
    wait_port_free $FRONTEND_PORT

    echo -e "${GREEN}Stopped.${NC}"
}

do_start() {
    echo -e "${CYAN}Starting dev servers...${NC}"
    mkdir -p "$ROOT/logs"

    # Check ports are free
    if port_in_use $BACKEND_PORT; then
        echo -e "${RED}Port $BACKEND_PORT in use — stopping first...${NC}"
        kill_port $BACKEND_PORT
        wait_port_free $BACKEND_PORT || return 1
    fi
    if port_in_use $FRONTEND_PORT; then
        echo -e "${RED}Port $FRONTEND_PORT in use — stopping first...${NC}"
        kill_port $FRONTEND_PORT
        wait_port_free $FRONTEND_PORT || return 1
    fi

    # Find Python
    PYTHON="python"
    if [ -f "$ROOT/.venv/Scripts/python.exe" ]; then
        PYTHON="$ROOT/.venv/Scripts/python.exe"
    elif [ -f "$ROOT/.venv/bin/python" ]; then
        PYTHON="$ROOT/.venv/bin/python"
    fi

    # Start backend
    echo -e "  Starting backend..."
    cd "$ROOT"
    "$PYTHON" -m uvicorn ui.backend.main:app --host 127.0.0.1 --port $BACKEND_PORT --reload \
        > "$BACKEND_LOG" 2>&1 &

    # Start frontend
    echo -e "  Starting frontend..."
    cd "$ROOT/ui/frontend"
    npm start > "$FRONTEND_LOG" 2>&1 &
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
    if port_in_use $BACKEND_PORT; then
        echo -e "  ${GREEN}Backend running on :${BACKEND_PORT}${NC}"
    else
        echo -e "  ${RED}Backend not running${NC}"
    fi
    if port_in_use $FRONTEND_PORT; then
        echo -e "  ${GREEN}Frontend running on :${FRONTEND_PORT}${NC}"
    else
        echo -e "  ${RED}Frontend not running${NC}"
    fi
}

# ── Main ─────────────────────────────────────────────────────────────────────

CMD="${1:-restart}"

case "$CMD" in
    stop)    do_stop ;;
    start)   do_start ;;
    restart) do_stop; do_start ;;
    status)  do_status ;;
    *)       echo "Usage: $0 {start|stop|restart|status}"; exit 1 ;;
esac
