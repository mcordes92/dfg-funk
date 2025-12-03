# Updates Directory

Dieses Verzeichnis enthält Client-Updates für das automatische Update-System.

## Struktur

```
updates/
├── version.json          # Aktuelle Version-Info
├── DFG-Funk-Client.exe   # Aktuelle Client-EXE
└── README.md             # Diese Datei
```

## version.json Format

```json
{
  "version": "1.8.0",
  "release_date": "2025-12-03",
  "changelog": "Änderungen in dieser Version...",
  "download_url": "http://srv01.dus.cordesm.de:8001/api/updates/download",
  "mandatory": false,
  "min_required_version": "1.7.0"
}
```

## Neues Update bereitstellen

1. Neue EXE hier ablegen: `DFG-Funk-Client.exe`
2. `version.json` aktualisieren mit neuer Versionsnummer und Changelog
3. Server neu starten (damit API die neue Version lädt)

## API Endpoints

- `GET /api/version` - Gibt `version.json` zurück (öffentlich)
- `GET /api/updates/download` - Download der EXE (öffentlich)
- `POST /api/admin/updates` - Upload neuer Version (Auth erforderlich)

## Client-Verhalten

Der Client prüft beim Start auf Updates und zeigt eine Benachrichtigung wenn:
- Eine neuere Version verfügbar ist
- Die Version zwingend erforderlich ist (`mandatory: true`)

Der User kann dann entscheiden:
- "Jetzt aktualisieren" → Öffnet Download-URL
- "Später" → Update überspringen (außer mandatory)
