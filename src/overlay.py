"""
KenXSearch Overlay UI - Tech-HUD Edition
Full-screen drawing overlay, techy search panel, and animated selection brackets.
"""

import math
import sys
from pathlib import Path

import mss
from PIL import Image
from PyQt6.QtCore import (Qt, QTimer, QPropertyAnimation, QRectF, QPointF,
                           QEasingCurve, pyqtSignal, pyqtProperty)
from PyQt6.QtGui import (QPainter, QPen, QColor, QPixmap, QImage,
                          QBrush, QPainterPath, QGuiApplication, QFont, QLinearGradient)
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget,
                              QHBoxLayout, QPushButton, QLabel)

from src.config import config, SearchType
import src.lens as lens

# ---------------------------------------------------------------------------
# Tech Button
# ---------------------------------------------------------------------------

class _TechButton(QPushButton):
    """High-tech minimalist button with cyan accents and mono font."""

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self._label   = label
        self._hover   = 0.0
        self._hovered = False
        self._anim    = QTimer(self)
        self._anim.timeout.connect(self._step)
        self.setFixedHeight(40)
        self.setMinimumWidth(120)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFlat(True)

    def _step(self):
        target = 1.0 if self._hovered else 0.0
        self._hover += (target - self._hover) * 0.15
        if abs(self._hover - target) < 0.005:
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

        r = self.rect()
        h = self._hover

        # Dark tech background
        bg_color = QColor(10, 12, 18, int(180 + h * 40))
        p.fillRect(r, bg_color)

        # Tech accent border (Electric Cyan)
        border_color = QColor(0, 242, 255, int(80 + h * 175))
        p.setPen(QPen(border_color, 1.5))
        p.drawRect(r.adjusted(1, 1, -1, -1))

        # Corner accents for buttons
        p.setPen(QPen(QColor(0, 242, 255, int(200 * h)), 2))
        l = 6
        p.drawLine(0, 0, l, 0)
        p.drawLine(0, 0, 0, l)
        p.drawLine(r.width(), r.height(), r.width()-l, r.height())
        p.drawLine(r.width(), r.height(), r.width(), r.height()-l)

        # Label — monospace uppercase with font fallback chain
        f = QFont()
        f.setFamilies(["JetBrains Mono", "Fira Mono", "DejaVu Sans Mono", "Courier New", "monospace"])
        f.setPointSize(9)
        f.setBold(True)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.5)
        p.setFont(f)
        p.setPen(QColor(0, 242, 255, int(180 + h * 75)))
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, self._label.upper())


