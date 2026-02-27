#!/bin/bash
# =============================================================================
# Build secure Docker images for distribution
#
# Usage:
#   ./build-secure.sh                    # Build both images
#   ./build-secure.sh --verify           # Build + verify no source code leaked
#   ./build-secure.sh --push REGISTRY    # Build + push to registry
# =============================================================================
set -e

TAG="${TAG:-latest}"
VERIFY=false
PUSH=false
REGISTRY=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --verify) VERIFY=true; shift ;;
        --push)   PUSH=true; REGISTRY="$2"; shift 2 ;;
        *)        echo "Unknown option: $1"; exit 1 ;;
    esac
done

echo "============================================"
echo "  Building secure AICodeGenCrew images"
echo "  Tag: $TAG"
echo "============================================"

# Build backend (context = project root)
echo ""
echo "--- Building backend (bytecode only) ---"
docker build \
    -f ui/backend/Dockerfile.secure \
    -t aicodegencrew-backend:$TAG \
    .

# Build frontend (context = ui/frontend/)
echo ""
echo "--- Building frontend (minified Angular) ---"
docker build \
    -f ui/frontend/Dockerfile \
    -t aicodegencrew-frontend:$TAG \
    ui/frontend/

echo ""
echo "=== Build complete ==="
echo "  aicodegencrew-backend:$TAG"
echo "  aicodegencrew-frontend:$TAG"

# Verification
if $VERIFY; then
    echo ""
    echo "--- Verifying: no .py source in backend image ---"
    PY_COUNT=$(docker run --rm --entrypoint="" aicodegencrew-backend:$TAG \
        find /app -name "*.py" 2>/dev/null | wc -l || echo "0")

    if [ "$PY_COUNT" -gt "0" ]; then
        echo "WARNING: Found $PY_COUNT .py files in backend image!"
        docker run --rm --entrypoint="" aicodegencrew-backend:$TAG \
            find /app -name "*.py" 2>/dev/null
    else
        echo "OK: No .py source files found in backend image"
    fi

    echo ""
    echo "--- Verifying: no TypeScript in frontend image ---"
    TS_COUNT=$(docker run --rm aicodegencrew-frontend:$TAG \
        find /usr/share/nginx/html -name "*.ts" 2>/dev/null | wc -l || echo "0")

    if [ "$TS_COUNT" -gt "0" ]; then
        echo "WARNING: Found $TS_COUNT .ts files in frontend image!"
    else
        echo "OK: No TypeScript source files found in frontend image"
    fi

    echo ""
    echo "--- Image sizes ---"
    docker images aicodegencrew-backend:$TAG --format "Backend:  {{.Size}}"
    docker images aicodegencrew-frontend:$TAG --format "Frontend: {{.Size}}"
fi

# Push to registry
if $PUSH; then
    if [ -z "$REGISTRY" ]; then
        echo "ERROR: --push requires a registry URL"
        exit 1
    fi
    echo ""
    echo "--- Pushing to $REGISTRY ---"
    docker tag aicodegencrew-backend:$TAG $REGISTRY/aicodegencrew-backend:$TAG
    docker tag aicodegencrew-frontend:$TAG $REGISTRY/aicodegencrew-frontend:$TAG
    docker push $REGISTRY/aicodegencrew-backend:$TAG
    docker push $REGISTRY/aicodegencrew-frontend:$TAG
    echo "Pushed successfully!"
fi
