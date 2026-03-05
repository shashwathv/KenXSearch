#!/usr/bin/env bash
# Lensix bootstrap — pipe directly to bash, no chmod needed:
#   curl -fsSL https://raw.githubusercontent.com/shashwathv/lensix/main/scripts/bootstrap.sh | bash
set -euo pipefail
IFS=$'\n\t'

GITHUB_REPO="shashwathv/KenXSearch"
INSTALL_DIR="${HOME}/.local/share/KenXSearch"

echo "╔══════════════════════════════════╗"
echo "║        Lensix  Installer         ║"
echo "╚══════════════════════════════════╝"
echo

command -v git >/dev/null 2>&1 || { echo "❌ git not found. Install git and retry."; exit 1; }

mkdir -p "$(dirname "${INSTALL_DIR}")"

if [ -d "${INSTALL_DIR}/.git" ]; then
  echo "↻  Existing install found — updating..."
  git -C "${INSTALL_DIR}" fetch --tags --prune
  git -C "${INSTALL_DIR}" pull --ff-only
else
  if [ -d "${INSTALL_DIR}" ]; then
    BAK="${INSTALL_DIR}.bak.$(date +%s)"
    echo "⚠  Non-git directory found, backing up to ${BAK}"
    mv "${INSTALL_DIR}" "${BAK}"
  fi
  echo "↓  Cloning repository..."
  git clone --depth 1 "https://github.com/${GITHUB_REPO}.git" "${INSTALL_DIR}"
fi

echo
echo "▶  Running installer..."
cd "${INSTALL_DIR}"
# chmod is handled here so the user never has to run it manually
chmod +x scripts/install.sh
exec bash scripts/install.sh
