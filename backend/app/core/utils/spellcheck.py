"""
[Core/Utils] 한국어 맞춤법 검사 유틸리티

이 모듈은 `py-hanspell` 라이브러리를 사용하여 한국어 텍스트의 맞춤법을
검사하고 교정하는 `SpellChecker` 클래스를 제공합니다.
네이버 맞춤법 검사기 API를 기반으로 동작합니다.

주요 기능:
- 텍스트의 맞춤법 오류 검사 및 교정
- 교정 제안 목록 제공
- 여러 텍스트에 대한 일괄 검사

NOTE: 이 모듈의 모든 기능을 사용하려면 `requirements.txt`에 명시된
      `py-hanspell` 라이브러리가 설치되어 있어야 합니다.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# py-hanspell 라이브러리 임포트 시도 및 사용 가능 여부 확인
try:
    from hanspell import spell_checker
    HANSPELL_AVAILABLE = True
except ImportError:
    HANSPELL_AVAILABLE = False

from app.core.logging import get_parent_logger

logger = get_parent_logger("SpellChecker")


# ============================================================
# 맞춤법 검사 결과 데이터 클래스
# ============================================================
@dataclass
class SpellCheckResult:
    """맞춤법 검사의 결과를 담는 데이터 클래스입니다."""
    original_text: str  # 원본 텍스트
    corrected_text: str # 교정된 텍스트
    errors_found: int   # 발견된 오류 수
    suggestions: List[Dict[str, str]]  # 교정 제안 목록 (예: [{"original": "안녕 하세요", "corrected": "안녕하세요"}])
    has_errors: bool    # 오류 존재 여부


# ============================================================
# 맞춤법 검사기 클래스
# ============================================================
class SpellChecker:
    """
    `py-hanspell` 라이브러리를 사용하여 한국어 맞춤법을 검사하는 클래스입니다.

    Example:
        checker = SpellChecker()
        if checker.is_available():
            result = checker.check("아버지가방에들어가신다.")
            print(result.corrected_text)
            # 출력: 아버지가 방에 들어가신다.
    """

    def __init__(self):
        """SpellChecker를 초기화합니다."""
        if not HANSPELL_AVAILABLE:
            logger.warning("__init__", "py-hanspell library not found. Spell checking will be disabled.")
        else:
            logger.info("__init__", "SpellChecker initialized.")

    def is_available(self) -> bool:
        """맞춤법 검사 기능이 사용 가능한지 확인합니다."""
        return HANSPELL_AVAILABLE

    def check(self, text: str) -> SpellCheckResult:
        """
        주어진 텍스트의 맞춤법을 검사하고 상세한 결과를 반환합니다.

        Args:
            text (str): 검사할 한국어 텍스트.

        Returns:
            SpellCheckResult: 맞춤법 검사 결과 객체.
        """
        if not self.is_available() or not text or not text.strip():
            return SpellCheckResult(text, text, 0, [], False)

        try:
            # hanspell 라이브러리를 사용하여 맞춤법 검사 실행
            result = spell_checker.check(text)

            suggestions = [
                {"original": err_info['original'], "corrected": err_info['correct']}
                for err_info in result.words
            ]
            
            logger.info("check", "Spell check complete", errors_found=result.errors, text_len=len(text))

            return SpellCheckResult(
                original_text=result.original,
                corrected_text=result.checked,
                errors_found=result.errors,
                suggestions=suggestions,
                has_errors=(result.errors > 0)
            )
        except Exception as e:
            logger.error("check", f"Spell check failed due to an unexpected error: {e}", text_len=len(text))
            # API 오류 발생 시 원본 텍스트를 그대로 반환
            return SpellCheckResult(text, text, 0, [], False)

    def correct(self, text: str) -> str:
        """
        텍스트의 맞춤법을 검사하고 교정된 텍스트만 간단히 반환합니다.

        Args:
            text (str): 교정할 텍스트.

        Returns:
            str: 맞춤법이 교정된 텍스트.
        """
        return self.check(text).corrected_text

    def has_errors(self, text: str) -> bool:
        """텍스트에 맞춤법 오류가 있는지 여부만 확인합니다."""
        return self.check(text).has_errors

    def check_batch(self, texts: List[str]) -> List[SpellCheckResult]:
        """
        여러 텍스트를 한 번에 검사합니다.

        Args:
            texts (List[str]): 검사할 텍스트 목록.

        Returns:
            List[SpellCheckResult]: 각 텍스트에 대한 검사 결과 목록.
        """
        results = [self.check(text) for text in texts]
        logger.info("check_batch", "Batch spell check complete", total=len(texts), errors_found=sum(r.errors_found for r in results))
        return results

    def suggest_corrections(self, text: str) -> List[Dict[str, str]]:
        """텍스트의 맞춤법 오류에 대한 교정 제안 목록만 반환합니다."""
        return self.check(text).suggestions

# ============================================================
# 전역 유틸리티 인스턴스
# ============================================================
_spell_checker_instance: Optional[SpellChecker] = None

def get_spell_checker() -> SpellChecker:
    """
    SpellChecker의 싱글톤 인스턴스를 반환합니다.
    """
    global _spell_checker_instance
    if _spell_checker_instance is None:
        _spell_checker_instance = SpellChecker()
    return _spell_checker_instance
