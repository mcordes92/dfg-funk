import json
import os


class Settings:
    def __init__(self, filename="settings.json"):
        self.filename = filename
        self.default_settings = {
            "server_ip": "127.0.0.1",
            "server_port": 50000,
            "channel": 41,
            "hotkey_primary": "f7",
            "hotkey_secondary": "f8",
            "mic_device": None,
            "speaker_device": None,
            "funk_key": None
        }
        self.settings = self.load()
    
    def load(self):
        """Load settings from JSON file"""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    settings = self.default_settings.copy()
                    settings.update(loaded)
                    return settings
            except Exception as e:
                print(f"Error loading settings: {e}")
                return self.default_settings.copy()
        return self.default_settings.copy()
    
    def save(self):
        """Save settings to JSON file"""
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False
    
    def get(self, key, default=None):
        """Get a setting value"""
        return self.settings.get(key, default)
    
    def set(self, key, value):
        """Set a setting value"""
        self.settings[key] = value
    
    def update(self, **kwargs):
        """Update multiple settings at once"""
        self.settings.update(kwargs)
    
    def reset(self):
        """Reset to default settings"""
        self.settings = self.default_settings.copy()
        self.save()
