#!/usr/bin/env bash
# ============================================================================
# setup-local.sh — Complete SDLC Pilot setup for WSL2 Ubuntu
#
# Installs EVERYTHING from scratch: git, Python 3.12, Node.js 22, clones the
# repo, configures .env, installs all dependencies, and starts the dashboard.
#
# Der Manager bekommt NUR diese Datei (per Teams, E-Mail, USB, etc.)
# und führt sie aus — alles andere passiert automatisch:
#
#   bash setup-local.sh
#
# Das Script klont das Repo, installiert alles, startet das Dashboard.
#
# Options:
#   --setup-only       Setup without starting the dashboard
#   --run-e2e <repo>   Setup + run full E2E pipeline on a repository
# ============================================================================

set -euo pipefail

# Prevent interactive prompts during apt install (e.g., tzdata)
export DEBIAN_FRONTEND=noninteractive
export TZ="${TZ:-Europe/Berlin}"

# ── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

log()  { echo -e "${CYAN}[setup]${NC} $*"; }
ok()   { echo -e "${GREEN}  ✓${NC} $*"; }
warn() { echo -e "${YELLOW}  !${NC} $*"; }
fail() { echo -e "${RED}  ✗ $*${NC}"; exit 1; }

# ── Configuration — Capgemini Sovereign AI Platform ──────────────────────────
# IMPORTANT: Fill in the API key before distributing this script to managers!
# Everything else is pre-configured — the manager only runs this script.
GIT_REPO_URL="https://bnotkca.pl.s2-eu.capgemini.com/gitlab/ai-group/aicodegencrew.git"
INSTALL_DIR="$HOME/aicodegencrew"

ENV_API_KEY="sk-gX7FLpLxfFUyORK8rv1Rog"
ENV_API_BASE="https://litellm.bnotk.sovai-de.apps.ce.capgemini.com/v1"
ENV_MODEL="openai/code"
ENV_FAST_MODEL="openai/code"
ENV_CODEGEN_MODEL="openai/code"
ENV_VISION_MODEL="openai/vision"
ENV_EMBED_MODEL="embed"
ENV_MAX_OUTPUT_TOKENS="65536"
ENV_CONTEXT_WINDOW="262144"

# ── Parse args ───────────────────────────────────────────────────────────────
SETUP_ONLY=false
RUN_E2E=false
E2E_REPO=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --setup-only) SETUP_ONLY=true; shift ;;
        --run-e2e)    RUN_E2E=true; E2E_REPO="${2:-}"; shift; shift ;;
        *)            fail "Unknown argument: $1" ;;
    esac
done

echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║          SDLC Pilot — Local Setup (WSL2 Ubuntu)         ║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================================
# STEP 1: System packages (apt)
# ============================================================================
log "${BOLD}Step 1/7: System packages${NC}"

sudo apt-get update -qq

# Pre-configure timezone to avoid interactive prompt
sudo ln -snf /usr/share/zoneinfo/"$TZ" /etc/localtime 2>/dev/null || true
echo "$TZ" | sudo tee /etc/timezone >/dev/null 2>&1 || true

# Git
if ! command -v git &>/dev/null; then
    sudo apt-get install -y -qq git
    ok "Git installed"
else
    ok "Git $(git --version | grep -oP '\d+\.\d+\.\d+')"
fi

# Build tools
sudo apt-get install -y -qq build-essential curl ca-certificates gnupg unzip >/dev/null 2>&1
ok "Build tools ready"

# Python 3.12
if ! command -v python3.12 &>/dev/null; then
    log "Installing Python 3.12..."
    sudo apt-get install -y -qq software-properties-common >/dev/null 2>&1
    sudo add-apt-repository -y ppa:deadsnakes/ppa >/dev/null 2>&1
    sudo apt-get update -qq
    sudo apt-get install -y -qq python3.12 python3.12-venv python3.12-dev
    ok "Python 3.12 installed"
else
    ok "Python $(python3.12 --version | grep -oP '[\d.]+')"
fi

# Ensure pip
python3.12 -m ensurepip --upgrade >/dev/null 2>&1 || sudo apt-get install -y -qq python3-pip >/dev/null 2>&1
ok "pip ready"

# Node.js 22 LTS
if ! command -v node &>/dev/null || [[ "$(node --version | grep -oP '\d+' | head -1)" -lt 18 ]]; then
    log "Installing Node.js 22 LTS..."
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
        | sudo gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg 2>/dev/null || true
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_22.x nodistro main" \
        | sudo tee /etc/apt/sources.list.d/nodesource.list >/dev/null
    sudo apt-get update -qq
    sudo apt-get install -y -qq nodejs
    ok "Node.js $(node --version) installed"
