#!/usr/bin/env bash
# =============================================================================
# Build and push Docker images to GitLab Container Registry
#
# Usage:
#   ./scripts/push-docker-images.sh              # build + push :latest
#   ./scripts/push-docker-images.sh 0.7.2        # build + push :0.7.2 + :latest
#
# Prerequisites:
#   docker login bnotkca.pl.s2-eu.capgemini.com:5050
# =============================================================================
set -e

REGISTRY="bnotkca.pl.s2-eu.capgemini.com:5050/ai-group/aicodegencrew"
VERSION="${1:-latest}"

echo ""
echo "========================================="
echo "  Building SDLC Pilot Docker Images"
echo "  Registry: $REGISTRY"
echo "  Version:  $VERSION"
echo "========================================="
echo ""

# Build backend
echo "[1/4] Building backend..."
docker build -t "$REGISTRY/backend:$VERSION" -f ui/backend/Dockerfile.dev .

# Build frontend
echo "[2/4] Building frontend..."
docker build -t "$REGISTRY/frontend:$VERSION" -f ui/frontend/Dockerfile .

# Tag as latest (if versioned)
if [ "$VERSION" != "latest" ]; then
    docker tag "$REGISTRY/backend:$VERSION" "$REGISTRY/backend:latest"
    docker tag "$REGISTRY/frontend:$VERSION" "$REGISTRY/frontend:latest"
fi

# Push
echo "[3/4] Pushing backend..."
docker push "$REGISTRY/backend:$VERSION"
[ "$VERSION" != "latest" ] && docker push "$REGISTRY/backend:latest"

echo "[4/4] Pushing frontend..."
docker push "$REGISTRY/frontend:$VERSION"
[ "$VERSION" != "latest" ] && docker push "$REGISTRY/frontend:latest"

echo ""
echo "========================================="
echo "  Done! Images pushed:"
echo "    $REGISTRY/backend:$VERSION"
echo "    $REGISTRY/frontend:$VERSION"
echo "========================================="
echo ""
