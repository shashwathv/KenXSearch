# KenXSearch — Circle to Search for Linux

A powerful **Circle to Search** tool for any Linux desktop, inspired by the Android feature. Draw a freehand circle around anything on your screen to instantly search it with Google — text, visual, translate, or shopping. Internally branded as **Lensix**.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/UI-PyQt6-41CD52?logo=qt&logoColor=white)
<!---![License](https://img.shields.io/badge/License-MIT-yellow) -->
![Platform](https://img.shields.io/badge/Platform-Linux-FCC624?logo=linux&logoColor=black)

---

## ✨ Features

- **Freehand Selection** — draw a circle (or any shape) around anything on screen
- **Multiple Search Modes** — Text, Visual, Translate, and Shopping via Google Lens
- **Smart OCR** — multi-strategy text extraction using Tesseract + OpenCV preprocessing
- **Sleek Overlay UI** — full-screen transparent overlay with iOS-style frosted glass buttons and pulsing selection glow
- **Wayland + X11** — works on both display protocols out of the box
- **Persistent Browser Session** — Google login and cookies are preserved between runs to avoid CAPTCHAs
- **Multi-Language OCR** — supports English, Spanish, French, German, Italian, Portuguese, Russian, Japanese, Korean, and Simplified Chinese

---

## 🏗️ Architecture

```
lensix (bash)  →  search.py  →  src/main.py
                                    │
                                    ├── config.py      — settings, paths, display detection
                                    ├── overlay.py     — full-screen PyQt6 overlay + drawing
                                    ├── ocr.py         — Tesseract OCR with OpenCV preprocessing
                                    └── lens.py        — Google Lens browser automation (Playwright)
```

| Layer | Technology |
|---|---|
| **UI / Overlay** | PyQt6 (frameless, translucent window) |
| **Screen Capture** | `mss` (X11) / `grim`, `gnome-screenshot`, `spectacle` (Wayland) |
| **Image Processing** | OpenCV, Pillow |
| **OCR** | Tesseract via pytesseract |
| **Browser Automation** | Playwright (Chromium, persistent context) |

---

## 📦 Installation

### Prerequisites

You must have `git` and `curl` installed.

```bash
# Debian/Ubuntu
sudo apt install git curl

# Fedora
sudo dnf install git curl

# Arch
sudo pacman -S git curl
```

### One-Step Install

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/shashwathv/KenXSearch/main/scripts/bootstrap.sh)"
```

This will:
1. Clone the repo to `~/.local/share/KenXSearch`
2. Install system dependencies (`tesseract-ocr`, `python3`, etc.)
3. Create a Python virtual environment and install all packages
4. Install Playwright Chromium browser
5. Symlink `lensix` to `~/.local/bin/`

> **Supported distros:** Debian/Ubuntu (`apt`), Fedora (`dnf`), Arch (`pacman`)

---

## 🚀 Usage

```bash
lensix
```

1. A full-screen overlay appears with a hint: **"✦ Circle anything to search"**
2. **Draw** a circle (or any shape) around the content you want to search
3. The selection morphs into a rounded rectangle with a pulsing glow
4. Pick a search mode from the floating pill buttons:
   - **Search** — OCR extracts text → Google text search (falls back to visual if no text found)
   - **Visual** — uploads the selection to Google Lens
   - **Translate** — opens Google Lens in translate mode
   - **Shopping** — opens Google Lens and switches to the Shopping tab

### Keyboard Shortcuts

| Key | Action |
|---|---|
| `Escape` | Quit the overlay |
| `Space` | Quick text search (after selection) |

---

## 🔧 Dependencies

### System

| Package | Purpose |
|---|---|
| `tesseract-ocr` | OCR engine |
| `grim` / `gnome-screenshot` / `spectacle` | Wayland screen capture (at least one needed) |

### Python (installed automatically in `.venv`)

| Package | Purpose |
|---|---|
| `PyQt6` | UI overlay and drawing |
| `mss` | X11 screen capture |
| `opencv-python` | Image preprocessing for OCR |
| `numpy` | Array operations for OpenCV |
| `Pillow` | Image manipulation |
| `pytesseract` | Python wrapper for Tesseract |
| `playwright` | Browser automation for Google Lens |

---

## 📁 Project Structure

```
KenXSearch/
├── lensix                  # Bash launcher (symlinked to ~/.local/bin)
├── search.py               # Python entry point
├── src/
│   ├── config.py           # Settings, paths, display detection
│   ├── main.py             # Dependency checker + app startup
│   ├── overlay.py          # Full-screen overlay UI (406 lines)
│   ├── ocr.py              # Multi-strategy OCR processor
│   └── lens.py             # Google Lens integration via Playwright
├── scripts/
│   ├── bootstrap.sh        # curl-pipeable installer bootstrap
│   └── install.sh          # Full dependency + venv installer
├── requirements.txt        # Pinned Python dependencies
└── README.md
```

---

## 🔒 A Note on Security

The one-step install method pipes a script from the internet into your shell. This requires trust in the source. You can inspect [bootstrap.sh](scripts/bootstrap.sh) and [install.sh](scripts/install.sh) on GitHub before running.

---

## 📄 License

TBD