# ---------------------------------------------------------------------------
# Search panel
# ---------------------------------------------------------------------------
class SearchOptionsPanel(QWidget):
    """Floating tech buttons."""
    searchRequested = pyqtSignal(SearchType)

    _BUTTONS = [
        ("Search",    SearchType.TEXT),
        ("Visual",    SearchType.IMAGE),
        ("Translate", SearchType.TRANSLATE),
        ("Shopping",  SearchType.SHOPPING),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(12)

        for label, stype in self._BUTTONS:
            btn = _TechButton(label, self)
            btn.clicked.connect(lambda _c, s=stype: self.searchRequested.emit(s))
            layout.addWidget(btn)

    def paintEvent(self, _):
        pass


# ---------------------------------------------------------------------------
# Full-screen overlay
# ---------------------------------------------------------------------------

class EnhancedOverlay(QMainWindow):
    """Tech-HUD drawing overlay."""

    def __init__(self):
        super().__init__()
        self.path                    = QPainterPath()
        self.is_drawing              = False
        self.selection_made          = False
        self.screenshot_pixmap       = None
        self.animation_timer         = QTimer(self)
        self.pulse_value             = 0.0
        self.animated_selection_rect = QRectF()

        self._setup_ui()
        self._capture_background()
        self._setup_animations()

    def _setup_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
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
            screen_rect.height() - sh - 60,
            sw, sh,
        )
        self.search_panel.hide()
        self.search_panel.searchRequested.connect(self._handle_search)

        # Hint label — font fallback chain for all distros
        self.hint_label = QLabel("TERMINAL INITIALIZED // CIRCLE AREA TO ANALYZE", self)
        self.hint_label.setStyleSheet("""
            QLabel {
                background: rgba(10, 12, 18, 230);
                color: #00f2ff;
                padding: 12px 30px;
                font-size: 13px;
                font-family: 'JetBrains Mono', 'Fira Mono', 'DejaVu Sans Mono', 'Courier New', monospace;
                border: 1px solid #00f2ff;
                letter-spacing: 1px;
            }
        """)
        self.hint_label.adjustSize()
        self.hint_label.move(
            (screen_rect.width() - self.hint_label.width()) // 2, 60
        )

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def showEvent(self, event):
        super().showEvent(event)
        self.activateWindow()
        self.raise_()
        self.setFocus()

    def _setup_animations(self):
        self.animation_timer.timeout.connect(self._tick)
        self.animation_timer.start(16)

    def _get_rect(self):
        return self.animated_selection_rect

    def _set_rect(self, rect):
        self.animated_selection_rect = rect
        self.update()

    animated_selection_rect_prop = pyqtProperty(QRectF, _get_rect, _set_rect)

    def _capture_background(self):
        """
        Capture using mss via XWayland — works on all distros (Fedora, Ubuntu,
        Arch, KDE, GNOME) without spawning gnome-screenshot, which takes 1-2s
        and causes the Wayland activation token to expire before the window shows.
        PyQt6 runs under XWayland by default so mss always works.
        """
        try:
            sct  = mss.mss()
            simg = sct.grab(sct.monitors[1])
            img  = Image.frombytes('RGB', simg.size, simg.rgb)
            qimg = QImage(img.tobytes(), img.width, img.height,
                          QImage.Format.Format_RGB888)
            self.screenshot_pixmap = QPixmap.fromImage(qimg)
        except Exception as e:
            print(f"Capture error: {e}", file=sys.stderr)

    def _tick(self):
        self.pulse_value = (self.pulse_value + 2.5) % 360
        if self.selection_made or self.is_drawing:
            self.update()

    def paintEvent(self, _):
        if not self.screenshot_pixmap:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        p.drawPixmap(self.rect(), self.screenshot_pixmap)
        p.fillRect(self.rect(), QColor(5, 8, 15, 200))

        if not (self.is_drawing or self.selection_made):
            return

        if self.selection_made:
            clip = QPainterPath()
            clip.addRect(self.animated_selection_rect)
        else:
            clip = self.path

        p.save()
        p.setClipPath(clip)
        p.drawPixmap(self.rect(), self.screenshot_pixmap)
        p.restore()

        if self.selection_made:
            self._draw_hud(p, self.animated_selection_rect)
        else:
            self._draw_stroke(p)

    def _draw_hud(self, p: QPainter, rect: QRectF):
        # 1. Scanning line
        scan_y = rect.top() + (self.pulse_value / 360.0) * rect.height()
        scan_grad = QLinearGradient(0, scan_y - 15, 0, scan_y)
        scan_grad.setColorAt(0, QColor(0, 242, 255, 0))
        scan_grad.setColorAt(1, QColor(0, 242, 255, 120))
        p.fillRect(QRectF(rect.left(), scan_y - 2, rect.width(), 2), QBrush(scan_grad))

        # 2. Tech corner brackets
        p.setPen(QPen(QColor(0, 242, 255, 220), 2))
        l = 20
        p.drawLine(rect.left(),  rect.top(),    rect.left() + l, rect.top())
        p.drawLine(rect.left(),  rect.top(),    rect.left(),     rect.top() + l)
        p.drawLine(rect.right(), rect.top(),    rect.right() - l, rect.top())
        p.drawLine(rect.right(), rect.top(),    rect.right(),    rect.top() + l)
        p.drawLine(rect.left(),  rect.bottom(), rect.left() + l, rect.bottom())
        p.drawLine(rect.left(),  rect.bottom(), rect.left(),     rect.bottom() - l)
        p.drawLine(rect.right(), rect.bottom(), rect.right() - l, rect.bottom())
        p.drawLine(rect.right(), rect.bottom(), rect.right(),    rect.bottom() - l)

        # 3. Data readouts
        f = QFont()
        f.setFamilies(["JetBrains Mono", "Fira Mono", "DejaVu Sans Mono", "Courier New", "monospace"])
        f.setPointSize(8)
        p.setFont(f)
        p.setPen(QColor(0, 242, 255, 180))
        p.drawText(rect.bottomRight() + QPointF(8, 0),
                   f"RES: {int(rect.width())}x{int(rect.height())}")
        p.drawText(rect.topLeft() - QPointF(0, 8),
                   f"LOC: {int(rect.x())},{int(rect.y())}")

        # 4. Subtle outer glow
        p.setPen(QPen(QColor(0, 242, 255, 40), 1))
        p.drawRect(rect)

    def _draw_stroke(self, p: QPainter):
        p.setPen(QPen(QColor(0, 242, 255, 180), 1.5))
        p.drawPath(self.path)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_drawing     = True
            self.selection_made = False
            self.path           = QPainterPath(event.position())
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
                QApplication.quit()
                return
            self.selection_made = True
            self.path.closeSubpath()
            self._animate_to_rect()
            self._show_panel()
            self._save_selection(self.path.boundingRect())

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            QApplication.quit()

    def _animate_to_rect(self):
        target = self.path.boundingRect()
        start  = QRectF(target.center(), target.size() * 0.9)
        self._anim = QPropertyAnimation(self, b'animated_selection_rect_prop', self)
        self._anim.setDuration(300)
        self._anim.setEasingCurve(QEasingCurve.Type.OutExpo)
        self._anim.setStartValue(start)
        self._anim.setEndValue(target)
        self._anim.start()

    def _show_panel(self):
        self.search_panel.show()
        end   = self.search_panel.geometry()
        start = self.search_panel.geometry()
        start.moveTop(self.height())
        self._panel_anim = QPropertyAnimation(self.search_panel, b"geometry")
        self._panel_anim.setDuration(400)
        self._panel_anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self._panel_anim.setStartValue(start)
        self._panel_anim.setEndValue(end)
        self._panel_anim.start()

    def _save_selection(self, rect: QRectF):
        try:
            x, y, w, h = [max(0, int(v)) for v in rect.getRect()]
            if self.screenshot_pixmap and w > 0 and h > 0:
                self.screenshot_pixmap.copy(x, y, w, h).save(str(config.screenshot_path))
        except Exception as e:
            print(f"Error saving selection: {e}", file=sys.stderr)

    def _handle_search(self, search_type: SearchType):
        if not config.screenshot_path.exists():
            return
        self.hide()
        lens.dispatch(search_type)
        QApplication.quit()