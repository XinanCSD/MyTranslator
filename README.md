# MyTranslator

Cross-platform local clipboard translator for Chinese, English, and Japanese.

## Install

### macOS / Linux

```bash
chmod +x install.sh run.sh
./install.sh
./run.sh
```

### Windows

Run `install.bat`, then `run.bat`.

The install scripts create/reuse `.venv` and download/reuse the NLLB model under `models/`.

## Features

- PySide6 GUI with editable 中文 / English / 日本語 text areas.
- Copy buttons: `复制`, `Copy`, `コピー`.
- Qt `QClipboard` monitoring.
- Lightweight local language detection for Chinese, English, and Japanese.
- Automatic translation for clipboard text up to 300 characters.
- Manual translation without the 300-character limit.
- Background translation through QThread.
- Generation checks prevent stale results from overwriting newer results.
- Local CTranslate2 + NLLB inference; no cloud translation API.

## Privacy

Logs are written to `logs/app.log` and do not include complete clipboard text or translation output.

## Structure

- `app.py` — entry point
- `main_window.py` — GUI and clipboard coordination
- `translator.py` — translation engine adapter
- `language_detector.py` — language detection
- `config.py` — constants
- `download_model.py` — model download
