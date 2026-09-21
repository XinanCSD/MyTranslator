import logging
from pathlib import Path

import ctranslate2
import sentencepiece as spm

from config import BEAM_SIZE, LANGUAGES, MAX_DECODING_LENGTH, MODEL_DIR

logger = logging.getLogger(__name__)


class TranslationError(RuntimeError):
    pass


class NLLBTokenizer:
    """Minimal tokenizer adapter for the CTranslate2 NLLB model package."""

    EOS_TOKEN = "</s>"

    def __init__(self, model_dir: Path):
        sp_path = model_dir / "sentencepiece.bpe.model"
        if not sp_path.exists():
            raise TranslationError(f"Tokenizer model not found: {sp_path}")

        self.sp = spm.SentencePieceProcessor()
        if not self.sp.Load(str(sp_path)):
            raise TranslationError(f"Failed to load tokenizer model: {sp_path}")

    def encode(self, text: str, source_lang: str) -> list[str]:
        pieces = self.sp.EncodeAsPieces(text.strip())
        # NLLB uses the source language token at the beginning of the
        # encoder input and an explicit EOS token at the end.
        return [source_lang, *pieces, self.EOS_TOKEN]

    def decode(self, tokens: list[str]) -> str:
        return self.sp.DecodePieces(tokens).strip()


class NLLBTranslator:
    def __init__(self, model_dir: Path = MODEL_DIR):
        self.model_dir = Path(model_dir)
        if not self.model_dir.exists():
            raise TranslationError(
                f"Translation model not found: {self.model_dir}. "
                "Run the installation script first."
            )

        try:
            logger.info("Loading translation model")
            self.translator = ctranslate2.Translator(
                str(self.model_dir),
                device="auto",
            )
            self.tokenizer = NLLBTokenizer(self.model_dir)
        except TranslationError:
            raise
        except Exception as exc:
            logger.exception("Failed to load translation model")
            raise TranslationError(
                f"Failed to load translation model: {exc}"
            ) from exc

        logger.info(
            "Translation model loaded (device=%s, compute_type=%s)",
            self.translator.device,
            self.translator.compute_type,
        )

    def translate_many(
        self,
        text: str,
        source_lang: str,
        target_langs: list[str],
    ) -> dict[str, str]:
        if source_lang not in LANGUAGES:
            raise TranslationError(f"Unsupported source language: {source_lang}")

        targets = [
            lang for lang in target_langs
            if lang in LANGUAGES and lang != source_lang
        ]
        if not targets:
            return {}

        source_code = LANGUAGES[source_lang]["code"]
        target_codes = [LANGUAGES[lang]["code"] for lang in targets]
        source = self.tokenizer.encode(text, source_code)

        # Translate all requested targets in one CTranslate2 batch.
        sources = [source] * len(target_codes)
        target_prefixes = [[code] for code in target_codes]

        try:
            results = self.translator.translate_batch(
                sources,
                target_prefix=target_prefixes,
                beam_size=BEAM_SIZE,
                max_decoding_length=MAX_DECODING_LENGTH,
                max_input_length=1024,
            )
        except Exception as exc:
            logger.exception(
                "Translation failed for %s -> %s",
                source_lang,
                ", ".join(targets),
            )
            raise TranslationError(f"Translation failed: {exc}") from exc

        translated: dict[str, str] = {}
        for lang, result in zip(targets, results):
            hypothesis = result.hypotheses[0]
            # The first hypothesis token is the forced target language token.
            translated[lang] = self.tokenizer.decode(hypothesis[1:])

        return translated


class TranslatorService:
    def __init__(self):
        self.engine = NLLBTranslator()

    def translate_many(
        self,
        text: str,
        source_lang: str,
        targets: list[str],
    ) -> dict[str, str]:
        return self.engine.translate_many(text, source_lang, targets)
