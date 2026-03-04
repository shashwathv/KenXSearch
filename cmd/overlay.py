from PyQt6.QtWidgets import QMainWindow, QApplication
from PyQt6.QtCore import Qt, QRectF, pyqtProperty, QPropertyAnimation
from PyQt6.QtGui import QPainter, QPen, QColor, QPainterPath
from config import cfg

class LensixOverlay(QMainWindow):
    def __init__(self, bg_pixmap):
        super().__init__()
        self.bg = bg_pixmap
        self.path = QPainterPath()
        self.is_drawing = False
        self._anim_rect = QRectF()
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.showFullScreen()

    def set_anim_rect(self, r): self._anim_rect = r; self.update()
    anim_rect = pyqtProperty(QRectF, fset=set_anim_rect)

    def paintEvent(self, _):
        p = QPainter(self)
        p.drawPixmap(self.rect(), self.bg)
        p.fillRect(self.rect(), QColor(0, 0, 0, cfg.bg_dim))
        
        if not self.path.isEmpty():
            p.save()
            # Draw the 'cutout' through the dark layer
            target = self.path.boundingRect()
            clip = QPainterPath()
            clip.addRoundedRect(target, 12, 12)
            p.setClipPath(clip)
            p.drawPixmap(self.rect(), self.bg)
            p.restore()
            p.setPen(QPen(QColor(cfg.accent), 3))
            p.drawPath(clip)

    def mousePressEvent(self, e): self.path = QPainterPath(e.position()); self.is_drawing = True
    def mouseMoveEvent(self, e): 
        if self.is_drawing: self.path.lineTo(e.position()); self.update()
    def mouseReleaseEvent(self, _):
        self.is_drawing = False
        r = self.path.boundingRect()
        self.bg.copy(int(r.x()), int(r.y()), int(r.width()), int(r.height())).save(str(cfg.crop_out))
        QApplication.quit()