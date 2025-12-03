#!/bin/bash
# Quick Start Script for DFG Funk Server

echo "========================================"
echo " DFG Funk Server - Quick Start"
echo "========================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "[!] .env file not found. Creating from template..."
    cp .env.example .env
    echo "[!] Please edit .env file and set your admin credentials!"
    echo ""
    exit 1
fi

# Create data directory
mkdir -p data

echo "[1/2] Starting Docker containers..."
docker-compose up -d

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to start containers!"
    exit 1
fi

echo ""
echo "[2/2] Checking container status..."
sleep 3
docker-compose ps

echo ""
echo "========================================"
echo " SUCCESS!"
echo "========================================"
echo ""
echo "Server is running!"
echo ""
echo "Admin Web UI:  http://localhost:8000/"
echo "API Docs:      http://localhost:8000/docs"
echo ""
echo "View logs:     docker-compose logs -f"
echo "Stop server:   docker-compose down"
echo ""
