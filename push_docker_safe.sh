#!/bin/bash
set -e

IMAGE_NAME="arnab2001/optischema-slim"
TAG="latest"

echo "🔨 Building frontend locally first (to avoid esbuild crash)..."
cd frontend
npm install
npm run build
cd ..

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
# Using a temporary Dockerfile that copies the pre-built frontend
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    --tag ${IMAGE_NAME}:${TAG} \
    --push \
    -f Dockerfile.prebuilt \
    .

echo "✅ Successfully pushed ${IMAGE_NAME}:${TAG}"
