# MyTranslator

Cross-platform local clipboard translator for Chinese, English, and Japanese.

## Model selection

The GUI has a model dropdown.

- macOS default: Apple Translation
- Windows/Linux default: TranslateGemma 4B Q4_K_M

Also available where supported:
- NLLB-200 600M
- TranslateGemma 4B Q4_K_M
- Apple Translation on macOS

The selected model is only loaded when the first translation is requested. Only one local model can be active at a time. Switching models stops/unloads the current local model before the next model is loaded. The last selected model is saved and restored on the next launch.

## Install

### macOS / Linux

```bash
chmod +x install.sh run.sh
./install.sh
./run.sh
```

### Windows

Run `install.bat`, then `run.bat`.

Installation prepares the Python environment, `llama-server`, and model files. It does not load models into memory.

## Runtime

``run.sh`` and ``run.bat`` only start MyTranslator. TranslateGemma's `llama-server` is started by the application only when TranslateGemma is selected for translation, and is stopped when another model is selected or the application exits.

## Features

- Editable 中文 / English / 日本語 fields with copy buttons.
- Clipboard monitoring and lightweight language detection.
- Automatic translation for clipboard text up to 200 characters.
- Manual translation without the automatic 200-character limit.
- Background translation via QThread.
- Stale-result protection with translation generations.
- Single active local translation model.

## Structure

- `app.py` — entry point
- `main_window.py` — GUI and clipboard coordination
- `model_manager.py` — model selection, loading, unloading, and persistence
- `translator.py` — translation backends and llama-server lifecycle
- `language_detector.py` — language detection
- `config.py` — model registry and platform defaults
- `download_model.py` — model downloads

## macOS Apple Translation

The Apple Translation entry is registered for macOS. The current project still needs a native Swift/Objective-C bridge to Apple's Translation framework for actual Apple Translation calls.
