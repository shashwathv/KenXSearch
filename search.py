#!/usr/bin/env python3

import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from shutil import which
from urllib.parse import quote_plus
from typing import Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum

import cv2
import mss
import numpy as np
import pytesseract
from PIL import Image, ImageEnhance
from PyQt6.QtCore import (Qt, QTimer, QPropertyAnimation, QRectF,
                          QEasingCurve, pyqtSignal, QPointF, pyqtProperty)
from PyQt6.QtGui import (QPainter, QPen, QColor, QPixmap, QImage,
                         QBrush, QPainterPath, QGuiApplication)
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget,
                           QHBoxLayout, QPushButton, QLabel, QGraphicsDropShadowEffect)
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# --- Configuration ---
@dataclass
class Config:
    """Configuration settings for Circle to Search"""
    use_freeform_selection: bool = True
    wayland: bool = os.getenv('XDG_SESSION_TYPE', '').lower() == 'wayland'
    desktop: str = os.getenv('XDG_CURRENT_DESKTOP', '').lower()
    temp_dir: Path = Path("/tmp")
    screenshot_path: Path = temp_dir / "circle_to_search_capture.png"
    playwright_user_data_dir: Path = temp_dir / "circle_search_playwright_data"

    # UI Configuration
    selection_color: str = "#4285F4"  # Google Blue
    selection_width: int = 3
    animation_duration: int = 250 # ms
    
    # OCR Configuration
    min_confidence: int = 40
    min_text_length: int = 3
    supported_languages: List[str] = None
    
    def __post_init__(self):
        if self.supported_languages is None:
            self.supported_languages = ['eng', 'spa', 'fra', 'deu', 'ita', 'por', 'rus', 'jpn', 'kor', 'chi_sim']

config = Config()

# --- Search Result Types ---
class SearchType(Enum):
    TEXT = "text"
    IMAGE = "image"
    TRANSLATE = "translate"
    HOMEWORK = "homework"

# --- Modern UI Components ---
class ModernButton(QPushButton):
    """Google-style material design button"""
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #dadce0;
                border-radius: 22px;
                padding: 8px 20px;
                font-family: 'Google Sans', 'Roboto', sans-serif;
                font-size: 14px;
                font-weight: 500;
                color: #3c4043;
                min-height: 32px;
            }
            QPushButton:hover {
                background-color: #f8f9fa;
                border-color: #d2e3fc;
            }
            QPushButton:pressed {
                background-color: #d2e3fc;
                border-color: #4285f4;
            }
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, 1)
        self.setGraphicsEffect(shadow)

class SearchOptionsPanel(QWidget):
    """Bottom panel with search options like Google's implementation"""
    searchRequested = pyqtSignal(SearchType)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(255, 255, 255, 0.98);
                border-radius: 28px;
            }
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 50))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        
        self.text_btn = ModernButton("🔍 Search Text")
        self.image_btn = ModernButton("📷 Visual Search")
        self.translate_btn = ModernButton("🌐 Translate")
        self.homework_btn = ModernButton("📚 Homework")
        
        self.text_btn.clicked.connect(lambda: self.searchRequested.emit(SearchType.TEXT))
        self.image_btn.clicked.connect(lambda: self.searchRequested.emit(SearchType.IMAGE))
        self.translate_btn.clicked.connect(lambda: self.searchRequested.emit(SearchType.TRANSLATE))
        self.homework_btn.clicked.connect(lambda: self.searchRequested.emit(SearchType.HOMEWORK))
        
        layout.addWidget(self.text_btn)
        layout.addWidget(self.image_btn)
        layout.addWidget(self.translate_btn)
        layout.addWidget(self.homework_btn)

