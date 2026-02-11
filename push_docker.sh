#!/bin/bash
set -e

IMAGE_NAME="arnab2001/optischema-slim"
TAG="latest"

echo "🐳 Building and Pushing ${IMAGE_NAME}:${TAG}..."

# check if buildx is installed
if ! docker buildx version > /dev/null 2>&1; then
    echo "❌ Docker Buildx not found. Please enable it in Docker Desktop."
    exit 1
fi

# Create builder if not exists
if ! docker buildx inspect optischema-builder > /dev/null 2>&1; then
    docker buildx create --name optischema-builder --use
fi

# Build and Push (Multi-arch)
# Note: You must be logged in to Docker Hub via `docker login`
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    --tag ${IMAGE_NAME}:${TAG} \
    --push \
    .

echo "✅ Successfully pushed ${IMAGE_NAME}:${TAG}"
