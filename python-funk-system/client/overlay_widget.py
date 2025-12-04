"""
In-Game Overlay Widget für DFG-Funk

Zeigt Verbindungsstatus, TX/RX Status in einem transparenten Overlay-Fenster
das über allen anderen Fenstern bleibt (auch über Spielen).
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QPalette, QColor
import sys

# Windows-specific imports for better fullscreen game support
if sys.platform == 'win32':
    try:
        import win32gui
        import win32con
        WINDOWS_AVAILABLE = True
    except ImportError:
        WINDOWS_AVAILABLE = False
else:
    WINDOWS_AVAILABLE = False


class OverlayWidget(QWidget):
    """Transparent overlay window that stays on top of all windows"""
    
    # Signals for thread-safe updates
    _update_connected_signal = Signal(bool)
    _update_transmitting_signal = Signal(bool, object)  # bool, channel or None
    _update_receiving_signal = Signal(bool, object)  # bool, channel or None
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # CRITICAL: Minimal flags for maximum game compatibility
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |      # Always on top
            Qt.FramelessWindowHint |        # No window frame  
            Qt.Tool                         # Don't show in taskbar
        )
        
        # Transparent background for text-only overlay
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)  # Don't steal focus from game
        
        # Set fixed size
        self.setFixedSize(220, 100)
        
        # Current state
        self.is_connected = False
        self.is_transmitting = False
        self.tx_channel = None
        self.rx_channel = None
        self.rx_active = False
        
        self.init_ui()
        
        # Auto-hide RX indicator after timeout
        self.rx_timer = QTimer()
        self.rx_timer.timeout.connect(self._clear_rx_slot)
        self.rx_timer.setSingleShot(True)
        
        # Force topmost refresh timer for game compatibility
        self.topmost_timer = QTimer()
        self.topmost_timer.timeout.connect(self._ensure_topmost)
        self.topmost_timer.start(1000)  # Refresh every second
        
        # Connect signals to slots for thread-safe updates
        self._update_connected_signal.connect(self._set_connected_slot)
        self._update_transmitting_signal.connect(self._set_transmitting_slot)
        self._update_receiving_signal.connect(self._set_receiving_slot)
    
    def showEvent(self, event):
        """Override show event to set Windows-specific flags"""
        super().showEvent(event)
        print(f"🖥️ Overlay showEvent triggered - Position: {self.pos()}")
        print(f"📏 Overlay Size: {self.size()}")
        print(f"👁️ Overlay Visible: {self.isVisible()}")
        
        if WINDOWS_AVAILABLE:
            self._set_windows_topmost_aggressive()
            print("✅ Windows AGGRESSIVE TOPMOST flags gesetzt")
        else:
            print("⚠️ pywin32 nicht verfügbar - Standard Qt flags")
            
        # Force repaint
        self.update()
        self.raise_()
        self.activateWindow()
    
    def _set_windows_topmost_aggressive(self):
        """Set AGGRESSIVE Windows flags for maximum visibility"""
        try:
            hwnd = int(self.winId())
            print(f"🪟 Window Handle: {hwnd}")
            
            # Get current extended style
            exstyle = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            
            # SIMPLE approach: Just add TOPMOST and TOOLWINDOW
            # Don't use WS_EX_LAYERED - it conflicts with Qt's transparency
            exstyle |= win32con.WS_EX_TOPMOST | win32con.WS_EX_TOOLWINDOW | win32con.WS_EX_NOACTIVATE
            exstyle &= ~win32con.WS_EX_TRANSPARENT  # Remove transparent for visibility
            
            # Set extended style
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, exstyle)
            print(f"✅ Extended Style: {hex(exstyle)}")
            
            # Force TOPMOST position - this is the key for games
            win32gui.SetWindowPos(
                hwnd,
                win32con.HWND_TOPMOST,
                0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE | win32con.SWP_SHOWWINDOW
            )
            print("✅ HWND_TOPMOST gesetzt")
            
        except Exception as e:
            print(f"⚠️ Windows-Topmost-Fehler: {e}")
    
    def _ensure_topmost(self):
        """Periodically ensure window stays on top (for games that reset Z-order)"""
        if not self.isVisible():
            return
            
        if WINDOWS_AVAILABLE:
            try:
                hwnd = int(self.winId())
                # Aggressively force topmost
                win32gui.SetWindowPos(
                    hwnd,
                    win32con.HWND_TOPMOST,
                    0, 0, 0, 0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE | win32con.SWP_SHOWWINDOW
                )
            except:
                pass  # Silently fail if window not ready
        else:
            # Fallback for non-Windows or no pywin32
            self.raise_()
            self.update()
    
    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # No background - fully transparent
        self.setStyleSheet("""
            QWidget {
                background: transparent;
                border: none;
            }
        """)
        
        # Status label
        self.status_label = QLabel("● Getrennt")
        self.status_label.setStyleSheet("""
            color: #ff4444;
            font-size: 12pt;
            font-weight: bold;
            background: transparent;
            border: none;
        """)
        layout.addWidget(self.status_label)
        
        # TX label
        self.tx_label = QLabel("▶ TX: ---")
        self.tx_label.setStyleSheet("""
            color: #ffffff;
            font-size: 11pt;
            background: transparent;
            border: none;
        """)
        layout.addWidget(self.tx_label)
        
        # RX label
        self.rx_label = QLabel("◀ RX: ---")
        self.rx_label.setStyleSheet("""
            color: #ffffff;
            font-size: 11pt;
            background: transparent;
            border: none;
        """)
        layout.addWidget(self.rx_label)
        
        self.setLayout(layout)
    
    def set_position(self, position):
        """Set overlay position on screen
        
        Args:
            position: "top-left", "top-right", "middle-left", "middle-right", 
                     "bottom-left", "bottom-right"
        """
        screen = self.screen().availableGeometry()
        margin = 20
        print(f"📐 Screen: {screen.width()}x{screen.height()}")
        
        if position == "top-left":
            x = margin
            y = margin
        elif position == "top-right":
            x = screen.width() - self.width() - margin
            y = margin
        elif position == "middle-left":
            x = margin
            y = (screen.height() - self.height()) // 2
        elif position == "middle-right":
            x = screen.width() - self.width() - margin
            y = (screen.height() - self.height()) // 2
        elif position == "bottom-left":
            x = margin
            y = screen.height() - self.height() - margin
        elif position == "bottom-right":
            x = screen.width() - self.width() - margin
            y = screen.height() - self.height() - margin
        else:
            # Default: top-right
            x = screen.width() - self.width() - margin
            y = margin
        
        self.move(x, y)
    
    # Thread-safe public methods
    def set_connected(self, connected):
        """Thread-safe: Update connection status"""
        self._update_connected_signal.emit(connected)
    
    def set_transmitting(self, transmitting, channel=None):
        """Thread-safe: Update TX status"""
        self._update_transmitting_signal.emit(transmitting, channel)
    
    def set_receiving(self, receiving, channel=None):
        """Thread-safe: Update RX status"""
        self._update_receiving_signal.emit(receiving, channel)
    
    # Internal slot methods (run in GUI thread)
    def _set_connected_slot(self, connected):
        """Internal: Update connection status in GUI thread"""
        self.is_connected = connected
        if connected:
            self.status_label.setText("● Verbunden")
            self.status_label.setStyleSheet("""
                color: #44ff44;
                font-size: 12pt;
                font-weight: bold;
                background: transparent;
                border: none;
            """)
        else:
            self.status_label.setText("● Getrennt")
            self.status_label.setStyleSheet("""
                color: #ff4444;
                font-size: 12pt;
                font-weight: bold;
                background: transparent;
                border: none;
            """)
            # Clear TX/RX when disconnected
            self.tx_label.setText("▶ TX: ---")
            self.rx_label.setText("◀ RX: ---")
    
    def _set_transmitting_slot(self, transmitting, channel):
        """Internal: Update TX status in GUI thread"""
        self.is_transmitting = transmitting
        self.tx_channel = channel
        
        if transmitting and channel:
            self.tx_label.setText(f"▶ TX: {channel:02d}")
            self.tx_label.setStyleSheet("""
                color: #ffaa00;
                font-size: 11pt;
                font-weight: bold;
                background: transparent;
                border: none;
            """)
        else:
            self.tx_label.setText("▶ TX: ---")
            self.tx_label.setStyleSheet("""
                color: #ffffff;
                font-size: 11pt;
                background: transparent;
                border: none;
            """)
    
    def _set_receiving_slot(self, receiving, channel):
        """Internal: Update RX status in GUI thread"""
        self.rx_active = receiving
        self.rx_channel = channel
        
        if receiving and channel:
            self.rx_label.setText(f"◀ RX: {channel:02d}")
            self.rx_label.setStyleSheet("""
                color: #44aaff;
                font-size: 11pt;
                font-weight: bold;
                background: transparent;
                border: none;
            """)
            # Auto-hide after 3 seconds
            self.rx_timer.start(3000)
        else:
            self._clear_rx_slot()
    
    def _clear_rx_slot(self):
        """Internal: Clear RX indicator in GUI thread"""
        self.rx_active = False
        self.rx_label.setText("◀ RX: ---")
        self.rx_label.setStyleSheet("""
            color: #ffffff;
            font-size: 11pt;
            background: transparent;
            border: none;
        """)
