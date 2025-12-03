from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QLineEdit, QPushButton, QSpinBox, QComboBox, QDialog, QDialogButtonBox, QApplication, QCheckBox, QSlider, QProgressBar, QTabWidget)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPixmap, QPainter
import sounddevice as sd
import os
from settings import Settings
from audio_in import AudioInput
from sound_manager import SoundManager


class MainWindow(QMainWindow):
    connect_requested = Signal(str, int, int, str, str, int, int, str, int)  # Added api_port as 9th parameter
    disconnect_requested = Signal()
    volume_changed = Signal(int)  # Signal for volume changes (0-100)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Funkgerät")
        
        # Load settings
        self.settings = Settings()
        
        # Initialize sound manager
        self.sound_manager = SoundManager()
        self.sound_manager.set_volume(self.settings.get("sound_volume", 50))
        
        self.is_connected = False
        self.blink_state = False
        self.allowed_channels = []  # Will be populated from server
        
        # Window dragging
        self.drag_position = None
        
        image_path = os.path.join(os.path.dirname(__file__), "walkie.png")
        original_pixmap = QPixmap(image_path)
        
        if not original_pixmap.isNull():
            scaled_width = int(original_pixmap.width() * 0.5)
            scaled_height = int(original_pixmap.height() * 0.5)
            self.background_pixmap = original_pixmap.scaled(scaled_width, scaled_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.setFixedSize(self.background_pixmap.size())
            self.device_width = scaled_width
            self.device_height = scaled_height
        else:
            self.background_pixmap = QPixmap()
            self.setFixedSize(400, 800)
            self.device_width = 400
            self.device_height = 800
        
        # Frameless window with transparency
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        style = """
            QMainWindow {
                background: transparent;
            }
            QWidget {
                background: transparent;
                color: #1a1a1a;
                font-family: 'Arial', 'Helvetica', sans-serif;
                font-weight: bold;
            }
            QLabel {
                color: #1a1a1a;
                font-size: 10pt;
                font-weight: bold;
                background: transparent;
            }
            QLineEdit, QSpinBox, QComboBox {
                background: rgba(230, 245, 235, 230);
                border: 2px solid #5a7a65;
                border-radius: 5px;
                padding: 8px;
                color: #1a1a1a;
                font-size: 10pt;
            }
            QComboBox::drop-down {
                border: none;
                background: #5a7a65;
                width: 25px;
            }
            QComboBox QAbstractItemView {
                background: #e6f5eb;
                border: 2px solid #5a7a65;
                selection-background-color: #8bb897;
                color: #1a1a1a;
            }
            QPushButton {
                background: rgba(42, 42, 42, 180);
                border: 2px solid #1a1a1a;
                border-radius: 12px;
                padding: 12px;
                color: #ffffff;
                font-size: 11pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(58, 58, 58, 220);
            }
            QPushButton:pressed {
                background: rgba(26, 26, 26, 220);
            }
        """
        self.setStyleSheet(style)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        central_widget.setStyleSheet("background: transparent;")
        
        self.central_widget = central_widget
        
        self.led_label = QLabel(central_widget)
        self.led_label.setStyleSheet("background: #333333; border: 1px solid #555555; border-radius: 6px;")
        
        self.power_button = QPushButton("", central_widget)
        self.power_button.setToolTip("Power ON/OFF")
        self.power_button.clicked.connect(self._on_connect_clicked)
        self.power_button.pressed.connect(self._on_power_pressed)
        self.power_button.released.connect(self._on_power_released)
        self.power_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 60);
                border-radius: 8px;
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 100);
            }
        """)
        
        display_frame = QWidget(central_widget)
        self.display_frame = display_frame
        display_frame.setStyleSheet("background: transparent;")
        
        display_layout = QVBoxLayout(display_frame)
        display_layout.setContentsMargins(5, 5, 5, 5)
        display_layout.setSpacing(2)
        
        # Status line
        self.display_label = QLabel("OFFLINE", display_frame)
        self.display_label.setAlignment(Qt.AlignCenter)
        self.display_label.setStyleSheet("""
            color: #1a1a1a; 
            font-size: 11pt; 
            font-weight: bold; 
            background: transparent;
        """)
        display_layout.addWidget(self.display_label)
        
        # Channel info
        self.channel_label = QLabel("K41", display_frame)
        self.channel_label.setAlignment(Qt.AlignCenter)
        self.channel_label.setStyleSheet("""
            color: #2a2a2a; 
            font-size: 9pt; 
            font-weight: bold; 
            background: transparent;
        """)
        display_layout.addWidget(self.channel_label)
        
        # Connection info
        self.info_label = QLabel("---", display_frame)
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("""
            color: #3a3a3a; 
            font-size: 7pt; 
            background: transparent;
        """)
        display_layout.addWidget(self.info_label)
        
        btn1 = QPushButton("🔊", central_widget)
        self.btn1 = btn1
        btn1.clicked.connect(self._volume_up)
        btn1.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                font-size: 16pt;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 50);
                border-radius: 8px;
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 100);
            }
        """)
        btn1.setToolTip("Lautstärke +")
        
        btn2 = QPushButton("▲", central_widget)
        self.btn2 = btn2
        btn2.clicked.connect(self._channel_up)
        btn2.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                font-size: 14pt;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 50);
                border-radius: 8px;
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 100);
            }
        """)
        btn2.setToolTip("Kanal +")
        
        self.connect_button = QPushButton("SET", central_widget)
        # Only use pressed/released for long-press detection (3 seconds)
        # Do NOT use clicked signal as it conflicts with long-press
        self.connect_button.pressed.connect(self._on_set_pressed)
        self.connect_button.released.connect(self._on_set_released)
        self.connect_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                font-size: 9pt;
                font-weight: bold;
                color: #ffffff;
            }
            QPushButton:hover {
                background: rgba(0, 200, 0, 50);
                border-radius: 10px;
            }
            QPushButton:pressed {
                background: rgba(0, 200, 0, 100);
            }
        """)
        self.connect_button.setToolTip("Einstellungen")
        
        btn3 = QPushButton("🔉", central_widget)
        self.btn3 = btn3
        btn3.clicked.connect(self._volume_down)
        btn3.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                font-size: 16pt;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 50);
                border-radius: 8px;
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 100);
            }
        """)
        btn3.setToolTip("Lautstärke -")
        
        btn4 = QPushButton("▼", central_widget)
        self.btn4 = btn4
        btn4.clicked.connect(self._channel_down)
        btn4.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                font-size: 14pt;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 50);
                border-radius: 8px;
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 100);
            }
        """)
        btn4.setToolTip("Kanal -")
        
        self.updateLayout()
        
        # Hidden input fields - load from settings
        self.server_input = QLineEdit()
        self.server_input.setText(self.settings.get("server_ip", "127.0.0.1"))
        self.server_input.hide()
        
        self.port_input = QSpinBox()
        self.port_input.setMinimum(1)
        self.port_input.setMaximum(65535)
        self.port_input.setValue(self.settings.get("server_port", 50000))
        self.port_input.hide()
        
        self.api_port_input = QSpinBox()
        self.api_port_input.setMinimum(1)
        self.api_port_input.setMaximum(65535)
        self.api_port_input.setValue(self.settings.get("api_port", 8000))
        self.api_port_input.hide()
        
        self.channel_combo = QComboBox()
        # Channels will be populated after funk_key check
        self.channel_combo.hide()
        
        self.mic_combo = QComboBox()
        self.speaker_combo = QComboBox()
        self._populate_audio_devices()
        
        self.mic_combo.hide()
        self.speaker_combo.hide()
        
        self.hotkey_primary_input = QLineEdit()
        self.hotkey_primary_input.setText(self.settings.get("hotkey_primary", "f7"))
        self.hotkey_primary_input.hide()
        
        self.hotkey_secondary_input = QLineEdit()
        self.hotkey_secondary_input.setText(self.settings.get("hotkey_secondary", "f8"))
        self.hotkey_secondary_input.hide()
        
        self.hotkey_channel1_input = QLineEdit()
        self.hotkey_channel1_input.setText(self.settings.get("hotkey_channel1", ""))
        self.hotkey_channel1_input.hide()
        
        self.hotkey_channel2_input = QLineEdit()
        self.hotkey_channel2_input.setText(self.settings.get("hotkey_channel2", ""))
        self.hotkey_channel2_input.hide()
        
        self.channel1_target = QSpinBox()
        self.channel1_target.setMinimum(41)
        self.channel1_target.setMaximum(69)
        self.channel1_target.setValue(self.settings.get("channel1_target", 41))
        self.channel1_target.hide()
        
        self.channel2_target = QSpinBox()
        self.channel2_target.setMinimum(41)
        self.channel2_target.setMaximum(69)
        self.channel2_target.setValue(self.settings.get("channel2_target", 42))
        self.channel2_target.hide()
        
        self.blink_timer = QTimer()
        self.blink_timer.timeout.connect(self._blink_led)
        self.blink_timer.start(800)
        
        self.ping_timer = QTimer()
        self.ping_timer.timeout.connect(self._update_ping)
        
        # Power button long press
        self.power_press_timer = QTimer()
        self.power_press_timer.setSingleShot(True)
        self.power_press_timer.timeout.connect(self._show_exit_dialog)
        
        # SET button long press
        self.set_press_timer = QTimer()
        self.set_press_timer.setSingleShot(True)
        self.set_press_timer.timeout.connect(self._show_settings)
        
        # Channel selection
        self.pending_channel = None  # Temporärer Kanal, noch nicht gesetzt
        self.channel_blink_timer = QTimer()
        self.channel_blink_timer.timeout.connect(self._blink_channel)
        self.channel_blink_state = False
        
        self.current_volume = 100
        self.current_ping = 0
        self.is_transmitting = False
    
    def updateLayout(self):
        w = self.device_width
        h = self.device_height

        display_x = int(w * 0.3242)
        display_y = int(h * 0.3398)
        display_width = int(w * 0.3438)
        display_height = int(h * 0.1120)
        self.display_frame.setGeometry(display_x, display_y, display_width, display_height)

        led_x = int(w * 0.4785)
        led_y = int(h * 0.4935)
        led_width = int(w * 0.0391)
        led_height = int(h * 0.0260)
        self.led_label.setGeometry(led_x, led_y, led_width, led_height)

        btn1_x = int(w * 0.3125)
        btn1_y = int(h * 0.5143)
        btn1_width = int(w * 0.0996)
        btn1_height = int(h * 0.0456)
        self.btn1.setGeometry(btn1_x, btn1_y, btn1_width, btn1_height)

        btn2_x = int(w * 0.5859)
        btn2_y = int(h * 0.5169)
        btn2_width = int(w * 0.1074)
        btn2_height = int(h * 0.0456)
        self.btn2.setGeometry(btn2_x, btn2_y, btn2_width, btn2_height)

        btn3_x = int(w * 0.3203)
        btn3_y = int(h * 0.5885)
        btn3_width = int(w * 0.0879)
        btn3_height = int(h * 0.0456)
        self.btn3.setGeometry(btn3_x, btn3_y, btn3_width, btn3_height)

        btn4_x = int(w * 0.5898)
        btn4_y = int(h * 0.5859)
        btn4_width = int(w * 0.0957)
        btn4_height = int(h * 0.0456)
        self.btn4.setGeometry(btn4_x, btn4_y, btn4_width, btn4_height)

        center_x = int(w * 0.4531)
        center_y = int(h * 0.5482)
        center_width = int(w * 0.0996)
        center_height = int(h * 0.0508)
        self.connect_button.setGeometry(center_x, center_y, center_width, center_height)

        pow_x = int(w * 0.6016)
        pow_y = int(h * 0.2591)
        pow_width = int(w * 0.0879)
        pow_height = int(h * 0.0326)
        self.power_button.setGeometry(pow_x, pow_y, pow_width, pow_height)
    
    def paintEvent(self, event):
        """Draw the walkie-talkie background image"""
        painter = QPainter(self)
        if not self.background_pixmap.isNull():
            painter.drawPixmap(0, 0, self.background_pixmap)
    
    def mousePressEvent(self, event):
        """Start dragging window when clicking on empty area"""
        if event.button() == Qt.LeftButton:
            # Check if click is on a widget
            widget = self.childAt(event.position().toPoint())
            if widget is None or widget == self.centralWidget():
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()
    
    def mouseMoveEvent(self, event):
        """Move window when dragging"""
        if event.buttons() == Qt.LeftButton and self.drag_position is not None:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """Stop dragging"""
        if event.button() == Qt.LeftButton:
            self.drag_position = None
            event.accept()
    
    def _populate_audio_devices(self):
        """Populate audio device comboboxes with saved settings"""
        devices = sd.query_devices()
        saved_mic = self.settings.get("mic_device")
        saved_speaker = self.settings.get("speaker_device")
        
        # Clear existing items first
        self.mic_combo.clear()
        self.speaker_combo.clear()
        
        # Track added devices to prevent duplicates
        added_mics = set()
        added_speakers = set()
        
        # Populate microphones
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                device_name = device['name']
                if device_name not in added_mics:
                    self.mic_combo.addItem(device_name, i)
                    added_mics.add(device_name)
        
        if self.mic_combo.count() > 0:
            # Try to load saved device, otherwise use default
            if saved_mic is not None:
                for i in range(self.mic_combo.count()):
                    if self.mic_combo.itemData(i) == saved_mic:
                        self.mic_combo.setCurrentIndex(i)
                        break
            else:
                default_input = sd.default.device[0]
                if default_input is not None:
                    for i in range(self.mic_combo.count()):
                        if self.mic_combo.itemData(i) == default_input:
                            self.mic_combo.setCurrentIndex(i)
                            break
        
        # Populate speakers
        for i, device in enumerate(devices):
            if device['max_output_channels'] > 0:
                device_name = device['name']
                if device_name not in added_speakers:
                    self.speaker_combo.addItem(device_name, i)
                    added_speakers.add(device_name)
        
        if self.speaker_combo.count() > 0:
            # Try to load saved device, otherwise use default
            if saved_speaker is not None:
                for i in range(self.speaker_combo.count()):
                    if self.speaker_combo.itemData(i) == saved_speaker:
                        self.speaker_combo.setCurrentIndex(i)
                        break
            else:
                default_output = sd.default.device[1]
                if default_output is not None:
                    for i in range(self.speaker_combo.count()):
                        if self.speaker_combo.itemData(i) == default_output:
                            self.speaker_combo.setCurrentIndex(i)
                            break
    
    def _on_connect_clicked(self):
        self._play_button_sound()
        if not self.is_connected:
            server_ip = self.settings.get("server_ip", "127.0.0.1")
            server_port = self.settings.get("server_port", 50000)
            api_port = self.settings.get("api_port", 8000)
            channel_id = self.channel_combo.currentData()
            
            # Validate: Channel 41 cannot be used as primary channel
            if channel_id == 41:
                self.display_label.setText("FEHLER")
                self.info_label.setText("Kanal 41 nur für Allgemein")
                return
            
            hotkey_primary = self.settings.get("hotkey_primary", "f7")
            hotkey_secondary = self.settings.get("hotkey_secondary", "f8")
            mic_device = self.mic_combo.currentData()
            speaker_device = self.speaker_combo.currentData()
            funk_key = self.settings.get("funk_key", "")
            
            self.connect_requested.emit(
                server_ip, server_port, channel_id,
                hotkey_primary, hotkey_secondary,
                mic_device, speaker_device, funk_key, api_port
            )
        else:
            self.disconnect_requested.emit()
    
    def _on_power_pressed(self):
        """Start timer for long press detection"""
        self.power_press_timer.start(1000)  # 1 second long press
    
    def _on_power_released(self):
        """Cancel long press timer"""
        self.power_press_timer.stop()
    
    def _on_set_pressed(self):
        """Start timer for SET button long press"""
        self.set_press_timer.start(3000)  # 3 seconds long press
    
    def _on_set_released(self):
        """Handle SET button release - apply channel only on short press"""
        # Check if timer is still running (short press) or already fired (long press)
        if self.set_press_timer.isActive():
            # Short press - only apply channel if there is a pending channel
            self.set_press_timer.stop()
            if self.pending_channel is not None:
                self._apply_channel()
        # If timer is not active, it already fired and opened settings (long press)
    
    def _show_exit_dialog(self):
        """Show exit confirmation dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Funkger\u00e4t schlie\u00dfen")
        dialog.setModal(True)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        label = QLabel("M\u00f6chten Sie das Funkger\u00e4t wirklich schlie\u00dfen?")
        label.setStyleSheet("font-size: 11pt;")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        yes_button = QPushButton("Ja")
        yes_button.setStyleSheet("""
            QPushButton {
                background: #cc0000;
                color: white;
                border: none;
                padding: 8px 20px;
                font-size: 10pt;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #ff0000;
            }
        """)
        yes_button.clicked.connect(lambda: (dialog.accept(), QApplication.quit()))
        
        no_button = QPushButton("Nein")
        no_button.setStyleSheet("""
            QPushButton {
                background: #666666;
                color: white;
                border: none;
                padding: 8px 20px;
                font-size: 10pt;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #888888;
            }
        """)
        no_button.clicked.connect(dialog.reject)
        
        button_layout.addWidget(yes_button)
        button_layout.addWidget(no_button)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        dialog.exec()
    
    def _blink_status(self):
        """Start timer for long press detection"""
        self.power_press_timer.start(1000)  # 1 second long press
    
    def _on_power_released(self):
        """Cancel long press timer"""
        self.power_press_timer.stop()
    
    def _show_exit_dialog(self):
        """Show exit confirmation dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Funkgerät schließen")
        dialog.setModal(True)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        label = QLabel("Möchten Sie das Funkgerät wirklich schließen?")
        label.setStyleSheet("font-size: 11pt; color: white;")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        yes_button = QPushButton("Ja")
        yes_button.setStyleSheet("""
            QPushButton {
                background: #cc0000;
                color: white;
                border: none;
                padding: 8px 20px;
                font-size: 10pt;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #ff0000;
            }
        """)
        yes_button.clicked.connect(lambda: (dialog.accept(), QApplication.quit()))
        
        no_button = QPushButton("Nein")
        no_button.setStyleSheet("""
            QPushButton {
                background: #666666;
                color: white;
                border: none;
                padding: 8px 20px;
                font-size: 10pt;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #888888;
            }
        """)
        no_button.clicked.connect(dialog.reject)
        
        button_layout.addWidget(yes_button)
        button_layout.addWidget(no_button)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        dialog.exec()
    
    def _blink_status(self):
        if self.is_connected:
            self.blink_state = not self.blink_state
            if self.blink_state:
                self.display_label.setText("◉ ONLINE")
                self.display_label.setStyleSheet("""
                    color: #00aa00; 
                    font-size: 11pt; 
                    font-weight: bold; 
                    background: transparent;
                """)
            else:
                self.display_label.setText("● ONLINE")
                self.display_label.setStyleSheet("""
                    color: #006600; 
                    font-size: 11pt; 
                    font-weight: bold; 
                    background: transparent;
                """)
    
    def _blink_led(self):
        # Don't blink LED when transmitting
        if self.is_transmitting:
            return
        
        if self.is_connected:
            self.blink_state = not self.blink_state
            if self.blink_state:
                self.led_label.setStyleSheet("background: #00ff00; border: 1px solid #00aa00; border-radius: 6px;")
            else:
                self.led_label.setStyleSheet("background: #00aa00; border: 1px solid #008800; border-radius: 6px;")
        else:
            self.led_label.setStyleSheet("background: #333333; border: 1px solid #555555; border-radius: 6px;")
    
    def _update_ping(self):
        import random
        self.current_ping = random.randint(5, 100)
        self._draw_ping_bars()
    
    def _draw_ping_bars(self):
        if not self.is_connected:
            self.display_label.setText("")
            self.display_label.setStyleSheet("""
                color: #000000; 
                font-size: 10pt; 
                font-weight: bold; 
                background: transparent;
                letter-spacing: 1px;
            """)
            return
        
        bars = ""
        num_bars = 8
        max_ping = 100
        filled_bars = int((1 - min(self.current_ping, max_ping) / max_ping) * num_bars)
        
        for i in range(num_bars):
            if i < filled_bars:
                if filled_bars >= 6:
                    bars += "█"
                elif filled_bars >= 4:
                    bars += "█"
                else:
                    bars += "█"
            else:
                bars += "░"
        
        self.display_label.setText(f"{bars} {self.current_ping}ms")
        self.display_label.setStyleSheet("""
            color: #000000; 
            font-size: 9pt; 
            font-weight: bold; 
            background: transparent;
            font-family: 'Courier New', monospace;
        """)
    
    def _play_button_sound(self):
        """Play button click sound"""
        if not self.settings.get("sounds_enabled", True):
            return
        self.sound_manager.play_sound()
    
    def _play_channel_switch_sound(self):
        """Play channel switch sound"""
        if not self.settings.get("sounds_enabled", True):
            return
        self.sound_manager.play_sound()
    
    def closeEvent(self, event):
        """Cleanup when window is closed"""
        self.sound_manager.cleanup()
        event.accept()
    
    def _volume_up(self):
        self._play_button_sound()
        if self.is_connected:
            self.current_volume = min(100, self.current_volume + 10)
            self.info_label.setText(f"VOL {self.current_volume}%")
            # Update audio output volume
            self.volume_changed.emit(self.current_volume)
    
    def _volume_down(self):
        self._play_button_sound()
        if self.is_connected:
            self.current_volume = max(0, self.current_volume - 10)
            self.info_label.setText(f"VOL {self.current_volume}%")
            # Update audio output volume
            self.volume_changed.emit(self.current_volume)
    
    def _channel_up(self):
        self._play_button_sound()
        current_index = self.channel_combo.currentIndex()
        if current_index < self.channel_combo.count() - 1:
            self.channel_combo.setCurrentIndex(current_index + 1)
            channel = self.channel_combo.currentData()
            self.pending_channel = channel
            self.channel_label.setText(f"KANAL {channel}")
            # Start blinking if channel changed but not applied
            if not self.channel_blink_timer.isActive():
                self.channel_blink_timer.start(500)  # Blink every 500ms
    
    def _channel_down(self):
        self._play_button_sound()
        current_index = self.channel_combo.currentIndex()
        if current_index > 0:
            self.channel_combo.setCurrentIndex(current_index - 1)
            channel = self.channel_combo.currentData()
            self.pending_channel = channel
            self.channel_label.setText(f"KANAL {channel}")
            # Start blinking if channel changed but not applied
            if not self.channel_blink_timer.isActive():
                self.channel_blink_timer.start(500)  # Blink every 500ms
    
    def _apply_channel(self):
        """Apply the selected channel and reconnect if necessary"""
        self._play_button_sound()
        
        # Stop blinking
        self.channel_blink_timer.stop()
        self.channel_label.setStyleSheet("""
            color: #000000; 
            font-size: 12pt; 
            font-weight: bold; 
            background: transparent;
            letter-spacing: 2px;
        """)
        
        if self.pending_channel is None:
            # No pending channel, do nothing
            return
        
        # Apply channel
        channel = self.pending_channel
        self.pending_channel = None
        
        # Save channel to settings
        self.settings.set("channel", channel)
        self.settings.save()
        
        if self.is_connected:
            # Reconnect with new channel
            self.disconnect_requested.emit()
            server_ip = self.settings.get("server_ip", "127.0.0.1")
            server_port = self.settings.get("server_port", 50000)
            api_port = self.settings.get("api_port", 8000)
            hotkey_primary = self.settings.get("hotkey_primary", "f7")
            hotkey_secondary = self.settings.get("hotkey_secondary", "f8")
            mic_device = self.mic_combo.currentData()
            speaker_device = self.speaker_combo.currentData()
            funk_key = self.settings.get("funk_key", "")
            self.connect_requested.emit(
                server_ip, server_port, channel,
                hotkey_primary, hotkey_secondary,
                mic_device, speaker_device, funk_key, api_port
            )
    
    def _blink_channel(self):
        """Blink channel label when channel is changed but not applied"""
        self.channel_blink_state = not self.channel_blink_state
        if self.channel_blink_state:
            self.channel_label.setStyleSheet("""
                color: #ff6600; 
                font-size: 12pt; 
                font-weight: bold; 
                background: transparent;
                letter-spacing: 2px;
            """)
        else:
            self.channel_label.setStyleSheet("""
                color: #000000; 
                font-size: 12pt; 
                font-weight: bold; 
                background: transparent;
                letter-spacing: 2px;
            """)
    
    def _show_settings(self):
        """Show comprehensive settings dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("⚙️ Funkgerät Einstellungen")
        dialog.setMinimumWidth(850)
        dialog.setMinimumHeight(650)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Create tab widget
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #cccccc;
                background: #f5f5f5;
            }
            QTabBar::tab {
                background: #e0e0e0;
                color: #333333;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: #00aa00;
                color: white;
            }
            QTabBar::tab:hover {
                background: #00cc00;
                color: white;
            }
        """)
        
        # === AUDIO TAB ===
        audio_tab = QWidget()
        audio_layout = QVBoxLayout()
        audio_layout.setSpacing(15)
        audio_layout.setContentsMargins(20, 20, 20, 20)
        
        # Audio section
        audio_label = QLabel("<b>🎧 Audio-Geräte</b>")
        audio_label.setStyleSheet("font-size: 12pt; color: #00aa00;")
        audio_layout.addWidget(audio_label)
        
        # Create new comboboxes for this dialog
        dialog_mic_combo = QComboBox()
        dialog_speaker_combo = QComboBox()
        
        # Populate audio devices
        devices = sd.query_devices()
        current_mic = self.mic_combo.currentData()
        current_speaker = self.speaker_combo.currentData()
        
        # Track added devices to prevent duplicates
        added_mics = set()
        added_speakers = set()
        
        # Populate microphones
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                device_name = device['name']
                if device_name not in added_mics:
                    dialog_mic_combo.addItem(device_name, i)
                    added_mics.add(device_name)
        # Set current selection
        for i in range(dialog_mic_combo.count()):
            if dialog_mic_combo.itemData(i) == current_mic:
                dialog_mic_combo.setCurrentIndex(i)
                break
        
        # Populate speakers
        for i, device in enumerate(devices):
            if device['max_output_channels'] > 0:
                device_name = device['name']
                if device_name not in added_speakers:
                    dialog_speaker_combo.addItem(device_name, i)
                    added_speakers.add(device_name)
        # Set current selection
        for i in range(dialog_speaker_combo.count()):
            if dialog_speaker_combo.itemData(i) == current_speaker:
                dialog_speaker_combo.setCurrentIndex(i)
                break
        
        # Microphone
        mic_layout = QHBoxLayout()
        mic_label = QLabel("🎤 Mikrofon:")
        mic_label.setMinimumWidth(140)
        mic_layout.addWidget(mic_label)
        mic_layout.addWidget(dialog_mic_combo)
        audio_layout.addLayout(mic_layout)
        
        # Speaker
        speaker_layout = QHBoxLayout()
        speaker_label = QLabel("🔊 Lautsprecher:")
        speaker_label.setMinimumWidth(140)
        speaker_layout.addWidget(speaker_label)
        speaker_layout.addWidget(dialog_speaker_combo)
        audio_layout.addLayout(speaker_layout)
        
        # Noise Gate section
        audio_layout.addSpacing(10)
        noisegate_label = QLabel("<b>🎚️ Hintergrundgeräuschfilter (Noise Gate)</b>")
        noisegate_label.setStyleSheet("font-size: 12pt; color: #00aa00;")
        audio_layout.addWidget(noisegate_label)
        
        # Enable/Disable checkbox
        noisegate_enabled = QCheckBox("Noise Gate aktivieren")
        noisegate_enabled.setChecked(self.settings.get("noise_gate_enabled", False))
        noisegate_enabled.setStyleSheet("font-size: 10pt; padding: 5px;")
        audio_layout.addWidget(noisegate_enabled)
        
        # Threshold slider
        threshold_layout = QHBoxLayout()
        threshold_label = QLabel("Schwellwert:")
        threshold_label.setMinimumWidth(140)
        threshold_layout.addWidget(threshold_label)
        
        threshold_slider = QSlider(Qt.Horizontal)
        threshold_slider.setMinimum(-60)
        threshold_slider.setMaximum(-20)
        threshold_slider.setValue(int(self.settings.get("noise_gate_threshold", -40)))
        threshold_slider.setStyleSheet("padding: 5px;")
        threshold_layout.addWidget(threshold_slider)
        
        threshold_value_label = QLabel(f"{threshold_slider.value()} dB")
        threshold_value_label.setMinimumWidth(60)
        threshold_value_label.setStyleSheet("font-weight: bold;")
        threshold_layout.addWidget(threshold_value_label)
        
        threshold_slider.valueChanged.connect(lambda v: threshold_value_label.setText(f"{v} dB"))
        audio_layout.addLayout(threshold_layout)
        
        # Level meter
        level_meter_layout = QHBoxLayout()
        level_meter_label = QLabel("Mikrofon-Pegel:")
        level_meter_label.setMinimumWidth(140)
        level_meter_layout.addWidget(level_meter_label)
        
        level_meter = QProgressBar()
        level_meter.setMinimum(-60)
        level_meter.setMaximum(-20)
        level_meter.setValue(-60)
        level_meter.setTextVisible(True)
        level_meter.setFormat("%v dB")
        level_meter.setStyleSheet("""
            QProgressBar {
                border: 2px solid #555;
                border-radius: 5px;
                text-align: center;
                background: #222;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00ff00, stop:0.7 #ffff00, stop:1 #ff0000);
            }
        """)
        level_meter_layout.addWidget(level_meter)
        audio_layout.addLayout(level_meter_layout)
        
        # Test button
        test_button = QPushButton("🎤 Mikrofon testen")
        test_button.setCheckable(True)
        test_button.setStyleSheet("""
            QPushButton {
                background: #0066cc;
                color: white;
                border: none;
                padding: 10px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background: #0088ff;
            }
            QPushButton:checked {
                background: #ff6600;
            }
        """)
        
        # Timer for level updates
        level_timer = QTimer(dialog)
        test_stream = None
        
        def toggle_test(checked):
            nonlocal test_stream
            if checked:
                test_button.setText("⏹️ Test stoppen")
                # Start test stream
                try:
                    test_stream = AudioInput(lambda data: None, device=dialog_mic_combo.currentData(),
                                            noise_gate_enabled=noisegate_enabled.isChecked(),
                                            noise_gate_threshold=threshold_slider.value())
                    test_stream.start_recording()
                    level_timer.start(50)  # Update every 50ms
                except Exception as e:
                    print(f"Fehler beim Starten des Tests: {e}")
                    test_button.setChecked(False)
            else:
                test_button.setText("🎤 Mikrofon testen")
                level_timer.stop()
                if test_stream:
                    test_stream.close()
                    test_stream = None
                level_meter.setValue(-60)
        
        def update_level():
            if test_stream:
                level = test_stream.get_current_level()
                level_meter.setValue(int(max(-60, min(-20, level))))
                # Update test stream settings in real-time
                test_stream.set_noise_gate(noisegate_enabled.isChecked(), threshold_slider.value())
        
        level_timer.timeout.connect(update_level)
        test_button.toggled.connect(toggle_test)
        audio_layout.addWidget(test_button)
        
        # Info text
        noisegate_info = QLabel("ℹ️ Der Noise Gate filtert Hintergrundgeräusche.\nStellen Sie den Schwellwert so ein, dass Ihre Stimme durchgelassen wird.")
        noisegate_info.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")
        noisegate_info.setWordWrap(True)
        audio_layout.addWidget(noisegate_info)
        
        # Sound effects section
        audio_layout.addSpacing(20)
        sound_label = QLabel("<b>🔔 Signaltöne</b>")
        sound_label.setStyleSheet("font-size: 12pt; color: #00aa00;")
        audio_layout.addWidget(sound_label)
        
        # Enable/Disable sounds
        sounds_enabled = QCheckBox("Signaltöne aktivieren")
        sounds_enabled.setChecked(self.settings.get("sounds_enabled", True))
        sounds_enabled.setStyleSheet("font-size: 10pt; padding: 5px;")
        audio_layout.addWidget(sounds_enabled)
        
        # Volume slider
        sound_volume_layout = QHBoxLayout()
        sound_volume_label = QLabel("Lautstärke:")
        sound_volume_label.setMinimumWidth(140)
        sound_volume_layout.addWidget(sound_volume_label)
        
        sound_volume_slider = QSlider(Qt.Horizontal)
        sound_volume_slider.setMinimum(0)
        sound_volume_slider.setMaximum(100)
        sound_volume_slider.setValue(self.settings.get("sound_volume", 50))
        sound_volume_slider.setEnabled(sounds_enabled.isChecked())
        sound_volume_slider.setStyleSheet("padding: 5px;")
        sound_volume_layout.addWidget(sound_volume_slider)
        
        sound_volume_value_label = QLabel(f"{sound_volume_slider.value()}%")
        sound_volume_value_label.setMinimumWidth(60)
        sound_volume_value_label.setStyleSheet("font-weight: bold;")
        sound_volume_layout.addWidget(sound_volume_value_label)
        
        sound_volume_slider.valueChanged.connect(lambda v: sound_volume_value_label.setText(f"{v}%"))
        sounds_enabled.toggled.connect(sound_volume_slider.setEnabled)
        audio_layout.addLayout(sound_volume_layout)
        
        # Test sound button
        test_sound_btn = QPushButton("🔔 Ton testen")
        test_sound_btn.setStyleSheet("""
            QPushButton {
                background: #0066cc;
                color: white;
                border: none;
                padding: 10px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background: #0088ff;
            }
        """)
        
        def test_sound():
            if sounds_enabled.isChecked():
                # Update volume for test
                self.sound_manager.set_volume(sound_volume_slider.value())
                self.sound_manager.play_sound()
        
        test_sound_btn.clicked.connect(test_sound)
        audio_layout.addWidget(test_sound_btn)
        
        # Sound info
        sound_info = QLabel("ℹ️ Signaltöne werden bei Tastendrücken und Kanalwechsel abgespielt.")
        sound_info.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")
        sound_info.setWordWrap(True)
        audio_layout.addWidget(sound_info)
        
        # Finish Audio tab
        audio_tab.setLayout(audio_layout)
        
        # ===== HOTKEYS TAB =====
        hotkeys_tab = QWidget()
        hotkeys_layout = QVBoxLayout()
        
        # Hotkeys section
        hotkey_label = QLabel("<b>⌨️ Hotkeys</b>")
        hotkey_label.setStyleSheet("font-size: 12pt; color: #00aa00;")
        hotkeys_layout.addWidget(hotkey_label)
        
        # Primary Hotkey
        hotkey1_layout = QHBoxLayout()
        hotkey1_label = QLabel("🎯 Primär-Taste:")
        hotkey1_label.setMinimumWidth(140)
        hotkey1_layout.addWidget(hotkey1_label)
        
        hotkey1_display = QLineEdit()
        hotkey1_display.setText(self.settings.get("hotkey_primary", "f7"))
        hotkey1_display.setReadOnly(True)
        hotkey1_display.setStyleSheet("background: #ffffff; padding: 8px;")
        hotkey1_layout.addWidget(hotkey1_display)
        
        # Temporary input to store recorded value
        temp_hotkey1_input = QLineEdit()
        temp_hotkey1_input.hide()
        
        hotkey1_record_btn = QPushButton("🎙️ Aufnehmen")
        hotkey1_record_btn.setStyleSheet("""
            QPushButton {
                background: #0066cc;
                color: white;
                border: none;
                padding: 8px 15px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #0088ff;
            }
        """)
        hotkey1_record_btn.clicked.connect(lambda: self._record_hotkey(hotkey1_display, temp_hotkey1_input))
        hotkey1_layout.addWidget(hotkey1_record_btn)
        hotkeys_layout.addLayout(hotkey1_layout)
        
        # Secondary Hotkey
        hotkey2_layout = QHBoxLayout()
        hotkey2_label = QLabel("🔄 Sekundär-Taste:")
        hotkey2_label.setMinimumWidth(140)
        hotkey2_layout.addWidget(hotkey2_label)
        
        hotkey2_display = QLineEdit()
        hotkey2_display.setText(self.settings.get("hotkey_secondary", "f8"))
        hotkey2_display.setReadOnly(True)
        hotkey2_display.setStyleSheet("background: #ffffff; padding: 8px;")
        hotkey2_layout.addWidget(hotkey2_display)
        
        # Temporary input to store recorded value
        temp_hotkey2_input = QLineEdit()
        temp_hotkey2_input.hide()
        
        hotkey2_record_btn = QPushButton("🎙️ Aufnehmen")
        hotkey2_record_btn.setStyleSheet("""
            QPushButton {
                background: #0066cc;
                color: white;
                border: none;
                padding: 8px 15px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #0088ff;
            }
        """)
        hotkey2_record_btn.clicked.connect(lambda: self._record_hotkey(hotkey2_display, temp_hotkey2_input))
        hotkey2_layout.addWidget(hotkey2_record_btn)
        hotkeys_layout.addLayout(hotkey2_layout)
        
        # Info text
        info_label = QLabel("ℹ️ Primär-Taste: Normaler Funkkanal\n🔄 Sekundär-Taste: Notruf-Kanal (41)\n🖱️ Unterstützt: Tastatur + Maustasten (mouse1-5)")
        info_label.setStyleSheet("color: #666; font-size: 9pt; padding: 10px;")
        info_label.setWordWrap(True)
        hotkeys_layout.addWidget(info_label)
        
        # Separator
        hotkeys_layout.addSpacing(10)
        
        # Quick channel switch section
        quickswitch_label = QLabel("<b>⚡ Schnellwahl-Kanäle</b>")
        quickswitch_label.setStyleSheet("font-size: 12pt; color: #00aa00;")
        hotkeys_layout.addWidget(quickswitch_label)
        
        # Channel 1 hotkey
        ch1_layout = QHBoxLayout()
        ch1_label = QLabel("📻 Kanal 1:")
        ch1_label.setMinimumWidth(140)
        ch1_layout.addWidget(ch1_label)
        
        ch1_hotkey_display = QLineEdit()
        ch1_hotkey_display.setText(self.settings.get("hotkey_channel1", ""))
        ch1_hotkey_display.setReadOnly(True)
        ch1_hotkey_display.setPlaceholderText("Keine Taste")
        ch1_hotkey_display.setStyleSheet("background: #ffffff; padding: 8px;")
        ch1_hotkey_display.setMaximumWidth(100)
        ch1_layout.addWidget(ch1_hotkey_display)
        
        # Temporary input to store recorded value
        temp_ch1_input = QLineEdit()
        temp_ch1_input.hide()
        
        ch1_record_btn = QPushButton("🎙️")
        ch1_record_btn.setStyleSheet("""
            QPushButton {
                background: #0066cc;
                color: white;
                border: none;
                padding: 8px 15px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #0088ff;
            }
        """)
        ch1_record_btn.clicked.connect(lambda: self._record_hotkey(ch1_hotkey_display, temp_ch1_input))
        ch1_layout.addWidget(ch1_record_btn)
        
        ch1_layout.addWidget(QLabel("→"))
        
        ch1_target_combo = QComboBox()
        ch1_target_combo.setStyleSheet("background: #ffffff; padding: 8px;")
        ch1_layout.addWidget(ch1_target_combo)
        
        hotkeys_layout.addLayout(ch1_layout)
        
        # Channel 2 hotkey
        ch2_layout = QHBoxLayout()
        ch2_label = QLabel("📻 Kanal 2:")
        ch2_label.setMinimumWidth(140)
        ch2_layout.addWidget(ch2_label)
        
        ch2_hotkey_display = QLineEdit()
        ch2_hotkey_display.setText(self.settings.get("hotkey_channel2", ""))
        ch2_hotkey_display.setReadOnly(True)
        ch2_hotkey_display.setPlaceholderText("Keine Taste")
        ch2_hotkey_display.setStyleSheet("background: #ffffff; padding: 8px;")
        ch2_hotkey_display.setMaximumWidth(100)
        ch2_layout.addWidget(ch2_hotkey_display)
        
        # Temporary input to store recorded value
        temp_ch2_input = QLineEdit()
        temp_ch2_input.hide()
        
        ch2_record_btn = QPushButton("🎙️")
        ch2_record_btn.setStyleSheet("""
            QPushButton {
                background: #0066cc;
                color: white;
                border: none;
                padding: 8px 15px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #0088ff;
            }
        """)
        ch2_record_btn.clicked.connect(lambda: self._record_hotkey(ch2_hotkey_display, temp_ch2_input))
        ch2_layout.addWidget(ch2_record_btn)
        
        ch2_layout.addWidget(QLabel("→"))
        
        ch2_target_combo = QComboBox()
        ch2_target_combo.setStyleSheet("background: #ffffff; padding: 8px;")
        ch2_layout.addWidget(ch2_target_combo)
        
        hotkeys_layout.addLayout(ch2_layout)
        
        # Populate channel target combos with allowed channels
        for channel_id in sorted(self.allowed_channels) if self.allowed_channels else list(range(41, 44)) + list(range(51, 70)):
            if channel_id in [41, 42, 43]:
                ch1_target_combo.addItem(f"Kanal {channel_id} (ALLGEMEIN)", channel_id)
                ch2_target_combo.addItem(f"Kanal {channel_id} (ALLGEMEIN)", channel_id)
            else:
                ch1_target_combo.addItem(f"Kanal {channel_id}", channel_id)
                ch2_target_combo.addItem(f"Kanal {channel_id}", channel_id)
        
        # Set saved target channels
        saved_ch1_target = self.settings.get("channel1_target", 41)
        saved_ch2_target = self.settings.get("channel2_target", 42)
        for i in range(ch1_target_combo.count()):
            if ch1_target_combo.itemData(i) == saved_ch1_target:
                ch1_target_combo.setCurrentIndex(i)
            if ch2_target_combo.itemData(i) == saved_ch2_target:
                ch2_target_combo.setCurrentIndex(i)
        
        # Info text
        quickswitch_info = QLabel("ℹ️ Diese Tasten wechseln sofort zum gewählten Kanal")
        quickswitch_info.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")
        hotkeys_layout.addWidget(quickswitch_info)
        
        # Finish Hotkeys tab
        hotkeys_tab.setLayout(hotkeys_layout)
        
        # ===== NETWORK TAB =====
        network_tab = QWidget()
        network_layout = QVBoxLayout()
        
        # Funk-Key section
        funkkey_label = QLabel("<b>🔑 Funk-Schlüssel</b>")
        funkkey_label.setStyleSheet("font-size: 12pt; color: #00aa00;")
        network_layout.addWidget(funkkey_label)
        
        # Funk key input
        funkkey_layout = QHBoxLayout()
        funkkey_input_label = QLabel("🔐 Schlüssel:")
        funkkey_input_label.setMinimumWidth(140)
        funkkey_layout.addWidget(funkkey_input_label)
        
        funkkey_input = QLineEdit()
        funkkey_input.setText(self.settings.get("funk_key", ""))
        funkkey_input.setEchoMode(QLineEdit.Password)
        funkkey_input.setStyleSheet("background: #ffffff; padding: 8px;")
        funkkey_layout.addWidget(funkkey_input)
        
        show_key_btn = QPushButton("👁️")
        show_key_btn.setCheckable(True)
        show_key_btn.setStyleSheet("""
            QPushButton {
                background: #666666;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #888888;
            }
            QPushButton:checked {
                background: #00aa00;
            }
        """)
        show_key_btn.toggled.connect(lambda checked: funkkey_input.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password))
        funkkey_layout.addWidget(show_key_btn)
        
        network_layout.addLayout(funkkey_layout)
        
        # Funk key info
        funkkey_info = QLabel("ℹ️ Änderungen werden erst nach Neuverbindung aktiv")
        funkkey_info.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")
        network_layout.addWidget(funkkey_info)
        
        # Separator
        network_layout.addSpacing(10)
        
        # Network section
        network_label = QLabel("<b>🌐 Netzwerk</b>")
        network_label.setStyleSheet("font-size: 12pt; color: #00aa00;")
        network_layout.addWidget(network_label)
        
        # Server IP
        server_layout = QHBoxLayout()
        server_label = QLabel("🖥️ Server IP:")
        server_label.setMinimumWidth(140)
        server_layout.addWidget(server_label)
        server_input = QLineEdit()
        server_input.setText(self.settings.get("server_ip", "127.0.0.1"))
        server_input.setStyleSheet("background: #ffffff; padding: 8px;")
        server_layout.addWidget(server_input)
        network_layout.addLayout(server_layout)
        
        # UDP Port
        port_layout = QHBoxLayout()
        port_label = QLabel("🔌 UDP Port:")
        port_label.setMinimumWidth(140)
        port_layout.addWidget(port_label)
        port_input = QSpinBox()
        port_input.setMinimum(1)
        port_input.setMaximum(65535)
        port_input.setValue(self.settings.get("server_port", 50000))
        port_input.setStyleSheet("background: #ffffff; padding: 8px;")
        port_layout.addWidget(port_input)
        network_layout.addLayout(port_layout)
        
        # API Port
        api_port_layout = QHBoxLayout()
        api_port_label = QLabel("🌐 API Port:")
        api_port_label.setMinimumWidth(140)
        api_port_layout.addWidget(api_port_label)
        api_port_input = QSpinBox()
        api_port_input.setMinimum(1)
        api_port_input.setMaximum(65535)
        api_port_input.setValue(self.settings.get("api_port", 8000))
        api_port_input.setStyleSheet("background: #ffffff; padding: 8px;")
        api_port_layout.addWidget(api_port_input)
        network_layout.addLayout(api_port_layout)
        
        # Finish Network tab
        network_tab.setLayout(network_layout)
        
        # Add all tabs to tab widget
        tab_widget.addTab(audio_tab, "🎧 Audio")
        tab_widget.addTab(hotkeys_tab, "⌨️ Hotkeys")
        tab_widget.addTab(network_tab, "🌐 Netzwerk")
        
        # Add tab widget to main layout
        main_layout.addWidget(tab_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_button = QPushButton("❌ Abbrechen")
        cancel_button.setStyleSheet("""
            QPushButton {
                background: #666666;
                color: white;
                border: none;
                padding: 10px 25px;
                font-size: 10pt;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background: #888888;
            }
        """)
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_button)
        
        ok_button = QPushButton("✔️ Speichern")
        ok_button.setStyleSheet("""
            QPushButton {
                background: #00aa00;
                color: white;
                border: none;
                padding: 10px 25px;
                font-size: 10pt;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background: #00cc00;
            }
        """)
        ok_button.clicked.connect(dialog.accept)
        button_layout.addWidget(ok_button)
        
        main_layout.addLayout(button_layout)
        
        dialog.setLayout(main_layout)
        dialog.setStyleSheet("""
            QDialog {
                background: #f0f0f0;
            }
            QLabel {
                color: #1a1a1a;
            }
        """)
        
        result = dialog.exec()
        
        # Save recorded hotkeys and settings if dialog was accepted
        if result == QDialog.Accepted:
            # Stop test if running
            if test_button.isChecked():
                test_button.setChecked(False)
            
            # Update main combobox selections from dialog
            selected_mic = dialog_mic_combo.currentData()
            selected_speaker = dialog_speaker_combo.currentData()
            
            # Find and set the same device in main comboboxes
            for i in range(self.mic_combo.count()):
                if self.mic_combo.itemData(i) == selected_mic:
                    self.mic_combo.setCurrentIndex(i)
                    break
            
            for i in range(self.speaker_combo.count()):
                if self.speaker_combo.itemData(i) == selected_speaker:
                    self.speaker_combo.setCurrentIndex(i)
                    break
            
            # Check if funk_key changed
            new_funk_key = funkkey_input.text().strip()
            old_funk_key = self.settings.get("funk_key", "")
            funk_key_changed = new_funk_key != old_funk_key
            
            # Save all settings
            self.settings.update(
                server_ip=server_input.text(),
                server_port=port_input.value(),
                api_port=api_port_input.value(),
                channel=self.channel_combo.currentData(),
                hotkey_primary=hotkey1_display.text(),
                hotkey_secondary=hotkey2_display.text(),
                hotkey_channel1=ch1_hotkey_display.text(),
                hotkey_channel2=ch2_hotkey_display.text(),
                channel1_target=ch1_target_combo.currentData(),
                channel2_target=ch2_target_combo.currentData(),
                mic_device=selected_mic,
                speaker_device=selected_speaker,
                funk_key=new_funk_key,
                noise_gate_enabled=noisegate_enabled.isChecked(),
                noise_gate_threshold=threshold_slider.value(),
                sounds_enabled=sounds_enabled.isChecked(),
                sound_volume=sound_volume_slider.value()
            )
            
            # Update sound manager volume
            self.sound_manager.set_volume(sound_volume_slider.value())
            self.settings.save()
            print("✔️ Einstellungen gespeichert!")
            
            # Reload channels if funk_key changed
            if funk_key_changed and new_funk_key:
                print("🔄 Funk-Schlüssel geändert, lade Kanäle neu...")
                self._fetch_allowed_channels(new_funk_key)
    
    def _record_hotkey(self, display_field, target_field):
        """Record a hotkey press (keyboard or mouse)"""
        import keyboard
        from pynput import mouse
        
        # Change button text to indicate recording
        display_field.setText("⏸️ Drücke Taste/Maustaste...")
        display_field.setStyleSheet("background: #ffeeaa; padding: 8px; font-weight: bold;")
        
        recorded = [False]  # Use list to allow modification in nested functions
        mouse_listener = [None]
        
        # Record keyboard key
        def on_key_event(event):
            if not recorded[0] and event.event_type == 'down':
                key_name = event.name.lower()
                display_field.setText(key_name)
                display_field.setStyleSheet("background: #ccffcc; padding: 8px;")
                recorded[0] = True
                keyboard.unhook_all()
                if mouse_listener[0]:
                    mouse_listener[0].stop()
        
        # Record mouse button
        def on_mouse_click(x, y, button, pressed):
            if not recorded[0] and pressed:
                button_name = None
                if button == mouse.Button.left:
                    button_name = 'mouse1'
                elif button == mouse.Button.right:
                    button_name = 'mouse2'
                elif button == mouse.Button.middle:
                    button_name = 'mouse3'
                elif hasattr(mouse.Button, 'x1') and button == mouse.Button.x1:
                    button_name = 'mouse4'
                elif hasattr(mouse.Button, 'x2') and button == mouse.Button.x2:
                    button_name = 'mouse5'
                
                if button_name:
                    display_field.setText(button_name)
                    display_field.setStyleSheet("background: #ccffcc; padding: 8px;")
                    recorded[0] = True
                    keyboard.unhook_all()
                    if mouse_listener[0]:
                        mouse_listener[0].stop()
                    return False  # Stop listener
        
        # Start both listeners
        keyboard.hook(on_key_event)
        mouse_listener[0] = mouse.Listener(on_click=on_mouse_click)
        mouse_listener[0].start()
    
    def _show_funk_key_dialog(self):
        """Show dialog to enter funk key"""
        dialog = QDialog(self)
        dialog.setWindowTitle("🔑 Funk-Schlüssel erforderlich")
        dialog.setModal(True)
        dialog.setMinimumWidth(450)
        
        # Prevent closing without entering key
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowCloseButtonHint)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Icon and title
        title_label = QLabel("🔐 Funk-Schlüssel eingeben")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #00aa00;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Info text
        info_label = QLabel("Bitte geben Sie Ihren Funk-Schlüssel ein,\num das Funkgerät zu aktivieren.")
        info_label.setStyleSheet("font-size: 10pt; color: #666;")
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        layout.addSpacing(10)
        
        # Funk key input
        key_input = QLineEdit()
        key_input.setPlaceholderText("z.B. a1b2c3d4e5f6...")
        key_input.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                font-size: 11pt;
                border: 2px solid #00aa00;
                border-radius: 5px;
                background: white;
                color: #000000;
            }
            QLineEdit:focus {
                border: 2px solid #00cc00;
            }
        """)
        layout.addWidget(key_input)
        
        # Error label (hidden by default)
        error_label = QLabel("")
        error_label.setStyleSheet("color: #cc0000; font-size: 9pt;")
        error_label.setAlignment(Qt.AlignCenter)
        error_label.hide()
        layout.addWidget(error_label)
        
        layout.addSpacing(10)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        save_button = QPushButton("✔️ Speichern")
        save_button.setStyleSheet("""
            QPushButton {
                background: #00aa00;
                color: white;
                border: none;
                padding: 12px 30px;
                font-size: 11pt;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background: #00cc00;
            }
            QPushButton:disabled {
                background: #cccccc;
            }
        """)
        
        def validate_and_save():
            funk_key = key_input.text().strip()
            if not funk_key:
                error_label.setText("⚠️ Bitte geben Sie einen Funk-Schlüssel ein!")
                error_label.show()
                return
            
            if len(funk_key) < 8:
                error_label.setText("⚠️ Der Funk-Schlüssel ist zu kurz (min. 8 Zeichen)!")
                error_label.show()
                return
            
            # Save funk key
            self.settings.set("funk_key", funk_key)
            self.settings.save()
            
            # Fetch allowed channels from server
            self._fetch_allowed_channels(funk_key)
            
            dialog.accept()
        
        save_button.clicked.connect(validate_and_save)
        key_input.returnPressed.connect(validate_and_save)
        button_layout.addWidget(save_button)
        
        layout.addLayout(button_layout)
        
        # Help text
        help_label = QLabel("ℹ️ Sie erhalten Ihren Funk-Schlüssel vom Administrator")
        help_label.setStyleSheet("font-size: 8pt; color: #999; margin-top: 20px;")
        help_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(help_label)
        
        dialog.setLayout(layout)
        dialog.setStyleSheet("""
            QDialog {
                background: #f0f0f0;
            }
        """)
        
        dialog.exec()
    
    def _fetch_allowed_channels(self, funk_key):
        """Fetch allowed channels from server API"""
        import requests
        try:
            server_ip = self.settings.get("server_ip", "127.0.0.1")
            api_port = self.settings.get("api_port", 8000)
            # Try to get channels from API
            api_url = f"http://{server_ip}:{api_port}/api/channels/{funk_key}"
            response = requests.get(api_url, timeout=3)
            
            if response.status_code == 200:
                data = response.json()
                channels = data.get("channels", [])
                self.allowed_channels = [ch["channel_id"] for ch in channels]
                print(f"✅ {len(self.allowed_channels)} Kanäle vom Server geladen")
            else:
                print(f"⚠️ Server-Antwort: {response.status_code}, verwende alle Kanäle")
                self.allowed_channels = list(range(41, 44)) + list(range(51, 70))
        except Exception as e:
            print(f"⚠️ Konnte Kanäle nicht vom Server laden: {e}")
            print("   Verwende alle Kanäle als Fallback")
            self.allowed_channels = list(range(41, 44)) + list(range(51, 70))
        
        # Remove channel 41 from primary channel selection (reserved for secondary/emergency)
        if 41 in self.allowed_channels:
            self.allowed_channels.remove(41)
            print("ℹ️ Kanal 41 als primärer Kanal nicht verfügbar (Allgemein-Kanal)")
        
        # Populate channel combo
        self._populate_channels()
    
    def _populate_channels(self):
        """Populate channel combobox with allowed channels"""
        self.channel_combo.clear()
        
        if not self.allowed_channels:
            # Default fallback: all channels
            self.allowed_channels = list(range(41, 44)) + list(range(51, 70))
        
        for channel_id in sorted(self.allowed_channels):
            if channel_id in [41, 42, 43]:
                self.channel_combo.addItem(f"📢 Kanal {channel_id} (ALLGEMEIN)", channel_id)
            else:
                self.channel_combo.addItem(f"🔒 Kanal {channel_id}", channel_id)
        
        # Set saved channel if it's in allowed list
        saved_channel = self.settings.get("channel", 41)
        if saved_channel in self.allowed_channels:
            for i in range(self.channel_combo.count()):
                if self.channel_combo.itemData(i) == saved_channel:
                    self.channel_combo.setCurrentIndex(i)
                    break
        else:
            # If saved channel not allowed, select first available
            if self.channel_combo.count() > 0:
                self.channel_combo.setCurrentIndex(0)
    
    def set_connected(self, connected):
        self.is_connected = connected
        
        if connected:
            # Stop channel blinking and clear pending channel
            self.channel_blink_timer.stop()
            self.pending_channel = None
            
            self.ping_timer.start(2000)
            self.current_ping = 20
            self._draw_ping_bars()
            channel = self.channel_combo.currentData()
            self.channel_label.setText(f"KANAL {channel}")
            self.channel_label.setStyleSheet("""
                color: #000000; 
                font-size: 12pt; 
                font-weight: bold; 
                background: transparent;
                letter-spacing: 2px;
            """)
            self.info_label.setText(f"VOL {self.current_volume}%")
            self.info_label.setStyleSheet("""
                color: #000000; 
                font-size: 8pt; 
                font-weight: bold;
                background: transparent;
                letter-spacing: 1px;
            """)
            self.server_input.setEnabled(False)
            self.port_input.setEnabled(False)
            self.channel_combo.setEnabled(False)
            self.mic_combo.setEnabled(False)
            self.speaker_combo.setEnabled(False)
            self.hotkey_primary_input.setEnabled(False)
            self.hotkey_secondary_input.setEnabled(False)
            self.ping_timer.start(2000)
        else:
            self.ping_timer.stop()
            self._draw_ping_bars()
            channel = self.channel_combo.currentData()
            self.channel_label.setText(f"KANAL {channel}")
            self.channel_label.setStyleSheet("""
                color: #000000; 
                font-size: 12pt; 
                font-weight: bold; 
                background: transparent;
                letter-spacing: 2px;
            """)
            self.info_label.setText("BEREIT")
            self.info_label.setStyleSheet("""
                color: #000000; 
                font-size: 8pt; 
                font-weight: bold;
                background: transparent;
                letter-spacing: 1px;
            """)
            self.server_input.setEnabled(True)
            self.port_input.setEnabled(True)
            self.channel_combo.setEnabled(True)
            self.mic_combo.setEnabled(True)
            self.speaker_combo.setEnabled(True)
            self.hotkey_primary_input.setEnabled(True)
            self.hotkey_secondary_input.setEnabled(True)
    
    def show_transmitting(self, is_transmitting, channel_type='primary'):
        """Change LED color based on channel: blue for primary, red for secondary"""
        self.is_transmitting = is_transmitting
        if is_transmitting:
            if channel_type == 'primary':
                # Blau für primären Kanal
                self.led_label.setStyleSheet("background: #0066ff; border: 1px solid #0088ff; border-radius: 6px;")
            else:
                # Rot für sekundären Kanal
                self.led_label.setStyleSheet("background: #ff0000; border: 1px solid #ff3333; border-radius: 6px;")
        else:
            # Reset to green if connected, otherwise dark
            if self.is_connected:
                self.led_label.setStyleSheet("background: #00ff00; border: 1px solid #00cc00; border-radius: 6px;")
            else:
                self.led_label.setStyleSheet("background: #333333; border: 1px solid #555555; border-radius: 6px;")

    def show_error(self, message):
        self.display_label.setText("ERROR!")
        self.display_label.setStyleSheet("""
            color: #ff0000; 
            font-size: 11pt; 
            font-weight: bold; 
            background: transparent;
        """)
        self.info_label.setText(message)
        self.info_label.setStyleSheet("""
            color: #ff0000; 
            font-size: 7pt; 
            background: transparent;
        """)
        self.info_label.setText(message[:20])
        self.info_label.setStyleSheet("""
            color: #ff0000; 
            font-size: 7pt; 
            background: transparent;
        """)
