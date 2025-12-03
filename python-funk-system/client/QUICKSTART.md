# 🚀 DFG Funk Client - Quick Start Guide

## Für Benutzer (EXE verwenden)

### 1. Download
Laden Sie `DFG-Funk-Client.exe` herunter.

### 2. Erste Einrichtung
Beim ersten Start wird automatisch nach den Verbindungsdaten gefragt:
- **Server-IP:** srv01.dus.cordes.me
- **Funk-Key:** (Von Administrator erhalten)
- **Kanal:** 41 (Standard)

### 3. Client starten
Doppelklick auf `DFG-Funk-Client.exe`

### 4. Hotkeys
- **F7** - Push-to-Talk
- **F8** - Notruf-Kanal
- **F9/F10** - Schnellwahl

### 5. Einstellungen
Rechtsklick auf Walkie-Talkie → "Einstellungen"

---

## Für Entwickler (Build selbst erstellen)

### 1. Repository klonen
```cmd
git clone <repository-url>
cd python-funk-system/client
```

### 2. EXE bauen
```cmd
build.bat
```

Die EXE befindet sich dann in `dist\DFG-Funk-Client.exe`

### 3. Distribution
Die `DFG-Funk-Client.exe` kann direkt an Benutzer verteilt werden:
- Per E-Mail
- Netzwerk-Share
- Download-Portal

Keine Installation oder Python erforderlich!

---

## Häufige Fragen

### Wo werden Einstellungen gespeichert?
In `settings.json` im gleichen Ordner wie die EXE.

### Kann ich mehrere Profile verwenden?
Ja, kopieren Sie die EXE in verschiedene Ordner. Jeder Ordner hat seine eigene `settings.json`.

### Funktioniert es ohne Internet?
Ja, wenn der Server im lokalen Netzwerk läuft.

### Wie bekomme ich einen Funk-Key?
Kontaktieren Sie Ihren Administrator oder fordern Sie einen im Web-Admin-Interface an.

### Kann ich eigene Hotkeys definieren?
Ja, in den Einstellungen unter "Hotkeys".

---

## Support

Bei Problemen:
1. Überprüfen Sie `settings.json`
2. Stellen Sie sicher, dass der Server läuft
3. Kontaktieren Sie den Administrator
4. Web-Admin: http://srv01.dus.cordes.me:8000/
