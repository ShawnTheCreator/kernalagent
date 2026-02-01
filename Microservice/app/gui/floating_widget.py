"""
Kernel Agent Floating Widget - PyQt5
A small always-on-top floating widget that appears when the C# app is minimized.
Provides voice input, status display, and quick actions.
"""

import sys
import threading
from typing import Callable, Optional
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QLabel, QSystemTrayIcon, QMenu, QAction, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, QPoint, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QIcon, QPixmap, QColor, QPainter, QBrush, QPen, QFont


class SignalBridge(QObject):
    """Bridge to communicate between async code and Qt main thread"""
    show_widget = pyqtSignal()
    hide_widget = pyqtSignal()
    update_status = pyqtSignal(str)
    update_listening = pyqtSignal(bool)
    show_response = pyqtSignal(str)


class FloatingWidget(QWidget):
    """
    Floating orb widget that appears when C# app is minimized.
    Features:
    - Draggable position
    - Voice input button
    - Status indicator
    - Minimize to system tray
    """
    
    def __init__(self, on_voice_click: Optional[Callable] = None, 
                 on_restore_click: Optional[Callable] = None):
        super().__init__()
        
        self.on_voice_click = on_voice_click
        self.on_restore_click = on_restore_click
        self.is_listening = False
        self.drag_position = None
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI components"""
        # Window flags: frameless, always on top, tool window
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Fixed size for the floating widget
        self.setFixedSize(200, 120)
        
        # Position at bottom-right of screen
        self.move_to_default_position()
        
        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)
        
        # Status label
        self.status_label = QLabel("Kernel Ready")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #00ff88;
                font-size: 11px;
                font-weight: bold;
                background: transparent;
            }
        """)
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Response label (for showing AI responses)
        self.response_label = QLabel("")
        self.response_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 10px;
                background: transparent;
            }
        """)
        self.response_label.setAlignment(Qt.AlignCenter)
        self.response_label.setWordWrap(True)
        self.response_label.setMaximumHeight(30)
        layout.addWidget(self.response_label)
        
        # Button layout
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        # Voice button
        self.voice_btn = QPushButton("🎤")
        self.voice_btn.setFixedSize(40, 40)
        self.voice_btn.setStyleSheet(self._get_button_style(False))
        self.voice_btn.clicked.connect(self._on_voice_clicked)
        self.voice_btn.setToolTip("Click to speak")
        btn_layout.addWidget(self.voice_btn)
        
        # Restore button
        self.restore_btn = QPushButton("⬆")
        self.restore_btn.setFixedSize(40, 40)
        self.restore_btn.setStyleSheet(self._get_button_style(False))
        self.restore_btn.clicked.connect(self._on_restore_clicked)
        self.restore_btn.setToolTip("Restore main window")
        btn_layout.addWidget(self.restore_btn)
        
        # Close button
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(40, 40)
        self.close_btn.setStyleSheet(self._get_button_style(False, is_close=True))
        self.close_btn.clicked.connect(self.hide)
        self.close_btn.setToolTip("Hide widget")
        btn_layout.addWidget(self.close_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        
        # Add drop shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 255, 136, 100))
        shadow.setOffset(0, 0)
        self.setGraphicsEffect(shadow)
        
    def _get_button_style(self, active: bool, is_close: bool = False) -> str:
        """Get button stylesheet"""
        if is_close:
            bg_color = "#ff4444" if active else "#333333"
            hover_color = "#ff6666"
        else:
            bg_color = "#00ff88" if active else "#333333"
            hover_color = "#00ffaa" if active else "#444444"
            
        return f"""
            QPushButton {{
                background-color: {bg_color};
                border: 2px solid #00ff88;
                border-radius: 20px;
                color: {'#000000' if active else '#00ff88'};
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
                color: #000000;
            }}
            QPushButton:pressed {{
                background-color: #00cc66;
            }}
        """
        
    def paintEvent(self, event):
        """Custom paint for rounded background"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Semi-transparent dark background
        painter.setBrush(QBrush(QColor(20, 20, 30, 230)))
        painter.setPen(QPen(QColor(0, 255, 136, 150), 2))
        painter.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 15, 15)
        
    def move_to_default_position(self):
        """Move widget to bottom-right corner"""
        screen = QApplication.primaryScreen().geometry()
        x = screen.width() - self.width() - 20
        y = screen.height() - self.height() - 80  # Above taskbar
        self.move(x, y)
        
    def mousePressEvent(self, event):
        """Handle mouse press for dragging"""
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
            
    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging"""
        if event.buttons() == Qt.LeftButton and self.drag_position:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
            
    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        self.drag_position = None
        
    def _on_voice_clicked(self):
        """Handle voice button click"""
        self.is_listening = not self.is_listening
        self.set_listening(self.is_listening)
        
        if self.on_voice_click:
            self.on_voice_click(self.is_listening)
            
    def _on_restore_clicked(self):
        """Handle restore button click"""
        if self.on_restore_click:
            self.on_restore_click()
        self.hide()
        
    def set_listening(self, listening: bool):
        """Update listening state UI"""
        self.is_listening = listening
        self.voice_btn.setStyleSheet(self._get_button_style(listening))
        self.status_label.setText("Listening..." if listening else "Kernel Ready")
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {'#ff8800' if listening else '#00ff88'};
                font-size: 11px;
                font-weight: bold;
                background: transparent;
            }}
        """)
        
    def set_status(self, status: str):
        """Update status text"""
        self.status_label.setText(status)
        
    def show_response_text(self, text: str):
        """Show AI response text briefly"""
        # Truncate if too long
        display_text = text[:50] + "..." if len(text) > 50 else text
        self.response_label.setText(display_text)
        
        # Clear after 5 seconds
        QTimer.singleShot(5000, lambda: self.response_label.setText(""))


