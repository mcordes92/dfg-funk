@echo off
REM Quick Start Script for DFG Funk Server

echo ========================================
echo  DFG Funk Server - Quick Start
echo ========================================
echo.

REM Check if .env exists
if not exist .env (
    echo [!] .env file not found. Creating from template...
    copy .env.example .env
    echo [!] Please edit .env file and set your admin credentials!
    echo.
    pause
    exit /b 1
)

REM Create data directory
if not exist data mkdir data

echo [1/2] Starting Docker containers...
docker-compose up -d

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to start containers!
    exit /b 1
)

echo.
echo [2/2] Checking container status...
timeout /t 3 >nul
docker-compose ps

echo.
echo ========================================
echo  SUCCESS!
echo ========================================
echo.
echo Server is running!
echo.
echo Admin Web UI:  http://localhost:8000/
echo API Docs:      http://localhost:8000/docs
echo.
echo View logs:     docker-compose logs -f
echo Stop server:   docker-compose down
echo.
