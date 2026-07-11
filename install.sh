#!/bin/bash
# itacli installer (macOS). Creates an isolated venv and installs everything.
# Usage:  ./install.sh
set -e
cd "$(dirname "$0")"

echo "==> Creating virtualenv (.venv)"
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip >/dev/null

echo "==> Installing spaCy + mlconjug3 (this pulls numpy/scikit-learn; a few min)"
.venv/bin/python -m pip install spacy mlconjug3
# mlconjug3's bundled model was pickled with scikit-learn 1.6.x; pin so it loads.
.venv/bin/python -m pip install 'scikit-learn==1.6.1'

echo "==> Downloading the Italian model (~40MB)"
.venv/bin/python -m spacy download it_core_news_md

echo
echo "Done. Start itacli with:"
echo "    .venv/bin/python run.py"
echo
echo "For an isolated data dir (recommended for a clean test):"
echo "    ITACLI_DATA_DIR=\"\$HOME/itacli-data\" .venv/bin/python run.py"
