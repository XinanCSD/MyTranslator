# MyTranslator

Cross-platform local clipboard translator for Chinese, English, and Japanese.

## Model selection

The GUI provides a model dropdown.

- macOS default: Apple Translation
- Windows/Linux default: TranslateGemma 4B Q4_K_M
- NLLB-200 600M is also available on desktop platforms.

The selected model is loaded only when the first translation is requested. Only one translation backend is active at a time. Switching models stops/unloads the current backend before another is loaded. The last selected model is persisted.

### TranslateGemma

The TranslateGemma backend uses the local GGUF model with `llama-server`. The translation request is rendered from Google's structured TranslateGemma format with explicit source and target language codes.

The 42ailab GGUF repository documents llama.cpp usage and identifies `translategemma-4b-it-Q4_K_M.gguf` as the Q4_K_M model file. Its model card also explicitly notes that its ordinary instruction-style chat prompt is not the upstream official TranslateGemma template. MyTranslator therefore uses the structured translation format rather than that chat adaptation.

### Apple Translation

On macOS, the Apple Translation backend uses a small native Swift command-line bridge around Apple's Translation framework. The bridge calls `TranslationSession(installedSource:target:)` and `translate(String)`.

The direct TranslationSession initializer requires the source and target language resources to already be installed on the Mac. If the required language pair is unavailable, MyTranslator reports the system error instead of falling back to another model automatically.

## Install

### macOS

```bash
chmod +x install.sh run.sh
./install.sh
./run.sh
```

On macOS, `install.sh` also builds the native Apple Translation bridge and installs/checks `llama-server`.

### Linux

```bash
chmod +x install.sh run.sh
./install.sh
./run.sh
```

Install llama.cpp separately and ensure `llama-server` is available in PATH.

### Windows

Run `install.bat`, then `run.bat`.

Install llama.cpp separately and ensure `llama-server.exe` is available in PATH.

Installation creates/reuses `.venv`, installs Python dependencies, prepares/checks the local runtime, and downloads/reuses model files.

## Runtime

`run.sh` / `run.bat` only start MyTranslator.

TranslateGemma's `llama-server` is started by MyTranslator when TranslateGemma is first used and is stopped when switching away from TranslateGemma or exiting.

## Features

- Editable 中文 / English / 日本語 fields with copy buttons.
- Model selection with platform defaults and persisted selection.
- Clipboard monitoring and lightweight language detection.
- Automatic translation for clipboard text up to 200 characters.
- Manual translation without the automatic 200-character limit.
- Background translation through QThread.
- Stale-result protection with translation generations.
- Single active local translation backend.

## Structure

- `app.py` — entry point
- `main_window.py` — GUI and clipboard coordination
- `model_manager.py` — single-model lifecycle and persistence
- `translator.py` — translation backends and llama-server lifecycle
- `native/AppleTranslationBridge` — macOS Translation framework bridge
- `language_detector.py` — language detection
- `config.py` — model registry and platform defaults
- `download_model.py` — model downloads
