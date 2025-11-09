"""
Fuzzy Matching Utility
오타 허용 문자열 매칭 (fuzzywuzzy + Levenshtein)

Features:
- 레벤슈타인 거리 기반 유사도 계산
- 부분 문자열 매칭
- 토큰 기반 매칭
- 한국어/영어 모두 지원
"""
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

try:
    from fuzzywuzzy import fuzz, process
    FUZZYWUZZY_AVAILABLE = True
except ImportError:
    FUZZYWUZZY_AVAILABLE = False

try:
    import Levenshtein
    LEVENSHTEIN_AVAILABLE = True
except ImportError:
    LEVENSHTEIN_AVAILABLE = False

from app.core.logging import get_parent_logger

logger = get_parent_logger("FuzzyMatcher")


@dataclass
class FuzzyMatchResult:
    """퍼지 매칭 결과"""
    matched_text: str
    original_text: str
    score: int  # 0-100
    method: str  # 'exact', 'fuzzy', 'partial', 'token'


class FuzzyMatcher:
    """
    오타 허용 문자열 매칭 시스템

    Methods:
    - exact_match: 정확한 매칭
    - fuzzy_match: 레벤슈타인 거리 기반 매칭
    - partial_match: 부분 문자열 매칭
    - token_match: 토큰 기반 매칭
    - best_match: 가장 유사한 후보 찾기

    Example:
        matcher = FuzzyMatcher(threshold=80)
        result = matcher.best_match("탄지로", ["탄지로", "렌고쿠", "이노스케"])
        # result.matched_text == "탄지로", result.score == 100

        result = matcher.best_match("단지로", ["탄지로", "렌고쿠"])
        # result.matched_text == "탄지로", result.score ~= 85 (오타 허용)
    """

    def __init__(self, threshold: int = 80):
        """
        Args:
            threshold: 매칭 임계값 (0-100, 높을수록 엄격)
        """
        self.threshold = threshold

        if not FUZZYWUZZY_AVAILABLE:
            logger.warning("__init__", "fuzzywuzzy not available, using fallback")

        if not LEVENSHTEIN_AVAILABLE:
            logger.warning("__init__", "python-Levenshtein not available, performance may be slow")

        logger.info("__init__", "FuzzyMatcher initialized", threshold=threshold)

    def exact_match(self, query: str, candidate: str) -> FuzzyMatchResult:
        """
        정확한 매칭 (대소문자 구분 안함)

        Args:
            query: 검색 문자열
            candidate: 후보 문자열

        Returns:
            FuzzyMatchResult
        """
        score = 100 if query.lower() == candidate.lower() else 0
        return FuzzyMatchResult(
            matched_text=candidate if score == 100 else "",
            original_text=query,
            score=score,
            method="exact"
        )

    def fuzzy_match(self, query: str, candidate: str) -> FuzzyMatchResult:
        """
        퍼지 매칭 (레벤슈타인 거리 기반)

        Args:
            query: 검색 문자열
            candidate: 후보 문자열

        Returns:
            FuzzyMatchResult
        """
        if not FUZZYWUZZY_AVAILABLE:
            # Fallback: simple similarity
            score = self._simple_similarity(query, candidate)
        else:
            score = fuzz.ratio(query, candidate)

        return FuzzyMatchResult(
            matched_text=candidate if score >= self.threshold else "",
            original_text=query,
            score=score,
            method="fuzzy"
        )

    def partial_match(self, query: str, candidate: str) -> FuzzyMatchResult:
        """
        부분 문자열 매칭

        Args:
            query: 검색 문자열
            candidate: 후보 문자열

        Returns:
            FuzzyMatchResult
        """
        if not FUZZYWUZZY_AVAILABLE:
            # Fallback: substring check
            if query.lower() in candidate.lower():
                score = 80
            else:
                score = self._simple_similarity(query, candidate)
        else:
            score = fuzz.partial_ratio(query, candidate)

        return FuzzyMatchResult(
            matched_text=candidate if score >= self.threshold else "",
            original_text=query,
            score=score,
            method="partial"
        )

    def token_match(self, query: str, candidate: str) -> FuzzyMatchResult:
        """
        토큰 기반 매칭 (순서 무시)

        Args:
            query: 검색 문자열
            candidate: 후보 문자열

        Returns:
            FuzzyMatchResult
        """
        if not FUZZYWUZZY_AVAILABLE:
            # Fallback: simple token overlap
            query_tokens = set(query.split())
            candidate_tokens = set(candidate.split())
            if query_tokens and candidate_tokens:
                overlap = len(query_tokens & candidate_tokens)
                score = int((overlap / max(len(query_tokens), len(candidate_tokens))) * 100)
            else:
                score = 0
        else:
            score = fuzz.token_sort_ratio(query, candidate)

        return FuzzyMatchResult(
            matched_text=candidate if score >= self.threshold else "",
            original_text=query,
            score=score,
            method="token"
        )

    def best_match(
        self,
        query: str,
        candidates: List[str],
        limit: int = 1
    ) -> List[FuzzyMatchResult]:
        """
        가장 유사한 후보 찾기

        Args:
            query: 검색 문자열
            candidates: 후보 문자열 리스트
            limit: 반환할 최대 개수

        Returns:
            FuzzyMatchResult 리스트 (유사도 내림차순)
        """
        if not candidates:
            return []

        results = []

        # 1. Exact match 시도
        for candidate in candidates:
            exact_result = self.exact_match(query, candidate)
            if exact_result.score == 100:
                return [exact_result]

        # 2. Fuzzy match
        if FUZZYWUZZY_AVAILABLE:
            # fuzzywuzzy의 process.extract 사용
            matches = process.extract(query, candidates, limit=limit)
            for matched_text, score in matches:
                if score >= self.threshold:
                    results.append(FuzzyMatchResult(
                        matched_text=matched_text,
                        original_text=query,
                        score=score,
                        method="fuzzy"
                    ))
        else:
            # Fallback: manual fuzzy matching
            scored_candidates = []
            for candidate in candidates:
                result = self.fuzzy_match(query, candidate)
                if result.score >= self.threshold:
                    scored_candidates.append(result)

            # Sort by score descending
            scored_candidates.sort(key=lambda x: x.score, reverse=True)
            results = scored_candidates[:limit]

        logger.debug("best_match", f"Found {len(results)} matches for '{query}'",
                    threshold=self.threshold)

        return results

    def find_closest(
        self,
        query: str,
        candidates: List[str]
    ) -> Optional[FuzzyMatchResult]:
        """
        가장 가까운 후보 하나만 반환 (threshold 무시)

        Args:
            query: 검색 문자열
            candidates: 후보 문자열 리스트

        Returns:
            가장 유사한 FuzzyMatchResult 또는 None
        """
        if not candidates:
            return None

        # Exact match 먼저 확인
        for candidate in candidates:
            if query.lower() == candidate.lower():
                return FuzzyMatchResult(
                    matched_text=candidate,
                    original_text=query,
                    score=100,
                    method="exact"
                )

        # Fuzzy match
        best_score = 0
        best_candidate = None

        for candidate in candidates:
            if FUZZYWUZZY_AVAILABLE:
                score = fuzz.ratio(query, candidate)
            else:
                score = self._simple_similarity(query, candidate)

            if score > best_score:
                best_score = score
                best_candidate = candidate

        if best_candidate:
            return FuzzyMatchResult(
                matched_text=best_candidate,
                original_text=query,
                score=best_score,
                method="fuzzy"
            )

        return None

    def _simple_similarity(self, s1: str, s2: str) -> int:
        """
        간단한 유사도 계산 (Fallback)

        Args:
            s1: 문자열 1
            s2: 문자열 2

        Returns:
            유사도 (0-100)
        """
        if s1 == s2:
            return 100

        if not s1 or not s2:
            return 0

        # Levenshtein distance (manual implementation)
        if LEVENSHTEIN_AVAILABLE:
            distance = Levenshtein.distance(s1, s2)
            max_len = max(len(s1), len(s2))
            if max_len == 0:
                return 100
            similarity = (1 - distance / max_len) * 100
            return int(similarity)

        # Fallback: character overlap
        s1_chars = set(s1.lower())
        s2_chars = set(s2.lower())
        overlap = len(s1_chars & s2_chars)
        total = len(s1_chars | s2_chars)

        if total == 0:
            return 0

        return int((overlap / total) * 100)

    def correct_typo(
        self,
        text: str,
        vocabulary: List[str],
        word_threshold: int = 70
    ) -> str:
        """
        오타 자동 교정

        Args:
            text: 교정할 텍스트
            vocabulary: 올바른 단어 목록
            word_threshold: 단어별 매칭 임계값

        Returns:
            교정된 텍스트
        """
        words = text.split()
        corrected_words = []

        for word in words:
            # 정확히 일치하는 단어가 있으면 그대로 사용
            if word in vocabulary:
                corrected_words.append(word)
                continue

            # 유사한 단어 찾기
            original_threshold = self.threshold
            self.threshold = word_threshold

            matches = self.best_match(word, vocabulary, limit=1)

            self.threshold = original_threshold

            if matches and matches[0].score >= word_threshold:
                corrected_word = matches[0].matched_text
                logger.debug("correct_typo", f"Corrected '{word}' → '{corrected_word}'",
                           score=matches[0].score)
                corrected_words.append(corrected_word)
            else:
                # 매칭 실패 시 원본 유지
                corrected_words.append(word)

        return " ".join(corrected_words)
