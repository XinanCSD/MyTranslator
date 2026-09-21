import json
import logging
import os
import shutil
import signal
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import ctranslate2
import sentencepiece as spm

from config import (
    BEAM_SIZE,
    LANGUAGES,
    MAX_DECODING_LENGTH,
    MODELS,
    SETTINGS_FILE,
)

logger = logging.getLogger(__name__)


class TranslationError(RuntimeError):
    pass


class NLLBTokenizer:
    EOS_TOKEN = "</s>"

    def __init__(self, model_dir: Path):
        sp_path = model_dir / "sentencepiece.bpe.model"
        if not sp_path.exists():
            raise TranslationError(f"Tokenizer model not found: {sp_path}")
        self.sp = spm.SentencePieceProcessor()
        if not self.sp.Load(str(sp_path)):
            raise TranslationError(f"Failed to load tokenizer model: {sp_path}")

    def encode(self, text: str, source_lang: str) -> list[str]:
        return [source_lang, *self.sp.EncodeAsPieces(text.strip()), self.EOS_TOKEN]

    def decode(self, tokens: list[str]) -> str:
        return self.sp.DecodePieces(tokens).strip()


class NLLBBackend:
    def __init__(self, model_dir: Path):
        if not Path(model_dir).exists():
            raise TranslationError(
                f"NLLB model not found: {model_dir}. Run the installation script first."
            )
        try:
            self.translator = ctranslate2.Translator(str(model_dir), device="auto")
            self.tokenizer = NLLBTokenizer(Path(model_dir))
        except Exception as exc:
            logger.exception("Failed to load NLLB")
            raise TranslationError(f"Failed to load NLLB: {exc}") from exc

    def translate_many(self, text, source_lang, target_langs):
        source_code = LANGUAGES[source_lang]["code"]
        targets = [x for x in target_langs if x in LANGUAGES and x != source_lang]
        if not targets:
            return {}
        source = self.tokenizer.encode(text, source_code)
        results = self.translator.translate_batch(
            [source] * len(targets),
            target_prefix=[[LANGUAGES[x]["code"]] for x in targets],
            beam_size=BEAM_SIZE,
            max_decoding_length=MAX_DECODING_LENGTH,
            max_input_length=1024,
        )
        return {
            lang: self.tokenizer.decode(result.hypotheses[0][1:])
            for lang, result in zip(targets, results)
        }


class LlamaServer:
    def __init__(self, model_dir: Path, model_file: str):
        self.model_dir = Path(model_dir)
        self.model_file = model_file
        self.process = None
        self.port = 39001

    def start(self):
        if self.process and self.process.poll() is None:
            return
        server = shutil.which("llama-server") or shutil.which("llama-server.exe")
        if not server:
            raise TranslationError(
                "llama-server was not found. Run the installation script first."
            )
        model_path = self.model_dir / self.model_file
        if not model_path.exists():
            raise TranslationError(
                f"TranslateGemma model not found: {model_path}. Run the installation script first."
            )
        self.process = subprocess.Popen(
            [server, "-m", str(model_path), "--host", "127.0.0.1", "--port", str(self.port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.monotonic() + 60
        url = f"http://127.0.0.1:{self.port}/health"
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise TranslationError("llama-server exited during startup.")
            try:
                with urllib.request.urlopen(url, timeout=1) as response:
                    if response.status == 200:
                        return
            except (OSError, urllib.error.URLError):
                time.sleep(0.5)
        raise TranslationError("Timed out waiting for llama-server.")

    def translate(self, prompt: str) -> str:
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/completion",
            data=json.dumps({
                "prompt": prompt,
                "temperature": 0.3,
                "top_p": 0.95,
                "top_k": 64,
                "n_predict": 1024,
                "stop": ["<end_of_turn>", "<eos>"],
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                payload = json.loads(response.read().decode("utf-8"))
                return payload.get("content", "").strip()
        except Exception as exc:
            raise TranslationError(f"TranslateGemma request failed: {exc}") from exc

    def stop(self):
        if not self.process:
            return
        if self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        self.process = None


class TranslateGemmaBackend:
    def __init__(self, model_dir: Path, model_file: str):
        self.server = LlamaServer(model_dir, model_file)
        self.server.start()

    def translate_many(self, text, source_lang, target_langs):
        # Adapt the source/target information to TranslateGemma's instruction format.
        names = {"zh": "Chinese", "en": "English", "ja": "Japanese"}
        result = {}
        for target in target_langs:
            prompt = (
                f"Translate the following text from {names[source_lang]} to {names[target]}. "
                "Return only the translation.\n\n"
                f"{text}"
            )
            result[target] = self.server.translate(prompt)
        return result

    def close(self):
        self.server.stop()


class AppleTranslationBackend:
    def __init__(self):
        raise TranslationError(
            "Apple Translation backend is not available in the current Python runtime. "
            "Add the native macOS Translation bridge before selecting it."
        )


class TranslatorService:
    def __init__(self, model_id: str):
        self.model_id = model_id
        self.backend = self._create_backend(model_id)

    def _create_backend(self, model_id):
        info = MODELS.get(model_id)
        if not info:
            raise TranslationError(f"Unknown model: {model_id}")
        if info["backend"] == "nllb":
            return NLLBBackend(info["model_dir"])
        if info["backend"] == "llama":
            return TranslateGemmaBackend(info["model_dir"], info["model_file"])
        if info["backend"] == "apple":
            return AppleTranslationBackend()
        raise TranslationError(f"Unsupported backend: {info['backend']}")

    def translate_many(self, text, source_lang, targets):
        return self.backend.translate_many(text, source_lang, targets)

    def close(self):
        close = getattr(self.backend, "close", None)
        if close:
            close()


def load_saved_model() -> str | None:
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8")).get("model_id")
    except (OSError, ValueError, TypeError):
        return None


def save_model(model_id: str):
    SETTINGS_FILE.write_text(
        json.dumps({"model_id": model_id}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
