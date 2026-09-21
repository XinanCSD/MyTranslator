from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
MODEL_ID = "osa911/nllb-200-distilled-600M-ct2-int8"
MODEL_DIR = BASE_DIR / "models" / "nllb-600m-ct2-int8"
LOG_DIR = BASE_DIR / "logs"

LANGUAGES = {
    "zh": {"label": "中文", "code": "zho_Hans"},
    "en": {"label": "English", "code": "eng_Latn"},
    "ja": {"label": "日本語", "code": "jpn_Jpan"},
}
AUTO_TRANSLATE_MAX_CHARS = 300
PLACEHOLDER = "......"
