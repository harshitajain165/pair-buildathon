import math

from PyQt6.QtCore import Qt, QTimer, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QBrush, QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication, QWidget


COLORS = {
    "ready":     "#666666",
    "listening": "#4A9EFF",
    "thinking":  "#FFB347",
    "speaking":  "#50C878",
    "running":   "#B57BFF",
    "error":     "#FF4C4C",
}


class PairWidget(QWidget):
    _sig = pyqtSignal(str)   # thread-safe bridge

    def __init__(self):
        super().__init__()
        self._status_key  = "ready"
        self._status_text = "Ready"
        self._phase       = 0.0
        self._drag_pos    = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(300, 72)

        # Bottom-right corner
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.width() - 320, screen.height() - 110)

        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)
        self._timer.start(40)   # ~25 fps

        self._sig.connect(self._apply_status)

    # ── Public API (thread-safe) ──────────────────────────────────────────────

    def set_status(self, status: str):
        self._sig.emit(status)

    def run(self):
        pass   # kept for compatibility

    # ── Internal ──────────────────────────────────────────────────────────────

    def _apply_status(self, status: str):
        key = status.split(" ")[0].split(":")[0].lower()
        self._status_key  = key if key in COLORS else "ready"
        self._status_text = status

    def _tick(self):
        self._phase = (self._phase + 0.12) % (2 * math.pi)
        self.update()

    # ── Painting ──────────────────────────────────────────────────────────────

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background pill
        p.setBrush(QColor(14, 14, 16, 230))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, self.width(), self.height(), 18, 18)

        # Subtle border
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QColor(255, 255, 255, 18))
        p.drawRoundedRect(1, 1, self.width() - 2, self.height() - 2, 17, 17)

        color = QColor(COLORS.get(self._status_key, "#666666"))
        cx, cy = 44, self.height() // 2

        if self._status_key in ("listening", "speaking"):
            self._draw_waveform(p, color, cx, cy)
        else:
            self._draw_orb(p, color, cx, cy)

        # Status text
        p.setPen(QColor(230, 230, 230, 210))
        font = QFont("SF Pro Text", 13)
        font.setWeight(QFont.Weight.Medium)
        p.setFont(font)
        label = self._status_text.capitalize()
        if len(label) > 22:
            label = label[:19] + "…"
        p.drawText(80, 0, self.width() - 90, self.height(),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                   label)

    def _draw_orb(self, p: QPainter, color: QColor, cx: int, cy: int):
        if self._status_key == "thinking":
            pulse = 0.4 + 0.6 * abs(math.sin(self._phase))
        elif self._status_key == "ready":
            pulse = 0.85
        else:
            pulse = 0.5 + 0.5 * math.sin(self._phase * 1.5)

        r = int(13 + 4 * (pulse - 0.5))

        # Glow
        glow = QColor(color)
        glow.setAlpha(int(40 * pulse))
        p.setBrush(QBrush(glow))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(cx - r - 9, cy - r - 9, (r + 9) * 2, (r + 9) * 2)

        # Core
        core = QColor(color)
        core.setAlpha(int(180 + 75 * (pulse - 0.5)))
        p.setBrush(QBrush(core))
        p.drawEllipse(cx - r, cy - r, r * 2, r * 2)

    def _draw_waveform(self, p: QPainter, color: QColor, cx: int, cy: int):
        n_bars    = 5
        bar_w     = 4
        bar_gap   = 3
        total_w   = n_bars * bar_w + (n_bars - 1) * bar_gap
        start_x   = cx - total_w // 2

        p.setPen(Qt.PenStyle.NoPen)
        for i in range(n_bars):
            offset = i * (math.pi * 2 / n_bars)
            h = int(8 + 18 * abs(math.sin(self._phase * 2.5 + offset)))
            x = start_x + i * (bar_w + bar_gap)
            y = cy - h // 2
            bar_color = QColor(color)
            bar_color.setAlpha(180 + int(60 * abs(math.sin(self._phase + offset))))
            p.setBrush(QBrush(bar_color))
            p.drawRoundedRect(x, y, bar_w, h, 2, 2)

    # ── Drag ──────────────────────────────────────────────────────────────────

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() == Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, _):
        self._drag_pos = None

    def mouseDoubleClickEvent(self, _):
        QApplication.quit()
