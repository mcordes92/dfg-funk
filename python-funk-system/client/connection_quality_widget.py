"""
Connection Quality Widget für DFG-Funk GUI

Zeigt Verbindungsqualität, Latenz, Packet Loss und Signal Strength an.
Integriert mit NetworkClient für Live-Updates.

Verwendung:
    from connection_quality_widget import ConnectionQualityWidget
    
    quality_widget = ConnectionQualityWidget(network_client)
    layout.addWidget(quality_widget)
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QProgressBar, QFrame)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor


class ConnectionQualityWidget(QWidget):
    """Widget to display connection quality metrics"""
    
    # Signals for parent widget
    quality_changed = Signal(dict)  # Emits quality data
    connection_lost = Signal()      # Emits when connection is lost
    
    def __init__(self, network_client, parent=None):
        super().__init__(parent)
        self.network_client = network_client
        self.init_ui()
        
        # Register callback with NetworkClient
        self.network_client.set_quality_callback(self.on_quality_update)
        
        # Fallback timer for manual updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.manual_update)
        self.update_timer.start(2000)  # Every 2 seconds
    
    def init_ui(self):
        """Initialize UI components"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # Title
        title = QLabel("📡 Verbindungsqualität")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #cccccc;")
        layout.addWidget(separator)
        
        # Status row
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("Status:"))
        self.status_label = QLabel("Verbinde...")
        self.status_label.setStyleSheet("font-weight: bold;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
        # Latency row
        latency_layout = QHBoxLayout()
        latency_layout.addWidget(QLabel("⏱️ Latenz:"))
        self.latency_label = QLabel("-- ms")
        self.latency_label.setStyleSheet("font-family: 'Courier New'; font-weight: bold;")
        latency_layout.addWidget(self.latency_label)
        latency_layout.addStretch()
        layout.addLayout(latency_layout)
        
        # Packet Loss row
        loss_layout = QHBoxLayout()
        loss_layout.addWidget(QLabel("📊 Packet Loss:"))
        self.loss_label = QLabel("-- %")
        self.loss_label.setStyleSheet("font-family: 'Courier New'; font-weight: bold;")
        loss_layout.addWidget(self.loss_label)
        loss_layout.addStretch()
        layout.addLayout(loss_layout)
        
        # Signal Strength
        signal_layout = QVBoxLayout()
        signal_layout.setSpacing(4)
        
        signal_label_row = QHBoxLayout()
        signal_label_row.addWidget(QLabel("📶 Signalstärke:"))
        self.signal_value_label = QLabel("100%")
        self.signal_value_label.setStyleSheet("font-family: 'Courier New'; font-weight: bold;")
        signal_label_row.addWidget(self.signal_value_label)
        signal_label_row.addStretch()
        signal_layout.addLayout(signal_label_row)
        
        # Progress bar for signal strength
        self.signal_bar = QProgressBar()
        self.signal_bar.setRange(0, 100)
        self.signal_bar.setValue(100)
        self.signal_bar.setTextVisible(False)
        self.signal_bar.setFixedHeight(20)
        self._update_signal_bar_color(100)
        signal_layout.addWidget(self.signal_bar)
        
        layout.addLayout(signal_layout)
        
        # Reconnect info (initially hidden)
        self.reconnect_label = QLabel()
        self.reconnect_label.setStyleSheet("color: orange; font-style: italic;")
        self.reconnect_label.hide()
        layout.addWidget(self.reconnect_label)
        
        layout.addStretch()
        self.setLayout(layout)
        
        # Set fixed width
        self.setFixedWidth(280)
    
    def on_quality_update(self, quality_data):
        """Called by NetworkClient when quality metrics change
        
        Args:
            quality_data: Dict with latency_ms, packet_loss, signal_strength, etc.
        """
        # Update latency
        latency = quality_data['latency_ms']
        self.latency_label.setText(f"{latency} ms")
        self._update_latency_color(latency)
        
        # Update packet loss
        loss = quality_data['packet_loss']
        self.loss_label.setText(f"{loss:.1f} %")
        self._update_loss_color(loss)
        
        # Update signal strength
        signal = int(quality_data['signal_strength'])
        self.signal_bar.setValue(signal)
        self.signal_value_label.setText(f"{signal}%")
        self._update_signal_bar_color(signal)
        
        # Emit signal for parent widget
        self.quality_changed.emit(quality_data)
    
    def manual_update(self):
        """Manual update from timer (fallback)"""
        if not self.network_client or not self.network_client.running:
            return
        
        try:
            quality = self.network_client.get_connection_quality()
            
            # Update status
            status = quality['status']
            self.status_label.setText(status)
            self._update_status_color(quality['signal_strength'])
            
            # Check for reconnect attempts
            if self.network_client.reconnect_attempts > 0:
                delay = min(2 ** self.network_client.reconnect_attempts, 
                           self.network_client.max_reconnect_delay)
                self.reconnect_label.setText(
                    f"🔄 Reconnect in {delay}s (Versuch {self.network_client.reconnect_attempts})"
                )
                self.reconnect_label.show()
            else:
                self.reconnect_label.hide()
            
            # Check if connection lost
            if quality['signal_strength'] == 0 and not quality['connected']:
                self.connection_lost.emit()
                
        except Exception as e:
            print(f"Error updating connection quality: {e}")
    
    def _update_latency_color(self, latency):
        """Update latency label color based on value"""
        if latency < 50:
            color = "green"
        elif latency < 100:
            color = "orange"
        else:
            color = "red"
        self.latency_label.setStyleSheet(f"color: {color}; font-family: 'Courier New'; font-weight: bold;")
    
    def _update_loss_color(self, loss):
        """Update packet loss label color based on value"""
        if loss < 1.0:
            color = "green"
        elif loss < 5.0:
            color = "orange"
        else:
            color = "red"
        self.loss_label.setStyleSheet(f"color: {color}; font-family: 'Courier New'; font-weight: bold;")
    
    def _update_signal_bar_color(self, strength):
        """Update signal strength progress bar color"""
        if strength >= 80:
            color = "#4CAF50"  # Green
        elif strength >= 60:
            color = "#FFC107"  # Yellow
        elif strength >= 40:
            color = "#FF9800"  # Orange
        else:
            color = "#F44336"  # Red
        
        self.signal_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #ccc;
                border-radius: 5px;
                text-align: center;
                background-color: #f0f0f0;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 4px;
            }}
        """)
    
    def _update_status_color(self, strength):
        """Update status label color based on signal strength"""
        if strength >= 80:
            color = "green"
        elif strength >= 60:
            color = "#FFC107"  # Yellow
        elif strength >= 40:
            color = "orange"
        else:
            color = "red"
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")
    
    def cleanup(self):
        """Clean up resources"""
        if self.update_timer:
            self.update_timer.stop()


# Example usage
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication, QMainWindow
    
    app = QApplication(sys.argv)
    
    # Mock NetworkClient for testing
    class MockNetworkClient:
        def __init__(self):
            self.running = True
            self.reconnect_attempts = 0
            self.max_reconnect_delay = 30
            self._quality_callback = None
            
            # Simulate quality changes
            self.timer = QTimer()
            self.timer.timeout.connect(self._simulate_quality_change)
            self.timer.start(3000)
        
        def set_quality_callback(self, callback):
            self._quality_callback = callback
        
        def get_connection_quality(self):
            import random
            return {
                'latency_ms': random.randint(20, 150),
                'packet_loss_percent': random.uniform(0, 5),
                'signal_strength': random.randint(50, 100),
                'status': 'Gut',
                'authenticated': True,
                'connected': True
            }
        
        def _simulate_quality_change(self):
            if self._quality_callback:
                import random
                quality_data = {
                    'latency_ms': random.randint(20, 150),
                    'packet_loss': random.uniform(0, 5),
                    'signal_strength': random.randint(50, 100),
                    'packets_sent': random.randint(1000, 2000),
                    'packets_received': random.randint(950, 1950)
                }
                self._quality_callback(quality_data)
    
    # Create main window
    window = QMainWindow()
    window.setWindowTitle("Connection Quality Widget - Demo")
    
    # Create mock client
    mock_client = MockNetworkClient()
    
    # Create widget
    quality_widget = ConnectionQualityWidget(mock_client)
    window.setCentralWidget(quality_widget)
    
    window.show()
    sys.exit(app.exec())
