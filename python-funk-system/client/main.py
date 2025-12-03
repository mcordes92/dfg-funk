import sys
import requests
import webbrowser
import time
import threading
from PySide6.QtWidgets import QApplication, QMessageBox
from gui import MainWindow
from audio_in import AudioInput
from audio_out import AudioOutput
from network import NetworkClient
from hotkeys import HotkeyManager
from config import USER_ID
from logger import setup_logger, log_exception

logger = setup_logger()

# Client version
CLIENT_VERSION = "1.8.0"


class FunkClient:
    def __init__(self):
        self.window = None
        self.audio_input = None
        self.audio_output = None
        self.network = None
        self.hotkey_manager = None
        self.is_connected = False
        self.mic_device = None
        self.speaker_device = None
        self.primary_channel = None
        self.secondary_channel = 41
        self.channel1_target = None
        self.channel2_target = None
        self.current_channel = None
        self.last_rx_time = 0  # Track when last audio was received
        self.rx_session_timeout = 3.0  # Seconds of silence before new RX sound
        self.tx_start_timer = None  # Timer for delayed TX start
        self.pending_tx_type = None  # Track which hotkey was pressed

    def initialize(self):
        self.window = MainWindow()
        self.window.connect_requested.connect(self.on_connect)
        self.window.disconnect_requested.connect(self.on_disconnect)
        self.window.volume_changed.connect(self.on_volume_changed)
        
        self.window.show()
        
        # Check for updates
        self._check_for_updates()
        
        # Check for funk key after window is shown
        funk_key = self.window.settings.get("funk_key")
        if not funk_key:
            self.window._show_funk_key_dialog()
        else:
            # Load allowed channels if funk_key exists
            self.window._fetch_allowed_channels(funk_key)
    
    def _check_for_updates(self):
        """Check for updates from server and prompt user if available"""
        try:
            server_host = self.window.settings.get("server_ip", "srv01.dus.cordesm.de")
            api_port = self.window.settings.get("api_port", 8001)
            
            # Get version info
            response = requests.get(
                f"http://{server_host}:{api_port}/api/version",
                timeout=5
            )
            
            if response.status_code != 200:
                logger.warning(f"Konnte nicht nach Updates suchen: HTTP {response.status_code}")
                return
            
            data = response.json()
            server_version = data.get("version")
            changelog = data.get("changelog", "Keine Informationen verfügbar")
            
            if not server_version:
                logger.info("Keine Server-Version verfügbar")
                return
            
            # Compare versions (simple string comparison for now)
            if self._compare_versions(server_version, CLIENT_VERSION) > 0:
                logger.info(f"Update verfügbar: {server_version} (aktuell: {CLIENT_VERSION})")
                
                # Build download URL
                download_url = f"http://{server_host}:{api_port}/api/updates/download"
                
                msg = QMessageBox(self.window)
                msg.setIcon(QMessageBox.Information)
                msg.setWindowTitle("Update verfügbar")
                msg.setText(f"Eine neue Version ist verfügbar!\n\n"
                           f"Aktuelle Version: {CLIENT_VERSION}\n"
                           f"Neue Version: {server_version}\n\n"
                           f"Änderungen:\n{changelog}")
                msg.setInformativeText(f"Download-Link:\n{download_url}")
                
                # Set white text color for message box
                msg.setStyleSheet("""
                    QMessageBox {
                        background-color: #2b2b2b;
                    }
                    QLabel {
                        color: white;
                    }
                    QPushButton {
                        background-color: #3d3d3d;
                        color: white;
                        border: 1px solid #555555;
                        padding: 5px 15px;
                        border-radius: 3px;
                    }
                    QPushButton:hover {
                        background-color: #4d4d4d;
                    }
                """)
                
                msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msg.setDefaultButton(QMessageBox.Yes)
                yes_btn = msg.button(QMessageBox.Yes)
                yes_btn.setText("Download öffnen")
                no_btn = msg.button(QMessageBox.No)
                no_btn.setText("Später")
                
                if msg.exec() == QMessageBox.Yes:
                    webbrowser.open(download_url)
                    logger.info(f"Download-Link geöffnet: {download_url}")
            else:
                logger.info(f"Client ist aktuell (Version {CLIENT_VERSION})")
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"Konnte nicht nach Updates suchen: {e}")
        except Exception as e:
            logger.error(f"Fehler beim Update-Check: {e}")
    
    def _compare_versions(self, v1, v2):
        """Compare two version strings (X.Y.Z format). Returns 1 if v1 > v2, -1 if v1 < v2, 0 if equal"""
        try:
            parts1 = [int(x) for x in v1.split('.')]
            parts2 = [int(x) for x in v2.split('.')]
            
            for i in range(max(len(parts1), len(parts2))):
                p1 = parts1[i] if i < len(parts1) else 0
                p2 = parts2[i] if i < len(parts2) else 0
                
                if p1 > p2:
                    return 1
                elif p1 < p2:
                    return -1
            
            return 0
        except Exception as e:
            logger.error(f"Fehler beim Versionsvergleich: {e}")
            return 0
    
    def on_connect(self, server_ip, server_port, channel_id, hotkey_primary, hotkey_secondary, mic_device, speaker_device, funk_key, api_port):
        try:
            logger.info(f"Verbindungsversuch zu {server_ip}:{server_port}, Kanal {channel_id}")
            logger.debug(f"Mic: {mic_device}, Speaker: {speaker_device}")
            self.mic_device = mic_device
            self.speaker_device = speaker_device
            self.primary_channel = channel_id
            self.secondary_channel = 41
            self.current_channel = channel_id
            
            self.audio_output = AudioOutput(device=self.speaker_device)
            
            # Get noise gate settings
            noise_gate_enabled = self.window.settings.get("noise_gate_enabled", False)
            noise_gate_threshold = self.window.settings.get("noise_gate_threshold", -40.0)
            
            self.audio_input = AudioInput(self.on_audio_captured, device=self.mic_device,
                                         noise_gate_enabled=noise_gate_enabled,
                                         noise_gate_threshold=noise_gate_threshold)
            
            # Get quick-switch channel configuration
            hotkey_channel1 = self.window.settings.get("hotkey_channel1", "").strip().lower()
            hotkey_channel2 = self.window.settings.get("hotkey_channel2", "").strip().lower()
            self.channel1_target = self.window.settings.get("channel1_target", 41)
            self.channel2_target = self.window.settings.get("channel2_target", 42)
            
            self.hotkey_manager = HotkeyManager(
                hotkey_primary,
                hotkey_secondary,
                self.on_hotkey_press,
                self.on_hotkey_release,
                hotkey_channel1 if hotkey_channel1 else None,
                hotkey_channel2 if hotkey_channel2 else None,
                self.on_channel_switch
            )
            
            self.network = NetworkClient(
                server_ip,
                server_port,
                channel_id,
                USER_ID,
                self.on_audio_received,
                self.on_connection_status,
                self.on_connection_lost,
                funk_key
            )
            self.network.connect()
            
            self.audio_output.start()
            
            self.hotkey_manager.enable()
            
            # Connection status will be set by on_connection_status callback
            
        except Exception as e:
            logger.error(f"Fehler beim Verbinden: {e}")
            log_exception(logger)
            self.window.show_error(str(e))
            self.cleanup_connection()

    def on_disconnect(self):
        self.cleanup_connection()
        self.window.set_connected(False)

    def cleanup_connection(self):
        self.is_connected = False
        
        if self.hotkey_manager:
            self.hotkey_manager.disable()
            self.hotkey_manager = None
        
        if self.audio_input:
            self.audio_input.stop_recording()
            self.audio_input.close()
            self.audio_input = None
        
        if self.audio_output:
            self.audio_output.stop()
            self.audio_output = None
        
        if self.network:
            self.network.disconnect()
            self.network = None

    def on_audio_captured(self, audio_data):
        if self.is_connected and self.network:
            self.network.send_audio(audio_data)

    def on_connection_status(self, success):
        """Called when connection is established"""
        if success:
            self.is_connected = True
            self.window.set_connected(True)
            logger.info(f"✅ Verbindung erfolgreich hergestellt zu Kanal {self.current_channel}")
    
    def on_connection_lost(self):
        """Called when connection to server is lost"""
        logger.warning("⚠️ Verbindung verloren!")
        # Check if it's an authentication error
        if self.network and self.network.auth_error:
            logger.error(f"Auth-Fehler: {self.network.auth_error}")
            self.window.show_error(self.network.auth_error)
        else:
            logger.warning("Verbindung zum Server unterbrochen")
            self.window.show_error("Verbindung verloren!")
        self.on_disconnect()
    
    def on_audio_received(self, audio_data):
        if self.is_connected and self.audio_output:
            current_time = time.time()
            
            # Play RX sound if it's been silent for more than rx_session_timeout
            if current_time - self.last_rx_time > self.rx_session_timeout:
                self.window.sound_manager.play_rx_start()
                logger.debug("RX sound played - new transmission detected")
            
            self.last_rx_time = current_time
            self.audio_output.play_audio(audio_data)

    def on_hotkey_press(self, hotkey_type):
        logger.debug(f"Hotkey gedrückt: {hotkey_type}, connected={self.is_connected}")
        if self.is_connected and self.audio_input and self.network:
            if hotkey_type == 'primary':
                self.current_channel = self.primary_channel
            else:
                self.current_channel = self.secondary_channel
            
            # Play TX start sound (1.mp3)
            self.window.sound_manager.play_tx_start()
            
            # Store pending TX type
            self.pending_tx_type = hotkey_type
            
            # Cancel any existing timer
            if self.tx_start_timer:
                self.tx_start_timer.cancel()
            
            # Start timer to begin recording after sound finishes (800ms)
            self.tx_start_timer = threading.Timer(0.8, self._start_transmission)
            self.tx_start_timer.start()
            logger.debug("TX Sound abgespielt, warte 800ms vor Aufnahme")
        else:
            logger.warning(f"❌ Kann nicht senden: connected={self.is_connected}, audio_input={self.audio_input is not None}, network={self.network is not None}")
    
    def _start_transmission(self):
        """Start actual transmission after TX sound delay"""
        if self.pending_tx_type and self.is_connected and self.audio_input and self.network:
            self.network.set_channel(self.current_channel)
            self.audio_input.start_recording()
            self.window.show_transmitting(True, self.pending_tx_type)
            logger.info(f"🎤 Sende auf Kanal {self.current_channel}")

    def on_hotkey_release(self, hotkey_type):
        # Cancel pending transmission if released before timer fires
        if self.tx_start_timer and self.tx_start_timer.is_alive():
            self.tx_start_timer.cancel()
            self.pending_tx_type = None
            logger.debug("Hotkey zu früh losgelassen, Übertragung abgebrochen")
            return
        
        # Stop active transmission
        if self.audio_input:
            self.audio_input.stop_recording()
        self.window.show_transmitting(False)
        self.pending_tx_type = None
    
    def on_channel_switch(self, channel_type):
        """Handle quick-switch channel hotkeys"""
        if not self.is_connected or not self.network:
            return
        
        target_channel = None
        if channel_type == 'channel1':
            target_channel = self.channel1_target
        elif channel_type == 'channel2':
            target_channel = self.channel2_target
        
        if target_channel and target_channel != self.current_channel:
            logger.info(f"🔀 Kanalwechsel: {self.current_channel} → {target_channel}")
            self.current_channel = target_channel
            self.network.set_channel(target_channel)
            # Play channel switch sound
            self.window._play_channel_switch_sound()
            # Update GUI to show new channel
            for i in range(self.window.channel_combo.count()):
                if self.window.channel_combo.itemData(i) == target_channel:
                    self.window.channel_combo.setCurrentIndex(i)
                    self.window.channel_label.setText(f"KANAL {target_channel}")
                    break
    
    def on_volume_changed(self, volume_percent):
        """Handle volume changes from GUI"""
        if self.audio_output:
            self.audio_output.set_volume(volume_percent)
            logger.debug(f"🔊 Lautstärke geändert: {volume_percent}%")

    def cleanup(self):
        self.cleanup_connection()
        
        if self.audio_input:
            self.audio_input.close()
        
        if self.audio_output:
            self.audio_output.stop()


def main():
    try:
        app = QApplication(sys.argv)
        
        client = FunkClient()
        client.initialize()
        
        exit_code = app.exec()
        
        client.cleanup()
        logger.info("Client sauber beendet")
        
        sys.exit(exit_code)
    except Exception as e:
        logger.critical(f"Kritischer Fehler: {e}")
        log_exception(logger)
        sys.exit(1)


if __name__ == '__main__':
    main()
