"""
Connection Statistics Dialog - Popup für Verbindungsstatistiken

Zeigt detaillierte Verbindungsdaten:
- Latenz zum Server
- Packet Loss
- Gesendete/Empfangene Pakete
- Signalstärke
- Jitter

Wird geöffnet durch Klick auf die Latenz-Anzeige im Display.
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QProgressBar, QFrame)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont


class ConnectionStatsDialog(QDialog):
    """Popup-Dialog für detaillierte Verbindungsstatistiken"""
    
    def __init__(self, network_client, parent=None):
        super().__init__(parent)
        self.network_client = network_client
        
        self.setWindowTitle("📡 Verbindungsstatistiken")
        self.setModal(False)  # Non-modal, damit Hauptfenster weiter bedienbar
        self.setFixedSize(400, 450)
        
        # Set dark background for dialog
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
        """)
        
        self.init_ui()
        
        # Auto-update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_stats)
        self.update_timer.start(1000)  # Update every second
        
        # Initial update
        self.update_stats()
    
    def init_ui(self):
        """UI initialisieren - Einfache Text-Übersicht"""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("📡 Verbindungsstatistiken")
        title.setStyleSheet("color: white; font-size: 16pt; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Stats text display
        self.stats_text = QLabel()
        self.stats_text.setStyleSheet("""
            color: white;
            font-size: 12pt;
            font-family: 'Courier New';
            line-height: 1.6;
        """)
        self.stats_text.setAlignment(Qt.AlignLeft)
        self.stats_text.setWordWrap(True)
        layout.addWidget(self.stats_text)
        
        layout.addStretch()
        
        # Close button
        close_btn = QPushButton("Schließen")
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #0066cc;
                color: white;
                border: none;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 11pt;
                border-radius: 5px;
            }
            QPushButton:hover {
                background: #0088ff;
            }
        """)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
    
    def update_stats(self):
        """Update statistics from network client"""
        if not self.network_client:
            self.stats_text.setText("⚠️ Kein Network-Client verfügbar")
            return
        
        try:
            # Get quality data from network client
            quality = self.network_client.get_connection_quality()
            
            # Connection status
            connected = quality.get('connected', False) and quality.get('authenticated', False)
            status = "✅ Verbunden" if connected else "❌ Getrennt"
            
            # Build stats text
            latency = int(quality.get('latency_ms', 0))
            loss = float(quality.get('packet_loss_percent', 0.0))
            signal = int(quality.get('signal_strength', 100))
            sent = int(quality.get('packets_sent', 0))
            recv = int(quality.get('packets_received', 0))
            jitter = int(quality.get('jitter_ms', 0))
            
            stats_text = f"""
Status:           {status}

Latenz:           {latency} ms
Packet Loss:      {loss:.1f} %
Signalstärke:     {signal} %

Pakete gesendet:  {sent}
Pakete empfangen: {recv}

Jitter:           {jitter} ms
            """.strip()
            
            self.stats_text.setText(stats_text)
            
        except Exception as e:
            self.stats_text.setText(f"❌ Fehler beim Laden:\n{str(e)}")
    
    def closeEvent(self, event):
        """Cleanup when dialog is closed"""
        if self.update_timer:
            self.update_timer.stop()
        event.accept()
