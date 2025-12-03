#!/bin/bash
# Build Script for DFG Funk Client
# Creates a standalone Windows EXE

echo "========================================"
echo " DFG Funk Client - Build EXE"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python is not installed!"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "[1/4] Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create virtual environment!"
        exit 1
    fi
fi

# Activate virtual environment
echo "[2/4] Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "[3/4] Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install dependencies!"
    exit 1
fi

# Build EXE
echo ""
echo "[4/4] Building EXE with PyInstaller..."
echo "This may take a few minutes..."
echo ""
pyinstaller --clean --noconfirm dfg-funk.spec

if [ $? -ne 0 ]; then
    echo "ERROR: Build failed!"
    exit 1
fi

echo ""
echo "========================================"
echo " SUCCESS!"
echo "========================================"
echo ""
echo "EXE created: dist/DFG-Funk-Client.exe"
echo ""
echo "You can now distribute this file to users."
echo "No installation or Python required!"
echo ""
