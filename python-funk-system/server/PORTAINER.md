# 🐙 Portainer Stack Deployment

## Deployment in Portainer

### 1. Stack erstellen
1. Portainer öffnen
2. Zu "Stacks" navigieren
3. "Add stack" klicken
4. Stack-Name: `dfg-funk-server`

### 2. Compose-Datei hochladen
**Option A: Web Editor**
- "Web editor" auswählen
- Inhalt von `portainer-stack.yml` einfügen

**Option B: Repository**
- "Repository" auswählen
- Repository URL eingeben
- Compose-Pfad: `python-funk-system/server/portainer-stack.yml`

### 3. Environment Variables
Unter "Environment variables" → "Advanced mode" aktivieren und einfügen:

```env
ADMIN_USER=admin
ADMIN_PASS=IhrSicheresPasswort
UDP_PORT=5000
API_PORT=8000
```

Oder die `stack.env` Datei hochladen.

### 4. Deploy
- "Deploy the stack" klicken
- Warten bis Status "running" ist

### 5. Zugriff
Nach erfolgreichem Deployment:
- Admin UI: `http://SERVER-IP:8000/`
- Login mit den in stack.env definierten Credentials

## Environment Variables

### Pflichtfelder
| Variable | Beschreibung | Standard |
|----------|--------------|----------|
| `ADMIN_USER` | Admin Benutzername | `admin` |
| `ADMIN_PASS` | Admin Passwort | `change_me_in_production` |

### Optional
| Variable | Beschreibung | Standard |
|----------|--------------|----------|
| `UDP_PORT` | VoIP Server Port | `5000` |
| `API_PORT` | API/Web UI Port | `8000` |

## Stack Management

### Update Stack
1. Neues Image builden und pushen
2. In Portainer Stack öffnen
3. "Update the stack" klicken
4. "Re-pull image and redeploy" aktivieren
5. "Update" klicken

### Stack Logs ansehen
1. Stack öffnen
2. Container auswählen
3. "Logs" Tab

### Stack neu starten
1. Stack öffnen
2. "Stop" → "Start"

## Volumes

### Datenbank-Persistierung
- Volume Name: `funk-data`
- Pfad im Container: `/app/data`
- Enthält: SQLite Datenbank

### Volume Backup
```bash
# Volume Location in Portainer finden
docker volume inspect dfg-funk-server_funk-data

# Backup erstellen
docker run --rm -v dfg-funk-server_funk-data:/data -v $(pwd):/backup \
  alpine tar czf /backup/funk-data-backup.tar.gz -C /data .

# Restore
docker run --rm -v dfg-funk-server_funk-data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/funk-data-backup.tar.gz -C /data
```

## Netzwerk

### Ports freigeben
Stellen Sie sicher, dass folgende Ports in der Firewall geöffnet sind:
- `5000/udp` - VoIP Server (für Clients)
- `8000/tcp` - Admin Web UI (nur für Admin-Zugriff)

### Reverse Proxy
Für HTTPS-Zugriff empfohlen:
```nginx
server {
    listen 443 ssl http2;
    server_name funk.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Troubleshooting

### Stack startet nicht
- Logs in Portainer prüfen
- Environment Variables überprüfen
- Ports verfügbar? `netstat -tuln | grep -E '8000|5000'`

### Image Pull Error
```bash
# Registry Login prüfen
docker login cr-hes-cordes.cr.de-fra.ionos.com

# Manuell pullen
docker pull cr-hes-cordes.cr.de-fra.ionos.com/dfg-funk-server:latest
```

### Container unhealthy
- Health-Check-Logs in Portainer ansehen
- Container neu starten
- Ports korrekt gemappt?

## Sicherheit

### Produktions-Checkliste
- [ ] `ADMIN_PASS` mit starkem Passwort setzen
- [ ] Port 8000 nur für Admin-IPs freigeben
- [ ] HTTPS Reverse Proxy einrichten
- [ ] Regelmäßige Volume-Backups
- [ ] Stack-Updates regelmäßig durchführen
- [ ] Logs monitoren

## Multi-Host Deployment

### Mit Docker Swarm
```yaml
version: '3.8'

services:
  funk-server:
    image: cr-hes-cordes.cr.de-fra.ionos.com/dfg-funk-server:latest
    deploy:
      replicas: 1
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      placement:
        constraints:
          - node.role == manager
    ports:
      - "5000:5000/udp"
      - "8000:8000"
    environment:
      - ADMIN_USER=${ADMIN_USER}
      - ADMIN_PASS=${ADMIN_PASS}
    volumes:
      - funk-data:/app/data
    networks:
      - funk-network

volumes:
  funk-data:

networks:
  funk-network:
    driver: overlay
```
