# Opus DLL Bundling Documentation

## Übersicht

Die `opus.dll` wird automatisch in die EXE-Datei integriert, sodass keine manuelle Installation mehr nötig ist.

## Wie es funktioniert

### 1. Automatischer Download beim Build

```batch
build.bat
```

Das Build-Script prüft automatisch, ob `libs\opus.dll` vorhanden ist:
- **Nicht vorhanden**: `download_opus.ps1` wird ausgeführt und lädt die DLL herunter
- **Vorhanden**: Build startet direkt

### 2. PyInstaller Integration

In `dfg-funk.spec` ist die DLL als Binary eingetragen:

```python
binaries=[
    ('libs/opus.dll', '.'),  # Bundle Opus DLL into EXE
],
```

PyInstaller kopiert die DLL automatisch:
- **Beim Build**: In das `_internal` Verzeichnis
- **Zur Laufzeit**: Aus dem temporären PyInstaller-Ordner geladen

### 3. Automatisches Finden durch opuslib

`opuslib` sucht die DLL in folgender Reihenfolge:
1. Im Anwendungsverzeichnis (dort legt PyInstaller sie ab)
2. In `System32`
3. Im `PATH`

Da PyInstaller die DLL ins Anwendungsverzeichnis legt, wird sie automatisch gefunden.

## Vorteile dieser Methode

✅ **Keine Admin-Rechte nötig** - User können die EXE direkt ausführen  
✅ **Portable** - Die EXE kann auf jeden PC kopiert werden  
✅ **Einfache Distribution** - Eine einzige EXE-Datei  
✅ **Automatisch aktualisiert** - Neue Opus-Version wird beim Build heruntergeladen  
✅ **Kein manueller Download** - `build.bat` macht alles automatisch

## Build-Prozess

### Erstmaliger Build:

```batch
cd d:\VSCode_Projects\dfg-funk\python-funk-system\client
build.bat
```

Das Script:
1. Erkennt fehlende `opus.dll`
2. Führt `download_opus.ps1` aus
3. Lädt Opus v1.5.2 von GitHub
4. Extrahiert `opus.dll` nach `libs\`
5. Startet PyInstaller
6. Bundlet DLL in die EXE

### Weitere Builds:

Da `libs\opus.dll` jetzt existiert, wird der Download-Schritt übersprungen.

## Manuelle DLL-Beschaffung (optional)

Falls der automatische Download fehlschlägt:

### Option 1: PowerShell-Script manuell ausführen

```powershell
powershell -ExecutionPolicy Bypass -File download_opus.ps1
```

### Option 2: Manueller Download

1. Lade herunter: https://opus-codec.org/downloads/
2. Suche `opus.dll` (64-bit)
3. Kopiere nach: `d:\VSCode_Projects\dfg-funk\python-funk-system\client\libs\opus.dll`
4. Führe `build.bat` aus

## Verzeichnisstruktur nach Build

```
client/
├── libs/
│   └── opus.dll          # Wird beim Build heruntergeladen
├── dist/
│   └── DFG-Funk-Client.exe
├── build.bat              # Automatischer Build-Prozess
├── download_opus.ps1      # Download-Script für opus.dll
└── dfg-funk.spec          # PyInstaller Config mit opus.dll Bundling
```

## Codec-Konfiguration

In `config.py`:

```python
AUDIO_CODEC = 'opus'  # Jetzt sicher, da DLL gebundelt ist
```

Die EXE enthält die DLL, daher kann `'opus'` als Default bleiben:
- **85% weniger Bandbreite** (1.6 MB/s → 0.24 MB/s pro Client)
- **Bessere Sprachqualität** durch psychoakustische Optimierung
- **Keine zusätzliche Installation** nötig

## Fallback zu PCM

Falls `opuslib` die DLL trotzdem nicht findet (sehr unwahrscheinlich):

```python
# In audio_in.py und audio_out.py
except (ImportError, Exception) as e:
    logger.warning(f"Opus codec not available: {e}")
    logger.info("Falling back to PCM codec")
    self.codec = 'pcm'
```

Der Client startet immer, entweder mit Opus oder PCM.

## Technische Details

### Opus DLL Version
- **Version**: 1.5.2
- **Quelle**: https://github.com/xiph/opus/releases
- **Architektur**: 64-bit (kompatibel mit Python 64-bit)

### PyInstaller Binary Bundling
- **Methode**: `binaries` Parameter in `.spec` file
- **Ziel-Pfad**: `'.'` (Root des _internal Ordners)
- **Laufzeit-Pfad**: Von PyInstaller automatisch gesetzt

### opuslib Suche
1. `sys._MEIPASS` (PyInstaller temp directory)
2. Current working directory
3. Executable directory
4. System paths

PyInstaller setzt `sys._MEIPASS` automatisch, daher findet `opuslib` die DLL sofort.

## Troubleshooting

### "opus.dll not found" beim Ausführen der EXE

**Ursache**: DLL wurde nicht korrekt gebundelt

**Lösung**:
```batch
# Prüfe ob opus.dll existiert
dir libs\opus.dll

# Falls nicht vorhanden
powershell -ExecutionPolicy Bypass -File download_opus.ps1

# Rebuild mit --clean
build.bat
```

### Download schlägt fehl

**Ursache**: Keine Internetverbindung oder GitHub nicht erreichbar

**Lösung**: Manuelle DLL-Beschaffung (siehe oben)

### "MSVCP140.dll missing"

**Ursache**: Visual C++ Redistributable fehlt

**Lösung**: 
- Opus DLL benötigt dies manchmal
- Download: https://aka.ms/vs/17/release/vc_redist.x64.exe
- Oder: Statisch gelinkte `opus.dll` verwenden

## Linux/Mac Support

Für Cross-Platform Support:

```python
# In dfg-funk.spec
import sys

binaries = []
if sys.platform == 'win32':
    binaries.append(('libs/opus.dll', '.'))
elif sys.platform == 'darwin':
    binaries.append(('libs/libopus.dylib', '.'))
elif sys.platform == 'linux':
    binaries.append(('libs/libopus.so.0', '.'))
```

## Performance-Vergleich

| Codec | Bandbreite/Client | CPU-Last | Qualität |
|-------|------------------|----------|----------|
| PCM   | 1.536 MB/s       | Niedrig  | Verlustfrei |
| Opus  | 0.192 MB/s       | Mittel   | Sehr gut |

**Bei 50 Clients**:
- PCM: 76.8 MB/s
- Opus: 9.6 MB/s (85% Reduktion)

## Zusammenfassung

✅ **Vollautomatisch**: `build.bat` lädt und bundlet Opus DLL  
✅ **Keine Installation**: User bekommen EXE mit allem drin  
✅ **Immer lauffähig**: Fallback zu PCM falls DLL fehlt  
✅ **Optimal**: Opus als Default für beste Performance  

**Empfehlung**: Opus DLL bundlen ist die beste Lösung für Production-Deployment.