# --- Enhanced Overlay with Google-style UI ---
class EnhancedOverlay(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = config
        self.sct = mss.mss() if not self.config.wayland else None
        self.path = QPainterPath()
        self.is_drawing = False
        self.selection_made = False
        self.screenshot_pixmap = None
        self.animation_timer = QTimer(self)
        self.pulse_value = 0
        self.animated_selection_rect = QRectF()
        
        self.setup_ui()
        self.capture_background()
        self.setup_animations()
        
    def setup_ui(self):
        """Setup the Google-style UI"""
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | 
                          Qt.WindowType.WindowStaysOnTopHint |
                          Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        
        screen = QGuiApplication.primaryScreen()
        screen_rect = screen.geometry()
        self.setGeometry(screen_rect)
        
        self.search_panel = SearchOptionsPanel(self)
        self.search_panel.adjustSize()
        panel_width = self.search_panel.width()
        panel_height = self.search_panel.height()
        self.search_panel.setGeometry(
            (screen_rect.width() - panel_width) // 2,
            screen_rect.height() - panel_height - 50,
            panel_width,
            panel_height
        )
        self.search_panel.hide()
        self.search_panel.searchRequested.connect(self.handle_search_request)
        
        self.hint_label = QLabel("Draw a circle around what you want to search", self)
        self.hint_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 0.7);
                color: white;
                padding: 12px 24px;
                border-radius: 24px;
                font-family: 'Google Sans', 'Roboto', sans-serif;
                font-size: 16px;
            }
        """)
        self.hint_label.adjustSize()
        self.hint_label.move(
            (screen_rect.width() - self.hint_label.width()) // 2, 50
        )
        
    def setup_animations(self):
        """Setup animations for pulsing selection effect"""
        self.animation_timer.timeout.connect(self.update_pulse_animation)
        self.animation_timer.start(16)  # ~60 FPS
        
    def update_pulse_animation(self):
        """Update animation values for the pulsing glow"""
        self.pulse_value = (self.pulse_value + 2) % 360
        if self.selection_made:
            self.update()
    
    def get_animated_rect(self):
        return self.animated_selection_rect

    def set_animated_rect(self, rect):
        self.animated_selection_rect = rect
        self.update()

    animated_selection_rect_prop = pyqtProperty(QRectF, get_animated_rect, set_animated_rect)

    def capture_background(self):
        """Capture the current screen as background"""
        try:
            if self.config.wayland:
                temp_path = self.config.temp_dir / "background_capture.png"
                if self.capture_wayland_screen(temp_path):
                    self.screenshot_pixmap = QPixmap(str(temp_path))
                    temp_path.unlink(missing_ok=True)
            else:
                monitor = self.sct.monitors[1] # 1 for primary monitor
                sct_img = self.sct.grab(monitor)
                img = Image.frombytes('RGB', sct_img.size, sct_img.rgb)
                qimg = QImage(img.tobytes(), img.width, img.height, QImage.Format.Format_RGB888)
                self.screenshot_pixmap = QPixmap.fromImage(qimg)
                
        except Exception as e:
            print(f"Error capturing background: {e}", file=sys.stderr)
            
    def capture_wayland_screen(self, output_path: Path) -> bool:
        """Capture screen on Wayland systems using fallback methods"""
        tools = {
            "grim": ["grim", str(output_path)],
            "gnome-screenshot": ["gnome-screenshot", "-f", str(output_path)],
            "spectacle": ["spectacle", "-b", "-n", "-o", str(output_path)],
        }
        for tool, command in tools.items():
            if which(tool):
                try:
                    subprocess.run(command, check=True, capture_output=True, timeout=5)
                    return output_path.exists()
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                    print(f"Failed to capture with {tool}: {e}", file=sys.stderr)
                    continue
        print("No compatible Wayland screenshot tool found.", file=sys.stderr)
        return False
    
    def paintEvent(self, event):
        """Paint the overlay with Google-style effects"""
        if not self.screenshot_pixmap:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.drawPixmap(self.rect(), self.screenshot_pixmap)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 180))
        
        if self.is_drawing or self.selection_made:
            painter.save()

            path_to_draw = QPainterPath()
            bounds = QRectF()
            
            if self.selection_made:
                bounds = self.animated_selection_rect
                path_to_draw.addRoundedRect(bounds, 16, 16)
            else: # is_drawing
                bounds = self.path.boundingRect()
                path_to_draw = self.path

            painter.setClipPath(path_to_draw)
            painter.drawPixmap(self.rect(), self.screenshot_pixmap)
            painter.restore()

            # Draw selection border
            pen = QPen(QColor(self.config.selection_color), self.config.selection_width)
            painter.setPen(pen)
            
            if self.selection_made:
                 # Add pulsing glow effect
                glow_alpha = int(abs(np.sin(np.deg2rad(self.pulse_value))) * 60)
                glow_pen = QPen(QColor(66, 133, 244, glow_alpha), 6)
                painter.setPen(glow_pen)
                painter.drawPath(path_to_draw)
                
                # Draw main border on top
                painter.setPen(pen)
                painter.drawPath(path_to_draw)
                self.draw_corner_handles(painter, bounds)
            else:
                painter.drawPath(self.path)

    def draw_corner_handles(self, painter, rect: QRectF):
        """Draw resize handles at corners of selection (currently cosmetic)"""
        handle_size = 5
        handle_color = QColor(self.config.selection_color)
        painter.setBrush(QBrush(handle_color))
        painter.setPen(Qt.PenStyle.NoPen)
        
        corners = [rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight()]
        for corner in corners:
            painter.drawEllipse(corner, handle_size, handle_size)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_drawing = True
            self.selection_made = False
            self.path = QPainterPath(event.position())
            self.hint_label.hide()
            self.search_panel.hide()
            
    def mouseMoveEvent(self, event):
        if self.is_drawing:
            self.path.lineTo(event.position())
            self.update()
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.is_drawing:
            self.is_drawing = False
            if self.path.elementCount() < 3: # Ignore simple clicks
                self.close()
                QApplication.quit()
                return

            self.selection_made = True
            self.path.closeSubpath()
            self.animate_to_rectangle()
            self.show_search_panel()
            self.capture_selected_area(self.path.boundingRect())
    
    def animate_to_rectangle(self):
        """Animate the freeform path into a stable rectangle."""
        target_rect = self.path.boundingRect()
        
        # Start animation from a slightly smaller, centered rectangle for a "pop" effect
        start_rect = QRectF(target_rect.center(), target_rect.size() * 0.8)
        
        self.animation = QPropertyAnimation(self, b'animated_selection_rect_prop', self)
        self.animation.setDuration(self.config.animation_duration)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.setStartValue(start_rect)
        self.animation.setEndValue(target_rect)
        self.animation.start()
    
    def show_search_panel(self):
        """Show the search options panel with a slide-up animation."""
        self.search_panel.show()
        
        current_rect = self.search_panel.geometry()
        start_rect = self.search_panel.geometry()
        start_rect.moveTop(self.height())
        
        self.panel_animation = QPropertyAnimation(self.search_panel, b"geometry")
        self.panel_animation.setDuration(350)
        self.panel_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.panel_animation.setStartValue(start_rect)
        self.panel_animation.setEndValue(current_rect)
        self.panel_animation.start()
    
    def capture_selected_area(self, rect: QRectF):
        """Capture and save the selected area."""
        try:
            x, y, w, h = [max(0, int(val)) for val in rect.getRect()]
            if self.screenshot_pixmap and w > 0 and h > 0:
                cropped = self.screenshot_pixmap.copy(x, y, w, h)
                cropped.save(str(self.config.screenshot_path))
                print(f"Captured area: {w}x{h} at ({x}, {y})")
        except Exception as e:
            print(f"Error capturing selected area: {e}", file=sys.stderr)
    
    def handle_search_request(self, search_type: SearchType):
        """Handle different search types."""
        if not self.config.screenshot_path.exists():
            print("No screenshot available.", file=sys.stderr)
            return
            
        self.hide()
        
        if search_type == SearchType.TEXT:
            self.perform_text_search()
        elif search_type == SearchType.IMAGE:
            self.perform_visual_search()
        elif search_type == SearchType.TRANSLATE:
            self.perform_translate_search()
        elif search_type == SearchType.HOMEWORK:
            self.perform_homework_search()
            
        QApplication.quit()
    
    def perform_text_search(self):
        """Perform OCR and text search."""
        text = self.extract_text_from_selection()
        if text:
            print(f"Extracted text: {text}")
            search_url = f"https://www.google.com/search?q={quote_plus(text)}"
            webbrowser.open(search_url)
        else:
            print("No text found, falling back to visual search.")
            self.perform_visual_search()
    
    def perform_visual_search(self):
        self.upload_to_google_lens()
    
    def perform_translate_search(self):
        text = self.extract_text_from_selection()
        if text:
            translate_url = f"https://translate.google.com/?sl=auto&tl=en&text={quote_plus(text)}"
            webbrowser.open(translate_url)
        else:
            print("No text found for translation. Please try a visual search.", file=sys.stderr)
    
    def perform_homework_search(self):
        text = self.extract_text_from_selection()
        if text:
            search_url = f"https://www.google.com/search?q=solve {quote_plus(text)}"
            webbrowser.open(search_url)
        else:
            self.perform_visual_search()
    
    def extract_text_from_selection(self) -> Optional[str]:
        """Extract text using the advanced OCRProcessor."""
        print("Performing advanced OCR...")
        text, confidence = OCRProcessor.extract_text_multi_strategy(self.config.screenshot_path)
        
        if text and confidence > self.config.min_confidence and len(text) >= self.config.min_text_length:
            return text
        
        return None
    
    def upload_to_google_lens(self):
        """
        Upload image to Google Lens using a persistent browser context to avoid CAPTCHAs.
        """
        print("Opening Google Lens...")
        print("On first run, you may need to log into Google to prevent CAPTCHAs.")
        
        playwright = None
        browser = None
        try:
            playwright = sync_playwright().start()
            browser = playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.config.playwright_user_data_dir),
                headless=False,
                no_viewport=True,
                args=['--start-maximized']
            )
            
            page = browser.pages[0] if browser.pages else browser.new_page()
            page.goto("https://lens.google.com/upload", wait_until="domcontentloaded", timeout=15000)
            
            file_input = page.locator('input[type="file"]')
            file_input.wait_for(state="attached", timeout=15000)
            
            file_input.set_input_files(str(self.config.screenshot_path))
            page.wait_for_url("**/search?**", timeout=60000)
            
            print("✅ Upload successful!")
            input("   Press Enter in this terminal to close the browser... ")

        except (PlaywrightTimeoutError, Exception) as e:
            print(f"Error uploading to Google Lens: {e}", file=sys.stderr)
        finally:
            if browser and browser.is_connected(): # <-- MODIFIED THIS LINE
                browser.close()
            if playwright:
                playwright.stop()
    
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts."""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            QApplication.quit()
        elif event.key() == Qt.Key.Key_Space and self.selection_made:
            self.handle_search_request(SearchType.TEXT)

