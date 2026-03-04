import os
from pathlib import Path
from dataclasses import dataclass

@dataclass
class Config:
    # 2026 Wayland Detection
    is_wayland: bool = os.getenv('XDG_SESSION_TYPE', '').lower() == 'wayland'
    desktop: str = os.getenv('XDG_CURRENT_DESKTOP', '').lower()
    
    # Paths (Stored in /tmp for speed)
    temp_dir: Path = Path("/tmp/lensix")
    raw_bg: Path = temp_dir / "background.png"
    crop_out: Path = temp_dir / "selection.png"

    # UI Styles (Google-Style)
    accent: str = "#4285F4"  # Google Blue
    bg_dim: int = 170        # Darken factor (0-255)

    def __post_init__(self):
        self.temp_dir.mkdir(parents=True, exist_ok=True)

cfg = Config()