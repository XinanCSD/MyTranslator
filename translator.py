import json
import logging
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import ctranslate2
import sentencepiece as spm

from config import BEAM_SIZE, LANGUAGES, MAX_DECODING_LENGTH, MODELS

logger = logging.getLogger(__name__)


class TranslationError(RuntimeError):
    pass


class NLLBTokenizer:
    EOS_TOKEN = "</s>"

    def __init__(self, model_dir):
        sp_path = Path(model_dir) / "sentencepiece.bpe.model"
        if not sp_path.exists():
            raise TranslationError(f"Tokenizer model not found: {sp_path}")
        self.sp = spm.SentencePieceProcessor()
        if not self.sp.Load(str(sp_path)):
            raise TranslationError(f"Failed to load tokenizer model: {sp_path}")

    def encode(self, text, source_lang):
        return [source_lang, *self.sp.EncodeAsPieces(text.strip()), self.EOS_TOKEN]

    def decode(self, tokens):
        return self.sp.DecodePieces(tokens).strip()


class NLLBBackend:
    def __init__(self, model_dir):
        model_dir = Path(model_dir)
        if not model_dir.exists():
            raise TranslationError(
                f"NLLB model not found: {model_dir}. Run the installation script first."
            )
        try:
            self.translator = ctranslate2.Translator(str(model_dir), device="auto")
            self.tokenizer = NLLBTokenizer(model_dir)
        except Exception as exc:
            logger.exception("Failed to load NLLB")
            raise TranslationError(f"Failed to load NLLB: {exc}") from exc

    def translate_many(self, text, source_lang, target_langs):
        targets = [x for x in target_langs if x in LANGUAGES and x != source_lang]
        if not targets:
            return {}
        try:
            source = self.tokenizer.encode(text, LANGUAGES[source_lang]["code"])
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
        except Exception as exc:
            logger.exception("NLLB translation failed")
            raise TranslationError(f"NLLB translation failed: {exc}") from exc


class LlamaServer:
    def __init__(self, model_dir, model_file):
        self.model_path = Path(model_dir) / model_file
        self.process = None
        self.port = 39001

    @staticmethod
    def _executable():
        names = ["llama-server.exe", "llama-server"] if sys.platform == "win32" else ["llama-server"]
        for name in names:
            path = shutil.which(name)
            if path:
                return path
        return None

    def start(self):
        if self.process and self.process.poll() is None:
            return
        executable = self._executable()
        if not executable:
            raise TranslationError(
                "llama-server was not found. Run the installation script first."
            )
        if not self.model_path.exists():
            raise TranslationError(
                f"TranslateGemma model not found: {self.model_path}. Run the installation script first."
            )

        self.process = subprocess.Popen(
            [
                executable,
                "-m", str(self.model_path),
                "--host", "127.0.0.1",
                "--port", str(self.port),
                "--jinja",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        deadline = time.monotonic() + 90
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

        self.stop()
        raise TranslationError("Timed out waiting for llama-server.")

    def translate(self, prompt):
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
        process, self.process = self.process, None
        if process is None or process.poll() is not None:
            return
        try:
            process.terminate()
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


class TranslateGemmaBackend:
    LANGUAGE_NAMES = {
        "zh": ("Chinese", "zh"),
        "en": ("English", "en"),
        "ja": ("Japanese", "ja"),
    }

    def __init__(self, model_dir, model_file):
        self.server = LlamaServer(model_dir, model_file)
        self.server.start()

    def _prompt(self, text, source_lang, target_lang):
        source_name, source_code = self.LANGUAGE_NAMES[source_lang]
        target_name, target_code = self.LANGUAGE_NAMES[target_lang]
        return (
            "<bos><start_of_turn>user\\n"
            f"You are a professional {source_name} ({source_code}) to "
            f"{target_name} ({target_code}) translator. Your goal is to accurately "
            f"convey the meaning and nuances of the original {source_name} text while "
            f"adhering to {target_name} grammar, vocabulary, and cultural sensitivities.\\n"
            f"Produce only the {target_name} translation, without any additional "
            f"explanations or commentary. Please translate the following {source_name} "
            f"text into {target_name}:\\n\\n\\n"
            f"{text.strip()}<end_of_turn>\\n"
            "<start_of_turn>model\\n"
        )

    def translate_many(self, text, source_lang, target_langs):
        results = {}
        for target in target_langs:
            if target in self.LANGUAGE_NAMES:
                results[target] = self.server.translate(self._prompt(text, source_lang, target))
        return results

    def close(self):
        self.server.stop()


class AppleTranslationBackend:
    def __init__(self):
        if sys.platform != "darwin":
            raise TranslationError("Apple Translation is only available on macOS.")
        root = Path(__file__).resolve().parent
        candidates = [
            root / "native" / "AppleTranslationBridge" / ".build" / "release" / "apple-translation-bridge",
            root / "native" / "AppleTranslationBridge" / ".build" / "debug" / "apple-translation-bridge",
        ]
        self.executable = next((p for p in candidates if p.exists()), None)
        if self.executable is None:
            raise TranslationError("Apple Translation bridge is not built. Run ./install.sh on macOS.")

    def translate_many(self, text, source_lang, target_langs):
        return {target: self._translate_one(text, source_lang, target) for target in target_langs}

    def _translate_one(self, text, source_lang, target_lang):
        payload = json.dumps({
            "source": LANGUAGES[source_lang]["code"].split("_")[0],
            "target": LANGUAGES[target_lang]["code"].split("_")[0],
            "text": text,
        }, ensure_ascii=False).encode("utf-8")
        try:
            completed = subprocess.run(
                [str(self.executable)], input=payload,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=180, check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise TranslationError("Apple Translation timed out.") from exc
        if completed.returncode != 0:
            error = completed.stderr.decode("utf-8", errors="replace").strip()
            raise TranslationError(error or "Apple Translation bridge failed.")
        try:
            response = json.loads(completed.stdout.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise TranslationError("Invalid response from Apple Translation bridge.") from exc
        if not response.get("ok"):
            raise TranslationError(response.get("error") or "Apple Translation failed.")
        return response["translation"]


class TranslatorService:
    def __init__(self, model_id):
        info = MODELS.get(model_id)
        if not info:
            raise TranslationError(f"Unknown model: {model_id}")
        self.model_id = model_id
        backend = info["backend"]
        if backend == "nllb":
            self.backend = NLLBBackend(info["model_dir"])
        elif backend == "llama":
            self.backend = TranslateGemmaBackend(info["model_dir"], info["model_file"])
        elif backend == "apple":
            self.backend = AppleTranslationBackend()
        else:
            raise TranslationError(f"Unsupported backend: {backend}")

    def translate_many(self, text, source_lang, targets):
        if source_lang not in LANGUAGES:
            raise TranslationError(f"Unsupported source language: {source_lang}")
        return self.backend.translate_many(text, source_lang, targets)

    def close(self):
        close = getattr(self.backend, "close", None)
        if close:
            close()
