"""
[Core/Utils] Fuzzy Matching 유틸리티

이 모듈은 오타나 약간의 차이를 허용하는 '유사 문자열 매칭(Fuzzy String Matching)'
기능을 제공합니다. `fuzzywuzzy`와 `python-Levenshtein` 라이브러리를 활용하여
레벤슈타인 거리(Levenshtein distance) 기반의 다양한 비교 알고리즘을 제공합니다.

주요 기능:
- 문자열 간의 유사도 점수 계산
- 후보 목록에서 가장 유사한 문자열 추출
- 부분 문자열, 토큰 순서 무시 등 다양한 매칭 전략 제공

NOTE: 이 모듈의 모든 기능을 사용하려면 `requirements.txt`에 명시된
      `fuzzywuzzy`와 `python-Levenshtein` 라이브러리가 설치되어 있어야 합니다.
      라이브러리가 없어도 기본적인 폴백(fallback) 기능은 동작합니다.
"""
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

# fuzzywuzzy 라이브러리 임포트 시도 및 사용 가능 여부 확인
try:
    from fuzzywuzzy import fuzz, process
    FUZZYWUZZY_AVAILABLE = True
except ImportError:
    FUZZYWUZZY_AVAILABLE = False

# python-Levenshtein 라이브러리 임포트 시도 (C 기반으로 성능 향상)
try:
    import Levenshtein
    LEVENSHTEIN_AVAILABLE = True
except ImportError:
    LEVENSHTEIN_AVAILABLE = False

from app.core.logging import get_parent_logger

logger = get_parent_logger("FuzzyMatcher")


# ============================================================
# 매칭 결과 데이터 클래스
# ============================================================
@dataclass
class FuzzyMatchResult:
    """퍼지 매칭의 결과를 담는 데이터 클래스입니다."""
    matched_text: str   # 매칭된 후보 문자열
    original_text: str  # 원본 검색 문자열
    score: int          # 유사도 점수 (0-100)
    method: str         # 사용된 매칭 방법 (예: 'exact', 'fuzzy')


