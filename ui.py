import math

from PyQt6.QtCore import Qt, QTimer, QPointF, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QColor, QBrush, QFont, QPen,
    QConicalGradient, QLinearGradient,
)
from PyQt6.QtWidgets import QApplication, QWidget


class PairWidget(QWidget):
    _sig = pyqtSignal(str)

    # Siri gradient stops (purple → blue → cyan → pink → purple)
    _SIRI = ["#8B5CF6", "#3B82F6", "#06B6D4", "#EC4899", "#8B5CF6"]

    # Waveform bar colors
    _BAR_COLORS = ["#8B5CF6", "#6EA8FE", "#06B6D4", "#EC4899", "#A78BFA"]

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

        # Bottom center, 28px above dock
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = screen.height() - self.height() - 28
        self.move(x, y)

        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)   # ~30 fps

        self._sig.connect(self._apply_status)

    def set_status(self, status: str):
        self._sig.emit(status)

    def run(self):
        pass

    def _apply_status(self, status: str):
        key = status.split(" ")[0].split(":")[0].lower()
        valid = {"ready", "listening", "thinking", "speaking", "running", "error"}
        self._status_key  = key if key in valid else "ready"
        self._status_text = status

    def _tick(self):
        speed = 0.10 if self._status_key in ("speaking", "thinking") else 0.07
        self._phase = (self._phase + speed) % (2 * math.pi)
        self.update()

    # ── Painting ─────────────────────────────────────────────────────────────

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w, h, r = self.width(), self.height(), 22

        # Drop shadow — lighter to suit semi-transparent pill
        p.setBrush(QColor(0, 0, 0, 14))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(4, 7, w - 8, h - 4, r, r)

        # Frosted glass pill — semi-transparent white with slight cool tint
        p.setBrush(QColor(245, 245, 255, 155))
        p.setPen(QPen(QColor(180, 180, 210, 60), 1.0))
        p.drawRoundedRect(0, 2, w, h - 2, r, r)

        # Inner highlight (top edge)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 120), 1.0))
        p.drawRoundedRect(1, 3, w - 2, h - 4, r - 1, r - 1)

        # Content
        cx, cy = 46, h // 2 + 1
        if self._status_key in ("listening", "speaking"):
            self._draw_waveform(p, cx, cy)
        else:
            self._draw_siri_orb(p, cx, cy)

        # Status text
        label = self._status_text.capitalize()
        if len(label) > 20:
            label = label[:17] + "…"

        font = QFont("-apple-system", 13)
        font.setWeight(QFont.Weight.Medium)
        p.setFont(font)
        p.setPen(QColor(29, 29, 31, 230))
        p.drawText(
            84, 0, w - 92, h,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            label,
        )

    def _draw_siri_orb(self, p: QPainter, cx: int, cy: int):
        if self._status_key == "ready":
            pulse = 0.88 + 0.12 * math.sin(self._phase)
        elif self._status_key == "thinking":
            pulse = 0.7 + 0.3 * abs(math.sin(self._phase * 1.6))
        else:
            pulse = 0.75 + 0.25 * abs(math.sin(self._phase))

        r = int(22 * pulse)

        # Soft outer glow rings
        for radius_extra, alpha in [(16, 10), (10, 18), (5, 28)]:
            gr = r + radius_extra
            c = QColor("#8B5CF6")
            c.setAlpha(alpha)
            p.setBrush(c)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(cx - gr, cy - gr, gr * 2, gr * 2)

        # Rotating Siri conic gradient
        angle = (self._phase * 360 / (2 * math.pi) * 2) % 360
        grad = QConicalGradient(QPointF(cx, cy), angle)
        for i, hex_color in enumerate(self._SIRI):
            grad.setColorAt(i / (len(self._SIRI) - 1), QColor(hex_color))

        p.setBrush(QBrush(grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        # Soft white center highlight for depth
        highlight = QLinearGradient(cx - r, cy - r, cx + r, cy + r)
        highlight.setColorAt(0.0, QColor(255, 255, 255, 90))
        highlight.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(QBrush(highlight))
        p.drawEllipse(cx - r, cy - r, r * 2, r * 2)

    def _draw_waveform(self, p: QPainter, cx: int, cy: int):
        n, bw, gap = 5, 4, 5
        total = n * bw + (n - 1) * gap
        sx = cx - total // 2

        speed = 2.8 if self._status_key == "listening" else 2.2
        p.setPen(Qt.PenStyle.NoPen)

        for i in range(n):
            offset = i * (math.pi * 2 / n)
            bar_h = int(10 + 22 * abs(math.sin(self._phase * speed + offset)))
            x = sx + i * (bw + gap)
            y = cy - bar_h // 2
            c = QColor(self._BAR_COLORS[i])
            c.setAlpha(190 + int(55 * abs(math.sin(self._phase + offset))))
            p.setBrush(c)
            p.drawRoundedRect(x, y, bw, bar_h, 2, 2)

    # ── Drag ─────────────────────────────────────────────────────────────────

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
