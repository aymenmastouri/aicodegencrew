#!/bin/bash
# =============================================================================
# AICodeGenCrew — Deploy Script
# Macht ALLES: Bauen, Verifizieren, Taggen, Pushen
#
# Usage:
#   ./deploy.sh                              # Bauen + Verifizieren (lokal)
#   ./deploy.sh --push registry.firma.internal  # + Push zur Registry
#   ./deploy.sh --tag v2.0                   # Bestimmte Version
#   ./deploy.sh --run                        # Bauen + lokal starten
# =============================================================================
set -e

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
TAG="latest"
PUSH=false
REGISTRY=""
RUN=false

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ---------------------------------------------------------------------------
# Args
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case $1 in
        --tag)    TAG="$2"; shift 2 ;;
        --push)   PUSH=true; REGISTRY="$2"; shift 2 ;;
        --run)    RUN=true; shift ;;
        --help)
            echo "Usage: ./deploy.sh [--tag VERSION] [--push REGISTRY] [--run]"
            echo ""
            echo "  --tag VERSION    Image-Tag setzen (default: latest)"
            echo "  --push REGISTRY  Images zur Registry pushen"
            echo "  --run            Nach dem Build lokal starten"
            exit 0
            ;;
        *)  echo "Unbekannte Option: $1"; exit 1 ;;
    esac
done

cd "$PROJECT_ROOT"

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  AICodeGenCrew — Secure Deploy${NC}"
echo -e "${BLUE}  Tag: ${TAG}${NC}"
echo -e "${BLUE}============================================${NC}"

# ---------------------------------------------------------------------------
# Step 1: Backend Image bauen
# ---------------------------------------------------------------------------
echo ""
echo -e "${YELLOW}[1/5] Backend bauen (Python → Bytecode)...${NC}"
docker build -f ui/backend/Dockerfile.secure -t aicodegencrew-backend:$TAG .
echo -e "${GREEN}  OK${NC}"

# ---------------------------------------------------------------------------
# Step 2: Frontend Image bauen
# ---------------------------------------------------------------------------
echo ""
echo -e "${YELLOW}[2/5] Frontend bauen (Angular → minified JS)...${NC}"
docker build -f ui/frontend/Dockerfile -t aicodegencrew-frontend:$TAG ui/frontend/
echo -e "${GREEN}  OK${NC}"

# ---------------------------------------------------------------------------
# Step 3: Verifizieren — kein Source Code im Image
# ---------------------------------------------------------------------------
echo ""
echo -e "${YELLOW}[3/5] Verifizieren: kein Source Code im Image...${NC}"

# Backend: keine .py Dateien?
PY_FILES=$(docker run --rm --entrypoint="" aicodegencrew-backend:$TAG \
    find /app -name "*.py" 2>/dev/null || true)

if [ -z "$PY_FILES" ]; then
    echo -e "${GREEN}  Backend: Keine .py Dateien gefunden${NC}"
else
    echo -e "${RED}  WARNUNG: .py Dateien im Backend-Image gefunden:${NC}"
    echo "$PY_FILES"
    echo -e "${RED}  Build abgebrochen!${NC}"
    exit 1
fi

# Frontend: keine .ts Dateien?
TS_FILES=$(docker run --rm --entrypoint="" aicodegencrew-frontend:$TAG \
    find /usr/share/nginx/html -name "*.ts" 2>/dev/null || true)

if [ -z "$TS_FILES" ]; then
    echo -e "${GREEN}  Frontend: Keine .ts Dateien gefunden${NC}"
else
    echo -e "${RED}  WARNUNG: .ts Dateien im Frontend-Image gefunden:${NC}"
    echo "$TS_FILES"
    echo -e "${RED}  Build abgebrochen!${NC}"
    exit 1
fi

# Image-Größen
echo ""
echo -e "  Image-Größen:"
docker images aicodegencrew-backend:$TAG --format "    Backend:  {{.Size}}"
docker images aicodegencrew-frontend:$TAG --format "    Frontend: {{.Size}}"

# ---------------------------------------------------------------------------
# Step 4: Push zur Registry (optional)
# ---------------------------------------------------------------------------
if $PUSH; then
    echo ""
    echo -e "${YELLOW}[4/5] Push zur Registry: ${REGISTRY}...${NC}"

    docker tag aicodegencrew-backend:$TAG $REGISTRY/aicodegencrew-backend:$TAG
    docker tag aicodegencrew-frontend:$TAG $REGISTRY/aicodegencrew-frontend:$TAG

    docker push $REGISTRY/aicodegencrew-backend:$TAG
    docker push $REGISTRY/aicodegencrew-frontend:$TAG

    # Auch als "latest" taggen wenn es ein Versions-Tag ist
    if [ "$TAG" != "latest" ]; then
        docker tag aicodegencrew-backend:$TAG $REGISTRY/aicodegencrew-backend:latest
        docker tag aicodegencrew-frontend:$TAG $REGISTRY/aicodegencrew-frontend:latest
        docker push $REGISTRY/aicodegencrew-backend:latest
        docker push $REGISTRY/aicodegencrew-frontend:latest
    fi

    echo -e "${GREEN}  OK — gepusht nach ${REGISTRY}${NC}"
else
    echo ""
    echo -e "${BLUE}[4/5] Push übersprungen (kein --push angegeben)${NC}"
fi

# ---------------------------------------------------------------------------
# Step 5: Lokal starten (optional)
# ---------------------------------------------------------------------------
if $RUN; then
    echo ""
    echo -e "${YELLOW}[5/5] Lokal starten...${NC}"

    cd ui/

    # .env erstellen falls nicht vorhanden
    if [ ! -f .env ]; then
        cp deploy.env.example .env
        echo -e "${YELLOW}  .env aus Template erstellt — bitte API_BASE eintragen!${NC}"
    fi

    docker compose -f docker-compose.secure.yml up -d

    echo -e "${GREEN}  OK — läuft auf http://localhost${NC}"
else
    echo ""
    echo -e "${BLUE}[5/5] Starten übersprungen (kein --run angegeben)${NC}"
fi

# ---------------------------------------------------------------------------
# Fertig
# ---------------------------------------------------------------------------
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  FERTIG!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "  Images:"
echo "    aicodegencrew-backend:$TAG"
echo "    aicodegencrew-frontend:$TAG"
echo ""

if $PUSH; then
    echo "  Registry:"
    echo "    $REGISTRY/aicodegencrew-backend:$TAG"
    echo "    $REGISTRY/aicodegencrew-frontend:$TAG"
    echo ""
fi

echo "  Nächste Schritte:"
if ! $PUSH; then
    echo "    Push:    ./deploy.sh --tag $TAG --push registry.firma.internal"
fi
if ! $RUN; then
    echo "    Testen:  ./deploy.sh --tag $TAG --run"
fi
echo ""
