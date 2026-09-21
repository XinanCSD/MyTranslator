import logging
from pathlib import Path

import ctranslate2
from transformers import AutoTokenizer

from config import LANGUAGES, MODEL_DIR

logger = logging.getLogger(__name__)

class TranslationError(RuntimeError):
    pass

class NLLBTranslator:
    def __init__(self, model_dir: Path = MODEL_DIR):
        self.model_dir = Path(model_dir)
        if not self.model_dir.exists():
            raise TranslationError(
                f"Translation model not found: {self.model_dir}. Run the installation script first."
            )
        try:
            logger.info("Loading translation model")
            self.translator = ctranslate2.Translator(str(self.model_dir), device="auto")
            self.tokenizer = AutoTokenizer.from_pretrained(
                str(self.model_dir), local_files_only=True, use_fast=True
            )
        except Exception as exc:
            logger.exception("Failed to load translation model")
            raise TranslationError(f"Failed to load translation model: {exc}") from exc
        logger.info("Translation model loaded")

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if source_lang not in LANGUAGES or target_lang not in LANGUAGES or source_lang == target_lang:
            raise TranslationError("Unsupported language pair")
        try:
            self.tokenizer.src_lang = LANGUAGES[source_lang]["code"]
            target = LANGUAGES[target_lang]["code"]
            encoded = self.tokenizer(text.strip(), return_tensors=None, add_special_tokens=True)
            tokens = self.tokenizer.convert_ids_to_tokens(encoded["input_ids"])
            result = self.translator.translate_batch(
                [[f">>{target}<<"] + tokens],
                beam_size=4,
                max_decoding_length=max(256, len(tokens) * 3),
            )[0]
            ids = self.tokenizer.convert_tokens_to_ids(result.hypotheses[0])
            return self.tokenizer.decode(ids, skip_special_tokens=True).strip()
        except Exception as exc:
            logger.exception("Translation failed: %s -> %s", source_lang, target_lang)
            raise TranslationError(f"Translation failed: {exc}") from exc

class TranslatorService:
    def __init__(self):
        self.engine = NLLBTranslator()

    def translate_many(self, text: str, source_lang: str, targets: list[str]) -> dict[str, str]:
        return {
            lang: self.engine.translate(text, source_lang, lang)
            for lang in targets if lang != source_lang
        }