else
    ok "Node.js $(node --version)"
fi

ok "npm $(npm --version)"

# ============================================================================
# STEP 2: Clone repository
# ============================================================================
log "${BOLD}Step 2/7: Repository${NC}"

# Detect if we're already running inside the cloned repo
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/../pyproject.toml" ]]; then
    INSTALL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
    ok "Running from inside repo: $INSTALL_DIR"
elif [[ -d "$INSTALL_DIR/.git" ]]; then
    ok "Repository exists at $INSTALL_DIR"
    cd "$INSTALL_DIR"
    git pull --quiet || warn "git pull failed — using existing code"
elif [[ -d "$INSTALL_DIR/src/aicodegencrew" ]]; then
    ok "Project found at $INSTALL_DIR (no .git)"
else
    log "Cloning repository..."
    git clone "$GIT_REPO_URL" "$INSTALL_DIR"
    ok "Cloned to $INSTALL_DIR"
fi

ROOT="$INSTALL_DIR"
cd "$ROOT"

# ============================================================================
# STEP 3: Python virtual environment
# ============================================================================
log "${BOLD}Step 3/7: Python environment${NC}"

if [[ ! -d "$ROOT/.venv" ]]; then
    python3.12 -m venv "$ROOT/.venv"
    ok "Virtual environment created"
else
    ok "Virtual environment exists"
fi

# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate"

pip install --quiet --upgrade pip setuptools wheel
pip install --quiet -e ".[dev,parsers]"
ok "Python dependencies installed"

# ============================================================================
# STEP 4: Configure .env
# ============================================================================
log "${BOLD}Step 4/7: Configuration (.env)${NC}"

# Always write .env with pre-configured values (overwrite if exists)
cat > "$ROOT/.env" << ENVEOF
# ── SDLC Pilot Configuration ────────────────────────────────────────────────
# Auto-generated by setup-local.sh on $(date +%Y-%m-%d)

PROJECT_PATH=/path/to/your/repo

# Task and reference input directories
TASK_INPUT_DIR=./inputs/tasks
REQUIREMENTS_DIR=./inputs/requirements
LOGS_DIR=./inputs/logs
REFERENCE_DIR=./inputs/reference

# ── LLM Configuration (Capgemini Sovereign AI Platform) ─────────────────────
LLM_PROVIDER=onprem
API_BASE=${ENV_API_BASE}
OPENAI_API_KEY=${ENV_API_KEY}

# Qwen3-Coder-Next (80B MoE, 3B active, 262K ctx)
MODEL=${ENV_MODEL}
FAST_MODEL=${ENV_FAST_MODEL}
CODEGEN_MODEL=${ENV_CODEGEN_MODEL}
VISION_MODEL=${ENV_VISION_MODEL}

# Token limits (Qwen3-Coder-Next best practices)
MAX_LLM_OUTPUT_TOKENS=${ENV_MAX_OUTPUT_TOKENS}
LLM_CONTEXT_WINDOW=${ENV_CONTEXT_WINDOW}

# Embeddings
EMBED_MODEL=${ENV_EMBED_MODEL}

# Output
INDEX_MODE=auto
OUTPUT_DIR=./knowledge/architecture
DOCS_OUTPUT_DIR=./architecture-docs

# Logging
LOG_LEVEL=INFO
CREWAI_TRACING_ENABLED=false
ENVEOF
ok ".env configured (API key + all settings pre-filled)"

# Validate API key is not the placeholder
if [[ "$ENV_API_KEY" == "sk-FILL-IN-BEFORE-DISTRIBUTING" ]]; then
    echo ""
    echo -e "  ${RED}┌──────────────────────────────────────────────────────────┐${NC}"
    echo -e "  ${RED}│  ${BOLD}FEHLER: API-Key wurde nicht eingetragen!${NC}${RED}                │${NC}"
    echo -e "  ${RED}│                                                          │${NC}"
    echo -e "  ${RED}│  Der Entwickler muss den API-Key in setup-local.sh       │${NC}"
    echo -e "  ${RED}│  eintragen BEVOR das Script verteilt wird.               │${NC}"
    echo -e "  ${RED}│                                                          │${NC}"
    echo -e "  ${RED}│  Zeile 36: ENV_API_KEY=\"sk-...\"                          │${NC}"
    echo -e "  ${RED}└──────────────────────────────────────────────────────────┘${NC}"
    echo ""
    fail "API-Key Platzhalter nicht ersetzt. Script kann nicht fortfahren."
