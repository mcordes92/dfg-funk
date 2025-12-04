import pygame
import os
import sys
from pathlib import Path
import logging

logger = logging.getLogger('DFG-Funk')


class SoundManager:
    """Manages sound playback with volume control using pygame"""
    
    def __init__(self, sound_profile="digitalfunk"):
        self.initialized = False
        self.sound = None
        self.tx_sound = None  # TX sound based on profile
        self.rx_sound = None  # RX sound based on profile
        self.volume = 0.5  # Default 50%
        self.sound_profile = sound_profile  # "digitalfunk" or "cbfunk"
        
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            self.initialized = True
            self._load_sound()
            self._load_profile_sounds()
            logger.info(f"Sound system initialized with profile: {sound_profile}")
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
    
    def _load_profile_sounds(self):
        """Load TX and RX sounds based on active profile"""
        # Determine filenames based on profile
        if self.sound_profile == "cbfunk":
            tx_file = "cb1.mp3"
            rx_file = "cb2.mp3"
        else:  # digitalfunk (default)
            tx_file = "1.mp3"
            rx_file = "2.mp3"
        
        # Load TX sound
        try:
            tx_path = self._get_sound_path(tx_file)
            if tx_path.exists():
                self.tx_sound = pygame.mixer.Sound(str(tx_path))
                self.tx_sound.set_volume(self.volume)
                logger.info(f"TX sound loaded from {tx_path}")
            else:
                logger.warning(f"TX sound not found at {tx_path}")
        except Exception as e:
            logger.error(f"Error loading TX sound: {e}")
        
        # Load RX sound
        try:
            rx_path = self._get_sound_path(rx_file)
            if rx_path.exists():
                self.rx_sound = pygame.mixer.Sound(str(rx_path))
                self.rx_sound.set_volume(self.volume)
                logger.info(f"RX sound loaded from {rx_path}")
            else:
                logger.warning(f"RX sound not found at {rx_path}")
        except Exception as e:
            logger.error(f"Error loading RX sound: {e}")
    
    def set_sound_profile(self, profile):
        """Change sound profile (digitalfunk or cbfunk) and reload sounds"""
        if profile not in ["digitalfunk", "cbfunk"]:
            logger.warning(f"Invalid sound profile: {profile}, using digitalfunk")
            profile = "digitalfunk"
        
        self.sound_profile = profile
        self._load_profile_sounds()
        logger.info(f"Sound profile changed to: {profile}")
    
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
