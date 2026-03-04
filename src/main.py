"""
Lensix Entry Point
Dependency checking and application startup.
"""

import sys
from shutil import which

from PyQt6.QtWidgets import QApplication

from src.config import config
from src.overlay import EnhancedOverlay


class DependencyChecker:
    """Verify required system tools and Python packages are available."""

    SYSTEM = {
        'tesseract': 'tesseract-ocr',
    }
    PYTHON = {
        'cv2':         'opencv-python',
        'mss':         'mss',
        'numpy':       'numpy',
        'pytesseract': 'pytesseract',
        'PIL':         'Pillow',
        'PyQt6':       'PyQt6',
        'playwright':  'playwright',
    }

    @classmethod
    def check(cls) -> bool:
        missing_sys = [pkg for cmd, pkg in cls.SYSTEM.items() if not which(cmd)]
        if missing_sys:
            print("❌ Missing system dependencies:", ', '.join(missing_sys))
            print("\n   Install with your package manager, e.g.:")
            print(f"   Ubuntu/Debian : sudo apt install {' '.join(missing_sys)}")
            print(f"   Fedora        : sudo dnf install {' '.join(missing_sys)}")
            print(f"   Arch          : sudo pacman -S {' '.join(missing_sys)}")
            return False

        missing_py = []
        for mod, pkg in cls.PYTHON.items():
            try:
                __import__(mod)
            except ImportError:
                missing_py.append(pkg)

        if missing_py:
            print("❌ Missing Python packages:", ', '.join(missing_py))
            print(f"\n   Install with: pip install {' '.join(missing_py)}")
            return False

        return True


def main():
    if not DependencyChecker.check():
        sys.exit(1)

    if config.screenshot_path.exists():
        config.screenshot_path.unlink()

    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(
        "QWidget { font-family: 'Noto Sans', 'Segoe UI', sans-serif; }"
    )

    overlay = EnhancedOverlay()
    # Show the window IMMEDIATELY so it claims the Wayland activation token.
    # _capture_background() already ran synchronously via mss (<50ms) so
    # by the time show() is called the screenshot is ready — but show() must
    # happen before the event loop starts to avoid token expiry.
    overlay.show()
    overlay.activateWindow()
    overlay.raise_()
    sys.exit(app.exec())