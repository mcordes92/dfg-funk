@echo off
echo ========================================
echo Opus Library Installation for Windows
echo ========================================
echo.

REM Download Opus DLL
echo [1/3] Downloading Opus DLL...
powershell -Command "& {Invoke-WebRequest -Uri 'https://github.com/xiph/opus/releases/download/v1.5.2/opus-tools-0.2-opus-1.5.2.zip' -OutFile 'opus.zip'}"

if errorlevel 1 (
    echo ERROR: Download failed!
    pause
    exit /b 1
)

echo [2/3] Extracting Opus DLL...
powershell -Command "& {Expand-Archive -Path 'opus.zip' -DestinationPath '.' -Force}"

REM Copy DLL to System32 (requires admin)
echo [3/3] Installing Opus DLL...
echo.
echo NOTE: This requires Administrator privileges!
echo Right-click this file and select "Run as administrator"
echo.

REM Try to find opus.dll in extracted files
for /r %%i in (opus.dll) do (
    if exist "%%i" (
        echo Found: %%i
        copy "%%i" "%WINDIR%\System32\" >nul 2>&1
        if errorlevel 1 (
            echo.
            echo ERROR: Could not copy to System32 - need admin rights!
            echo.
            echo Manual steps:
            echo 1. Find opus.dll in current directory
            echo 2. Copy to C:\Windows\System32\
            echo 3. Or add current directory to PATH
            pause
            exit /b 1
        ) else (
            echo SUCCESS: Opus DLL installed!
        )
    )
)

REM Cleanup
del opus.zip

echo.
echo ========================================
echo Installation complete!
echo ========================================
echo.
echo You can now run: python main.py
pause
