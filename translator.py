import logging
from pathlib import Path

import ctranslate2
import sentencepiece as spm

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

        sp_path = self.model_dir / "sentencepiece.bpe.model"
        if not sp_path.exists():
            raise TranslationError(f"Tokenizer model not found: {sp_path}")

        try:
            logger.info("Loading translation model")
            self.translator = ctranslate2.Translator(str(self.model_dir), device="auto")
            self.sp = spm.SentencePieceProcessor()
            if not self.sp.Load(str(sp_path)):
                raise TranslationError(f"Failed to load tokenizer model: {sp_path}")
        except TranslationError:
            raise
        except Exception as exc:
            logger.exception("Failed to load translation model")
            raise TranslationError(f"Failed to load translation model: {exc}") from exc

        logger.info("Translation model loaded")

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if source_lang not in LANGUAGES or target_lang not in LANGUAGES or source_lang == target_lang:
            raise TranslationError("Unsupported language pair")

        source_code = LANGUAGES[source_lang]["code"]
        target_code = LANGUAGES[target_lang]["code"]

        try:
            pieces = self.sp.EncodeAsPieces(text.strip())
            source = [source_code] + pieces + ["</s>"]

            result = self.translator.translate_batch(
                [source],
                target_prefix=[[target_code]],
                beam_size=4,
                max_decoding_length=max(256, len(pieces) * 3),
            )[0]

            # The first hypothesis token is the target language prefix.
            target = result.hypotheses[0][1:]
            return self.sp.DecodePieces(target).strip()
        except Exception as exc:
            logger.exception("Translation failed: %s -> %s", source_lang, target_lang)
            raise TranslationError(f"Translation failed: {exc}") from exc

class TranslatorService:
    def __init__(self):
        self.engine = NLLBTranslator()

    def translate_many(self, text: str, source_lang: str, targets: list[str]) -> dict[str, str]:
        return {
            lang: self.engine.translate(text, source_lang, lang)
            for lang in targets
            if lang != source_lang
        }
