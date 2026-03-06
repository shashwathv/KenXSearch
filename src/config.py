from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List
import os


@dataclass
class Config:
    """All configuration settings for Lensix."""
    use_freeform_selection: bool = True
    desktop: str = os.getenv('XDG_CURRENT_DESKTOP', '').lower()
    temp_dir: Path = Path("/tmp")
    screenshot_path: Path = temp_dir / "circle_to_search_capture.png"
    playwright_user_data_dir: Path = temp_dir / "circle_search_playwright_data"

    # UI
    selection_color: str = "#4285F4"
    selection_width: int = 3
    animation_duration: int = 250  # ms

    # OCR
    min_confidence: int = 40
    min_text_length: int = 3
    supported_languages: List[str] = None

    def __post_init__(self):
        if self.supported_languages is None:
            self.supported_languages = [
                'eng', 'spa', 'fra', 'deu', 'ita',
                'por', 'rus', 'jpn', 'kor', 'chi_sim',
            ]


class SearchType(Enum):
    TEXT      = "text"
    IMAGE     = "image"
    TRANSLATE = "translate"
    SHOPPING  = "shopping"


# Single shared instance used across all modules
config = Config()