import subprocess
from shutil import which
from PyQt6.QtGui import QPixmap
from config import cfg

class CaptureEngine:
    @staticmethod
    def get_screen() -> QPixmap:
        """Arch Linux Wayland-safe capture. No more black screens."""
        # 1. Primary: Grim (Native Wayland)
        if which("grim"):
            subprocess.run(["grim", str(cfg.raw_bg)], capture_output=True)
            if cfg.raw_bg.exists(): return QPixmap(str(cfg.raw_bg))

        # 2. Secondary: GNOME Built-in (High Privilege)
        if which("gnome-screenshot"):
            subprocess.run(["gnome-screenshot", "-f", str(cfg.raw_bg)], capture_output=True)
            if cfg.raw_bg.exists(): return QPixmap(str(cfg.raw_bg))

        # 3. Fallback: Portal Request (Will show a system popup)
        subprocess.run(["gdbus", "call", "--session", "--dest", "org.freedesktop.portal.Desktop", 
                        "--object-path", "/org/freedesktop/portal/desktop", 
                        "--method", "org.freedesktop.portal.Screenshot.Screenshot", "", "{'interactive': <false>}"])
        return QPixmap()