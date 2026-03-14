#!/bin/bash
# =============================================================================
# AICodeGenCrew — Build & Deploy Script
#
# Usage:
#   ./deploy.sh                    # Build images + create release ZIP
#   ./deploy.sh --wsl              # Build + deploy to WSL2 + start
#   ./deploy.sh --skip-build       # Repackage ZIP only (skip Docker build)
#   ./deploy.sh --skip-build --wsl # Deploy existing ZIP to WSL2
#   ./deploy.sh --push REGISTRY    # Build + push to registry
#   ./deploy.sh --tag v2.0         # Custom version tag
# =============================================================================
set -e

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
VERSION="0.7.4"
RELEASE_NAME="sdlc-pilot-v${VERSION}"
TAG="latest"
PUSH=false
REGISTRY=""
WSL=false
SKIP_BUILD=false

DIST_DIR="${PROJECT_ROOT}/dist"
RELEASE_DIR="${DIST_DIR}/${RELEASE_NAME}"
TEMPLATE_DIR="${DIST_DIR}/release-template"

WSL_DISTRO="Ubuntu-24.04"
WSL_USER="amastour"
WSL_DEPLOY_DIR="/home/${WSL_USER}/${RELEASE_NAME}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

step()  { echo -e "\n${CYAN}[$1]${NC} $2"; }
info()  { echo -e "${GREEN}  [OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}  [!]${NC} $1"; }
fail()  { echo -e "${RED}  [ERROR]${NC} $1"; exit 1; }

# ---------------------------------------------------------------------------
# Args
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case $1 in
        --tag)          TAG="$2"; shift 2 ;;
        --push)         PUSH=true; REGISTRY="$2"; shift 2 ;;
        --wsl)          WSL=true; shift ;;
        --skip-build)   SKIP_BUILD=true; shift ;;
        --help)
            echo "Usage: ./deploy.sh [OPTIONS]"
            echo ""
            echo "  --wsl              Deploy to WSL2 and start Dashboard"
            echo "  --skip-build       Skip Docker image build"
            echo "  --tag VERSION      Image tag (default: latest)"
            echo "  --push REGISTRY    Push images to registry"
            exit 0
            ;;
        *)  echo "Unknown option: $1"; exit 1 ;;
    esac
done

cd "$PROJECT_ROOT"

echo -e "\n${BLUE}==============================================${NC}"
echo -e "${BLUE}  SDLC Pilot v${VERSION} — Build & Deploy${NC}"
echo -e "${BLUE}==============================================${NC}"

# =========================================================================
# PHASE 1: BUILD DOCKER IMAGES
# =========================================================================
if ! $SKIP_BUILD; then

    step "1/6" "Preparing build context..."
    rm -rf ui/backend/src_bundle ui/backend/certs
    cp -r src/aicodegencrew ui/backend/src_bundle
    cp pyproject.toml ui/backend/src_bundle/pyproject.toml
    # Corporate CA cert (optional — Dockerfile uses wildcard COPY so missing cert is OK)
    [ -d certs ] && cp -r certs ui/backend/certs
    info "Source bundle ready."

    step "2/6" "Building backend Docker image..."
    docker build -t sdlc-pilot/backend:${TAG} ui/backend/
    info "Backend image built."

    step "3/6" "Building frontend Docker image..."
    docker build -f ui/frontend/Dockerfile -t sdlc-pilot/frontend:${TAG} .
    info "Frontend image built."

    # Cleanup
    rm -rf ui/backend/src_bundle ui/backend/certs

    # Show image sizes
    echo ""
    docker images sdlc-pilot/backend:${TAG} --format "  Backend:  {{.Size}}"
    docker images sdlc-pilot/frontend:${TAG} --format "  Frontend: {{.Size}}"

else
    step "1/6" "Skipped (--skip-build)"
    step "2/6" "Skipped (--skip-build)"
    step "3/6" "Skipped (--skip-build)"
fi

# =========================================================================
# PHASE 2: CREATE RELEASE PACKAGE
# =========================================================================
step "4/6" "Creating release package..."

# Remove old release dir (tolerate "device busy" — just reuse the dir)
rm -rf "${RELEASE_DIR}" 2>/dev/null || true
mkdir -p "${RELEASE_DIR}"

# Copy template files
for f in docker-compose.yml .env.example start.sh clean.sh README.md; do
    [ -f "${TEMPLATE_DIR}/${f}" ] && cp "${TEMPLATE_DIR}/${f}" "${RELEASE_DIR}/"
done

# Copy config directory
[ -d "${TEMPLATE_DIR}/config" ] && cp -r "${TEMPLATE_DIR}/config" "${RELEASE_DIR}/"

# Copy license
[ -f "${PROJECT_ROOT}/LICENSE" ] && cp "${PROJECT_ROOT}/LICENSE" "${RELEASE_DIR}/"

# Save Docker images
echo "  Saving backend image..."
docker save sdlc-pilot/backend:${TAG} | gzip > "${RELEASE_DIR}/sdlc-pilot-backend.tar.gz"
echo "  Saving frontend image..."
docker save sdlc-pilot/frontend:${TAG} | gzip > "${RELEASE_DIR}/sdlc-pilot-frontend.tar.gz"

