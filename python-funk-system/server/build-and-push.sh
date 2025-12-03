#!/bin/bash
# Build and Push Script for DFG Funk Server
# Docker Registry: cr-hes-cordes.cr.de-fra.ionos.com

REGISTRY="cr-hes-cordes.cr.de-fra.ionos.com"
IMAGE_NAME="dfg-funk-server"
VERSION="latest"

echo "========================================"
echo " Building DFG Funk Server Docker Image"
echo "========================================"
echo ""

# Build the Docker image
echo "[1/3] Building Docker image..."
docker build -t ${IMAGE_NAME}:${VERSION} .
if [ $? -ne 0 ]; then
    echo "ERROR: Docker build failed!"
    exit 1
fi

echo ""
echo "[2/3] Tagging image for registry..."
docker tag ${IMAGE_NAME}:${VERSION} ${REGISTRY}/${IMAGE_NAME}:${VERSION}
if [ $? -ne 0 ]; then
    echo "ERROR: Docker tag failed!"
    exit 1
fi

echo ""
echo "[3/3] Pushing to registry ${REGISTRY}..."
docker push ${REGISTRY}/${IMAGE_NAME}:${VERSION}
if [ $? -ne 0 ]; then
    echo "ERROR: Docker push failed!"
    echo ""
    echo "Make sure you are logged in:"
    echo "  docker login ${REGISTRY}"
    exit 1
fi

echo ""
echo "========================================"
echo " SUCCESS!"
echo "========================================"
echo "Image pushed to: ${REGISTRY}/${IMAGE_NAME}:${VERSION}"
echo ""
echo "To pull and run on another machine:"
echo "  docker pull ${REGISTRY}/${IMAGE_NAME}:${VERSION}"
echo "  docker run -d -p 5000:5000/udp -p 8000:8000 ${REGISTRY}/${IMAGE_NAME}:${VERSION}"
echo ""
