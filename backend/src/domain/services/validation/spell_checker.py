# ============================================================
# ✅ 맞춤법 검사기 — 입력 교정과 권장 표현 제공
# ============================================================
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional


_DEFAULT_TERMS: Iterable[str] = (
    "이노스케",
    "젠이츠",
    "네즈코",
    "탄지로",
)


@dataclass
class SpellCheckResult:
    has_typo: bool
    corrected: Optional[str]
    notes: Optional[str] = None

    def as_dict(self) -> Dict[str, Optional[str]]:
        return {
            "has_typo": self.has_typo,
            "corrected": self.corrected,
            "notes": self.notes,
        }


class SpellChecker:
    """단순 유사도 기반 오탈자 교정기."""

    _WORD_RE = re.compile(r"[^\w가-힣]+")

    def __init__(self, vocabulary: Optional[Iterable[str]] = None) -> None:
        base_terms = set(_DEFAULT_TERMS)
        if vocabulary:
            base_terms.update(vocabulary)
        self._vocabulary = sorted(base_terms)
        self._lower_to_word = {word.lower(): word for word in self._vocabulary}

    def check(self, text: str) -> Dict[str, Optional[str]]:
        normalized = text.strip()
        if not normalized:
            return SpellCheckResult(False, None).as_dict()

        tokens = normalized.split()
        corrected_tokens: List[str] = []
        has_typo = False

        for token in tokens:
            lowered = token.lower()
            if lowered in self._lower_to_word:
                corrected_tokens.append(self._lower_to_word[lowered])
                continue

            candidate = self._suggest(token)
            if candidate:
                corrected_tokens.append(candidate)
                has_typo = True
            else:
                corrected_tokens.append(token)

        corrected_text = " ".join(corrected_tokens)
        if has_typo and corrected_text != normalized:
            return SpellCheckResult(True, corrected_text).as_dict()
        return SpellCheckResult(False, None).as_dict()

    def _suggest(self, token: str) -> Optional[str]:
        cleaned = self._WORD_RE.sub("", token.lower())
        if not cleaned:
            return None

        matches = difflib.get_close_matches(cleaned, self._lower_to_word.keys(), n=1, cutoff=0.85)
        if not matches:
            return None
        return self._lower_to_word.get(matches[0])


_SPELL_CHECKER: Optional[SpellChecker] = None


def get_spell_checker() -> SpellChecker:
    global _SPELL_CHECKER
    if _SPELL_CHECKER is None:
        _SPELL_CHECKER = SpellChecker()
    return _SPELL_CHECKER


__all__ = ["SpellChecker", "get_spell_checker"]
