from __future__ import annotations

from typing import Iterable, Optional, Sequence

from .embedding_matcher import EmbeddingMatcher

_INOSUKE_TERMS: Iterable[str] = (
    "이노스케",
    "멧돼지",
    "inosuke",
    "ino",
    "멧돼",
    "ino suke",
)

_ZENITSU_TERMS: Iterable[str] = (
    "젠이츠",
    "zenitsu",
    "zen",
    "츠구코",
    "번개",
    "zen itsu",
)


_MISSION_TARGET_MATCHER = EmbeddingMatcher(
    {
        "inosuke": _INOSUKE_TERMS,
        "zenitsu": _ZENITSU_TERMS,
    },
    threshold=0.82,
)


def detect_mission_target(text: str, *, embedding: Optional[Sequence[float]] = None) -> Optional[str]:
    """
    Detect which mission target the user refers to.

    Returns:
        "inosuke", "zenitsu", "both", or None.
    """
    if not text:
        return None

    normalized = text.strip()
    if not normalized:
        return None

    lowered = normalized.lower()
    has_inosuke = any(term.lower() in lowered for term in _INOSUKE_TERMS if term)
    has_zenitsu = any(term.lower() in lowered for term in _ZENITSU_TERMS if term)

    if has_inosuke and has_zenitsu:
        return "both"

    result = _MISSION_TARGET_MATCHER.match(normalized, embedding=embedding)
    return result.label


__all__ = ["detect_mission_target"]
