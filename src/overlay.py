"""
Lensix Overlay UI
Full-screen drawing overlay, search panel, and animated selection ring.
"""

import math
import subprocess
import sys
from pathlib import Path
from shutil import which

import mss
from PIL import Image
from PyQt6.QtCore import (Qt, QTimer, QPropertyAnimation, QRectF,
                           QEasingCurve, pyqtSignal, pyqtProperty)
from PyQt6.QtGui import (QPainter, QPen, QColor, QPixmap, QImage,
                          QBrush, QPainterPath, QGuiApplication, QFont)
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget,
                              QHBoxLayout, QPushButton, QLabel)

from src.config import config, SearchType
import src.lens as lens


# ---------------------------------------------------------------------------
# Button
# ---------------------------------------------------------------------------

class _PillButton(QPushButton):
    """Professional button: accent dot + label, no emojis."""

    ACCENTS = {
        "Search":    (66,  133, 244),   # Blue
        "Visual":    (52,  168,  83),   # Green
        "Translate": (251, 188,   5),   # Yellow
        "Shopping":  (234,  67,  53),   # Red
    }

    def __init__(self, key: str, label: str, parent=None):
        super().__init__(parent)
        self._key     = key
        self._label   = label
        self._rgb     = self.ACCENTS.get(key, (66, 133, 244))
        self._hover   = 0.0
        self._hovered = False
        self._anim    = QTimer(self)
        self._anim.timeout.connect(self._step)
        self.setFixedHeight(44)
        self.setMinimumWidth(118)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFlat(True)

    def _step(self):
        target = 1.0 if self._hovered else 0.0
        self._hover += (target - self._hover) * 0.22
        if abs(self._hover - target) < 0.008:
            self._hover = target
            self._anim.stop()
        self.update()

    def enterEvent(self, e):
        self._hovered = True
        self._anim.start(16)

    def leaveEvent(self, e):
        self._hovered = False
        self._anim.start(16)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        r   = self.rect()
        rad = 10.0
        h   = self._hover
        rv, gv, bv = self._rgb

        # Background — dark base with accent wash on hover
        bg = QPainterPath()
        bg.addRoundedRect(float(r.x()), float(r.y()),
                          float(r.width()), float(r.height()), rad, rad)
        p.fillPath(bg, QBrush(QColor(20, 20, 28, int(200 + h * 30))))
        if h > 0.01:
            p.fillPath(bg, QBrush(QColor(rv, gv, bv, int(h * 28))))

        # Border: dim white → accent colour on hover
        br = int(255 * (1 - h) + rv * h)
        bg_ = int(255 * (1 - h) + gv * h)
        bb  = int(255 * (1 - h) + bv * h)
        p.setPen(QPen(QColor(br, bg_, bb, int(38 + h * 180)), 1.1))
        p.drawPath(bg)

        # Accent dot (replaces emoji)
        dot_r = 4.5 + h * 1.0
        dot_x = float(r.left() + 18)
        dot_y = float(r.center().y())
        p.setBrush(QBrush(QColor(rv, gv, bv, int(200 + h * 55))))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(int(dot_x - dot_r), int(dot_y - dot_r),
                      int(dot_r * 2), int(dot_r * 2))

        # Label
        f = QFont("Noto Sans", 12)
        f.setWeight(QFont.Weight.Medium)
        p.setFont(f)
        p.setPen(QColor(255, 255, 255, int(160 + h * 95)))
        p.drawText(r.adjusted(32, 0, -8, 0),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                   self._label)


# ---------------------------------------------------------------------------
# Search panel
# ---------------------------------------------------------------------------

class SearchOptionsPanel(QWidget):
    """Floating dark glass bar that slides up from the bottom."""
    searchRequested = pyqtSignal(SearchType)

    _BUTTONS = [
        ("Search",    "Search",    SearchType.TEXT),
        ("Visual",    "Visual",    SearchType.IMAGE),
        ("Translate", "Translate", SearchType.TRANSLATE),
        ("Shopping",  "Shopping",  SearchType.SHOPPING),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)

        for key, label, stype in self._BUTTONS:
            btn = _PillButton(key, label, self)
            btn.clicked.connect(lambda _c, s=stype: self.searchRequested.emit(s))
            layout.addWidget(btn)

    def paintEvent(self, _):
        p   = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r   = self.rect()
        rad = 16.0

        path = QPainterPath()
        path.addRoundedRect(float(r.x()), float(r.y()),
                            float(r.width()), float(r.height()), rad, rad)

        p.fillPath(path, QBrush(QColor(10, 10, 18, 230)))
        p.setPen(QPen(QColor(255, 255, 255, 28), 1.0))
        p.drawPath(path)

        # Subtle inner top highlight for glass depth
        inner = QPainterPath()
        inner.addRoundedRect(float(r.x()) + 1, float(r.y()) + 1,
                             float(r.width()) - 2, float(r.height() / 2), rad, rad)
        p.fillPath(inner, QBrush(QColor(255, 255, 255, 7)))


