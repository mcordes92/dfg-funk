# 🎙️ DFG Funk Client

Windows Desktop-Client für das DFG Funk System.

## ✨ Features

- 🎤 Push-to-Talk VoIP
- 🖼️ Walkie-Talkie UI Design
- ⌨️ Konfigurierbare Hotkeys
- 🔊 Noise Gate Filter
- 📡 Kanal-Schnellwahl
- 🔐 Funk-Key Authentifizierung
- 🎚️ Audio-Geräte Auswahl

## 🚀 EXE erstellen (für Distribution)

### Windows
```cmd
build.bat
```

Die fertige EXE befindet sich dann in: `dist\DFG-Funk-Client.exe`

### Linux/Mac
```bash
chmod +x build.sh
./build.sh
```

## 📦 Distribution

Die generierte `DFG-Funk-Client.exe` ist komplett standalone:
- ✅ Keine Python-Installation nötig
- ✅ Keine zusätzlichen Dependencies
- ✅ Einfach kopieren und starten
- ✅ Funktioniert auf jedem Windows-PC

## 🔧 Entwicklung (ohne EXE)

### Dependencies installieren
```cmd
pip install -r requirements.txt
```

### Client starten
```cmd
python main.py
```

## ⚙️ Erste Einrichtung

Beim ersten Start wird automatisch eine `settings.json` erstellt.

### Minimale Konfiguration:
```json
{
    "server_ip": "srv01.dus.cordes.me",
    "server_port": 5000,
    "api_port": 8000,
    "funk_key": "IhrFunkKey",
    "channel": 41
}
```

### Vollständige Konfiguration:
```json
{
    "server_ip": "srv01.dus.cordes.me",
    "server_port": 5000,
    "api_port": 8000,
    "funk_key": "IhrFunkKey",
    "channel": 41,
    "hotkey_primary": "f7",
    "hotkey_secondary": "f8",
    "hotkey_channel1": "f9",
    "hotkey_channel2": "f10",
    "channel1_target": 51,
    "channel2_target": 43,
    "mic_device": 0,
    "speaker_device": 0,
    "noise_gate_enabled": false,
    "noise_gate_threshold": -40
}
```

## 🎮 Bedienung

### Standard-Hotkeys
- **F7** - Push-to-Talk (Primär-Kanal)
- **F8** - Push-to-Talk (Notruf-Kanal 41)
- **F9** - Schnellwahl Kanal 1
- **F10** - Schnellwahl Kanal 2

### Einstellungen
Rechtsklick auf das Walkie-Talkie → "Einstellungen"

Tabs:
- **🎧 Audio** - Mikrofon, Lautsprecher, Noise Gate
- **⌨️ Hotkeys** - Tastenbelegung, Schnellwahl
- **🌐 Netzwerk** - Server, Ports, Funk-Key

## 📡 Kanäle

### Öffentliche Kanäle (41-43)
- Für alle Benutzer zugänglich
- Keine Berechtigung erforderlich

### Private Kanäle (51-69)
- Müssen vom Administrator freigegeben werden
- Zugriff über Web-Admin-Interface

## 🔊 Noise Gate

Der Noise Gate filtert Hintergrundgeräusche:
1. In Einstellungen aktivieren
2. Schwellwert anpassen (-60 bis -20 dB)
3. Mit "Mikrofon testen" optimieren

**Empfehlung:** -40 dB für normale Umgebungen

## 🐛 Troubleshooting

### Client verbindet nicht
- Server-IP in `settings.json` prüfen
- Firewall-Einstellungen (UDP Port 5000)
- Funk-Key korrekt?

### Kein Audio
- Richtige Audio-Geräte ausgewählt?
- Mikrofon-Berechtigung in Windows
- Lautstärke-Einstellungen prüfen

### Hotkeys funktionieren nicht
- Programm muss im Vordergrund sein
- Admin-Rechte für globale Hotkeys
- Taste nicht von anderem Programm belegt?

## 📋 Systemanforderungen

- **OS:** Windows 10/11 (64-bit)
- **RAM:** 100 MB
- **Disk:** 150 MB
- **Audio:** Mikrofon + Lautsprecher

## 🏗️ Build-Prozess Details

Der Build-Prozess verwendet PyInstaller um eine standalone EXE zu erstellen:

1. Erstellt Virtual Environment
2. Installiert alle Dependencies
3. Bundled Python-Runtime
4. Komprimiert mit UPX
5. Erstellt One-File EXE

**Build-Zeit:** ~3-5 Minuten  
**EXE-Größe:** ~80-100 MB

## 📁 Projektstruktur

```
client/
├── main.py              # Haupt-Einstiegspunkt
├── gui.py               # PySide6 GUI
├── audio_in.py          # Audio Input + Noise Gate
├── audio_out.py         # Audio Output
├── network.py           # UDP Network Client
├── hotkeys.py           # Keyboard Hotkeys
├── protocol.py          # Network Protocol
├── config.py            # Configuration
├── settings.py          # Settings Manager
├── walkie.png           # UI Background
├── settings.json        # User Settings (auto-generated)
├── requirements.txt     # Python Dependencies
├── dfg-funk.spec        # PyInstaller Config
├── version_info.txt     # EXE Version Info
├── build.bat            # Windows Build Script
└── build.sh             # Linux Build Script
```

## 🔒 Sicherheit

Der Funk-Key wird lokal in `settings.json` gespeichert.

**Wichtig:**
- Funk-Key nicht teilen
- Bei Verlust: Administrator kontaktieren
- Neuen Key im Web-Admin generieren lassen

## 📝 Lizenz

Proprietär - DFG

## 🤝 Support

Bei Problemen den Administrator kontaktieren oder im Web-Admin-Interface ein Ticket erstellen.
