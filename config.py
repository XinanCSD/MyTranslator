
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
MODEL_ROOT = BASE_DIR / "models"

LANGUAGES = {
    "zh": {"label": "中文", "code": "zho_Hans"},
    "en": {"label": "English", "code": "eng_Latn"},
    "ja": {"label": "日本語", "code": "jpn_Jpan"},
}

MODELS = {
    "apple_translation": {
        "label": "Apple Translation",
        "backend": "apple",
        "platforms": {"darwin"},
    },
    "translategemma_4b_q4km": {
        "label": "TranslateGemma 4B Q4_K_M",
        "backend": "llama",
        "platforms": {"darwin", "win32", "linux"},
        "model_repo": "42ailab/TranslateGemma-4B-GGUF",
        "model_file": "translategemma-4b-it-Q4_K_M.gguf",
        "model_dir": MODEL_ROOT / "translategemma-4b-q4km",
    },
    "nllb_600m": {
        "label": "NLLB-200 600M",
        "backend": "nllb",
        "platforms": {"darwin", "win32", "linux"},
        "model_id": "osa911/nllb-200-distilled-600M-ct2-int8",
        "model_dir": MODEL_ROOT / "nllb-600m-ct2-int8",
    },
}

AUTO_TRANSLATE_MAX_CHARS = 200
BEAM_SIZE = 2
MAX_DECODING_LENGTH = 256
PLACEHOLDER = "......"
SETTINGS_FILE = BASE_DIR / "settings.json"

def default_model_id() -> str:
    if sys.platform == "darwin":
        return "apple_translation"
    return "translategemma_4b_q4km"
