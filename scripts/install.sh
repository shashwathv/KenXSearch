#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

echo "╔══════════════════════════════════╗"
echo "║    KenXSearch — Dependency Setup ║"
echo "╚══════════════════════════════════╝"
echo

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

[[ -f "KenXSearch" ]]       || { echo "❌ 'KenXSearch' launcher not found in ${REPO_ROOT}"; exit 1; }
[[ -f "requirements.txt" ]] || { echo "❌ 'requirements.txt' not found in ${REPO_ROOT}"; exit 1; }

# ---------------------------------------------------------------------------
# Distro detection
# ---------------------------------------------------------------------------
if command -v pacman >/dev/null 2>&1; then
  DISTRO="arch"
  # numpy, pillow, pyqt6 installed via pacman — prebuilt, no compilation needed
  SYS_PKGS=(python python-pip python-numpy python-pillow python-pyqt6 tesseract tesseract-data-eng xdg-desktop-portal xdg-desktop-portal-gtk ttf-jetbrains-mono)
  install_sys() { sudo pacman -S --needed --noconfirm "$@"; }
  is_installed() { pacman -Qi "$1" >/dev/null 2>&1; }

elif command -v apt >/dev/null 2>&1; then
  DISTRO="debian"
  SYS_PKGS=(python3 python3-pip python3-venv tesseract-ocr tesseract-ocr-eng xdg-desktop-portal xdg-desktop-portal-gtk fonts-jetbrains-mono)
  install_sys() { sudo apt-get update -qq && sudo apt-get install -y "$@"; }
  is_installed() { dpkg-query -W -f='${Status}' "$1" 2>/dev/null | grep -q "ok installed"; }

elif command -v dnf >/dev/null 2>&1; then
  DISTRO="fedora"
  SYS_PKGS=(python3 python3-pip tesseract tesseract-langpack-eng xdg-desktop-portal xdg-desktop-portal-gtk jetbrains-mono-fonts)
  install_sys() { sudo dnf install -y "$@"; }
  is_installed() { rpm -q "$1" >/dev/null 2>&1; }

else
  echo "❌ Unsupported distro — no apt, dnf, or pacman found."
  echo "   Supported: Debian/Ubuntu, Fedora, Arch/Manjaro"
  exit 1
fi

echo "✓ Detected: ${DISTRO}"

# ---------------------------------------------------------------------------
# System packages
# ---------------------------------------------------------------------------
MISSING=()
for pkg in "${SYS_PKGS[@]}"; do
  is_installed "$pkg" || MISSING+=("$pkg")
done

if (( ${#MISSING[@]} > 0 )); then
  echo "→ Installing system packages: ${MISSING[*]}"
  install_sys "${MISSING[@]}"
else
  echo "✓ System packages already installed"
fi

# ---------------------------------------------------------------------------
# Python venv
# ---------------------------------------------------------------------------
if [[ ! -d ".venv" ]]; then
  echo "→ Creating virtual environment..."
  if [[ "${DISTRO}" == "arch" ]]; then
    # Use system site-packages so pacman-installed numpy/pillow/pyqt6 are visible
    python3 -m venv --system-site-packages .venv
  else
    python3 -m venv .venv
  fi
else
  echo "✓ Virtual environment already exists"
fi

echo "→ Upgrading pip..."
./.venv/bin/python -m pip install --upgrade pip setuptools wheel -q

echo "→ Installing Python dependencies..."
if [[ "${DISTRO}" == "arch" ]]; then
  # Exclude packages already provided by pacman to avoid source compilation
  grep -v -E "numpy|Pillow|PyQt6" requirements.txt > /tmp/kenxsearch_req_filtered.txt
  ./.venv/bin/pip install -r /tmp/kenxsearch_req_filtered.txt -q
else
  ./.venv/bin/pip install -r requirements.txt -q
fi

# ---------------------------------------------------------------------------
# Playwright browser
# ---------------------------------------------------------------------------
if ./.venv/bin/python -c "import playwright.sync_api" 2>/dev/null; then
  echo "→ Installing Playwright Chromium browser..."
  ./.venv/bin/playwright install chromium
else
  echo "⚠  Playwright not found in venv — skipping browser install"
fi

# ---------------------------------------------------------------------------
# Launcher symlink
# ---------------------------------------------------------------------------
echo "→ Setting up launcher..."
chmod +x "${REPO_ROOT}/KenXSearch"

BIN_DIR="${HOME}/.local/bin"
mkdir -p "${BIN_DIR}"
ln -sf "${REPO_ROOT}/KenXSearch" "${BIN_DIR}/KenXSearch"
echo "✓ Linked: ${BIN_DIR}/KenXSearch → ${REPO_ROOT}/KenXSearch"

# ---------------------------------------------------------------------------
# PATH setup
# ---------------------------------------------------------------------------
EXPORT_LINE='export PATH="$HOME/.local/bin:$PATH"'
case ":${PATH}:" in
  *:"${BIN_DIR}":*) ;;
  *)
    echo "→ Adding ${BIN_DIR} to PATH..."
    for RC in "${HOME}/.zshrc" "${HOME}/.bashrc"; do
      if ! grep -qF "${EXPORT_LINE}" "${RC}" 2>/dev/null; then
        echo "${EXPORT_LINE}" >> "${RC}"
        echo "✓ Added to ${RC}"
      fi
    done
    export PATH="${BIN_DIR}:${PATH}"
    echo "✓ PATH updated for this session"
    ;;
esac

echo
echo "✅ Installation complete!"
echo
echo "   Run:  KenXSearch"
echo