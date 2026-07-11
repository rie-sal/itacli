#!/bin/bash
# One-shot installer: clones itacli and installs it. Safe to re-run (updates).
# Usage:  curl -fsSL https://raw.githubusercontent.com/rie-sal/itacli/main/bootstrap.sh | bash
set -e
REPO="https://github.com/rie-sal/itacli.git"
DEST="${ITACLI_HOME:-$HOME/itacli}"

echo "==> itacli bootstrap"
command -v git >/dev/null 2>&1 || {
  echo "git is required. Install the Xcode Command Line Tools first:"
  echo "    xcode-select --install"
  exit 1
}
command -v python3 >/dev/null 2>&1 || { echo "python3 is required."; exit 1; }

if [ -d "$DEST/.git" ]; then
  echo "==> Updating existing install at $DEST"
  git -C "$DEST" pull --ff-only
else
  echo "==> Cloning to $DEST"
  git clone "$REPO" "$DEST"
fi

cd "$DEST"
./install.sh

echo
echo "======================================================================"
echo " itacli is installed at: $DEST"
echo " Start it with:"
echo "     cd \"$DEST\" && ITACLI_DATA_DIR=\"\$HOME/itacli-data\" .venv/bin/python run.py"
echo "======================================================================"
