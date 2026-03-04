import sys, webbrowser, pytesseract
from PIL import Image
from urllib.parse import quote_plus
from PyQt6.QtWidgets import QApplication
from engine import CaptureEngine
from overlay import LensixOverlay
from config import cfg

def main():
    app = QApplication(sys.argv)
    
    # 1. Capture screen WITHOUT showing a window yet
    bg = CaptureEngine.get_screen()
    if not bg or bg.isNull():
        print("❌ Error: Install 'grim' (sudo pacman -S grim) to fix the black screen.")
        return

    # 2. Run the UI
    overlay = LensixOverlay(bg)
    app.exec() # Wait here until user circles something

    # 3. Post-Capture: Search
    try:
        text = pytesseract.image_to_string(Image.open(cfg.crop_out)).strip()
        if text:
            webbrowser.open(f"https://www.google.com/search?q={quote_plus(text)}")
        else:
            # No text? Go straight to Google Lens Visual Search
            webbrowser.open(f"https://lens.google.com/uploadbyurl?url={cfg.crop_out}")
            print("Visual search triggered in your browser.")
    except:
        pass

if __name__ == "__main__":
    main()