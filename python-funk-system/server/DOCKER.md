# DFG Funk Server - Docker Deployment

## 🐳 Docker Build & Deploy

### Voraussetzungen
- Docker installiert
- Zugriff auf die Docker Registry: `cr-hes-cordes.cr.de-fra.ionos.com`

### Registry Login
```bash
docker login cr-hes-cordes.cr.de-fra.ionos.com
```

### Build & Push
**Windows:**
```cmd
build-and-push.bat
```

**Linux/Mac:**
```bash
chmod +x build-and-push.sh
./build-and-push.sh
```

### Manueller Build
```bash
# Build
docker build -t dfg-funk-server:latest .

# Tag
docker tag dfg-funk-server:latest cr-hes-cordes.cr.de-fra.ionos.com/dfg-funk-server:latest

# Push
docker push cr-hes-cordes.cr.de-fra.ionos.com/dfg-funk-server:latest
```

## 🚀 Deployment

### Mit Docker Compose (Empfohlen)
```bash
# Starten
docker-compose up -d

# Logs anzeigen
docker-compose logs -f

# Stoppen
docker-compose down
```

### Direkt mit Docker
```bash
docker run -d \
  --name dfg-funk-server \
  -p 5000:5000/udp \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/.env:/app/.env \
  --restart unless-stopped \
  cr-hes-cordes.cr.de-fra.ionos.com/dfg-funk-server:latest
```

### Auf Remote Server deployen
```bash
# Pull auf Server
docker pull cr-hes-cordes.cr.de-fra.ionos.com/dfg-funk-server:latest

# Starten
docker run -d \
  --name dfg-funk-server \
  -p 5000:5000/udp \
  -p 8000:8000 \
  -v /opt/dfg-funk/data:/app/data \
  --env-file /opt/dfg-funk/.env \
  --restart unless-stopped \
  cr-hes-cordes.cr.de-fra.ionos.com/dfg-funk-server:latest
```

## ⚙️ Konfiguration

### .env Datei erstellen
```bash
cp .env.example .env
```

Dann `.env` anpassen:
```env
ADMIN_USER=admin
ADMIN_PASS=IhrSicheresPasswort
HOST=0.0.0.0
API_PORT=8000
UDP_PORT=5000
```

### Ports
- **5000/udp** - UDP VoIP Server (Clients verbinden sich hierüber)
- **8000/tcp** - HTTP API & Admin Web UI

## 📊 Volumes

### Datenbank-Persistierung
Die Datenbank wird in `/app/data` gespeichert und sollte als Volume gemountet werden:
```bash
-v ./data:/app/data
```

## 🔍 Container Management

### Status prüfen
```bash
docker ps
docker logs dfg-funk-server
```

### Container neu starten
```bash
docker restart dfg-funk-server
```

### Container stoppen
```bash
docker stop dfg-funk-server
docker rm dfg-funk-server
```

### In Container einsteigen
```bash
docker exec -it dfg-funk-server /bin/bash
```

## 🌐 Zugriff

Nach dem Start ist das Admin-Interface erreichbar unter:
- http://SERVER-IP:8000/
- Login-Daten aus `.env` Datei

## 🔒 Sicherheit

**Wichtig für Produktion:**
1. `.env` Datei mit sicheren Passwörtern erstellen
2. Ports nur für notwendige IPs freigeben (Firewall)
3. HTTPS Reverse Proxy (nginx/traefik) vorschalten
4. Regelmäßige Backups der `data/` Ordner

## 📦 Update

```bash
# Neues Image pullen
docker pull cr-hes-cordes.cr.de-fra.ionos.com/dfg-funk-server:latest

# Container neu starten mit neuem Image
docker-compose down
docker-compose up -d
```