class FloatingWidgetManager:
    """
    Manager class to handle the floating widget from async/threaded code.
    Uses Qt signals to safely communicate with the widget.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.app: Optional[QApplication] = None
        self.widget: Optional[FloatingWidget] = None
        self.signal_bridge: Optional[SignalBridge] = None
        self._qt_thread: Optional[threading.Thread] = None
        self._running = False
        
        # Callbacks
        self.on_voice_callback: Optional[Callable] = None
        self.on_restore_callback: Optional[Callable] = None
        
    def start(self, on_voice: Optional[Callable] = None, 
              on_restore: Optional[Callable] = None):
        """Start the Qt application in a separate thread"""
        if self._running:
            return
            
        self.on_voice_callback = on_voice
        self.on_restore_callback = on_restore
        
        self._qt_thread = threading.Thread(target=self._run_qt, daemon=True)
        self._qt_thread.start()
        
        # Wait for Qt to initialize
        import time
        for _ in range(50):  # 5 second timeout
            if self.signal_bridge is not None:
                break
            time.sleep(0.1)
            
    def _run_qt(self):
        """Run Qt event loop in thread"""
        self._running = True
        
        # Create Qt application
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        
        # Create signal bridge
        self.signal_bridge = SignalBridge()
        
        # Create widget
        self.widget = FloatingWidget(
            on_voice_click=self._handle_voice,
            on_restore_click=self._handle_restore
        )
        
        # Connect signals
        self.signal_bridge.show_widget.connect(self.widget.show)
        self.signal_bridge.hide_widget.connect(self.widget.hide)
        self.signal_bridge.update_status.connect(self.widget.set_status)
        self.signal_bridge.update_listening.connect(self.widget.set_listening)
        self.signal_bridge.show_response.connect(self.widget.show_response_text)
        
        # Run event loop
        self.app.exec_()
        self._running = False
        
    def _handle_voice(self, listening: bool):
        """Handle voice button from Qt thread"""
        if self.on_voice_callback:
            # Run callback in separate thread to not block Qt
            threading.Thread(
                target=self.on_voice_callback, 
                args=(listening,),
                daemon=True
            ).start()
            
    def _handle_restore(self):
        """Handle restore button from Qt thread"""
        if self.on_restore_callback:
            threading.Thread(
                target=self.on_restore_callback,
                daemon=True
            ).start()
    
    def show(self):
        """Show the floating widget (thread-safe)"""
        if self.signal_bridge:
            self.signal_bridge.show_widget.emit()
            
    def hide(self):
        """Hide the floating widget (thread-safe)"""
        if self.signal_bridge:
            self.signal_bridge.hide_widget.emit()
            
    def set_status(self, status: str):
        """Update status text (thread-safe)"""
        if self.signal_bridge:
            self.signal_bridge.update_status.emit(status)
            
    def set_listening(self, listening: bool):
        """Update listening state (thread-safe)"""
        if self.signal_bridge:
            self.signal_bridge.update_listening.emit(listening)
            
    def show_response(self, text: str):
        """Show response text (thread-safe)"""
        if self.signal_bridge:
            self.signal_bridge.show_response.emit(text)
            
    def stop(self):
        """Stop the Qt application"""
        if self.app:
            self.app.quit()
        self._running = False


# Global instance
_widget_manager: Optional[FloatingWidgetManager] = None


def get_widget_manager() -> FloatingWidgetManager:
    """Get or create the global widget manager"""
    global _widget_manager
    if _widget_manager is None:
        _widget_manager = FloatingWidgetManager()
    return _widget_manager


def init_floating_widget(on_voice: Optional[Callable] = None,
                         on_restore: Optional[Callable] = None):
    """Initialize and start the floating widget system"""
    manager = get_widget_manager()
    manager.start(on_voice=on_voice, on_restore=on_restore)
    return manager


# Test mode
if __name__ == "__main__":
    def test_voice(listening):
        print(f"Voice callback: listening={listening}")
        
    def test_restore():
        print("Restore callback called")
        
    app = QApplication(sys.argv)
    widget = FloatingWidget(
        on_voice_click=test_voice,
        on_restore_click=test_restore
    )
    widget.show()
    sys.exit(app.exec_())
