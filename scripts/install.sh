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
  if [[ "${DISTRO}" == "arch" ]]; then
    # Use system site packages so pacman-installed numpy/pillow/pyqt6 are available
    python3 -m venv --system-site-packages .venv
  else
    python3 -m venv .venv
  fi
else
  echo "✓ Reusing existing virtual environment"
fi

echo "Upgrading pip..."
./.venv/bin/python -m pip install --upgrade pip setuptools wheel -q

echo "Installing Python dependencies..."
if [[ "${DISTRO}" == "arch" ]]; then
  # Skip packages already installed via pacman to avoid compiling from source
  grep -v -E "numpy|Pillow|PyQt6" requirements.txt > /tmp/kenxsearch_req_filtered.txt
  ./.venv/bin/pip install -r /tmp/kenxsearch_req_filtered.txt -q
else
  ./.venv/bin/pip install -r requirements.txt -q
fi

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

# Auto-add ~/.local/bin to PATH in shell config if missing
case ":${PATH}:" in
  *:"${BIN_DIR}":*) ;;
  *)
    echo
    echo "⚠  ${BIN_DIR} is not on your PATH — adding it automatically..."
    EXPORT_LINE='export PATH="$HOME/.local/bin:$PATH"'
    for RC in "${HOME}/.zshrc" "${HOME}/.bashrc"; do
      if [[ -f "${RC}" ]] && ! grep -qF "${EXPORT_LINE}" "${RC}"; then
        echo "${EXPORT_LINE}" >> "${RC}"
        echo "✓ Added to ${RC}"
      fi
    done
    export PATH="${BIN_DIR}:${PATH}"
    echo "✓ PATH updated for this session"
    ;;
esac

echo
echo "✅ Done! Run:  KenXSearch"