# ---------------------------------------------------------------------------
# Full-screen overlay
# ---------------------------------------------------------------------------

class EnhancedOverlay(QMainWindow):
    """Transparent full-screen drawing overlay."""

    def __init__(self):
        super().__init__()
        self.path             = QPainterPath()
        self.is_drawing       = False
        self.selection_made   = False
        self.screenshot_pixmap = None
        self.animation_timer  = QTimer(self)
        self.pulse_value      = 0.0
        self.animated_selection_rect = QRectF()
        self._trail: list     = []

        self._setup_ui()
        self._capture_background()
        self._setup_animations()

    # ------------------------------------------------------------------ setup

    def _setup_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)

        screen      = QGuiApplication.primaryScreen()
        screen_rect = screen.geometry()
        self.setGeometry(screen_rect)

        # Search panel
        self.search_panel = SearchOptionsPanel(self)
        self.search_panel.adjustSize()
        sw, sh = self.search_panel.width(), self.search_panel.height()
        self.search_panel.setGeometry(
            (screen_rect.width() - sw) // 2,
            screen_rect.height() - sh - 40,
            sw, sh,
        )
        self.search_panel.hide()
        self.search_panel.searchRequested.connect(self._handle_search)

        # Hint label
        self.hint_label = QLabel("✦  Circle anything to search", self)
        self.hint_label.setStyleSheet("""
            QLabel {
                background: rgba(10, 10, 14, 200);
                color: rgba(255,255,255,220);
                padding: 10px 26px;
                border-radius: 20px;
                font-size: 15px;
                font-family: 'Noto Sans', 'Segoe UI', sans-serif;
                font-weight: 500;
                border: 1px solid rgba(255,255,255,25);
                letter-spacing: 0.5px;
            }
        """)
        self.hint_label.adjustSize()
        self.hint_label.move(
            (screen_rect.width() - self.hint_label.width()) // 2, 44
        )

    def _setup_animations(self):
        self.animation_timer.timeout.connect(self._tick)
        self.animation_timer.start(16)  # 60 fps

    # ---------------------------------------------------------------- property

    def _get_rect(self):
        return self.animated_selection_rect

    def _set_rect(self, rect):
        self.animated_selection_rect = rect
        self.update()

    animated_selection_rect_prop = pyqtProperty(QRectF, _get_rect, _set_rect)

    # ---------------------------------------------------------------- capture

    def _capture_background(self):
        try:
            if config.wayland:
                tmp = config.temp_dir / "background_capture.png"
                if self._capture_wayland(tmp):
                    self.screenshot_pixmap = QPixmap(str(tmp))
                    tmp.unlink(missing_ok=True)
            else:
                sct  = mss.mss()
                simg = sct.grab(sct.monitors[1])
                img  = Image.frombytes('RGB', simg.size, simg.rgb)
                qimg = QImage(img.tobytes(), img.width, img.height,
                              QImage.Format.Format_RGB888)
                self.screenshot_pixmap = QPixmap.fromImage(qimg)
        except Exception as e:
            print(f"Error capturing background: {e}", file=sys.stderr)

    def _capture_wayland(self, output_path: Path) -> bool:
        tools = {
            "grim":             ["grim", str(output_path)],
            "gnome-screenshot": ["gnome-screenshot", "-f", str(output_path)],
            "spectacle":        ["spectacle", "-b", "-n", "-o", str(output_path)],
        }
        for tool, cmd in tools.items():
            if which(tool):
                try:
                    subprocess.run(cmd, check=True, capture_output=True, timeout=5)
                    return output_path.exists()
                except Exception as e:
                    print(f"Failed to capture with {tool}: {e}", file=sys.stderr)
        return False

    # ---------------------------------------------------------------- animation

    def _tick(self):
        self.pulse_value = (self.pulse_value + 1.8) % 360
        if self.selection_made or self.is_drawing:
            self.update()

    # ---------------------------------------------------------------- painting

    def paintEvent(self, _):
        if not self.screenshot_pixmap:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        p.drawPixmap(self.rect(), self.screenshot_pixmap)
        p.fillRect(self.rect(), QColor(0, 0, 0, 160))

        if not (self.is_drawing or self.selection_made):
            return

        # Clip path — rounded rect when settled, freehand path while drawing
        if self.selection_made:
            clip = QPainterPath()
            clip.addRoundedRect(self.animated_selection_rect, 14, 14)
        else:
            clip = self.path

        # Reveal sharp screenshot inside selection
        p.save()
        p.setClipPath(clip)
        p.drawPixmap(self.rect(), self.screenshot_pixmap)
        p.restore()

        if self.selection_made:
            self._draw_glow(p, clip, self.animated_selection_rect)
        else:
            self._draw_stroke(p)

    def _draw_glow(self, p: QPainter, clip: QPainterPath, rect: QRectF):
        t     = self.pulse_value
        outer = abs(math.sin(math.radians(t)))
        inner = abs(math.sin(math.radians(t + 60)))

        p.setPen(QPen(QColor(66, 133, 244, int(outer * 35)), 12))
        p.drawPath(clip)
        p.setPen(QPen(QColor(100, 160, 255, int(outer * 80)), 5))
        p.drawPath(clip)
        p.setPen(QPen(QColor(180, 210, 255, int(160 + inner * 80)), 1.8))
        p.drawPath(clip)
        self._draw_corner_dots(p, rect, inner)

    def _draw_corner_dots(self, p: QPainter, rect: QRectF, pulse: float):
        size = 5 + pulse * 2
        p.setBrush(QBrush(QColor(140, 195, 255, int(180 + pulse * 75))))
        p.setPen(Qt.PenStyle.NoPen)
        for corner in [rect.topLeft(), rect.topRight(),
                       rect.bottomLeft(), rect.bottomRight()]:
            p.drawEllipse(corner, size, size)

    def _draw_stroke(self, p: QPainter):
        gpen = QPen(QColor(66, 133, 244, 50), 8)
        gpen.setCapStyle(Qt.PenCapStyle.RoundCap)
        gpen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(gpen)
        p.drawPath(self.path)

        core = QPen(QColor(180, 215, 255, 220), 2.2)
        core.setCapStyle(Qt.PenCapStyle.RoundCap)
        core.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(core)
        p.drawPath(self.path)

    # ---------------------------------------------------------------- mouse

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_drawing     = True
            self.selection_made = False
            self.path           = QPainterPath(event.position())
            self._trail         = [event.position()]
            self.hint_label.hide()
            self.search_panel.hide()

    def mouseMoveEvent(self, event):
        if self.is_drawing:
            self.path.lineTo(event.position())
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.is_drawing:
            self.is_drawing = False
            if self.path.elementCount() < 3:
                self.close()
                QApplication.quit()
                return
            self.selection_made = True
            self.path.closeSubpath()
            self._animate_to_rect()
            self._show_panel()
            self._save_selection(self.path.boundingRect())

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            QApplication.quit()
        elif event.key() == Qt.Key.Key_Space and self.selection_made:
            self._handle_search(SearchType.TEXT)

    # ---------------------------------------------------------------- helpers

    def _animate_to_rect(self):
        target = self.path.boundingRect()
        start  = QRectF(target.center(), target.size() * 0.85)
        self._anim = QPropertyAnimation(self, b'animated_selection_rect_prop', self)
        self._anim.setDuration(config.animation_duration)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.setStartValue(start)
        self._anim.setEndValue(target)
        self._anim.start()

    def _show_panel(self):
        self.search_panel.show()
        end   = self.search_panel.geometry()
        start = self.search_panel.geometry()
        start.moveTop(self.height())
        self._panel_anim = QPropertyAnimation(self.search_panel, b"geometry")
        self._panel_anim.setDuration(380)
        self._panel_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._panel_anim.setStartValue(start)
        self._panel_anim.setEndValue(end)
        self._panel_anim.start()

    def _save_selection(self, rect: QRectF):
        try:
            x, y, w, h = [max(0, int(v)) for v in rect.getRect()]
            if self.screenshot_pixmap and w > 0 and h > 0:
                self.screenshot_pixmap.copy(x, y, w, h).save(
                    str(config.screenshot_path)
                )
                print(f"Captured area: {w}x{h} at ({x}, {y})")
        except Exception as e:
            print(f"Error capturing selected area: {e}", file=sys.stderr)

    def _handle_search(self, search_type: SearchType):
        if not config.screenshot_path.exists():
            print("No screenshot available.", file=sys.stderr)
            return
        self.hide()
        lens.dispatch(search_type)
        QApplication.quit()