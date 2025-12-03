# Sound System - Setup Anleitung

## Änderungen

Das DFG-Funk System nutzt jetzt **pygame** für Sound-Wiedergabe mit echter Lautstärke-Kontrolle!

## Was wurde geändert:

1. **Neue Abhängigkeit**: `pygame>=2.5.0` in `requirements.txt`
2. **Neues Modul**: `sound_manager.py` - Verwaltet Sound-Wiedergabe
3. **Sound-Datei**: `system.mp3` im Client-Ordner (MUSS vorhanden sein!)
4. **GUI-Updates**: 
   - Lautstärke-Slider (0-100%, Standard: 50%)
   - "Ton testen" Button mit Lautstärke-Preview
   - Sounds aktivieren/deaktivieren Checkbox

## Installation:

```cmd
# 1. Pygame installieren
pip install pygame

# 2. system.mp3 in den client Ordner legen
# Stelle sicher dass die Datei existiert:
# d:\VSCode_Projects\dfg-funk\python-funk-system\client\system.mp3
```

## Wie es funktioniert:

- **Ein Sound für alles**: `system.mp3` wird für Button-Clicks UND Kanalwechsel verwendet
- **Echte Lautstärke**: pygame.mixer erlaubt präzise Lautstärke-Kontrolle (0-100%)
- **Standard**: 50% Lautstärke
- **Einstellungen**: Gespeichert in `settings.json` als `sound_volume` und `sounds_enabled`

## EXE-Build:

Die `system.mp3` wird automatisch in die EXE eingebunden via `dfg-funk.spec`:
```python
datas=[
    ('walkie.png', '.'),
    ('settings.json', '.'),
    ('system.mp3', '.'),  # <-- NEU
],
```

## Wichtig:

⚠️ **Die Datei `system.mp3` MUSS im client Ordner existieren, sonst startet der Client nicht!**

Lege sie hier ab:
```
d:\VSCode_Projects\dfg-funk\python-funk-system\client\system.mp3
```

## Test:

1. Starte den Client: `python main.py`
2. Öffne Einstellungen (Zahnrad-Button)
3. Gehe zum "Audio" Tab
4. Teste mit "🔔 Ton testen" Button
5. Passe Lautstärke an (0-100%)
6. Deaktiviere Sounds komplett mit Checkbox
