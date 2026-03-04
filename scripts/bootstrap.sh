#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# --- Config ---
GITHUB_REPO="shashwathv/lensix"
INSTALL_DIR="${HOME}/.local/share/lensix"

echo "Bootstrapping Lensix installation..."
echo "Target repository: ${GITHUB_REPO}"
echo "Installation directory: ${INSTALL_DIR}"
echo

command -v git >/dev/null 2>&1 || { echo "Error: git not found. Install git and retry."; exit 1; }

mkdir -p "$(dirname "${INSTALL_DIR}")"

if [ -d "${INSTALL_DIR}/.git" ]; then
  echo "Existing git installation found. Updating..."
  git -C "${INSTALL_DIR}" fetch --tags --prune
  git -C "${INSTALL_DIR}" pull --ff-only
else
  if [ -d "${INSTALL_DIR}" ]; then
    echo "Existing non-git directory found at ${INSTALL_DIR}."
    BAK="${INSTALL_DIR}.bak.$(date +%s)"
    echo "Moving it to ${BAK} ..."
    mv "${INSTALL_DIR}" "${BAK}"
  fi
  echo "Cloning repository..."
  git clone --depth 1 "https://github.com/${GITHUB_REPO}.git" "${INSTALL_DIR}"
fi

echo "Running the main installer..."
cd "${INSTALL_DIR}"
chmod +x scripts/install.sh
exec ./scripts/install.sh
