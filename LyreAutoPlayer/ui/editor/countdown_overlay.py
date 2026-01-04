# ui/editor/countdown_overlay.py
# Transparent countdown overlay widget for auto-pause feature

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtGui import QFont, QPainter, QColor


class CountdownOverlay(QWidget):
    """Transparent overlay showing countdown before auto-resume.

    Displays a large countdown number with a semi-transparent dark background.
    Mouse events pass through to the underlying widget.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # Make mouse events pass through
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Countdown number label
        self.lbl_countdown = QLabel()
        self.lbl_countdown.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_countdown.setFont(QFont("Arial", 96, QFont.Weight.Bold))
        self.lbl_countdown.setStyleSheet("color: rgba(255, 200, 50, 220);")
        layout.addWidget(self.lbl_countdown)

        # Hint label
        self.lbl_hint = QLabel("Press F5 to continue")
        self.lbl_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_hint.setStyleSheet("color: rgba(255, 255, 255, 180); font-size: 18px;")
        layout.addWidget(self.lbl_hint)

        self.hide()

    def show_countdown(self, seconds: int):
        """Display the countdown number.

        Args:
            seconds: Number of seconds remaining. 0 shows "Ready".
        """
        if seconds > 0:
            self.lbl_countdown.setText(str(seconds))
        else:
            self.lbl_countdown.setText("Ready")
        self.show()
        self.raise_()

    def hide_countdown(self):
        """Hide the overlay."""
        self.hide()

    def update_hint_text(self, text: str):
        """Update the hint text (for i18n)."""
        self.lbl_hint.setText(text)

    def paintEvent(self, event):
        """Draw semi-transparent dark background."""
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 160))
        super().paintEvent(event)
