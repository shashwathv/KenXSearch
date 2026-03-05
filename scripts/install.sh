#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

echo "--- Installing KenXSearch Dependencies ---"
echo

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

[[ -f "KenXSearch" ]]          || { echo "❌ 'KenXSearch' launcher not found in ${REPO_ROOT}"; exit 1; }
[[ -f "requirements.txt" ]] || { echo "❌ 'requirements.txt' not found in ${REPO_ROOT}"; exit 1; }

# ---------------------------------------------------------------------------
# Distro detection
# ---------------------------------------------------------------------------
if command -v pacman >/dev/null 2>&1; then
  DISTRO="arch"
  SYS_PKGS=(python python-pip tesseract tesseract-data-eng scrot gnome-screenshot xdg-desktop-portal xdg-desktop-portal-gtk)
  install_sys() { sudo pacman -S --needed --noconfirm "$@"; }
  is_installed() { pacman -Qi "$1" >/dev/null 2>&1; }

elif command -v apt >/dev/null 2>&1; then
  DISTRO="debian"
  SYS_PKGS=(python3 python3-pip python3-venv tesseract-ocr tesseract-ocr-eng scrot gnome-screenshot xdg-desktop-portal xdg-desktop-portal-gtk)
  install_sys() { sudo apt-get update -qq && sudo apt-get install -y "$@"; }
  is_installed() { dpkg-query -W -f='${Status}' "$1" 2>/dev/null | grep -q "ok installed"; }

elif command -v dnf >/dev/null 2>&1; then
  DISTRO="fedora"
  SYS_PKGS=(python3 python3-pip tesseract tesseract-langpack-eng scrot gnome-screenshot xdg-desktop-portal xdg-desktop-portal-gtk)
  install_sys() { sudo dnf install -y "$@"; }
  is_installed() { rpm -q "$1" >/dev/null 2>&1; }

else
  echo "❌ No supported package manager found (apt / dnf / pacman)."
  exit 1
fi

echo "✓ Detected distro: ${DISTRO}"

# ---------------------------------------------------------------------------
# Auto-install missing system packages
# ---------------------------------------------------------------------------
MISSING=()
for pkg in "${SYS_PKGS[@]}"; do
  is_installed "$pkg" || MISSING+=("$pkg")
done

if (( ${#MISSING[@]} > 0 )); then
  echo "Installing missing system packages: ${MISSING[*]}"
  install_sys "${MISSING[@]}"
else
  echo "✓ All system packages already installed"
fi

# ---------------------------------------------------------------------------
# Python venv
# ---------------------------------------------------------------------------
if [[ ! -d ".venv" ]]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
else
  echo "✓ Reusing existing virtual environment"
fi

echo "Upgrading pip..."
./.venv/bin/python -m pip install --upgrade pip setuptools wheel -q

echo "Installing Python dependencies..."
./.venv/bin/pip install -r requirements.txt -q

# ---------------------------------------------------------------------------
# Playwright browser install (fixed importlib bug)
# ---------------------------------------------------------------------------
if ./.venv/bin/python -c "import playwright" 2>/dev/null; then
  echo "Installing Playwright browsers..."
  ./.venv/bin/playwright install chromium
else
  echo "⚠  Playwright not found in venv — skipping browser install"
fi

# ---------------------------------------------------------------------------
# Symlink lensix onto PATH
# ---------------------------------------------------------------------------
echo "Creating 'KenXSearch' launcher..."
chmod +x "${REPO_ROOT}/KenXSearch"

BIN_DIR="${HOME}/.local/bin"
mkdir -p "${BIN_DIR}"
ln -sf "${REPO_ROOT}/KenXSearch" "${BIN_DIR}/KenXSearch"
echo "✓ Linked: ${BIN_DIR}/KenXSearch → ${REPO_ROOT}/KenxSearch"

# Warn if ~/.local/bin is not on PATH
case ":${PATH}:" in
  *:"${BIN_DIR}":*) ;;
  *)
    echo
    echo "⚠  ${BIN_DIR} is not on your PATH."
    echo "   Add this line to your ~/.bashrc or ~/.zshrc:"
    echo '   export PATH="$HOME/.local/bin:$PATH"'
    echo "   Then run:  source ~/.bashrc"
    ;;
esac

echo
echo "✅ Done! Run:  KenXSearch"
