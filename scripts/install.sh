#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

echo "--- Installing Lensix Dependencies ---"

# Ensure we're in repo root (where lensix & requirements.txt live)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

# --- Basic sanity checks ---
[[ -f "lensix" ]] || { echo "Error: 'lensix' launcher not found in ${REPO_ROOT}"; exit 1; }
[[ -f "requirements.txt" ]] || { echo "Error: 'requirements.txt' not found in ${REPO_ROOT}"; exit 1; }

# --- Distro detection & package lists ---
PKG_MANAGER=""
INSTALL_CMD=""
declare -a PKGS

if command -v pacman >/dev/null 2>&1; then
  echo "Detected Arch-based Linux (pacman)."
  PKG_MANAGER="pacman"
  # Arch package names
  PKGS=(
    python            # provides venv on Arch
    python-pip
    tesseract
    tesseract-data-eng
    scrot
    gnome-screenshot
    xdg-desktop-portal
    xdg-desktop-portal-gtk
  )  # grim/slurp/spectacle/wl-clipboard omitted: wlroots-only, not needed on GNOME
  INSTALL_CMD="sudo pacman -S --needed --noconfirm"
elif command -v apt >/dev/null 2>&1; then
  echo "Detected Debian/Ubuntu (apt)."
  PKG_MANAGER="apt"
  PKGS=(
    python3
    python3-pip
    python3-venv
    tesseract-ocr
    tesseract-ocr-eng
    scrot
    gnome-screenshot
    xdg-desktop-portal
    xdg-desktop-portal-gtk
  )  # grim/slurp/kde-spectacle/wl-clipboard omitted: wlroots-only, not needed on GNOME
  INSTALL_CMD="sudo apt update && sudo apt install -y"
else
  echo "Error: supported package manager not found (need apt or pacman)."
  exit 1
fi

# --- Detect missing packages ---
MISSING=()
case "$PKG_MANAGER" in
  pacman)
    for p in "${PKGS[@]}"; do
      pacman -Qi "$p" >/dev/null 2>&1 || MISSING+=("$p")
    done
    ;;
  apt)
    for p in "${PKGS[@]}"; do
      dpkg-query -W -f='${Status}' "$p" 2>/dev/null | grep -q "ok installed" || MISSING+=("$p")
    done
    ;;
esac

if (( ${#MISSING[@]} > 0 )); then
  echo "Missing system dependencies:"
  printf '  - %s\n' "${MISSING[@]}"
  echo
  echo "Install with:"
  echo "  $INSTALL_CMD ${MISSING[*]}"
  exit 1
fi

# --- Create or reuse venv ---
if [[ ! -d ".venv" ]]; then
  echo "Creating virtual environment..."
  if command -v python3 >/dev/null 2>&1; then
    python3 -m venv .venv
  else
    python -m venv .venv
  fi
else
  echo "Reusing existing virtual environment (.venv)"
fi

echo "Upgrading pip/setuptools/wheel..."
./.venv/bin/python -m pip install --upgrade pip setuptools wheel

echo "Installing Python dependencies..."
./.venv/bin/pip install -r requirements.txt

# If Playwright is in requirements, install browsers
if ./.venv/bin/python -c "import importlib,sys; sys.exit(0 if importlib.util.find_spec('playwright') else 1)"; then
  echo "Installing Playwright browsers..."
  ./.venv/bin/playwright install
fi

# --- Make 'lensix' available on PATH ---
echo "Creating the 'lensix' launcher symlink..."

chmod +x "${REPO_ROOT}/lensix"

CANDIDATES=("${HOME}/.local/bin" "/usr/local/bin")
TARGET_BIN=""

for d in "${CANDIDATES[@]}"; do
  mkdir -p "$d" 2>/dev/null || true
  if [[ -w "$d" ]]; then TARGET_BIN="$d"; break; fi
done

LINK_TARGET="${TARGET_BIN:-/usr/local/bin}/lensix"
if [[ -n "$TARGET_BIN" ]]; then
  ln -sf "${REPO_ROOT}/lensix" "$LINK_TARGET"
  echo "Linked: $LINK_TARGET -> ${REPO_ROOT}/lensix"
  case ":$PATH:" in
    *:"$TARGET_BIN":*) : ;;
    *) echo "NOTE: $TARGET_BIN is not on PATH. Add:"
       echo "  export PATH=\"$TARGET_BIN:\$PATH\""
       ;;
  esac
else
  echo "No writable bin dir; using sudo for /usr/local/bin..."
  sudo mkdir -p /usr/local/bin
  sudo ln -sf "${REPO_ROOT}/lensix" /usr/local/bin/lensix
  echo "Linked: /usr/local/bin/lensix -> ${REPO_ROOT}/lensix"
fi

echo
echo "✅ Installation Complete. Run:  lensix"