#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

PYTHON=""
for candidate in python3.11 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)' >/dev/null 2>&1; then
        PYTHON="$candidate"
        break
    fi
done
if [[ -z "$PYTHON" ]]; then
    echo "Python 3.11+ is required."
    exit 1
fi

if [[ ! -d .venv ]]; then
    "$PYTHON" -m venv .venv
fi
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

if [[ "$(uname -s)" == "Darwin" ]]; then
    if ! command -v swift >/dev/null 2>&1; then
        echo "Swift is required to build AppleTranslationBridge."
        echo "Install Xcode or the Swift toolchain, then rerun ./install.sh."
        exit 1
    fi

    if ! command -v llama-server >/dev/null 2>&1; then
        if command -v brew >/dev/null 2>&1; then
            echo "llama-server was not found. Installing llama.cpp with Homebrew..."
            brew install llama.cpp
        else
            echo "llama-server was not found and Homebrew is unavailable."
            echo "Install llama.cpp so that llama-server is in PATH, then rerun ./install.sh."
            exit 1
        fi
    fi

    if ! command -v llama-server >/dev/null 2>&1; then
        echo "llama-server is still not available after installing llama.cpp."
        echo "Ensure llama-server is in PATH, then rerun ./install.sh."
        exit 1
    fi

    echo "Building AppleTranslationBridge..."
    swift build -c release --package-path native/AppleTranslationBridge
else
    if ! command -v llama-server >/dev/null 2>&1; then
        echo "llama-server was not found."
        echo "Install llama.cpp and ensure llama-server is in PATH, then rerun ./install.sh."
        exit 1
    fi
fi

.venv/bin/python download_model.py
echo "Installation completed successfully."
