#!/usr/bin/env python3

import argparse
import time
from pathlib import Path

from config import LANGUAGES
from translator import TranslatorService


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark MyTranslator's local NLLB translation."
    )
    parser.add_argument("input", type=Path, help="UTF-8 text file to translate")
    parser.add_argument(
        "--source",
        choices=LANGUAGES,
        required=True,
        help="Source language: zh, en, or ja",
    )
    parser.add_argument(
        "--target",
        choices=LANGUAGES,
        action="append",
        dest="targets",
        help="Target language. Repeat to test multiple targets. Defaults to all other languages.",
    )
    args = parser.parse_args()

    text = args.input.read_text(encoding="utf-8")
    targets = args.targets or [lang for lang in LANGUAGES if lang != args.source]

    print(f"Input characters: {len(text.strip())}")
    print(f"Source: {LANGUAGES[args.source]['label']}")
    print("Targets:", ", ".join(LANGUAGES[lang]["label"] for lang in targets))

    load_start = time.perf_counter()
    service = TranslatorService()
    load_seconds = time.perf_counter() - load_start
    print(f"Model load time: {load_seconds:.3f} s")

    translate_start = time.perf_counter()
    results = service.translate_many(text, args.source, targets)
    translate_seconds = time.perf_counter() - translate_start

    print(f"Translation time: {translate_seconds:.3f} s")
    if translate_seconds > 0:
        print(f"Input chars/sec: {len(text.strip()) / translate_seconds:.1f}")

    print("\n===== Results =====")
    for lang in targets:
        print(f"\n[{LANGUAGES[lang]['label']}]")
        print(results.get(lang, ""))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
