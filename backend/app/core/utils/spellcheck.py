"""
Spell Checking Utility
한국어 맞춤법 검사 (py-hanspell)

Features:
- 네이버/다음 맞춤법 검사 API 활용
- 오타 자동 교정
- 교정 제안
- 한국어 특화
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

try:
    from hanspell import spell_checker
    HANSPELL_AVAILABLE = True
except ImportError:
    HANSPELL_AVAILABLE = False

from app.core.logging import get_parent_logger

logger = get_parent_logger("SpellChecker")


@dataclass
class SpellCheckResult:
    """맞춤법 검사 결과"""
    original_text: str
    corrected_text: str
    errors_found: int
    suggestions: List[Dict[str, str]]  # [{"original": "...", "corrected": "..."}]
    has_errors: bool


class SpellChecker:
    """
    한국어 맞춤법 검사 시스템

    py-hanspell 라이브러리를 사용하여 네이버/다음 맞춤법 검사 API 활용

    Example:
        checker = SpellChecker()
        result = checker.check("안녕하세요 저는 학생이에요")
        print(result.corrected_text)
        print(result.has_errors)
    """

    def __init__(self):
        """SpellChecker 초기화"""
        if not HANSPELL_AVAILABLE:
            logger.warning("__init__", "py-hanspell not available, spell checking disabled")
        else:
            logger.info("__init__", "SpellChecker initialized")

    def check(self, text: str) -> SpellCheckResult:
        """
        맞춤법 검사

        Args:
            text: 검사할 텍스트

        Returns:
            SpellCheckResult
        """
        if not text or not text.strip():
            return SpellCheckResult(
                original_text=text,
                corrected_text=text,
                errors_found=0,
                suggestions=[],
                has_errors=False
            )

        if not HANSPELL_AVAILABLE:
            logger.warning("check", "Spell checking not available (py-hanspell not installed)")
            return SpellCheckResult(
                original_text=text,
                corrected_text=text,
                errors_found=0,
                suggestions=[],
                has_errors=False
            )

        try:
            # py-hanspell 사용
            result = spell_checker.check(text)

            # 결과 파싱
            original = result.original
            corrected = result.checked
            errors = result.errors

            # 오류 위치 추출
            suggestions = []
            if errors > 0:
                # 변경된 부분 찾기 (간단한 구현)
                orig_words = original.split()
                corr_words = corrected.split()

                for i, (orig_word, corr_word) in enumerate(zip(orig_words, corr_words)):
                    if orig_word != corr_word:
                        suggestions.append({
                            "original": orig_word,
                            "corrected": corr_word
                        })

            logger.info("check", f"Spell check complete",
                       errors_found=errors,
                       text_len=len(text))

            return SpellCheckResult(
                original_text=original,
                corrected_text=corrected,
                errors_found=errors,
                suggestions=suggestions,
                has_errors=errors > 0
            )

        except Exception as e:
            logger.error("check", f"Spell check failed: {e}")
            return SpellCheckResult(
                original_text=text,
                corrected_text=text,
                errors_found=0,
                suggestions=[],
                has_errors=False
            )

    def correct(self, text: str) -> str:
        """
        맞춤법 자동 교정 (교정된 텍스트만 반환)

        Args:
            text: 교정할 텍스트

        Returns:
            교정된 텍스트
        """
        result = self.check(text)
        return result.corrected_text

    def has_errors(self, text: str) -> bool:
        """
        오류 존재 여부만 확인

        Args:
            text: 검사할 텍스트

        Returns:
            오류 존재 여부
        """
        result = self.check(text)
        return result.has_errors

    def check_batch(self, texts: List[str]) -> List[SpellCheckResult]:
        """
        여러 텍스트 일괄 검사

        Args:
            texts: 검사할 텍스트 리스트

        Returns:
            SpellCheckResult 리스트
        """
        results = []
        for text in texts:
            result = self.check(text)
            results.append(result)

        logger.info("check_batch", f"Batch spell check complete",
                   total=len(texts),
                   errors_found=sum(r.errors_found for r in results))

        return results

    def suggest_corrections(self, text: str) -> List[Dict[str, str]]:
        """
        교정 제안만 반환

        Args:
            text: 검사할 텍스트

        Returns:
            교정 제안 리스트 [{"original": "...", "corrected": "..."}]
        """
        result = self.check(text)
        return result.suggestions