# --- OCR Enhancement Functions ---
class OCRProcessor:
    """Advanced OCR processing with multiple strategies"""
    
    @staticmethod
    def preprocess_image(image_path: Path) -> List[Path]:
        """Apply multiple preprocessing techniques and return paths to processed images."""
        processed_paths = []
        try:
            img = cv2.imread(str(image_path))
            if img is None: return [image_path]

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Strategy 1: Adaptive threshold (often best for varied lighting)
            adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                           cv2.THRESH_BINARY, 11, 2)
            path1 = config.temp_dir / "ocr_adaptive.png"
            cv2.imwrite(str(path1), adaptive)
            processed_paths.append(path1)

            # Strategy 2: Simple binary threshold (Otsu's method)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            path2 = config.temp_dir / "ocr_otsu.png"
            cv2.imwrite(str(path2), thresh)
            processed_paths.append(path2)
            
            # Strategy 3: Enhanced contrast before conversion
            enhanced = Image.open(image_path).convert('L')
            enhancer = ImageEnhance.Contrast(enhanced)
            enhanced = enhancer.enhance(2.0)
            path3 = config.temp_dir / "ocr_enhanced.png"
            enhanced.save(path3)
            processed_paths.append(path3)

        except Exception as e:
            print(f"Image preprocessing failed: {e}", file=sys.stderr)
            return [image_path]
            
        return processed_paths
    
    @staticmethod
    def extract_text_multi_strategy(image_path: Path) -> Tuple[str, float]:
        """Extract text using multiple strategies and return the best result."""
        processed_paths = OCRProcessor.preprocess_image(image_path)
        best_text, best_confidence = "", 0.0
        
        for i, path in enumerate(processed_paths):
            try:
                data = pytesseract.image_to_data(
                    Image.open(path),
                    output_type=pytesseract.Output.DICT,
                    config='--oem 3 --psm 6',
                    lang='+'.join(config.supported_languages)
                )
                
                words, confidences = [], []
                for i, word in enumerate(data['text']):
                    if word.strip() and int(data['conf'][i]) > 0:
                        words.append(word)
                        confidences.append(int(data['conf'][i]))
                
                if words and confidences:
                    text = ' '.join(words)
                    avg_conf = sum(confidences) / len(confidences)
                    
                    if avg_conf > best_confidence:
                        best_text, best_confidence = text, avg_conf
                        
            except Exception as e:
                print(f"OCR failed for strategy {i+1}: {e}", file=sys.stderr)
                continue
        
        for path in processed_paths:
            if path != image_path:
                path.unlink(missing_ok=True)
                
        return best_text, best_confidence