# Create ZIP
rm -f "${DIST_DIR}/${RELEASE_NAME}.zip"
cd "${DIST_DIR}"
zip -r "${RELEASE_NAME}.zip" "${RELEASE_NAME}/"
cd "${PROJECT_ROOT}"

ZIP_SIZE=$(du -h "${DIST_DIR}/${RELEASE_NAME}.zip" | cut -f1)
info "Release ZIP: dist/${RELEASE_NAME}.zip (${ZIP_SIZE})"

# =========================================================================
# PHASE 3: PUSH TO REGISTRY (optional)
# =========================================================================
if $PUSH; then
    step "5/6" "Pushing to registry: ${REGISTRY}..."
    docker tag sdlc-pilot/backend:${TAG} ${REGISTRY}/sdlc-pilot-backend:${TAG}
    docker tag sdlc-pilot/frontend:${TAG} ${REGISTRY}/sdlc-pilot-frontend:${TAG}
    docker push ${REGISTRY}/sdlc-pilot-backend:${TAG}
    docker push ${REGISTRY}/sdlc-pilot-frontend:${TAG}
    info "Pushed to ${REGISTRY}"
else
    step "5/6" "Push skipped (no --push)"
fi

# =========================================================================
# PHASE 4: DEPLOY TO WSL2 (optional)
# =========================================================================
if $WSL; then
    step "6/6" "Deploying to WSL2 (${WSL_DISTRO})..."

    # Save .env from old deployment (if exists)
    echo "  Backing up old .env..."
    wsl -d "${WSL_DISTRO}" -- bash -c "
        [ -f '${WSL_DEPLOY_DIR}/.env' ] && cp '${WSL_DEPLOY_DIR}/.env' '/tmp/.env.backup' || true
    " 2>/dev/null || true

    # Stop old containers + remove old images + cleanup
    echo "  Cleaning old deployment..."
    wsl -d "${WSL_DISTRO}" -- bash -c "
        # Stop containers (PROJECT_PATH needed for docker-compose.yml)
        cd '${WSL_DEPLOY_DIR}' 2>/dev/null && \
            PROJECT_PATH=/tmp docker compose down -v --remove-orphans 2>/dev/null
        # Remove old images
        docker rmi sdlc-pilot/backend:latest sdlc-pilot/frontend:latest 2>/dev/null
        # Remove old dir (Docker alpine handles UID 999 owned files)
        docker run --rm -v /home/${WSL_USER}:/host alpine rm -rf /host/${RELEASE_NAME} 2>/dev/null
        true
    " 2>/dev/null || true
    info "Old deployment cleaned."

    # Extract ZIP in WSL2
    echo "  Extracting release..."
    WSL_ZIP="/mnt/c/projects/aicodegencrew/dist/${RELEASE_NAME}.zip"
    wsl -d "${WSL_DISTRO}" -- bash -c "
        set -e
        cd /home/${WSL_USER}
        unzip -o '${WSL_ZIP}'
    "
    info "Extracted to ${WSL_DEPLOY_DIR}"

    # Restore .env from backup or create from template
    echo "  Configuring .env..."
    wsl -d "${WSL_DISTRO}" -- bash -c "
        cd '${WSL_DEPLOY_DIR}'
        if [ -f '/tmp/.env.backup' ]; then
            cp '/tmp/.env.backup' .env
            rm -f '/tmp/.env.backup'
        else
            cp .env.example .env
            sed -i 's|PROJECT_PATH=.*|PROJECT_PATH=/mnt/c/uvz|' .env
            sed -i 's|OPENAI_API_KEY=sk-your-api-key-here|OPENAI_API_KEY=${OPENAI_API_KEY:-sk-your-api-key-here}|' .env
        fi
    "
    info ".env configured."

    # Start Dashboard using start.sh (as documented in README)
    echo "  Starting Dashboard..."
    wsl -d "${WSL_DISTRO}" -- bash -c "
        cd '${WSL_DEPLOY_DIR}'
        chmod +x start.sh clean.sh
        ./start.sh
    "

    echo ""
    echo -e "${GREEN}==============================================${NC}"
    echo -e "${GREEN}  Deploy complete!${NC}"
    echo -e "${GREEN}  Dashboard: http://localhost${NC}"
    echo -e "${GREEN}==============================================${NC}"
    echo ""

else
    step "6/6" "WSL deploy skipped (no --wsl)"

    echo ""
    echo -e "${GREEN}==============================================${NC}"
    echo -e "${GREEN}  Build complete!${NC}"
    echo -e "${GREEN}  ZIP: dist/${RELEASE_NAME}.zip (${ZIP_SIZE})${NC}"
    echo -e "${GREEN}==============================================${NC}"
    echo ""
    echo "  Next steps:"
    echo "    Deploy to WSL2:  ./deploy.sh --skip-build --wsl"
    echo "    Push to registry: ./deploy.sh --skip-build --push REGISTRY"
    echo ""
fi
