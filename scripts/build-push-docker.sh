#!/usr/bin/env bash
# Build and push Docker image to ghcr.io (GitHub Container Registry).
# Usage: ./scripts/build-push-docker.sh [build|push|build-push]
# Env: REGISTRY (default ghcr.io), IMAGE_NAME (default from git remote), DOCKER_TAG (default latest)

set -e

REGISTRY="${REGISTRY:-ghcr.io}"
ACTION="${1:-build-push}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# Infer IMAGE_NAME from git remote (e.g. github.com:owner/repo -> owner/repo)
if [ -z "$IMAGE_NAME" ] && command -v git >/dev/null 2>&1; then
  REMOTE="$(git remote get-url origin 2>/dev/null || true)"
  if [[ "$REMOTE" =~ github\.com[:/]([^/]+/[^/.]+) ]]; then
    IMAGE_NAME="${BASH_REMATCH[1]}"
  fi
fi
IMAGE_NAME="${IMAGE_NAME:-agentwork-simulator}"
DOCKER_TAG="${DOCKER_TAG:-latest}"
FULL_IMAGE="${REGISTRY}/${IMAGE_NAME}:${DOCKER_TAG}"

echo "→ Registry: $REGISTRY"
echo "→ Image:    $FULL_IMAGE"
echo ""

case "$ACTION" in
  build)
    echo "Building $FULL_IMAGE ..."
    docker build -t "$FULL_IMAGE" .
    echo "✅ Built $FULL_IMAGE"
    ;;
  push)
    echo "Pushing $FULL_IMAGE ..."
    docker push "$FULL_IMAGE"
    echo "✅ Pushed $FULL_IMAGE"
    ;;
  build-push)
    echo "Building $FULL_IMAGE ..."
    docker build -t "$FULL_IMAGE" .
    echo "Pushing $FULL_IMAGE ..."
    docker push "$FULL_IMAGE"
    echo "✅ Built and pushed $FULL_IMAGE"
    ;;
  *)
    echo "Usage: $0 [build|push|build-push]"
    echo ""
    echo "  build       - build image only"
    echo "  push        - push existing image only"
    echo "  build-push  - build then push (default)"
    echo ""
    echo "Optional env: REGISTRY, IMAGE_NAME, DOCKER_TAG"
    echo "  e.g. DOCKER_TAG=main $0 build-push"
    exit 1
    ;;
esac
