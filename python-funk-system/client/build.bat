@echo off
REM Build Script for DFG Funk Client
REM Creates a standalone Windows EXE

echo ========================================
echo  DFG Funk Client - Build EXE
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python is not installed or not in PATH!
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist venv (
    echo [1/4] Creating virtual environment...
    python -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: Failed to create virtual environment!
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo [2/4] Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo [3/5] Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install dependencies!
    pause
    exit /b 1
)

REM Download Opus DLL if not present
echo.
echo [4/5] Checking Opus DLL...
if not exist "libs\opus.dll" (
    echo Downloading Opus DLL for bundling...
    powershell -ExecutionPolicy Bypass -File download_opus.ps1
    if %ERRORLEVEL% NEQ 0 (
        echo WARNING: Failed to download Opus DLL automatically
        echo The client will fall back to PCM codec
        echo You can manually place opus.dll in libs\ folder and rebuild
        timeout /t 3 >nul
    )
) else (
    echo Opus DLL found - will be bundled into EXE
)

REM Build EXE
echo.
echo [5/5] Building EXE with PyInstaller...
echo This may take a few minutes...
echo.
pyinstaller --clean --noconfirm dfg-funk.spec

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo  SUCCESS!
echo ========================================
echo.
echo EXE created: dist\DFG-Funk-Client.exe
echo.
echo You can now distribute this file to users.
echo No installation or Python required!
echo.
pause
