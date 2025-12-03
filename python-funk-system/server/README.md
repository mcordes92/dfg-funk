# 🎙️ DFG Funk Server

VoIP Funk-System Server mit Web-Admin-Interface und REST API.

## ✨ Features

- 🔊 UDP VoIP Server (Port 5000)
- 🌐 REST API & Web Admin Interface (Port 8000)
- 🔐 Login-geschütztes Admin Dashboard
- 👥 Benutzerverwaltung mit Funk-Keys
- 📡 Kanal-Management (41-43 öffentlich, 51-69 privat)
- 📊 Traffic-Statistiken (24h, 7d, 30d)
- 📝 Verbindungs-Logs
- 🐳 Docker-Ready

## 🚀 Schnellstart

### Option 1: Docker (Empfohlen)

**Windows:**
```cmd
start.bat
```

**Linux/Mac:**
```bash
chmod +x start.sh
./start.sh
```

Dann im Browser öffnen: http://localhost:8000/

### Option 2: Direkt mit Python

```bash
# Abhängigkeiten installieren
pip install -r requirements.txt

# Server starten
python main.py
```

## 🐳 Docker Deployment

### Lokale Entwicklung
```bash
docker-compose up -d
```

### Produktion auf Remote Server
Siehe [DOCKER.md](DOCKER.md) für detaillierte Anweisungen.

### Build & Push zur Registry
```bash
# Windows
build-and-push.bat

# Linux/Mac
./build-and-push.sh
```

## ⚙️ Konfiguration

### Umgebungsvariablen (.env)

```env
# Admin Login
ADMIN_USER=admin
ADMIN_PASS=IhrSicheresPasswort

# Server Ports
API_PORT=8000
UDP_PORT=5000

# Host
HOST=0.0.0.0

# Datenbank
DATABASE_PATH=/app/data/funkserver.db
```

## 📁 Projektstruktur

```
server/
├── api_server.py         # FastAPI REST API
├── udp_server.py         # UDP VoIP Server
├── database.py           # SQLite Datenbank
├── main.py               # Haupt-Einstiegspunkt
├── protocol.py           # Netzwerk-Protokoll
├── config.py             # Konfiguration
├── requirements.txt      # Python Abhängigkeiten
├── Dockerfile            # Docker Image
├── docker-compose.yml    # Docker Compose Config
├── .env.example          # Beispiel-Konfiguration
├── web/                  # Admin Web UI
│   ├── index.html
│   ├── login.html
│   └── admin.js
├── build-and-push.bat    # Windows Build-Script
├── build-and-push.sh     # Linux Build-Script
├── start.bat             # Windows Quick-Start
└── start.sh              # Linux Quick-Start
```

## 🔌 API Endpunkte

### Authentifizierung
- `POST /api/admin/login` - Admin Login
- `POST /api/admin/logout` - Logout
- `GET /api/admin/verify` - Session prüfen

### Benutzerverwaltung
- `GET /api/admin/users` - Alle Benutzer
- `POST /api/admin/users` - Benutzer erstellen
- `GET /api/admin/users/{username}` - Benutzer abrufen
- `PUT /api/admin/users/{username}` - Benutzer aktualisieren
- `DELETE /api/admin/users/{username}` - Benutzer löschen

### Statistiken
- `GET /api/stats/active-users` - Aktive Benutzer
- `GET /api/stats/traffic` - Traffic-Statistiken
- `GET /api/stats/channel-usage` - Kanal-Nutzung

### Logs
- `GET /api/logs/connections` - Verbindungs-Logs

### Kanäle
- `GET /api/channels/list` - Alle Kanäle
- `GET /api/channels/{funk_key}` - Erlaubte Kanäle für Funk-Key

API-Dokumentation: http://localhost:8000/docs

## 👥 Benutzerverwaltung

### Standard Admin-Login
```
Benutzername: admin
Passwort: admin123
```

⚠️ **Ändern Sie diese Credentials in der `.env` Datei!**

### Neuen Benutzer erstellen

1. Im Admin-Dashboard anmelden
2. Zu "Benutzer" Tab wechseln
3. "Neuer Benutzer" klicken
4. Daten eingeben:
   - Benutzername
   - Funk-Key (mind. 8 Zeichen)
   - Erlaubte Kanäle auswählen
5. Speichern

## 📡 Kanäle

### Öffentliche Kanäle (41-43)
- Für alle Benutzer verfügbar
- Keine spezielle Berechtigung nötig

### Private Kanäle (51-69)
- Müssen explizit pro Benutzer freigegeben werden
- Über Admin-Dashboard konfigurierbar

## 📊 Monitoring

### Container Status
```bash
docker-compose ps
```

### Logs ansehen
```bash
docker-compose logs -f
```

### Healthcheck
```bash
docker inspect --format='{{json .State.Health}}' dfg-funk-server
```

## 🔒 Sicherheit

### Produktion Checkliste
- [ ] Admin-Passwort in `.env` ändern
- [ ] Firewall-Regeln konfigurieren
- [ ] HTTPS Reverse Proxy einrichten (nginx/traefik)
- [ ] Regelmäßige Backups der `data/` Ordner
- [ ] Log-Rotation konfigurieren
- [ ] Rate-Limiting aktivieren

### Ports
- **5000/udp** - VoIP Server (nur für Clients)
- **8000/tcp** - Admin API (mit Firewall schützen!)

## 🐛 Troubleshooting

### Container startet nicht
```bash
docker-compose logs
```

### Datenbank-Fehler
```bash
# Backup erstellen
cp data/funkserver.db data/funkserver.db.backup

# Datenbank neu initialisieren
rm data/funkserver.db
docker-compose restart
```

### Port bereits belegt
```bash
# Prüfen welcher Prozess den Port nutzt
netstat -ano | findstr :8000
netstat -ano | findstr :5000
```

## 📦 Updates

```bash
# Neuestes Image pullen
docker-compose pull

# Container neu starten
docker-compose down
docker-compose up -d
```

## 📝 Lizenz

Proprietär - DFG

## 🤝 Support

Bei Fragen oder Problemen bitte ein Issue erstellen.