fi

# ============================================================================
# STEP 5: Frontend dependencies
# ============================================================================
log "${BOLD}Step 5/7: Frontend${NC}"

cd "$ROOT/ui/frontend"
npm install --silent 2>/dev/null
ok "Frontend dependencies installed"

cd "$ROOT"
npm install --silent 2>/dev/null
ok "Root dev dependencies installed"

# ============================================================================
# STEP 6: Create directories + verify
# ============================================================================
log "${BOLD}Step 6/7: Directories & verification${NC}"

mkdir -p "$ROOT/logs" \
         "$ROOT/knowledge" \
         "$ROOT/inputs/tasks" \
         "$ROOT/inputs/requirements" \
         "$ROOT/inputs/logs" \
         "$ROOT/inputs/reference"
ok "Directory structure ready"

# Verify Python package
python3.12 -c "import aicodegencrew; print('  ✓ aicodegencrew package OK')" 2>/dev/null \
    || warn "aicodegencrew import check failed"

# Verify LLM connectivity
python3.12 -c "
from aicodegencrew.shared.utils.llm_factory import check_llm_connectivity
ok, msg = check_llm_connectivity(timeout=5)
print(f'  {chr(10003) if ok else chr(33)} LLM: {msg}')
" 2>/dev/null || warn "LLM connectivity check failed"

# ============================================================================
# STEP 7: Done — start or print instructions
# ============================================================================
echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║                   Setup abgeschlossen!                   ║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}Verzeichnis:${NC}   $ROOT"
echo -e "  ${BOLD}Python:${NC}        $(python3.12 --version)"
echo -e "  ${BOLD}Node:${NC}          $(node --version)"
echo -e "  ${BOLD}npm:${NC}           $(npm --version)"
echo ""
echo -e "  ${BOLD}Dashboard starten:${NC}"
echo -e "    cd $ROOT"
echo -e "    source .venv/bin/activate"
echo -e "    npm run dev"
echo -e "    → ${CYAN}http://localhost:4200${NC}"
echo ""
echo -e "  ${BOLD}Pipeline (CLI):${NC}"
echo -e "    aicodegencrew run --preset document"
echo ""
echo -e "  ${BOLD}E2E Pipeline:${NC}"
echo -e "    bash scripts/setup-local.sh --run-e2e ~/mein-projekt"
echo ""

if $SETUP_ONLY; then
    exit 0
fi

if $RUN_E2E; then
    [[ -z "$E2E_REPO" ]] && fail "--run-e2e braucht einen Repo-Pfad, z.B.: --run-e2e ~/mein-projekt"
    [[ ! -d "$E2E_REPO" ]] && fail "Repository nicht gefunden: $E2E_REPO"

    echo -e "${BOLD}${CYAN}━━━ E2E Pipeline: $E2E_REPO ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    export PROJECT_PATH="$E2E_REPO"

    PHASES=("discover" "extract" "analyze" "document")
    TOTAL=${#PHASES[@]}
    CURRENT=0
    FAILED=0

    for phase in "${PHASES[@]}"; do
        CURRENT=$((CURRENT + 1))
        echo -e "${CYAN}[$CURRENT/$TOTAL] Phase: ${BOLD}$phase${NC}"
        START_TIME=$(date +%s)

        if aicodegencrew run --phases "$phase" --index-mode auto --no-clean 2>&1 | tail -5; then
            ELAPSED=$(( $(date +%s) - START_TIME ))
            ok "$phase completed (${ELAPSED}s)"
        else
            ELAPSED=$(( $(date +%s) - START_TIME ))
            warn "$phase failed after ${ELAPSED}s — check logs/current.log"
            FAILED=$((FAILED + 1))
        fi
        echo ""
    done

    echo -e "${BOLD}${GREEN}━━━ E2E fertig: $((TOTAL - FAILED))/${TOTAL} Phasen erfolgreich ━━━━━━━━━━${NC}"
    echo -e "  Ergebnisse: ${CYAN}$ROOT/knowledge/${NC}"
    ls -lh "$ROOT/knowledge/" 2>/dev/null || true
    [[ $FAILED -gt 0 ]] && exit 1
else
    log "Dashboard wird gestartet..."
    echo ""
    cd "$ROOT"
    source "$ROOT/.venv/bin/activate"
    exec npm run dev
fi
