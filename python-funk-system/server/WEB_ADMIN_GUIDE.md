# Funk System - Web Admin Interface

## Zugriff

Nach dem Start des Servers ist das Web Admin Interface verfügbar unter:

**URL:** http://localhost:8000

## Features

### 📊 Dashboard
- Live-Übersicht aktiver Benutzer
- Statistik-Karten (Aktive User, Gesamt-User, Kanäle, Verbindungen)
- Echtzeit-Anzeige der verbundenen Benutzer mit Kanal-Informationen

### 👥 Benutzer-Verwaltung
- **Neuen Benutzer anlegen**
  - Benutzername (min. 3 Zeichen)
  - Funk-Schlüssel (min. 8 Zeichen oder automatisch generieren)
  - Kanal-Berechtigungen (Auswahl aus Kanälen 41-72)
  - Status (Aktiv/Inaktiv)
  
- **Benutzer bearbeiten**
  - Kanal-Berechtigungen ändern
  - Status aktivieren/deaktivieren
  
- **Benutzer löschen**
  - Mit Sicherheitsabfrage

### 📡 Kanal-Übersicht
- Liste aller Kanäle (41-72)
- Aktive Nutzer pro Kanal
- Verbindungsstatistiken (24h)

### 📋 Verbindungs-Logs
- Zeitstempel aller Verbindungen
- Benutzer- und Kanal-Informationen
- IP-Adressen
- Aktionen (connect/disconnect)

### 📈 Verkehrsstatistiken
- Übertragene Pakete pro Benutzer
- Bytes gesendet
- Kanal-spezifische Statistiken

## Bedienung

### Einen neuen Benutzer anlegen

1. Wechsel zum Tab **"Benutzer"**
2. Klick auf **"➕ Neuer Benutzer"**
3. Eingabe der Daten:
   - Benutzername eingeben
   - Funk-Schlüssel eingeben oder mit **"🎲 Zufälligen Schlüssel generieren"** erzeugen
   - Gewünschte Kanäle auswählen (mehrere möglich)
   - Status auf "Aktiv" setzen
4. Klick auf **"Speichern"**

**Der Funk-Schlüssel wird angezeigt und muss dem Benutzer mitgeteilt werden!**

### Benutzer-Berechtigungen ändern

1. Wechsel zum Tab **"Benutzer"**
2. Klick auf **"✏️ Bearbeiten"** beim gewünschten Benutzer
3. Kanal-Auswahl anpassen
4. Bei Bedarf Status ändern
5. Klick auf **"Speichern"**

### Live-Monitoring

- Das Dashboard aktualisiert sich automatisch alle 10 Sekunden
- Zeigt alle aktuell verbundenen Benutzer mit ihren aktiven Kanälen
- Status-Badge oben rechts zeigt Server-Status (grün = online)

## Technische Details

- **Frontend:** Reines HTML/CSS/JavaScript (keine Dependencies)
- **Backend:** FastAPI REST API
- **Datenbank:** SQLite
- **Auto-Refresh:** Dashboard alle 10 Sekunden
- **Responsive Design:** Funktioniert auf Desktop und Tablet

## Browser-Kompatibilität

- Chrome/Edge (empfohlen)
- Firefox
- Safari
- Opera

## Sicherheitshinweis

⚠️ **Wichtig:** Das Admin-Interface hat derzeit keine Authentifizierung! 

Für Produktionsumgebungen sollte:
- Eine Admin-Authentifizierung hinzugefügt werden
- HTTPS verwendet werden
- CORS-Origins eingeschränkt werden
