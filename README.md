# MyTranslator

Cross-platform local clipboard translator for Chinese, English, and Japanese.

## Model selection

The GUI provides a model dropdown.

- macOS default: Apple Translation
- Windows/Linux default: TranslateGemma 4B Q4_K_M
- NLLB-200 600M is also available on all desktop platforms.

The selected model is not loaded at startup. Models load only when translation is requested. Only one local model is active at a time. Switching models unloads/stops the previous local model before another is loaded. The last selected model is persisted.

TranslateGemma 4B Q4_K_M uses a local `llama-server` process and the GGUF model `42ailab/TranslateGemma-4B-GGUF`.

## Install

### macOS / Linux

```bash
chmod +x install.sh run.sh
./install.sh
./run.sh
```

### Windows

Run `install.bat`, then `run.bat`.

Installation creates/reuses `.venv`, installs Python dependencies, checks `llama-server` where it is required, and downloads/reuses NLLB and TranslateGemma files. Models are not loaded into memory by installation.

## Runtime

`run.sh` / `run.bat` only start MyTranslator. TranslateGemma's server is started by the application on first use and stopped when switching away from TranslateGemma or exiting.

## Features

- Editable 中文 / English / 日本語 fields with copy buttons.
- Model selection with platform defaults and persisted selection.
- Clipboard monitoring and lightweight language detection.
- Automatic translation for clipboard text up to 200 characters.
- Manual translation without the automatic 200-character limit.
- Background translation through QThread.
- Stale-result protection with translation generations.
- Single active local translation model.

## Structure

- `app.py` — entry point
- `main_window.py` — GUI and clipboard coordination
- `model_manager.py` — single-model lifecycle and persistence
- `translator.py` — translation backends and llama-server lifecycle
- `language_detector.py` — language detection
- `config.py` — model registry and platform defaults
- `download_model.py` — model downloads

## Note

Apple Translation is registered as the macOS default model, but actual Apple Translation calls require a native macOS Translation framework bridge. The current Python-only implementation does not yet provide that bridge.