# --- Dependency Checker ---
class DependencyChecker:
    """Check for required system and Python dependencies"""
    SYSTEM_PACKAGES = {'tesseract': 'tesseract-ocr', 'grim': 'grim', 'spectacle': 'spectacle'}
    PYTHON_PACKAGES = {'cv2': 'opencv-python', 'mss': 'mss', 'numpy': 'numpy', 'pytesseract': 'pytesseract', 
                       'PIL': 'Pillow', 'PyQt6': 'PyQt6', 'playwright': 'playwright'}
    
    @classmethod
    def check(cls) -> bool:
        """Check all dependencies and print instructions for missing ones."""
        missing_system = [pkg for cmd, pkg in cls.SYSTEM_PACKAGES.items() if not which(cmd)]
        if missing_system:
            print("❌ Missing system dependencies:", ', '.join(missing_system))
            print("\n   Please install them using your package manager, e.g.:")
            print(f"   - Ubuntu/Debian: sudo apt install {' '.join(missing_system)}")
            print(f"   - Fedora: sudo dnf install {' '.join(missing_system)}")
            print(f"   - Arch: sudo pacman -S {' '.join(missing_system)}")
            return False

        missing_python = []
        for import_name, pkg_name in cls.PYTHON_PACKAGES.items():
            try:
                __import__(import_name)
            except ImportError:
                missing_python.append(pkg_name)
        
        if missing_python:
            print("❌ Missing Python packages:", ', '.join(missing_python))
            print(f"\n   Install with: pip install {' '.join(missing_python)}")
            return False
            
        return True

# --- Main Application ---
def main():
    """Main entry point for Circle to Search"""
    if not DependencyChecker.check():
        sys.exit(1)
    
    if config.screenshot_path.exists():
        config.screenshot_path.unlink()
    
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet("QWidget { font-family: 'Google Sans', 'Roboto', 'Segoe UI', sans-serif; }")
    
    overlay = EnhancedOverlay()
    overlay.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()