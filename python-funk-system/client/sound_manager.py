import pygame
import os
import sys
from pathlib import Path
import logging

logger = logging.getLogger('DFG-Funk')


class SoundManager:
    """Manages sound playback with volume control using pygame"""
    
    def __init__(self):
        self.initialized = False
        self.sound = None
        self.tx_sound = None  # 1.mp3 - Eigener Sendestart
        self.rx_sound = None  # 2.mp3 - Empfang von anderen
        self.volume = 0.5  # Default 50%
        
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            self.initialized = True
            self._load_sound()
            self._load_tx_sound()
            self._load_rx_sound()
            logger.info("Sound system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize sound system: {e}")
    
    def _get_sound_path(self, filename="system.mp3"):
        """Get the path to a sound file, works for both script and frozen exe"""
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            # PyInstaller extracts to _MEIPASS temp folder
            if hasattr(sys, '_MEIPASS'):
                base_path = Path(sys._MEIPASS)
            else:
                base_path = Path(sys.executable).parent
        else:
            # Running as script
            base_path = Path(__file__).parent
        
        sound_file = base_path / filename
        logger.debug(f"Looking for sound at: {sound_file}")
        return sound_file
    
    def _load_sound(self):
        """Load the system sound file"""
        try:
            sound_path = self._get_sound_path("system.mp3")
            
            if sound_path.exists():
                self.sound = pygame.mixer.Sound(str(sound_path))
                self.sound.set_volume(self.volume)
                logger.info(f"Sound loaded from {sound_path}")
            else:
                logger.warning(f"System sound not found at {sound_path}")
                
        except Exception as e:
            logger.error(f"Error loading sound: {e}")
    
    def _load_tx_sound(self):
        """Load TX start sound (1.mp3)"""
        try:
            sound_path = self._get_sound_path("1.mp3")
            
            if sound_path.exists():
                self.tx_sound = pygame.mixer.Sound(str(sound_path))
                self.tx_sound.set_volume(self.volume)
                logger.info(f"TX sound loaded from {sound_path}")
            else:
                logger.warning(f"TX sound not found at {sound_path}")
                
        except Exception as e:
            logger.error(f"Error loading TX sound: {e}")
    
    def _load_rx_sound(self):
        """Load RX start sound (2.mp3)"""
        try:
            sound_path = self._get_sound_path("2.mp3")
            
            if sound_path.exists():
                self.rx_sound = pygame.mixer.Sound(str(sound_path))
                self.rx_sound.set_volume(self.volume)
                logger.info(f"RX sound loaded from {sound_path}")
            else:
                logger.warning(f"RX sound not found at {sound_path}")
                
        except Exception as e:
            logger.error(f"Error loading RX sound: {e}")
    
    def set_volume(self, volume_percent):
        """Set volume for all sounds (0-100)"""
        self.volume = volume_percent / 100.0
        if self.sound:
            self.sound.set_volume(self.volume)
        if self.tx_sound:
            self.tx_sound.set_volume(self.volume)
        if self.rx_sound:
            self.rx_sound.set_volume(self.volume)
        logger.debug(f"Sound volume set to {volume_percent}%")
    
    def play_sound(self):
        """Play the system sound"""
        if self.initialized and self.sound:
            try:
                self.sound.play()
            except Exception as e:
                logger.error(f"Error playing sound: {e}")
    
    def play_tx_start(self):
        """Play TX start sound (1.mp3) - when user starts transmitting"""
        if self.initialized and self.tx_sound:
            try:
                self.tx_sound.play()
                logger.debug("TX start sound played")
            except Exception as e:
                logger.error(f"Error playing TX sound: {e}")
    
    def play_rx_start(self):
        """Play RX start sound (2.mp3) - when receiving from another user"""
        if self.initialized and self.rx_sound:
            try:
                self.rx_sound.play()
                logger.debug("RX start sound played")
            except Exception as e:
                logger.error(f"Error playing RX sound: {e}")
    
    def cleanup(self):
        """Cleanup pygame mixer"""
        if self.initialized:
            try:
                pygame.mixer.quit()
                logger.debug("Sound system cleaned up")
            except:
                pass
