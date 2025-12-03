@echo off
REM DFG Funk Client - Erste Einrichtung

echo ========================================
echo  DFG Funk Client - Erste Einrichtung
echo ========================================
echo.

REM Check if settings.json exists
if exist settings.json (
    echo [!] settings.json existiert bereits.
    echo.
    choice /C JN /M "Moechten Sie die Einstellungen zuruecksetzen?"
    if errorlevel 2 goto :END
    echo.
)

echo Bitte geben Sie Ihre Verbindungsdaten ein:
echo.

REM Get Server IP
set /p SERVER_IP="Server-IP [srv01.dus.cordes.me]: "
if "%SERVER_IP%"=="" set SERVER_IP=srv01.dus.cordes.me

REM Get Funk-Key
set /p FUNK_KEY="Ihr Funk-Key: "
if "%FUNK_KEY%"=="" (
    echo ERROR: Funk-Key wird benoetigt!
    pause
    exit /b 1
)

REM Get Channel
set /p CHANNEL="Start-Kanal [41]: "
if "%CHANNEL%"=="" set CHANNEL=41

echo.
echo Erstelle settings.json...
(
echo {
echo     "server_ip": "%SERVER_IP%",
echo     "server_port": 5000,
echo     "api_port": 8000,
echo     "funk_key": "%FUNK_KEY%",
echo     "channel": %CHANNEL%,
echo     "hotkey_primary": "f7",
echo     "hotkey_secondary": "f8",
echo     "hotkey_channel1": "f9",
echo     "hotkey_channel2": "f10",
echo     "channel1_target": 51,
echo     "channel2_target": 43,
echo     "mic_device": 0,
echo     "speaker_device": 0,
echo     "noise_gate_enabled": false,
echo     "noise_gate_threshold": -40
echo }
) > settings.json

echo.
echo ========================================
echo  Einrichtung abgeschlossen!
echo ========================================
echo.
echo Die Konfiguration wurde gespeichert.
echo Sie koennen jetzt den Client starten.
echo.
echo Weitere Einstellungen koennen Sie im Client
echo ueber das Kontextmenue aendern.
echo.

:END
pause
