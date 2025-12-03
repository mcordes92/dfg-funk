# Docker Persistence Fix für Updates

## Problem
Nach einem Redeploy waren hochgeladene Client-Updates verschwunden.

## Ursache
Das `updates/` Verzeichnis war nicht als Docker Volume gemountet, daher wurden die Dateien beim Container-Neustart gelöscht.

## Lösung

### 1. docker-compose.yml
```yaml
volumes:
  - ./data:/app/data
  - ./updates:/app/updates  # ✅ NEU: Persistent updates
```

### 2. portainer-stack.yml
```yaml
volumes:
  - funk-data:/app/data
  - funk-updates:/app/updates  # ✅ NEU: Named volume

volumes:
  funk-data:
    driver: local
  funk-updates:  # ✅ NEU: Volume Definition
    driver: local
```

### 3. Dockerfile
```dockerfile
RUN mkdir -p /app/data /app/updates
VOLUME ["/app/data", "/app/updates"]
```

### 4. .dockerignore
```
updates/  # ✅ NEU: Nicht ins Image kopieren
```

## Deployment

### Bei Docker Compose
```bash
docker-compose down
docker-compose up -d --build
```

### Bei Portainer
1. Stack aktualisieren (neues `portainer-stack.yml`)
2. **Wichtig:** Beim ersten Update nach diesem Fix müssen die Updates neu hochgeladen werden
3. Danach bleiben sie persistent über Redeploys

## Verzeichnisstruktur

```
server/
├── data/              # Volume: Datenbank (bereits persistent)
│   └── funkserver.db
└── updates/           # Volume: Client-Updates (neu persistent)
    ├── version.json
    └── DFG-Funk-Client.exe
```

## Testen

Nach dem Redeploy sollten die Dateien erhalten bleiben:
```bash
# In Container prüfen
docker exec dfg-funk-server ls -lh /app/updates/

# Output sollte sein:
# version.json
# DFG-Funk-Client.exe (falls hochgeladen)
```

## Backup

Die Updates sind jetzt Teil der Docker Volumes und sollten mit gebackupt werden:

```bash
# Volume Backup (Portainer)
docker run --rm -v funk-updates:/data -v $(pwd):/backup \
  alpine tar czf /backup/updates-backup.tar.gz /data

# Volume Restore
docker run --rm -v funk-updates:/data -v $(pwd):/backup \
  alpine tar xzf /backup/updates-backup.tar.gz -C /
```

## Migrationsschritte

1. ✅ Docker-Dateien angepasst
2. 🔄 **Nächster Schritt:** Build & Push neues Image
3. 🔄 **Dann:** Stack in Portainer neu deployen
4. 🔄 **Danach:** Updates neu hochladen (einmalig nötig)
5. ✅ Ab dann: Updates bleiben persistent
