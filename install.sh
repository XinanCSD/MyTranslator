#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$ROOT_DIR"
PYTHON=""
for candidate in python3.11 python3 python; do if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)' >/dev/null 2>&1; then PYTHON="$candidate"; break; fi; done
if [[ -z "$PYTHON" ]]; then echo "Python 3.11+ is required."; exit 1; fi
if [[ ! -d .venv ]]; then "$PYTHON" -m venv .venv; fi
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python download_model.py
echo "Installation completed successfully."
