"""
Lensix OCR
Multi-strategy text extraction using Tesseract + OpenCV preprocessing.
"""

import sys
from pathlib import Path
from typing import List, Tuple

import cv2
import pytesseract
from PIL import Image, ImageEnhance

from cmd.config import config


class OCRProcessor:
    """Advanced OCR with multiple image preprocessing strategies."""

    @staticmethod
    def preprocess_image(image_path: Path) -> List[Path]:
        """Return a list of preprocessed image variants to try OCR on."""
        processed = []
        try:
            img = cv2.imread(str(image_path))
            if img is None:
                return [image_path]

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Strategy 1: Adaptive threshold — best for varied lighting
            adaptive = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2,
            )
            p1 = config.temp_dir / "ocr_adaptive.png"
            cv2.imwrite(str(p1), adaptive)
            processed.append(p1)

            # Strategy 2: Otsu binary threshold
            _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            p2 = config.temp_dir / "ocr_otsu.png"
            cv2.imwrite(str(p2), otsu)
            processed.append(p2)

            # Strategy 3: Contrast-enhanced grayscale
            enhanced = ImageEnhance.Contrast(Image.open(image_path).convert('L')).enhance(2.0)
            p3 = config.temp_dir / "ocr_enhanced.png"
            enhanced.save(p3)
            processed.append(p3)

        except Exception as e:
            print(f"Image preprocessing failed: {e}", file=sys.stderr)
            return [image_path]

        return processed

    @staticmethod
    def extract_text_multi_strategy(image_path: Path) -> Tuple[str, float]:
        """Run OCR with all strategies; return (best_text, confidence)."""
        processed = OCRProcessor.preprocess_image(image_path)
        best_text, best_conf = "", 0.0
        lang = '+'.join(config.supported_languages)

        for i, path in enumerate(processed):
            try:
                data = pytesseract.image_to_data(
                    Image.open(path),
                    output_type=pytesseract.Output.DICT,
                    config='--oem 3 --psm 6',
                    lang=lang,
                )
                words, confs = [], []
                for j, word in enumerate(data['text']):
                    if word.strip() and int(data['conf'][j]) > 0:
                        words.append(word)
                        confs.append(int(data['conf'][j]))

                if words and confs:
                    text = ' '.join(words)
                    avg  = sum(confs) / len(confs)
                    if avg > best_conf:
                        best_text, best_conf = text, avg

            except Exception as e:
                print(f"OCR strategy {i + 1} failed: {e}", file=sys.stderr)

        for p in processed:
            if p != image_path:
                p.unlink(missing_ok=True)

        return best_text, best_conf