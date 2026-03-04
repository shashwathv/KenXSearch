#!/usr/bin/env bash

# Stop on first error
set -e

echo "=========================================="
echo "   Installing Lensix Dependencies"
echo "=========================================="
echo ""

# --- Get the script's directory ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Project root: $PROJECT_ROOT"
echo ""

# --- Function to check if a command exists ---
command_exists() {
    command -v "$1" &> /dev/null
}

# --- Detect package manager ---
detect_package_manager() {
    if command_exists apt; then
        echo "apt"
    elif command_exists dnf; then
        echo "dnf"
    elif command_exists pacman; then
        echo "pacman"
    elif command_exists zypper; then
        echo "zypper"
    else
        echo "unknown"
    fi
}

PKG_MANAGER=$(detect_package_manager)

# --- System Dependency Check ---
echo "[1/5] Checking for system dependencies..."

declare -A deps=(
    ["python3"]="python3"
    ["pip3"]="python3-pip"
    ["tesseract"]="tesseract-ocr"
    ["gnome-screenshot"]="gnome-screenshot"
)

# Add Wayland-specific dependencies if on Wayland
if [ "$XDG_SESSION_TYPE" = "wayland" ]; then
    deps["grim"]="grim"
    echo "   Wayland session detected, grim is recommended."
fi

missing_deps=()
for cmd in "${!deps[@]}"; do
    if ! command_exists "$cmd"; then
        missing_deps+=("${deps[$cmd]}")
    fi
done

if [ ${#missing_deps[@]} -ne 0 ]; then
    echo ""
    echo "❌ Missing system dependencies: ${missing_deps[*]}"
    echo ""
    case "$PKG_MANAGER" in
        apt)
            echo "Install with: sudo apt update && sudo apt install ${missing_deps[*]}"
            ;;
        dnf)
            echo "Install with: sudo dnf install ${missing_deps[*]}"
            ;;
        pacman)
            echo "Install with: sudo pacman -S ${missing_deps[*]}"
            ;;
        zypper)
            echo "Install with: sudo zypper install ${missing_deps[*]}"
            ;;
        *)
            echo "Please install these packages using your package manager."
            ;;
    esac
    echo ""
    read -p "Would you like to continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "   ✓ All system dependencies found"
fi

# --- Python Version Check ---
echo ""
echo "[2/5] Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.8"

if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)"; then
    echo "   ❌ Python 3.8+ required, found $PYTHON_VERSION"
    exit 1
fi
echo "   ✓ Python $PYTHON_VERSION detected"

# --- Create Virtual Environment ---
echo ""
echo "[3/5] Setting up Python virtual environment..."
cd "$PROJECT_ROOT"

if [ -d ".venv" ]; then
    echo "   Virtual environment already exists, removing old one..."
    rm -rf .venv
fi

python3 -m venv .venv
echo "   ✓ Virtual environment created"

# --- Activate Virtual Environment and Install Dependencies ---
echo ""
echo "[4/5] Installing Python packages..."
source .venv/bin/activate

# Upgrade pip first
pip install --upgrade pip wheel setuptools

# Install requirements
if [ ! -f "requirements.txt" ]; then
    echo "   ❌ requirements.txt not found!"
    exit 1
fi

pip install -r requirements.txt
echo "   ✓ Python packages installed"

# --- Playwright Browser Installation ---
echo ""
echo "[5/5] Installing Playwright browser (this may take a few minutes)..."
python -m playwright install chromium
echo "   ✓ Playwright browser installed"

deactivate

# --- Make launcher executable ---
echo ""
echo "Making launcher executable..."
chmod +x "$PROJECT_ROOT/lensix"
chmod +x "$PROJECT_ROOT/search.py"

# --- Create Symlink for global command ---
echo ""
echo "Setting up global 'lensix' command..."

LAUNCHER_PATH="$PROJECT_ROOT/lensix"

# Check if /usr/local/bin is writable
if [ -w "/usr/local/bin" ]; then
    # No sudo needed
    if [ -L "/usr/local/bin/lensix" ] || [ -f "/usr/local/bin/lensix" ]; then
        rm "/usr/local/bin/lensix" 2>/dev/null || true
    fi
    ln -sf "$LAUNCHER_PATH" /usr/local/bin/lensix
    echo "   ✓ Global command created (no sudo required)"
elif command_exists sudo; then
    # Need sudo
    if [ -L "/usr/local/bin/lensix" ] || [ -f "/usr/local/bin/lensix" ]; then
        sudo rm "/usr/local/bin/lensix" 2>/dev/null || true
    fi
    sudo ln -sf "$LAUNCHER_PATH" /usr/local/bin/lensix
    echo "   ✓ Global command created (with sudo)"
else
    echo "   ⚠ Could not create global command (no sudo access)"
    echo "   You can still run: $LAUNCHER_PATH"
fi

echo ""
echo "=========================================="
echo "   ✅ Installation Complete!"
echo "=========================================="
echo ""
echo "Run the program from anywhere by typing:"
echo "   lensix"
echo ""
echo "Or directly:"
echo "   $LAUNCHER_PATH"
echo ""