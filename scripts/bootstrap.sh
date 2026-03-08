#!/usr/bin/env bash
# KenXSearch bootstrap — pipe directly to bash, no chmod needed:
#   curl -fsSL https://raw.githubusercontent.com/shashwathv/KenXSearch/main/scripts/bootstrap.sh | bash
set -euo pipefail
IFS=$'\n\t'

GITHUB_REPO="shashwathv/KenXSearch"
INSTALL_DIR="${HOME}/.local/share/KenXSearch"

echo "╔══════════════════════════════════╗"
echo "║      KenXSearch Installer        ║"
echo "╚══════════════════════════════════╝"
echo

command -v git >/dev/null 2>&1 || { echo "❌ git not found. Install git and retry."; exit 1; }

mkdir -p "$(dirname "${INSTALL_DIR}")"

if [ -d "${INSTALL_DIR}/.git" ]; then
  echo "→ Existing install found — updating..."
  git -C "${INSTALL_DIR}" fetch -q --tags --prune
  git -C "${INSTALL_DIR}" pull -q --ff-only
  echo "✓ Up to date"
else
  if [ -d "${INSTALL_DIR}" ]; then
    BAK="${INSTALL_DIR}.bak.$(date +%s)"
    echo "⚠  Non-git directory found, backing up to ${BAK}"
    mv "${INSTALL_DIR}" "${BAK}"
  fi
  echo "→ Cloning KenXSearch..."
  git clone -q --depth 1 "https://github.com/${GITHUB_REPO}.git" "${INSTALL_DIR}"
  echo "✓ Done"
fi

echo
echo "→ Running installer..."
cd "${INSTALL_DIR}"
chmod +x scripts/install.sh
exec bash scripts/install.sh