"""
Lensix Google Lens Integration
Handles all search dispatch and Google Lens browser automation.
"""

import sys
import webbrowser
from urllib.parse import quote_plus

from src.config import config, SearchType
from src.ocr import OCRProcessor


# ---------------------------------------------------------------------------
# Search dispatchers
# ---------------------------------------------------------------------------

def dispatch(search_type: SearchType):
    """Route a SearchType to the correct search function."""
    {
        SearchType.TEXT:      search_text,
        SearchType.IMAGE:     search_visual,
        SearchType.TRANSLATE: search_translate,
        SearchType.SHOPPING:  search_shopping,
    }[search_type]()


def search_text():
    """OCR the selection and open a Google text search. Falls back to visual."""
    text, conf = OCRProcessor.extract_text_multi_strategy(config.screenshot_path)
    if text and conf > config.min_confidence and len(text) >= config.min_text_length:
        print(f"Extracted text: {text}")
        webbrowser.open(f"https://www.google.com/search?q={quote_plus(text)}")
    else:
        print("No text found, falling back to visual search.")
        search_visual()


def search_visual():
    """Upload to Google Lens for visual/reverse image search."""
    upload_to_google_lens(mode="search")


def search_translate():
    """Upload to Google Lens in translate mode.

    Uses Lens instead of Tesseract OCR so every language is supported
    natively — Korean, Japanese, Arabic, Hindi, etc.
    """
    upload_to_google_lens(mode="translate")


def search_shopping():
    """Upload to Google Lens and switch to the Shopping results tab."""
    upload_to_google_lens(mode="shopping")


# ---------------------------------------------------------------------------
# Google Lens browser automation
# ---------------------------------------------------------------------------

def upload_to_google_lens(mode: str = "search"):
    """
    Open Chromium via Playwright, navigate to Google Lens, and silently
    upload the captured selection image.

    mode: "search" | "translate" | "shopping"

    A persistent browser context is used so cookies and Google login are
    preserved between runs — this avoids repeated CAPTCHA challenges.
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout
    except ImportError:
        print("Playwright not installed — opening Lens in default browser.", file=sys.stderr)
        webbrowser.open("https://lens.google.com/")
        return

    URLS = {
        "translate": "https://lens.google.com/?mode=translate",
        "shopping":  "https://lens.google.com/?mode=visual",
        "search":    "https://lens.google.com/",
    }

    print("Opening Google Lens...")
    pw      = None
    browser = None
    try:
        pw = sync_playwright().start()
        browser = pw.chromium.launch_persistent_context(
            user_data_dir=str(config.playwright_user_data_dir),
            headless=False,
            no_viewport=True,
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ],
            # Spoof a real Chrome UA to reduce bot-detection triggers
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            ignore_default_args=["--enable-automation"],
        )

        page = browser.pages[0] if browser.pages else browser.new_page()

        # Remove the navigator.webdriver flag that Google checks for bots
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        page.goto(URLS.get(mode, URLS["search"]),
                  wait_until="domcontentloaded", timeout=20000)

        # Wait for the upload link and intercept the file chooser it triggers
        upload_link = page.get_by_text("upload a file", exact=False)
        upload_link.wait_for(timeout=15000)

        with page.expect_file_chooser(timeout=10000) as fc_info:
            upload_link.click()

        # Inject the image silently — no file picker dialog shown to user
        fc_info.value.set_files(str(config.screenshot_path))
        print("✅ Image uploaded, waiting for results...")

        try:
            page.wait_for_load_state("domcontentloaded", timeout=15000)
        except Exception:
            pass
        page.wait_for_timeout(3000)

        # Shopping: click the Shopping tab in Lens results
        if mode == "shopping":
            try:
                tab = page.get_by_text("Shopping", exact=False)
                tab.wait_for(timeout=5000)
                tab.click()
                page.wait_for_timeout(2000)
            except Exception:
                pass

        input("   Press Enter in this terminal to close the browser... ")

    except Exception as e:
        print(f"Error uploading to Google Lens: {e}", file=sys.stderr)
    finally:
        try:
            if browser:
                browser.close()
        except Exception:
            pass
        try:
            if pw:
                pw.stop()
        except Exception:
            pass
