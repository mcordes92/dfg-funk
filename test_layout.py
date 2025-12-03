import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QFrame, QPushButton, QLabel
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QColor


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Walkie-Talkie Layout")
        self.setMinimumSize(400, 800)
        
        self.device_widget = QWidget(self)
        self.setCentralWidget(self.device_widget)
        
        self.device_widget.setStyleSheet("""
            QWidget {
                background-color: #3a4449;
            }
        """)
        
        self.displayFrame = QFrame(self.device_widget)
        self.displayFrame.setObjectName("displayFrame")
        self.displayFrame.setStyleSheet("""
            QFrame#displayFrame {
                background-color: #5a7a6a;
                border: 3px solid #2a3a34;
                border-radius: 10px;
            }
        """)
        
        self.btnPower = QPushButton("⏻", self.device_widget)
        self.btnPower.setObjectName("btnPower")
        self.btnPower.setStyleSheet("""
            QPushButton#btnPower {
                background-color: #2a2a2a;
                border: 2px solid #1a1a1a;
                border-radius: 8px;
                color: #ffffff;
                font-size: 14pt;
                font-weight: bold;
            }
            QPushButton#btnPower:hover {
                background-color: #3a3a3a;
            }
            QPushButton#btnPower:pressed {
                background-color: #1a1a1a;
            }
        """)
        
        self.ledStatus = QFrame(self.device_widget)
        self.ledStatus.setObjectName("ledStatus")
        self.ledStatus.setStyleSheet("""
            QFrame#ledStatus {
                background-color: #2a2a2a;
                border: 2px solid #1a1a1a;
                border-radius: 50%;
            }
        """)
        
        self.btnMidLeft = QPushButton("", self.device_widget)
        self.btnMidLeft.setObjectName("btnMidLeft")
        self.btnMidRight = QPushButton("", self.device_widget)
        self.btnMidRight.setObjectName("btnMidRight")
        
        self.btnLowLeft = QPushButton("", self.device_widget)
        self.btnLowLeft.setObjectName("btnLowLeft")
        self.btnLowMid = QPushButton("", self.device_widget)
        self.btnLowMid.setObjectName("btnLowMid")
        self.btnLowRight = QPushButton("", self.device_widget)
        self.btnLowRight.setObjectName("btnLowRight")
        
        button_style = """
            QPushButton {
                background-color: #2a2a2a;
                border: 2px solid #1a1a1a;
                border-radius: 8px;
                color: #ffffff;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
            }
            QPushButton:pressed {
                background-color: #1a1a1a;
            }
        """
        
        self.btnMidLeft.setStyleSheet(button_style)
        self.btnMidRight.setStyleSheet(button_style)
        self.btnLowLeft.setStyleSheet(button_style)
        self.btnLowMid.setStyleSheet(button_style)
        self.btnLowRight.setStyleSheet(button_style)
        
        self.speakerArea = QFrame(self.device_widget)
        self.speakerArea.setObjectName("speakerArea")
        self.speakerArea.setStyleSheet("""
            QFrame#speakerArea {
                background-color: #4a5459;
                border: none;
            }
        """)
        
        self.updateLayout()
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.updateLayout()
    
    def updateLayout(self):
        device_width = self.device_widget.width()
        device_height = self.device_widget.height()
        
        display_width = int(device_width * 0.60)
        display_height = int(device_height * 0.18)
        display_x = int((device_width - display_width) / 2)
        display_y = int(device_height * 0.05)
        self.displayFrame.setGeometry(display_x, display_y, display_width, display_height)
        
        power_width = int(device_width * 0.08)
        power_height = int(device_height * 0.08)
        power_x = int(device_width - power_width - device_width * 0.05)
        power_y = int(device_height * 0.03)
        self.btnPower.setGeometry(power_x, power_y, power_width, power_height)
        
        led_size = int(device_width * 0.06)
        led_x = int((device_width - led_size) / 2)
        led_y = display_y + display_height + int(device_height * 0.02)
        self.ledStatus.setGeometry(led_x, led_y, led_size, led_size)
        self.ledStatus.setStyleSheet(f"""
            QFrame#ledStatus {{
                background-color: #2a2a2a;
                border: 2px solid #1a1a1a;
                border-radius: {led_size // 2}px;
            }}
        """)
        
        mid_button_width = int(device_width * 0.14)
        mid_button_height = int(device_height * 0.10)
        mid_y = led_y + led_size + int(device_height * 0.03)
        
        mid_left_x = int(device_width * 0.20)
        self.btnMidLeft.setGeometry(mid_left_x, mid_y, mid_button_width, mid_button_height)
        
        mid_right_x = int(device_width - mid_button_width - device_width * 0.20)
        self.btnMidRight.setGeometry(mid_right_x, mid_y, mid_button_width, mid_button_height)
        
        low_button_width = int(device_width * 0.14)
        low_button_height = int(device_height * 0.10)
        low_y = mid_y + mid_button_height + int(device_height * 0.03)
        
        low_left_x = int(device_width * 0.15)
        self.btnLowLeft.setGeometry(low_left_x, low_y, low_button_width, low_button_height)
        
        low_mid_x = int((device_width - low_button_width) / 2)
        self.btnLowMid.setGeometry(low_mid_x, low_y, low_button_width, low_button_height)
        
        low_right_x = int(device_width - low_button_width - device_width * 0.15)
        self.btnLowRight.setGeometry(low_right_x, low_y, low_button_width, low_button_height)
        
        speaker_y = low_y + low_button_height + int(device_height * 0.03)
        speaker_height = device_height - speaker_y
        self.speakerArea.setGeometry(0, speaker_y, device_width, speaker_height)
    
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self.speakerArea)
        painter.setRenderHint(QPainter.Antialiasing)
        
        pen_color = QColor("#3a4449")
        painter.setPen(pen_color)
        
        speaker_rect = self.speakerArea.rect()
        line_spacing = 15
        y_start = 10
        
        for i in range(6):
            y = y_start + i * line_spacing
            if y < speaker_rect.height() - 10:
                x_margin = int(speaker_rect.width() * 0.15)
                painter.drawLine(x_margin, y, speaker_rect.width() - x_margin, y)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
