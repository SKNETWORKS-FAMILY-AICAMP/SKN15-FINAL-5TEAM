'''미션 대상 감지(“이노스케”, “젠이츠”, “둘 다”). 키워드/바이그램 코사인 유사도 기반 매칭 수행.'''

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, Iterable, Literal, Optional

MissionTarget = Literal["inosuke", "zenitsu", "both"]

_TARGET_KEYWORDS: Dict[str, Iterable[str]] = {
    "inosuke": ("이노스케", "멧돼지", "inosuke", "ino", "멧돼"),
    "zenitsu": ("젠이츠", "zenitsu", "zen", "츠구코", "번개"),
}

_SPACE_RE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    lowered = text.lower().strip()
    return _SPACE_RE.sub(" ", lowered)


def _char_vector(text: str) -> Counter:
    cleaned = re.sub(r"[^0-9a-z\u3131-\u318f\uac00-\ud7a3 ]", "", text)
    tokens = cleaned.split()
    grams = [cleaned[i : i + 2] for i in range(max(len(cleaned) - 1, 0))]
    return Counter(tokens + grams)


def _cosine_similarity(a: Counter, b: Counter) -> float:
    dot = sum(a[key] * b.get(key, 0) for key in a)
    if dot == 0:
        return 0.0
    norm_a = math.sqrt(sum(value * value for value in a.values()))
    norm_b = math.sqrt(sum(value * value for value in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def detect_mission_target(user_input: str) -> Optional[MissionTarget]:
    """
    Determine which mission branch the user referenced.

    Returns:
        "inosuke", "zenitsu", "both", or None when no confident match exists.
    """
    if not user_input:
        return None

    normalized = _normalize(user_input)
    lowered = normalized.lower()

    matches = {key: False for key in _TARGET_KEYWORDS}
    for target, keywords in _TARGET_KEYWORDS.items():
        for keyword in keywords:
            if keyword and keyword.lower() in lowered:
                matches[target] = True
                break

    if matches["inosuke"] and matches["zenitsu"]:
        return "both"
    if matches["inosuke"]:
        return "inosuke"
    if matches["zenitsu"]:
        return "zenitsu"

    # Fallback to cosine similarity for fuzzy matches
    user_vec = _char_vector(normalized)
    if not user_vec:
        return None

    scored = []
    for target, keywords in _TARGET_KEYWORDS.items():
        ref_vec = _char_vector(" ".join(keywords))
        scored.append((target, _cosine_similarity(user_vec, ref_vec)))

    scored.sort(key=lambda item: item[1], reverse=True)
    best_target, score = scored[0]
    return best_target if score >= 0.35 else None


__all__ = ["detect_mission_target", "MissionTarget"]
