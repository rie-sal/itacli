#!/bin/bash
# Double-click this file in Finder to install itacli - no typing required.
# (First time, macOS Gatekeeper may block it: right-click the file > Open >
#  Open, to confirm you trust it.)
set -e
echo "Installing itacli..."
curl -fsSL https://raw.githubusercontent.com/rie-sal/itacli/main/bootstrap.sh | bash
echo
echo "All set. You can close this window."