# ============================================================
# Fuzzy Matcher 클래스
# ============================================================
class FuzzyMatcher:
    """
    오타를 허용하는 다양한 문자열 매칭 알고리즘을 제공하는 클래스입니다.

    Example:
        matcher = FuzzyMatcher(threshold=80)
        # '단지로'라는 오타를 '탄지로'로 찾아냄
        result = matcher.best_match("단지로", ["탄지로", "렌고쿠", "이노스케"])
        if result:
            print(result[0].matched_text, result[0].score)
            # 출력: 탄지로 86
    """

    def __init__(self, threshold: int = 80):
        """
        FuzzyMatcher를 초기화합니다.

        Args:
            threshold (int): 매칭으로 인정할 최소 유사도 점수 (0-100).
                             이 값보다 낮으면 매칭 실패로 간주됩니다.
        """
        self.threshold = threshold
        if not FUZZYWUZZY_AVAILABLE:
            logger.warning("__init__", "fuzzywuzzy library not found. Using basic fallback methods.")
        if not LEVENSHTEIN_AVAILABLE:
            logger.warning("__init__", "python-Levenshtein not found. Performance may be slower.")
        logger.info("__init__", "FuzzyMatcher initialized", threshold=threshold)

    def fuzzy_match(self, query: str, candidate: str) -> FuzzyMatchResult:
        """
        가장 기본적인 퍼지 매칭을 수행합니다. (레벤슈타인 거리 기반)
        전체 문자열 간의 유사도를 계산합니다.
        """
        score = fuzz.ratio(query, candidate) if FUZZYWUZZY_AVAILABLE else self._simple_similarity(query, candidate)
        return FuzzyMatchResult(
            matched_text=candidate if score >= self.threshold else "",
            original_text=query,
            score=score,
            method="fuzzy"
        )

    def partial_match(self, query: str, candidate: str) -> FuzzyMatchResult:
        """
        부분 문자열 매칭을 수행합니다.
        짧은 문자열이 긴 문자열 안에 포함되어 있는지 여부를 중심으로 유사도를 계산합니다.
        """
        if FUZZYWUZZY_AVAILABLE:
            score = fuzz.partial_ratio(query, candidate)
        else: # Fallback
            score = 80 if query.lower() in candidate.lower() else self._simple_similarity(query, candidate)
        return FuzzyMatchResult(
            matched_text=candidate if score >= self.threshold else "",
            original_text=query,
            score=score,
            method="partial"
        )

    def token_match(self, query: str, candidate: str) -> FuzzyMatchResult:
        """
        토큰 기반 매칭을 수행합니다. 문자열을 공백 기준으로 단어(토큰)로 나눈 뒤,
        순서에 상관없이 토큰들의 유사도를 계산합니다.
        """
        if FUZZYWUZZY_AVAILABLE:
            score = fuzz.token_sort_ratio(query, candidate)
        else: # Fallback
            query_tokens = set(query.split())
            candidate_tokens = set(candidate.split())
            if not (query_tokens and candidate_tokens):
                score = 0
            else:
                overlap = len(query_tokens & candidate_tokens)
                total = max(len(query_tokens), len(candidate_tokens))
                score = int((overlap / total) * 100) if total > 0 else 0
        return FuzzyMatchResult(
            matched_text=candidate if score >= self.threshold else "",
            original_text=query,
            score=score,
            method="token"
        )

    def best_match(self, query: str, candidates: List[str], limit: int = 1) -> List[FuzzyMatchResult]:
        """
        주어진 후보 목록(`candidates`)에서 `query`와 가장 유사한 항목을 찾습니다.

        Args:
            query (str): 검색할 문자열.
            candidates (List[str]): 비교 대상이 될 문자열 목록.
            limit (int): 반환할 최상위 매칭 결과의 수.

        Returns:
            List[FuzzyMatchResult]: 유사도 점수가 높은 순으로 정렬된 매칭 결과 리스트.
        """
        if not candidates:
            return []

        # 1. 정확히 일치하는 경우를 먼저 확인 (가장 높은 우선순위)
        for candidate in candidates:
            if query.lower() == candidate.lower():
                return [FuzzyMatchResult(candidate, query, 100, "exact")]

        # 2. fuzzywuzzy 라이브러리가 있으면 효율적인 process.extract 사용
        if FUZZYWUZZY_AVAILABLE:
            matches = process.extract(query, candidates, limit=limit, scorer=fuzz.ratio)
            return [
                FuzzyMatchResult(matched_text, query, score, "fuzzy")
                for matched_text, score in matches if score >= self.threshold
            ]
        
        # 3. Fallback: 수동으로 모든 후보와 비교
        scored_candidates = [res for res in (self.fuzzy_match(query, c) for c in candidates) if res.score >= self.threshold]
        scored_candidates.sort(key=lambda x: x.score, reverse=True)
        return scored_candidates[:limit]

    def _simple_similarity(self, s1: str, s2: str) -> int:
        """
        `fuzzywuzzy`가 없을 때 사용하는 간단한 유사도 계산 폴백 메서드.
        `python-Levenshtein`이 있으면 사용하고, 없으면 단순 문자 중복도를 계산합니다.
        """
        if s1 == s2: return 100
        if not s1 or not s2: return 0

        # C로 구현되어 성능이 좋은 Levenshtein 라이브러리가 있으면 우선 사용
        if LEVENSHTEIN_AVAILABLE:
            distance = Levenshtein.distance(s1, s2)
            max_len = max(len(s1), len(s2))
            if max_len == 0: return 100
            return int((1 - distance / max_len) * 100)

        # 최후의 폴백: 문자 집합의 중복도(Jaccard 유사도와 유사) 계산
        s1_chars, s2_chars = set(s1.lower()), set(s2.lower())
        overlap = len(s1_chars & s2_chars)
        total = len(s1_chars | s2_chars)
        return int((overlap / total) * 100) if total > 0 else 0

    def correct_typo(self, text: str, vocabulary: List[str], word_threshold: int = 70) -> str:
        """
        입력 텍스트의 각 단어를 주어진 어휘 목록(`vocabulary`)과 비교하여 오타를 교정합니다.

        Args:
            text (str): 교정할 원본 텍스트.
            vocabulary (List[str]): 올바른 단어 목록.
            word_threshold (int): 단어를 교체할 최소 유사도 점수.

        Returns:
            str: 오타가 교정된 텍스트.
        """
        words = text.split()
        corrected_words = []
        for word in words:
            if word in vocabulary:
                corrected_words.append(word)
                continue
            
            # best_match를 사용하여 가장 유사한 단어 찾기
            matches = self.best_match(word, vocabulary, limit=1)
            if matches and matches[0].score >= word_threshold:
                corrected_word = matches[0].matched_text
                logger.debug("correct_typo", f"Corrected '{word}' → '{corrected_word}'", score=matches[0].score)
                corrected_words.append(corrected_word)
            else:
                corrected_words.append(word) # 매칭 실패 시 원본 단어 유지
        return " ".join(corrected_words)

# ============================================================
# 전역 유틸리티 인스턴스
# ============================================================
_fuzzy_matcher_instance: Optional[FuzzyMatcher] = None

def get_fuzzy_matcher(threshold: int = 80) -> FuzzyMatcher:
    """
    FuzzyMatcher의 싱글톤 인스턴스를 반환합니다.
    (threshold가 다르면 다른 인스턴스가 생성될 수 있으므로 엄밀한 싱글톤은 아님)
    """
    global _fuzzy_matcher_instance
    if _fuzzy_matcher_instance is None or _fuzzy_matcher_instance.threshold != threshold:
        _fuzzy_matcher_instance = FuzzyMatcher(threshold=threshold)
    return _fuzzy_matcher_instance
