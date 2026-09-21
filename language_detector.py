from dataclasses import dataclass
import re
from typing import Optional

@dataclass(frozen=True)
class DetectionResult:
    language: Optional[str]
    confidence: float
    reliable: bool

_HIRAGANA = re.compile(r"[\u3040-\u309f]")
_KATAKANA = re.compile(r"[\u30a0-\u30ff]")
_HAN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uF900-\uFAFF]")
_LATIN = re.compile(r"[A-Za-z]")
_EN_WORD = re.compile(r"\b(?:the|and|is|are|to|of|in|for|with|this|that|you|i|a|an)\b", re.I)
_ZH_WORD = re.compile(r"(?:的|了|是|在|我|你|和|有|不|这|那|一个|可以|中文)")

def detect_language(text: str, last_detected_language: Optional[str] = None) -> DetectionResult:
    s = text.strip()
    if not s:
        return DetectionResult(None, 0.0, False)
    hira = len(_HIRAGANA.findall(s))
    kata = len(_KATAKANA.findall(s))
    han = len(_HAN.findall(s))
    latin = len(_LATIN.findall(s))
    en_words = len(_EN_WORD.findall(s))
    zh_words = len(_ZH_WORD.findall(s))

    if hira + kata:
        return DetectionResult("ja", min(0.99, 0.78 + 0.04 * min(hira + kata, 4)), True)
    if en_words and latin >= han:
        return DetectionResult("en", min(0.98, 0.76 + 0.05 * min(en_words, 4)), True)
    if zh_words and han >= 1 and latin <= han:
        return DetectionResult("zh", min(0.95, 0.74 + 0.06 * min(zh_words, 3)), True)
    if latin > 0 and han == 0:
        letters = len(_LATIN.findall(s))
        return DetectionResult("en", 0.62 + min(0.25, letters / 80), letters >= 4)
    if han > 0:
        if last_detected_language in ("zh", "ja"):
            return DetectionResult(last_detected_language, 0.58, False)
        return DetectionResult(None, 0.50, False)
    return DetectionResult(None, 0.0, False)
